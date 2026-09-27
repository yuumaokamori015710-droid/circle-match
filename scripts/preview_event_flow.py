"""Disposable, loopback-only UI fixture. Never deploy this entry point."""
import tempfile
from http.server import ThreadingHTTPServer
from pathlib import Path
from test_event_flow import load_app, user, create_account


def main():
    with tempfile.TemporaryDirectory() as directory:
        app = load_app(Path(directory) / 'preview.sqlite')
        app.EMAIL_NOTIFICATIONS_ENABLED = False
        app.init_db()
        sessions = {}
        for role, name in [('host', 'テスト主催者'), ('participant', 'テスト参加者')]:
            account = user('qa_' + role, role + '@example.test', name)
            create_account(app, account)
            with app.connect() as conn:
                sessions['/qa/' + role] = app.create_user_session(conn, account['user_id'])

        class PreviewHandler(app.Handler):
            def do_GET(self):
                if self.path in sessions:
                    self.redirect('/mypage', [f'cm_session={sessions[self.path]}; Path=/; HttpOnly; SameSite=Lax'])
                    return
                super().do_GET()

        with ThreadingHTTPServer(('127.0.0.1', 8894), PreviewHandler) as server:
            print('Temporary UI fixture: http://127.0.0.1:8894/qa/host', flush=True)
            server.serve_forever()


if __name__ == '__main__':
    main()
