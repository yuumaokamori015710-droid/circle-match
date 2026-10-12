"""Circle map filtering and SSR, isolated from the real circle databases."""
import json
import re
from html import unescape
from urllib.parse import urlencode, parse_qs, urlsplit
from unittest.mock import patch

from test_venues import IsolatedAppHttpCase


class CircleRegionTests(IsolatedAppHttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        with cls.app.connect() as conn:
            for code, pref, city in [('shinjuku', '東京都', '新宿区'), ('shibuya', '東京都', '渋谷区'), ('saitama', '埼玉県', 'さいたま市'), ('osaka', '大阪府', '大阪市'), ('unknown', '東京都', '')]:
                conn.execute('insert into universities(university_id,university_name,prefecture,city,created_at,updated_at) values(?,?,?,?,?,?)',
                             ('map_'+code, '地図テスト大学'+code, pref, city, cls.app.now(), cls.app.now()))
                for audience, kind in [('university', 'サークル'), ('social', '社会人サークル')]:
                    for number in range(26 if code == 'shinjuku' else 1):
                        cls.app.upsert_circle(conn, {'university_id': 'map_'+code, 'circle_name': f'地図テスト{audience}{code}{number}',
                            'organization_type': kind, 'sport_category': 'サッカー・フットサル', 'public_status': 'published',
                            'activity_area': '新宿区の体育館' if code == 'unknown' else '', 'verification_status': 'unverified'}, audit_entry=False)

    def params(self, **values):
        return {key: [value] for key, value in dict(q='地図テスト', audience='university', **values).items()}

    def test_or_filter_and_audience_scope(self):
        for audience in ['university', 'social']:
            query = self.params(places='新宿区,渋谷区', sport='サッカー・フットサル')
            query['audience'] = [audience]
            circles = self.app.search_circles(query)
            self.assertEqual(len(circles), 28)
            self.assertTrue(all(audience in c['circle_name'] for c in circles))
            self.assertEqual(self.app.circle_query_stats(query)['circles'], 28)

    def test_prefecture_region_and_legacy_urls(self):
        for places, expected in [('東京都,埼玉県', 29), ('関東', 29), ('大阪府', 1), ('23区', 28), ('多摩', 0)]:
            self.assertEqual(self.app.circle_query_stats(self.params(places=places))['circles'], expected)
        self.assertEqual(self.app.circle_query_stats(self.params(prefecture='埼玉県'))['circles'], 1)
        self.assertEqual(self.app.circle_query_stats(self.params(region='kansai'))['circles'], 1)
        self.assertEqual(self.app.circle_query_stats(self.params(places='大阪府', prefecture='東京都'))['circles'], 1)

    def test_parameters_are_bound_and_repeated_places_supported(self):
        for token in ["' or 1=1 --", '%', '_', '存在しない区']:
            self.assertEqual(self.app.circle_query_stats(self.params(places=token))['circles'], 0)
        query = self.params()
        query['places'] = ['新宿区', '渋谷区']
        self.assertEqual(self.app.circle_query_stats(query)['circles'], 28)

    def test_inline_ssr_in_all_circle_views(self):
        for path, audience in [('/?tab=db', 'university'), ('/?tab=db&audience=social', 'social'), ('/circles?', 'university'), ('/social/circles?', 'social')]:
            status, body, _ = self.request(path + '&' + urlencode({'q': '地図テスト', 'places': '新宿区,渋谷区', 'c_map': 'wards'}))
            text = body.decode()
            self.assertEqual(status, 200)
            self.assertIn('id="circle-region-picker"', text)
            self.assertNotIn('<dialog', text)
            visible = re.sub(r'<script\b[^>]*>.*?</script>', '', text, flags=re.S)
            self.assertIn('地図テスト'+audience+'shinjuku', visible)
            self.assertNotIn('地図テスト'+('social' if audience == 'university' else 'university')+'shinjuku', visible)
            self.assertIn('circle-map-shape is-active', visible)

    def test_map_counts_scoped_by_sport_and_audience(self):
        status, body, _ = self.request('/api/circle-map?' + urlencode({'path': '/circles', 'audience': 'social', 'q': '地図テスト', 'c_map': 'wards'}))
        self.assertEqual(status, 200)
        markup = json.loads(body)['html']
        self.assertIn('aria-label="新宿区 27団体"', markup)
        self.assertNotIn('地図テスト', markup)
        status, body, _ = self.request('/api/circle-map?' + urlencode({'path': '/social/circles', 'q': '地図テスト', 'sport': 'テニス', 'c_map': 'wards'}))
        self.assertIn('aria-label="新宿区 0団体"', json.loads(body)['html'])

    def test_national_drilldown_and_links_preserve_conditions(self):
        query = self.params(tab='db', places='東京都,埼玉県', c_map='japan')
        markup = self.app.render_circle_region_map(query)
        hrefs = [unescape(h) for h in re.findall(r'href="([^"]+)"', markup) if h.startswith('/?')]
        self.assertTrue(hrefs)
        for href in hrefs:
            params = parse_qs(urlsplit(href).query)
            self.assertEqual(params['q'], ['地図テスト'])
            self.assertEqual(params['audience'], ['university'])
        self.assertIn('関西を詳しく選ぶ', markup)
        query['c_map'] = ['kansai']
        self.assertIn('大阪府', self.app.render_circle_region_map(query))

    def test_pagination_and_audience_links_retain_multiple_places(self):
        query = self.params(tab='db', places='新宿区,渋谷区', c_map='wards')
        markup = self.app.render_public_html(query).decode()
        for href in re.findall(r'href="([^"]+)"', markup):
            parsed = parse_qs(urlsplit(unescape(href)).query)
            if parsed.get('page') or parsed.get('audience') == ['social']:
                self.assertEqual(parsed['places'], ['新宿区,渋谷区'])

    def test_map_failure_does_not_claim_zero_groups(self):
        with patch.object(self.app, 'circle_region_groups', side_effect=RuntimeError('map test failure')):
            markup = self.app.render_circle_region_map(self.params())
        self.assertIn('取得失敗', markup)
        self.assertNotIn('0団体', markup)
