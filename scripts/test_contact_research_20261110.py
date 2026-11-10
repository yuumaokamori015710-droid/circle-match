"""Verify the new public contact against the current directory data and privacy rules."""
import json
from pathlib import Path
import subprocess
import unittest
from urllib.parse import urlencode

from bs4 import BeautifulSoup

from test_venues import IsolatedAppHttpCase

ROOT = Path(__file__).resolve().parents[1]
BASE = '68f9bb73660bd4c7ed3f433e2151a8ee28b27db5'
CHECKED = '2026-11-10'
CIRCLE_ID = 'c_u_社会人サークル_東京都__社会人サークル_3885b36aa9_コー_18c2287b0e'
LISTING = 'https://www.net-menber.com/look/data/228965.html'
SOURCE = 'https://ameblo.jp/korfballclubtokyo/'
EMAIL = 'k.c.tokyo.2004@gmail.com'
SEARCH = urlencode({'audience': 'social', 'q': 'コーフボールクラブ東京'})


class November10ContactTests(IsolatedAppHttpCase):
    def result(self):
        status, body, _ = self.request('/api/circles?' + SEARCH)
        self.assertEqual(status, 200)
        return next(row for row in json.loads(body) if row['circle_id'] == CIRCLE_ID)

    def test_only_verified_contact_appended(self):
        path = 'outputs/circle_public_contacts.json'
        old = json.loads(subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT))
        current = json.loads((ROOT / path).read_bytes())
        self.assertEqual(current[:len(old)], old)
        contact, = [row for row in current[len(old):] if row['checked_at'] == CHECKED]
        self.assertEqual((contact['circle_id'], contact['circle_source_url']), (CIRCLE_ID, LISTING))
        self.assertEqual((contact['source_url'], contact['email']), (SOURCE, EMAIL))
        self.assertIn('最新記事は2017年', contact['purpose'])
        self.assertIn('受信同意は未確認', contact['purpose'])

    def test_public_directory_uses_original_identity_and_source(self):
        row = self.result()
        self.assertEqual(row['circle_name'], 'コーフボールクラブ東京')
        self.assertEqual(row['organization_type'], '社会人サークル')
        self.assertEqual(row['source_url'], LISTING)
        self.assertEqual(row['contact_source_url'], SOURCE)
        self.assertEqual(row['contact_checked_at'], CHECKED)
        self.assertEqual(row['public_contact_email'], EMAIL)
        status, body, _ = self.request('/?tab=db&' + SEARCH)
        self.assertEqual(status, 200)
        page = BeautifulSoup(body.decode(), 'html.parser')
        link = page.find('a', href='/invitations/new?' + urlencode({'circle_id': CIRCLE_ID}))
        self.assertIsNotNone(link)
        self.assertIn('公開メールあり', link.find_parent(class_='circle-row').get_text())

    def test_reimport_respects_existing_disable_and_profile_settings(self):
        store = self.app.public_contacts
        with self.app.connect() as conn:
            conn.execute('update circle_public_contacts set enabled=0 where circle_id=?', (CIRCLE_ID,))
            store.import_reviewed(conn)
        self.assertFalse(self.result()['public_contact_email'])

        with self.app.connect() as conn:
            conn.execute('update circle_public_contacts set enabled=1 where circle_id=?', (CIRCLE_ID,))
            conn.execute('''insert into circle_public_profiles
                (profile_id,circle_id,profile_slug,public_contact_consent,is_published,created_at,updated_at)
                values(?,?,?,0,1,?,?)''',
                ('kct-test', CIRCLE_ID, 'kct-test', self.app.now(), self.app.now()))
            store.import_reviewed(conn)
        self.assertFalse(self.result()['public_contact_email'])

        with self.app.connect() as conn:
            conn.execute('update circle_public_profiles set public_contact_consent=1,is_published=0 where circle_id=?',
                         (CIRCLE_ID,))
            store.import_reviewed(conn)
        self.assertFalse(self.result()['public_contact_email'])
