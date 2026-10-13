"""Club contact attribution and URL boundaries; synthetic HTML, no network."""
import importlib.util
from pathlib import Path
import socket
import tempfile
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
    def test_adjacent_ascii_headings_are_not_swallowed_as_email_local_part(self):
        found, _ = self.contacts('''<main><article><h2>Blue Tennis Club</h2></article>
            <article><h2>Red Football Club</h2><p>red@clubs.example</p></article></main>''',
            peers=['Blue Tennis Club','Red Football Club'])
        self.assertEqual(found, [])

    def test_another_article_is_a_boundary_even_for_an_unknown_club(self):
        found, _ = self.contacts('''<main><article><h2>Blue Tennis Club</h2></article>
            <article><h2>Unknown Other Club</h2><p>other@clubs.example</p></article></main>''')
        self.assertEqual(found, [])

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

    def test_unregistered_other_club_in_sibling_heading_cannot_supply_email(self):
        found, _ = self.contacts("""<html><body><main><h1>大学祭</h1><div class="editor">
            <h2>白金祭</h2><h4>11月1日</h4><p>運営：白金祭実行委員会</p>
            <p>お問い合わせ <a href="mailto:white@clubs.example">メール</a></p>
            <h2>戸塚まつり</h2><h4>5月23日</h4><p>運営：戸塚まつり準備会</p>
            <p>戸塚まつりに関するお問い合わせ <a href="mailto:totsuka@clubs.example">メール</a></p>
            </div></main></body></html>""", name="戸塚まつり準備会", peers=["戸塚まつり準備会"])
        self.assertEqual([item["email"] for item in found], ["totsuka@clubs.example"])
        self.assertNotIn("白金祭", found[0]["evidence"])

    def test_dedicated_h1_identifies_contact_section_after_long_activity_section(self):
        content = """<html><body><main><h1>Blue Tennis Club</h1><div>
            <h2>Activities</h2><p>""" + ("Weekly tennis practice. " * 100) + """</p>
            <h2>Contact</h2><!-- CMS editor comment --><p>Contact: blue@clubs.example</p>
            </div></main></body></html>"""
        found, _ = self.contacts(content)
        self.assertEqual([item["email"] for item in found], ["blue@clubs.example"])
        self.assertEqual(found[0]["attribution"], "club_page")
        self.assertNotIn("Weekly tennis practice", found[0]["evidence"])

    def test_dedicated_h1_does_not_override_office_heading_boundary(self):
        found, _ = self.contacts("""<html><body><main><h1>Blue Tennis Club</h1><div>
            <h2>Activities</h2><p>Every Saturday.</p>
            <h2>学生支援課へのお問い合わせ</h2><p>Contact: office@university.example</p>
            </div></main></body></html>""")
        self.assertEqual(found, [])

    def test_contact_subheading_inherits_only_its_enclosing_club_heading(self):
        found, _ = self.contacts("""<html><body><main><div>
            <h2>Unregistered Red Club</h2><h3>Contact</h3><p>red@clubs.example</p>
            <h2>Blue Tennis Club</h2><h3>Activities</h3><p>Weekly practice.</p>
            <h3>Contact</h3><p>blue@clubs.example</p>
            </div></main></body></html>""")
        self.assertEqual([item["email"] for item in found], ["blue@clubs.example"])
        self.assertNotIn("Unregistered Red Club", found[0]["evidence"])

    def test_dedicated_h1_identifies_direct_contact_text_before_first_subheading(self):
        found, _ = self.contacts("""<html><body><main><h1>Blue Tennis Club</h1><div>
            blue@clubs.example<h2>Activities</h2><p>Weekly practice.</p>
            <h2>History</h2><p>Founded last year.</p>
            </div></main></body></html>""")
        self.assertEqual([item["email"] for item in found], ["blue@clubs.example"])
        self.assertEqual(found[0]["attribution"], "club_page")

    def test_bounded_profile_title_can_identify_nested_lower_level_contact_headings(self):
        found, _ = self.contacts("""<html><body><main><div>
            <div><h4>Blue Tennis Club</h4></div><div><h5>Welcome</h5><p>Weekly practice.</p>
            <h5>Join us</h5><p>お問い合わせ blue@clubs.example</p></div>
            <h3>Photo album</h3><p>Club photos.</p><h3>Other information</h3>
            </div></main></body></html>""")
        self.assertEqual([item["email"] for item in found], ["blue@clubs.example"])

    def test_social_url_at_handle_is_not_an_email(self):
        found, uncertain = self.contacts("""<html><body><main><article>
            <h2>Blue Tennis Club</h2><p>https://www.tiktok.com/@blue.tennis</p>
            </article></main></body></html>""")
        self.assertEqual(found, [])
        self.assertEqual(uncertain, [])

    def test_visitor_question_email_is_excluded_but_club_answer_email_is_kept(self):
        page, parsed = page_html("""<html><body><main><dl>
            <dt>Visitor</dt><dd class="q_d">Please reply to visitor@personal.example</dd>
            <dt>回答：Blue Tennis Club</dt><dd class="a_d">Our club contact is blue@clubs.example</dd>
            </dl></main></body></html>""", "https://www.net-menber.com/look/data/123.html")
        found, uncertain = crawler.extract_contacts(club(), page, parsed, ["Blue Tennis Club"])
        self.assertEqual([item["email"] for item in found], ["blue@clubs.example"])
        self.assertNotIn("visitor@personal.example", uncertain)

    def test_long_club_description_email_is_contact_but_portal_mail_is_not(self):
        page, parsed = page_html('''<main><h1>サークル「Blue Tennis Club」のメンバー募集情報</h1>
            <table><tr><th>連絡事項やアピールポイント</th><td>''' + ('週末に活動しています。' * 160) +
            '''<p>参加希望は blue@clubs.example までメールでご連絡ください。</p>
            <p>サイトからの通知を受け取るため info@mail.net-menber.com を許可してください。</p>
            </td></tr></table><dd class="q_d">visitor@personal.example</dd></main>''',
            "https://www.net-menber.com/look/data/123.html")
        found, uncertain = crawler.extract_contacts(club(), page, parsed, ["Blue Tennis Club"])
        self.assertEqual([item['email'] for item in found], ['blue@clubs.example'])
        self.assertEqual(found[0]['attribution'], 'club_listing')
        self.assertNotIn('visitor@personal.example', uncertain)

    def test_long_listing_description_requires_exact_club_and_contact_intent(self):
        for heading, message in [
            ('Red Tennis Club', '参加希望は blue@clubs.example までメールでご連絡ください。'),
            ('Blue Tennis Club', 'SNSのサンプルは blue@clubs.example です。'),
        ]:
            with self.subTest(heading=heading):
                page, parsed = page_html('''<main><h1>サークル「''' + heading + '''」のメンバー募集情報</h1>
                    <table><tr><th>連絡事項やアピールポイント</th><td>''' + ('活動紹介。' * 250) +
                    message + '''</td></tr></table></main>''',
                    "https://www.net-menber.com/look/data/123.html")
                found, _ = crawler.extract_contacts(club(), page, parsed, ["Blue Tennis Club", "Red Tennis Club"])
                self.assertEqual(found, [])

    def test_dedicated_h1_cannot_identify_email_in_a_separate_content_region(self):
        found, _ = self.contacts("""<html><body><main><article><h1>Blue Tennis Club</h1>
            <p>Weekly practice.</p></article><article><h2>Other group</h2><p>Other group activity</p>
            <h2>Contact</h2><p>Contact: other@clubs.example</p></article></main></body></html>""")
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

    def test_html_comments_and_processing_instructions_are_not_contact_candidates(self):
        found, uncertain = self.contacts("""<html><body><main><h1>Blue Tennis Club</h1>
            <!-- Blue Tennis Club hidden@clubs.example -->
            <?legacy Blue Tennis Club instruction@clubs.example ?>
            <p>活動紹介</p></main></body></html>""")
        self.assertEqual(found, [])
        self.assertEqual(uncertain, [])


@unittest.skipIf(crawler.dom is None, "lxml is required for the contact research runtime")
class CircleContactDiscoveryTests(unittest.TestCase):
    def test_listing_homepage_field_is_bound_to_exact_club(self):
        links, _ = self.links('''<main><table>
            <tr><th>サークル名</th><td>Blue Tennis Club</td></tr>
            <tr><th>サークル<br>ホームページ</th><td><a href="https://blue.example/">https://blue.example/</a></td></tr>
            </table><table><tr><th>サークル名</th><td>Other Club</td></tr>
            <tr><th>サークルホームページ</th><td><a href="https://other.example/">https://other.example/</a></td></tr>
            </table></main>''', source='https://www.net-menber.com/look/data/2651.html')
        self.assertEqual(links, ['https://blue.example/'])

    def test_dedicated_club_contact_does_not_follow_university_global_contact(self):
        markup = '''<main><h1>Blue Tennis Club</h1><section><h2>参加</h2>
            <a href="/clubs/blue/contact">お問い合わせ</a><a href="/contact">お問い合わせ</a></section></main>'''
        links, _ = self.links(markup, source='https://university.example/clubs/blue/', dedicated=True)
        self.assertEqual(links, ['https://university.example/clubs/blue/contact'])

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


class CircleContactExportTests(unittest.TestCase):
    def fixtures(self, contacts):
        circles = [{"circle_id": circle_id, "university_name": "University " + circle_id,
                    "circle_name": "Club " + circle_id, "source_url": "https://clubs.example/" + circle_id}
                   for circle_id in contacts]
        results = {circle_id: {"circle_id": circle_id, "status": "email_found", "checked_at": "2026-10-11T00:00:00Z",
                              "note": "Public club contact checked", "contacts": entries}
                   for circle_id, entries in contacts.items()}
        return circles, results

    def contact(self, email="Shared@clubs.example", evidence="Club's official contact", source="https://clubs.example/contact"):
        return {"email": email, "evidence": evidence, "source_url": source, "attribution": "club_context"}

    def export(self, circles, results, **kwargs):
        with tempfile.TemporaryDirectory(dir=ROOT / 'work') as path:
            return crawler.export(Path(path), circles, results, **kwargs)

    def test_cli_default_keeps_shared_contact_guard_without_exceptions(self):
        circles, results = self.fixtures({"a": [self.contact()], "b": [self.contact()]})
        stats = self.export(circles, results)
        self.assertEqual(stats["statuses"], {"review_needed": 2})
        self.assertEqual([row["contacts"] for row in results.values()], [[], []])

    def test_verified_pair_does_not_allow_another_circle_or_another_email(self):
        circles, results = self.fixtures({
            "a": [self.contact(), self.contact("second@clubs.example")],
            "b": [self.contact(), self.contact("second@clubs.example")],
            "c": [self.contact()],
        })
        stats = self.export(circles, results, verified_shared_pairs={("a", "shared@clubs.example")})
        self.assertEqual([item["email"].casefold() for item in results["a"]["contacts"]], ["shared@clubs.example"])
        self.assertEqual(results["a"]["status"], "email_found")
        self.assertEqual(results["b"]["contacts"], [])
        self.assertEqual(results["c"]["contacts"], [])
        self.assertEqual(stats["statuses"], {"email_found": 1, "review_needed": 2})

    def test_verified_pairs_cannot_override_office_email_or_source_validation(self):
        circles, results = self.fixtures({
            "a": [self.contact(evidence="学生支援課の共通窓口")],
            "b": [self.contact("bad@@clubs.example")],
            "c": [self.contact("private@clubs.example", source="http://127.0.0.1/contact")],
            "d": [self.contact()],
        })
        approved = {(circle_id, item["email"].casefold())
                    for circle_id, row in results.items() for item in row["contacts"]}
        stats = self.export(circles, results, verified_shared_pairs=approved)
        for circle_id in ["a", "b", "c"]:
            self.assertEqual(results[circle_id]["contacts"], [])
            self.assertEqual(results[circle_id]["status"], "review_needed")
        self.assertEqual(len(results["d"]["contacts"]), 1)
        self.assertEqual(stats["statuses"], {"review_needed": 3, "email_found": 1})


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
