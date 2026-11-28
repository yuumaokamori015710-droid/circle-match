"""The reviewed club mailbox must keep its original identity and privacy overrides."""
import json
from pathlib import Path
import sqlite3
import subprocess
import sys
import unittest
from urllib.parse import urlencode

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'outputs'))
import circlematch_public_contacts as contacts
from test_venues import IsolatedAppHttpCase

BASE = '6eeb6b65e6ee1aa32755b3fa0c8dc09aba48d5d5'
IDENT = 'c_u_社会人サークル_東京都__社会人サークル_3885b36aa9_快楽_f419e9f56f'
NAME = '快楽忍者隊サタモッツ【次回：7/25】東京版'
SOURCE = 'https://www.net-menber.com/look/data/227793.html'
OFFICIAL = 'https://www.saturmotts.com/team_info/'
EMAIL = 'info@saturmotts.com'
CHECKED = '2026-11-28'


def entry():
    rows = json.loads(contacts.SEED_PATH.read_text(encoding='utf-8'))
    return next(row for row in rows if row['circle_id'] == IDENT)


class November28ContactSeedTests(unittest.TestCase):
    def test_prior_494_contacts_and_explicit_organization_provenance_are_preserved(self):
        current = json.loads(contacts.SEED_PATH.read_text(encoding='utf-8'))
        prior = json.loads(subprocess.check_output(
            ['git', 'show', BASE + ':outputs/circle_public_contacts.json'], cwd=ROOT))
        self.assertEqual(len(prior), 494)
        self.assertEqual(current[:494], prior)
        self.assertEqual(current[494], entry())
        self.assertEqual(sum(row['circle_id'] == IDENT for row in current), 1)
        for key, value in dict(circle_name=NAME, circle_source_url=SOURCE,
                               source_url=OFFICIAL, email=EMAIL, checked_at=CHECKED).items():
            self.assertEqual(entry()[key], value)
        self.assertNotEqual(EMAIL, 'info@mail.net-menber.com')
        for condition in ['ビジター参加は禁止', '入隊', '18～39歳', '記載差', '受信同意は未確認']:
            self.assertIn(condition, entry()['purpose'])

    def test_original_identity_and_all_privacy_overrides_survive_reimport(self):
        with sqlite3.connect(':memory:') as conn:
            conn.row_factory = sqlite3.Row
            conn.executescript('''create table circles(circle_id text primary key,circle_name text,source_url text);
                create table circle_public_profiles(circle_id text,public_contact_consent integer,is_published integer);''')
            conn.execute('insert into circles values(?,?,?)', (IDENT, NAME, SOURCE))
            contacts.ensure_tables(conn)
            contacts.import_reviewed(conn)
            contacts.import_reviewed(conn)
            self.assertEqual(conn.execute('select count(*) from circle_public_contacts').fetchone()[0], 1)

            def visible():
                return contacts.attach(conn, [{'circle_id': IDENT, 'public_contact_email': ''}])[0]['public_contact_email']

            self.assertEqual(visible(), EMAIL)
            conn.execute('update circle_public_contacts set enabled=0 where circle_id=?', (IDENT,))
            contacts.import_reviewed(conn)
            self.assertEqual(visible(), '')
            conn.execute('update circle_public_contacts set enabled=1 where circle_id=?', (IDENT,))
            for consent, published in [(0, 1), (1, 0), (0, 0)]:
                conn.execute('insert into circle_public_profiles values(?,?,?)', (IDENT, consent, published))
                contacts.import_reviewed(conn)
                self.assertEqual(visible(), '')
                self.assertEqual(tuple(conn.execute(
                    'select public_contact_consent,is_published from circle_public_profiles where circle_id=?',
                    (IDENT,)).fetchone()), (consent, published))
                conn.execute('delete from circle_public_profiles where circle_id=?', (IDENT,))
            conn.execute('delete from circle_public_contacts')
            conn.execute('update circles set circle_name=? where circle_id=?', ('Different club', IDENT))
            contacts.import_reviewed(conn)
            self.assertIsNone(conn.execute('select email from circle_public_contacts where circle_id=?', (IDENT,)).fetchone())
            conn.execute('update circles set circle_name=?,source_url=? where circle_id=?',
                         (NAME, 'https://different.example/', IDENT))
            contacts.import_reviewed(conn)
            self.assertIsNone(conn.execute('select email from circle_public_contacts where circle_id=?', (IDENT,)).fetchone())


class November28ContactHttpTests(IsolatedAppHttpCase):
    def test_imported_catalog_api_and_directory_show_only_the_reviewed_contact(self):
        params = urlencode({'audience': 'social', 'q': 'サタモッツ'})
        status, body, _ = self.request('/api/circles?' + params)
        self.assertEqual(status, 200)
        row = next(row for row in json.loads(body) if row['circle_id'] == IDENT)
        for key, expected in dict(circle_name=NAME, source_url=SOURCE, organization_type='社会人サークル',
                                  contact_source_url=OFFICIAL, public_contact_email=EMAIL,
                                  contact_checked_at=CHECKED, contact_purpose=entry()['purpose']).items():
            self.assertEqual(row[key], expected)
        self.assertNotIn('claimant_email', row)
        self.assertNotIn('user_id', row)
        status, body, _ = self.request('/?tab=db&' + params)
        self.assertEqual(status, 200)
        page = BeautifulSoup(body.decode(), 'html.parser')
        link = page.find('a', href='/invitations/new?' + urlencode({'circle_id': IDENT}))
        self.assertIsNotNone(link)
        self.assertIn('公開メールあり', link.find_parent(class_='circle-row').get_text())
