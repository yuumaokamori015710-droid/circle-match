"""UX regressions with isolated SQLite and dummy accounts; no outgoing mail."""
import json
import re
import subprocess
import tempfile
import unittest
import threading
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from test_event_flow import load_app, user, create_account, event_payload, request_json


class EventUXTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.app = load_app(Path(cls.temp.name) / "ux.sqlite")
        cls.app.init_db()
        cls.app.EMAIL_NOTIFICATIONS_ENABLED = False
        cls.host = user("ux_host", "host@example.test", "主催者")
        cls.person = user("ux_person", "person@example.test", "参加者")
        cls.other = user("ux_other", "other@example.test", "他の利用者")
        for account in (cls.host, cls.person, cls.other):
            create_account(cls.app, account)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def event(self, mode="first_come", capacity="1"):
        with self.app.connect() as conn:
            return self.app.save_event_post(conn, event_payload(self.id(), mode, "individual", capacity), self.host)

    def test_competition_home_navigation_and_filter_labels(self):
        from html.parser import HTMLParser
        class Links(HTMLParser):
            def __init__(self):
                super().__init__()
                self.home = []
                self.labels = []
            def handle_starttag(self, tag, attrs):
                attrs = dict(attrs)
                if tag == "a" and attrs.get("class") == "home-link":
                    self.home.append(attrs["href"])
                if tag == "label" and attrs.get("class") == "event-filter":
                    self.labels.append(attrs)
        for audience in ("university", "social"):
            for tab in ("events", "db"):
                params = {"tab": [tab], "audience": [audience], "sport": ["サッカー・フットサル"], "region": ["kanto"]}
                page = self.app.render_public_html(params).decode()
                parsed = Links()
                parsed.feed(page)
                expected = "/" if tab == "events" else "/?tab=db&audience=" + audience
                self.assertEqual(parsed.home, [expected])
                self.assertNotIn(">すべての競技</a>", page)
                self.assertIn('aria-label="現在位置"', page)
                self.assertIn("link.classList.contains('home-link')", page)
                if tab == "events":
                    self.assertIn('/events/new?sport=', page)
                    self.assertEqual(len(parsed.labels), 5)
                    self.assertIn('class="button primary publish-cta"', page)

    def test_publish_action_is_between_sport_image_and_results_not_in_header(self):
        from urllib.parse import parse_qs, urlparse
        import html
        for sport in self.app.event_sport_options():
            page = self.app.render_public_html({"sport": [sport], "region": ["kanto"]}).decode()
            header = page.split("</header>", 1)[0]
            self.assertNotIn(">募集を掲載する</a>", header)
            self.assertEqual(page.count(">募集を掲載する</a>"), 1)
            image = page.index('class="event-results-intro"')
            action = page.index('class="event-publish"')
            results = page.index('id="events"')
            self.assertLess(image, action)
            self.assertLess(action, results)
            target = re.search(r'class="button primary publish-cta" href="([^"]+)"', page)[1]
            url = urlparse(html.unescape(target))
            self.assertEqual(url.path, "/events/new")
            self.assertEqual(parse_qs(url.query), {"sport": [sport], "region": ["kanto"]})
        for page in (self.app.render_public_html().decode(),
                     self.app.render_public_html({"tab": ["db"]}).decode(),
                     self.app.render_event_form_html({}, self.host),
                     self.app.render_mypage_html(self.host)):
            self.assertNotIn(">募集を掲載する</a>", page.split("</header>", 1)[0])

    def test_form_back_button_does_not_reserve_empty_mobile_row(self):
        page = self.app.render_event_form_html({}, self.host)
        self.assertIn("$('backStep').hidden=step===0", page)
        self.assertNotIn("$('backStep').style.visibility", page)

    def test_publish_action_is_centered_with_full_width_mobile_button(self):
        page = self.app.render_public_html({"sport": ["サッカー・フットサル"]}).decode()
        self.assertIn(".event-publish{display:flex;justify-content:center;", page)
        self.assertIn(".event-publish .publish-cta{width:100%;min-width:0;min-height:48px}", page)

    def apply(self, eid, person=None):
        with self.app.connect() as conn:
            return self.app.submit_event_application(conn, eid, {
                "participation_type": "individual", "applicant_name": "確認参加者",
                "participant_count": 1, "applicant_message": "持ち物を相談したいです <script>test</script>",
            }, person or self.person)

    def test_closed_and_expired_admission_still_allows_review(self):
        eid = self.event("approval")
        application = self.apply(eid)
        with self.app.connect() as conn:
            self.app.set_event_status(conn, eid, "closed", self.host)
            conn.execute("update event_posts set application_deadline='2000-01-01 00:00' where event_id=?", (eid,))
        with self.app.connect() as conn:
            self.assertEqual(self.app.set_event_application_status(conn, eid, application["application_id"], "confirm", self.host), "confirmed")
        with self.assertRaises(ValueError):
            self.apply(eid, self.other)

    def test_cancelled_event_takes_precedence_and_blocks_approval(self):
        eid = self.event("approval")
        application = self.apply(eid)
        with self.app.connect() as conn:
            self.app.set_event_status(conn, eid, "cancelled", self.host)
        page = self.app.render_mypage_html(self.person)
        self.assertIn('<span class="badge cancelled">開催中止</span>', page)
        with self.assertRaisesRegex(ValueError, "中止"), self.app.connect() as conn:
            self.app.set_event_application_status(conn, eid, application["application_id"], "confirm", self.host)

    def test_cancel_reapply_preserves_history_and_messages(self):
        eid = self.event()
        application = self.apply(eid)
        with self.app.connect() as conn:
            self.app.cancel_event_application(conn, eid, application["application_id"], self.person)
        with self.app.connect() as conn:
            self.app.send_event_message(conn, eid, {"body": "取消後の相談"}, self.person)
        self.assertEqual(self.app.event_messages_for_user(eid, self.host, self.person["user_id"])[0]["body"], "取消後の相談")
        self.assertEqual(self.app.event_messages_for_user(eid, self.other), [])
        with self.assertRaises(PermissionError):
            self.app.event_messages_for_user(eid, self.other, self.person["user_id"])
        again = self.apply(eid)
        self.assertEqual(again["application_id"], application["application_id"])
        with self.app.connect() as conn:
            history = conn.execute("select snapshot_json from event_application_history where application_id=?", (again["application_id"],)).fetchall()
        self.assertEqual(len(history), 1)
        self.assertEqual(json.loads(history[0][0])["status"], "cancelled")
        self.assertIn("取消後の相談", self.app.event_messages_for_user(eid, self.person)[0]["body"])

    def test_reapply_race_and_active_duplicate(self):
        eid = self.event()
        first = self.apply(eid)
        with self.app.connect() as conn:
            self.app.cancel_event_application(conn, eid, first["application_id"], self.person)
        def apply_once(_):
            try:
                return self.apply(eid)["status"]
            except ValueError:
                return "rejected"
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertCountEqual(list(pool.map(apply_once, [1, 2])), ["confirmed", "rejected"])
        self.assertEqual(self.app.get_event(eid)["confirmed_count"], 1)

    def test_full_state_in_cards_detail_and_apply(self):
        eid = self.event()
        self.apply(eid)
        event = self.app.get_event(eid)
        self.assertEqual(self.app.event_availability(event), ("満員", False))
        self.assertIn("満員", self.app.render_event_cards([event]))
        self.assertNotIn('id="applicationForm"', self.app.render_event_apply_html(eid, self.other))
        self.assertNotIn('class="button primary mobile-apply"', self.app.render_event_detail_html(eid))
        self.assertIn("マイページへ", self.app.render_event_apply_html(eid, self.person))

    def test_cancelled_application_has_no_reapply_link_when_full(self):
        eid = self.event()
        application = self.apply(eid)
        with self.app.connect() as conn:
            self.app.cancel_event_application(conn, eid, application["application_id"], self.person)
        self.apply(eid, self.other)
        attending = next(row for row in self.app.event_my_page(self.person)["attending"] if row["event_id"] == eid)
        self.assertEqual(attending["confirmed_count"], 1)
        self.assertEqual(self.app.event_availability(attending), ("満員", False))

    def test_initial_message_owner_only_and_rejected_cannot_reapply(self):
        eid = self.event("approval")
        application = self.apply(eid)
        rows = self.app.event_applications_for_owner(eid, self.host)
        self.assertIn("持ち物", rows[0]["applicant_message"])
        with self.assertRaises(PermissionError):
            self.app.event_applications_for_owner(eid, self.other)
        self.assertNotIn("applicant_message", self.app.get_event(eid))
        with self.app.connect() as conn:
            self.app.set_event_application_status(conn, eid, application["application_id"], "decline", self.host)
        with self.assertRaises(ValueError):
            self.apply(eid)

    def test_partial_draft_and_publication_validation(self):
        payload = event_payload("入力途中の下書き")
        payload.update(status="draft", sport_category="", starts_at="", ends_at="", location="", description="", cancellation_policy="")
        with self.app.connect() as conn:
            eid = self.app.save_event_post(conn, payload, self.host)
        self.assertIsNone(self.app.get_event(eid))
        payload.update(event_id=eid, status="published")
        with self.assertRaises(ValueError), self.app.connect() as conn:
            self.app.save_event_post(conn, payload, self.host)

    def test_search_context_pagination_and_source_fallback(self):
        params = {"tab": ["db"], "audience": ["university"], "sport": ["野球"], "region": ["kanto"], "page": ["2"]}
        page = self.app.render_public_html(params).decode("utf-8")
        self.assertIn("/events?sport=", page)
        self.assertIn("region=kanto", page)
        self.assertIn('id="dbPager"', page)
        self.assertIn("前へ", page)
        markup = self.app.render_db_rows([{"circle_name": "出典のあるサークル", "source_url": "https://example.test/circle"}])
        self.assertIn("出典を確認（外部）", markup)
        self.assertNotIn("掲載準備中", markup)
        self.assertFalse(self.app.safe_public_source("javascript:alert(1)"))

    def test_non_destructive_quarantine_and_restore(self):
        source = next(iter(self.app.LISTING_REVIEW_SOURCES))
        with self.app.connect() as conn:
            cid = conn.execute("select circle_id from circles where source_url=?", (source,)).fetchone()[0]
            self.assertTrue(conn.execute("select 1 from circle_listing_reviews where circle_id=?", (cid,)).fetchone())
            before = dict(conn.execute("select * from circles where circle_id=?", (cid,)).fetchone())
            where = self.app.public_circle_clause()
            self.assertIsNone(conn.execute(f"select 1 from circles c where c.circle_id=? and {where}", (cid,)).fetchone())
            conn.execute("update circle_listing_reviews set review_status='approved' where circle_id=?", (cid,))
            self.assertTrue(conn.execute(f"select 1 from circles c where c.circle_id=? and {where}", (cid,)).fetchone())
            self.assertEqual(before, dict(conn.execute("select * from circles where circle_id=?", (cid,)).fetchone()))
            conn.execute("update circle_listing_reviews set review_status='pending' where circle_id=?", (cid,))

    def test_generated_javascript_parses(self):
        eid = self.event()
        pages = [self.app.render_public_html(), self.app.render_public_html({"tab": ["db"]}),
                 self.app.render_event_form_html({"sport": ["野球"], "region": ["kanto"]}, self.host),
                 self.app.render_event_apply_html(eid, self.person), self.app.render_mypage_html(self.host),
                 self.app.render_notifications_html(self.host), self.app.NOTIFICATION_BADGE_SCRIPT]
        pages = [page.decode("utf-8") if isinstance(page, bytes) else page for page in pages]
        scripts = [script for page in pages for script in re.findall(r'<script>(.*?)</script>', page, re.S) if script.strip()]
        command = "const vm=require('node:vm');const s=JSON.parse(require('node:fs').readFileSync(0,'utf8'));s.forEach(x=>new vm.Script(x));console.log(s.length+' scripts parsed');"
        result = subprocess.run(["node", "-e", command], input=json.dumps(scripts), text=True, capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_notification_read_only_changes_recipient_records(self):
        with self.app.connect() as conn:
            for account in (self.person, self.other):
                self.app.add_event_notification(conn, account["user_id"], None, "ux_read_test", "テスト", "既読権限の確認")
            ids = [row[0] for row in conn.execute("select notification_id from event_notifications where notification_type='ux_read_test'")]
            session = self.app.create_user_session(conn, self.person["user_id"])
        server = ThreadingHTTPServer(("127.0.0.1", 0), self.app.Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            url = f"http://127.0.0.1:{server.server_port}/api/notifications/read"
            with self.assertRaises(HTTPError) as error:
                request_json(url, "POST", {"notification_ids": ids})
            self.assertEqual(error.exception.code, 401)
            error.exception.close()
            request_json(url, "POST", {"notification_ids": ids}, "cm_session=" + session)
            with self.app.connect() as conn:
                notes = {row["recipient_user_id"]: row["read_at"] for row in conn.execute("select * from event_notifications where notification_type='ux_read_test'")}
            self.assertTrue(notes[self.person["user_id"]])
            self.assertIsNone(notes[self.other["user_id"]])
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    unittest.main(verbosity=2)
