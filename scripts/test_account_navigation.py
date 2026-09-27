"""Account navigation and logout against isolated SQLite and a real HTTP server."""
import html
import json
import re
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlencode, quote, urlparse, parse_qs

from test_event_flow import load_app, user, create_account, event_payload


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None


class AccountNavigationTest(unittest.TestCase):
    def test_signin_header_and_public_back_destinations(self):
        with tempfile.TemporaryDirectory() as folder:
            app = load_app(Path(folder) / 'signin.sqlite')
            owner = user('host', 'host@example.test', '主催者')
            create_account(app, owner)
            with app.connect() as conn:
                session = app.create_user_session(conn, owner['user_id'])
            filters = urlencode({'sport': 'サッカー・フットサル', 'region': 'kanto'})
            cases = (
                ('/events/new?' + filters, '/events?' + filters),
                ('/events/new?copy=private-id&' + filters, '/events?' + filters),
                ('/events/event-123/apply', '/events/event-123'),
                ('/circles?' + filters, '/circles?' + filters),
                ('/mypage', '/'),
                ('/signin', '/'),
                ('//evil.example/path', '/'),
            )
            for return_to, expected_back in cases:
                for session_id in ('', session):
                    with self.subTest(return_to=return_to, authenticated=bool(session_id)):
                        body = app.render_signin_html(return_to)
                        page = app.personalize_navigation(body, session_id, '/signin').decode()
                        header = page.split('<header', 1)[1].split('</header>', 1)[0]
                        self.assertNotIn('id="accountLink"', header)
                        self.assertNotIn('>ログイン</a>', header)
                        self.assertNotIn('action="/logout"', header)
                        self.assertIn('aria-label="Circle Match"', header)
                        back = re.search(r'<a class="back-link" href="([^"]+)"', header)
                        self.assertIsNotNone(back)
                        self.assertEqual(html.unescape(back[1]), expected_back)
                        self.assertIn('aria-label="戻る"', header)
                        self.assertIn('>募集を探す</a>', header)
                        self.assertIn('Google でログイン', page)
                        self.assertIn('メールアドレスでログイン', page)

    def test_hosting_login_gate_and_saved_basics(self):
        with tempfile.TemporaryDirectory() as folder:
            app = load_app(Path(folder) / 'hosting.sqlite')
            owner = user('host', 'host@example.test', '初回の主催者')
            other = user('other', 'other@example.test', '別の主催者')
            for account in (owner, other):
                create_account(app, account)

            def initial(params):
                page = app.render_event_form_html(params, owner)
                return json.loads(re.search(r'const initialEvent=(.*?), defaultEmail=', page)[1])

            self.assertIsNone(app.render_event_form_html({}, {'authenticated': False}))
            first = initial({'sport': ['サッカー・フットサル']})
            self.assertEqual(first['organizer_name'], owner['display_name'])
            self.assertEqual(first['organizer_contact_email'], owner['email'])
            with app.connect() as conn:
                saved = event_payload('主催者の以前の募集')
                saved.update(organizer_name='保存した主催チーム', organizer_contact_email='team@example.test')
                event_id = app.save_event_post(conn, saved, owner)
                app.save_event_post(conn, event_payload('他人の募集'), other)
                session = app.create_user_session(conn, owner['user_id'])
            returning = initial({'sport': ['サッカー・フットサル']})
            self.assertEqual(returning['organizer_name'], '保存した主催チーム')
            self.assertEqual(returning['organizer_contact_email'], 'team@example.test')
            self.assertEqual(returning['sport_category'], 'サッカー・フットサル')
            self.assertNotIn('title', returning)
            self.assertNotIn('linked_circle_id', returning, 'never infer organization authority')
            edited = initial({'event_id': [event_id]})
            self.assertEqual(edited['title'], saved['title'])
            copied = initial({'copy': [event_id]})
            self.assertEqual(copied['organizer_contact_email'], 'team@example.test')
            self.assertNotIn('starts_at', copied)

            server = ThreadingHTTPServer(('127.0.0.1', 0), app.Handler)
            threading.Thread(target=server.serve_forever, daemon=True).start()
            base = f'http://127.0.0.1:{server.server_port}'
            target = '/events/new?' + urlencode({'sport': 'サッカー・フットサル', 'region': 'kanto'})
            try:
                for path in (target, '/events/new?' + urlencode({'event_id': event_id}),
                             '/events/new?' + urlencode({'copy': event_id})):
                    with urllib.request.urlopen(base + path) as response:
                        destination = urlparse(response.geturl())
                        self.assertEqual(destination.path, '/signin')
                        self.assertEqual(parse_qs(destination.query)['return_to'][0], path)
                        page = response.read().decode()
                        self.assertIn('ログインすると、基本情報の登録が簡単になります。', page)
                        self.assertIn('Google でログイン', page)
                        self.assertIn('メールアドレスでログイン', page)
                        self.assertNotIn('id="eventForm"', page)
                request = urllib.request.Request(base + target, headers={'Cookie': 'cm_session=' + session})
                with urllib.request.urlopen(request) as response:
                    self.assertEqual(response.geturl(), base + target)
                    self.assertIn('id="eventForm"', response.read().decode())
                general = app.render_signin_html('/mypage').decode()
                self.assertNotIn('募集掲載の前に、ログイン', general)
                external = app.render_signin_html('//evil.example/events/new').decode()
                self.assertIn('const returnTo = "/";', external)
                self.assertNotIn('evil.example', external)
            finally:
                server.shutdown()
                server.server_close()

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
