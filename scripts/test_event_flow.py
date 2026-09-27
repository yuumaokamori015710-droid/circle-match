"""End-to-end checks for the event posting and application domain.

This test uses a temporary SQLite file. It validates business rules directly and
through the HTTP handler without touching the developer or Render database.
"""

import importlib.util
import json
import os
import sqlite3
import tempfile
import threading
import urllib.error
import urllib.request
from contextlib import closing
from urllib.parse import quote, unquote, parse_qs, urlparse
from pathlib import Path
from http.server import ThreadingHTTPServer


ROOT = Path(__file__).resolve().parents[1]
APP_PATH = ROOT / "outputs" / "circlematch_db_app.py"


def load_app(database_path):
    os.environ["CIRCLEMATCH_DB_PATH"] = str(database_path)
    os.environ["CIRCLEMATCH_ADMIN_PASSWORD"] = "event-flow-test"
    spec = importlib.util.spec_from_file_location("circlematch_event_flow", APP_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.init_db()
    # Reproduce Render's original payment CHECK before populating real relations.
    with closing(sqlite3.connect(database_path)) as conn, conn:
        schema = conn.execute("select sql from sqlite_master where name='event_posts'").fetchone()[0]
        conn.execute("drop table event_posts")
        conn.execute(schema.replace("'free','on_site','bank_transfer'", "'free','on_site'"))
        conn.execute("create index idx_event_posts_public on event_posts(status, starts_at, sport_category, prefecture)")
    return module


def user(user_id, email, name):
    return {"authenticated": True, "user_id": user_id, "email": email, "display_name": name}


def create_account(app, account):
    with app.connect() as conn:
        conn.execute(
            """
            insert into user_accounts(user_id,provider,provider_subject,email,display_name,picture_url,created_at,updated_at)
            values(?,?,?,?,?,?,?,?)
            """,
            (
                account["user_id"], "test", account["user_id"], account["email"], account["display_name"], "", app.now(), app.now()
            ),
        )


def event_payload(title, acceptance_mode="first_come", participation_type="individual", capacity="2"):
    return {
        "event_type": "大会",
        "sport_category": "ピックルボール",
        "title": title,
        "starts_at": "2030-06-01T10:00",
        "ends_at": "2030-06-01T14:00",
        "prefecture": "東京都",
        "location": "テストスポーツセンター",
        "description": "実際の参加フローを確認するためのテスト募集です。",
        "participation_type": participation_type,
        "capacity": capacity,
        "capacity_unit": "チーム" if participation_type == "team" else "人",
        "eligibility": "どなたでも参加できます",
        "fee_amount": "1000",
        "fee_unit": "1チーム" if participation_type == "team" else "1人",
        "payment_method": "on_site",
        "application_deadline": "2030-05-30T18:00",
        "acceptance_mode": acceptance_mode,
        "organizer_name": "テスト主催者",
        "organizer_contact_email": "host@example.test",
        "cancellation_policy": "テスト用の条件です",
        "status": "published",
    }


def request_json(url, method="GET", data=None, cookie=""):
    headers = {"Accept": "application/json"}
    if cookie:
        headers["Cookie"] = cookie
    body = None
    if data is not None:
        headers["Content-Type"] = "application/json"
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    with urllib.request.urlopen(request, timeout=10) as response:
        return response.status, json.loads(response.read().decode("utf-8"))


def main():
    with tempfile.TemporaryDirectory() as temporary:
        app = load_app(Path(temporary) / "event-flow.sqlite")
        host = user("user_host", "host@example.test", "主催者")
        first = user("user_first", "first@example.test", "参加者1")
        second = user("user_second", "second@example.test", "参加者2")
        for account in (host, first, second):
            create_account(app, account)

        with app.connect() as conn:
            first_come_id = app.save_event_post(conn, event_payload("先着順テスト大会"), host)
        with app.connect() as conn:
            application = app.submit_event_application(
                conn, first_come_id,
                {"participation_type": "individual", "applicant_name": "参加者1", "participant_count": 1}, first,
            )
        assert application["status"] == "confirmed"
        with app.connect() as conn:
            try:
                app.submit_event_application(
                    conn, first_come_id,
                    {"participation_type": "individual", "applicant_name": "重複", "participant_count": 1}, first,
                )
                raise AssertionError("duplicate application was accepted")
            except ValueError as exc:
                assert "すでに申し込み済み" in str(exc)

        with app.connect() as conn:
            approval_id = app.save_event_post(
                conn, event_payload("承認制テスト大会", "approval", "team", "2"), host
            )
        with app.connect() as conn:
            pending = app.submit_event_application(
                conn, approval_id,
                {
                    "participation_type": "team", "team_name": "テストチーム",
                    "representative_name": "参加者2", "participant_count": 2,
                }, second,
            )
        assert pending["status"] == "pending"
        with app.connect() as conn:
            assert app.set_event_application_status(conn, approval_id, pending["application_id"], "confirm", host) == "confirmed"
            app.send_event_message(
                conn, approval_id,
                {"body": "参加確定です", "recipient_user_id": second["user_id"]}, host,
            )
        messages = app.event_messages_for_user(approval_id, second)
        assert any(message["body"] == "参加確定です" for message in messages)
        with app.connect() as conn:
            tables = ("event_posts", "event_applications", "event_notifications", "event_messages")
            before = {table: [tuple(row) for row in conn.execute(f"select * from {table} order by rowid")] for table in tables}
            app.migrate_event_payment_methods(conn)
            assert conn.execute("pragma foreign_keys").fetchone()[0] == 1
            assert not conn.execute("pragma foreign_key_check").fetchall()
            for table in tables:
                assert before[table] == [tuple(row) for row in conn.execute(f"select * from {table} order by rowid")]
            assert conn.execute("select 1 from sqlite_master where name='idx_event_posts_public'").fetchone()
            app.migrate_event_payment_methods(conn)
        backups = list(Path(temporary).glob("*.pre-bank-transfer-*.sqlite"))
        assert len(backups) == 1
        with closing(sqlite3.connect(backups[0])) as backup:
            assert backup.execute("select count(*) from event_applications").fetchone()[0] == 2
        bank = event_payload("口座振込・終了時刻なしの大会")
        bank.pop("ends_at")
        bank["payment_method"] = "bank_transfer"
        with app.connect() as conn:
            bank_id = app.save_event_post(conn, bank, host)
        assert app.get_event(bank_id)["ends_at"] is None
        assert app.get_event(bank_id)["payment_method"] == "bank_transfer"
        assert app.event_fee_text({"payment_method": "bank_transfer"}).startswith("口座振込")
        bank["payment_method"] = "credit_card"
        with app.connect() as conn:
            try:
                app.save_event_post(conn, bank, host)
                raise AssertionError("unsupported payment method was accepted")
            except ValueError:
                pass
        with app.connect() as conn:
            app.cancel_event_application(conn, first_come_id, application["application_id"], first)
            app.set_event_status(conn, approval_id, "cancelled", host)

        published = app.search_events({"sport": ["ピックルボール"]})
        assert any(item["event_id"] == first_come_id for item in published)
        football = event_payload("サッカー募集の遷移確認大会")
        football["sport_category"] = "サッカー・フットサル"
        with app.connect() as conn:
            app.save_event_post(conn, football, host)
        with app.connect() as conn:
            try:
                app.event_owner(conn, approval_id, first["user_id"])
                raise AssertionError("non-owner could manage event")
            except PermissionError:
                pass

        server = ThreadingHTTPServer(("127.0.0.1", 0), app.Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        base = f"http://127.0.0.1:{server.server_address[1]}"
        try:
            with urllib.request.urlopen(base + "/", timeout=10) as response:
                home = response.read().decode("utf-8")
            assert "大会・イベント" in home and "ピックルボール" in home and "先着順テスト大会" in home
            football_query = "sport=" + quote("サッカー・フットサル") + "&region=kanto&date_from=2030-05-01"
            with urllib.request.urlopen(base + "/events?" + football_query, timeout=10) as response:
                assert response.geturl() == base + "/events?" + football_query
                listing = response.read().decode("utf-8")
            assert "サッカー・フットサル<span>大会・イベント</span>" in listing
            assert "サッカー募集の遷移確認大会" in listing and "先着順テスト大会" not in listing
            assert 'class="sport-grid"' not in listing and '/assets/sports/soccer.png' in listing
            assert 'id="eventResultCount" role="status">1件を表示' in listing
            assert "date_from=2030-05-01" in listing
            with urllib.request.urlopen(base + "/events?sport=" + quote("ラグビー"), timeout=10) as response:
                empty_listing = response.read().decode("utf-8")
            assert "現在、ラグビーの募集中の大会・イベントはありません。" in empty_listing
            assert 'id="eventResultCount" role="status">0件を表示' in empty_listing
            with urllib.request.urlopen(base + "/events/new?sport=%E3%83%94%E3%83%83%E3%82%AF%E3%83%AB%E3%83%9C%E3%83%BC%E3%83%AB", timeout=10) as response:
                form = response.read().decode("utf-8")
            assert "募集を掲載する" in form and '"sport_category": "ピックルボール"' in form
            assert 'id="ends_at" type="hidden"' in form and "終了日時（任意）" not in form
            assert '<option value="bank_transfer">口座振込</option>' in form
            with urllib.request.urlopen(base + f"/events/{quote(bank_id)}", timeout=10) as response:
                detail = response.read().decode("utf-8")
            assert "口座振込" in detail and "ログインして参加を申し込む" in detail
            with urllib.request.urlopen(base + f"/events/{quote(bank_id)}/apply", timeout=10) as response:
                redirect = urlparse(response.geturl())
                assert redirect.path == "/signin"
                assert unquote(parse_qs(redirect.query)["return_to"][0]) == f"/events/{bank_id}/apply"
                assert 'id="applicationForm"' not in response.read().decode("utf-8")
            try:
                request_json(base + f"/api/events/{quote(bank_id)}/applications", method="POST", data={})
                raise AssertionError("unauthenticated application was accepted")
            except urllib.error.HTTPError as exc:
                assert exc.code == 401
            with app.connect() as conn:
                session_id = app.create_user_session(conn, host["user_id"])
                participant_session_id = app.create_user_session(conn, second["user_id"])
            request = urllib.request.Request(base + f"/events/{quote(bank_id)}/apply", headers={"Cookie": f"cm_session={participant_session_id}"})
            with urllib.request.urlopen(request, timeout=10) as response:
                assert 'id="applicationForm"' in response.read().decode("utf-8")
            status, mine = request_json(base + "/api/events/mine", cookie=f"cm_session={session_id}")
            assert status == 200 and any(item["event_id"] == approval_id for item in mine["hosted"])
            status, result = request_json(
                base + f"/api/events/{quote(approval_id)}/applications",
                method="GET", cookie=f"cm_session={session_id}",
            )
            assert status == 200 and result[0]["application_id"] == pending["application_id"]
            status, created = request_json(
                base + "/api/events", method="POST", data=event_payload("HTTP掲載テスト大会"),
                cookie=f"cm_session={session_id}",
            )
            assert status == 200 and created["event_id"]
            http_event_id = created["event_id"]
            status, applied = request_json(
                base + f"/api/events/{quote(http_event_id)}/applications", method="POST",
                data={"participation_type": "individual", "applicant_name": "参加者2", "participant_count": 1},
                cookie=f"cm_session={participant_session_id}",
            )
            assert status == 200 and applied["status"] == "confirmed"
            status, closed = request_json(
                base + f"/api/events/{quote(http_event_id)}/status", method="POST", data={"status": "closed"},
                cookie=f"cm_session={session_id}",
            )
            assert status == 200 and closed["ok"]
            with urllib.request.urlopen(base + "/events/" + quote(http_event_id), timeout=10) as response:
                detail = response.read().decode("utf-8")
            assert "HTTP掲載テスト大会" in detail and "受付終了" in detail
            assert f"/events/{quote(first_come_id)}" in app.sitemap_xml().decode("utf-8")
        finally:
            server.shutdown()
            server.server_close()
        print("event flow: ok")


if __name__ == "__main__":
    main()
