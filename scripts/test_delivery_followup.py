"""Additional public delivery savings, with private flows kept out of scope."""
import gzip
import json
import os
from unittest.mock import patch

import test_delivery
from test_event_flow import create_account, user
from test_venues import IsolatedAppHttpCase
import circlematch_delivery as delivery


class PublicDocumentDeliveryTests(IsolatedAppHttpCase):
    call = test_delivery.DeliveryTests.call

    def test_information_pages_compress_and_revalidate(self):
        for path in ('/privacy', '/terms', '/operator', '/about-data', '/contact', '/guides/tokyo-venue-costs'):
            with self.subTest(path=path):
                status, plain, _ = self.call(path)
                compressed_status, encoded, headers = self.call(path, {'Accept-Encoding': 'gzip'})
                self.assertEqual((status, compressed_status), (200, 200))
                self.assertEqual(headers['Content-Encoding'], 'gzip')
                self.assertEqual(gzip.decompress(encoded), plain)
                self.assertLess(len(encoded), len(plain) / 2)
                self.assertIn('max-age=60', headers['Cache-Control'])
                self.assertEqual(self.call(path, {'Accept-Encoding': 'gzip', 'If-None-Match': headers['ETag']})[:2], (304, b''))

    def test_public_route_allowlist_excludes_private_and_unknown_paths(self):
        for path in ('/privacy', '/terms', '/guides/tennis', '/circles/sample-club'):
            self.assertTrue(delivery.public_document(path), path)
        for path in ('/signin', '/settings', '/events/new', '/events/example', '/events/example/guest',
                     '/invitations/new', '/mypage', '/notifications', '/payments', '/admin',
                     '/api/me', '/api/events', '/unknown', '/circles/sample/edit', '/guides/a/b'):
            self.assertFalse(delivery.public_document(path), path)

    def test_information_pages_with_credentials_are_never_cached_or_compressed(self):
        for path in ('/privacy', '/terms', '/contact'):
            for extra in ({'Cookie': 'cm_session=invalid'}, {'Authorization': 'Basic invalid'}):
                status, _, headers = self.call(path, {**extra, 'Accept-Encoding': 'gzip', 'If-None-Match': '*'})
                self.assertEqual(status, 200)
                self.assertIn('no-store', headers['Cache-Control'])
                self.assertNotIn('ETag', headers)
                self.assertNotIn('Content-Encoding', headers)

    def test_public_data_and_text_assets_have_encoding_specific_validators(self):
        for path in ('/api/venues?view=page&limit=50', '/api/tennis-courts', '/assets/venues/tennis.js'):
            with self.subTest(path=path):
                _, plain, identity = self.call(path)
                status, encoded, compressed = self.call(path, {'Accept-Encoding': 'gzip'})
                self.assertEqual(status, 200)
                self.assertEqual(compressed['Content-Encoding'], 'gzip')
                self.assertEqual(gzip.decompress(encoded), plain)
                self.assertLess(len(encoded), len(plain) / 2)
                self.assertNotEqual(identity['ETag'], compressed['ETag'])
                for headers in (identity, compressed):
                    self.assertIn('Accept-Encoding', headers['Vary'])
                self.assertEqual(self.call(path, {'Accept-Encoding': 'gzip', 'If-None-Match': compressed['ETag']})[:2], (304, b''))
                self.assertEqual(self.call(path, {'If-None-Match': compressed['ETag']})[0], 200)
                self.assertEqual(self.call(path, {'Accept-Encoding': 'gzip;q=0'})[1], plain)
                self.assertNotIn('Content-Encoding', self.call(path, {'Accept-Encoding': 'gzip;q=0'})[2])

    def test_public_information_uses_same_crawler_budget(self):
        calls = []

        class Reject:
            def allow(self, family, paginated):
                calls.append((family, paginated))
                return False

        with patch.dict(os.environ, {'RENDER': 'true'}), patch.object(delivery, 'CRAWLER_LIMITER', Reject()):
            for path in ('/privacy', '/terms', '/guides/article', '/circles/sample-club'):
                status, body, headers = self.call(path, {'User-Agent': 'meta-externalagent'})
                self.assertEqual(status, 429)
                self.assertEqual(headers['Retry-After'], '3')
                self.assertEqual(json.loads(body)['error'], 'crawler_rate_limit')
            for agent in ('Mozilla/5.0', 'Googlebot', 'AdsBot-Google', 'Mediapartners-Google', 'Bingbot', 'Applebot'):
                self.assertEqual(self.call('/privacy', {'User-Agent': agent})[0], 200)
            for extra in ({'Cookie': 'cm_session=invalid'}, {'Authorization': 'Basic invalid'}):
                self.assertEqual(self.call('/privacy', {'User-Agent': 'meta-externalagent', **extra})[0], 200)
            for path in ('/signin', '/healthz', '/events/new', '/events/example', '/events/example/guest'):
                self.assertNotEqual(self.call(path, {'User-Agent': 'meta-externalagent'})[0], 429)
        self.assertEqual(calls, [('meta-crawler', False)] * 4)

    def test_profile_visibility_and_private_navigation_remain_live(self):
        with self.app.connect() as conn:
            circle = conn.execute("select c.circle_id from circles c where not exists (select 1 from circle_listing_reviews lr where lr.circle_id=c.circle_id and lr.review_status='pending') limit 1").fetchone()[0]
            conn.execute("insert into circle_public_profiles(profile_id,circle_id,profile_slug,is_published,created_at,updated_at) values(?,?,?,1,?,?)",
                         ('delivery-test', circle, 'delivery-test-club', self.app.now(), self.app.now()))
        try:
            path = '/circles/delivery-test-club'
            status, encoded, headers = self.call(path, {'Accept-Encoding': 'gzip'})
            self.assertEqual(status, 200)
            self.assertIn('max-age=0, must-revalidate', headers['Cache-Control'])
            self.assertIn(b'Circle Match', gzip.decompress(encoded))
            self.assertEqual(self.call(path, {'Accept-Encoding': 'gzip', 'If-None-Match': headers['ETag']})[:2], (304, b''))
            account = user('delivery-member', 'delivery@example.test', 'Delivery member')
            create_account(self.app, account)
            with self.app.connect() as conn:
                session = self.app.create_user_session(conn, account['user_id'])
            status, private_body, private = self.call(path, {'Cookie': 'cm_session=' + session, 'Accept-Encoding': 'gzip', 'If-None-Match': '*'})
            self.assertEqual(status, 200)
            self.assertIn(b'/logout', private_body)
            self.assertIn('no-store', private['Cache-Control'])
            self.assertNotIn('ETag', private)
            self.assertNotIn('Content-Encoding', private)
            with self.app.connect() as conn:
                conn.execute("update circle_public_profiles set is_published=0 where profile_id='delivery-test'")
            status, _, hidden = self.call(path, {'If-None-Match': '*', 'Accept-Encoding': 'gzip'})
            self.assertEqual(status, 404)
            self.assertIn('no-store', hidden['Cache-Control'])
            self.assertNotIn('ETag', hidden)
        finally:
            with self.app.connect() as conn:
                conn.execute("delete from circle_public_profiles where profile_id='delivery-test'")

    def test_binary_assets_and_error_pages_are_not_compressed_or_cached_as_documents(self):
        for path in ('/assets/circle-match-mark.png', '/signin', '/guides/not-an-article'):
            status, body, headers = self.call(path, {'Accept-Encoding': 'gzip'})
            self.assertNotIn('Content-Encoding', headers)
            if path.endswith('.png'):
                self.assertTrue(body.startswith(b'\x89PNG'))
            else:
                self.assertIn('no-store', headers['Cache-Control'])
                self.assertNotIn('ETag', headers)

    def test_new_route_groups_do_not_record_identifiers(self):
        self.assertEqual(delivery.route_group('/privacy?token=secret'), '/privacy')
        self.assertEqual(delivery.route_group('/terms'), '/terms')
        self.assertEqual(delivery.route_group('/signin?return_to=secret'), '/signin')
        self.assertEqual(delivery.route_group('/circles/private-looking-name?email=private@example.test'), '/circles/:profile')
        self.assertEqual(delivery.route_group('/invitations/secret'), '/other')
