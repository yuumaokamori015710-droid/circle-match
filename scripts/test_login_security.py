"""Login observations with disposable accounts and mocked providers; no real email."""
import io
import json
import secrets
import tempfile
import threading
import time
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from test_event_flow import load_app, user, create_account


class LoginSecurityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.app = load_app(Path(cls.temp.name)/'login-security.sqlite')
        cls.app.init_db()
        cls.server = ThreadingHTTPServer(('127.0.0.1',0),cls.app.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever,daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.temp.cleanup()

    def setUp(self):
        self.uid = 'login_'+secrets.token_hex(8)
        self.account = user(self.uid,self.uid+'@example.test','テスト利用者')
        create_account(self.app,self.account)
        setting = patch.multiple(self.app,EMAIL_NOTIFICATIONS_ENABLED=True,RESEND_API_KEY='test-only-not-a-key',
                                 EMAIL_FROM='Circle Match <notifications@example.test>',SITE_BASE_URL=self.base,
                                 SUPABASE_URL='https://project.example.test',SUPABASE_ANON_KEY='public-test-key')
        setting.start()
        self.addCleanup(setting.stop)

    def notify(self, proof='verified-provider-proof', **kwargs):
        with self.app.connect() as conn:
            return self.app.login_security.record_login(conn,self.uid,'supabase_email',proof,self.app.SESSION_SECRET,
                                                       self.app.add_event_notification,self.app.audit,**kwargs)

    def notes(self):
        return self.app.notifications_for_user(self.account)

    def request(self,path,*,data=None,cookie=''):
        headers = {'Cookie':cookie} if cookie else {}
        if data is not None:
            headers['Content-Type'] = 'application/json'
        return urlopen(Request(self.base+path,data=json.dumps(data).encode() if data is not None else None,headers=headers),timeout=10)

    def enable_https_mail(self):
        self.app.SITE_BASE_URL = 'https://circle-match.example'

    def test_success_notification_has_time_and_verified_recipient_only(self):
        self.enable_https_mail()
        with patch.object(self.app,'urlopen',side_effect=AssertionError('request-time network send')):
            self.notify()
        notes = self.notes()
        self.assertEqual(len(notes),1)
        self.assertEqual(notes[0]['notification_type'],'login_success')
        self.assertIn('JST',notes[0]['body'])
        self.assertIn('メール認証',notes[0]['body'])
        with self.app.connect() as conn:
            payload = json.loads(conn.execute('select payload_json from event_email_outbox where notification_id=?',(notes[0]['notification_id'],)).fetchone()[0])
        self.assertEqual(payload['to'],[self.account['email']])
        self.assertIn('https://circle-match.example/settings/security',payload['text'])
        self.assertNotIn('verified-provider-proof',json.dumps(payload))

    def test_repeated_exchange_has_one_login_mail_and_one_alert(self):
        self.enable_https_mail()
        for _ in range(12):
            self.notify('same-session-proof')
        kinds = [row['notification_type'] for row in self.notes()]
        self.assertEqual(kinds.count('login_success'),1)
        self.assertEqual(kinds.count('login_security_alert'),1)
        with self.app.connect() as conn:
            events = self.app.login_security.recent_events(conn,self.uid)
        self.assertIn('exchange_burst',[row['kind'] for row in events])

    def test_distinct_logins_detected_without_denying_a_session(self):
        for number in range(6):
            self.notify(str(number))
        self.assertEqual(sum(row['notification_type']=='login_security_alert' for row in self.notes()),1)
        with self.app.connect() as conn:
            events = self.app.login_security.recent_events(conn,self.uid)
            session = self.app.create_user_session(conn,self.uid)
        self.assertIn('rapid_logins',[row['kind'] for row in events])
        self.assertTrue(self.app.current_user(session)['authenticated'])

    def test_unconfigured_mail_is_honest_and_not_retroactively_queued(self):
        self.app.EMAIL_NOTIFICATIONS_ENABLED = False
        self.notify()
        self.assertEqual(self.notes()[0]['email_status'],'not_configured')
        self.app.EMAIL_NOTIFICATIONS_ENABLED = True
        self.enable_https_mail()
        with self.app.connect() as conn:
            self.assertIsNone(conn.execute('select 1 from event_email_outbox where notification_id=?',(self.notes()[0]['notification_id'],)).fetchone())

    def test_unverified_email_gets_in_app_only_without_changing_auth(self):
        self.enable_https_mail()
        self.notify(email_allowed=False)
        self.assertEqual(self.notes()[0]['email_status'],'not_configured')
        with self.app.connect() as conn:
            self.assertIsNone(conn.execute('select 1 from event_email_outbox where notification_id=?',(self.notes()[0]['notification_id'],)).fetchone())

    def test_observer_failure_keeps_session_and_rolls_back_partial_notes(self):
        def broken_notify(*args,**kwargs):
            self.app.add_event_notification(*args,**kwargs)
            raise RuntimeError('private provider error')
        messages = []
        with self.app.connect() as conn:
            session = self.app.create_user_session(conn,self.uid)
            result = self.app.login_security.observe_login(conn,self.uid,'google','proof',self.app.SESSION_SECRET,
                                                          broken_notify,self.app.audit,messages.append)
        self.assertIsNone(result)
        self.assertTrue(self.app.current_user(session)['authenticated'])
        self.assertEqual(self.notes(),[])
        self.assertNotIn('private provider error',' '.join(messages))

    def test_rollback_never_queues_a_login_mail(self):
        self.enable_https_mail()
        with self.assertRaises(RuntimeError), self.app.connect() as conn:
            self.app.login_security.record_login(conn,self.uid,'google','proof',self.app.SESSION_SECRET,
                                                 self.app.add_event_notification,self.app.audit)
            raise RuntimeError('cancel transaction')
        self.assertEqual(self.notes(),[])

    def test_no_schema_changes_or_raw_network_and_token_storage(self):
        peer,token = '203.0.113.61','raw-login-secret-that-must-not-be-stored'
        with self.app.connect() as conn:
            before = list(conn.execute('select name,sql from sqlite_master order by name'))
            conn.execute('begin immediate')
            for _ in range(7):
                self.app.login_security.record_failure(conn,self.app.SESSION_SECRET,peer,'supabase',self.app.audit)
        self.notify(token)
        with self.app.connect() as conn:
            self.assertEqual(before,list(conn.execute('select name,sql from sqlite_master order by name')))
            persisted = json.dumps([tuple(row) for row in conn.execute("select state_key,state_value from app_state where state_key like 'login-security:%'")])
            persisted += json.dumps([tuple(row) for row in conn.execute("select entity_id,payload from audit_logs where action='login_security'")])
        self.assertNotIn(peer,persisted)
        self.assertNotIn(token,persisted)

    def test_failed_auth_burst_is_operator_only_and_has_no_account_lockout(self):
        with self.app.connect() as conn:
            conn.execute('begin immediate')
            results = [self.app.login_security.record_failure(conn,self.app.SESSION_SECRET,self.uid,'supabase',self.app.audit) for _ in range(8)]
            events = self.app.login_security.recent_events(conn)
        self.assertEqual(results.count(True),1)
        self.assertIn('failure_burst',[row['kind'] for row in events])
        self.assertEqual(self.notes(),[])
        self.notify('subsequent-verified-login')
        self.assertEqual(self.notes()[0]['notification_type'],'login_success')

    def test_pruning_preserves_other_audit_state_and_notifications(self):
        self.notify()
        with self.app.connect() as conn:
            conn.execute("insert into app_state values('unrelated-old-setting','{}','2000-01-01')")
            conn.execute("insert into app_state values('login-security:proof:obsolete','{}','2000-01-01')")
            self.app.audit(conn,'unrelated_audit','test','keep',{})
            self.app.audit(conn,'login_security','user',self.uid,{'kind':'login_success','method':'google','occurred_at':0,'count':1})
            conn.execute("update audit_logs set created_at='2000-01-01' where entity_id=? and action='login_security'",(self.uid,))
            self.app.login_security.prune(conn)
            self.assertIsNotNone(conn.execute("select 1 from app_state where state_key='unrelated-old-setting'").fetchone())
            self.assertIsNone(conn.execute("select 1 from app_state where state_key='login-security:proof:obsolete'").fetchone())
            self.assertIsNotNone(conn.execute("select 1 from audit_logs where action='unrelated_audit'").fetchone())
        self.assertEqual(len(self.notes()),1)

    def test_private_history_does_not_expose_another_user_or_proofs(self):
        self.notify()
        with self.app.connect() as conn:
            self.assertEqual(self.app.login_security.recent_events(conn,'someone-else'),[])
            page = self.app.login_security.render(self.app.login_security.recent_events(conn,self.uid),1,False)
            session = self.app.create_user_session(conn,self.uid)
        with self.request('/settings/security',cookie='cm_session='+session) as response:
            self.assertIn('no-store',response.headers['Cache-Control'])
            self.assertIn('ログイン成功',response.read().decode())
        with self.request('/settings/security') as response:
            self.assertIn('/signin',response.url)
        self.assertIn('メール配信は未設定',page)
        self.assertNotIn('verified-provider-proof',page)

    def test_admin_history_requires_existing_admin_auth(self):
        with self.assertRaises(HTTPError) as error:
            self.request('/admin/security')
        self.assertEqual(error.exception.code,401)
        error.exception.close()
        with patch.object(self.app,'ADMIN_PASSWORD',''):
            with self.assertRaises(HTTPError) as error:
                self.request('/admin/security')
            self.assertEqual(error.exception.code,503)
            error.exception.close()

    def test_supabase_verified_login_is_observed_and_refresh_read_is_not(self):
        profile = dict(id=self.uid,email=self.account['email'],email_confirmed_at='2026-01-01',
                       last_sign_in_at='2026-11-02T00:00:00Z',app_metadata={'provider':'google'},
                       user_metadata={'email':'attacker@example.test','full_name':'Member'})
        with patch.object(self.app,'fetch_supabase_user',return_value=profile):
            with self.request('/api/auth/supabase',data={'access_token':'test-access'}) as response:
                result = json.loads(response.read())
                cookie = response.headers['Set-Cookie'].split(';')[0]
        account = result['user']
        self.assertTrue(account['authenticated'])
        notes = self.app.notifications_for_user(account)
        self.assertEqual(len(notes),1)
        self.assertIn('Google',notes[0]['body'])
        for _ in range(3):
            with self.request('/api/me',cookie=cookie) as response:
                self.assertTrue(json.loads(response.read())['authenticated'])
        self.assertEqual(len(self.app.notifications_for_user(account)),1)

    def test_upstream_rejected_token_does_not_notify_unverified_email(self):
        error = HTTPError('https://project.example.test/auth/v1/user',401,'Unauthorized',{},io.BytesIO())
        with patch.object(self.app,'fetch_supabase_user',side_effect=error):
            with self.assertRaises(HTTPError) as caught:
                self.request('/api/auth/supabase',data={'access_token':'bad-token'})
            caught.exception.close()
        self.assertEqual(self.notes(),[])

    def test_provider_outage_is_not_classified_as_a_failed_authentication(self):
        with self.app.connect() as conn:
            before = conn.execute("select count(*) from app_state where state_key like 'login-security:counter:failure:%'").fetchone()[0]
        error = HTTPError('https://project.example.test/auth/v1/user',503,'Unavailable',{},io.BytesIO())
        with patch.object(self.app,'fetch_supabase_user',side_effect=error):
            with self.assertRaises(HTTPError) as caught:
                self.request('/api/auth/supabase',data={'access_token':'valid-provider-token'})
            caught.exception.close()
        with self.app.connect() as conn:
            self.assertEqual(before,conn.execute("select count(*) from app_state where state_key like 'login-security:counter:failure:%'").fetchone()[0])

    def test_legacy_google_login_policy_is_unchanged(self):
        profile = dict(sub=self.uid,email=self.account['email'],name='Member',email_verified=False)
        with patch.multiple(self.app,GOOGLE_CLIENT_ID='test-client',GOOGLE_CLIENT_SECRET='test-secret'):
            state = self.app.make_oauth_state()
            with patch.object(self.app,'post_form',return_value={'access_token':'test-google-access'}), patch.object(self.app,'fetch_json',return_value=profile):
                with self.request('/auth/google/callback?code=test-code&state='+state,cookie='cm_oauth_state='+state) as response:
                    self.assertEqual(response.status,200)
        with self.app.connect() as conn:
            account = conn.execute("select user_id from user_accounts where provider='google' and provider_subject=?",(self.uid,)).fetchone()
            note = conn.execute("select notification_id from event_notifications where recipient_user_id=? and notification_type='login_success'",(account['user_id'],)).fetchone()
            self.assertIsNotNone(note)
            self.assertIsNone(conn.execute('select 1 from event_email_outbox where notification_id=?',(note['notification_id'],)).fetchone())

    def test_notification_route_links_to_private_security_history(self):
        self.notify()
        page = self.app.render_notifications_html(self.account)
        self.assertIn('href="/settings/security"',page)
        self.assertNotIn('verified-provider-proof',page)


if __name__ == '__main__':
    unittest.main()
