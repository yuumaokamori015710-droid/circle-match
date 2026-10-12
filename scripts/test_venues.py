"""Native venue directory checks using disposable SQLite and loopback HTTP only."""
from collections import Counter
import base64
from html.parser import HTMLParser
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import urlsplit, urlencode
from urllib.request import build_opener, HTTPRedirectHandler, Request
from xml.etree import ElementTree

from test_event_flow import load_app, user, create_account


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None


class PublicPage(HTMLParser):
    """Read the visible directory navigation and document metadata."""
    def __init__(self, page):
        super().__init__()
        self.tabs = []
        self.meta = {}
        self.canonicals = []
        self._in_tabs = False
        self._link = None
        self.feed(page)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == 'nav' and 'tabs' in attrs.get('class', '').split():
            self._in_tabs = True
        if tag == 'a' and self._in_tabs:
            self._link = {**attrs, 'text': ''}
        if tag == 'meta' and attrs.get('name'):
            self.meta[attrs['name']] = attrs.get('content', '')
        if tag == 'link' and attrs.get('rel') == 'canonical':
            self.canonicals.append(attrs.get('href', ''))

    def handle_data(self, data):
        if self._link is not None:
            self._link['text'] += data

    def handle_endtag(self, tag):
        if tag == 'a' and self._link is not None:
            self._link['text'] = self._link['text'].strip()
            self.tabs.append(self._link)
            self._link = None
        if tag == 'nav':
            self._in_tabs = False


class IsolatedAppHttpCase(unittest.TestCase):
    """Shared disposable app fixture; imports never start background workers."""
    @classmethod
    def setUpClass(cls):
        scratch = Path(__file__).resolve().parents[1] / 'work'
        scratch.mkdir(exist_ok=True)
        cls.temp = tempfile.TemporaryDirectory(dir=scratch)
        cls.addClassCleanup(cls.temp.cleanup)
        cls.database = Path(cls.temp.name) / 'venues.sqlite'
        cls.environment = patch.dict(os.environ, {
            'CIRCLEMATCH_DB_PATH': str(cls.database),
            'HOST': '127.0.0.1',
            'CIRCLEMATCH_SITE_BASE_URL': 'https://circle-match.jp',
            'CIRCLEMATCH_EMAIL_NOTIFICATIONS_ENABLED': 'false',
            'CIRCLEMATCH_EMAIL_AUTH_ENABLED': 'false',
            'CIRCLEMATCH_GOOGLE_CLIENT_ID': '',
            'CIRCLEMATCH_GOOGLE_CLIENT_SECRET': '',
            'CIRCLEMATCH_SUPABASE_URL': '',
            'CIRCLEMATCH_SUPABASE_ANON_KEY': '',
            'CIRCLEMATCH_RESEND_API_KEY': '',
            'CIRCLEMATCH_SESSION_SECRET': 'isolated-venue-tests-only',
        })
        cls.environment.start()
        cls.addClassCleanup(cls.environment.stop)
        cls.app = load_app(cls.database)
        cls.app.LOG_PATH = Path(cls.temp.name) / 'preview.log'
        cls.app.EMAIL_NOTIFICATIONS_ENABLED = False
        cls.app.ADSENSE_HEAD = ''
        outbound = patch.object(cls.app, 'urlopen', side_effect=AssertionError('External requests are forbidden in venue tests'))
        outbound.start()
        cls.addClassCleanup(outbound.stop)
        # Never call app.main(): it starts email and tweet-bot workers.
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), cls.app.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.addClassCleanup(cls.stop_server)
        cls.base = 'http://127.0.0.1:' + str(cls.server.server_port)
        cls.opener = build_opener(NoRedirect())

    @classmethod
    def stop_server(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join(timeout=3)

    def request(self, path, method='GET', cookie='', admin=False):
        headers = {'Accept': 'application/json'}
        if cookie:
            headers['Cookie'] = cookie
        if admin:
            value = (self.app.ADMIN_USERNAME + ':' + self.app.ADMIN_PASSWORD).encode('utf-8')
            headers['Authorization'] = 'Basic ' + base64.b64encode(value).decode('ascii')
        data = None
        if method == 'POST':
            # These calls only check method rejection. An unread request body
            # can race socket close on Windows before the 405 reaches the client.
            data = b''
            headers['Content-Type'] = 'application/json'
            headers['Origin'] = self.base
        req = Request(self.base + path, data=data, headers=headers, method=method)
        try:
            response = self.opener.open(req, timeout=10)
        except HTTPError as error:
            response = error
        with response:
            return response.status, response.read(), response.headers


class VenueIntegrationTests(IsolatedAppHttpCase):
    def catalog(self):
        status, body, headers = self.request('/api/tennis-courts')
        self.assertEqual(status, 200)
        self.assertEqual(headers.get_content_type(), 'application/json')
        return json.loads(body)

    def assert_tabs(self, page, current):
        parsed = PublicPage(page)
        self.assertEqual([item['text'] for item in parsed.tabs], ['大会・イベント', 'サークルDB', '会場予約'])
        active = [item['text'] for item in parsed.tabs
                  if 'active' in item.get('class', '').split() or item.get('aria-current') == 'page']
        self.assertEqual(active, [current])
        self.assertEqual(parsed.tabs[2]['href'], '/venues')
        for item in parsed.tabs:
            self.assertTrue(item['href'].startswith('/'))
            self.assertFalse(urlsplit(item['href']).netloc)
        return parsed

    def test_public_page_json_and_assets_work_without_database(self):
        paths = {'/venues': {'text/html'}, '/api/tennis-courts': {'application/json'}, '/api/venues': {'application/json'},
                 '/assets/venues/tennis.css': {'text/css'},
                 '/assets/venues/tennis.js': {'text/javascript', 'application/javascript'}}
        with patch.object(self.app, 'connect', side_effect=AssertionError('Public directory must not open SQLite')) as connect:
            for path, content_type in paths.items():
                with self.subTest(path=path):
                    status, body, headers = self.request(path)
                    self.assertEqual(status, 200)
                    self.assertIn(headers.get_content_type(), content_type)
                    self.assertTrue(body)
                    self.assertNotIn('Set-Cookie', headers)
            connect.assert_not_called()
        page = self.request('/venues')[1].decode('utf-8')
        self.assert_tabs(page, '会場予約')
        self.assertNotIn('<iframe', page.lower())
        self.assertNotIn('circlematch-acquisition.onrender.com', page)
        self.assertNotIn('予約管理を開く', page)
        self.assertRegex(page, r'href="/assets/venues/tennis\.css\?v=[0-9a-f]{12}"')
        self.assertRegex(page, r'src="/assets/venues/tennis\.js\?v=[0-9a-f]{12}"')

    def test_public_catalog_keeps_all_curated_facilities_and_evidence(self):
        data = self.catalog()
        courts = data['courts']
        self.assertEqual(len(courts), 404)
        self.assertEqual(data['meta']['total'], len(courts))
        self.assertEqual(len({court['id'] for court in courts}), len(courts))
        self.assertEqual(Counter(court['operator_type'] for court in courts), {'PUBLIC': 361, 'PRIVATE': 43})
        self.assertEqual(len({court['municipality'] for court in courts}), 58)
        public_fields = {'id', 'name', 'operator', 'municipality', 'area', 'address', 'price_unit',
                         'price_note', 'booking_method', 'booking_note', 'booking_url', 'official_url',
                         'checked_at', 'operator_type', 'courts_count', 'surface', 'indoor',
                         'night_lighting', 'price_from', 'sources', 'availability_status',
                         'facility_kind', 'availability_note', 'price_per_hour'}
        for court in courts:
            with self.subTest(court=court['id']):
                self.assertLessEqual(set(court), public_fields)
                self.assertTrue(court['name'])
                self.assertTrue(court['checked_at'])
                self.assertTrue(court['sources'])
                for source in court['sources']:
                    self.assertEqual(set(source), {'title', 'url'})
                    self.assertTrue(source['title'])
                for url in [court['official_url'], court['booking_url'], *(s['url'] for s in court['sources'])]:
                    parsed = urlsplit(url)
                    self.assertIn(parsed.scheme, {'http', 'https'})
                    self.assertTrue(parsed.hostname)
                    self.assertIsNone(parsed.username)
                    self.assertIsNone(parsed.password)

    def test_all_sports_have_verified_booking_routes_and_legacy_tennis_is_unchanged(self):
        status, body, _ = self.request('/api/venues')
        self.assertEqual(status, 200)
        catalog = json.loads(body)
        self.assertGreaterEqual(catalog['meta']['sports']['サッカー・フットサル'], 15)
        self.assertGreaterEqual(catalog['meta']['sports']['テニス'], 404)
        self.assertEqual(set(catalog['meta']['sports']), set(self.app.venues.SPORTS))
        for sport in self.app.venues.SPORTS:
            with self.subTest(sport=sport):
                query = urlencode({'sport': sport, 'prefecture': '東京都'})
                status, data, _ = self.request('/api/venues?' + query)
                rows = json.loads(data)['courts']
                self.assertTrue(rows)
                self.assertTrue(all(sport in row['sports'] and row['booking_url'] and row['sources'] for row in rows))
                html = self.request('/venues?' + query)[1].decode()
                self.assertIn('class="venue-court-card"', html)
                self.assertIn('この会場で募集を作る', html)
                self.assertNotIn('__VENUE_', html)
                self.assertTrue(PublicPage(html).meta['robots'].startswith('index, follow'))
                self.assertNotIn('JavaScriptを有効', html)

    def test_expansion_preserves_original_records_and_exceeds_one_thousand(self):
        status, body, _ = self.request('/api/venues')
        self.assertEqual(status, 200)
        catalog = json.loads(body)
        rows = catalog['courts']
        self.assertGreaterEqual(len(rows), 1000)
        self.assertEqual(catalog['meta']['total'], len(rows))
        self.assertEqual(len({row['id'] for row in rows}), len(rows))
        by_id = {row['id']: row for row in rows}
        for original in self.catalog()['courts']:
            for field, value in original.items():
                self.assertEqual(by_id[original['id']][field], value)
        new = [row for row in rows if row['id'].startswith('tokyo-venue-')]
        self.assertGreaterEqual(len(new), 550)
        for row in new:
            self.assertEqual(row['checked_at'], '2026-10-12')
            self.assertEqual(row['availability_status'], 'UNKNOWN')
            self.assertTrue(row['sources'])
            self.assertTrue(row['booking_url'])
            self.assertTrue(row['address'].startswith('東京都'))
            self.assertIn(row['municipality'], row['address'])
        self.assertGreaterEqual(catalog['meta']['sports']['サッカー・フットサル'], 100)

    def test_no_javascript_expansion_pagination_keeps_filters_and_next_page(self):
        query = {'sport': 'サッカー・フットサル', 'prefecture': '東京都'}
        first = self.request('/venues?' + urlencode(query))[1].decode()
        second = self.request('/venues?' + urlencode({**query, 'v_page': 2}))[1].decode()
        self.assertEqual(first.count('class="venue-court-card"'), 50)
        self.assertIn('class="venue-court-card"', second)
        self.assertNotEqual(first, second)
        self.assertIn('v_page=2', first)
        self.assertIn('sport=', second)

    def test_server_filters_and_escaped_input_keep_booking_links_in_initial_html(self):
        rows = json.loads(self.request('/api/venues?' + urlencode({'sport': 'サッカー・フットサル'}))[1])['courts']
        first = rows[0]
        html = self.request('/venues?' + urlencode({'sport': 'サッカー・フットサル', 'v_q': first['name']}))[1].decode()
        self.assertIn(first['name'], html)
        self.assertIn('class="venue-court-card"', html)
        self.assertIn('method="get"', html)
        empty = self.request('/venues?' + urlencode({'sport': 'サッカー・フットサル', 'q': '<script>unmatched</script>'}))[1].decode()
        self.assertNotIn('<script>unmatched</script>', empty)
        self.assertNotIn('class="venue-court-card"', empty)
        raw = self.request('/venues?' + urlencode({'sport': 'サッカー・フットサル', 'q': first['name']}))[1].decode()
        self.assertIn('class="venue-court-card"', raw)

    def test_catalog_failure_is_not_a_false_zero(self):
        with patch.object(self.app.venues, 'get_venue_catalog', side_effect=OSError('test read error')):
            status, body, _ = self.request('/venues')
        self.assertEqual(status, 200)
        self.assertIn('会場データを取得できませんでした', body.decode())
        self.assertNotIn('掲載 0', body.decode())

    def test_venue_prefill_requires_a_published_catalog_id_and_survives_login(self):
        row = json.loads(self.request('/api/venues?' + urlencode({'sport': 'サッカー・フットサル'}))[1])['courts'][0]
        defaults = self.app.venues.venue_defaults(row['id'], 'サッカー・フットサル')
        self.assertIn(row['name'], defaults['location'])
        self.assertEqual(defaults['prefecture'], '東京都')
        self.assertEqual(defaults['sport_category'], 'サッカー・フットサル')
        self.assertEqual(self.app.venues.venue_defaults('unlisted-private-venue'), {})
        path = '/events/new?' + urlencode({'venue': row['id'], 'sport': 'サッカー・フットサル'})
        status, _, headers = self.request(path)
        self.assertIn(status, {302, 303})
        self.assertIn('venue', headers['Location'])
        account = user('venue-prefill-host', 'prefill@example.test', '会場主催者')
        create_account(self.app, account)
        form = self.app.render_event_form_html({'venue': [row['id']], 'sport': ['サッカー・フットサル']}, account)
        self.assertIn(row['name'], form.decode() if isinstance(form, bytes) else form)

    def test_catalog_prices_keep_original_units_free_and_unknown_values(self):
        courts = {court['id']: court for court in self.catalog()['courts']}
        self.assertEqual(courts['metro-hibiya']['price_from'], 1300)
        self.assertEqual(courts['metro-hibiya']['price_per_hour'], 1300)
        self.assertEqual(courts['koganei-municipal']['price_from'], 1600)
        self.assertEqual(courts['koganei-municipal']['price_unit'], '1面2時間')
        self.assertEqual(courts['koganei-municipal']['price_per_hour'], 800)
        self.assertEqual(courts['okutama-kawai']['price_from'], 0)
        self.assertEqual(courts['okutama-kawai']['price_per_hour'], 0)
        self.assertIsNone(courts['inagi-kitamidori']['price_from'])
        self.assertIsNone(courts['inagi-kitamidori']['price_per_hour'])
        self.assertEqual(courts['taito-ryuhoku']['availability_status'], 'SUSPENDED')
        self.assertTrue(courts['taito-ryuhoku']['availability_note'])

    def test_aliases_redirect_to_the_native_directory(self):
        with patch.object(self.app, 'connect', side_effect=AssertionError('Redirect must not open SQLite')) as connect:
            for path in ('/?tab=venues', '/venues/', '/tennis'):
                with self.subTest(path=path):
                    status, _, headers = self.request(path)
                    self.assertIn(status, {301, 302, 303, 307, 308})
                    self.assertEqual(headers['Location'], '/venues')
            connect.assert_not_called()

    def test_public_paths_reject_posts_and_asset_traversal_without_persistence(self):
        before = self.database.read_bytes()
        with patch.object(self.app, 'connect', side_effect=AssertionError('Public directory must not write SQLite')) as connect:
            for admin in (False, True):
                for path in ('/venues', '/api/tennis-courts', '/api/venues', '/assets/venues/tennis.js', '/assets/venues/tennis.css'):
                    with self.subTest(method='POST', path=path, admin=admin):
                        status, _, headers = self.request(path, method='POST', admin=admin)
                        self.assertEqual(status, 405)
                        self.assertEqual(headers['Allow'], 'GET')
            for path in ('/assets/venues/../circlematch_db_app.py',
                         '/assets/venues/%2e%2e/circlematch_db_app.py',
                         '/assets/venues/../../.git/config',
                         '/assets/venues/tokyo_tennis.json',
                         '/assets/venues/tennis.js/extra'):
                with self.subTest(method='GET', path=path):
                    status, body, _ = self.request(path)
                    self.assertEqual(status, 404)
                    self.assertNotIn(b'CIRCLEMATCH_ADMIN_PASSWORD', body)
            connect.assert_not_called()
        self.assertEqual(self.database.read_bytes(), before)

    def test_public_directory_does_not_weaken_existing_admin_authentication(self):
        with patch.object(self.app, 'connect', side_effect=AssertionError('Denied admin requests must not open SQLite')) as connect:
            for path in ('/admin', '/api/audit_logs'):
                with self.subTest(path=path):
                    status, _, headers = self.request(path)
                    self.assertEqual(status, 401)
                    self.assertIn('Basic', headers['WWW-Authenticate'])
            connect.assert_not_called()

    def test_existing_event_and_circle_pages_expose_three_body_tabs(self):
        for path, current in (('/?tab=events', '大会・イベント'), ('/events', '大会・イベント'),
                              ('/?tab=db&audience=university', 'サークルDB'),
                              ('/?tab=db&audience=social', 'サークルDB'), ('/venues', '会場予約')):
            with self.subTest(path=path):
                status, body, _ = self.request(path)
                self.assertEqual(status, 200)
                self.assert_tabs(body.decode('utf-8'), current)

    def test_native_page_preserves_existing_account_navigation(self):
        account = user('venue-host', 'venue-host@example.test', '会場テスト主催者')
        create_account(self.app, account)
        with self.app.connect() as conn:
            session = self.app.create_user_session(conn, account['user_id'])
        status, body, _ = self.request('/venues', cookie='cm_session=' + session)
        self.assertEqual(status, 200)
        header = body.decode('utf-8').split('</header>', 1)[0]
        self.assertIn('href="/mypage">マイページ</a>', header)
        self.assertIn('action="/logout" method="post"', header)
        self.assertNotIn(account['email'], header)
        anonymous = self.request('/venues')[1].decode('utf-8').split('</header>', 1)[0]
        self.assertIn('>ログイン</a>', anonymous)

    def test_native_directory_seo_is_canonical_and_in_sitemap(self):
        status, body, _ = self.request('/venues')
        self.assertEqual(status, 200)
        parsed = PublicPage(body.decode('utf-8'))
        self.assertEqual(parsed.canonicals, ['https://circle-match.jp/venues'])
        self.assertTrue(parsed.meta['robots'].startswith('index, follow'))
        self.assertIn('テニス', parsed.meta['description'])
        filtered = PublicPage(self.request('/venues?q=test')[1].decode('utf-8'))
        self.assertEqual(filtered.meta['robots'], 'noindex, follow')
        self.assertEqual(filtered.canonicals, ['https://circle-match.jp/venues'])
        status, body, _ = self.request('/sitemap.xml')
        self.assertEqual(status, 200)
        sitemap = ElementTree.fromstring(body)
        urls = [node.text for node in sitemap.iter('{http://www.sitemaps.org/schemas/sitemap/0.9}loc')]
        self.assertEqual(urls.count('https://circle-match.jp/venues'), 1)
        self.assertNotIn('https://circle-match.jp/?tab=venues', urls)


if __name__ == '__main__':
    unittest.main(verbosity=2)
