"""Reviewed public addresses must not expose private research or override opt-outs."""
import json
from pathlib import Path
import sqlite3
import sys
import unittest
from unittest.mock import patch
import tempfile
from urllib.parse import parse_qs, urlsplit, quote
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'outputs'))
import circlematch_public_contacts as contacts
import circlematch_invitation_ui as ui
from test_venues import IsolatedAppHttpCase


class PublicContactTests(unittest.TestCase):
    def setUp(self):
        self.conn = sqlite3.connect(':memory:')
        self.conn.row_factory = sqlite3.Row
        self.addCleanup(self.conn.close)
        self.conn.executescript('''create table circles(circle_id text primary key,circle_name text,source_url text);
          create table circle_public_profiles(circle_id text,public_contact_consent integer,is_published integer);''')
        contacts.ensure_tables(self.conn)
        self.seed = json.loads(contacts.SEED_PATH.read_text(encoding='utf-8'))
        self.conn.executemany('insert into circles values(?,?,?)', [(c['circle_id'],c['circle_name'],c.get('circle_source_url',c['source_url'])) for c in self.seed])

    def test_seed_matches_identity_and_is_idempotent(self):
        contacts.import_reviewed(self.conn)
        contacts.import_reviewed(self.conn)
        self.assertEqual(self.conn.execute('select count(*) from circle_public_contacts').fetchone()[0], len(self.seed))
        self.conn.execute('delete from circle_public_contacts')
        self.conn.execute("update circles set circle_name='Different organization'")
        contacts.import_reviewed(self.conn)
        self.assertEqual(self.conn.execute('select count(*) from circle_public_contacts').fetchone()[0], 0)

    def test_profile_privacy_and_suppression_survive_reimport(self):
        contacts.import_reviewed(self.conn)
        first,second = self.seed[:2]
        self.conn.execute('update circle_public_contacts set enabled=0 where circle_id=?', (first['circle_id'],))
        self.conn.execute('insert into circle_public_profiles values(?,0,1)', (second['circle_id'],))
        contacts.import_reviewed(self.conn)
        rows = contacts.attach(self.conn, [{'circle_id':r['circle_id'],'public_contact_email':''} for r in self.seed])
        self.assertEqual([r['public_contact_email'] for r in rows[:2]], ['', ''])
        self.assertEqual(sum(bool(r.get('public_contact_email') or r.get('contact_url')) for r in rows), len(self.seed)-2)

    def test_existing_table_upgrades_without_losing_suppression(self):
        self.conn.execute('drop table circle_public_contacts')
        self.conn.execute('''create table circle_public_contacts (
            circle_id text primary key,email text not null,source_url text not null,
            purpose text not null,checked_at text not null,enabled integer not null default 1)''')
        self.conn.execute('insert into circle_public_contacts values(?,?,?,?,?,0)',
                          (self.seed[0]['circle_id'], self.seed[0]['email'], self.seed[0]['source_url'],
                           self.seed[0]['purpose'], self.seed[0]['checked_at']))
        contacts.ensure_tables(self.conn)
        contacts.import_reviewed(self.conn)
        row = self.conn.execute('select enabled,contact_method,contact_url from circle_public_contacts where circle_id=?',
                                (self.seed[0]['circle_id'],)).fetchone()
        self.assertEqual(tuple(row), (0, 'email', ''))

    def test_linked_official_contact_keeps_original_circle_identity(self):
        entry = dict(self.seed[0], circle_source_url=self.seed[0]['source_url'],
                     source_url='https://club.example/contact')
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)/'reviewed.json'
            path.write_text(json.dumps([entry]),encoding='utf-8')
            with patch.object(contacts,'SEED_PATH',path):
                contacts.import_reviewed(self.conn)
                self.assertEqual(self.conn.execute('select source_url from circle_public_contacts').fetchone()[0], entry['source_url'])
                self.conn.execute('delete from circle_public_contacts')
                self.conn.execute("update circles set source_url='https://different.example/'")
                contacts.import_reviewed(self.conn)
                self.assertEqual(self.conn.execute('select count(*) from circle_public_contacts').fetchone()[0], 0)

    def test_mailto_has_single_recipient_and_template_and_requires_sender(self):
        item = self.seed[1]
        contact = dict(public_contact_email=item['email'], contact_source_url=item['source_url'], contact_purpose=item['purpose'])
        data = dict(invitation_id='test',subject='合同練習 & ご相談',target_circle_name=item['circle_name'],
                    sender_label='招待側',body='日時を相談したいです。',status='pending',is_sender=True,contact=contact)
        markup,_ = ui.detail(data, {'authenticated':True}, 'https://circle-match.jp')
        soup = BeautifulSoup(markup,'html.parser')
        mail = urlsplit(soup.select_one('a[href^="mailto:"]')['href'])
        self.assertEqual(mail.path, item['email'])
        query = parse_qs(mail.query)
        self.assertEqual(query['subject'], [data['subject']])
        self.assertIn('Circle Match', query['body'][0])
        self.assertIn('https://circle-match.jp/invitations/test', query['body'][0])
        self.assertIn('この画面では送信されません', soup.get_text())
        guest,_ = ui.detail(data, {'authenticated':False}, 'https://circle-match.jp')
        self.assertNotIn(item['email'],guest)

    def test_missing_contact_has_source_fallback(self):
        markup,_ = ui.compose({'circle_id':'missing','source_url':'https://example.org/contact'}, [], {})
        self.assertIn('掲載元を確認', markup)
        self.assertNotIn('mailto:', markup)

    def test_form_contact_opens_official_window_without_sending(self):
        item = next(entry for entry in self.seed if entry.get('contact_method') == 'form')
        contact = dict(contact_method='form', contact_url=item['contact_url'],
                       contact_source_url=item['source_url'], contact_purpose=item['purpose'])
        markup,_ = ui.compose(contact, [], {})
        self.assertIn('問い合わせフォームを開く', markup)
        self.assertIn(item['contact_url'].replace('&', '&amp;'), markup)
        self.assertNotIn('mailto:', markup)
        data = dict(invitation_id='test', subject='交流相談', target_circle_name=item['circle_name'],
                    sender_label='招待側', body='よろしくお願いします。', status='pending', is_sender=True, contact=contact)
        detail,_ = ui.detail(data, {'authenticated':True}, 'https://circle-match.jp')
        self.assertIn('招待文をコピー', detail)
        self.assertIn('この画面では送信されません', detail)

    def test_form_contact_respects_existing_opt_outs(self):
        item = next(entry for entry in self.seed if entry.get('contact_method') == 'form')
        contacts.import_reviewed(self.conn)
        self.conn.execute('update circle_public_contacts set enabled=0 where circle_id=?', (item['circle_id'],))
        contacts.import_reviewed(self.conn)
        circle = {'circle_id': item['circle_id'], 'public_contact_email': ''}
        self.assertFalse(contacts.attach(self.conn, [circle])[0].get('contact_url'))
        self.conn.execute('update circle_public_contacts set enabled=1 where circle_id=?', (item['circle_id'],))
        self.conn.execute('insert into circle_public_profiles values(?,0,1)', (item['circle_id'],))
        circle = {'circle_id': item['circle_id'], 'public_contact_email': ''}
        self.assertFalse(contacts.attach(self.conn, [circle])[0].get('contact_url'))

    def test_form_contact_cannot_use_unsafe_url_or_email(self):
        item = next(entry for entry in self.seed if entry.get('contact_method') == 'form')
        for changes in ({'contact_url': 'javascript:alert(1)'}, {'email': 'someone@example.org'}):
            with tempfile.TemporaryDirectory() as directory:
                path = Path(directory)/'reviewed.json'
                path.write_text(json.dumps([dict(item, **changes)]), encoding='utf-8')
                with patch.object(contacts, 'SEED_PATH', path):
                    with self.assertRaises(ValueError):
                        contacts.import_reviewed(self.conn)


class PublicContactHttpTests(IsolatedAppHttpCase):
    def test_every_reviewed_contact_reaches_the_real_seeded_directory(self):
        expected = {r['circle_id']:r for r in json.loads(contacts.SEED_PATH.read_text(encoding='utf-8'))}
        found = {}
        for offset in range(0, 20000, 200):
            rows = json.loads(self.request('/api/circles?audience=all&limit=200&sort=circle&offset='+str(offset))[1])
            found.update({r['circle_id']:r for r in rows if r.get('public_contact_email') or r.get('contact_url')})
            if len(rows)<200:
                break
        self.assertEqual(set(expected)-set(found),set())
        for ident,entry in expected.items():
            self.assertEqual(found[ident]['public_contact_email'],entry.get('email',''))
            self.assertEqual(found[ident]['contact_source_url'],entry['source_url'])
            self.assertEqual(found[ident]['contact_method'],entry.get('contact_method','email'))
            self.assertEqual(found[ident]['contact_url'],entry.get('contact_url',''))

    def test_seed_is_available_to_public_search_but_not_claimant_email(self):
        body = json.loads(self.request('/api/circles?audience=social&q=Bandits')[1])
        rows = body
        self.assertTrue(rows)
        target = next(row for row in rows if 'Bandits' in row['circle_name'])
        self.assertTrue(target['public_contact_email'])
        self.assertIn('119837', target['contact_source_url'])
        self.assertNotIn('claimant_email', target)
        self.assertNotIn('user_id', target)

    def test_official_form_is_linked_in_initial_directory_html(self):
        rows = json.loads(self.request('/api/circles?audience=social&q=FLAT9')[1])
        target = next(row for row in rows if row['circle_name'].startswith('FLAT9'))
        self.assertEqual(target['contact_method'], 'form')
        self.assertIn('roon01.jimdofree.com/', target['contact_url'])
        self.assertFalse(target['public_contact_email'])
        html = self.request('/?tab=db&audience=social&q=FLAT9')[1].decode()
        self.assertIn('問い合わせフォーム', html)
        self.assertIn('roon01.jimdofree.com/', html)

    def test_cancellation_sources_and_unknown_state_in_ssr(self):
        rows = json.loads(self.request('/api/venues')[1])['courts']
        known = next(r for r in rows if r['id']=='tokyo-sports-014')
        self.assertEqual(known['fee_ranges'][0]['minimum'],11000)
        self.assertEqual(known['fee_ranges'][0]['maximum'],13200)
        self.assertIn('4時間以上',known['cancellation']['summary'])
        self.assertIsNone(next(r for r in rows if r['id']=='tokyo-sports-013')['cancellation'])
        html = self.request('/venues?v_q='+quote('高倉体育館'))[1].decode()
        self.assertIn('公式キャンセル規定',html)
        self.assertIn('13〜7日前50%',html)


if __name__ == '__main__':
    unittest.main()
