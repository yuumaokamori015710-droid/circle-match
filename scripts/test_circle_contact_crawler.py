"""Club contact attribution and URL boundaries; synthetic HTML, no network."""
import importlib.util
from pathlib import Path
import socket
import unittest
from unittest.mock import patch
from urllib.request import Request


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "circle_contact_crawler_under_test", ROOT / "scripts" / "research_circle_contacts.py"
)
crawler = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(crawler)


def page_html(content, url="https://university.example/clubs/"):
    page = {"url": url, "status": "ok", "kind": "text/html; charset=utf-8",
            "body": content.encode("utf-8")}
    return page, crawler.parse_page(page)


def club(name="Blue Tennis Club", source="https://university.example/clubs/"):
    return {"circle_id": "club-1", "circle_name": name,
            "university_id": "university-1", "source_url": source}


@unittest.skipIf(crawler.dom is None, "lxml is required for the contact research runtime")
class CircleContactAttributionTests(unittest.TestCase):
    def contacts(self, content, name="Blue Tennis Club", peers=None):
        page, parsed = page_html(content)
        return crawler.extract_contacts(club(name), page, parsed, peers or [name])

    def test_shared_listing_keeps_each_clubs_email_in_its_own_row(self):
        content = """<html><body><main><table>
            <tr><th>Blue Tennis Club</th><td><a href="mailto:blue@clubs.example">メール</a></td></tr>
            <tr><th>Red Football Club</th><td><a href="mailto:red@clubs.example">メール</a></td></tr>
            </table></main></body></html>"""
        peers = ["Blue Tennis Club", "Red Football Club"]
        blue, _ = self.contacts(content, peers=peers)
        red, _ = self.contacts(content, "Red Football Club", peers)
        self.assertEqual([item["email"] for item in blue], ["blue@clubs.example"])
        self.assertEqual([item["email"] for item in red], ["red@clubs.example"])

    def test_shared_student_office_and_site_footer_are_not_club_contacts(self):
        found, _ = self.contacts("""<html><body><main>
            <ul><li>Blue Tennis Club</li><li>Red Football Club</li></ul>
            <section><h2>学生課のお問い合わせ</h2><p>student-office@university.example</p></section>
            </main><footer><a href="mailto:info@university.example">大学全体へのお問い合わせ</a></footer>
            </body></html>""", peers=["Blue Tennis Club", "Red Football Club"])
        self.assertEqual(found, [])

    def test_dedicated_profile_does_not_turn_student_office_into_club_contact(self):
        found, _ = self.contacts("""<html><body><main>
            <h1>Blue Tennis Club</h1><p>週2回活動しています。</p>
            <section><h2>大学・学生課へのお問い合わせ</h2>
            <a href="mailto:student-office@university.example">学生支援窓口</a></section>
            </main></body></html>""")
        self.assertEqual(found, [])

    def test_email_local_part_alone_does_not_prove_club_identity(self):
        found, _ = self.contacts("""<html><body><main><h1>University news</h1>
            <p>Contact: ABC@university.example</p></main></body></html>""", name="ABC")
        self.assertEqual(found, [])

    def test_shared_container_with_two_clubs_and_one_email_stays_unattributed(self):
        found, _ = self.contacts("""<html><body><main><section>
            <h2>Blue Tennis Club / Red Football Club</h2>
            <p>office@university.example</p></section></main></body></html>""",
            peers=["Blue Tennis Club", "Red Football Club"])
        self.assertEqual(found, [])

    def test_visible_obfuscated_email_in_named_card_is_decoded(self):
        found, _ = self.contacts("""<html><body><main><article>
            <h2>Blue Tennis Club</h2><p>団体への連絡： blue [at] clubs.example</p>
            </article></main></body></html>""")
        self.assertEqual([item["email"] for item in found], ["blue@clubs.example"])

    def test_script_and_template_addresses_are_not_contact_candidates(self):
        found, uncertain = self.contacts("""<html><body><main><h1>Blue Tennis Club</h1>
            <script>const contact = 'tracking@analytics.example';</script>
            <template>template@analytics.example</template><p>活動紹介</p></main></body></html>""")
        self.assertEqual(found, [])
        self.assertEqual(uncertain, [])


@unittest.skipIf(crawler.dom is None, "lxml is required for the contact research runtime")
class CircleContactDiscoveryTests(unittest.TestCase):
    def links(self, content, source="https://university.example/clubs/", dedicated=False):
        _, parsed = page_html(content, source)
        return crawler.next_links(club(source=source), parsed, source, dedicated)

    def test_shared_directory_follows_exact_club_link_only(self):
        links, forms = self.links("""<html><body><main><ul>
            <li><a href="/clubs/blue/">Blue Tennis Club</a></li>
            <li><a href="/clubs/red/">Red Football Club</a></li></ul></main></body></html>""")
        self.assertEqual(links, ["https://university.example/clubs/blue/"])
        self.assertEqual(forms, [])

    def test_named_club_card_can_link_its_external_official_website(self):
        links, forms = self.links("""<html><body><main>
            <article><h2>Blue Tennis Club</h2><a href="https://blue-club.example/">公式サイト</a></article>
            <article><h2>Red Football Club</h2><a href="https://red-club.example/">公式サイト</a></article>
            </main></body></html>""")
        self.assertEqual(links, ["https://blue-club.example/"])
        self.assertEqual(forms, [])

    def test_shared_directory_can_identify_a_club_specific_contact_form(self):
        links, forms = self.links("""<html><body><main>
            <article><h2>Blue Tennis Club</h2><a href="/clubs/blue/inquiry-form">団体へ問い合わせ</a></article>
            <article><h2>Red Football Club</h2><a href="/clubs/red/inquiry-form">団体へ問い合わせ</a></article>
            </main></body></html>""")
        self.assertIn("https://university.example/clubs/blue/inquiry-form", links)
        self.assertEqual(forms, ["https://university.example/clubs/blue/inquiry-form"])

    def test_dedicated_profile_ignores_sitewide_navigation_and_footer_contacts(self):
        links, forms = self.links("""<html><body>
            <header><nav><a href="/contact">お問い合わせ</a></nav></header>
            <main><h1>Blue Tennis Club</h1><p>毎週練習します。</p></main>
            <footer><a href="/support/form">大学へのお問い合わせ</a></footer></body></html>""",
            source="https://university.example/clubs/blue/", dedicated=True)
        self.assertEqual(forms, [])
        self.assertEqual(links, [])

    def test_club_profile_uses_own_contact_form(self):
        links, forms = self.links("""<html><body><main><article>
            <h1>Blue Tennis Club</h1><p><a href="/clubs/blue/inquiry-form">Blue Tennis Clubへ問い合わせ</a></p>
            </article></main></body></html>""",
            source="https://university.example/clubs/blue/", dedicated=True)
        self.assertIn("https://university.example/clubs/blue/inquiry-form", links)
        self.assertEqual(forms, ["https://university.example/clubs/blue/inquiry-form"])

    def test_related_same_name_club_does_not_replace_original_contact(self):
        _, parsed = page_html("""<html><head><title>Blue Tennis Club</title></head><body>
            <main><h1>Blue Tennis Club</h1><a href="/users/66088/conversations/new">問い合わせる</a></main>
            <aside class="related"><h2>おすすめ団体</h2><a href="/circles/10914">Blue Tennis Club</a>
            <a href="/users/10914/conversations/new">問い合わせる</a></aside></body></html>""",
            "https://circle-book.com/circles/66088")
        links, forms = crawler.next_links(
            club(source="https://circle-book.com/circles/66088"), parsed,
            "https://circle-book.com/circles/66088", True)
        self.assertNotIn("https://circle-book.com/circles/10914", links)
        self.assertNotIn("https://circle-book.com/users/10914/conversations/new", forms)
        self.assertNotIn("https://circle-book.com/users/66088/conversations/new", links)
        self.assertEqual(forms, [])

    def test_net_member_site_help_is_not_a_club_contact_form(self):
        links, forms = self.links("""<html><body>
            <nav><a href="/other/help.html">お問い合わせ</a></nav>
            <main><h1>Blue Tennis Club</h1><p>参加を募集しています。</p></main></body></html>""",
            source="https://www.net-menber.com/look/data/2651.html", dedicated=True)
        self.assertNotIn("https://www.net-menber.com/other/help.html", links)
        self.assertEqual(forms, [])


class CircleContactUrlBoundaryTests(unittest.TestCase):
    def test_nonpublic_urls_and_url_credentials_are_rejected(self):
        for url in ("http://127.0.0.1/admin", "http://10.0.0.1/", "http://[::1]/",
                    "http://169.254.169.254/latest/meta-data/", "http://localhost/",
                    "https://secrets.internal/", "https://user:pass@public.example/",
                    "file:///C:/private.txt", "https://public.example:8443/"):
            with self.subTest(url=url):
                self.assertEqual(crawler.safe_url(url), "")

    def test_dns_private_or_mixed_addresses_are_rejected(self):
        def answers(*addresses):
            return [(socket.AF_INET, socket.SOCK_STREAM, 6, "", (ip, 443)) for ip in addresses]

        for records in (answers("10.0.0.2"), answers("93.184.216.34", "127.0.0.1")):
            with self.subTest(records=records), patch.object(crawler.socket, "getaddrinfo", return_value=records):
                self.assertEqual(crawler.safe_url("https://club.example/", resolve=True), "")

    def test_redirect_to_private_ip_is_rejected_before_following(self):
        redirect = crawler.CheckedRedirect()
        with self.assertRaises(ValueError):
            redirect.redirect_request(Request("https://club.example/start"), None, 302, "Found", {},
                                      "http://127.0.0.1/admin")

    def test_redirect_to_public_name_resolving_private_is_rejected(self):
        records = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("192.168.1.5", 443))]
        with patch.object(crawler.socket, "getaddrinfo", return_value=records), self.assertRaises(ValueError):
            crawler.CheckedRedirect().redirect_request(Request("https://club.example/start"), None,
                                                      302, "Found", {}, "https://other.example/private")

    def test_safe_public_redirect_remains_followable(self):
        records = [(socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443))]
        with patch.object(crawler.socket, "getaddrinfo", return_value=records):
            result = crawler.CheckedRedirect().redirect_request(Request("https://club.example/start"), None,
                                                               302, "Found", {}, "https://other.example/contact")
        self.assertEqual(result.full_url, "https://other.example/contact")


if __name__ == "__main__":
    unittest.main()
