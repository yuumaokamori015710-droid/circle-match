"""Check November 16 provenance, original identity and privacy suppression."""
from contextlib import closing
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import unittest
from urllib.parse import urlencode

from bs4 import BeautifulSoup
from test_venues import IsolatedAppHttpCase

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'outputs'))
import circlematch_public_contacts as contacts

BASE = '2c58258c799c6716b6df943a44bf5e39565678a3'
CHECKED = '2026-11-16'
IDENT = 'c_u_社会人サークル_東京都__社会人サークル_3885b36aa9_zu_b729986daa'
NAME = 'ZUMBAサークル PANELA'
SOURCE = 'https://circle-book.com/circles/42329'
EMAIL = 'panela9632@gmail.com'


def batch():
    return [r for r in json.loads(contacts.SEED_PATH.read_bytes()) if r['checked_at'] == CHECKED]


class November16ContactSeedTests(unittest.TestCase):
    def test_prior_seed_preserved_and_only_verified_organization_mail_added(self):
        baseline = json.loads(subprocess.check_output(
            ['git', 'show', BASE + ':outputs/circle_public_contacts.json'], cwd=ROOT))
        current = json.loads(contacts.SEED_PATH.read_bytes())
        self.assertEqual(len(baseline), 491)
        self.assertEqual(current[:len(baseline)], baseline)
        self.assertEqual(current[len(baseline):len(baseline) + 1], batch())
        self.assertEqual(len(batch()), 1)
        self.assertEqual(len({r['circle_id'] for r in current}), len(current))
        entry = batch()[0]
        self.assertEqual((entry['circle_id'], entry['circle_name']), (IDENT, NAME))
        self.assertEqual((entry['circle_source_url'], entry['source_url']), (SOURCE, SOURCE))
        self.assertEqual(entry['email'], EMAIL)
        self.assertFalse(entry.get('contact_url'))
        for restriction in ['問い合わせ・参加申込用', '★→＠に変更', '48時間', '成人女性',
                            '男性・18歳未満', '紹介', '4・5月', '受信同意']:
            self.assertIn(restriction, entry['purpose'])

    def test_identity_mismatch_opt_out_and_unpublished_profile_stay_protected(self):
        with closing(sqlite3.connect(':memory:')) as conn:
            conn.row_factory = sqlite3.Row
            conn.executescript('''
                create table circles(circle_id text primary key, circle_name text, source_url text);
                create table circle_public_profiles(
                    circle_id text, public_contact_consent integer, is_published integer);
            ''')
            contacts.ensure_tables(conn)
            conn.execute('insert into circles values(?,?,?)', (IDENT, 'Different club', SOURCE))
            contacts.import_reviewed(conn)
            self.assertIsNone(conn.execute(
                'select email from circle_public_contacts where circle_id=?', (IDENT,)).fetchone())
            conn.execute('update circles set circle_name=?,source_url=? where circle_id=?',
                         (NAME, 'https://different.example/', IDENT))
            contacts.import_reviewed(conn)
            self.assertIsNone(conn.execute(
                'select email from circle_public_contacts where circle_id=?', (IDENT,)).fetchone())
            conn.execute('update circles set source_url=? where circle_id=?', (SOURCE, IDENT))
            contacts.import_reviewed(conn)

            def visible():
                return contacts.attach(conn, [{'circle_id': IDENT, 'public_contact_email': ''}])[0]['public_contact_email']

            self.assertEqual(visible(), EMAIL)
            conn.execute('update circle_public_contacts set enabled=0 where circle_id=?', (IDENT,))
            contacts.import_reviewed(conn)
            self.assertEqual(visible(), '')
            self.assertEqual(conn.execute(
                'select enabled from circle_public_contacts where circle_id=?', (IDENT,)).fetchone()[0], 0)
            conn.execute('update circle_public_contacts set enabled=1 where circle_id=?', (IDENT,))
            for consent, published in [(0, 1), (1, 0), (0, 0)]:
                conn.execute('insert into circle_public_profiles values(?,?,?)', (IDENT, consent, published))
                contacts.import_reviewed(conn)
                self.assertEqual(visible(), '')
                self.assertEqual(tuple(conn.execute(
                    'select public_contact_consent,is_published from circle_public_profiles where circle_id=?',
                    (IDENT,)).fetchone()), (consent, published))
                conn.execute('delete from circle_public_profiles where circle_id=?', (IDENT,))


class November16ContactHttpTests(IsolatedAppHttpCase):
    def test_real_seed_identity_api_and_directory_attach_only_public_contact(self):
        entry = batch()[0]
        params = urlencode({'audience': 'social', 'q': NAME})
        status, body, _ = self.request('/api/circles?' + params)
        self.assertEqual(status, 200)
        row = next(r for r in json.loads(body) if r['circle_id'] == IDENT)
        for key, expected in {
            'circle_name': NAME, 'source_url': SOURCE, 'organization_type': '社会人サークル',
            'contact_source_url': SOURCE, 'public_contact_email': EMAIL,
            'contact_checked_at': CHECKED, 'contact_purpose': entry['purpose'],
        }.items():
            self.assertEqual(row[key], expected)
        self.assertNotIn('claimant_email', row)
        self.assertNotIn('user_id', row)
        status, body, _ = self.request('/?tab=db&' + params)
        self.assertEqual(status, 200)
        page = BeautifulSoup(body.decode(), 'html.parser')
        link = page.find('a', href='/invitations/new?' + urlencode({'circle_id': IDENT}))
        self.assertIsNotNone(link)
        self.assertIn('公開メールあり', link.find_parent(class_='circle-row').get_text())
