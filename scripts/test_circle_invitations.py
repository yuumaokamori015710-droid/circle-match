"""Invitation privacy, authorization and races; disposable DB and loopback only."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
import importlib.util
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import Request

from test_event_flow import create_account, event_payload, user
from test_venues import IsolatedAppHttpCase, PublicPage


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "circlematch_invitations_under_test", ROOT / "outputs" / "circlematch_invitations.py"
)
invitations = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(invitations)
PUBLIC_CLAUSE = """(coalesce(c.public_status,'published')<>'demo' and not exists
    (select 1 from circle_listing_reviews lr where lr.circle_id=c.circle_id
     and lr.review_status='pending'))"""


class CircleInvitationDomainTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=ROOT / "work")
        self.addCleanup(self.temp.cleanup)
        self.database = Path(self.temp.name) / "invitations.sqlite"
        self.host = user("host", "host-private@example.test", "Host account name")
        self.peer = user("peer", "peer-private@example.test", "Peer account name")
        self.other = user("outsider", "outsider-private@example.test", "Outsider")
        self.guest = {"authenticated": False}
        with self.connect() as conn:
            conn.executescript("""
                create table user_accounts(user_id text primary key,email text);
                create table universities(university_id text primary key,university_name text,prefecture text);
                create table circles(circle_id text primary key,university_id text,circle_name text,
                    sport_category text,source_url text,public_status text);
                create table circle_public_profiles(circle_id text,profile_slug text,is_published integer,
                    public_contact_consent integer,public_contact_email text);
                create table circle_listing_reviews(circle_id text,review_status text);
                create table circle_claims(circle_id text,claimant_email text,university_email_verified integer);
                create table event_posts(event_id text primary key,title text,organizer_user_id text,
                    status text,starts_at text,application_deadline text,capacity integer,confirmed_count integer);
                create table event_applications(application_id text,event_id text,applicant_user_id text,status text);
                create table event_notifications(notification_id text primary key,recipient_user_id text,
                    event_id text,notification_type text,title text,body text,email_status text,created_at text);
                create table event_email_outbox(notification_id text,payload_json text);
            """)
            invitations.init_schema(conn)
            conn.executemany("insert into user_accounts values(?,?)", [
                (p["user_id"], p["email"]) for p in (self.host, self.peer, self.other)
            ])
            conn.execute("insert into universities values('u','Test University','東京都')")
            conn.executemany("insert into circles values(?, 'u', ?, 'テニス', 'https://official.example/circle', ?)", [
                ("visible", "公開サークル", "published"),
                ("demo", "デモ団体", "demo"),
                ("review", "審査中団体", "published"),
            ])
            conn.execute("insert into circle_listing_reviews values('review','pending')")
            conn.execute("insert into circle_public_profiles values('visible','public-profile',1,0,'unconsented-private@example.test')")
            future = (datetime.now(timezone.utc) + timedelta(days=7)).isoformat()
            conn.execute("insert into event_posts values('event','Public exchange','host','published',?,?,10,0)", (future, future))

    @contextmanager
    def connect(self):
        conn = sqlite3.connect(self.database, timeout=10)
        conn.row_factory = sqlite3.Row
        conn.execute("pragma foreign_keys=on")
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    @staticmethod
    def event_check(conn, event_id, user_id=None):
        row = conn.execute("select * from event_posts where event_id=?", (event_id,)).fetchone()
        if not row:
            return None
        item = dict(row)
        now = datetime.now(timezone.utc).isoformat()
        if (item["status"] != "published" or item["starts_at"] <= now
                or item["application_deadline"] <= now
                or item["confirmed_count"] >= item["capacity"]
                or (user_id is not None and item["organizer_user_id"] != user_id)):
            return None
        return item

    @staticmethod
    def payload(**changes):
        result = {"target_circle_id": "visible", "kind": "consultation", "subject": "合同練習のご相談",
                  "sender_label": "招待側の表示名", "activity": "合同練習", "proposed_date": "来月の週末",
                  "location": "東京都内", "body": "交流について相談したいです。"}
        result.update(changes)
        return result

    @staticmethod
    def response(**changes):
        result = {"response": "interested", "affiliation_confirmed": True,
                  "display_name": "招待先関係者の自己申告名", "body": "日程を相談したいです。"}
        result.update(changes)
        return result

    def create(self, **changes):
        with self.connect() as conn:
            return invitations.create(conn, self.payload(**changes), self.host, PUBLIC_CLAUSE, self.event_check)

    def details(self, iid, person=None):
        with self.connect() as conn:
            return invitations.detail(conn, iid, person or self.guest, self.event_check)

    def reply(self, iid, person=None, **changes):
        with self.connect() as conn:
            return invitations.respond(conn, iid, self.response(**changes), person or self.peer)

    def count(self, table):
        with self.connect() as conn:
            return conn.execute("select count(*) from " + table).fetchone()[0]

    def assert_no_account_leak(self, value):
        encoded = json.dumps(value, ensure_ascii=False)
        for text in ("host-private@example.test", "peer-private@example.test", "outsider-private@example.test",
                     "unconsented-private@example.test", '"sender_user_id"', '"recipient_user_id"'):
            self.assertNotIn(text, encoded)

    def test_schema_is_idempotent_and_public_target_projection_is_small(self):
        with self.connect() as conn:
            invitations.init_schema(conn)
            actual = invitations.target(conn, "visible", PUBLIC_CLAUSE)
        self.assertEqual(actual["circle_id"], "visible")
        self.assertEqual(actual["profile_url"], "/circles/public-profile")
        self.assertEqual(actual["public_contact_email"], "")
        self.assert_no_account_leak(actual)

    def test_nonpublic_demo_pending_and_unknown_target_are_rejected(self):
        for circle in ("demo", "review", "does-not-exist"):
            with self.subTest(circle=circle), self.assertRaises(ValueError):
                self.create(target_circle_id=circle)
        self.assertEqual(self.count("circle_invitations"), 0)

    def test_guest_can_read_intro_without_account_or_discussion_data(self):
        iid = self.create()
        detail = self.details(iid)
        self.assertRegex(iid, r"^[A-Za-z0-9_-]{32}$")
        self.assertEqual(detail["subject"], self.payload()["subject"])
        self.assertEqual(detail["body"], self.payload()["body"])
        self.assertEqual(detail["messages"], [])
        self.assertEqual(detail["reply_name"], "")
        self.assertFalse(detail["is_sender"])
        self.assertFalse(detail["can_message"])
        self.assert_no_account_leak(detail)
        self.assertNotEqual(iid, self.create())

    def test_create_uses_server_owned_identity_and_fixed_expiry(self):
        iid = self.create(sender_user_id="outsider", recipient_user_id="outsider", status="interested",
                          target_circle_name="Forged target", expires_at="2099-01-01T00:00:00+00:00")
        with self.connect() as conn:
            row = invitations.row_for(conn, iid)
        self.assertEqual(row["sender_user_id"], "host")
        self.assertIsNone(row["recipient_user_id"])
        self.assertEqual(row["status"], "pending")
        self.assertEqual(row["target_circle_name"], "公開サークル")
        ttl = datetime.fromisoformat(row["expires_at"]) - datetime.fromisoformat(row["created_at"])
        self.assertLess(abs(ttl.total_seconds() - 30 * 86400), 2)

    def test_event_invite_requires_own_available_public_event(self):
        iid = self.create(kind="event", event_id="event")
        self.assertTrue(self.details(iid)["event_available"])
        with self.connect() as conn:
            conn.execute("update event_posts set organizer_user_id='outsider' where event_id='event'")
        with self.assertRaises(ValueError):
            self.create(kind="event", event_id="event")
        self.assertEqual(self.count("circle_invitations"), 1)

    def test_draft_closed_cancelled_full_expired_or_unknown_event_is_rejected(self):
        changes = [("status", "draft"), ("status", "closed"), ("status", "cancelled"),
                   ("confirmed_count", 10), ("application_deadline", "2000-01-01T00:00:00+00:00"),
                   ("starts_at", "2000-01-01T00:00:00+00:00")]
        for key, value in changes:
            with self.subTest(key=key, value=value):
                with self.connect() as conn:
                    old = conn.execute("select " + key + " from event_posts where event_id='event'").fetchone()[0]
                    conn.execute("update event_posts set " + key + "=? where event_id='event'", (value,))
                try:
                    with self.assertRaises(ValueError):
                        self.create(kind="event", event_id="event")
                finally:
                    with self.connect() as conn:
                        conn.execute("update event_posts set " + key + "=? where event_id='event'", (old,))
        with self.assertRaises(ValueError):
            self.create(kind="event", event_id="missing")

    def test_event_closure_after_link_creation_removes_event_action(self):
        iid = self.create(kind="event", event_id="event")
        with self.connect() as conn:
            conn.execute("update event_posts set status='closed' where event_id='event'")
        detail = self.details(iid)
        self.assertFalse(detail["event_available"])
        self.assertEqual(detail["event_url"], "")
        self.assertEqual(detail["event_title"], "")

    def test_respond_requires_login_and_explicit_boolean_affiliation(self):
        iid = self.create()
        with self.assertRaises(PermissionError), self.connect() as conn:
            invitations.respond(conn, iid, self.response(), self.guest)
        for value in (False, None, 1, "true", "yes"):
            with self.subTest(value=value), self.assertRaises(ValueError):
                self.reply(iid, affiliation_confirmed=value)
        with self.assertRaises(PermissionError):
            self.reply(iid, person=self.host)
        self.assertEqual(self.details(iid)["status"], "pending")

    def test_anonymous_cannot_create_send_or_withdraw(self):
        iid = self.create()
        with self.assertRaises(PermissionError), self.connect() as conn:
            invitations.create(conn, self.payload(), self.guest, PUBLIC_CLAUSE, self.event_check)
        with self.assertRaises(PermissionError), self.connect() as conn:
            invitations.message(conn, iid, {"body": "anonymous"}, self.guest)
        with self.assertRaises(PermissionError), self.connect() as conn:
            invitations.withdraw(conn, iid, self.guest)
        self.assertEqual(self.details(iid)["status"], "pending")

    def test_response_is_personal_no_circle_claim_application_capacity_or_email(self):
        iid = self.create(kind="event", event_id="event")
        self.assertEqual(self.reply(iid), "interested")
        self.assertEqual(self.count("circle_claims"), 0)
        self.assertEqual(self.count("event_applications"), 0)
        self.assertEqual(self.count("event_email_outbox"), 0)
        with self.connect() as conn:
            self.assertEqual(conn.execute("select confirmed_count from event_posts").fetchone()[0], 0)
            note = conn.execute("select * from event_notifications").fetchone()
        self.assertEqual(note["recipient_user_id"], "host")
        self.assertIsNone(note["event_id"])
        self.assertEqual(note["notification_type"], "circle_invitation")
        self.assertEqual(note["email_status"], "not_configured")

    def test_duplicate_response_is_idempotent_and_other_account_cannot_claim(self):
        iid = self.create()
        self.assertEqual(self.reply(iid), "interested")
        self.assertEqual(self.reply(iid, response="declined", body="Duplicate body"), "interested")
        self.assertEqual(self.count("circle_invitation_messages"), 1)
        self.assertEqual(self.count("event_notifications"), 1)
        with self.assertRaises(PermissionError):
            self.reply(iid, person=self.other)

    def test_simultaneous_first_replies_have_exactly_one_recipient(self):
        iid = self.create()
        barrier = threading.Barrier(2)
        def attempt(person):
            barrier.wait(timeout=5)
            try:
                return person["user_id"], self.reply(iid, person=person)
            except PermissionError:
                return person["user_id"], "forbidden"
        with ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(attempt, (self.peer, self.other)))
        self.assertCountEqual([result for _, result in results], ["interested", "forbidden"])
        winner = next(uid for uid, result in results if result == "interested")
        with self.connect() as conn:
            self.assertEqual(invitations.row_for(conn, iid)["recipient_user_id"], winner)
        self.assertEqual(self.count("event_notifications"), 1)
        self.assertEqual(self.count("circle_invitation_messages"), 1)

    def test_discussion_is_visible_only_to_the_two_accounts(self):
        iid = self.create()
        self.reply(iid, body="Private first reply")
        with self.connect() as conn:
            invitations.message(conn, iid, {"body": "Private host reply"}, self.host)
        for person in (self.host, self.peer):
            detail = self.details(iid, person)
            self.assertEqual([m["body"] for m in detail["messages"]], ["Private first reply", "Private host reply"])
            self.assertEqual([m["is_self"] for m in detail["messages"]], [person == self.peer, person == self.host])
            self.assert_no_account_leak(detail)
        for person in (self.guest, self.other):
            detail = self.details(iid, person)
            self.assertEqual(detail["messages"], [])
            self.assertEqual(detail["reply_name"], "")
            self.assertFalse(detail["can_message"])
            self.assert_no_account_leak(detail)
            with self.assertRaises(PermissionError), self.connect() as conn:
                invitations.message(conn, iid, {"body": "intrusion"}, person)
        self.assertEqual(self.count("event_email_outbox"), 0)

    def test_no_discussion_before_response_and_sender_only_withdrawal(self):
        iid = self.create()
        with self.assertRaises(ValueError), self.connect() as conn:
            invitations.message(conn, iid, {"body": "Too early"}, self.host)
        with self.assertRaises(PermissionError), self.connect() as conn:
            invitations.withdraw(conn, iid, self.other)
        with self.connect() as conn:
            invitations.withdraw(conn, iid, self.host)
        with self.assertRaises(ValueError):
            self.reply(iid)
        self.assertEqual(self.count("circle_invitation_messages"), 0)

    def test_withdrawn_or_expired_link_redacts_guest_content_and_stops_actions(self):
        for state in ("withdrawn", "expired"):
            with self.subTest(state=state):
                iid = self.create(kind="event", event_id="event")
                self.reply(iid, body="Private history")
                with self.connect() as conn:
                    if state == "withdrawn":
                        invitations.withdraw(conn, iid, self.host)
                    else:
                        conn.execute("update circle_invitations set expires_at='2000-01-01T00:00:00+00:00' where invitation_id=?", (iid,))
                for person in (self.guest, self.other):
                    detail = self.details(iid, person)
                    self.assertEqual(detail["status"], state)
                    for key in ("body", "sender_label", "proposed_date", "location", "subject", "target_circle_name", "event_url", "reply_name"):
                        self.assertEqual(detail[key], "", key)
                    self.assertEqual(detail["messages"], [])
                    self.assertFalse(detail["can_respond"])
                    self.assertFalse(detail["can_message"])
                self.assertEqual(self.details(iid, self.host)["messages"][0]["body"], "Private history")
                with self.assertRaises(ValueError), self.connect() as conn:
                    invitations.message(conn, iid, {"body": "After end"}, self.host)

    def test_listing_is_account_scoped_and_anonymous_is_forbidden(self):
        iid = self.create()
        self.reply(iid)
        with self.connect() as conn:
            self.assertEqual([i["invitation_id"] for i in invitations.listing(conn, self.host, self.event_check)], [iid])
            self.assertEqual([i["invitation_id"] for i in invitations.listing(conn, self.peer, self.event_check)], [iid])
            self.assertEqual(invitations.listing(conn, self.other, self.event_check), [])
            with self.assertRaises(PermissionError):
                invitations.listing(conn, self.guest, self.event_check)

    def test_validation_rejects_wrong_json_types_oversize_controls_and_unknown_choices(self):
        for changes in ({"subject": True}, {"body": {"nested": "value"}}, {"subject": "x" * 121},
                        {"body": "x" * 2001}, {"sender_label": "\x00bad"}, {"activity": "unknown"},
                        {"kind": "unknown"}, {"subject": " "}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.create(**changes)
        self.assertEqual(self.count("circle_invitations"), 0)
        for malformed in (None, [], "text", True, 123):
            with self.subTest(malformed=malformed), self.assertRaises(ValueError), self.connect() as conn:
                invitations.create(conn, malformed, self.host, PUBLIC_CLAUSE, self.event_check)

    def test_daily_creation_and_conversation_message_limits(self):
        ids = [self.create() for _ in range(50)]
        with self.assertRaises(ValueError):
            self.create()
        self.reply(ids[0], body="")
        with self.connect() as conn:
            conn.executemany("insert into circle_invitation_messages(invitation_id,sender_user_id,display_name,body,created_at) values(?,?,?,?,?)", [
                (ids[0], "host", "Host", "old message", "2000-01-01T00:00:00+00:00") for _ in range(200)
            ])
        with self.assertRaises(ValueError), self.connect() as conn:
            invitations.message(conn, ids[0], {"body": "Message 201"}, self.peer)


class CircleInvitationHttpTests(IsolatedAppHttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.host = user("invitation-http-host", "http-host-private@example.test", "Private host profile")
        cls.peer = user("invitation-http-peer", "http-peer-private@example.test", "Private peer profile")
        cls.other = user("invitation-http-other", "http-other-private@example.test", "Private outsider profile")
        cls.cookies = {}
        for person in (cls.host, cls.peer, cls.other):
            create_account(cls.app, person)
            with cls.app.connect() as conn:
                cls.cookies[person["user_id"]] = "cm_session=" + cls.app.create_user_session(conn, person["user_id"])
        with cls.app.connect() as conn:
            university = cls.app.upsert_university(conn, {"university_name": "招待境界検証大学", "prefecture": "東京都"}, audit=False)
            cls.circle = cls.app.upsert_circle(conn, {
                "university_id": university, "circle_name": "招待境界検証テニス同好会", "sport_category": "テニス",
                "source_type": "university_official", "source_url": "https://official.example/circle",
                "verification_status": "unverified", "public_status": "published",
            })
            cls.app.upsert_circle_public_profile(conn, cls.circle, {
                "public_contact_email": "unconsented-http-private@example.test", "public_contact_consent": False,
                "introduction": "招待境界の検証用団体です。",
            })

    def send(self, path, method="GET", payload=None, actor=None, headers=None, raw=None):
        request_headers = {"Accept": "application/json"}
        if actor is not None:
            request_headers["Cookie"] = self.cookies[actor["user_id"]]
        if method == "POST":
            request_headers.update({"Content-Type": "application/json", "Origin": self.base})
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if raw is None else raw
        else:
            data = None
        request_headers.update(headers or {})
        req = Request(self.base + quote(path, safe="/?=&%:#"), data=data, method=method, headers=request_headers)
        try:
            response = self.opener.open(req, timeout=10)
        except HTTPError as error:
            response = error
        with response:
            return response.status, response.read(), response.headers

    def payload(self, **changes):
        result = CircleInvitationDomainTests.payload(target_circle_id=self.circle,
                    subject="招待HTTP検証 " + self.id().rsplit(".", 1)[-1][-50:])
        result.update(changes)
        return result

    def create(self, **changes):
        code, body, _ = self.send("/api/invitations", "POST", self.payload(**changes), self.host)
        self.assertEqual(code, 200, body.decode("utf-8"))
        return json.loads(body)["invitation_id"]

    def reply(self, iid, **changes):
        return self.send("/api/invitations/" + iid + "/respond", "POST",
                         CircleInvitationDomainTests.response(**changes), self.peer)

    def event(self, **changes):
        payload = event_payload("招待用イベント " + self.id().rsplit(".", 1)[-1], capacity="10")
        payload.update(changes)
        with self.app.connect() as conn:
            return self.app.save_event_post(conn, payload, self.host)

    def assert_private_identity_absent(self, page):
        for private in (self.host["email"], self.peer["email"], self.other["email"],
                        self.host["user_id"], self.peer["user_id"], self.other["user_id"],
                        "unconsented-http-private@example.test"):
            self.assertNotIn(private, page)

    def test_anonymous_preview_login_redirects_and_write_authentication(self):
        iid = self.create()
        for path in ("/invitations", "/invitations/new?circle_id=" + self.circle):
            code, _, headers = self.send(path)
            self.assertEqual(code, 302)
            self.assertTrue(headers["Location"].startswith("/signin?return_to="))
        code, body, _ = self.send("/invitations/" + iid)
        self.assertEqual(code, 200)
        self.assertIn("ログインして返信する", body.decode())
        self.assertIn("return_to=%2Finvitations%2F" + iid, body.decode())
        for path, payload in (("/api/invitations", self.payload()),
                              ("/api/invitations/" + iid + "/respond", CircleInvitationDomainTests.response()),
                              ("/api/invitations/" + iid + "/message", {"body": "guest"}),
                              ("/api/invitations/" + iid + "/withdraw", {})):
            with self.subTest(path=path):
                self.assertEqual(self.send(path, "POST", payload)[0], 401)

    def test_link_preview_has_noindex_no_referrer_no_ad_or_identity_leak(self):
        iid = self.create()
        code, body, headers = self.send("/invitations/" + iid)
        self.assertEqual(code, 200)
        page = body.decode()
        metadata = PublicPage(page).meta
        self.assertIn("noindex", metadata["robots"])
        self.assertEqual(metadata["referrer"], "no-referrer")
        self.assertIn("no-store", headers["Cache-Control"])
        self.assertNotIn("pagead2.googlesyndication.com", page)
        self.assertNotIn("adsbygoogle", page)
        self.assert_private_identity_absent(page)

    def test_http_reply_discussion_does_not_create_ownership_or_event_application(self):
        eid = self.event()
        iid = self.create(kind="event", event_id=eid)
        self.assertEqual(self.reply(iid, body="Only the two accounts can read this")[0], 200)
        self.assertEqual(self.send("/api/invitations/" + iid + "/message", "POST",
                                   {"body": "Private host follow-up"}, self.host)[0], 200)
        for actor in (self.host, self.peer):
            code, body, _ = self.send("/invitations/" + iid, actor=actor)
            self.assertEqual(code, 200)
            page = body.decode()
            self.assertIn("Only the two accounts can read this", page)
            self.assertIn("Private host follow-up", page)
            self.assert_private_identity_absent(page)
        with self.app.connect() as conn:
            self.assertEqual(conn.execute("select count(*) from event_applications where event_id=?", (eid,)).fetchone()[0], 0)
            self.assertEqual(conn.execute("select count(*) from circle_claims where circle_id=?", (self.circle,)).fetchone()[0], 0)
            self.assertEqual(conn.execute("select count(*) from event_email_outbox").fetchone()[0], 0)
        self.assertEqual(self.app.get_event(eid)["confirmed_count"], 0)

    def test_http_third_account_cannot_read_discussion_or_modify_link(self):
        iid = self.create()
        self.assertEqual(self.reply(iid, body="PRIVATE_RESPONSE_TEXT")[0], 200)
        for actor in (None, self.other):
            code, body, _ = self.send("/invitations/" + iid, actor=actor)
            self.assertEqual(code, 200)
            self.assertNotIn("PRIVATE_RESPONSE_TEXT", body.decode())
            self.assertNotIn("招待先関係者の自己申告名", body.decode())
        for action, payload in (("respond", CircleInvitationDomainTests.response()),
                                ("message", {"body": "intrusion"}), ("withdraw", {})):
            with self.subTest(action=action):
                self.assertEqual(self.send("/api/invitations/" + iid + "/" + action,
                                           "POST", payload, self.other)[0], 403)
        code, body, _ = self.send("/invitations", actor=self.other)
        self.assertEqual(code, 200)
        self.assertNotIn(iid, body.decode())

    def test_http_expired_and_withdrawn_links_hide_intro_from_guests(self):
        for state in ("withdrawn", "expired"):
            with self.subTest(state=state):
                iid = self.create(subject="PRIVATE_INTRO_SUBJECT", body="PRIVATE_INTRO_BODY")
                if state == "withdrawn":
                    self.assertEqual(self.send("/api/invitations/" + iid + "/withdraw", "POST", {}, self.host)[0], 200)
                else:
                    with self.app.connect() as conn:
                        conn.execute("update circle_invitations set expires_at='2000-01-01T00:00:00+00:00' where invitation_id=?", (iid,))
                code, body, _ = self.send("/invitations/" + iid)
                self.assertEqual(code, 200)
                self.assertNotIn("PRIVATE_INTRO_SUBJECT", body.decode())
                self.assertNotIn("PRIVATE_INTRO_BODY", body.decode())
                self.assertEqual(self.reply(iid)[0], 400)

    def test_http_rejects_cross_site_wrong_content_type_and_bad_json_without_mutation(self):
        with self.app.connect() as conn:
            before = conn.execute("select count(*) from circle_invitations").fetchone()[0]
        for headers, expected in (({"Origin": "https://attacker.example"}, 403),
                                  ({"Sec-Fetch-Site": "cross-site"}, 403),
                                  ({"Content-Type": "text/plain"}, 400)):
            with self.subTest(headers=headers):
                self.assertEqual(self.send("/api/invitations", "POST", self.payload(), self.host, headers)[0], expected)
        for value in (None, [], "string", True, 1):
            with self.subTest(value=type(value).__name__):
                self.assertEqual(self.send("/api/invitations", "POST", value, self.host)[0], 400)
        # A bounded header rejection must happen before trying to read the announced large body.
        # Sending a huge unread body can make Windows reset the socket before its 400 is received.
        self.assertEqual(self.send("/api/invitations", "POST", {}, self.host,
                                   {"Content-Length": "65537"}, raw=b"{}")[0], 400)
        self.assertEqual(self.send("/api/invitations", "POST", actor=self.host, raw=b'{"broken":')[0], 400)
        with self.app.connect() as conn:
            self.assertEqual(conn.execute("select count(*) from circle_invitations").fetchone()[0], before)

    def test_http_response_and_message_also_require_same_site_json(self):
        iid = self.create()
        for action, payload in (("respond", CircleInvitationDomainTests.response()),
                                ("message", {"body": "no mutation"}), ("withdraw", {})):
            with self.subTest(action=action):
                actor = self.host if action == "withdraw" else self.peer
                code, _, _ = self.send("/api/invitations/" + iid + "/" + action, "POST", payload, actor,
                                        {"Origin": "https://attacker.example"})
                self.assertEqual(code, 403)
        with self.app.connect() as conn:
            row = conn.execute("select status,recipient_user_id from circle_invitations where invitation_id=?", (iid,)).fetchone()
        self.assertEqual(row["status"], "pending")
        self.assertIsNone(row["recipient_user_id"])

    def test_http_foreign_draft_closed_cancelled_full_and_past_events_are_rejected(self):
        own = self.event()
        cases = (("organizer_user_id", self.other["user_id"]), ("status", "draft"), ("status", "closed"),
                 ("status", "cancelled"), ("starts_at", "2000-01-01T00:00"),
                 ("application_deadline", "2000-01-01T00:00"))
        for column, value in cases:
            with self.subTest(column=column, value=value):
                with self.app.connect() as conn:
                    old = conn.execute("select " + column + " from event_posts where event_id=?", (own,)).fetchone()[0]
                    conn.execute("update event_posts set " + column + "=? where event_id=?", (value, own))
                try:
                    code, body, _ = self.send("/api/invitations", "POST", self.payload(kind="event", event_id=own), self.host)
                    self.assertEqual(code, 400, body.decode())
                finally:
                    with self.app.connect() as conn:
                        conn.execute("update event_posts set " + column + "=? where event_id=?", (old, own))
        with self.app.connect() as conn:
            self.app.submit_event_application(conn, own, {"participation_type": "individual", "applicant_name": "Peer",
                                                         "participant_count": 10}, self.peer)
        self.assertEqual(self.send("/api/invitations", "POST", self.payload(kind="event", event_id=own), self.host)[0], 400)

    def test_http_html_escapes_intro_and_private_followup(self):
        marker = '<script>window.__INVITATION_XSS__=1</script>'
        iid = self.create(subject=marker, sender_label=marker, body="</textarea>" + marker)
        self.assertEqual(self.reply(iid, display_name=marker, body=marker)[0], 200)
        for actor in (None, self.host, self.peer, self.other):
            code, body, _ = self.send("/invitations/" + iid, actor=actor)
            self.assertEqual(code, 200)
            page = body.decode()
            self.assertNotIn(marker, page)
            self.assertIn("&lt;script&gt;", page)
            self.assert_private_identity_absent(page)

    def test_http_unknown_demo_and_pending_review_targets_are_rejected(self):
        for kind in ("missing", "demo", "review"):
            with self.subTest(kind=kind):
                cid = "invitation-http-" + kind
                if kind != "missing":
                    with self.app.connect() as conn:
                        source = conn.execute("select * from circles where circle_id=?", (self.circle,)).fetchone()
                        columns = list(source.keys())
                        data = dict(source)
                        data.update(circle_id=cid, circle_name="招待境界 " + kind,
                                    public_status="demo" if kind == "demo" else "published")
                        conn.execute("insert into circles(" + ",".join(columns) + ") values(" + ",".join("?" for _ in columns) + ")",
                                     [data[column] for column in columns])
                        if kind == "review":
                            conn.execute("insert into circle_listing_reviews(circle_id,reason,review_status,created_at) values(?,'test','pending',?)",
                                         (cid, self.app.now()))
                code, _, _ = self.send("/api/invitations", "POST", self.payload(target_circle_id=cid), self.host)
                self.assertEqual(code, 400)

    def test_http_private_event_is_rejected_when_visibility_is_supported(self):
        eid = self.event()
        with self.app.connect() as conn:
            columns = {row[1] for row in conn.execute("pragma table_info(event_posts)")}
            if "visibility" not in columns:
                # Exercise the compatibility branch using this test's disposable database only.
                conn.execute("alter table event_posts add column visibility text not null default 'public'")
            conn.execute("update event_posts set visibility='private' where event_id=?", (eid,))
        code, _, _ = self.send("/api/invitations", "POST", self.payload(kind="event", event_id=eid), self.host)
        self.assertEqual(code, 400)
        code, body, _ = self.send("/invitations/new?circle_id=" + self.circle, actor=self.host)
        self.assertEqual(code, 200)
        self.assertNotIn(eid, body.decode())

    def test_public_db_entrypoint_and_no_other_hosts_events_in_composer(self):
        own = self.event()
        code, body, _ = self.send("/?tab=db&q=招待境界検証")
        self.assertEqual(code, 200)
        self.assertIn("/invitations/new?circle_id=" + quote(self.circle, safe=""), body.decode())
        code, body, _ = self.send("/invitations/new?circle_id=" + self.circle, actor=self.host)
        self.assertEqual(code, 200)
        self.assertIn(own, body.decode())
        self.assert_private_identity_absent(body.decode())


if __name__ == "__main__":
    unittest.main()
