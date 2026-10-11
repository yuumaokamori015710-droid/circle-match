"""Admin-only contact research HTTP checks with a disposable DB and no network."""
import base64
import json
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request

from test_venues import IsolatedAppHttpCase


class ContactResearchHttpTests(IsolatedAppHttpCase):
    def setUp(self):
        with self.app.connect() as conn:
            conn.execute("delete from circle_contact_research_emails")
            conn.execute("delete from circle_contact_research_history")
            conn.execute("delete from circle_contact_research")
        # Use a record actually returned by the public directory, so the public
        # API privacy assertion checks the researched record itself.
        self.circle_id = self.app.search_circles({}, limit=1)[0]["circle_id"]

    def payload(self, **changes):
        record = {"circle_id": self.circle_id, "status": "email_found", "checked_at": "2026-10-11T04:00:00+00:00",
                  "sources": ["https://contact-test.example/club"],
                  "contacts": [{"email": "research-only@example.test", "source_url": "https://contact-test.example/club",
                                "evidence": "Official club contact section: research-only@example.test", "attribution": "club_page"}],
                  "note": "Private research evidence"}
        record.update(changes)
        return {"job_id": "http-test", "results": [record]}

    def call(self, path, method="GET", payload=None, admin=True, headers=None):
        request_headers = {"Accept": "application/json"}
        if admin:
            value = (self.app.ADMIN_USERNAME + ":" + self.app.ADMIN_PASSWORD).encode("utf-8")
            request_headers["Authorization"] = "Basic " + base64.b64encode(value).decode("ascii")
        data = None
        if method == "POST":
            data = json.dumps(payload, ensure_ascii=False).encode("utf-8") if payload is not None else b""
            request_headers["Content-Type"] = "application/json"
            request_headers["Origin"] = self.base
        request_headers.update(headers or {})
        req = Request(self.base + path, data=data, headers=request_headers, method=method)
        try:
            response = self.opener.open(req, timeout=10)
        except HTTPError as error:
            response = error
        with response:
            return response.status, response.read(), response.headers

    def test_unauthorized_gets_do_not_open_database(self):
        paths = ("/admin/contact-research", "/admin/contact-research.csv", "/api/admin/contact-research")
        with patch.object(self.app, "connect", side_effect=AssertionError("Unauthorized request opened DB")) as connect:
            for path in paths:
                with self.subTest(path=path):
                    status, body, headers = self.call(path, admin=False, headers={"Cookie": "cm_session=not-an-admin"})
                    self.assertEqual(status, 401)
                    self.assertIn("Basic", headers["WWW-Authenticate"])
                    self.assertNotIn(b"research-only", body)
            connect.assert_not_called()

    def test_unauthorized_import_does_not_read_body_or_open_database(self):
        with patch.object(self.app, "connect", side_effect=AssertionError("Unauthorized request opened DB")) as connect, \
             patch.object(self.app.Handler, "read_json", side_effect=AssertionError("Unauthorized request read body")) as read:
            for authorization in (None, "Basic !!!", "Basic " + base64.b64encode(b"admin:wrong-password").decode("ascii")):
                with self.subTest(authorization=authorization):
                    status, _, _ = self.call("/api/admin/contact-research/import", method="POST", admin=False,
                                             headers={"Authorization": authorization} if authorization else {})
                    self.assertEqual(status, 401)
            connect.assert_not_called()
            read.assert_not_called()

    def test_missing_admin_configuration_fails_closed_without_database(self):
        with patch.object(self.app, "ADMIN_PASSWORD", ""), \
             patch.object(self.app, "connect", side_effect=AssertionError("Unconfigured admin request opened DB")) as connect:
            for path in ("/admin/contact-research", "/admin/contact-research.csv", "/api/admin/contact-research"):
                with self.subTest(path=path):
                    status, body, _ = self.call(path, admin=False)
                    self.assertEqual(status, 503, body)
            status, body, _ = self.call("/api/admin/contact-research/import", method="POST", admin=False)
            self.assertEqual(status, 503, body)
            connect.assert_not_called()

    def test_authenticated_import_does_not_publish_or_enqueue_email(self):
        with self.app.connect() as conn:
            before_public = conn.execute("select * from circle_public_profiles where circle_id=?", (self.circle_id,)).fetchall()
            before_private = conn.execute("select * from circle_private_profiles where circle_id=?", (self.circle_id,)).fetchall()
            notifications = conn.execute("select count(*) from event_notifications").fetchone()[0]
            outbox = conn.execute("select count(*) from event_email_outbox").fetchone()[0]
        status, body, headers = self.call("/api/admin/contact-research/import", method="POST", payload=self.payload())
        self.assertEqual(status, 200, body)
        self.assertEqual(json.loads(body)["imported"]["updated"], 1)
        self.assertEqual(headers["Cache-Control"], "no-store")
        with self.app.connect() as conn:
            self.assertEqual(conn.execute("select * from circle_public_profiles where circle_id=?", (self.circle_id,)).fetchall(), before_public)
            self.assertEqual(conn.execute("select * from circle_private_profiles where circle_id=?", (self.circle_id,)).fetchall(), before_private)
            self.assertEqual(conn.execute("select count(*) from event_notifications").fetchone()[0], notifications)
            self.assertEqual(conn.execute("select count(*) from event_email_outbox").fetchone()[0], outbox)
        status, public, _ = self.call("/api/circles?limit=500", admin=False)
        self.assertEqual(status, 200)
        self.assertIn(self.circle_id, [row["circle_id"] for row in json.loads(public)])
        self.assertNotIn(b"research-only@example.test", public)
        self.assertNotIn(b"Private research evidence", public)

    def test_authenticated_views_are_private_and_admin_json_has_provenance(self):
        self.assertEqual(self.call("/api/admin/contact-research/import", method="POST", payload=self.payload())[0], 200)
        for path, content_type in (("/admin/contact-research", "text/html"),
                                   ("/admin/contact-research.csv", "text/csv"),
                                   ("/api/admin/contact-research", "application/json")):
            with self.subTest(path=path):
                status, body, headers = self.call(path + "?status=email_found&page=1")
                self.assertEqual(status, 200, body)
                self.assertEqual(headers.get_content_type(), content_type)
                self.assertEqual(headers["Cache-Control"], "private, no-store")
                self.assertEqual(headers["X-Robots-Tag"], "noindex, nofollow")
                self.assertEqual(headers["Referrer-Policy"], "no-referrer")
                self.assertEqual(headers["X-Content-Type-Options"], "nosniff")
                self.assertIn(b"research-only@example.test", body)
                if content_type == "application/json":
                    data = json.loads(body)
                    self.assertEqual(data["total"], 1)
                    self.assertEqual(data["results"][0]["contacts"][0]["source_url"], "https://contact-test.example/club")
                if content_type == "text/csv":
                    self.assertIn("attachment", headers["Content-Disposition"])
                    self.assertTrue(body.startswith(b"\xef\xbb\xbf"))
                if content_type == "text/html":
                    self.assertIn(b'name="robots" content="noindex,nofollow"', body)
                    self.assertNotIn(b"<script", body.lower())
                    self.assertNotIn(b"adsbygoogle", body.lower())

    def test_bad_import_is_atomic(self):
        payload = self.payload()
        payload["results"].append(dict(payload["results"][0], circle_id="not-a-real-circle"))
        status, body, _ = self.call("/api/admin/contact-research/import", method="POST", payload=payload)
        self.assertEqual(status, 400, body)
        with self.app.connect() as conn:
            self.assertEqual(conn.execute("select count(*) from circle_contact_research").fetchone()[0], 0)

    def test_cross_site_or_non_json_import_never_opens_database(self):
        cases = (({"Origin": "https://unrelated.example"}, 403), ({"Sec-Fetch-Site": "cross-site"}, 403),
                 ({"Content-Type": "text/plain"}, 400), ({"Content-Type": "application/x-www-form-urlencoded"}, 400))
        with patch.object(self.app, "connect", side_effect=AssertionError("Rejected request opened DB")) as connect:
            for headers, expected in cases:
                with self.subTest(headers=headers):
                    status, body, _ = self.call("/api/admin/contact-research/import", method="POST", headers=headers)
                    self.assertEqual(status, expected, body)
            connect.assert_not_called()

    def test_oversized_or_negative_declared_import_never_opens_database(self):
        with patch.object(self.app, "connect", side_effect=AssertionError("Oversized request opened DB")) as connect:
            for size in (-1, self.app.contact_research.MAX_PAYLOAD_BYTES + 1):
                with self.subTest(size=size):
                    status, body, _ = self.call("/api/admin/contact-research/import", method="POST", headers={"Content-Length": str(size)})
                    self.assertEqual(status, 400, body)
            connect.assert_not_called()

    def test_invalid_admin_view_filter_returns_bad_request(self):
        for path in ("/api/admin/contact-research?page=abc", "/api/admin/contact-research?page=0",
                     "/api/admin/contact-research?status=invalid"):
            with self.subTest(path=path):
                status, body, _ = self.call(path)
                self.assertEqual(status, 400, body)


if __name__ == "__main__":
    unittest.main()
