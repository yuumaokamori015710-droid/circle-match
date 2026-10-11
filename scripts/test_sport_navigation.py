"""Sports-first navigation checks; disposable SQLite and loopback HTTP only."""
from html import unescape
from html.parser import HTMLParser
import re
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlencode, urlsplit

from test_venues import IsolatedAppHttpCase, PublicPage
from test_event_flow import create_account, event_payload, user


class NavigationPage(HTMLParser):
    """Read actual anchors and selected controls, excluding script/style text."""
    def __init__(self, page):
        super().__init__()
        self.metadata = PublicPage(page)
        self.cards, self.selects, self.inputs, self.resources, self.ids = [], [], [], [], set()
        self.visible_parts = []
        self._hidden = 0
        self._form = None
        self._select = None
        self._option = None
        self._anchor = None
        self.feed(page)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if attrs.get('id'):
            self.ids.add(attrs['id'])
        if tag in {'script', 'style'}:
            self._hidden += 1
        if tag == 'script' and attrs.get('src'):
            self.resources.append(urlsplit(attrs['src']).path)
        if tag == 'form':
            self._form = attrs
        if tag == 'input':
            self.inputs.append({**attrs, 'form': self._form})
        if tag == 'select':
            self._select = {**attrs, 'form': self._form, 'options': []}
        if tag == 'option' and self._select is not None:
            self._option = {**attrs, 'text': ''}
        if tag == 'a' and 'sport-card' in attrs.get('class', '').split():
            self._anchor = {**attrs, 'text': ''}

    def handle_data(self, data):
        if not self._hidden:
            self.visible_parts.append(data)
        if self._option is not None:
            self._option['text'] += data
        if self._anchor is not None:
            self._anchor['text'] += data

    def handle_endtag(self, tag):
        if tag in {'script', 'style'}:
            self._hidden = max(0, self._hidden - 1)
        if tag == 'option' and self._option is not None:
            self._select['options'].append(self._option)
            self._option = None
        if tag == 'select' and self._select is not None:
            self.selects.append(self._select)
            self._select = None
        if tag == 'form':
            self._form = None
        if tag == 'a' and self._anchor is not None:
            self._anchor['text'] = self._anchor['text'].strip()
            self.cards.append(self._anchor)
            self._anchor = None

    @property
    def visible(self):
        return ' '.join(self.visible_parts)

    def context(self, name):
        matches = [item for item in self.selects if item.get('name') == name
                   and (item['form'] or {}).get('id') == 'directoryContext']
        if len(matches) != 1:
            raise AssertionError(f'Expected one shared {name} selector, found {len(matches)}')
        return matches[0]

    def selected(self, name):
        options = self.context(name)['options']
        selected = [item.get('value', item['text']) for item in options if 'selected' in item]
        return selected or [options[0].get('value', options[0]['text'])]


class SportNavigationTests(IsolatedAppHttpCase):
    GLOBAL = {'sport': 'テニス', 'region': 'kanto', 'prefecture': '東京都'}
    LOCAL = {'q': 'event-only-search', 'date_from': '2030-04-01', 'date_to': '2030-05-01',
             'event_type': '大会', 'participation': 'team', 'page': '7', 'sort': 'price',
             'v_q': '日比谷', 'v_municipality': '千代田区', 'v_price_max': '1500'}

    def page(self, path):
        status, body, _ = self.request(path)
        self.assertEqual(status, 200)
        text = body.decode('utf-8')
        return text, NavigationPage(text)

    def assert_shared_context(self, parsed, sport, area):
        self.assertEqual(parsed.selected('sport'), [sport])
        self.assertEqual(parsed.selected('area'), [area])
        self.assertEqual(parsed.context('sport')['form']['aria-label'], '競技・地域を選ぶ')

    def assert_shared_tabs(self, parsed, current, global_values, audience='university'):
        tabs = parsed.metadata.tabs
        self.assertEqual([item['text'] for item in tabs], ['大会・イベント', 'サークルDB', '会場予約'])
        active = [item['text'] for item in tabs if item.get('aria-current') == 'page'
                  or 'active' in item.get('class', '').split()]
        self.assertEqual(active, [current] if current else [])
        for item, path in zip(tabs, ['/events', '/', '/venues']):
            parts = urlsplit(item['href'])
            self.assertEqual(parts.path, path)
            self.assertFalse(parts.netloc)
            expected = dict(global_values)
            if item['text'] == 'サークルDB':
                expected.update(tab='db', audience=audience)
            self.assertEqual(parse_qs(parts.query), {key: [value] for key, value in expected.items()})

    def test_home_orders_purpose_then_sports_then_latest_without_active_feature(self):
        text, page = self.page('/')
        self.assertEqual(page.metadata.tabs, [])
        self.assertIn('スポーツ', page.visible)
        self.assertIn('募集する・仲間を集める', page.visible)
        self.assertIn('参加先・サークルを探す', page.visible)
        self.assertIn('home-journeys-heading', page.ids)
        self.assertIn('home-journey-host-heading', page.ids)
        self.assertIn('home-journey-join-heading', page.ids)
        self.assertIn('sports-list', page.ids)
        self.assertLess(text.index('id="home-journeys-heading"'), text.index('id="sports-list"'))
        self.assertLess(text.index('id="sports-list"'), text.index('id="homeLatestEvents"'))
        self.assertGreaterEqual(len(page.cards), len(self.app.POPULAR_SPORTS))
        self.assertIn('homeLatestEvents', page.ids)
        self.assertIn('最新の募集', page.visible)
        self.assertNotIn('eventList', page.ids)
        self.assertNotIn('dbList', page.ids)
        self.assertNotIn('venue-court-list', page.ids)
        self.assertNotIn('/assets/venues/tennis.js', page.resources)
        self.assertNotIn("fetch('/api/events", text)
        self.assertNotIn('fetch("/api/tennis-courts', text)

    def test_home_journey_links_preserve_only_shared_context_and_use_real_destinations(self):
        params = {key: [value] for key, value in dict(self.GLOBAL, **self.LOCAL, audience='social').items()}
        markup = self.app.render_home_journeys(params)
        hrefs = [unescape(value) for value in re.findall(r'href="([^"]+)"', markup)]
        for href in hrefs:
            path = urlsplit(href)
            self.assertFalse(path.netloc)
            self.assertIn(path.path, ['/events', '/events/new', '/', '/venues', '/mypage'])
            query = parse_qs(path.query)
            if path.path == '/mypage':
                self.assertEqual(query, {'tab': ['hosted']})
                continue
            expected = {key: [value] for key, value in self.GLOBAL.items()}
            if path.path == '/':
                expected.update(tab=['db'], audience=['social'])
            self.assertEqual(query, expected)
        self.assertIn('会場が決まっていれば、そのまま募集へ', markup)
        self.assertIn('募集詳細からSNSへ共有', markup)
        empty = self.app.render_home_journeys({})
        self.assertEqual(empty.count('href="#sports-list"'), 2)
        self.assertIn('href="/events/new?custom=1"', empty)

    def test_home_compact_flows_keep_numbered_bold_steps_without_extra_actions(self):
        text, _ = self.page('/')
        flows = [
            ('home-journey-host-heading', '募集の流れ',
             ['競技を選ぶ', '会場を予約する', '募集を作る', '募集を広める'], ['①', '②', '③', '④']),
            ('home-journey-join-heading', '参加先を探す流れ',
             ['競技を選ぶ', '地域を絞る', '参加先・サークルを選ぶ'], ['①', '②', '③']),
        ]
        for heading, label, expected, numbers in flows:
            with self.subTest(flow=label):
                article = re.search(r'<article\b[^>]*aria-labelledby="' + heading + r'"[^>]*>(.*?)</article>', text, re.S)
                self.assertIsNotNone(article)
                summaries = re.findall(r'<ol\b([^>]*class="home-journey-summary"[^>]*)>(.*?)</ol>', article.group(1), re.S)
                self.assertEqual(len(summaries), 1)
                attributes, summary = summaries[0]
                self.assertIn('aria-label="' + label + '"', attributes)
                items = re.findall(r'<li\b[^>]*>(.*?)</li>', summary, re.S)
                self.assertEqual(len(items), len(expected))
                self.assertEqual(re.findall(r'<strong>(.*?)</strong>', summary, re.S), expected)
                self.assertEqual(re.findall(r'<span\b(?=[^>]*class="home-summary-number")(?=[^>]*aria-hidden="true")[^>]*>(.*?)</span>', summary, re.S), numbers)
                self.assertEqual(set(re.findall(r'<([a-z]+)\b', summary)), {'li', 'span', 'strong'})
                self.assertNotRegex(summary, r'\b(?:href|tabindex|onclick)=')
                details = re.search(r'<ol\b[^>]*class="home-journey-steps"[^>]*>(.*?)</ol>', article.group(1), re.S)
                self.assertIsNotNone(details)
                self.assertEqual(re.findall(r'<strong>(.*?)</strong>', details.group(1), re.S), expected)
                self.assertLess(article.group(1).index('class="home-journey-steps"'), article.group(1).index('class="home-journey-summary"'))
                self.assertLess(article.group(1).index('class="home-journey-summary"'), article.group(1).index('class="home-journey-actions"'))
                if heading == 'home-journey-host-heading':
                    self.assertIn('>募集を作る</a>', article.group(1))
                    self.assertNotIn('募集をつくる', article.group(1))

    def test_home_cards_choose_sport_once_and_preserve_only_shared_area(self):
        context = {'region': 'kanto', 'prefecture': '東京都'}
        _, page = self.page('/?' + urlencode(dict(context, q='not-for-cards', v_q='not-for-cards')))
        sports = {item[0] for item in self.app.POPULAR_SPORTS}
        cards = [card for card in page.cards if parse_qs(urlsplit(card['href']).query).get('sport', [''])[0] in sports]
        self.assertEqual(len(cards), len(sports))
        for card in cards:
            with self.subTest(card=card['text']):
                parsed = urlsplit(card['href'])
                self.assertEqual(parsed.path, '/events')
                query = parse_qs(parsed.query)
                self.assertEqual(set(query), {'sport', 'region', 'prefecture'})
                self.assertEqual(query['region'], ['kanto'])
                self.assertEqual(query['prefecture'], ['東京都'])
                self.assertIn('探す', card['text'])
                self.assertNotIn('募集を見る', card['text'])

    def test_global_context_crosses_tabs_without_feature_filters(self):
        query = dict(self.GLOBAL, **self.LOCAL, audience='social')
        for route, current in [('/events', '大会・イベント'), ('/?tab=db', 'サークルDB'), ('/venues', '会場予約')]:
            path = route + ('&' if '?' in route else '?') + urlencode(query)
            with self.subTest(path=path):
                _, parsed = self.page(path)
                self.assert_shared_tabs(parsed, current, self.GLOBAL, 'social' if current == 'サークルDB' else 'university')
                self.assert_shared_context(parsed, 'テニス', 'prefecture:東京都')

    def test_selected_sport_db_keeps_audience_and_does_not_repeat_cards(self):
        for audience in ['university', 'social']:
            with self.subTest(audience=audience):
                _, parsed = self.page('/?' + urlencode(dict(self.GLOBAL, tab='db', audience=audience)))
                self.assert_shared_tabs(parsed, 'サークルDB', self.GLOBAL, audience)
                self.assert_shared_context(parsed, 'テニス', 'prefecture:東京都')
                self.assertEqual(parsed.cards, [])
                self.assertIn('dbList', parsed.ids)

    def test_direct_all_events_and_legacy_event_tab_remain_lists(self):
        for path in ['/events', '/?tab=events']:
            with self.subTest(path=path):
                _, parsed = self.page(path)
                self.assert_shared_tabs(parsed, '大会・イベント', {})
                self.assert_shared_context(parsed, '', '')
                self.assertIn('eventList', parsed.ids)
        _, regional = self.page('/events?' + urlencode({'sport': 'テニス', 'region': 'kanto'}))
        self.assert_shared_context(regional, 'テニス', 'region:kanto')
        self.assertEqual(regional.cards, [])

    def test_public_custom_sport_remains_discoverable_and_selected_without_exposing_drafts(self):
        host = user('navigation-host', 'navigation-host@example.test', '導線テスト主催者')
        create_account(self.app, host)
        published = dict(event_payload('独自競技の公開イベント'), sport_category='独自競技')
        draft = dict(event_payload('非公開の入力途中'), sport_category='非公開競技', status='draft')
        with self.app.connect() as conn:
            self.app.save_event_post(conn, published, host)
        with self.app.connect() as conn:
            self.app.save_event_post(conn, draft, host)
        _, all_events = self.page('/events')
        options = [option['value'] for option in all_events.context('sport')['options']]
        self.assertIn('独自競技', options)
        self.assertNotIn('非公開競技', options)
        _, selected = self.page('/events?' + urlencode({'sport': '独自競技'}))
        self.assert_shared_context(selected, '独自競技', '')
        with patch.object(self.app, 'connect', side_effect=AssertionError('Unknown sport venue must not query SQLite')):
            _, venues = self.page('/venues?' + urlencode({'sport': '独自競技'}))
        self.assert_shared_context(venues, '独自競技', '')
        self.assertIn('掲載準備中', venues.visible)

    def test_venue_aliases_preserve_global_and_venue_query_state(self):
        query = dict(self.GLOBAL, v_q='日比谷', v_municipality='千代田区', v_price_max='1500')
        with patch.object(self.app, 'connect', side_effect=AssertionError('Aliases must not open SQLite')) as connect:
            for route in ['/?tab=venues', '/venues/', '/tennis']:
                with self.subTest(route=route):
                    status, _, headers = self.request(route + ('&' if '?' in route else '?') + urlencode(query))
                    self.assertIn(status, {301, 302, 303, 307, 308})
                    target = urlsplit(headers['Location'])
                    self.assertEqual(target.path, '/venues')
                    self.assertEqual(parse_qs(target.query), {key: [value] for key, value in query.items()})
            connect.assert_not_called()

    def test_noscript_area_submission_replaces_conflicting_area_and_resets_page(self):
        cases = [('/events', {'area': 'region:kansai', 'date_from': '2030-04-01'},
                  {'sport': 'テニス', 'region': 'kansai', 'date_from': '2030-04-01'}),
                 ('/', {'area': 'prefecture:大阪府', 'tab': 'db', 'audience': 'social', 'q': '団体'},
                  {'sport': 'テニス', 'prefecture': '大阪府', 'tab': 'db', 'audience': 'social', 'q': '団体'}),
                 ('/venues', {'area': 'prefecture:神奈川県', 'v_q': 'コート'},
                  {'sport': 'テニス', 'prefecture': '神奈川県', 'v_q': 'コート'})]
        with patch.object(self.app, 'connect', side_effect=AssertionError('Area redirect must not open SQLite')) as connect:
            for route, submitted, expected in cases:
                query = dict(self.GLOBAL, page='7', **submitted)
                with self.subTest(route=route):
                    status, _, headers = self.request(route + '?' + urlencode(query))
                    self.assertIn(status, {301, 302, 303, 307, 308})
                    target = urlsplit(headers['Location'])
                    self.assertEqual(target.path, route)
                    self.assertEqual(parse_qs(target.query), {key: [value] for key, value in expected.items()})
            connect.assert_not_called()

    def test_unknown_venue_filter_names_cannot_inject_markup(self):
        attack_key = 'v_"><script>__navigation_probe__</script><input name="x'
        query = dict(self.GLOBAL, v_q='日比谷', v_unknown='unrecognized', **{attack_key: 'injected'})
        with patch.object(self.app, 'connect', side_effect=AssertionError('Venue filtering must not query SQLite')):
            text, parsed = self.page('/venues?' + urlencode(query))
        self.assertNotIn('<script>__navigation_probe__</script>', text)
        names = [item.get('name') for item in parsed.inputs
                 if (item['form'] or {}).get('id') == 'directoryContext']
        self.assertIn('v_q', names)
        self.assertNotIn('v_unknown', names)
        self.assertNotIn(attack_key, names)

    def test_supported_tennis_tokyo_pages_load_catalog_script_without_database(self):
        cases = [{}, {'sport': 'テニス'}, {'sport': 'テニス', 'region': 'kanto'},
                 {'sport': 'テニス', 'prefecture': '東京都'}]
        with patch.object(self.app, 'connect', side_effect=AssertionError('Venue pages must not open SQLite')) as connect:
            for query in cases:
                path = '/venues' + ('?' + urlencode(query) if query else '')
                with self.subTest(query=query):
                    _, parsed = self.page(path)
                    self.assertIn('/assets/venues/tennis.js', parsed.resources)
                    self.assertIn('venue-court-list', parsed.ids)
            connect.assert_not_called()

    def test_unavailable_sports_or_areas_do_not_claim_or_fetch_tokyo_tennis(self):
        cases = [{'sport': 'サッカー・フットサル'}, {'sport': 'テニス', 'prefecture': '大阪府'},
                 {'sport': 'テニス', 'region': 'kansai'}, {'region': 'kansai'},
                 {'sport': 'テニス', 'region': 'kanto', 'prefecture': '神奈川県'}]
        with patch.object(self.app, 'connect', side_effect=AssertionError('Unavailable directory must stay static')) as connect:
            for query in cases:
                with self.subTest(query=query):
                    text, parsed = self.page('/venues?' + urlencode(query))
                    self.assertIn('掲載準備中', parsed.visible)
                    self.assertNotIn('/assets/venues/tennis.js', parsed.resources)
                    self.assertNotIn('venue-court-list', parsed.ids)
                    self.assertNotIn('fetch("/api/tennis-courts', text)
                    self.assertEqual(parsed.metadata.meta['robots'], 'noindex, follow')
                    self.assert_shared_tabs(parsed, '会場予約', query)
            connect.assert_not_called()

    def test_home_and_all_event_listing_have_distinct_canonical_metadata(self):
        home_text, home = self.page('/')
        event_text, events = self.page('/events')
        self.assertEqual(home.metadata.canonicals, ['https://circle-match.jp/'])
        self.assertEqual(events.metadata.canonicals, ['https://circle-match.jp/events'])
        self.assertTrue(home.metadata.meta['robots'].startswith('index, follow'))
        titles = [unescape(re.search(r'<title>(.*?)</title>', text, re.S).group(1)) for text in [home_text, event_text]]
        self.assertNotEqual(*titles)
        self.assertIn('大会・イベント', titles[1])
        _, legacy = self.page('/?tab=events')
        self.assertEqual(legacy.metadata.canonicals, ['https://circle-match.jp/events'])

    def test_venue_metadata_retains_shared_context_but_not_local_filters(self):
        _, supported = self.page('/venues?' + urlencode(self.GLOBAL))
        self.assertTrue(supported.metadata.meta['robots'].startswith('index, follow'))
        canonical = urlsplit(supported.metadata.canonicals[0])
        self.assertEqual(canonical.path, '/venues')
        self.assertEqual(parse_qs(canonical.query), {key: [value] for key, value in self.GLOBAL.items()})
        _, filtered = self.page('/venues?' + urlencode(dict(self.GLOBAL, v_q='日比谷', v_price_max='1500')))
        self.assertEqual(filtered.metadata.meta['robots'], 'noindex, follow')
        self.assertEqual(filtered.metadata.canonicals, supported.metadata.canonicals)
        text, unavailable = self.page('/venues?' + urlencode({'sport': 'サッカー・フットサル', 'prefecture': '大阪府'}))
        title = unescape(re.search(r'<title>(.*?)</title>', text, re.S).group(1))
        self.assertIn('サッカー・フットサル', title)
        self.assertIn('大阪府', title)
        self.assertEqual(unavailable.metadata.meta['robots'], 'noindex, follow')


if __name__ == '__main__':
    unittest.main(verbosity=2)
