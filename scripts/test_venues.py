"""Native venue directory checks using disposable SQLite and loopback HTTP only."""
from collections import Counter
import base64
import importlib
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
        self.assertEqual([item['text'] for item in parsed.tabs], ['大会・イベント', '会場予約', 'サークルDB'])
        active = [item['text'] for item in parsed.tabs
                  if 'active' in item.get('class', '').split() or item.get('aria-current') == 'page']
        self.assertEqual(active, [current])
        self.assertEqual(parsed.tabs[1]['href'], '/venues')
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

    def test_registration_guides_link_all_wards_and_metropolitan_courts(self):
        page = self.request('/venues?sport=%E3%83%86%E3%83%8B%E3%82%B9')[1].decode('utf-8')
        guides = self.app.venues.REGISTRATION_GUIDES
        self.assertEqual(len(guides), 24)
        self.assertEqual(len({name for name, _, _ in guides}), 24)
        self.assertEqual(page.count('class="venue-registration-guide-link"'), 24)
        for name, url, note in guides:
            with self.subTest(name=name):
                self.assertIn(name, page)
                self.assertIn(note, page)
                self.assertIn('href="' + url + '"', page)
                self.assertEqual(urlsplit(url).scheme, 'https')
        self.assertIn('窓口予約の例外', page)
        self.assertNotIn('__VENUE_REGISTRATION_GUIDES__', page)

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
                         'night_lighting', 'price_from', 'price_to', 'sources', 'availability_status',
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
            if row['id'] == 'tokyo-venue-6b06aed3958d':
                self.assertEqual(row['checked_at'], '2026-10-17')
                self.assertEqual(row['availability_status'], 'SUSPENDED')
                self.assertIn('2027年5月', row['availability_note'])
                self.assertIn('https://www.city.fussa.tokyo.jp/education/sports/1002683.html',
                              [source['url'] for source in row['sources']])
            elif row['id'] == 'tokyo-venue-ecb55dd79d92':
                self.assertEqual(row['checked_at'], '2026-10-18')
                self.assertEqual(row['availability_status'], 'SUSPENDED')
                self.assertIn('2027年3月末', row['availability_note'])
                self.assertIn('https://www.regasu-shinjuku.or.jp/?p=657',
                              [source['url'] for source in row['sources']])
            elif row['id'] == 'tokyo-venue-d7b168f67c73':
                self.assertEqual(row['checked_at'], '2026-10-19')
                self.assertEqual(row['availability_status'], 'SUSPENDED')
                self.assertIn('2027年3月末', row['availability_note'])
                self.assertIn('https://www.city.kodaira.tokyo.jp/kurashi/001/001348.html',
                              [source['url'] for source in row['sources']])
            elif row['id'] == 'tokyo-venue-ec7d0ac023ca':
                self.assertEqual(row['checked_at'], '2026-10-23')
                self.assertEqual(row['availability_status'], 'SUSPENDED')
                self.assertIn('2026年3月31日', row['availability_note'])
            elif row['id'] == 'tokyo-venue-a2d6191898f8':
                self.assertEqual(row['checked_at'], '2026-10-23')
                self.assertEqual(row['availability_status'], 'UNKNOWN')
                self.assertIn('第一体育室', row['booking_note'])
            else:
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

    def test_indoor_sports_expansion_has_evidence_and_usable_filters(self):
        status, body, _ = self.request('/api/venues')
        self.assertEqual(status, 200)
        catalog = json.loads(body)
        additions = [row for row in catalog['courts'] if row['id'].startswith('tokyo-gym-')]
        self.assertGreaterEqual(len(additions), 80)
        supported = {'バスケットボール', 'バレーボール', 'バドミントン', '卓球'}
        for row in additions:
            with self.subTest(venue=row['id']):
                self.assertTrue(row['indoor'])
                self.assertEqual(row['facility_label'], '体育館・体育室')
                self.assertTrue(set(row['sports']) <= supported)
                self.assertTrue(row['sources'])
                self.assertIn(row['municipality'], row['address'])
                if row['price_from'] is not None:
                    self.assertGreaterEqual(row['price_to'], row['price_from'])
                    self.assertTrue(any('公式料金表' in s['title'] for s in row['sources']))
                self.assertIn(row['availability_status'], {'UNKNOWN', 'SUSPENDED'})
                if row['availability_status'] == 'SUSPENDED':
                    self.assertTrue(row['availability_note'])
        for sport in supported:
            with self.subTest(sport=sport):
                self.assertGreaterEqual(catalog['meta']['sports'][sport], 130)
                query = urlencode({'sport': sport, 'v_indoor': 1, 'v_q': '新宿コズミック'})
                status, body, _ = self.request('/venues?' + query)
                self.assertEqual(status, 200)
                self.assertIn('新宿コズミックスポーツセンター', body.decode('utf-8'))
                self.assertIn('class="venue-court-card"', body.decode('utf-8'))

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

    def test_price_ranges_are_validated_without_changing_legacy_payloads(self):
        module = importlib.import_module(self.app.venues.get_catalog.__module__)
        original = next(r for r in self.catalog()['courts'] if r['id'] == 'metro-hibiya')
        self.assertNotIn('price_to', module.validate_catalog([original])[0])
        for minimum, maximum in ((None, 1), (1300, 1299), (1300, True),
                                 (1300, float('nan')), (1300, float('inf')), (1300, '1500')):
            with self.subTest(minimum=minimum, maximum=maximum), self.assertRaises(ValueError):
                module.validate_catalog([{**original, 'price_from': minimum, 'price_to': maximum}])
        variable = module.validate_catalog([{**original, 'price_to': 2000}])[0]
        self.assertEqual(variable['price_to'], 2000)
        self.assertIsNone(variable['price_per_hour'])
        fixed = module.validate_catalog([{**original, 'price_to': 1300}])[0]
        self.assertEqual(fixed['price_per_hour'], 1300)
        for unit in ('1人30分', '1室1時間', '体育館貸切2時間'):
            row = module.validate_catalog([{**original, 'price_unit': unit, 'price_to': 1300}])[0]
            self.assertIsNone(row['price_per_hour'])

    def test_reviewed_fees_have_source_units_and_no_hourly_range_misrepresentation(self):
        rows = {r['id']: r for r in json.loads(self.request('/api/venues')[1])['courts']}
        audit_path = Path(__file__).resolve().parents[1] / 'docs' / 'venue-fee-review-2026-10-12.json'
        changes = json.loads(audit_path.read_text(encoding='utf-8'))
        self.assertGreaterEqual(len(changes), 300)
        self.assertEqual(len(changes), len({r['id'] for r in changes}))
        for change in changes:
            with self.subTest(venue=change['id']):
                row = rows[change['id']]
                for field in ('name', 'price_from', 'price_to', 'price_unit', 'price_note', 'checked_at'):
                    self.assertEqual(row[field], change[field])
                self.assertTrue(change['evidence'])
                self.assertIn(change['source'], [s['url'] for s in row['sources'] if '公式料金表' in s['title']])
                if row['price_from'] != row['price_to']:
                    self.assertIsNone(row['price_per_hour'])
        query = urlencode({'q': 'Bonfim Football Park 落合南長崎', 'price_max': 100000})
        self.assertNotIn('class="venue-court-card"', self.request('/venues?' + query)[1].decode())

    def test_initial_html_displays_reviewed_ranges_units_sources_free_and_unknown(self):
        html = self.request('/venues?' + urlencode({'q': '高円寺みんなの体育館'}))[1].decode()
        self.assertIn('>1,500円</td>', html)
        self.assertIn('>1,500円〜6,000円</span>', html)
        self.assertNotIn('<small>〜</small>', html)
        self.assertIn('条件別料金', html)
        self.assertIn('半面', html)
        self.assertIn('体育館貸切2時間', html)
        self.assertIn('class="venue-fee-link"', html)
        self.assertNotIn('料金は要確認', html)
        rows = json.loads(self.request('/api/venues')[1])['courts']
        free = next(r for r in rows if r['id'] == 'okutama-kawai')
        card = self.app.venues._card({**free, 'price_to': 0}, 0, 'テニス')
        self.assertIn('>0円</span>', card)
        self.assertNotIn('料金は要確認', card)
        unknown = self.request('/venues?' + urlencode({'q': '千歳テニスクラブ'}))[1].decode()
        self.assertIn('金額未取得', unknown)

    def test_map_drilldown_is_ssr_and_preserves_conditions(self):
        from bs4 import BeautifulSoup
        query = {'sport': 'サッカー・フットサル', 'v_q': '公園', 'v_booking_channel': 'web'}
        for stage, destination, area in [('japan','関東',''),('kanto','東京都',''),('tokyo','23区','23区'),('wards','新宿区','23区')]:
            params = {**query,'v_map':stage}
            if stage == 'wards':
                params['v_area'] = '23区'
            page = self.request('/venues?' + urlencode(params))[1].decode()
            soup = BeautifulSoup(page,'html.parser')
            panel = soup.select_one('.venue-region-panel')
            self.assertEqual(panel['data-stage'],stage)
            self.assertGreater(len(panel.select('svg path')),0)
            if stage == 'japan':
                link = panel.select_one('.venue-map-choice[href]')
            elif stage in {'kanto','tokyo'}:
                link = panel.select_one(f'.venue-map-zoom[aria-label="{destination}を詳しく選ぶ"]')
            else:
                link = panel.select_one(f'.venue-map-shape[data-place="{destination}"]')
            from urllib.parse import parse_qs
            target = parse_qs(urlsplit(link['href']).query)
            self.assertEqual(target['sport'],[query['sport']])
            self.assertEqual(target['v_q'],['公園'])
            self.assertEqual(target['v_booking_channel'],['web'])
            if stage == 'wards':
                self.assertEqual(target['v_places'],['新宿区'])
            self.assertNotIn('v_area',target)
        self.assertIn('掲載準備中', self.request('/venues?v_map=japan')[1].decode())

    def test_compact_table_and_removed_filters_keep_legacy_urls(self):
        from bs4 import BeautifulSoup
        page = BeautifulSoup(self.request('/venues')[1].decode(),'html.parser')
        self.assertEqual(len(page.select('.venue-filter-grid>*')),4)
        self.assertIsNotNone(page.select_one('.venue-filter-grid #venue-open-region'))
        self.assertIsNotNone(page.select_one('.venue-filter-grid>*:first-child [name="q"]'))
        self.assertIsNotNone(page.select_one('.venue-extra-filters [name="registration"]'))
        self.assertEqual(len(page.select('.venue-table>thead th')),6)
        self.assertEqual(len(page.select('.venue-table>tbody>tr.venue-court-card')),50)
        for key in ('venue_type','operator_type','open_from','open_until'):
            self.assertEqual(page.select_one(f'[name="{key}"]')['type'],'hidden')
        self.assertIsNone(page.select_one('[type="time"]'))
        old = self.request('/venues?' + urlencode({'venue_type':'gym','operator_type':'PUBLIC','open_from':'20:00','open_until':'21:00'}))[1].decode()
        self.assertIn('以前のURLの追加条件',old)
        self.assertIn('class="venue-court-card"',old)

    def test_region_is_a_condition_with_a_closed_map_dialog(self):
        from bs4 import BeautifulSoup
        html = self.request('/venues?' + urlencode({'v_area':'23区','v_municipality':'新宿区','v_map':'wards'}))[1].decode()
        page = BeautifulSoup(html,'html.parser')
        button = page.select_one('#venue-open-region')
        self.assertEqual(button['aria-haspopup'],'dialog')
        self.assertEqual(button['aria-controls'],'venue-region-dialog')
        self.assertEqual(button.select_one('#venue-region-label').get_text(),'東京都 / 新宿区')
        dialog = page.select_one('dialog#venue-region-dialog')
        self.assertNotIn('open',dialog.attrs)
        self.assertIsNotNone(dialog.select_one('#venue-region-selector svg'))
        self.assertIsNotNone(dialog.select_one('#venue-region-close'))
        self.assertIsNotNone(dialog.select_one('#venue-region-done'))
        self.assertIsNotNone(dialog.select_one('#venue-map-error[hidden]'))
        self.assertLess(html.index('id="venue-court-filters"'),html.index('id="venue-region-dialog"'))
        self.assertIn('.venue-region-dialog{display:block;position:static',html)

    def test_tariffs_are_explicit_sourced_and_do_not_modify_legacy_records(self):
        from venues.fees import validate
        rows = json.loads(self.request('/api/venues')[1])['courts']
        priced = [r for r in rows if r.get('fee_options')]
        self.assertGreaterEqual(len(priced),230)
        for row in priced:
            validate([{'id':row['id'],'checked_at':row['fee_checked_at'],'fee_options':row['fee_options']}])
        kita = next(r for r in rows if r['name']=='岸町ふれあい館')
        self.assertIsNone(kita['price_from'])
        self.assertEqual(kita['fee_options'][0]['amount'],360)
        self.assertTrue(any('北区民以外' in p['label'] for p in kita['fee_options']))
        meguro = next(r for r in rows if r['name']=='上目黒住区センター')
        self.assertTrue(any('一般団体' in p['label'] for p in meguro['fee_options']))
        schools = [r for r in rows if r['id'].startswith('school-')]
        self.assertTrue(all(r['price_from'] is None and not r.get('fee_options') for r in schools))
        example = {'id':'test','checked_at':'2026-10-12','fee_options':[{'label':'全面','amount':1,'unit':'1時間','conditions':'一般','source_url':'https://example.com/fees'}]}
        for amount in (True,-1,1.5,'100'):
            with self.assertRaises(ValueError):
                validate([{**example,'fee_options':[{**example['fee_options'][0],'amount':amount}]}])

    def test_ota_and_adachi_followup_keeps_field_tariffs_separate(self):
        rows = {r['id']: r for r in json.loads(self.request('/api/venues')[1])['courts']}
        expected = {
            'tokyo-venue-9d64ebf08879': (2200, 8800),
            'tokyo-venue-9e9f2744cb5f': (4800, 19200),
            'tokyo-venue-04126fcd0345': (4800, 19200),
            'tokyo-venue-163714172e30': (9600, 38400),
            'tokyo-venue-8209aecab477': (0, 0),
            'tokyo-venue-edf26e5b5c90': (1400, 1400),
            'tokyo-venue-c6af863d384f': (1400, 1400),
        }
        for ident, bounds in expected.items():
            with self.subTest(venue=ident):
                row = rows[ident]
                self.assertIsNone(row['price_from'])
                self.assertEqual(len(row['fee_ranges']), 1)
                self.assertEqual((row['fee_ranges'][0]['minimum'], row['fee_ranges'][0]['maximum']), bounds)
                self.assertIn('2時間', row['fee_ranges'][0]['unit'])
                self.assertEqual(row['fee_checked_at'], '2026-10-15')
                self.assertEqual(row['cancellation']['checked_at'], '2026-10-15')
        hockey = rows['tokyo-venue-3de282b7fae3']
        self.assertIsNone(hockey['price_from'])
        if hockey.get('fee_checked_at', '') <= '2026-10-19':
            self.assertNotIn('fee_options', hockey)
        else:
            self.assertTrue(all('サブピッチ' in p['unit'] and 'oi-hockey-price' in p['source_url']
                                for p in hockey['fee_options']))

    def test_second_tokyo_followup_preserves_tariff_scope_and_unknowns(self):
        rows = {r['id']: r for r in json.loads(self.request('/api/venues')[1])['courts']}
        expected = {
            'tokyo-venue-f2d52ea48c01': ('運動場全面2時間', 1200, 1200),
            'tokyo-venue-da052fe01f64': ('運動場全面2時間', 6600, 12600),
            'tokyo-venue-58060c86dbf1': ('サッカー場1面2時間', 2400, 2400),
            'tokyo-venue-7594d0210e7b': ('サッカー場1面2時間', 1150, 1150),
            'tokyo-venue-577e7e506936': ('少年サッカー場1面2時間', 0, 0),
            'tokyo-venue-acf6eedff95e': ('球技場1面2時間以内', 1200, 1200),
            'tokyo-venue-e4038f2459a4': ('多目的広場1面2時間', 2440, 2440),
        }
        for ident, (unit, minimum, maximum) in expected.items():
            with self.subTest(venue=ident):
                row = rows[ident]
                self.assertIsNone(row['price_from'])
                group = next(item for item in row['fee_ranges'] if item['unit'] == unit)
                self.assertEqual((group['minimum'], group['maximum']), (minimum, maximum))
                self.assertEqual(row['fee_checked_at'], '2026-10-15')
                self.assertTrue(all(p['source_url'].startswith('https://') for p in row['fee_options']))
        takashimadaira = rows['tokyo-venue-d28e20b0de17']
        self.assertEqual(len(takashimadaira['fee_ranges']), 3)
        okudo = rows['tokyo-venue-48461c620190']
        self.assertEqual(len(okudo['fee_ranges']), 2)
        for ident in ('tokyo-venue-6ff79262c31f',):
            self.assertIsNone(rows[ident]['price_from'])
            if rows[ident].get('fee_checked_at', '') <= '2026-10-19':
                self.assertNotIn('fee_options', rows[ident])
            else:
                self.assertEqual([(p['amount'], p['unit']) for p in rows[ident]['fee_options']],
                                 [(2600, 'フットサルコート1面・2時間')])

    def test_third_tokyo_followup_uses_official_group_tariffs_only(self):
        rows = {r['id']: r for r in json.loads(self.request('/api/venues')[1])['courts']}
        priced = (
            'tokyo-venue-f136cd6fc520', 'tokyo-venue-a5eb0eeb5db6',
            'tokyo-venue-357a53525a36', 'tokyo-venue-554e93c69264',
            'tokyo-venue-fc31b1b81a63', 'tokyo-venue-692ae63adef9',
            'tokyo-venue-a74e54348f42', 'tokyo-venue-933ef55fd937',
            'tokyo-gym-2bc89d47e515', 'tokyo-gym-ee6d6a06a544',
        )
        for ident in priced:
            with self.subTest(venue=ident):
                row = rows[ident]
                self.assertIsNone(row['price_from'])
                self.assertEqual(row['fee_checked_at'], '2026-10-15')
                self.assertTrue(row['fee_options'])
                self.assertTrue(all(option['source_url'].startswith('https://') for option in row['fee_options']))
        arakawa = rows['tokyo-venue-f136cd6fc520']
        self.assertEqual(arakawa['fee_options'][0]['label'], '多目的運動場・一般')
        self.assertEqual(arakawa['fee_ranges'][0]['minimum'], 300)
        for ident, bounds in (
            ('tokyo-gym-2bc89d47e515', (3100, 6200)),
            ('tokyo-gym-ee6d6a06a544', (4300, 8600)),
        ):
            row = rows[ident]
            self.assertEqual(len(row['fee_ranges']), 1)
            self.assertEqual((row['fee_ranges'][0]['minimum'], row['fee_ranges'][0]['maximum']), bounds)
            self.assertEqual(row['cancellation']['checked_at'], '2026-10-15')
        for ident in ('tokyo-venue-933ef55fd937', 'tokyo-gym-07d760f3b816'):
            self.assertEqual(rows[ident]['cancellation']['checked_at'], '2026-10-15')
        for ident in ('tokyo-venue-71237581c393', 'tokyo-venue-2e14b39dc02c'):
            self.assertEqual(rows[ident]['fee_checked_at'], '2026-10-25')
            self.assertTrue(all(p['source_url'] == rows[ident]['official_url'] for p in rows[ident]['fee_options']))
        self.assertTrue(all(p['unit'].startswith('武道場') for p in rows['tokyo-venue-71237581c393']['fee_options']))
        self.assertEqual(rows['tokyo-venue-2e14b39dc02c']['fee_ranges'], [
            {'unit': '庭球場1面・1時間（単価）', 'minimum': 1000, 'maximum': 1000, 'tariff_count': 1}])

    def test_aliases_redirect_to_the_native_directory(self):
        with patch.object(self.app, 'connect', side_effect=AssertionError('Redirect must not open SQLite')) as connect:
            for path in ('/?tab=venues', '/venues/', '/tennis'):
                with self.subTest(path=path):
                    status, _, headers = self.request(path)
                    self.assertIn(status, {301, 302, 303, 307, 308})
                    self.assertEqual(headers['Location'], '/venues')
            connect.assert_not_called()

    def test_tariffs_keep_room_person_and_short_slot_units_distinct(self):
        module = importlib.import_module(self.app.venues.get_venue_catalog.__module__)
        rows = {r['id']:r for r in module.get_catalog()['courts']}
        room = next(r for r in rows.values() if r['name']=='カラオケまねきねこ 経堂農大通り店')
        self.assertTrue(all('1室30分' in p['unit'] for p in room['fee_options']))
        fuchu = rows['tokyo-sports-020']['fee_options']
        late = [p for p in fuchu if '21:00–21:45' in p['label']]
        self.assertEqual({p['amount'] for p in late}, {9900,11550})
        self.assertTrue(all('45分' in p['unit'] for p in late))
        for ident in ('tokyo-sports-029','tokyo-gym-a158d5ba41af','tokyo-venue-a231a98caa19'):
            self.assertTrue(any('アリーナ' in p['label'] and '貸切' in p['unit'] for p in rows[ident]['fee_options']))
        self.assertEqual(module.get_catalog()['meta']['prices_available'], sum(r['price_from'] is not None or bool(r.get('fee_options')) for r in rows.values()))

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

    def test_legacy_area_urls_preselect_the_new_multiple_region_form(self):
        from bs4 import BeautifulSoup
        for area in ('多摩', '23区'):
            status, body, _ = self.request('/venues?' + urlencode({'area': area}))
            self.assertEqual(status, 200)
            page = body.decode()
            field = BeautifulSoup(page,'html.parser').select_one('#venue-places-filter')
            self.assertIn('multiple',field.attrs)
            self.assertEqual([option['value'] for option in field.select('option[selected]')],[area])
            self.assertIn('class="venue-court-card"', page)

    def test_multiple_regions_are_or_matched_and_server_rendered(self):
        from bs4 import BeautifulSoup
        from venues.sports_catalog import get_catalog, filter_catalog
        rows = get_catalog()['courts']
        expected = [row for row in rows if row['municipality'] in {'新宿区','渋谷区'} and row['availability_status']!='SUSPENDED']
        for places in ('新宿区,渋谷区',['新宿区','渋谷区']):
            params = {'places':places}
            self.assertEqual({r['id'] for r in filter_catalog(rows,params)},{r['id'] for r in expected})
            page = BeautifulSoup(self.request('/venues?' + urlencode(params,doseq=True))[1].decode(),'html.parser')
            self.assertEqual(page.select_one('#venue-result-count').get_text(),f'{len(expected):,} 件')
            self.assertEqual(len(page.select('.venue-map-shape.is-active')),2)
            self.assertEqual([o['value'] for o in page.select('#venue-places-filter option[selected]')],['新宿区','渋谷区'])
            self.assertEqual(page.select_one('#venue-region-done').get_text(),'反映する')
            pager = page.select_one('nav[aria-label="会場一覧ページ"] a')
            self.assertIsNotNone(pager)
            next_page = BeautifulSoup(self.request(pager['href'])[1].decode(),'html.parser')
            self.assertEqual(next_page.select_one('#venue-result-count').get_text(),f'{len(expected):,} 件')
            self.assertEqual([o['value'] for o in next_page.select('#venue-places-filter option[selected]')],['新宿区','渋谷区'])
        self.assertEqual(filter_catalog(rows,{'v_places':'埼玉県'}),[])
        self.assertEqual(len(filter_catalog(rows,{'v_places':'東京都,埼玉県'})),len(filter_catalog(rows,{})))
        combined=filter_catalog(rows,{'v_places':'新宿区,渋谷区','v_booking_channel':'web'})
        self.assertTrue(all(r['municipality'] in {'新宿区','渋谷区'} and 'web' in r['booking_channels'] for r in combined))
        page = BeautifulSoup(self.request('/venues?' + urlencode({'places':['新宿区','渋谷区']},doseq=True))[1].decode(),'html.parser')
        self.assertEqual(page.select_one('#directoryContext input[name="v_places"]')['value'],'新宿区,渋谷区')

    def test_region_hierarchy_refines_only_the_selected_parent(self):
        from venues.geography import toggle, matches
        self.assertEqual(toggle(['東京都','埼玉県'],'新宿区'),['埼玉県','新宿区'])
        self.assertEqual(toggle(['新宿区','渋谷区','埼玉県'],'東京都'),['埼玉県','東京都'])
        self.assertEqual(toggle(['23区','多摩'],'渋谷区'),['多摩','渋谷区'])
        self.assertEqual(toggle(['新宿区','渋谷区'],'新宿区'),['渋谷区'])
        self.assertTrue(matches({'prefecture':'埼玉県','area':'県南','municipality':'川口市'},['東京都','埼玉県']))

    def test_search_is_normalized_partial_matching_not_typo_correction(self):
        from venues.sports_catalog import get_catalog, filter_catalog
        rows = get_catalog()['courts']
        self.assertGreater(len(filter_catalog(rows,{'q':'高円寺'})),0)
        self.assertEqual({r['id'] for r in filter_catalog(rows,{'q':'ＦＣ'})},
                         {r['id'] for r in filter_catalog(rows,{'q':'fc'})})
        self.assertGreater(len(filter_catalog(rows,{'q':'ＦＣ'})),0)
        self.assertEqual(filter_catalog(rows,{'q':'高円寺XYZ存在しない'}),[])

    def test_sort_is_associated_with_form_but_outside_filter_panel(self):
        page = self.request('/venues?v_sort=price')[1].decode()
        self.assertNotIn('name="sort"', page.split('</form>')[0])
        self.assertIn('id="venue-sort" name="sort" form="venue-court-filters"', page)
        self.assertIn('value="price" selected', page)
        self.assertIn('name="price_max" type="text" inputmode="numeric"', page)
        self.assertNotIn('step="1"', page)

    def test_booking_and_registration_filters_do_not_treat_unknown_as_no_registration(self):
        module = importlib.import_module(self.app.venues.get_venue_catalog.__module__)
        rows = module.get_catalog()['courts']
        for channel in ('web', 'phone', 'counter'):
            matches = module.filter_catalog(rows, {'booking_channel': channel})
            self.assertGreater(len(matches), 0)
            self.assertTrue(all(channel in r['booking_channels'] for r in matches))
        unknown = module.filter_catalog(rows, {'registration': 'unknown'})
        required = module.filter_catalog(rows, {'registration': 'required'})
        self.assertGreater(len(unknown), 0)
        self.assertGreater(len(required), 0)
        self.assertTrue(all(r['registration_required'] is None for r in unknown))
        self.assertTrue(all(r['registration_required'] is True for r in required))
        not_required = module.filter_catalog(rows, {'registration': 'not_required'})
        self.assertTrue(all(r['registration_required'] is False for r in not_required))
        facets = importlib.import_module(module.enrich.__module__)
        base = {**rows[0], 'booking_method': '窓口申請（予約システムでは空き状況確認のみ）', 'booking_note': ''}
        self.assertEqual(facets.enrich(base)['booking_channels'], ['counter'])
        base.update(booking_method='電話予約・登録不要')
        self.assertIs(facets.enrich(base)['registration_required'], False)

    def test_hours_filters_only_match_confirmed_windows_and_boundaries(self):
        module = importlib.import_module(self.app.venues.get_venue_catalog.__module__)
        rows = module.get_catalog()['courts']
        matches = module.filter_catalog(rows, {'open_from': '20:00', 'open_until': '21:00'})
        self.assertEqual(len(matches), 12)
        self.assertTrue(all(r['opening_checked_at'] and r['official_url'] for r in matches))
        late = module.filter_catalog(rows, {'open_from': '22:00', 'open_until': '23:00'})
        self.assertEqual({r['id'] for r in late}, {'tokyo-jelly-ikebukuro', 'tokyo-jelly-shibuya', 'tokyo-sports-011'})
        self.assertEqual(module.filter_catalog(rows, {'open_from': '23:00', 'open_until': '01:00'}), [])
        self.assertEqual(module.filter_catalog(rows, {'open_from': '21:00', 'open_until': '21:00'}), [])
        self.assertEqual(module.filter_catalog(rows, {'open_from': '25:00'}), module.filter_catalog(rows, {}))
        page = self.request('/venues?open_from=20%3A00&open_until=21%3A00')[1].decode()
        self.assertEqual(page.count('class="venue-court-card"'), 12)
        self.assertIn('伊興地域学習センター', page)
        self.assertIn('通常利用時間', page)

    def test_facility_types_are_independent_of_operator(self):
        module = importlib.import_module(self.app.venues.get_venue_catalog.__module__)
        rows = module.get_catalog()['courts']
        gyms = module.filter_catalog(rows, {'venue_type': 'gym'})
        self.assertGreater(len(gyms), 100)
        self.assertTrue(all('gym' in r['venue_types'] for r in gyms))
        public = module.filter_catalog(rows, {'venue_type': 'gym', 'operator_type': 'PUBLIC'})
        self.assertTrue(all(r['operator_type'] == 'PUBLIC' for r in public))
        matches = module.filter_catalog(rows, {'price_max': '１,３００'})
        self.assertTrue(matches)
        self.assertTrue(all(r['price_per_hour'] is not None and r['price_per_hour'] <= 1300 for r in matches))

    def test_settings_page_assets_and_navigation_are_public_and_safe(self):
        with patch.object(self.app, 'connect', side_effect=AssertionError('Preferences must not open SQLite')):
            for path in ('/settings', *self.app.settings_ui.ASSET_PATHS):
                status, body, headers = self.request(path)
                self.assertEqual(status, 200)
                self.assertTrue(body)
                self.assertNotIn('Set-Cookie', headers)
                self.assertEqual(self.request(path, method='POST')[0], 405)
            page = self.request('/settings?return_to=https://evil.example')[1].decode()
            self.assertIn('class="cm-settings-back" href="/"', page)
            self.assertIn('スマホビュー', page)
            self.assertIn('PCビュー', page)
            self.assertIn('前回の会場検索条件を引き継ぐ', page)
            self.assertTrue(PublicPage(page).meta['robots'].startswith('noindex'))
            self.assertNotIn('https://evil.example', page)
            header = self.request('/venues')[1].decode().split('</header>')[0]
            self.assertIn('class="cm-settings"', header)
            self.assertLess(header.index('id="notificationBell"'), header.index('class="cm-settings"'))
            self.assertIn('/assets/settings/preferences.js?v=', header)
            self.assertEqual(self.request('/assets/settings/../circlematch_db_app.py')[0], 404)


if __name__ == '__main__':
    unittest.main(verbosity=2)
