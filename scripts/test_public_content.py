"""Public content and ad eligibility contracts; disposable DB, no ad requests."""
from html.parser import HTMLParser
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlencode, urlsplit

from test_event_flow import create_account, event_payload, user
from test_venues import IsolatedAppHttpCase


class Links(HTMLParser):
    def __init__(self, page):
        super().__init__()
        self.urls = []
        self.feed(page)

    def handle_starttag(self, tag, attrs):
        if tag == 'a':
            self.urls.append(dict(attrs).get('href', ''))


class PublicContentTests(IsolatedAppHttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.app.init_db()
        cls.host = user('content-host', 'private-content@example.test', 'Content host')
        create_account(cls.app, cls.host)
        cls.app.ADSENSE_HEAD = '<script src="https://ads.example.test/adsbygoogle.js"></script>'

    def test_common_footer_connects_core_pages_and_policies(self):
        for path in ['/', '/events', '/venues', '/?tab=db', '/guides', '/privacy', '/signin']:
            with self.subTest(path=path):
                status, raw, _ = self.request(path)
                self.assertEqual(status, 200)
                page = raw.decode()
                self.assertEqual(page.count('id="cm-public-footer"'), 1)
                for link in ['/guides', '/operator', '/privacy', '/terms', '/about-data', '/contact']:
                    self.assertIn(link, Links(page).urls)
                self.assertNotIn(self.host['email'], page)

    def test_home_promotes_useful_editorial_content_without_fake_events(self):
        page = self.request('/')[1].decode()
        self.assertIn('/guides/tokyo-venue-costs', Links(page).urls)
        self.assertIn('/guides/practice-match-how-to', Links(page).urls)
        self.assertIn('会場選び・活動ガイド', page)

    def test_empty_events_offer_contextual_alternatives_without_ads(self):
        page = self.request('/events?' + urlencode({'sport': 'テニス', 'prefecture': '東京都'}))[1].decode()
        self.assertIn('0件を表示', page)
        self.assertIn('この競技の会場を探す', page)
        links = Links(page).urls
        self.assertTrue(any(url.startswith('/venues?') and 'sport=' in url for url in links))
        self.assertTrue(any('tab=db' in url and 'sport=' in url for url in links))
        self.assertNotIn('adsbygoogle.js', page)

    def test_ad_loader_is_absent_on_operations_legal_directories_and_errors(self):
        for path in ['/signin', '/settings', '/privacy', '/terms', '/contact', '/operator', '/venues', '/events',
                     '/?tab=db', '/circles', '/social/circles', '/guides/adsense-site-policy',
                     '/guides/not-an-article', '/events/not-an-event']:
            with self.subTest(path=path):
                page = self.request(path)[1].decode()
                self.assertNotIn('adsbygoogle.js', page)
        status, raw, _ = self.request('/admin', admin=True)
        self.assertEqual(status, 200)
        self.assertNotIn('cm-public-footer', raw.decode())
        self.assertNotIn('adsbygoogle.js', raw.decode())

    def test_meaningful_public_pages_remain_ad_eligible(self):
        for path in ['/', '/guides/practice-match-how-to', '/guides/tokyo-venue-costs']:
            with self.subTest(path=path):
                page = self.request(path)[1].decode()
                self.assertEqual(page.count('adsbygoogle.js'), 1)

    def test_noindex_and_catalog_failure_are_ad_free(self):
        page = self.request('/venues?' + urlencode({'sport': 'テニス', 'v_q': 'no-such-venue-999'}))[1].decode()
        self.assertNotIn('adsbygoogle.js', page)
        with patch.object(self.app.venues, 'get_venue_catalog', side_effect=OSError('fixture')):
            page = self.request('/venues')[1].decode()
        self.assertNotIn('adsbygoogle.js', page)
        with patch.object(self.app, 'latest_home_events', side_effect=OSError('fixture')):
            page = self.request('/')[1].decode()
        self.assertNotIn('adsbygoogle.js', page)

    def test_public_event_stays_eligible_and_prices_do_not_change(self):
        payload = event_payload('Content test cup')
        payload.update(participation_type='both', fee_amount='2500',
                       individual_fee_amount='2500', team_fee_amount='15000')
        with self.app.connect() as conn:
            eid = self.app.save_event_post(conn, payload, self.host)
        page = self.request('/events/' + eid)[1].decode()
        self.assertEqual(page.count('adsbygoogle.js'), 1)
        self.assertIn('2,500', page)
        self.assertIn('15,000', page)
        self.assertNotIn('adsbygoogle.js', self.request('/events/' + eid + '/apply')[1].decode())

    def test_guides_have_specific_steps_examples_and_revision_metadata(self):
        for slug, terms in {
            'practice-match-how-to': ['6,000', '雨天', '準備', '例示'],
            'recruiting-template': ['返信期限', '参加費', 'テンプレート'],
            'circle-database-guide': ['掲載元の確認日', '活動日', '公認を保証'],
        }.items():
            page = self.request('/guides/' + slug)[1].decode()
            self.assertIn('2026-11-04', page)
            self.assertIn('Circle Match編集', page)
            self.assertIn('class="cm-article"', page)
            for term in terms:
                self.assertIn(term, page)

    def test_comparison_uses_live_catalog_units_sources_and_conditions(self):
        page = self.request('/guides/tokyo-venue-costs')[1].decode()
        self.assertIn('猿江恩賜公園', page)
        self.assertIn('新宿コズミック', page)
        self.assertIn('1面1時間', page)
        self.assertIn('1面2時間', page)
        self.assertIn('大体育室半面・3時間', page)
        self.assertIn('照明', page)
        self.assertIn('条件付きの最安値', page)
        self.assertIn('https://www.tokyo-park.or.jp/park/sports/index.html', Links(page).urls)
        self.assertIn('https://bonfim.co.jp/ochiai/court_price/', Links(page).urls)
        self.assertIn('料金確認日', page)
        self.assertIn('未確認', page)
        self.assertNotRegex(page, r'(?<![\d,])0円')
        with patch.object(self.app.venues, 'get_venue_catalog', side_effect=OSError('fixture')):
            raw = self.request('/guides/tokyo-venue-costs')[1].decode()
        self.assertIn('比較データを取得できませんでした', raw)
        self.assertNotIn('adsbygoogle.js', raw)

    def test_unverified_records_show_provenance_not_invented_activity(self):
        rows = [{'circle_name': '<test>', 'source_type': 'university_official',
                 'verification_status': 'unverified', 'last_checked_at': '2026-10-20',
                 'source_url': 'https://example.test/club'}]
        page = self.app.render_db_rows(rows)
        self.assertIn('大学公式掲載情報', page)
        self.assertIn('掲載元の確認日', page)
        self.assertIn('2026-10-20', page)
        self.assertIn('活動日・会費・募集中かは掲載元で確認', page)
        self.assertIn('&lt;test&gt;', page)
        self.assertNotIn('<test>', page)
        self.assertNotIn('公認サークル', page)

    def test_sitemap_contains_new_comparison(self):
        page = self.request('/sitemap.xml')[1].decode()
        self.assertIn('/guides/tokyo-venue-costs', page)

    def test_comparison_counts_only_available_examples_and_is_explicit_on_failure(self):
        rows = self.app.venues.get_venue_catalog()['courts']
        selected = next(row for row in rows if row['id'] == 'metro-sarue')
        page = self.app.public_content.comparison({'courts': [selected]})
        self.assertIn('見比べる1施設', page)
        hidden = dict(selected, availability_status='SUSPENDED')
        page = self.app.public_content.comparison({'courts': [hidden]})
        self.assertIn('取得できませんでした', page)
        self.assertNotIn('猿江恩賜公園', page)

    def test_footer_preserves_cr_and_unicode_line_separators(self):
        for text in ['before\rafter', 'before\u2028after', 'before\r\nafter']:
            with self.subTest(text=repr(text)):
                page = '<html><head></head><body><main>' + text + '</main><footer>Old</footer><script>const tail=1;</script></body></html>'
                result = self.app.public_content.decorate(page, '/circles').decode()
                self.assertIn('<main>' + text + '</main>', result)
                self.assertIn('<script>const tail=1;</script>', result)
                self.assertEqual(result.count('<footer'), 1)
                self.assertEqual(result.count('</footer>'), 1)

    def test_football_empty_venue_alternative_uses_catalog_category(self):
        for sport in ['サッカー', 'フットサル']:
            page = self.app.public_content.empty_options({'sport': [sport], 'prefecture': ['東京都']})
            links = Links(page).urls
            venue = next(url for url in links if url.startswith('/venues'))
            self.assertEqual(parse_qs(urlsplit(venue).query)['sport'], ['サッカー・フットサル'])
            circle = next(url for url in links if url.startswith('/?'))
            self.assertEqual(parse_qs(urlsplit(circle).query)['sport'], [sport])
            target = self.app.directory_url({'sport': [sport]}, 'venues')
            self.assertEqual(parse_qs(urlsplit(target).query)['sport'], ['サッカー・フットサル'])
            page = self.request('/events?' + urlencode({'sport': sport}))[1].decode()
            nav = page[page.index('<nav class="club-bottom-nav"'):]
            venue = next(url for url in Links(nav).urls if url.startswith('/venues'))
            self.assertEqual(parse_qs(urlsplit(venue).query)['sport'], ['サッカー・フットサル'])

    def test_comparison_keeps_known_booking_and_registration_notes(self):
        page = self.request('/guides/tokyo-venue-costs')[1].decode()
        self.assertIn('初回は窓口で団体登録', page)
        self.assertIn('利用条件', page)
        self.assertNotIn('登録条件は未確認', page)

    def test_detailed_directory_renderers_include_shared_provenance(self):
        row = {'circle_name': 'Example', 'source_type': 'university_official',
               'last_checked_at': '2026-10-20', 'source_url': 'https://example.test/club'}
        for render in [self.app.ssr_circle_rows, self.app.ssr_social_circle_rows]:
            page = render([row])
            self.assertIn('大学公式掲載情報', page)
            self.assertIn('掲載元の確認日：2026-10-20', page)
        for template in [self.app.PUBLIC_HTML, self.app.SOCIAL_HTML]:
            self.assertIn('${sourceNote(c)}', template)
        for path in ['/circles', '/social/circles']:
            page = self.request(path)[1].decode()
            self.assertEqual(page.count('function sourceNote(c)'), 1)


if __name__ == '__main__':
    unittest.main(verbosity=2)
