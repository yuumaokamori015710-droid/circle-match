"""Custom categories, group admission and privacy-safe sharing; isolated DB only."""
import json
import re
import subprocess
import tempfile
import threading
import unittest
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from test_event_flow import load_app, user, create_account, event_payload


class SharingGroupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.app = load_app(Path(cls.temp.name) / "sharing.sqlite")
        cls.app.init_db()
        cls.app.EMAIL_NOTIFICATIONS_ENABLED = False
        cls.host = user("share-host", "host@example.test", "Host")
        cls.people = [user(f"friend-{i}", f"p{i}@example.test", f"Person {i}") for i in range(3)]
        for person in [cls.host, *cls.people]:
            create_account(cls.app, person)
        with cls.app.connect() as conn:
            cls.session = cls.app.create_user_session(conn, cls.host["user_id"])

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def event(self, **changes):
        payload = event_payload(self.id().rsplit(".", 1)[1], capacity="4")
        payload.update(changes)
        with self.app.connect() as conn:
            return self.app.save_event_post(conn, payload, self.host)

    def apply(self, eid, person=0, count=2):
        with self.app.connect() as conn:
            return self.app.submit_event_application(conn, eid, {
                "participation_type": "individual", "applicant_name": "Representative",
                "participant_count": count,
            }, self.people[person])

    def test_free_payment_hidden_and_form_fee_is_direct_text(self):
        eid = self.event(fee_amount="０", payment_method="bank_transfer")
        event = self.app.get_event(eid)
        self.assertEqual(event["fee_amount"], 0)
        self.assertEqual(event["payment_method"], "free")
        for page in (self.app.render_event_detail_html(eid), self.app.event_application_recap(event)):
            self.assertNotIn("支払方法", page)
        form = self.app.render_event_form_html({}, self.host)
        self.assertIn('id="fee_amount" type="text" inputmode="numeric"', form)
        self.assertIn("k!=='支払方法'||Number(p.fee_amount)!==0", form)
        self.assertEqual(self.app.event_fee_value({"fee_amount": "１，５００"}), 1500)
        with self.assertRaises(ValueError):
            self.app.event_fee_value({"fee_amount": "要相談"})

    def test_custom_category_create_edit_copy_and_public_search(self):
        category = "ボードゲーム <集まろう>"
        eid = self.event(sport_category=category)
        self.assertTrue(any(e["event_id"] == eid for e in self.app.search_events({"sport": [category]})))
        for params in ({"custom": ["1"]}, {"event_id": [eid]}, {"copy": [eid]}):
            page = self.app.render_event_form_html(params, self.host)
            self.assertIn('id="sport_category" type="text" maxlength="100"', page)
            self.assertNotIn('<select id="sport_category">', page)
        page = self.app.render_public_html({"sport": [category]}).decode()
        self.assertIn("ボードゲーム &lt;集まろう&gt;", page)
        self.assertIn(category, self.app.event_sport_options())
        self.event(title="Private category draft", sport_category="Secret draft category", status="draft")
        self.assertNotIn("Secret draft category", self.app.event_sport_options())

    def test_category_cards_and_header_order(self):
        cards = self.app.event_sport_cards({"region": ["kanto"]}, "events")
        self.assertIn("karaoke.png", cards)
        self.assertIn("events.png", cards)
        self.assertIn("board-games.png", cards)
        self.assertNotIn("other.png", cards)
        self.assertIn("custom=1", cards)
        self.assertEqual(cards.count('class="sport-card'), 15)
        body = self.app.personalize_navigation(self.app.render_public_html(), self.session, "/").decode()
        header = body.split("<header", 1)[1].split("</header>", 1)[0]
        self.assertLess(header.index('class="cm-home"'), header.index('class="tab-link'))
        self.assertLess(header.index('action="/logout"'), header.index('id="notificationBell"'))
        self.assertLess(header.index('id="notificationBell"'), header.index('</nav>'))

    def test_board_games_preset_listing_and_creation(self):
        category = "ボードゲーム"
        self.assertIn(category, self.app.event_sport_options())
        self.assertTrue((Path(self.app.__file__).parent / "sports" / "board-games.png").is_file())
        for audience in ("university", "social"):
            cards = self.app.event_sport_cards({}, "db", audience)
            self.assertIn("board-games.png", cards)
            self.assertIn(category, cards)
        page = self.app.render_public_html({"sport": [category], "region": ["kanto"]}).decode()
        self.assertIn('/assets/sports/board-games.png', page)
        self.assertIn(f'<option value="{category}" selected>', page)
        form = self.app.render_event_form_html({"sport": [category]}, self.host)
        self.assertIn('<select id="sport_category">', form)
        self.assertIn(f'<option value="{category}">', form)
        eid = self.event(sport_category=category)
        self.assertTrue(any(e["event_id"] == eid for e in self.app.search_events({"sport": [category]})))

    def test_group_count_cancellation_privacy_and_duplicate(self):
        eid = self.event()
        admission = self.apply(eid, count=3)
        self.assertEqual(self.app.get_event(eid)["confirmed_count"], 3)
        with self.assertRaisesRegex(ValueError, "すでに"):
            self.apply(eid, count=1)
        with self.assertRaisesRegex(ValueError, "定員"):
            self.apply(eid, 1, 2)
        self.assertNotIn("Representative", self.app.render_event_detail_html(eid))
        with self.assertRaises(PermissionError), self.app.connect() as conn:
            self.app.cancel_event_application(conn, eid, admission["application_id"], self.people[1])
        with self.app.connect() as conn:
            self.app.cancel_event_application(conn, eid, admission["application_id"], self.people[0])
        self.assertEqual(self.app.get_event(eid)["confirmed_count"], 0)
        self.apply(eid, 1, 4)
        self.assertEqual(self.app.get_event(eid)["confirmed_count"], 4)

    def test_concurrent_groups_cannot_overbook(self):
        eid = self.event(capacity="3")
        barrier = threading.Barrier(2)
        def submit(person):
            barrier.wait(timeout=5)
            try:
                return self.apply(eid, person, 2)["status"]
            except ValueError:
                return "full"
        with ThreadPoolExecutor(max_workers=2) as pool:
            self.assertCountEqual(list(pool.map(submit, [0, 1])), ["confirmed", "full"])
        self.assertEqual(self.app.get_event(eid)["confirmed_count"], 2)

    def test_approval_checks_whole_group_and_invalid_counts(self):
        eid = self.event(acceptance_mode="approval", capacity="3")
        for invalid in (0, -1, "1.5", "", 100001):
            with self.subTest(invalid=invalid), self.assertRaises(ValueError):
                self.apply(eid, count=invalid)
        first, second = self.apply(eid), self.apply(eid, 1)
        with self.app.connect() as conn:
            self.app.set_event_application_status(conn, eid, first["application_id"], "confirm", self.host)
        with self.assertRaisesRegex(ValueError, "定員"), self.app.connect() as conn:
            self.app.set_event_application_status(conn, eid, second["application_id"], "confirm", self.host)
        self.assertEqual(self.app.get_event(eid)["confirmed_count"], 2)

    def test_share_dialog_contains_only_public_metadata(self):
        eid = self.event(target_total_amount=987654321)
        event = self.app.get_event(eid)
        markup, script = self.app.event_share_dialog(event, True)
        for name in ("LINE", "X", "Insta", "TikTok", "リンク"):
            self.assertIn(">" + name + "<", markup)
        for secret in ("host@example.test", "target_total_amount", "987654321"):
            self.assertNotIn(secret, markup + script)
        owner = self.app.render_event_detail_html(eid, self.host)
        public = self.app.render_event_detail_html(eid)
        self.assertIn('"auto": true', owner)
        self.assertIn('"auto": false', public)
        self.assertIn("?published=1", self.app.EVENT_FORM_SCRIPT)
        page = self.app.render_event_apply_html(eid, self.people[0])
        self.assertIn('class="application-action-buttons"><button class="button share-button"', page)
        for js in re.findall(r"<script>(.*?)</script>", page, re.S):
            check = subprocess.run(["node", "--check"], input=js, encoding="utf-8", capture_output=True)
            self.assertEqual(check.returncode, 0, check.stderr)

    def test_share_native_fallback_copy_failure_and_auto_open(self):
        result = subprocess.run(["node", str(Path(__file__).with_name("test_event_sharing.cjs"))],
                                input=self.app.EVENT_SHARE_SCRIPT, encoding="utf-8", capture_output=True)
        self.assertEqual(result.returncode, 0, result.stderr)


if __name__ == "__main__":
    unittest.main()
