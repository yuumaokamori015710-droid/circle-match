"""Cost controls exercise disposable SQLite/loopback HTTP, never production."""
import json
import gzip
import os
import sys
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request
from unittest.mock import patch

from test_venues import IsolatedAppHttpCase

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'outputs'))
import circlematch_delivery as delivery


class DeliveryTests(IsolatedAppHttpCase):
    def call(self, path, headers=None, method='GET'):
        request = Request(self.base + path, headers=headers or {}, method=method)
        try:
            response = self.opener.open(request, timeout=15)
        except HTTPError as error:
            response = error
        with response:
            return response.status, response.read(), response.headers

    def test_public_cache_is_identical_with_credentials_and_conditional_get(self):
        path = '/api/venues?view=page&limit=50'
        status, body, headers = self.call(path)
        self.assertEqual(status, 200)
        self.assertIn('public, max-age=300', headers['Cache-Control'])
        self.assertNotIn('Set-Cookie', headers)
        tag = headers['ETag']
        for extra in ({'Cookie': 'cm_session=not-a-session'}, {'Authorization': 'Basic invalid'}):
            self.assertEqual(self.call(path, extra)[1], body)
        for condition in (tag, 'W/' + tag, '"different", ' + tag, '*'):
            status, body, headers = self.call(path, {'If-None-Match': condition})
            self.assertEqual((status, body), (304, b''))
            self.assertEqual(headers['ETag'], tag)
        self.assertEqual(self.call(path, {'If-None-Match': '"old"'})[0], 200)
        with patch.object(self.app.venues, 'get_venue_page', return_value={'courts': [], 'meta': {'changed': True}}):
            changed_status, changed_body, changed_headers = self.call(path, {'If-None-Match': tag})
            self.assertEqual(changed_status, 200)
            self.assertNotEqual(changed_headers['ETag'], tag)
            self.assertTrue(json.loads(changed_body)['meta']['changed'])

    def test_page_only_transfers_requested_results_and_does_not_mutate_catalog(self):
        full = json.loads(self.call('/api/venues')[1])
        first_body = self.call('/api/venues?view=page&limit=50')[1]
        first = json.loads(first_body)
        second = json.loads(self.call('/api/venues?view=page&limit=50&offset=50')[1])
        self.assertEqual(len(first['courts']), 50)
        self.assertEqual(first['meta']['results'], len(self.app.venues.filter_catalog(full['courts'], {})))
        self.assertTrue(first['meta']['has_more'])
        self.assertFalse({r['id'] for r in first['courts']} & {r['id'] for r in second['courts']})
        self.assertLess(len(first_body), len(json.dumps(full, ensure_ascii=False).encode()) / 5)
        self.assertEqual(len(json.loads(self.call('/api/venues')[1])['courts']), len(full['courts']))
        self.assertNotEqual(self.call('/api/venues?view=page')[2]['ETag'],
                            self.call('/api/venues?view=page&offset=50')[2]['ETag'])

    def test_filters_sort_pagination_and_bounds(self):
        query = {'v_registration': ['not_required'], 'v_sort': ['name_desc'], 'v_places': ['江東区']}
        full = self.app.venues.get_venue_catalog(query)
        expected = self.app.venues.filter_catalog(full['courts'], query)
        actual = json.loads(self.call('/api/venues?view=page&v_registration=not_required&v_sort=name_desc&v_places=%E6%B1%9F%E6%9D%B1%E5%8C%BA')[1])
        self.assertEqual(actual['courts'], expected[:50])
        self.assertEqual(actual['meta']['results'], len(expected))
        for suffix in ('&limit=999999&offset=-5', '&limit=bad&offset=bad', '&limit=0'):
            result = json.loads(self.call('/api/venues?view=page' + suffix)[1])
            self.assertLessEqual(len(result['courts']), 50)
        self.assertEqual(json.loads(self.call('/api/venues?view=page&offset=999999')[1])['courts'], [])

    def test_assets_revalidate_and_private_pages_never_cache(self):
        path = '/assets/venues/tennis.js'
        _, _, headers = self.call(path)
        self.assertEqual(self.call(path, {'If-None-Match': headers['ETag']})[:2], (304, b''))
        for path in ('/signin', '/settings', '/events/new', '/api/me', '/api/notifications/unread'):
            status, _, headers = self.call(path, {'If-None-Match': '*', 'Cookie': 'cm_session=invalid'})
            self.assertNotEqual(status, 304)
            self.assertNotIn('ETag', headers)
            self.assertNotIn('public', headers.get('Cache-Control', ''))
        with patch.object(self.app, 'current_user', return_value={'authenticated': True, 'user_id': 'member'}):
            status, _, headers = self.call('/settings')
            self.assertEqual(status, 200)
            self.assertIn('no-store', headers['Cache-Control'])

    def test_only_cookie_free_public_listings_cache_and_compress(self):
        status, body, headers = self.call('/venues', {'Accept-Encoding': 'gzip'})
        self.assertEqual(status, 200)
        self.assertEqual(headers['Content-Encoding'], 'gzip')
        self.assertIn(b'venue-directory', gzip.decompress(body))
        self.assertIn('Cookie', headers['Vary'])
        self.assertIn('Authorization', headers['Vary'])
        self.assertIn('Accept-Encoding', headers['Vary'])
        self.assertIn('max-age=60', headers['Cache-Control'])
        self.assertEqual(self.call('/venues', {'Accept-Encoding': 'gzip', 'If-None-Match': headers['ETag']})[:2], (304, b''))
        for extra in ({'Cookie': 'cm_session=invalid'}, {'Authorization': 'Basic invalid'}):
            status, body, private = self.call('/venues', {**extra, 'Accept-Encoding': 'gzip', 'If-None-Match': '*'})
            self.assertEqual(status, 200)
            self.assertIn('no-store', private['Cache-Control'])
            self.assertNotIn('ETag', private)
            self.assertNotIn('Content-Encoding', private)
        self.assertEqual(self.call('/venues', {'Accept-Encoding': 'gzip;q=0, *;q=1'})[2].get('Content-Encoding'), None)
        self.assertTrue(delivery.accepts_gzip('br, gzip'))
        self.assertFalse(delivery.accepts_gzip('gzip;q=bad'))

    def test_excess_crawlers_only_not_browsers_or_search_engines(self):
        class Reject:
            def allow(self, *args):
                return False
        with patch.dict(os.environ, {'RENDER': 'true'}), patch.object(delivery, 'CRAWLER_LIMITER', Reject()):
            headers = {'CF-Connecting-IP': '192.0.2.1', 'User-Agent': 'AhrefsBot'}
            status, _, response = self.call('/', headers)
            self.assertEqual(status, 429)
            self.assertEqual(response['Retry-After'], '3')
            for agent in ('Mozilla/5.0', 'Googlebot', 'AdsBot-Google', 'Mediapartners-Google', 'bingbot', 'Applebot'):
                self.assertEqual(self.call('/', {**headers, 'User-Agent': agent})[0], 200)
            self.assertEqual(self.call('/', {**headers, 'Cookie': 'cm_session=invalid'})[0], 200)
            for path in ('/healthz', '/events/new'):
                self.assertNotEqual(self.call(path, headers)[0], 429)
        self.assertEqual(delivery.client_group('GPTBot'), 'openai-crawler')

    def test_robots_excludes_duplicate_facets_not_public_core(self):
        status, body, _ = self.call('/robots.txt')
        self.assertEqual(status, 200)
        self.assertIn(b'Disallow: /*?*q=', body)
        self.assertIn(b'Disallow: /*?*v_', body)
        self.assertNotIn(b'Disallow: /events\n', body)
        self.assertNotIn(b'Disallow: /venues\n', body)

    def test_distributed_crawler_family_shares_one_budget(self):
        calls = []
        class Record:
            def allow(self, key, paginated):
                calls.append(key)
                return True
        with patch.dict(os.environ, {'RENDER': 'true'}), patch.object(delivery, 'CRAWLER_LIMITER', Record()):
            for address in ('192.0.2.1', '192.0.2.2'):
                self.assertEqual(self.call('/', {'User-Agent': 'meta-externalagent', 'CF-Connecting-IP': address})[0], 200)
            self.assertEqual(self.call('/signin', {'User-Agent': 'meta-externalagent'})[0], 200)
            self.assertEqual(self.call('/', {'User-Agent': 'Mozilla/5.0'})[0], 200)
        self.assertEqual(calls, ['meta-crawler', 'meta-crawler', 'meta-crawler'])

    def test_limit_applies_only_to_catalogs_not_login_health_or_applications(self):
        class Reject:
            def allow(self, *args):
                return False
        with patch.dict(os.environ, {'RENDER': 'true'}), patch.object(delivery, 'LIMITER', Reject()):
            status, body, headers = self.call('/api/venues?view=page', {'CF-Connecting-IP': '192.0.2.1'})
            self.assertEqual(status, 429)
            self.assertEqual(headers['Retry-After'], '2')
            self.assertEqual(headers['Cache-Control'], 'no-store')
            for path in ('/healthz', '/signin', '/api/events', '/events/new'):
                self.assertNotEqual(self.call(path)[0], 429)

    def test_stats_group_urls_and_never_record_secrets(self):
        timestamp = [0]
        reports = []
        stats = delivery.DeliveryStats(interval=60, clock=lambda: timestamp[0], emit=reports.append)
        stats.record('/events/secret-id?email=secret@example.test&token=never-log', 200, 100, 'Mozilla/5.0 raw-secret-agent')
        timestamp[0] = 61
        stats.record('/api/venues?v_q=secret-address', 304, 0, 'CircleMatchContactResearch/1.0')
        text = json.dumps(reports)
        for secret in ('secret', 'token', 'example.test', 'Mozilla', 'v_q'):
            self.assertNotIn(secret, text)
        self.assertEqual(sum(row['body_bytes'] for row in reports[0]['rows']), 100)
        self.assertEqual(sum(row['requests'] for row in reports[0]['rows']), 2)
        self.assertEqual(delivery.client_address('127.0.0.1', 'fake, 192.0.2.2', True, '192.0.2.1'), '192.0.2.1')
        self.assertIsNone(delivery.client_address('127.0.0.1', 'fake, 192.0.2.1', True))
        self.assertEqual(delivery.client_address('127.0.0.1', '192.0.2.1', True), '192.0.2.1')
        self.assertEqual(delivery.client_address('127.0.0.1', 'fake', False), '127.0.0.1')

    def test_limiter_refills_and_bounds_memory(self):
        now = [0]
        limiter = delivery.CatalogLimiter(clock=lambda: now[0], capacity=4)
        self.assertTrue(all(limiter.allow('test', False) for _ in range(30)))
        self.assertFalse(limiter.allow('test', False))
        self.assertTrue(limiter.allow('test', True))
        now[0] = 2
        self.assertTrue(limiter.allow('test', False))
        for index in range(20):
            limiter.allow(str(index), True)
        self.assertLessEqual(len(limiter.clients), 4)

    def test_logging_failure_never_affects_response(self):
        with patch.object(delivery.STATS, 'record', side_effect=OSError('diagnostic failure')):
            self.assertEqual(self.call('/signin')[0], 200)
            self.assertEqual(self.call('/api/venues?view=page')[0], 200)
