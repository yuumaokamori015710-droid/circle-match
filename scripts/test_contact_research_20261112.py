"""Check November 12 contact provenance, seed identity and opt-out preservation."""
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

BASE = 'fe00b6f5ddf49378ad83fa5235b0771e11c48af1'
CHECKED = '2026-11-12'
CASES = {
    'https://circle-book.com/circles/3282': (
        'バドミントンサークル CLOVER',
        'https://clover-kitasenju.jimdofree.com/%E7%B7%B4%E7%BF%92%E5%8F%82%E5%8A%A0%E3%81%AE%E4%BB%95%E6%96%B9/',
        'badnet2004@yahoo.co.jp', '練習当日12時まで'),
    'https://circle-book.com/circles/5270': (
        '世田谷ヒート', 'https://circle-book.com/circles/5270',
        'setagaya22heat14@gmail.com', '参加連絡・質問用'),
}


def batch():
    return [r for r in json.loads(contacts.SEED_PATH.read_bytes()) if r['checked_at'] == CHECKED]


class November12ContactSeedTests(unittest.TestCase):
    def test_previous_records_preserved_and_only_two_verified_emails_added(self):
        baseline = json.loads(subprocess.check_output(
            ['git', 'show', BASE + ':outputs/circle_public_contacts.json'], cwd=ROOT))
        current = json.loads(contacts.SEED_PATH.read_bytes())
        self.assertEqual(len(baseline), 489)
        self.assertEqual(current[:len(baseline)], baseline)
        self.assertEqual(current[len(baseline):len(baseline) + 2], batch())
        self.assertEqual(len(batch()), 2)
        self.assertEqual(len({r['circle_id'] for r in current}), len(current))
        self.assertEqual({r['circle_source_url'] for r in batch()}, set(CASES))
        for entry in batch():
            name, source, email, purpose = CASES[entry['circle_source_url']]
            self.assertEqual(entry['circle_name'], name)
            self.assertEqual((entry['source_url'], entry['email']), (source, email))
            self.assertIn(purpose, entry['purpose'])
            self.assertIn('記載差', entry['purpose'])
            self.assertIn('受信同意', entry['purpose'])
            self.assertFalse(entry.get('contact_url'))

    def test_identity_mismatch_and_suppression_are_not_overridden(self):
        with closing(sqlite3.connect(':memory:')) as conn:
            conn.row_factory = sqlite3.Row
            conn.executescript('''
                create table circles(circle_id text primary key, circle_name text, source_url text);
                create table circle_public_profiles(
                    circle_id text, public_contact_consent integer, is_published integer);
            ''')
            contacts.ensure_tables(conn)
            for entry in batch():
                ident = entry['circle_id']
                conn.execute('insert into circles values(?,?,?)', (ident, 'Different club', entry['circle_source_url']))
                contacts.import_reviewed(conn)
                self.assertIsNone(conn.execute('select email from circle_public_contacts where circle_id=?', (ident,)).fetchone())
                conn.execute('update circles set circle_name=?,source_url=? where circle_id=?',
                             (entry['circle_name'], 'https://different.example/', ident))
                contacts.import_reviewed(conn)
                self.assertIsNone(conn.execute('select email from circle_public_contacts where circle_id=?', (ident,)).fetchone())
                conn.execute('update circles set source_url=? where circle_id=?', (entry['circle_source_url'], ident))
                contacts.import_reviewed(conn)

                def visible():
                    return contacts.attach(conn, [{'circle_id': ident, 'public_contact_email': ''}])[0]['public_contact_email']

                self.assertEqual(visible(), entry['email'])
                conn.execute('update circle_public_contacts set enabled=0 where circle_id=?', (ident,))
                contacts.import_reviewed(conn)
                self.assertEqual(visible(), '')
                self.assertEqual(conn.execute('select enabled from circle_public_contacts where circle_id=?', (ident,)).fetchone()[0], 0)
                conn.execute('update circle_public_contacts set enabled=1 where circle_id=?', (ident,))
                for consent, published in [(0, 1), (1, 0), (0, 0)]:
                    conn.execute('insert into circle_public_profiles values(?,?,?)', (ident, consent, published))
                    contacts.import_reviewed(conn)
                    self.assertEqual(visible(), '')
                    self.assertEqual(tuple(conn.execute('select public_contact_consent,is_published from circle_public_profiles where circle_id=?',
                                                        (ident,)).fetchone()), (consent, published))
                    conn.execute('delete from circle_public_profiles where circle_id=?', (ident,))


class November12ContactHttpTests(IsolatedAppHttpCase):
    def test_contacts_attach_to_real_directory_records_with_original_sources(self):
        for entry in batch():
            with self.subTest(circle=entry['circle_id']):
                params = urlencode({'audience': 'social', 'q': entry['circle_name']})
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
                link = page.find('a', href='/invitations/new?' + urlencode({'circle_id': entry['circle_id']}))
                self.assertIsNotNone(link)
                self.assertIn('公開メールあり', link.find_parent(class_='circle-row').get_text())
