"""Real public HTTP/UI contracts using disposable data; no external effects."""
from html.parser import HTMLParser
from html import unescape
import json
import unittest
from urllib.parse import parse_qs, urlencode, urlparse

from test_event_flow import create_account, event_payload, user
from test_venues import IsolatedAppHttpCase


class Elements(HTMLParser):
    def __init__(self, markup):
        super().__init__()
        self.nodes = []
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        self.nodes.append((tag, dict(attrs)))


class ClubUITests(IsolatedAppHttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.app.init_db()
        cls.host = user('club-host', 'private-club-host@example.test', '公開主催者')
        create_account(cls.app, cls.host)

    def setUp(self):
        with self.app.connect() as conn:
            conn.execute('delete from event_applications')
            conn.execute('delete from event_posts')

    def event(self, title='Club UI <test>', **updates):
        payload = event_payload(title)
        payload.update(updates)
        with self.app.connect() as conn:
            return self.app.save_event_post(conn, payload, self.host)

    def test_real_home_preserves_logo_public_event_and_navigation(self):
        eid = self.event()
        status, raw, _ = self.request('/')
        self.assertEqual(status, 200)
        page = raw.decode()
        self.assertIn('/events/' + eid, page)
        self.assertIn('Club UI &lt;test&gt;', page)
        self.assertIn('/assets/circle-match-mark.png?v=20260809', page)
        self.assertIn('club-bottom-nav', page)
        self.assertIn('競技イメージ', page)
        self.assertNotIn(self.host['email'], page)
        nodes = Elements(page).nodes
        for suffix in ('styles.css', 'app.js'):
            urls = [a.get('src') or a.get('href') or '' for _, a in nodes]
            self.assertEqual(sum(url.startswith('/assets/club/' + suffix + '?v=') for url in urls), 1)

    def test_rail_is_context_safe_and_all_clears_sport(self):
        rail = self.app.club_ui.sport_rail({'sport':['テニス'], 'prefecture':['東京都'],
            'date_from':['2030-01-01'], 'q':['A&B'], 'page':['4']})
        links = [attrs for tag, attrs in Elements(rail).nodes if tag == 'a']
        self.assertEqual(len(links), 17)
        for link in links:
            url = urlparse(unescape(link['href']))
            query = parse_qs(url.query)
            self.assertEqual(url.path, '/events')
            self.assertEqual(query['prefecture'], ['東京都'])
            self.assertEqual(query['date_from'], ['2030-01-01'])
            self.assertEqual(query['q'], ['A&B'])
            self.assertNotIn('page', query)
        self.assertNotIn('sport', parse_qs(urlparse(links[0]['href']).query))
        self.assertEqual(sum(a.get('aria-current') == 'true' for a in links), 1)
        custom = self.app.club_ui.sport_rail({'sport':['<long "custom">']})
        self.assertIn('&lt;long &quot;custom&quot;&gt;', custom)
        self.assertNotIn('<long', custom)
        venue = self.app.club_ui.sport_rail({}, 'venues')
        queries = [parse_qs(urlparse(a['href']).query).get('sport', [''])[0]
                   for tag, a in Elements(venue).nodes if tag == 'a']
        self.assertIn('サッカー・フットサル', queries)
        self.assertNotIn('フットサル', queries)

    def test_keyword_search_is_real_and_filters_remain_combined(self):
        wanted = self.event('Keyword Cup', sport_category='テニス', location='West Court')
        self.event('Other Cup', sport_category='サッカー・フットサル', location='East Court')
        self.event('Keyword draft', status='draft')
        for query in ('Keyword', 'West Court', 'テスト主催者'):
            status, raw, _ = self.request('/api/events?' + urlencode({'sport':'テニス', 'q':query}))
            self.assertEqual(status, 200)
            self.assertEqual([e['event_id'] for e in json.loads(raw)], [wanted])
        result = self.app.search_events({'q':["' OR 1=1 --"]})
        self.assertEqual(result, [])
        page = self.request('/events?' + urlencode({'q':'<script>alert(1)</script>'}))[1].decode()
        self.assertNotIn('value="<script>', page)
        self.assertIn('name="q" value="&lt;script&gt;', page)
        self.assertIn('clubPhoto(e.sport_category)', page)
        self.assertNotIn('__CLUB_SPORTS__', page)

    def test_assets_and_mutating_methods_are_bounded(self):
        for path, kind in (('/assets/club/styles.css', 'text/css'), ('/assets/club/app.js', 'application/javascript'),
                           ('/assets/club/tennis.webp', 'image/webp'), ('/assets/club/tennis-thumb.webp', 'image/webp')):
            status, raw, headers = self.request(path)
            self.assertEqual(status, 200)
            self.assertGreater(len(raw), 200)
            self.assertIn(kind, headers['Content-Type'])
            self.assertIn('max-age', headers['Cache-Control'])
            self.assertEqual(self.request(path, method='POST')[0], 405)
        self.assertEqual(self.request('/assets/club/icons.json')[0], 404)
        self.assertEqual(self.request('/assets/club/../../circlematch.sqlite')[0], 404)

    def test_signin_retains_auth_controls_with_matching_style(self):
        status, raw, _ = self.request('/signin?return_to=/mypage')
        page = raw.decode()
        self.assertEqual(status, 200)
        self.assertIn('<body class="cm-club">', page)
        self.assertIn('/assets/club/styles.css?v=', page)
        self.assertIn('id="googleButton"', page)
        self.assertNotIn('<nav class="club-bottom-nav"', page)

    def test_detail_uses_existing_member_path_and_preserves_fees(self):
        eid = self.event(participation_type='both', capacity='', fee_amount='2500',
                         individual_fee_amount='2500', team_fee_amount='15000', payment_method='bank_transfer')
        status, raw, _ = self.request('/events/' + eid)
        page = raw.decode()
        self.assertEqual(status, 200)
        self.assertIn('2,500', page)
        self.assertIn('15,000', page)
        self.assertIn('定員なし', page)
        self.assertIn('mobile-apply', page)
        self.assertIn('/signin?', page)
        self.assertNotIn('private-club-host', page)
        self.assertIn('club-detail-photo', page)
        self.assertIn('キャンセル・中止条件', page)


if __name__ == '__main__':
    unittest.main(verbosity=2)
