"""Exercise the reviewed contact against the seeded public directory."""
import json
from pathlib import Path
import subprocess
import unittest
from urllib.parse import urlencode

from bs4 import BeautifulSoup

from test_venues import IsolatedAppHttpCase

ROOT = Path(__file__).resolve().parents[1]
BASE = 'd565e59529dfc385fb758f16f9d94624d7dec541'
CHECKED = '2026-11-09'
CIRCLE_ID = 'c_u_社会人サークル_東京都__社会人サークル_3885b36aa9_hi_ef8d19ab75'
LISTING = 'https://circle-book.com/circles/66187'
SOURCE = 'https://moshicom.com/user/831504'
EMAIL = 'tomtom211997@gmail.com'
SEARCH = urlencode({'audience': 'social', 'q': 'HINODE'})


class November9ContactTests(IsolatedAppHttpCase):
    def result(self):
        status, body, _ = self.request('/api/circles?' + SEARCH)
        self.assertEqual(status, 200)
        return next(row for row in json.loads(body) if row['circle_id'] == CIRCLE_ID)

    def test_appends_one_contact_without_changing_prior_entries(self):
        path = 'outputs/circle_public_contacts.json'
        base = json.loads(subprocess.check_output(['git', 'show', f'{BASE}:{path}'], cwd=ROOT))
        current = json.loads((ROOT / path).read_bytes())
        self.assertEqual(current[:len(base)], base)
        batch = [row for row in current if row['checked_at'] == CHECKED]
        self.assertEqual(len(batch), 1)
        self.assertEqual(batch[0]['circle_id'], CIRCLE_ID)
        self.assertEqual(batch[0]['circle_source_url'], LISTING)
        self.assertEqual(batch[0]['source_url'], SOURCE)
        self.assertEqual(batch[0]['email'], EMAIL)
        self.assertIn('受信同意', batch[0]['purpose'])

    def test_public_directory_binding_and_existing_opt_outs(self):
        row = self.result()
        self.assertEqual(row['circle_name'], 'HINODE｜日の出ランコミュニティ')
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
                ('hinode-test', CIRCLE_ID, 'hinode-test', self.app.now(), self.app.now()))
            store.import_reviewed(conn)
        self.assertFalse(self.result()['public_contact_email'])
        with self.app.connect() as conn:
            conn.execute('update circle_public_profiles set public_contact_consent=1,is_published=0 where circle_id=?',
                         (CIRCLE_ID,))
            store.import_reviewed(conn)
        self.assertFalse(self.result()['public_contact_email'])
