"""Loopback-only login notification preview with a disposable DB and no mail."""
from http.server import ThreadingHTTPServer
import os
from pathlib import Path
import tempfile
from urllib.parse import urlsplit

os.environ.update(CIRCLEMATCH_EMAIL_NOTIFICATIONS_ENABLED='false',CIRCLEMATCH_EMAIL_AUTH_ENABLED='false',
                  CIRCLEMATCH_RESEND_API_KEY='',CIRCLEMATCH_SUPABASE_URL='',CIRCLEMATCH_SUPABASE_ANON_KEY='',
                  CIRCLEMATCH_GOOGLE_CLIENT_ID='',CIRCLEMATCH_GOOGLE_CLIENT_SECRET='',
                  CIRCLEMATCH_SITE_BASE_URL='http://127.0.0.1:8931',CIRCLEMATCH_SESSION_SECRET='local-login-preview')
from test_event_flow import load_app, user, create_account


def main():
    work = Path(__file__).resolve().parents[1]/'work/login-security-preview'
    work.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='preview-',dir=work) as folder:
        app = load_app(Path(folder)/'preview.sqlite')
        app.init_db()
        app.ADSENSE_HEAD = ''
        app.LOG_PATH = work/'preview.log'
        account = user('security-preview-user','preview@example.test','プレビュー利用者')
        create_account(app,account)
        with app.connect() as conn:
            session = app.create_user_session(conn,account['user_id'])
            for n in range(5):
                app.login_security.record_login(conn,account['user_id'],'supabase_google','local-proof-'+str(n),
                    app.SESSION_SECRET,app.add_event_notification,app.audit)

        class Handler(app.Handler):
            def cookie_value(self,name):
                return super().cookie_value('cm_security_preview_session' if name=='cm_session' else name)

            def redirect(self,location,cookies=None):
                super().redirect(location,[value.replace('cm_session=','cm_security_preview_session=',1) for value in cookies or []])

            def do_GET(self):
                path = urlsplit(self.path).path
                if path in {'/__preview__/login-security','/__preview__/notifications'}:
                    self.redirect('/settings/security' if path.endswith('login-security') else '/notifications',
                                  [f'cm_session={session}; Path=/; HttpOnly; SameSite=Lax'])
                    return
                super().do_GET()

        with ThreadingHTTPServer(('127.0.0.1',8931),Handler) as server:
            print('http://127.0.0.1:8931/__preview__/login-security',flush=True)
            server.serve_forever()


if __name__ == '__main__':
    main()
