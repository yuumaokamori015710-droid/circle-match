"""Capacity, host messaging and persistent email outbox regression tests.

All accounts/databases are temporary; provider calls are mocked. No real mail.
"""
import io
import hashlib
import json
import tempfile
import threading
import time
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

from test_event_flow import load_app, user, create_account, event_payload


class EventRegressionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.app = load_app(Path(cls.temp.name) / "regression.sqlite")
        cls.host = user("host", "host@example.test", "主催者")
        cls.people = [user(f"p{i}", f"p{i}@example.test", f"参加者{i}") for i in range(4)]
        for account in [cls.host, *cls.people]:
            create_account(cls.app, account)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def setUp(self):
        self.app.EMAIL_NOTIFICATIONS_ENABLED = False

    def make_event(self, mode="first_come", participation="team", capacity=2):
        data = event_payload(self.id() + participation, mode, participation, str(capacity))
        with self.app.connect() as conn:
            return self.app.save_event_post(conn, data, self.host)

    def apply(self, event_id, person=0, count=10, participation="team"):
        with self.app.connect() as conn:
            return self.app.submit_event_application(conn, event_id, {
                "participation_type": participation, "team_name": "テストチーム",
                "representative_name": "代表者", "participant_count": count,
                "applicant_name": "個人参加者",
            }, self.people[person])

    def test_two_ten_person_teams_fill_two_team_slots(self):
        event_id = self.make_event()
        first = self.apply(event_id)
        self.apply(event_id, 1)
        self.assertEqual(self.app.get_event(event_id)["confirmed_count"], 2)
        hosted = self.app.event_my_page(self.host)["hosted"]
        self.assertEqual(next(e for e in hosted if e["event_id"] == event_id)["confirmed_count"], 2)
        self.assertIn("2 / 2チーム", self.app.render_event_detail_html(event_id))
        with self.assertRaisesRegex(ValueError, "定員"):
            self.apply(event_id, 2)
        with self.app.connect() as conn:
            self.app.cancel_event_application(conn, event_id, first["application_id"], self.people[0])
        self.apply(event_id, 2)
        self.assertEqual(self.app.get_event(event_id)["confirmed_count"], 2)
        notices = self.app.event_my_page(self.host)["notifications"]
        self.assertTrue(any("1チーム（10名）" in n["body"] for n in notices))

    def test_approval_counts_teams_not_roster(self):
        event_id = self.make_event(mode="approval", capacity=1)
        first = self.apply(event_id, 0, count=20)
        second = self.apply(event_id, 1, count=3)
        self.assertEqual(self.app.get_event(event_id)["confirmed_count"], 0)
        with self.app.connect() as conn:
            self.app.set_event_application_status(conn, event_id, first["application_id"], "confirm", self.host)
        with self.assertRaisesRegex(ValueError, "定員"), self.app.connect() as conn:
            self.app.set_event_application_status(conn, event_id, second["application_id"], "confirm", self.host)
        self.assertEqual(self.app.get_event(event_id)["confirmed_count"], 1)

    def test_concurrent_last_team_slot(self):
        event_id = self.make_event(capacity=1)
        barrier = threading.Barrier(2)
        def submit(person):
            barrier.wait(timeout=5)
            try:
                return self.apply(event_id, person)["status"]
            except ValueError:
                return "full"
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(submit, [0, 1]))
        self.assertCountEqual(results, ["confirmed", "full"])
        self.assertEqual(self.app.get_event(event_id)["confirmed_count"], 1)

    def test_individual_and_mixed_capacity_and_edit_guard(self):
        event_id = self.make_event(participation="both", capacity=3)
        self.apply(event_id, 0, count=2)
        self.apply(event_id, 1, count=1, participation="individual")
        with self.assertRaisesRegex(ValueError, "定員"):
            self.apply(event_id, 2, count=1, participation="individual")
        self.assertEqual(self.app.get_event(event_id)["confirmed_count"], 3)
        edit = event_payload(self.id(), participation_type="both", capacity="2")
        edit["event_id"] = event_id
        with self.assertRaisesRegex(ValueError, "定員"), self.app.connect() as conn:
            self.app.save_event_post(conn, edit, self.host)
        edit.update(capacity="4", participation_type="team", capacity_unit="チーム")
        with self.assertRaisesRegex(ValueError, "変更できません"), self.app.connect() as conn:
            self.app.save_event_post(conn, edit, self.host)
        individual = self.make_event(participation="individual")
        self.apply(individual, count=2, participation="individual")
        self.assertEqual(self.app.get_event(individual)["confirmed_count"], 2)

    def test_host_pane_messages_and_access(self):
        event_id = self.make_event()
        self.apply(event_id)
        with self.app.connect() as conn:
            self.app.send_event_message(conn, event_id, {"recipient_user_id": "p0", "body": "集合場所のお知らせ"}, self.host)
        self.assertEqual(self.app.event_messages_for_user(event_id, self.people[0])[0]["body"], "集合場所のお知らせ")
        self.assertIn(f'id="messages-{event_id}"', self.app.render_mypage_html(self.host))
        with self.assertRaises(PermissionError):
            self.app.event_messages_for_user(event_id, self.people[1])
        with self.assertRaises(PermissionError), self.app.connect() as conn:
            self.app.send_event_message(conn, event_id, {"body": "部外者"}, self.people[1])
        with self.assertRaises(PermissionError):
            self.app.event_messages_for_user(event_id, self.host, "p1")

    def configure_email(self):
        self.app.EMAIL_NOTIFICATIONS_ENABLED = True
        self.app.RESEND_API_KEY = "test-secret-never-render"
        self.app.EMAIL_FROM = "Circle Match <notifications@example.test>"
        self.app.SITE_BASE_URL = "https://circle-match.example"
        with self.app.connect() as conn:
            conn.execute("delete from event_email_outbox")

    def enqueue(self):
        with self.app.connect() as conn:
            return self.app.add_event_notification(conn, "p0", None, "test", "テスト通知", "アプリ内でご確認ください")

    def job(self, notification_id):
        with self.app.connect() as conn:
            return dict(conn.execute("select * from event_email_outbox where notification_id=?", (notification_id,)).fetchone())

    def test_unconfigured_and_rollback_never_send(self):
        self.enqueue()
        with patch.object(self.app, "urlopen") as remote:
            self.assertFalse(self.app.process_event_email())
            remote.assert_not_called()
        self.configure_email()
        with self.assertRaises(ValueError), self.app.connect() as conn:
            self.app.add_event_notification(conn, "p0", None, "rollback", "ロールバック", "送信しない")
            raise ValueError("rollback")
        with self.app.connect() as conn:
            self.assertEqual(conn.execute("select count(*) from event_email_outbox").fetchone()[0], 0)

    def test_email_provider_acceptance_and_retry_uses_same_payload(self):
        self.configure_email()
        notification_id = self.enqueue()
        self.assertEqual(self.job(notification_id)["status"], "queued")
        with patch.object(self.app, "urlopen", side_effect=HTTPError("https://api.resend.com/emails", 503, "down", {}, None)):
            self.assertTrue(self.app.process_event_email())
        self.assertEqual(self.job(notification_id)["status"], "retry")
        with self.app.connect() as conn:
            conn.execute("update event_email_outbox set next_attempt_at=0")
        def accepted(request, timeout):
            self.assertEqual(timeout, 15)
            self.assertEqual(request.get_header("User-agent"), "CircleMatch/1.0 (+https://circle-match.jp)")
            self.assertEqual(request.get_header("Accept"), "application/json")
            self.assertEqual(request.get_header("Idempotency-key"), "circlematch-notification/" + hashlib.sha256(notification_id.encode()).hexdigest())
            payload = json.loads(request.data)
            self.assertEqual(payload["to"], ["p0@example.test"])
            self.assertIn("/notifications", payload["text"])
            # Network calls must not hold the SQLite write lock.
            with self.app.connect() as conn:
                conn.execute("begin immediate")
            return io.BytesIO(b'{"id":"provider-test-id"}')
        with patch.object(self.app, "urlopen", side_effect=accepted) as remote:
            self.assertTrue(self.app.process_event_email())
            self.assertFalse(self.app.process_event_email())
            self.assertEqual(remote.call_count, 1)
        job = self.job(notification_id)
        self.assertEqual(job["status"], "sent")
        self.assertEqual(job["attempts"], 2)
        self.assertEqual(job["provider_id"], "provider-test-id")
        self.assertNotIn("test-secret-never-render", self.app.render_mypage_html(self.people[0]))

    def test_permanent_error_and_expired_uncertain_job(self):
        self.configure_email()
        notification_id = self.enqueue()
        with patch.object(self.app, "urlopen", side_effect=HTTPError("https://api.resend.com/emails", 401, "credential", {}, None)):
            self.app.process_event_email()
        self.assertEqual(self.job(notification_id)["status"], "failed")
        second = self.enqueue()
        with self.app.connect() as conn:
            conn.execute("update event_email_outbox set status='sending',attempts=1,lease_until=0,first_attempt_at=? where notification_id=?", (int(time.time())-86400, second))
        with patch.object(self.app, "urlopen") as remote:
            self.app.process_event_email()
            remote.assert_not_called()
        self.assertEqual(self.job(second)["status"], "failed")

    def test_event_changes_and_decisions_enqueue_notifications(self):
        self.configure_email()
        event_id = self.make_event(mode="approval")
        first = self.apply(event_id)
        second = self.apply(event_id, 1)
        with self.app.connect() as conn:
            self.app.set_event_application_status(conn, event_id, first["application_id"], "confirm", self.host)
        with self.app.connect() as conn:
            self.app.set_event_application_status(conn, event_id, second["application_id"], "decline", self.host)
        edit = event_payload(self.id(), "approval", "team", "2")
        edit.update(event_id=event_id, location="変更した会場")
        with self.app.connect() as conn:
            self.app.save_event_post(conn, edit, self.host)
        with self.app.connect() as conn:
            self.app.set_event_status(conn, event_id, "cancelled", self.host)
            self.app.cancel_event_application(conn, event_id, first["application_id"], self.people[0])
        with self.app.connect() as conn:
            types = {r[0] for r in conn.execute("""select n.notification_type from event_notifications n
                join event_email_outbox o on o.notification_id=n.notification_id where n.event_id=?""", (event_id,))}
            count = conn.execute("select count(*) from event_email_outbox").fetchone()[0]
            self.app.set_event_status(conn, event_id, "cancelled", self.host)
            self.assertEqual(conn.execute("select count(*) from event_email_outbox").fetchone()[0], count)
        self.assertTrue({"new_application", "application_received", "application_confirmed",
                         "application_declined", "event_updated", "event_cancelled",
                         "application_cancelled", "cancellation_received"}.issubset(types))

    def test_verified_email_login_only(self):
        profile = {"id": "email-only-user", "email": "login@example.test"}
        with self.assertRaisesRegex(ValueError, "確認"), self.app.connect() as conn:
            self.app.upsert_supabase_user(conn, profile)
        profile["email_confirmed_at"] = self.app.now()
        with self.app.connect() as conn:
            uid = self.app.upsert_supabase_user(conn, profile)
            session = self.app.create_user_session(conn, uid)
        self.assertEqual(self.app.current_user(session)["email"], profile["email"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
