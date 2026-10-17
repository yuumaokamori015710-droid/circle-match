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

    def test_official_line_has_source_and_never_sends(self):
        item = next(entry for entry in self.seed if entry.get('contact_method') == 'line')
        target = dict(circle_id=item['circle_id'], circle_name=item['circle_name'],
                      contact_method='line', contact_url=item['contact_url'],
                      contact_source_url=item['source_url'], contact_purpose=item['purpose'],
                      contact_checked_at=item['checked_at'])
        markup, _ = ui.compose(target, [], {})
        soup = BeautifulSoup(markup, 'html.parser')
        link = soup.find('a', href=item['contact_url'])
        self.assertIsNotNone(link)
        self.assertIn('公式LINE', link.get_text())
        self.assertIn('noopener', link.get('rel', []))
        self.assertIn(item['source_url'], markup)
        self.assertNotIn('mailto:', markup)
        data = dict(invitation_id='line-test', subject='交流相談', target_circle_name=item['circle_name'],
                    sender_label='招待側', body='日時を相談します。', status='pending', is_sender=True, contact=target)
        detail, _ = ui.detail(data, {'authenticated': True}, 'https://circle-match.jp')
        self.assertIn('この画面では送信されません', detail)

    def test_latest_review_preserves_suppression_for_each_contact_method(self):
        batch = [entry for entry in self.seed if entry['checked_at'] == '2026-10-16']
        self.assertTrue({'email', 'form', 'line'}.issubset(
            {entry.get('contact_method', 'email') for entry in batch}))
        contacts.import_reviewed(self.conn)
        for entry in batch:
            with self.subTest(circle=entry['circle_name']):
                ident = entry['circle_id']
                self.conn.execute('update circle_public_contacts set enabled=0 where circle_id=?', (ident,))
                contacts.import_reviewed(self.conn)
                row = contacts.attach(self.conn, [{'circle_id': ident, 'public_contact_email': ''}])[0]
                self.assertFalse(row.get('public_contact_email') or row.get('contact_url'))
                self.conn.execute('update circle_public_contacts set enabled=1 where circle_id=?', (ident,))
                self.conn.execute('insert into circle_public_profiles values(?,0,1)', (ident,))
                contacts.import_reviewed(self.conn)
                row = contacts.attach(self.conn, [{'circle_id': ident, 'public_contact_email': ''}])[0]
                self.assertFalse(row.get('public_contact_email') or row.get('contact_url'))

    def test_scope_warning_is_preserved_for_recruitment_only_inbox(self):
        entry = next(item for item in self.seed if item['circle_name'] == 'paradox横浜')
        target = dict(circle_name=entry['circle_name'], public_contact_email=entry['email'],
                      contact_source_url=entry['source_url'], contact_purpose=entry['purpose'])
        markup, _ = ui.compose(target, [], {})
        self.assertIn('一般のイベント勧誘窓口とは確認できていません', markup)

    def test_october_17_review_keeps_every_new_contact_private_when_opted_out(self):
        batch = [entry for entry in self.seed if entry['checked_at'] == '2026-10-17']
        self.assertEqual(len(batch), 6)
        self.assertEqual(sum(bool(entry['email']) for entry in batch), 4)
        contacts.import_reviewed(self.conn)
        for entry in batch:
            with self.subTest(circle=entry['circle_name']):
                ident = entry['circle_id']
                self.conn.execute('update circle_public_contacts set enabled=0 where circle_id=?', (ident,))
                contacts.import_reviewed(self.conn)
                row = contacts.attach(self.conn, [{'circle_id': ident, 'public_contact_email': ''}])[0]
                self.assertFalse(row.get('public_contact_email') or row.get('contact_url'))
                self.conn.execute('update circle_public_contacts set enabled=1 where circle_id=?', (ident,))
                self.conn.execute('insert into circle_public_profiles values(?,0,1)', (ident,))
                contacts.import_reviewed(self.conn)
                row = contacts.attach(self.conn, [{'circle_id': ident, 'public_contact_email': ''}])[0]
                self.assertFalse(row.get('public_contact_email') or row.get('contact_url'))

    def test_october_17_review_preserves_published_mail_aliases_and_scope(self):
        pink = next(entry for entry in self.seed if entry['circle_name'] == 'ピンクレディ')
        self.assertEqual(pink['email'], 'pinkladyfc+KL@gmail.com')
        self.assertIn('2日以上', pink['purpose'])
        running = next(entry for entry in self.seed if entry['circle_name'] == '【皇居ランニング】を始めよう♪')
        self.assertIn('営業', running['purpose'])
        miyatama = next(entry for entry in self.seed if entry['circle_name'] == 'みやたまクラブ')
        self.assertIn('フォームを優先', miyatama['purpose'])
        self.assertIn('HTTP', miyatama['purpose'])
        rascals = next(entry for entry in self.seed if entry['circle_name'] == 'ラスカルズ 卓球部')
        self.assertIn('交流戦', rascals['purpose'])


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

    def test_new_contact_channels_are_linked_in_initial_directory_html(self):
        for name, label in [('SITクラブ', '問い合わせフォーム'), ('ラビサル神奈川', '公式LINE')]:
            with self.subTest(circle=name):
                entry = next(item for item in json.loads(contacts.SEED_PATH.read_text(encoding='utf-8'))
                             if item['circle_name'] == name)
                markup = self.request('/?tab=db&audience=social&q=' + quote(name))[1].decode()
                soup = BeautifulSoup(markup, 'html.parser')
                link = soup.find('a', href=entry['contact_url'])
                self.assertIsNotNone(link)
                self.assertIn(label, link.get_text())
                self.assertIn(name, soup.get_text())

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

    def test_october_17_contacts_reach_directory_and_invitation_with_scope(self):
        batch = [entry for entry in json.loads(contacts.SEED_PATH.read_text(encoding='utf-8'))
                 if entry['checked_at'] == '2026-10-17']
        for entry in batch:
            with self.subTest(circle=entry['circle_name']):
                markup = self.request('/?tab=db&audience=social&q=' + quote(entry['circle_name']))[1].decode()
                soup = BeautifulSoup(markup, 'html.parser')
                self.assertIsNotNone(soup.find('a', href='/invitations/new?circle_id=' + quote(entry['circle_id'], safe='')))
                if entry['email']:
                    self.assertIn('公開メールあり', soup.get_text())
                else:
                    self.assertIsNotNone(soup.find('a', href=entry['contact_url']))
                self.assertIn(entry['circle_name'], soup.get_text())
                rows = json.loads(self.request('/api/circles?audience=social&q=' + quote(entry['circle_name']))[1])
                target = next(row for row in rows if row['circle_id'] == entry['circle_id'])
                self.assertEqual(target['public_contact_email'], entry['email'])
                self.assertEqual(target['contact_purpose'], entry['purpose'])
                self.assertEqual(target['contact_source_url'], entry['source_url'])
                invitation, _ = ui.compose(target, [], {'authenticated': True})
                self.assertIn(entry['purpose'], BeautifulSoup(invitation, 'html.parser').get_text())
                self.assertIn(entry['source_url'].replace('&', '&amp;'), invitation)
                if entry['email']:
                    self.assertIn(entry['email'], invitation)


if __name__ == '__main__':
    unittest.main()
