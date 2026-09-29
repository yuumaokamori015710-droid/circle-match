"""Formation, announcement, attendance and private payment data. No real mail."""
import json
import re
import sqlite3
import subprocess
import tempfile
import threading
import unittest
import urllib.request
from contextlib import closing
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError

from test_event_flow import load_app, user, create_account, event_payload, request_json


class FormationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.path = Path(cls.temp.name) / "formation.sqlite"
        cls.app = load_app(cls.path)
        cls.app.init_db()
        cls.app.EMAIL_NOTIFICATIONS_ENABLED = False
        cls.host = user("host", "host@example.test", "Host")
        cls.people = [user(f"person{i}", f"p{i}@example.test", f"Person {i}") for i in range(3)]
        cls.sessions = {}
        for account in [cls.host, *cls.people]:
            create_account(cls.app, account)
            with cls.app.connect() as conn:
                cls.sessions[account["user_id"]] = cls.app.create_user_session(conn, account["user_id"])

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def event(self, **changes):
        payload = event_payload(self.id(), capacity=4)
        payload.update(minimum_participants=2, target_total_amount="３，５００", payment_method="bank_transfer")
        payload.update(changes)
        with self.app.connect() as conn:
            return self.app.save_event_post(conn, payload, self.host)

    def apply(self, eid, person=0, count=1, team=False):
        with self.app.connect() as conn:
            return self.app.submit_event_application(conn, eid, {
                "participation_type": "team" if team else "individual", "applicant_name": "Person",
                "participant_count": count, "team_name": "Test team", "representative_name": "Representative",
            }, self.people[person])

    def announce(self, eid, account=None, **changes):
        data = dict(version=0, starts_at="2030-06-01T10:00", location="確定会場",
                    announcement_details="集合は入口。持ち物は運動靴。", bank_transfer_details="PRIVATE-ACCOUNT-1234567",
                    payment_deadline="2030-05-31T18:00")
        data.update(changes)
        with self.app.connect() as conn:
            return self.app.announce_event(conn, eid, data, account or self.host)

    def confirm(self, eid, person=0, version=1):
        with self.app.connect() as conn:
            self.app.confirm_event_attendance(conn, eid, {"version": version}, self.people[person])

    def notes(self, account, eid, kind):
        with self.app.connect() as conn:
            return [dict(r) for r in conn.execute("select * from event_notifications where recipient_user_id=? and event_id=? and notification_type=?", (account["user_id"], eid, kind))]

    def test_threshold_group_then_announcement_attendance_payment_privacy(self):
        eid = self.event()
        with self.assertRaisesRegex(ValueError, "最低開催"):
            self.announce(eid)
        self.apply(eid, count=2)
        self.assertEqual(len(self.notes(self.host, eid, "event_provisional")), 1)
        with self.app.connect() as conn:
            self.app.update_event_formation(conn, eid)
        self.assertEqual(len(self.notes(self.host, eid, "event_provisional")), 1)
        self.assertIn("受付確定・開催決定待ち", self.app.render_mypage_html(self.people[0]))
        self.announce(eid)
        self.assertEqual(self.announce(eid, version=1), 1)  # Identical retry, no duplicate mail.
        self.assertEqual(len(self.notes(self.people[0], eid, "event_announced")), 1)
        self.assertNotIn("PRIVATE-ACCOUNT", self.app.render_event_attendance_html(eid, self.people[0]))
        with self.assertRaises(PermissionError):
            self.app.render_event_attendance_html(eid, self.people[1])
        self.confirm(eid)
        self.confirm(eid)
        self.assertEqual(len(self.notes(self.host, eid, "attendance_confirmed")), 1)
        private = self.app.render_event_attendance_html(eid, self.people[0])
        self.assertIn("PRIVATE-ACCOUNT", private)
        self.assertIn("2,000円", private)
        for data in (self.app.get_event(eid), self.app.search_events({}), self.app.event_my_page(self.people[0]), self.notes(self.people[0], eid, "event_announced")):
            self.assertNotIn("PRIVATE-ACCOUNT", json.dumps(data))
            self.assertNotIn("target_total_amount", json.dumps(data))
        self.assertIn("+500円", self.app.render_mypage_html(self.host))
        self.assertNotIn("損益分岐点", self.app.render_mypage_html(self.people[0]))
        markup, script = self.app.event_share_dialog(self.app.get_event(eid))
        self.assertNotIn("PRIVATE-ACCOUNT", markup + script)
        self.assertNotIn("target_total_amount", markup + script)

    def test_approval_counts_teams_not_people_pending_excluded_and_drop_alert(self):
        eid = self.event(acceptance_mode="approval", participation_type="team")
        first = self.apply(eid, count=12, team=True)
        second = self.apply(eid, 1, 8, True)
        self.assertFalse(self.notes(self.host, eid, "event_provisional"))
        with self.app.connect() as conn:
            self.app.set_event_application_status(conn, eid, first["application_id"], "confirm", self.host)
        self.assertFalse(self.notes(self.host, eid, "event_provisional"))
        with self.app.connect() as conn:
            self.app.set_event_application_status(conn, eid, second["application_id"], "confirm", self.host)
        self.assertEqual(len(self.notes(self.host, eid, "event_provisional")), 1)
        self.announce(eid)
        self.confirm(eid)
        self.assertIn("お支払額：1,000円", self.app.render_event_attendance_html(eid, self.people[0]))
        with self.app.connect() as conn:
            self.app.cancel_event_application(conn, eid, first["application_id"], self.people[0])
        self.assertEqual(len(self.notes(self.host, eid, "event_below_minimum")), 1)
        self.assertNotIn("PRIVATE-ACCOUNT", self.app.render_event_attendance_html(eid, self.people[0]))
        with self.assertRaises(PermissionError):
            self.confirm(eid)
        self.apply(eid, count=12, team=True)
        self.assertEqual(self.app.user_event_application(eid, self.people[0])["attendance_version"], 0)

    def test_permissions_versions_updates_cancellation_and_deadlines(self):
        eid = self.event()
        self.apply(eid, count=2)
        with self.assertRaises(PermissionError):
            self.announce(eid, self.people[0])
        with self.assertRaises(ValueError):
            self.announce(eid, bank_transfer_details="")
        with self.assertRaises(ValueError):
            self.announce(eid, payment_deadline="2020-01-01T10:00")
        self.announce(eid)
        with self.assertRaises(ValueError):
            self.confirm(eid, version=0)
        with self.assertRaises(PermissionError):
            self.confirm(eid, person=1)
        self.confirm(eid)
        self.announce(eid, version=1, location="変更後の会場")
        self.assertNotIn("PRIVATE-ACCOUNT", self.app.render_event_attendance_html(eid, self.people[0]))
        with self.assertRaises(ValueError):
            self.confirm(eid, version=1)
        self.confirm(eid, version=2)
        with self.assertRaisesRegex(ValueError, "振込先"):
            self.announce(eid, version=2, bank_transfer_details="different")
        with self.app.connect() as conn:
            copied = self.app.event_copy_for_owner(conn, eid, self.host)
            self.assertNotIn("bank_transfer_details", copied)
            self.assertNotIn("announcement_version", copied)
        with self.app.connect() as conn:
            self.app.set_event_status(conn, eid, "cancelled", self.host)
        with self.assertRaises(ValueError):
            self.confirm(eid, version=2)
        self.assertNotIn("PRIVATE-ACCOUNT", self.app.render_event_attendance_html(eid, self.people[0]))

    def test_form_share_and_new_pages_javascript(self):
        eid = self.event()
        self.apply(eid, count=2)
        form = self.app.render_event_form_html({}, self.host)
        self.assertIn('id="target_total_amount" type="text" inputmode="numeric"', form)
        self.assertIn("損益分岐点 [円]（任意）", form)
        self.assertNotIn('<option value="free">', form)
        pages = [form, self.app.render_event_organize_html(eid, self.host)]
        self.announce(eid)
        pages.append(self.app.render_event_attendance_html(eid, self.people[0]))
        for page in pages:
            for script in re.findall(r"<script>(.*?)</script>", page, re.S):
                result = subprocess.run(["node", "--check"], input=script, encoding="utf-8", capture_output=True)
                self.assertEqual(result.returncode, 0, result.stderr)
        for invalid in ("1.5", "0", -1, 100001):
            with self.assertRaises(ValueError):
                self.event(title=str(invalid), minimum_participants=invalid)
        with self.assertRaises(ValueError):
            self.event(minimum_participants=5, capacity=4)

    def test_notifications_use_existing_outbox_without_private_account_data(self):
        eid = self.event()
        self.apply(eid, count=2)
        previous = (self.app.EMAIL_NOTIFICATIONS_ENABLED, self.app.RESEND_API_KEY, self.app.EMAIL_FROM, self.app.SITE_BASE_URL)
        try:
            self.app.EMAIL_NOTIFICATIONS_ENABLED = True
            self.app.RESEND_API_KEY = "local-test-not-a-key"
            self.app.EMAIL_FROM = "Circle Match <notify@example.test>"
            self.app.SITE_BASE_URL = "https://example.test"
            self.announce(eid)
            with self.app.connect() as conn:
                jobs = conn.execute("select payload_json from event_email_outbox o join event_notifications n using(notification_id) where n.event_id=? and n.notification_type='event_announced'", (eid,)).fetchall()
                self.assertEqual(len(jobs), 1)
                body = json.loads(jobs[0]["payload_json"])["text"]
                self.assertIn("確定会場", body)
                self.assertIn("最終参加確認", body)
                self.assertNotIn("PRIVATE-ACCOUNT", body)
        finally:
            self.app.EMAIL_NOTIFICATIONS_ENABLED, self.app.RESEND_API_KEY, self.app.EMAIL_FROM, self.app.SITE_BASE_URL = previous

    def test_legacy_migration_is_additive_backed_up_and_idempotent(self):
        eid = self.event()
        application = self.apply(eid)
        with closing(sqlite3.connect(self.path)) as conn, conn:
            for column in ("minimum_participants", "minimum_notice_sent", "announcement_version", "announcement_details", "announced_at", "bank_transfer_details", "payment_deadline"):
                conn.execute(f"alter table event_posts drop column {column}")
            for column in ("attendance_version", "attendance_confirmed_at"):
                conn.execute(f"alter table event_applications drop column {column}")
        backups_before = set(self.path.parent.glob("*.pre-formation-*.sqlite"))
        self.app.init_db()
        self.app.init_db()
        backups = set(self.path.parent.glob("*.pre-formation-*.sqlite")) - backups_before
        self.assertEqual(len(backups), 1)
        with closing(sqlite3.connect(backups.pop())) as backup:
            self.assertEqual(backup.execute("pragma integrity_check").fetchone()[0], "ok")
            self.assertTrue(backup.execute("select 1 from event_applications where application_id=?", (application["application_id"],)).fetchone())
            self.assertNotIn("minimum_participants", {row[1] for row in backup.execute("pragma table_info(event_posts)")})
        self.assertEqual(self.app.get_event(eid)["minimum_participants"], 0)
        with self.app.connect() as conn:
            self.assertEqual(conn.execute("pragma foreign_key_check").fetchall(), [])
        self.assertIn("参加確定", self.app.render_mypage_html(self.people[0]))

    def test_payment_deadline_blocks_new_admission_and_confirmation(self):
        eid = self.event()
        self.apply(eid, count=2)
        self.announce(eid)
        with self.app.connect() as conn:
            conn.execute("update event_posts set payment_deadline='2020-01-01 10:00' where event_id=?", (eid,))
        with self.assertRaisesRegex(ValueError, "振込期限"):
            self.apply(eid, person=1)
        with self.assertRaisesRegex(ValueError, "振込期限"):
            self.confirm(eid)
        self.assertFalse(self.app.event_availability(self.app.get_event(eid))[1])

    def test_http_workflow_and_cross_user_protection(self):
        eid = self.event()
        self.apply(eid, count=2)
        server = ThreadingHTTPServer(("127.0.0.1", 0), self.app.Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{server.server_port}"
        cookie = lambda who: "cm_session=" + self.sessions[who["user_id"]]
        try:
            for who, expected in ((None, 401), (self.people[0], 403)):
                with self.assertRaises(HTTPError) as error:
                    request_json(base + f"/api/events/{eid}/announce", "POST", {}, cookie(who) if who else "")
                self.assertEqual(error.exception.code, expected)
                error.exception.close()
            payload = dict(version=0, starts_at="2030-06-01T10:00", location="会場", announcement_details="案内",
                           bank_transfer_details="PRIVATE-ACCOUNT", payment_deadline="2030-05-31T10:00")
            self.assertEqual(request_json(base + f"/api/events/{eid}/announce", "POST", payload, cookie(self.host))[0], 200)
            self.assertEqual(request_json(base + f"/api/events/{eid}/attendance", "POST", {"version": 1}, cookie(self.people[0]))[0], 200)
            request = urllib.request.Request(base + f"/events/{eid}/attendance", headers={"Cookie": cookie(self.people[1])})
            with self.assertRaises(HTTPError) as error:
                urllib.request.urlopen(request)
            self.assertEqual(error.exception.code, 403)
            error.exception.close()
            request = urllib.request.Request(base + f"/events/{eid}/attendance", headers={"Cookie": cookie(self.people[0])})
            with urllib.request.urlopen(request) as response:
                self.assertIn("no-store", response.headers.get("Cache-Control", ""))
                self.assertIn("PRIVATE-ACCOUNT", response.read().decode())
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
