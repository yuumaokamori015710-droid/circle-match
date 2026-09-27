"""Account navigation and logout against isolated SQLite and a real HTTP server."""
import re
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlencode, quote

from test_event_flow import load_app, user, create_account, event_payload


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None


class AccountNavigationTest(unittest.TestCase):
    def test_server_header_and_logout(self):
        with tempfile.TemporaryDirectory() as folder:
            app = load_app(Path(folder) / 'accounts.sqlite')
            owner = user('host', 'host@example.test', '主催者')
            create_account(app, owner)
            with app.connect() as conn:
                event_id = app.save_event_post(conn, event_payload('ヘッダー確認大会'), owner)
                session = app.create_user_session(conn, owner['user_id'])
                other_session = app.create_user_session(conn, owner['user_id'])
            server = ThreadingHTTPServer(('127.0.0.1', 0), app.Handler)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            base = f'http://127.0.0.1:{server.server_port}'

            def get(path, session_id=''):
                req = urllib.request.Request(base + path, headers={'Cookie': 'cm_session=' + session_id})
                with urllib.request.urlopen(req) as response:
                    self.assertIn('no-store', response.headers['Cache-Control'])
                    return response.read().decode()

            try:
                for path in ('/', '/?tab=db', '/events', '/events/new', '/events/' + quote(event_id),
                             '/circles', '/social/circles', '/mypage'):
                    with self.subTest(path=path):
                        page = get(path, session)
                        header = page.split('</header>')[0]
                        self.assertIn('href="/mypage">マイページ</a>', header)
                        self.assertIn('method="post"', header)
                        self.assertIn('>ログアウト</button>', header)
                        self.assertNotIn('>ログイン</a>', header)
                        self.assertNotIn('host@example.test', header)
                self.assertIn('>ログイン</a>', get('/').split('</header>')[0])
                self.assertIn('>ログイン</a>', get('/', 'invalid').split('</header>')[0])
                page = get('/logout', session)
                self.assertTrue(app.current_user(session)['authenticated'], 'GET must not log out')
                token = re.search('name="csrf_token" value="([^"]+)"', page)[1]
                opener = urllib.request.build_opener(NoRedirect)
                for sent, status in (('bad-token', 403), (token, 302)):
                    req = urllib.request.Request(base + '/logout', data=urlencode({'csrf_token': sent}).encode(),
                                                 headers={'Cookie': 'cm_session=' + session})
                    with self.assertRaises(urllib.error.HTTPError) as result:
                        opener.open(req)
                    self.assertEqual(result.exception.code, status)
                    if status == 403:
                        self.assertTrue(app.current_user(session)['authenticated'])
                    else:
                        self.assertIn('Max-Age=0', result.exception.headers['Set-Cookie'])
                    result.exception.close()
                self.assertFalse(app.current_user(session)['authenticated'])
                self.assertTrue(app.current_user(other_session)['authenticated'], 'other devices stay signed in')
                self.assertIn('>ログイン</a>', get('/', session).split('</header>')[0])
            finally:
                server.shutdown()
                server.server_close()


if __name__ == '__main__':
    unittest.main()
