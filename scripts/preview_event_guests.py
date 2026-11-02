"""Loopback-only disposable guest fixture. Mail is captured, never delivered."""
import html
import json
import tempfile
from http.server import ThreadingHTTPServer
from pathlib import Path
from threading import Thread
from test_event_flow import load_app, user, create_account, event_payload


def main():
    with tempfile.TemporaryDirectory() as directory:
        app = load_app(Path(directory) / 'guest-preview.sqlite')
        app.init_db()
        app.EMAIL_NOTIFICATIONS_ENABLED = False
        app.email_notifications_ready = lambda: True
        app.ADSENSE_HEAD = ''
        inbox = []
        def capture(_key, payload):
            inbox.append(json.loads(payload))
            return 'local-preview-only'
        app.send_notification_email = capture
        host = user('guest-qa-host','host@example.test','テスト主催者')
        create_account(app,host)
        data = event_payload('ゲスト申込の動作確認',participation_type='both',capacity='')
        data.update(individual_fee_amount=2500,team_fee_amount=15000,minimum_participants=1,
                    payment_method='on_site_or_bank_transfer')
        with app.connect() as conn:
            eid = app.save_event_post(conn,data,host)
        class Preview(app.Handler):
            def do_GET(self):
                if self.path == '/qa/inbox':
                    text = '<h1>LOCAL TEST INBOX</h1>'
                    for mail in inbox:
                        link = mail['text'].splitlines()[3]
                        text += '<p><a href="'+html.escape(link,quote=True)+'">確認リンクを開く</a></p>'
                    self.send_html(text.encode())
                else:
                    super().do_GET()
        with ThreadingHTTPServer(('127.0.0.1',0),Preview) as server:
            app.SITE_BASE_URL = 'http://127.0.0.1:'+str(server.server_port)
            app.BASE_URL = app.SITE_BASE_URL
            app.EMAIL_FROM = 'local@example.test'
            worker = Thread(target=server.serve_forever,daemon=True)
            worker.start()
            print('GUEST_PREVIEW='+app.SITE_BASE_URL+'/events/'+eid,flush=True)
            try:
                input('Press Enter to stop local preview.\n')
            finally:
                server.shutdown()
                worker.join()


if __name__ == '__main__':
    main()
