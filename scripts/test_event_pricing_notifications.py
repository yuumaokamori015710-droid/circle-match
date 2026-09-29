"""Pricing/privacy and the global inbox, using disposable users and SQLite only."""
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
from urllib.parse import quote

from test_event_flow import load_app, user, create_account, event_payload, request_json


class PricingNotificationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name) / "pricing.sqlite"
        self.app = load_app(self.path)
        self.app.init_db()
        self.app.EMAIL_NOTIFICATIONS_ENABLED = False
        self.host = user("host", "host@example.test", "Host")
        self.person = user("person", "person@example.test", "Participant")
        self.other = user("other", "other@example.test", "Other")
        self.sessions = {}
        for account in (self.host, self.person, self.other):
            create_account(self.app, account)
            with self.app.connect() as conn:
                self.sessions[account["user_id"]] = self.app.create_user_session(conn, account["user_id"])

    def tearDown(self):
        self.temp.cleanup()

    def save(self, **changes):
        payload = event_payload(self.id())
        payload.update(changes)
        with self.app.connect() as conn:
            return self.app.save_event_post(conn, payload, self.host)

    def test_fee_is_never_silently_overwritten_and_units_are_derived(self):
        eid = self.save(fee_amount=2500, participation_type="team", capacity_unit="人", fee_unit="bad")
        saved = self.app.get_event(eid)
        self.assertEqual((saved["fee_amount"], saved["fee_unit"], saved["capacity_unit"]), (2500, "1チーム", "チーム"))
        with self.assertRaisesRegex(ValueError, "参加費がある場合"):
            self.save(payment_method="free", fee_amount=2500)
        free = self.save(title="Free event", payment_method="free", fee_amount=0)
        self.assertEqual(self.app.get_event(free)["fee_amount"], 0)
        self.assertEqual(self.app.event_payment_label("free"), "-")
        draft = self.save(title="Paid draft", status="draft", payment_method="free", fee_amount=2500)
        with self.app.connect() as conn:
            self.assertEqual(self.app.event_owner(conn, draft, "host")["fee_amount"], 2500)
        for invalid in (-1, "1.5", 10000001, "nan"):
            with self.subTest(value=invalid), self.assertRaises(ValueError):
                self.save(fee_amount=invalid)

    def test_private_target_survives_edit_copy_and_is_not_public(self):
        eid = self.save(target_total_amount=987654321)
        with self.app.connect() as conn:
            self.app.submit_event_application(conn, eid, {
                "participation_type": "individual", "applicant_name": "Participant", "participant_count": 1,
            }, self.person)
            copied = self.app.event_copy_for_owner(conn, eid, self.host)
            self.assertEqual(copied["target_total_amount"], 987654321)
            with self.assertRaises(PermissionError):
                self.app.event_copy_for_owner(conn, eid, self.other)
        for data in (self.app.get_event(eid), self.app.search_events({}), self.app.event_my_page(self.person)):
            self.assertNotIn("target_total_amount", json.dumps(data))
            self.assertNotIn("987654321", json.dumps(data))
        for page in (self.app.render_event_detail_html(eid), self.app.render_event_detail_html(eid, self.person),
                     self.app.render_event_apply_html(eid, self.other), self.app.render_mypage_html(self.person)):
            self.assertNotIn("987654321", page)
            self.assertNotIn("損益分岐点", page)
        owner = self.app.render_event_form_html({"event_id": [eid]}, self.host)
        self.assertIn('"target_total_amount": 987654321', owner)
        self.assertIn("987,654,321円", self.app.render_mypage_html(self.host))
        count_before = len(self.app.notifications_for_user(self.person))
        self.save(event_id=eid, target_total_amount=123456)
        self.assertEqual(count_before, len(self.app.notifications_for_user(self.person)), "private edits must not notify participants")
        self.save(event_id=eid)  # Older clients omit the field.
        with self.app.connect() as conn:
            self.assertEqual(self.app.event_owner(conn, eid, "host")["target_total_amount"], 123456)
        self.save(event_id=eid, target_total_amount="")
        with self.app.connect() as conn:
            self.assertIsNone(self.app.event_owner(conn, eid, "host")["target_total_amount"])
        for invalid in (-1, "1.2", 1000000001, "NaN"):
            with self.subTest(value=invalid), self.assertRaises(ValueError):
                self.save(target_total_amount=invalid)

    def test_additive_migration_backs_up_legacy_rows_and_is_idempotent(self):
        eid = self.save()
        with closing(sqlite3.connect(self.path)) as conn, conn:
            conn.execute("alter table event_posts drop column target_total_amount")
        self.app.init_db()
        self.app.init_db()
        with self.app.connect() as conn:
            self.assertIsNone(self.app.event_owner(conn, eid, "host")["target_total_amount"])
            self.assertEqual(conn.execute("pragma foreign_key_check").fetchall(), [])
        backups = list(Path(self.temp.name).glob("*.pre-target-total-*.sqlite"))
        self.assertEqual(len(backups), 1)
        with closing(sqlite3.connect(backups[0])) as conn:
            self.assertEqual(conn.execute("select count(*) from event_posts where event_id=?", (eid,)).fetchone()[0], 1)
            self.assertNotIn("target_total_amount", {row[1] for row in conn.execute("pragma table_info(event_posts)")})

    def test_legacy_team_person_capacity_is_preserved_on_edit(self):
        eid = self.save(participation_type="team")
        with self.app.connect() as conn:
            conn.execute("update event_posts set capacity_unit='人',fee_unit='1人' where event_id=?", (eid,))
        self.save(event_id=eid, participation_type="team")
        saved = self.app.get_event(eid)
        self.assertEqual((saved["capacity_unit"], saved["fee_unit"]), ("人", "1人"))

    def test_fee_input_and_unit_sync_javascript(self):
        source = self.app.EVENT_FORM_SCRIPT
        unit = source[source.index("function syncCapacityUnit(){"):source.index("function fill(){")]
        payment = re.search(r"function normalizeFee\(value\)\{[^\n]+", source)[0] + "\n" + re.search(r"function syncPayment\(\)\{[^\n]+", source)[0]
        command = r'''
const assert=require('node:assert/strict'),vm=require('node:vm');
const code=JSON.parse(require('node:fs').readFileSync(0,'utf8'));
const fields=Object.fromEntries(['participation_type','capacity_unit','fee_unit','capacity','minimum_participants','fee_amount','payment_method','paymentHelp'].map(id=>[id,{value:'',labels:[{textContent:''}]}]));
const context=vm.createContext({$:id=>fields[id],persistedUnits:null});vm.runInContext(code,context);
for(const type of ['individual','team','both']){
fields.participation_type.value=type;fields.payment_method.value='free';vm.runInContext('syncCapacityUnit();syncPayment()',context);
assert.equal(fields.capacity_unit.value,type==='team'?'チーム':'人');assert.equal(fields.fee_unit.value,type==='team'?'1チーム':'1人');assert.equal(fields.fee_amount.disabled,false);assert.equal(fields.fee_amount.required,true);
}
context.persistedUnits={participation:'team',capacity:'人',fee:'1人'};fields.participation_type.value='team';vm.runInContext('syncCapacityUnit()',context);assert.equal(fields.capacity_unit.value,'人');assert.equal(fields.fee_unit.value,'1人');
fields.fee_amount.value='０';fields.payment_method.value='bank_transfer';vm.runInContext('syncPayment()',context);assert.equal(fields.payment_method.disabled,true);assert.equal(fields.payment_method.value,'bank_transfer');assert.equal(fields.paymentHelp.hidden,true);
fields.fee_amount.value='１，５００';vm.runInContext('syncPayment()',context);assert.equal(fields.payment_method.disabled,false);assert.equal(vm.runInContext('normalizeFee($("fee_amount").value)',context),'1500');
'''
        result = subprocess.run(["node", "-e", command], input=json.dumps(unit + payment), encoding="utf-8", capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_bell_inbox_scope_count_pagination_and_old_links(self):
        with self.app.connect() as conn:
            for i in range(51):
                self.app.add_event_notification(conn, "host", None, "test", f"Host notice {i}", "Private host body")
            other_id = self.app.add_event_notification(conn, "other", None, "test", "Other notice", "Other private body")
        server = ThreadingHTTPServer(("127.0.0.1", 0), self.app.Handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        base = f"http://127.0.0.1:{server.server_port}"
        cookie = "cm_session=" + self.sessions["host"]
        def get(path, account="host"):
            req = urllib.request.Request(base + path, headers={"Cookie": "cm_session=" + self.sessions.get(account, "")})
            with urllib.request.urlopen(req) as response:
                return response.geturl(), response.read().decode()
        try:
            for path in ("/", "/events", "/?tab=db", "/events/new", "/mypage", "/circles"):
                _, page = get(path)
                self.assertIn('id="notificationBell"', page)
                self.assertIn('aria-label="通知（未読51件）"', page)
                self.assertNotIn("Private host body", page)
            _, page = get("/mypage")
            self.assertNotIn('data-my-tab="notifications"', page)
            url, notes = get("/mypage?tab=notifications")
            self.assertEqual(url, base + "/notifications")
            self.assertEqual(notes.count('class="notification unread"'), 50)
            self.assertNotIn("Other private body", notes)
            self.assertEqual(get("/notifications?page=1")[1].count('class="notification unread"'), 1)
            url, _ = get("/notifications", "guest")
            self.assertIn("/signin?", url)
            with self.assertRaises(HTTPError) as result:
                request_json(base + "/api/notifications/unread")
            self.assertEqual(result.exception.code, 401)
            result.exception.close()
            ids = [n["notification_id"] for n in self.app.notifications_for_user(self.host)]
            _, state = request_json(base + "/api/notifications/read", "POST", {"notification_ids": ids}, cookie)
            self.assertEqual(state["unread_count"], 1)
            request_json(base + "/api/notifications/read", "POST", {"notification_ids": [other_id]}, cookie)
            self.assertEqual(self.app.unread_notification_count(self.other), 1)
            self.assertEqual(request_json(base + "/api/notifications/unread", cookie=cookie)[1]["unread_count"], 1)
        finally:
            server.shutdown()
            server.server_close()


if __name__ == "__main__":
    unittest.main()
