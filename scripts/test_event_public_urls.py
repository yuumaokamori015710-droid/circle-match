"""Known malformed public share URLs recover without prefix matching or data changes."""
from unittest.mock import patch
from urllib.parse import parse_qs, quote, urlsplit

from test_event_flow import create_account, event_payload, user
from test_venues import IsolatedAppHttpCase


BROKEN_ID = 'event_user_supabase_fe23d660_0d10_49cc_ae6_'
CANONICAL_ID = 'event_user_supabase_fe23d660_0d10_49cc_ae6_f42c6bd8fd'


class PublicEventURLTests(IsolatedAppHttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.app.init_db()
        cls.host = user('public-url-host', 'urlhost@example.test', 'Host')
        create_account(cls.app, cls.host)

    def setUp(self):
        with self.app.connect() as conn:
            self.eid = self.app.save_event_post(conn, event_payload(self._testMethodName), self.host)
        self.alias = 'known_shared_link_' + self._testMethodName
        self.alias_patch = patch.dict(self.app.PUBLIC_EVENT_URL_ALIASES, {self.alias:self.eid})
        self.alias_patch.start()
        self.addCleanup(self.alias_patch.stop)

    def test_exact_reported_share_url_maps_to_existing_canonical_id(self):
        self.assertEqual(self.app.PUBLIC_EVENT_URL_ALIASES[BROKEN_ID], CANONICAL_ID)
        with patch.object(self.app, 'get_event', return_value={'event_id':CANONICAL_ID}):
            status, _, headers = self.request('/events/' + BROKEN_ID)
        self.assertEqual(status, 302)
        self.assertEqual(headers['Location'], '/events/' + CANONICAL_ID)
        self.assertNotIn('Set-Cookie', headers)

    def test_anonymous_alias_redirects_to_public_detail_without_altering_event(self):
        original = self.app.get_event(self.eid, include_private=True)
        status, _, headers = self.request('/events/' + self.alias)
        self.assertEqual(status, 302)
        self.assertEqual(headers['Location'], '/events/' + quote(self.eid, safe=''))
        result, body, _ = self.request(headers['Location'])
        self.assertEqual(result, 200)
        self.assertIn(self._testMethodName, body.decode())
        self.assertEqual(self.app.get_event(self.eid, include_private=True), original)

    def test_query_context_and_trailing_slash_are_preserved(self):
        query = '?return_to=%2Fevents%3Fsport%3Dtennis&tag=one&tag=two'
        status, _, headers = self.request('/events/' + self.alias + '/' + query)
        self.assertEqual(status, 302)
        target = urlsplit(headers['Location'])
        self.assertEqual(target.path, '/events/' + quote(self.eid, safe=''))
        self.assertEqual(parse_qs(target.query), {'return_to':['/events?sport=tennis'], 'tag':['one','two']})

    def test_drafts_missing_targets_and_unknown_prefixes_stay_unavailable(self):
        with self.app.connect() as conn:
            conn.execute("update event_posts set status='draft' where event_id=?", (self.eid,))
        self.assertEqual(self.request('/events/' + self.alias)[0], 404)
        with patch.dict(self.app.PUBLIC_EVENT_URL_ALIASES, {self.alias:'missing-event'}):
            self.assertEqual(self.request('/events/' + self.alias)[0], 404)
        self.assertEqual(self.request('/events/' + self.eid[:-5])[0], 404)
        self.assertEqual(self.request('/events/event_user_supabase_fe23d660_')[0], 404)

    def test_closed_and_cancelled_events_keep_their_public_status(self):
        for state in ('closed','cancelled'):
            with self.subTest(state=state):
                with self.app.connect() as conn:
                    conn.execute('update event_posts set status=? where event_id=?', (state,self.eid))
                status, _, headers = self.request('/events/' + self.alias)
                self.assertEqual(status, 302)
                self.assertEqual(self.request(headers['Location'])[0], 200)
                self.assertEqual(self.app.get_event(self.eid)['status'], state)

    def test_past_event_retains_details_with_a_clear_end_state_and_no_apply_cta(self):
        path = '/events/' + self.eid
        with self.app.connect() as conn:
            conn.execute("update event_posts set starts_at=?, ends_at=? where event_id=?",
                         ('2020-06-01 10:00', '2020-06-01 14:00', self.eid))
        for state in ('published', 'closed'):
            with self.subTest(state=state):
                with self.app.connect() as conn:
                    conn.execute('update event_posts set status=? where event_id=?', (state, self.eid))
                status, body, _ = self.request(path)
                page = body.decode()
                self.assertEqual(status, 200)
                self.assertIn(self._testMethodName, page)
                self.assertIn('このイベントは終了しました', page)
                self.assertIn('href="/events">開催予定のイベントを見る', page)
                self.assertNotIn('mobile-apply"', page)
                self.assertNotIn('会員登録なしで申し込む', page)
                self.assertNotIn(path, self.request('/sitemap.xml')[1].decode())
                self.assertNotIn(path, self.request('/events')[1].decode())

    def test_ongoing_cancelled_and_upcoming_are_not_mislabeled_as_ended(self):
        path = '/events/' + self.eid
        status, body, _ = self.request(path)
        self.assertEqual(status, 200)
        self.assertIn('ログインして参加を申し込む', body.decode())
        self.assertNotIn('このイベントは終了しました', body.decode())
        self.assertIn(path, self.request('/sitemap.xml')[1].decode())
        with self.app.connect() as conn:
            conn.execute("update event_posts set starts_at=? where event_id=?",
                         ('2020-06-01 10:00', self.eid))
        self.assertNotIn('このイベントは終了しました', self.request(path)[1].decode())
        with self.app.connect() as conn:
            conn.execute("update event_posts set status='cancelled',ends_at=? where event_id=?",
                         ('2020-06-01 14:00', self.eid))
        page = self.request(path)[1].decode()
        self.assertIn('開催中止', page)
        self.assertNotIn('このイベントは終了しました', page)

    def test_missing_and_deleted_details_are_real_404s_logged_without_queries(self):
        with self.app.connect() as conn:
            conn.execute('delete from event_posts where event_id=?', (self.eid,))
        for path in ('/events/event_missing_test', '/events/' + self.eid):
            with self.subTest(path=path):
                with patch.object(self.app, 'log', wraps=self.app.log) as log:
                    status, body, _ = self.request(path + '?token=do-not-log')
                page = body.decode()
                self.assertEqual(status, 404)
                self.assertIn('イベントが見つかりません', page)
                self.assertIn('href="/">トップへ戻る', page)
                self.assertIn('href="/events">開催予定のイベントを見る', page)
                self.assertIn('content="noindex, follow"', page)
                log.assert_any_call(f'event_detail_not_found path="{path}"')
                self.assertNotIn('do-not-log', str(log.call_args_list))

    def test_action_and_post_routes_do_not_resolve_aliases(self):
        status, _, headers = self.request('/events/' + self.alias + '/unknown')
        self.assertEqual(status, 404)
        self.assertNotIn('Location', headers)
        status, _, headers = self.request('/events/' + self.alias, method='POST')
        self.assertNotEqual(status, 302)
        self.assertNotIn('Location', headers)
