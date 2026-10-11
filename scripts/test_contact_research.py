"""Private contact research integrity; isolated in-memory SQLite, no network."""
import csv
from io import StringIO
import importlib.util
import json
from pathlib import Path
import sqlite3
import unittest


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location("contact_research_under_test", ROOT / "outputs" / "circlematch_contact_research.py")
research = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(research)


class ContactResearchTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(":memory:")
        self.addCleanup(self.conn.close)
        self.conn.execute("pragma foreign_keys=on")
        self.conn.executescript("""
            create table circles(circle_id text primary key,circle_name text,source_url text);
            create table circle_public_profiles(circle_id text,public_contact_email text,public_contact_consent integer);
            create table circle_private_profiles(circle_id text,internal_notes text);
            create table event_notifications(notification_id text);
            create table event_email_outbox(notification_id text);
            insert into circles values('club-a','Alpha tennis','https://clubs.example/alpha');
            insert into circles values('club-b','Beta tennis','https://clubs.example/beta');
            insert into circles values('club-c','Gamma tennis','');
            insert into circle_public_profiles values('club-a','owner-consented@example.test',1);
            insert into circle_private_profiles values('club-a','existing private notes');
        """)
        research.ensure_tables(self.conn)

    def record(self, circle_id="club-a", **changes):
        record = {"circle_id": circle_id, "status": "email_found", "checked_at": "2026-10-11T12:00:00+09:00",
            "sources": [{"url": "https://clubs.example/alpha", "evidence": "Alpha tennis club contact page"}],
            "contacts": [{"email": "tennis@CLUBS.example", "source_url": "https://clubs.example/alpha",
                "evidence": "Alpha tennis club: tennis@clubs.example", "attribution": "club_page"}],
            "note": "Found in the club's contact section"}
        record.update(changes)
        return record

    def import_one(self, **changes):
        return research.import_results(self.conn, {"job_id": "test-job", "results": [self.record(**changes)]})

    def count(self, table):
        return self.conn.execute("select count(*) from " + table).fetchone()[0]

    def test_private_import_has_provenance_and_does_not_change_profiles_or_send_mail(self):
        before_public = self.conn.execute("select * from circle_public_profiles").fetchall()
        before_private = self.conn.execute("select * from circle_private_profiles").fetchall()
        self.assertEqual(self.import_one()["updated"], 1)
        row = research.query_results(self.conn, status="email_found")["results"][0]
        self.assertEqual(row["contacts"][0]["email"], "tennis@clubs.example")
        self.assertEqual(row["contacts"][0]["attribution"], "club_page")
        self.assertEqual(row["checked_at"], "2026-10-11T03:00:00+00:00")
        self.assertIn("Alpha tennis", row["contacts"][0]["evidence"])
        self.assertEqual(self.conn.execute("select * from circle_public_profiles").fetchall(), before_public)
        self.assertEqual(self.conn.execute("select * from circle_private_profiles").fetchall(), before_private)
        self.assertEqual(self.count("event_notifications"), 0)
        self.assertEqual(self.count("event_email_outbox"), 0)

    def test_summary_includes_unresearched_circles(self):
        self.import_one()
        research.import_results(self.conn, [self.record("club-b", status="no_email", contacts=[])])
        summary = research.summary(self.conn)
        self.assertEqual((summary["total"], summary["researched"], summary["remaining"], summary["with_email"]), (3, 2, 1, 1))
        self.assertEqual(summary["distinct_emails"], 1)
        self.assertEqual(summary["statuses"]["no_email"], 1)
        self.assertEqual(research.query_results(self.conn, status="unresearched")["results"][0]["circle_id"], "club-c")

    def test_bad_record_in_batch_prevents_all_writes(self):
        with self.assertRaises(ValueError):
            research.import_results(self.conn, [self.record(), self.record("club-b", status="invented")])
        self.assertEqual(self.count("circle_contact_research"), 0)
        self.assertEqual(self.count("circle_contact_research_history"), 0)

    def test_unknown_circle_prevents_entire_batch(self):
        with self.assertRaisesRegex(ValueError, "存在しない"):
            research.import_results(self.conn, [self.record(), self.record("unknown")])
        self.assertEqual(self.count("circle_contact_research"), 0)

    def test_database_failure_rolls_back_whole_batch(self):
        self.conn.execute("""create trigger force_research_failure before insert on circle_contact_research
            when new.circle_id='club-b' begin select raise(abort,'forced failure'); end""")
        with self.assertRaises(sqlite3.IntegrityError):
            research.import_results(self.conn, [self.record(), self.record("club-b")])
        self.assertEqual(self.count("circle_contact_research"), 0)
        self.assertEqual(self.count("circle_contact_research_emails"), 0)
        self.assertEqual(self.count("circle_contact_research_history"), 0)

    def test_outer_transaction_remains_controlled_by_caller(self):
        self.conn.execute("insert into circles values('extra','Outer change','')")
        self.import_one()
        self.conn.rollback()
        self.assertEqual(self.count("circle_contact_research"), 0)
        self.assertEqual(self.count("circles"), 3)

    def test_retry_is_idempotent_and_changed_result_retains_history(self):
        self.assertEqual(self.import_one()["updated"], 1)
        self.assertEqual(self.import_one()["unchanged"], 1)
        self.assertEqual(self.count("circle_contact_research_history"), 1)
        self.assertEqual(self.import_one(status="no_email", contacts=[], note="Address removed from official page")["updated"], 1)
        self.assertEqual(self.count("circle_contact_research_emails"), 0)
        history = self.conn.execute("select result_json from circle_contact_research_history order by revision_id").fetchall()
        self.assertEqual(len(history), 2)
        self.assertEqual(json.loads(history[0][0])["contacts"][0]["email"], "tennis@clubs.example")
        self.assertEqual(json.loads(history[1][0])["status"], "no_email")

    def test_duplicate_batch_circle_rejected_and_contact_duplicates_collapsed(self):
        with self.assertRaisesRegex(ValueError, "重複"):
            research.import_results(self.conn, [self.record(), self.record()])
        record = self.record()
        record["contacts"].append(dict(record["contacts"][0], email="tennis@clubs.example"))
        research.import_results(self.conn, [record])
        self.assertEqual(self.count("circle_contact_research_emails"), 1)

    def test_missing_or_ambiguous_email_evidence_rejected(self):
        for changes in ({"contacts": []}, {"status": "review_needed"}, {"status": "no_email"}):
            with self.subTest(changes=changes), self.assertRaises(ValueError):
                self.import_one(**changes)
        for field, value in (("email", "not-an-email"), ("email", "mail\r\nBcc:hack@clubs.example"),
                             ("email", ".dots@clubs.example"), ("email", "a..b@clubs.example"),
                             ("email", "mail@localhost"), ("source_url", "javascript:alert(1)"),
                             ("attribution", "university_general"), ("evidence", "")):
            contact = dict(self.record()["contacts"][0], **{field: value})
            with self.subTest(field=field, value=value), self.assertRaises(ValueError):
                self.import_one(contacts=[contact])
        self.assertEqual(self.count("circle_contact_research"), 0)

    def test_sources_and_forms_reject_local_credential_and_invalid_urls(self):
        urls = ("ftp://clubs.example/contact", "https://user:password@clubs.example/contact", "http://localhost/",
                "http://127.0.0.1/", "http://169.254.169.254/", "http://10.1.1.1/", "http://[::1]/",
                "http://2130706433/", "http://127.1/", "http://0x7f.0.0.1/", "http://0177.0.0.1/",
                "https://printer.local/", "https://intranet.internal/", "https://clubs.example:8123/",
                "https://clubs.example\\@127.0.0.1/", "https://clubs.example/line\nbreak")
        for url in urls:
            with self.subTest(url=url), self.assertRaises(ValueError):
                self.import_one(sources=[url])
            with self.subTest(form=url), self.assertRaises(ValueError):
                self.import_one(status="contact_form", contacts=[], contact_form_url=url)
        self.import_one(status="contact_form", contacts=[], contact_form_url="https://clubs.example/contact")
        self.assertEqual(research.summary(self.conn)["statuses"]["contact_form"], 1)

    def test_payload_types_size_and_unknown_fields_rejected(self):
        cases = (None, "payload", {}, {"results": []}, {"results": "bad"}, {"results": [self.record()], "unknown": True},
                 {"results": [self.record()], "job_id": 3}, {"results": [self.record(contacts={})]},
                 {"results": [self.record(sources="bad")]}, {"results": [self.record(unknown="bad")]},
                 {"results": [self.record(note=4)]}, {"results": [self.record(checked_at="2026-10-11")]},
                 {"results": [self.record(checked_at=12)]}, {"results": [self.record(note="x" * 4001)]},
                 {"results": [self.record()] * 1001})
        for payload in cases:
            with self.subTest(payload=str(payload)[:80]), self.assertRaises(ValueError):
                research.import_results(self.conn, payload)
        self.assertEqual(self.count("circle_contact_research"), 0)

    def test_query_pagination_email_search_and_invalid_filters(self):
        self.import_one()
        first = research.query_results(self.conn, page_size=2)
        second = research.query_results(self.conn, page=2, page_size=2)
        self.assertEqual((first["total"], first["pages"], len(first["results"]), len(second["results"])), (3, 2, 2, 1))
        self.assertEqual(research.query_results(self.conn, q="tennis@clubs")["total"], 1)
        self.assertEqual(research.query_results(self.conn, q="' OR 1=1 --")["total"], 0)
        for arguments in ({"status": "invalid"}, {"page": 0}, {"page": "1"}, {"page": True}, {"page_size": 201}):
            with self.subTest(arguments=arguments), self.assertRaises(ValueError):
                research.query_results(self.conn, **arguments)

    def test_admin_html_escapes_untrusted_names_notes_evidence_and_query(self):
        self.conn.execute("update circles set circle_name=?,source_url=? where circle_id='club-a'",
                          ('<script>alert("club")</script>', 'javascript:alert("source")'))
        record = self.record(note='<img src=x onerror="alert(1)">')
        record["contacts"][0]["evidence"] = '<svg onload="alert(2)"> public contact'
        research.import_results(self.conn, [record])
        data = research.query_results(self.conn)
        data["q"] = '\" autofocus onfocus=\"alert(3)'
        rendered = research.render_admin_html(data)
        self.assertNotIn("<script>", rendered)
        self.assertNotIn("<img src=x", rendered)
        self.assertNotIn("<svg onload=", rendered)
        self.assertNotIn('href="javascript:', rendered)
        self.assertIn("&lt;script&gt;", rendered)
        self.assertIn("&lt;svg", rendered)
        self.assertIn('value="&quot; autofocus', rendered)
        self.assertIn('name="robots" content="noindex,nofollow"', rendered)
        self.assertIn('rel="noopener noreferrer"', rendered)
        self.assertIn('href="mailto:tennis@clubs.example"', rendered)

    def test_csv_includes_all_circles_and_prevents_spreadsheet_formulas(self):
        self.conn.execute("update circles set circle_name='=HYPERLINK(\"bad\")' where circle_id='club-b'")
        self.import_one(note="+SUM(1,2)")
        data = list(csv.DictReader(StringIO(research.export_csv(self.conn))))
        self.assertEqual(len(data), 3)
        by_id = {row["circle_id"]: row for row in data}
        self.assertEqual(by_id["club-a"]["email"], "tennis@clubs.example")
        self.assertEqual(by_id["club-a"]["research_note"], "'+SUM(1,2)")
        self.assertTrue(by_id["club-b"]["circle_name"].startswith("'="))
        self.assertEqual(by_id["club-c"]["status"], "unresearched")

    def test_schema_initialization_is_repeatable_and_does_not_commit_outer_work(self):
        self.conn.execute("insert into circles values('not-committed','Temporary club','')")
        research.ensure_tables(self.conn)
        research.ensure_tables(self.conn)
        self.conn.rollback()
        self.assertEqual(self.count("circles"), 3)


if __name__ == "__main__":
    unittest.main()
