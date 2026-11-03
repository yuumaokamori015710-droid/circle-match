"""HTTP organizer-fee journey with real SDK/signatures and no external transport."""

import hashlib
import hmac
import json
import os
from pathlib import Path
import re
import tempfile
import threading
import time
import unittest
from http.server import ThreadingHTTPServer
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request, urlopen

import stripe

from test_event_flow import create_account, event_payload, load_app, user


class IsolatedStripeTransport(stripe.HTTPClient):
    name = "organizer-journey-no-network"

    def __init__(self):
        super().__init__()
        self.sessions, self.idempotency, self.calls = {}, {}, []

    def request(self, method, url, headers, post_data=None, **kwargs):
        method = method.upper()
        parsed = urlsplit(url)
        if parsed.hostname != "api.stripe.com":
            raise AssertionError("Unexpected transport destination")
        data = parse_qs(post_data or "")
        headers = {key.lower(): value for key, value in headers.items()}
        if headers.get("authorization") != "Bearer rk_test_local_journey":
            raise AssertionError("Only the synthetic test key is allowed")
        self.calls.append((method, parsed.path, data))
        if method == "GET" and parsed.path == "/v1/account":
            obj = dict(id="acct_Journey", object="account", country="JP",
                       default_currency="jpy", charges_enabled=True)
        elif method == "POST" and parsed.path == "/v1/checkout/sessions":
            assert data["allowed_payment_method_types[0]"] == ["card"]
            assert data["managed_payments[enabled]"] == ["false"]
            assert not any("transfer_data" in key or "application_fee" in key for key in data)
            key = headers["idempotency-key"]
            if key not in self.idempotency:
                sid = "cs_test_journey_" + str(len(self.sessions) + 1)
                self.idempotency[key] = sid
                order_id = data["client_reference_id"][0]
                self.sessions[sid] = dict(id=sid, object="checkout.session", mode="payment",
                    currency="jpy", livemode=False, status="open", payment_status="unpaid",
                    amount_total=int(data["line_items[0][price_data][unit_amount]"][0]),
                    client_reference_id=order_id, metadata={"host_fee_order_id": order_id},
                    payment_intent=None, url="https://checkout.stripe.com/c/pay/" + sid + "#issued-fragment")
            obj = self.sessions[self.idempotency[key]]
        elif method == "POST" and parsed.path.endswith("/expire"):
            obj = self.sessions[parsed.path.split("/")[-2]]
            obj["status"] = "expired"
        elif method == "GET" and parsed.path.startswith("/v1/checkout/sessions/"):
            obj = self.sessions[parsed.path.rsplit("/", 1)[1]]
        else:
            raise AssertionError("Unexpected Stripe call; network access is never used")
        return json.dumps(obj), 200, {}

    def mark_test_payment_complete(self, sid):
        session = self.sessions[sid]
        amount = session["amount_total"]
        intent_id = "pi_journey_1"
        session.update(status="complete", payment_status="paid", payment_intent=dict(
            id=intent_id, object="payment_intent", status="succeeded", currency="jpy",
            livemode=False, amount=amount, amount_received=amount,
            latest_charge=dict(id="ch_journey_1", object="charge", payment_intent=intent_id,
                paid=True, captured=True, amount=amount, currency="jpy", livemode=False,
                amount_refunded=0)))


class HostFeeJourneyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix="host-fee-journey-")
        folder = Path(cls.temp.name)
        cls.environ = patch.dict(os.environ, dict(
            CIRCLEMATCH_HOST_FEES_ENABLED="true", CIRCLEMATCH_EMAIL_NOTIFICATIONS_ENABLED="false",
            CIRCLEMATCH_EMAIL_AUTH_ENABLED="false", CIRCLEMATCH_RESEND_API_KEY="",
            CIRCLEMATCH_SUPABASE_URL="", CIRCLEMATCH_SUPABASE_ANON_KEY="",
            CIRCLEMATCH_SESSION_SECRET="local-only-host-fee-journey",
            CIRCLEMATCH_PUBLIC_SEED_PATH=str(folder / "unused.csv")))
        cls.environ.start()
        cls.app = load_app(folder / "journey.sqlite")
        cls.app.HOST_FEES_ENABLED = True
        cls.app.EMAIL_NOTIFICATIONS_ENABLED = False
        cls.app.LOG_PATH = folder / "journey.log"
        cls.app.init_db()
        with cls.app.connect() as conn:
            cls.app.fee_campaign.change(conn, dict(enabled=True, revision=0, accepted=True))
        cls.people = {role: user("journey_" + role, role + "@example.test", "Journey " + role)
                      for role in ("host", "individual", "team")}
        cls.cookies = {}
        for role, account in cls.people.items():
            create_account(cls.app, account)
            with cls.app.connect() as conn:
                cls.cookies[role] = cls.app.create_user_session(conn, account["user_id"])

        class Handler(cls.app.Handler):
            def cookie_value(self, name):
                return super().cookie_value("cm_journey_session" if name == "cm_session" else name)

            def do_GET(self):
                role = self.path.removeprefix("/__journey__/")
                if self.path.startswith("/__journey__/") and role in cls.people and hasattr(cls, "event_id"):
                    self.redirect("/events/" + cls.event_id + ("/host-fee" if role == "host" else ""),
                        ["cm_journey_session=" + cls.cookies[role] + "; Path=/; HttpOnly; SameSite=Lax"])
                    return
                super().do_GET()

        cls.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = "http://127.0.0.1:" + str(cls.server.server_port)
        cls.transport = IsolatedStripeTransport()
        cls.config = cls.app.online_payments.Config(enabled=True, mode="test", key="rk_test_local_journey",
            webhook_secret="whsec_local_journey_platform", connect_webhook_secret="whsec_local_journey_connect",
            platform="acct_Journey", base_url=cls.base)
        with patch.object(stripe, "RequestsClient", return_value=cls.transport):
            gateway = cls.app.online_payments.StripeGateway(cls.config)
        cls.app._payments = cls.app.online_payments.Payments(cls.app.connect, cls.app.add_event_notification,
            cls.config, gateway, unmatched_webhook=lambda job: cls.app.host_fee_service().webhook_job(job))

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.environ.stop()
        cls.temp.cleanup()

    def request(self, path, role=None, data=None, headers=None):
        headers = dict(headers or {})
        if role:
            headers["Cookie"] = "cm_journey_session=" + self.cookies[role]
        if isinstance(data, dict):
            data = json.dumps(data).encode()
        if data is not None:
            headers.setdefault("Content-Type", "application/json")
        try:
            response = urlopen(Request(self.base + path, data=data, headers=headers), timeout=10)
        except HTTPError as error:
            response = error
        with response:
            body = response.read().decode()
            return response.code, json.loads(body) if "application/json" in response.headers.get("Content-Type", "") else body

    def fee(self):
        status, result = self.request("/api/events/" + self.event_id + "/host-fee", "host")
        self.assertEqual(status, 200, result)
        return result

    def test_mixed_applications_formation_invoice_signed_webhook_and_private_result(self):
        payload = event_payload("Isolated organizer-fee journey", capacity="")
        payload.update(participation_type="both", individual_fee_amount=2500, team_fee_amount=15000,
            minimum_participants=2, host_fee_accepted=True,
            host_fee_policy_version=self.app.host_fees.POLICY_VERSION)
        status, created = self.request("/api/events", "host", payload)
        self.assertEqual(status, 200, created)
        type(self).event_id = created["event_id"]
        prefix = "/api/events/" + self.event_id
        for role, kind, count in [("individual", "individual", 2), ("team", "team", 11)]:
            status, result = self.request(prefix + "/applications", role, dict(
                participation_type=kind, participant_count=count, applicant_name="Test participant",
                team_name="Test FC", representative_name="Test captain"))
            self.assertEqual(status, 200, result)
            self.assertEqual(result["status"], "confirmed")
        self.assertEqual((self.fee()["charge_due"], self.fee()["collected_gross"]), (0, 0))
        self.assertEqual(self.request(prefix + "/host-fee")[0], 401)
        self.assertEqual(self.request(prefix + "/host-fee", "individual")[0], 403)
        status, result = self.request(prefix + "/announce", "host", dict(version=0,
            starts_at="2030-06-01T10:00", location="Test court", announcement_details="Test formation",
            attendance_deadline="2030-05-31T10:00"))
        self.assertEqual(status, 200, result)
        self.assertEqual(self.fee()["charge_due"], 0)
        for role in ("individual", "team"):
            self.assertEqual(self.request(prefix + "/attendance", role, {"version": 1})[0], 200)
        status, applications = self.request(prefix + "/applications", "host")
        self.assertEqual(status, 200, applications)
        for application in applications:
            status, result = self.request(prefix + "/applications/" + application["application_id"] + "/payment",
                "host", dict(payment_status="paid", payment_note="Synthetic test receipt",
                             revision=application["operation_revision"]))
            self.assertEqual(status, 200, result)
        balance = self.fee()
        self.assertEqual((balance["collected_gross"], balance["charge_due"]), (20000, 2000))

        status, owner_page = self.request("/events/" + self.event_id + "/host-fee", "host")
        self.assertEqual(status, 200)
        self.assertIn("2,000円", owner_page)
        self.assertIn("主催者のみ / 利用料10%", owner_page)
        csrf = json.loads(re.search(r"'X-CSRF-Token':(\"[^\"]+\")", owner_page).group(1))
        checkout = "/api/payments/host-fees/" + self.event_id + "/checkout"
        data = dict(accepted=True, quote_token=balance["quote_token"])
        self.assertEqual(self.request(checkout, "host", data)[0], 403)
        headers = {"X-CSRF-Token": csrf}
        self.assertEqual(self.request(checkout, "host", dict(data, amount=1), headers)[0], 400)
        status, first = self.request(checkout, "host", data, headers)
        self.assertEqual(status, 200, first)
        status, repeated = self.request(checkout, "host", data, headers)
        self.assertEqual((status, repeated), (200, first))
        self.assertEqual(len(self.transport.sessions), 1)
        sid = next(iter(self.transport.sessions))
        self.assertEqual(first["url"], self.transport.sessions[sid]["url"])
        self.assertTrue(first["url"].endswith("#issued-fragment"))
        self.transport.mark_test_payment_complete(sid)
        self.assertEqual(self.fee()["fee_paid"], 0)

        body = json.dumps(dict(id="evt_local_host_journey", object="event", livemode=False,
            type="checkout.session.completed", data={"object":dict(id=sid, object="checkout.session",
            payment_intent="pi_journey_1")})).encode()
        timestamp = str(int(time.time()))
        signature = "t=" + timestamp + ",v1=" + hmac.new(self.config.webhook_secret.encode(),
            timestamp.encode() + b"." + body, hashlib.sha256).hexdigest()
        signed = {"Stripe-Signature": signature}
        self.assertEqual(self.request("/api/payments/webhook", data=body + b" ", headers=signed)[0], 400)
        self.assertEqual(self.request("/api/payments/webhook", data=body, headers=signed)[0], 200)
        self.assertTrue(self.app.payment_service().webhook_job())
        settled = self.fee()
        self.assertEqual((settled["fee_paid"], settled["charge_due"]), (2000, 0))
        self.assertEqual(self.request("/api/payments/webhook", data=body, headers=signed)[0], 200)
        self.assertFalse(self.app.payment_service().webhook_job())
        with self.app.connect() as conn:
            self.assertEqual(conn.execute("select count(*) from host_fee_orders").fetchone()[0], 1)
            self.assertEqual(conn.execute("select count(*) from payment_orders").fetchone()[0], 0)
            self.assertEqual(conn.execute("select count(*) from payment_accounts").fetchone()[0], 0)
            self.assertEqual(conn.execute("select count(*) from event_notifications where notification_type='host_fee_paid'").fetchone()[0], 1)
            self.assertEqual(conn.execute("select state from payment_webhooks").fetchone()[0], "done")
        for path in ("/events/" + self.event_id, "/events/" + self.event_id + "/apply", prefix):
            status, page = self.request(path, "individual")
            self.assertEqual(status, 200, page)
            rendered = page if isinstance(page, str) else json.dumps(page)
            for private in ("data-host-fee-private", "forecast_fee", "Circle Matchへの利用料支払済み"):
                self.assertNotIn(private, rendered)
        status, owner_result = self.request("/events/" + self.event_id + "/host-fee", "host")
        self.assertEqual(status, 200)
        self.assertIn("2,000円", owner_result)
        self.assertNotIn("Stripeの利用料支払確認へ", owner_result)


if __name__ == "__main__":
    import sys
    if "--preview" not in sys.argv:
        unittest.main()
    else:
        HostFeeJourneyTests.setUpClass()
        try:
            result = unittest.TestResult()
            HostFeeJourneyTests("test_mixed_applications_formation_invoice_signed_webhook_and_private_result").run(result)
            if not result.wasSuccessful():
                raise RuntimeError(result.errors + result.failures)
            print("Verified local-only journey. No external Stripe requests or real charges.", flush=True)
            print("Owner: " + HostFeeJourneyTests.base + "/__journey__/host", flush=True)
            print("Participant: " + HostFeeJourneyTests.base + "/__journey__/individual", flush=True)
            threading.Event().wait(180)
        finally:
            HostFeeJourneyTests.tearDownClass()
