"""Real Stripe signature verification, isolated storage, no network or charges."""

import copy
import hashlib
import hmac
import json
import os
import sys
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "outputs"))
import circlematch_stripe_qa as qa


class StripeQaTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "isolated.sqlite3"
        self.env = {"CIRCLEMATCH_STRIPE_QA_WEBHOOK_UNTIL": str(int(time.time()) + 3600),
                    "CIRCLEMATCH_STRIPE_QA_WEBHOOK_SECRET": "whsec_isolated_unit_test_only",
                    "CIRCLEMATCH_STRIPE_QA_SECRET_KEY": "rk_test_isolated_unit_test_only",
                    "CIRCLEMATCH_STRIPE_QA_CHECKOUT_SESSION": "cs_test_isolated_unit_test_only"}
        self.config = qa.settings(self.env)
        self.event = {"id": "evt_qa_only", "object": "event", "type": "checkout.session.completed",
                      "livemode": False, "data": {"object": {
                          "object": "checkout.session", "id": self.config.session_id, "livemode": False,
                          "metadata": {"purpose": "circlematch_qa_only"},
                          "customer_email": "must-not-be-stored@example.test"}}}

    def deliver(self, event=None, **kwargs):
        body = json.dumps(self.event if event is None else event).encode()
        timestamp = kwargs.pop("timestamp", int(time.time()))
        digest = hmac.new(self.config.secret.encode(), str(timestamp).encode() + b"." + body,
                          hashlib.sha256).hexdigest()
        return qa.receive(body, f"t={timestamp},v1={digest}", config=self.config, path=self.path, **kwargs)

    def paid_session(self):
        return {"id": self.config.session_id, "livemode": False, "status": "complete",
                "payment_status": "paid", "currency": "jpy", "amount_total": 500,
                "metadata": {"purpose": "circlematch_qa_only"}, "payment_intent": {
                    "id": "pi_qa", "livemode": False, "status": "succeeded",
                    "amount_received": 500, "currency": "jpy", "latest_charge": {
                        "payment_intent": "pi_qa", "livemode": False, "status": "succeeded",
                        "paid": True, "captured": True, "amount": 500, "amount_refunded": 0,
                        "currency": "jpy", "payment_method_details": {"card": {"three_d_secure": {
                            "result": "authenticated", "authentication_flow": "challenge"}}}}}}

    def test_disabled_by_default_and_expiry_is_bounded(self):
        for changes in [{}, {"CIRCLEMATCH_STRIPE_QA_WEBHOOK_UNTIL": "0"},
                        {"CIRCLEMATCH_STRIPE_QA_WEBHOOK_UNTIL": "invalid"},
                        {"CIRCLEMATCH_STRIPE_QA_WEBHOOK_UNTIL": str(int(time.time()) + qa.MAX_WINDOW + 60)},
                        {"CIRCLEMATCH_STRIPE_QA_SECRET_KEY": "rk_live_must_not_be_used"},
                        {"CIRCLEMATCH_STRIPE_QA_CHECKOUT_SESSION": "cs_live_not_allowed"},
                        {"CIRCLEMATCH_ONLINE_PAYMENTS_ENABLED": "true"},
                        {"CIRCLEMATCH_STRIPE_LIVE_APPROVED": "true"},
                        {"CIRCLEMATCH_STRIPE_WEBHOOK_SECRET": self.config.secret},
                        {"CIRCLEMATCH_STRIPE_CONNECT_WEBHOOK_SECRET": self.config.secret}]:
            env = {} if not changes else {**self.env, **changes}
            with self.subTest(changes=list(changes)), self.assertRaises(qa.Disabled):
                qa.settings(env)
        self.assertFalse(self.path.exists())
        self.assertNotIn(self.config.secret, repr(self.config))
        self.assertNotIn(self.config.key, repr(self.config))

    def test_real_signature_and_duplicate_receipt_do_not_store_payload(self):
        self.assertFalse(self.deliver()["duplicate"])
        self.assertTrue(self.deliver()["duplicate"])
        report = qa.report(config=self.config, path=self.path)
        self.assertEqual(len(report["receipts"]), 1)
        self.assertEqual(report["receipts"][0]["deliveries"], 2)
        self.assertEqual(report["receipts"][0]["state"], "queued")
        self.assertNotIn(b"must-not-be-stored@example.test", self.path.read_bytes())
        self.assertNotIn(self.config.secret.encode(), self.path.read_bytes())
        self.assertNotIn(self.config.key.encode(), self.path.read_bytes())

    def test_bad_signature_stale_timestamp_and_oversized_body_are_rejected(self):
        for body, signature in [(b"{}", "t=1,v1=bad"), (b"", ""), (b"x" * (qa.MAX_BODY + 1), "")]:
            with self.assertRaises(ValueError):
                qa.receive(body, signature, config=self.config, path=self.path)
        with self.assertRaisesRegex(ValueError, "signature"):
            self.deliver(timestamp=int(time.time()) - 601)
        self.assertFalse(self.path.exists())

    def test_live_other_session_connected_account_and_unrelated_events_are_rejected(self):
        cases = []
        for key, value in [("livemode", True), ("account", "acct_other"),
                           ("type", "payment_intent.succeeded"), ("id", "wrong_id"),
                           ("data", [])]:
            event = copy.deepcopy(self.event)
            event[key] = value
            cases.append(event)
        for key, value in [("id", "cs_test_other"), ("livemode", True),
                           ("metadata", {}), ("metadata", []), ("object", "payment_intent")]:
            event = copy.deepcopy(self.event)
            event["data"]["object"][key] = value
            cases.append(event)
        for event in cases:
            with self.subTest(event_id=event["id"]), self.assertRaises(ValueError):
                self.deliver(event)
        self.assertFalse(self.path.exists())

    def test_reconcile_uses_provider_state_once_after_duplicate_delivery(self):
        self.deliver()
        retrieve = Mock(return_value=self.paid_session())
        self.assertEqual(qa.reconcile(config=self.config, path=self.path, retrieve=retrieve),
                         {"verified": 1, "failed": 0})
        self.deliver()
        another_event = copy.deepcopy(self.event)
        another_event["id"] = "evt_distinct_same_checkout"
        self.assertTrue(self.deliver(another_event)["duplicate"])
        self.assertEqual(qa.reconcile(config=self.config, path=self.path, retrieve=retrieve),
                         {"verified": 0, "failed": 0})
        retrieve.assert_called_once_with(self.config)
        row = qa.report(config=self.config, path=self.path)["receipts"][0]
        self.assertEqual((row["deliveries"], row["processed_count"], row["state"]), (3, 1, "verified"))

    def test_provider_mismatch_and_timeout_never_mark_verified(self):
        for field, value in [("livemode", True), ("payment_status", "unpaid"),
                             ("amount_total", 501), ("currency", "usd")]:
            session = self.paid_session()
            session[field] = value
            with self.subTest(field=field), self.assertRaises(ValueError):
                qa._assert_paid(session, self.config.session_id)
        with self.assertRaisesRegex(ValueError, "not_verified"):
            session = self.paid_session()
            session["payment_intent"]["latest_charge"]["payment_method_details"]["card"]["three_d_secure"]["result"] = "failed"
            qa._assert_paid(session, self.config.session_id)
        self.deliver()
        retrieve = Mock(side_effect=TimeoutError(self.config.key))
        self.assertEqual(qa.reconcile(config=self.config, path=self.path, retrieve=retrieve),
                         {"verified": 0, "failed": 1})
        row = qa.report(config=self.config, path=self.path)["receipts"][0]
        self.assertEqual((row["processed_count"], row["last_error"]), (0, "TimeoutError"))
        self.assertNotIn(self.config.key.encode(), self.path.read_bytes())

    def test_sdk_retrieval_is_read_only_and_uses_only_the_restricted_test_key(self):
        with patch("stripe.StripeClient") as client:
            client.return_value.v1.checkout.sessions.retrieve.return_value.to_dict.return_value = self.paid_session()
            self.assertEqual(qa._retrieve(self.config)["id"], self.config.session_id)
            self.assertEqual(client.call_args.args[0], self.config.key)
            client.return_value.v1.checkout.sessions.retrieve.assert_called_once_with(
                self.config.session_id, {"expand": ["payment_intent.latest_charge"]})
            client.return_value.v1.checkout.sessions.create.assert_not_called()
            client.return_value.v1.refunds.create.assert_not_called()


    def test_http_receiver_is_separate_from_production_payment_service_and_db(self):
        from test_event_flow import load_app
        database = Path(self.temp.name) / "application.sqlite"
        app = load_app(database)
        before = database.read_bytes()
        server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        body = json.dumps(self.event).encode()
        stamp = int(time.time())
        digest = hmac.new(self.config.secret.encode(), str(stamp).encode() + b"." + body, hashlib.sha256).hexdigest()
        def post(signature):
            request = urllib.request.Request(f"http://127.0.0.1:{server.server_port}" + qa.WEBHOOK_PATH,
                data=body, headers={"Content-Type": "application/json", "Stripe-Signature": signature})
            try:
                with urllib.request.urlopen(request, timeout=5) as response:
                    return response.status, response.read()
            except urllib.error.HTTPError as response:
                with response:
                    return response.code, response.read()
        try:
            with patch.object(app, "payment_service", side_effect=AssertionError("must not use live service")), \
                    patch.object(app, "connect", side_effect=AssertionError("must not open application DB")), \
                    patch.object(app.stripe_qa, "database_path", return_value=self.path):
                with patch.dict(os.environ, self.env):
                    self.assertEqual(post("invalid")[0], 400)
                    self.assertEqual(post(f"t={stamp},v1={digest}")[0], 200)
                    self.assertTrue(json.loads(post(f"t={stamp},v1={digest}")[1])["duplicate"])
                with patch.dict(os.environ, {"CIRCLEMATCH_STRIPE_QA_WEBHOOK_UNTIL": "0"}):
                    self.assertEqual(post(f"t={stamp},v1={digest}")[0], 410)
            self.assertEqual(database.read_bytes(), before)
        finally:
            server.shutdown()
            server.server_close()
            thread.join()


if __name__ == "__main__":
    unittest.main()
