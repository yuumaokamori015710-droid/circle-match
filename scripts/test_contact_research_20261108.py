"""Check November 8 contact provenance, real seed binding and privacy controls."""
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

BASE = 'dd99a013d63cadebe66a7d50e388c3c33b128e3f'
CHECKED = '2026-11-08'
CASES = {
    'https://circle-book.com/circles/74205': (
        'アスフレわいわいスクール', 'https://tokyo.earthfriends.jp/school/wai2school/',
        'earthfriendsinfo@gmail.com', '運営窓口'),
    'https://circle-book.com/circles/3774': (
        '1989〜1995年生まれ中心', 'https://kawasumi.work/',
        'test.suwamika@gmail.com', 'ブログへの問い合わせ窓口'),
}


def reviewed_batch():
    return [r for r in json.loads(contacts.SEED_PATH.read_bytes()) if r['checked_at'] == CHECKED]


class November8ContactSeedTests(unittest.TestCase):
    def test_previous_records_and_distinct_provenance(self):
        baseline = json.loads(subprocess.check_output(
            ['git', 'show', BASE + ':outputs/circle_public_contacts.json'], cwd=ROOT))
        current = json.loads(contacts.SEED_PATH.read_bytes())
        batch = reviewed_batch()
        self.assertEqual(len(baseline), 485)
        self.assertEqual(current[:len(baseline)], baseline)
        self.assertEqual(current[len(baseline):len(baseline) + len(CASES)], batch)
        self.assertEqual(len(batch), len(CASES))
        self.assertEqual(len({r['circle_id'] for r in current}), len(current))
        self.assertEqual({r['circle_source_url'] for r in batch}, set(CASES))
        for entry in batch:
            _, source, email, purpose = CASES[entry['circle_source_url']]
            self.assertEqual(entry['source_url'], source)
            self.assertEqual(entry['email'], email)
            self.assertIn(purpose, entry['purpose'])
            self.assertIn('受信同意', entry['purpose'])

    def test_identity_mismatch_and_privacy_overrides(self):
        with closing(sqlite3.connect(':memory:')) as conn:
            conn.row_factory = sqlite3.Row
            conn.executescript('''
                create table circles(circle_id text primary key, circle_name text, source_url text);
                create table circle_public_profiles(
                    circle_id text, public_contact_consent integer, is_published integer
                );
            ''')
            contacts.ensure_tables(conn)
            for entry in reviewed_batch():
                ident = entry['circle_id']
                conn.execute('insert into circles values(?,?,?)',
                             (ident, entry['circle_name'], entry['source_url']))
                contacts.import_reviewed(conn)
                self.assertIsNone(conn.execute(
                    'select email from circle_public_contacts where circle_id=?', (ident,)).fetchone())
                conn.execute('update circles set source_url=? where circle_id=?',
                             (entry['circle_source_url'], ident))
                contacts.import_reviewed(conn)

                def visible_email():
                    return contacts.attach(conn, [{'circle_id': ident, 'public_contact_email': ''}])[0]['public_contact_email']

                self.assertEqual(visible_email(), entry['email'])
                conn.execute('update circle_public_contacts set enabled=0 where circle_id=?', (ident,))
                contacts.import_reviewed(conn)
                self.assertEqual(visible_email(), '')
                self.assertEqual(conn.execute(
                    'select enabled from circle_public_contacts where circle_id=?', (ident,)).fetchone()[0], 0)
                conn.execute('update circle_public_contacts set enabled=1 where circle_id=?', (ident,))
                for consent, published in [(0, 1), (1, 0), (0, 0)]:
                    with self.subTest(circle=ident, consent=consent, published=published):
                        conn.execute('insert into circle_public_profiles values(?,?,?)',
                                     (ident, consent, published))
                        contacts.import_reviewed(conn)
                        self.assertEqual(visible_email(), '')
                        self.assertEqual(tuple(conn.execute(
                            'select public_contact_consent,is_published from circle_public_profiles where circle_id=?',
                            (ident,)).fetchone()), (consent, published))
                        conn.execute('delete from circle_public_profiles where circle_id=?', (ident,))


class November8ContactHttpTests(IsolatedAppHttpCase):
    def test_public_directory_uses_real_seed_id_and_contact_provenance(self):
        for entry in reviewed_batch():
            with self.subTest(circle=entry['circle_id']):
                query, _, _, _ = CASES[entry['circle_source_url']]
                params = urlencode({'audience': 'social', 'q': query})
                status, body, _ = self.request('/api/circles?' + params)
                self.assertEqual(status, 200)
                row = next(r for r in json.loads(body) if r['circle_id'] == entry['circle_id'])
                for key, expected in {
                    'circle_name': entry['circle_name'], 'source_url': entry['circle_source_url'],
                    'organization_type': '社会人サークル', 'contact_source_url': entry['source_url'],
                    'public_contact_email': entry['email'], 'contact_checked_at': CHECKED,
                    'contact_purpose': entry['purpose'],
                }.items():
                    self.assertEqual(row[key], expected)
                self.assertNotIn('claimant_email', row)
                self.assertNotIn('user_id', row)
                status, body, _ = self.request('/?tab=db&' + params)
                self.assertEqual(status, 200)
                page = BeautifulSoup(body.decode(), 'html.parser')
                self.assertIn(entry['circle_name'], page.get_text())
                self.assertIn('公開メールあり', page.get_text())
                self.assertIsNotNone(page.find(
                    'a', href='/invitations/new?' + urlencode({'circle_id': entry['circle_id']})))
