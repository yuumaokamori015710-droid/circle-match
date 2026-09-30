"""Private settlement, group amendments, reminders and pre-application questions."""
import json
import re
import sqlite3
import subprocess
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import datetime, timedelta
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from test_event_flow import load_app, user, create_account, event_payload, request_json


class OperationsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.path = Path(cls.temp.name) / 'operations.sqlite'
        cls.app = load_app(cls.path)
        cls.app.init_db()
        cls.app.EMAIL_NOTIFICATIONS_ENABLED = False
        cls.host = user('ops-host', 'host@example.test', '主催者')
        cls.people = [user('ops-person' + str(i), f'p{i}@example.test', '参加者' + str(i)) for i in range(4)]
        cls.sessions = {}
        for person in [cls.host, *cls.people]:
            create_account(cls.app, person)
            with cls.app.connect() as conn:
                cls.sessions[person['user_id']] = cls.app.create_user_session(conn, person['user_id'])

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def event(self, **changes):
        payload = event_payload(self.id(), capacity=6)
        payload.update(changes)
        with self.app.connect() as conn:
            return self.app.save_event_post(conn, payload, self.host)

    def apply(self, eid, person=0, count=2, team=False):
        with self.app.connect() as conn:
            return self.app.submit_event_application(conn, eid, dict(participation_type='team' if team else 'individual',
                participant_count=count, applicant_name='申込代表者', team_name='チーム', representative_name='代表者'), self.people[person])['application_id']

    def row(self, eid, person=0):
        return self.app.user_event_application(eid, self.people[person])

    def count(self, eid, aid, number, person=0, **extra):
        with self.app.connect() as conn:
            return self.app.change_application_count(conn, eid, aid, dict(revision=self.row(eid, person)['operation_revision'], participant_count=number, **extra), self.people[person])

    def payment(self, eid, aid, state, actor=None, **extra):
        data = dict(revision=self.row(eid)['operation_revision'], payment_status=state, payment_note='PRIVATE-LEDGER')
        data.update(extra)
        with self.app.connect() as conn:
            return self.app.set_application_payment(conn, eid, aid, data, actor or self.host)

    def announce(self, eid, **changes):
        payload = dict(version=0, starts_at='2030-06-01T10:00', location='確定会場', announcement_details='集合案内',
                       attendance_deadline='2030-05-29T18:00', payment_deadline='2030-05-31T18:00', bank_transfer_details='PRIVATE-ACCOUNT')
        payload.update(changes)
        with self.app.connect() as conn:
            self.app.announce_event(conn, eid, payload, self.host)

    def test_partial_group_reduction_and_capacity_preserves_original_on_failure(self):
        eid = self.event(capacity=4)
        aid = self.apply(eid, count=3)
        self.apply(eid, person=1, count=1)
        with self.assertRaisesRegex(ValueError, '定員'):
            self.count(eid, aid, 4)
        self.assertEqual(self.row(eid)['participant_count'], 3)
        self.assertEqual(self.count(eid, aid, 2), 'updated')
        self.assertEqual(self.row(eid)['status'], 'confirmed')
        with self.app.connect() as conn:
            self.assertEqual(self.app.active_confirmed_capacity(conn, eid), 3)
        with self.assertRaises(PermissionError), self.app.connect() as conn:
            self.app.change_application_count(conn, eid, aid, {'participant_count': 1, 'revision': 1}, self.people[1])
        with self.assertRaises(ValueError), self.app.connect() as conn:
            self.app.change_application_count(conn, eid, aid, {'participant_count': 1, 'revision': 0}, self.people[0])

    def test_approval_increase_requires_host_and_rechecks_capacity(self):
        eid = self.event(acceptance_mode='approval', capacity=4)
        aid = self.apply(eid)
        with self.app.connect() as conn:
            self.app.set_event_application_status(conn, eid, aid, 'confirm', self.host)
        self.assertEqual(self.count(eid, aid, 4), 'pending')
        self.assertEqual(self.row(eid)['participant_count'], 2)
        second = self.apply(eid, person=1)
        with self.app.connect() as conn:
            self.app.set_event_application_status(conn, eid, second, 'confirm', self.host)
        data = dict(revision=self.row(eid)['operation_revision'])
        with self.assertRaises(ValueError), self.app.connect() as conn:
            self.app.change_application_count(conn, eid, aid, data, self.host, 'approve')
        with self.assertRaises(PermissionError), self.app.connect() as conn:
            self.app.change_application_count(conn, eid, aid, data, self.people[1], 'approve')
        with self.app.connect() as conn:
            self.app.change_application_count(conn, eid, aid, data, self.host, 'decline')
        self.assertEqual(self.row(eid)['participant_count'], 2)
        self.assertIsNone(self.row(eid)['requested_participant_count'])
        self.count(eid, aid, 1)
        self.count(eid, aid, 2)
        with self.app.connect() as conn:
            self.app.change_application_count(conn, eid, aid, {'revision': self.row(eid)['operation_revision']}, self.host, 'approve')
        self.assertEqual(self.row(eid)['participant_count'], 2)

    def test_team_changes_do_not_consume_people_as_team_slots(self):
        eid = self.event(participation_type='team', capacity=2)
        aid = self.apply(eid, count=12, team=True)
        self.apply(eid, person=1, count=8, team=True)
        self.count(eid, aid, 15)
        with self.app.connect() as conn:
            self.assertEqual(self.app.active_confirmed_capacity(conn, eid), 2)

    def test_simultaneous_increases_cannot_exceed_capacity(self):
        eid = self.event(capacity=3)
        ids = [self.apply(eid, person=i, count=1) for i in range(2)]
        def change(i):
            try:
                self.count(eid, ids[i], 2, person=i)
                return True
            except ValueError:
                return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertEqual(sum(pool.map(change, range(2))), 1)
        with self.app.connect() as conn:
            self.assertEqual(self.app.active_confirmed_capacity(conn, eid), 3)

    def test_payment_permissions_privacy_settlement_and_stale_updates(self):
        eid = self.event()
        aid = self.apply(eid)
        with self.assertRaises(PermissionError):
            self.payment(eid, aid, 'paid', actor=self.people[0])
        with self.assertRaises(ValueError):
            self.payment(eid, aid, 'refunded')
        self.payment(eid, aid, 'paid')
        with self.assertRaises(ValueError):
            self.payment(eid, aid, 'unpaid', revision=0)
        with self.assertRaisesRegex(ValueError, '入金'):
            self.count(eid, aid, 1)
        for value in [self.app.get_event(eid), self.app.search_events({}), self.app.event_my_page(self.people[0])]:
            self.assertNotIn('PRIVATE-LEDGER', json.dumps(value))
        private = self.app.render_event_application_operations(eid, self.host, aid)
        self.assertIn('PRIVATE-LEDGER', private)
        own = self.app.render_event_application_operations(eid, self.people[0], aid)
        self.assertNotIn('PRIVATE-LEDGER', own)
        self.assertIn('入金確認済み', own)
        with self.app.connect() as conn:
            self.app.cancel_event_application(conn, eid, aid, self.people[0])
        self.assertEqual(self.row(eid)['payment_status'], 'refund_pending')
        with self.assertRaises(ValueError):
            self.apply(eid)
        self.payment(eid, aid, 'refunded')
        self.apply(eid)
        self.assertEqual(self.row(eid)['payment_status'], 'unpaid')
        self.assertEqual(self.row(eid)['payment_note'], '')

    def test_paid_event_fee_cannot_change_and_cancellation_flags_settlement(self):
        eid = self.event()
        aid = self.apply(eid)
        self.payment(eid, aid, 'paid')
        payload = event_payload(self.id(), capacity=6)
        payload.update(event_id=eid, fee_amount=5000)
        with self.assertRaises(ValueError), self.app.connect() as conn:
            self.app.save_event_post(conn, payload, self.host)
        with self.app.connect() as conn:
            self.app.set_event_status(conn, eid, 'cancelled', self.host)
        self.assertEqual(self.row(eid)['payment_status'], 'refund_pending')

    def test_confirmation_deadline_reconfirmation_and_payment_gate(self):
        eid = self.event(minimum_participants=1, payment_method='bank_transfer')
        aid = self.apply(eid)
        self.announce(eid)
        with self.assertRaises(ValueError):
            self.payment(eid, aid, 'paid')
        with self.app.connect() as conn:
            self.app.confirm_event_attendance(conn, eid, {'version': 1}, self.people[0])
        self.count(eid, aid, 1)
        self.assertEqual(self.row(eid)['attendance_version'], 0)
        with self.assertRaises(ValueError):
            self.announce(eid, version=1, attendance_deadline='2030-06-01T11:00')
        with self.app.connect() as conn:
            conn.execute("update event_posts set attendance_deadline='2020-01-01 00:00' where event_id=?", (eid,))
        with self.assertRaisesRegex(ValueError, '確認の期限'), self.app.connect() as conn:
            self.app.confirm_event_attendance(conn, eid, {'version': 1}, self.people[0])
        self.assertFalse(self.app.event_availability(self.app.get_event(eid))[1])
        with self.assertRaises(ValueError):
            self.apply(eid, person=1)

    def test_reminders_once_restart_safe_and_expiration_never_auto_cancels(self):
        eid = self.event(minimum_participants=1)
        aid = self.apply(eid)
        self.announce(eid)
        deadline = (datetime.strptime(self.app.event_local_now(), '%Y-%m-%d %H:%M') + timedelta(hours=1)).strftime('%Y-%m-%d %H:%M')
        with self.app.connect() as conn:
            conn.execute('update event_posts set attendance_deadline=? where event_id=?', (deadline, eid))
        self.app.process_attendance_reminders()
        self.app.process_attendance_reminders()
        self.app.init_db()
        self.app.process_attendance_reminders()
        with self.app.connect() as conn:
            self.assertEqual(conn.execute("select count(*) from event_notifications where event_id=? and notification_type='attendance_reminder'", (eid,)).fetchone()[0], 1)
            conn.execute("update event_posts set attendance_deadline='2020-01-01 00:00' where event_id=?", (eid,))
        self.app.process_attendance_reminders()
        self.app.process_attendance_reminders()
        self.assertEqual(self.row(eid)['status'], 'confirmed')
        with self.app.connect() as conn:
            self.assertEqual(conn.execute("select count(*) from event_notifications where event_id=? and notification_type='attendance_expired_host'", (eid,)).fetchone()[0], 1)
            self.app.release_unconfirmed_application(conn, eid, aid, dict(revision=self.row(eid)['operation_revision'], reason='連絡後も確認できないため'), self.host)
        self.assertEqual(self.row(eid)['status'], 'cancelled')

    def test_host_release_denied_before_expiration_and_for_paid_or_confirmed(self):
        eid = self.event(minimum_participants=1)
        aid = self.apply(eid)
        self.announce(eid)
        data = dict(revision=0, reason='理由')
        with self.assertRaises(ValueError), self.app.connect() as conn:
            self.app.release_unconfirmed_application(conn, eid, aid, data, self.host)
        with self.app.connect() as conn:
            self.app.confirm_event_attendance(conn, eid, {'version': 1}, self.people[0])
        self.payment(eid, aid, 'paid')
        with self.app.connect() as conn:
            conn.execute("update event_posts set attendance_deadline='2020-01-01 00:00' where event_id=?", (eid,))
        data['revision'] = self.row(eid)['operation_revision']
        with self.assertRaises(ValueError), self.app.connect() as conn:
            self.app.release_unconfirmed_application(conn, eid, aid, data, self.host)
        with self.assertRaises(PermissionError), self.app.connect() as conn:
            self.app.release_unconfirmed_application(conn, eid, aid, data, self.people[0])

    def test_pre_application_questions_are_private_and_reachable(self):
        eid = self.event()
        self.assertIn('主催者に質問する', self.app.render_event_detail_html(eid))
        with self.app.connect() as conn:
            self.app.send_event_message(conn, eid, {'body': '道具は必要ですか？'}, self.people[0])
            self.app.send_event_message(conn, eid, {'body': '貸出あり', 'recipient_user_id': self.people[0]['user_id']}, self.host)
        self.assertIsNone(self.row(eid))
        self.assertEqual(self.app.event_messages_for_user(eid, self.people[1]), [])
        with self.assertRaises(PermissionError):
            self.app.event_messages_for_user(eid, self.people[1], self.people[0]['user_id'])
        with self.assertRaises(PermissionError), self.app.connect() as conn:
            self.app.send_event_message(conn, eid, {'body': '不可', 'recipient_user_id': self.people[1]['user_id']}, self.host)
        self.assertIn('貸出あり', self.app.render_event_contact_html(eid, self.people[0]))
        self.assertIn('申込前の質問・連絡', self.app.render_mypage_html(self.people[0]))
        self.assertNotIn('道具は必要ですか', self.app.render_event_detail_html(eid))
        self.assertIn('/contact', self.app.render_notifications_html(self.people[0]))
        with self.app.connect() as conn:
            self.app.set_event_status(conn, eid, 'cancelled', self.host)
        with self.assertRaises(PermissionError), self.app.connect() as conn:
            self.app.send_event_message(conn, eid, {'body': '新規質問'}, self.people[1])
        with self.app.connect() as conn:
            self.app.send_event_message(conn, eid, {'body': '中止後の確認'}, self.people[0])

    def test_question_rate_limit_draft_protection_and_escaping(self):
        eid = self.event()
        person = self.people[3]
        for i in range(10):
            with self.app.connect() as conn:
                self.app.send_event_message(conn, eid, {'body': '<script>alert(1)</script>'}, person)
        with self.assertRaisesRegex(ValueError, '送信が続'), self.app.connect() as conn:
            self.app.send_event_message(conn, eid, {'body': '11'}, person)
        self.assertIn('&lt;script&gt;', self.app.render_event_contact_html(eid, person))
        draft = self.event(status='draft', title='Private draft')
        with self.assertRaises(PermissionError):
            self.app.render_event_contact_html(draft, self.people[2])

    def test_http_access_csrf_and_javascript(self):
        eid = self.event()
        aid = self.apply(eid)
        server = ThreadingHTTPServer(('127.0.0.1', 0), self.app.Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f'http://127.0.0.1:{server.server_port}'
        cookie = lambda who: 'cm_session=' + self.sessions[who['user_id']]
        try:
            for headers, expected in [
                ({'Content-Type': 'application/json', 'Origin': 'https://untrusted.example'}, 403),
                ({'Content-Type': 'application/json', 'Sec-Fetch-Site': 'cross-site'}, 403),
                ({'Content-Type': 'text/plain'}, 400),
            ]:
                req = Request(base + f'/api/events/{eid}/applications/{aid}/count',
                              data=b'{"revision":0,"participant_count":1}',
                              headers={'Cookie': cookie(self.people[0]), **headers}, method='POST')
                with self.assertRaises(HTTPError) as error:
                    urlopen(req)
                self.assertEqual(error.exception.code, expected)
                error.exception.close()
            for suffix, actor, payload, expected in [
                ('count', None, {}, 401), ('count', self.people[1], {'revision': 0, 'participant_count': 1}, 403),
                ('payment', self.people[0], {'revision': 0, 'payment_status': 'paid'}, 403),
                ('count', self.people[0], {'revision': 0, 'participant_count': 1}, 200),
                ('payment', self.host, {'revision': 1, 'payment_status': 'paid'}, 200),
            ]:
                url = base + f'/api/events/{eid}/applications/{aid}/{suffix}'
                if expected == 200:
                    self.assertEqual(request_json(url, 'POST', payload, cookie(actor))[0], expected)
                else:
                    with self.assertRaises(HTTPError) as error:
                        request_json(url, 'POST', payload, cookie(actor) if actor else '')
                    self.assertEqual(error.exception.code, expected)
                    error.exception.close()
            for actor, suffix, expected in [(self.host, '/applications', 200), (self.people[0], '/applications/' + aid, 200), (self.people[1], '/applications/' + aid, 403), (self.people[1], '/applications', 403), (self.people[2], '/contact', 200)]:
                req = Request(base + '/events/' + eid + suffix, headers={'Cookie': cookie(actor)})
                if expected == 200:
                    with urlopen(req) as response:
                        self.assertIn('no-store', response.headers['Cache-Control'])
                        page = response.read().decode()
                    for script in re.findall(r'<script>(.*?)</script>', page, re.S):
                        result = subprocess.run(['node', '--check'], input=script, encoding='utf-8', capture_output=True)
                        self.assertEqual(result.returncode, 0, result.stderr)
                else:
                    with self.assertRaises(HTTPError) as error:
                        urlopen(req)
                    self.assertEqual(error.exception.code, expected)
                    error.exception.close()
        finally:
            server.shutdown()
            server.server_close()

    def test_migration_preserves_data_and_backup_is_valid(self):
        eid = self.event()
        aid = self.apply(eid)
        with closing(sqlite3.connect(self.path)) as conn, conn:
            conn.execute('alter table event_applications drop column payment_note')
        before = set(self.path.parent.glob('*.pre-operations-*.sqlite'))
        self.app.init_db()
        self.app.init_db()
        backups = set(self.path.parent.glob('*.pre-operations-*.sqlite')) - before
        self.assertEqual(len(backups), 1)
        with closing(sqlite3.connect(backups.pop())) as conn:
            self.assertEqual(conn.execute('pragma integrity_check').fetchone()[0], 'ok')
            self.assertTrue(conn.execute('select 1 from event_applications where application_id=?', (aid,)).fetchone())
        self.assertEqual(self.row(eid)['payment_note'], '')


if __name__ == '__main__':
    unittest.main()
