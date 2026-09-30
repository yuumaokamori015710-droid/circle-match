"""Loopback-only operation walkthrough with disposable data and no outgoing email."""
import tempfile
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote
from test_event_flow import load_app, user, create_account, event_payload


def main():
    with tempfile.TemporaryDirectory() as directory:
        app = load_app(Path(directory) / 'preview.sqlite')
        app.EMAIL_NOTIFICATIONS_ENABLED = False
        app.init_db()
        accounts = {role: user('qa_' + role, role + '@example.test', name) for role, name in
                    [('host', 'テスト主催者'), ('participant', 'テスト参加者'), ('visitor', '質問する人')]}
        sessions = {}
        for role, account in accounts.items():
            create_account(app, account)
            with app.connect() as conn:
                sessions['/qa/' + role] = app.create_user_session(conn, account['user_id'])
        payload = event_payload('ローカル確認用 ピックルボール交流会', capacity=8)
        payload.update(minimum_participants=2, payment_method='bank_transfer')
        with app.connect() as conn:
            eid = app.save_event_post(conn, payload, accounts['host'])
        with app.connect() as conn:
            app.submit_event_application(conn, eid, dict(participation_type='individual', applicant_name='申込代表者', participant_count=3), accounts['participant'])
        with app.connect() as conn:
            app.announce_event(conn, eid, dict(version=0, starts_at='2030-06-01T10:00', location='テスト体育館',
                announcement_details='入口に集合してください。貸出ラケットがあります。',
                attendance_deadline='2030-05-29T18:00', payment_deadline='2030-05-31T18:00',
                bank_transfer_details='テスト用口座（実在しません）'), accounts['host'])

        class PreviewHandler(app.Handler):
            def do_GET(self):
                if self.path in sessions:
                    self.redirect('/mypage', [f'cm_session={sessions[self.path]}; Path=/; HttpOnly; SameSite=Lax'])
                    return
                if self.path == '/qa/event':
                    self.redirect('/events/' + quote(eid, safe=''))
                    return
                super().do_GET()

        with ThreadingHTTPServer(('127.0.0.1', 8895), PreviewHandler) as server:
            print('Local operations fixture: http://127.0.0.1:8895/qa/participant', flush=True)
            server.serve_forever()


if __name__ == '__main__':
    main()
