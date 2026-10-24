"""Reviewed public addresses must not expose private research or override opt-outs."""
import json
from pathlib import Path
import sqlite3
import subprocess
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

    def test_october_18_contacts_keep_opt_outs_and_narrow_purposes(self):
        batch = [entry for entry in self.seed if entry['checked_at'] == '2026-10-18']
        self.assertEqual(len(batch), 10)
        self.assertEqual(sum(bool(entry['email']) for entry in batch), 4)
        self.assertEqual(sum(entry.get('contact_method') == 'form' for entry in batch), 5)
        self.assertEqual(sum(entry.get('contact_method') == 'line' for entry in batch), 1)
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
        by_name = {entry['circle_name']: entry for entry in batch}
        fld = next(entry for entry in batch if 'サークルFLD' in entry['circle_name'])
        self.assertEqual(fld['email'], 'support@circlefld.com')
        self.assertIn('フォームを優先', fld['purpose'])
        self.assertIn('一般のイベント勧誘窓口とは確認できていません', by_name['保谷クラブ']['purpose'])
        self.assertIn('40代以上', by_name['cielシニアバレーボールクラブ']['purpose'])
        self.assertIn('営業', by_name['葛飾ACバドミントンクラブ']['purpose'])
        self.assertEqual(by_name['東砂排球部']['contact_url'], 'https://form1.fc2.com/form/?id=949100')
        self.assertIn('練習試合・合同練習専用', by_name['東砂排球部']['purpose'])
        self.assertFalse({'welcomejupiter@yahoo.co.jp', 'ponyo.info@gmail.com',
                          'cielvc@gmail.com', 'dekoboko.tvc@gmail.com'} &
                         {entry['email'] for entry in batch})

    def test_october_19_batch_keeps_opt_outs_for_all_12_records(self):
        batch = [entry for entry in self.seed if entry['checked_at'] == '2026-10-19']
        self.assertEqual(len(batch), 12)
        self.assertEqual(sum(bool(entry['email']) for entry in batch), 4)
        self.assertEqual(sum(entry.get('contact_method') == 'form' for entry in batch), 6)
        self.assertEqual(sum(entry.get('contact_method') == 'line' for entry in batch), 2)
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

    def test_october_19_keeps_ownership_scope_and_rejects_unrelated_mail(self):
        batch = [entry for entry in self.seed if entry['checked_at'] == '2026-10-19']
        by_name = {entry['circle_name']: entry for entry in batch}
        self.assertEqual(by_name['日本空手道錬聖会 東京道場']['email'], 'renseikai_tokyo@yahoo.co.jp')
        self.assertIn('フォーム優先', by_name['田グリバドミントン']['purpose'])
        self.assertIn('同じ団体・同じ窓口', by_name['サルミナート']['purpose'])
        old = next(entry for entry in self.seed if entry['circle_name'] == 'FC.サルミナート')
        self.assertEqual(old['email'], by_name['サルミナート']['email'])
        self.assertNotEqual(old['circle_id'], by_name['サルミナート']['circle_id'])
        self.assertIn('HTTP', by_name['有隣空手倶楽部']['purpose'])
        self.assertIn('画像認証', by_name['有隣空手倶楽部']['purpose'])
        self.assertIn('営業・勧誘', by_name['社会人サークルJOINT']['purpose'])
        self.assertEqual(by_name['社会人サークルJOINT']['source_url'],
                         'https://www.net-menber.com/look/data/25365.html')
        self.assertIn('団体固有', by_name['東京スポーツビレッジ']['purpose'])
        for name in ['バドミントンで遊ぶ会', 'ド素人バレー練習会']:
            self.assertIn('直接運営', by_name[name]['purpose'])
        self.assertFalse({'odaiba@jbeach.jp', 'arakawa.smash@gmail.com'} & {entry['email'] for entry in batch})
        self.assertTrue(all(entry['circle_source_url'] and entry['source_url'] and entry['purpose']
                            and '社会人サークル' in entry['circle_id'] for entry in batch))

    def test_october_20_opt_outs_survive_for_all_16_contacts(self):
        batch = [r for r in self.seed if r['checked_at'] == '2026-10-20']
        self.assertEqual(len(batch), 16)
        self.assertEqual(sum(bool(r['email']) for r in batch), 1)
        self.assertEqual(sum(r.get('contact_method') == 'form' for r in batch), 14)
        self.assertEqual(sum(r.get('contact_method') == 'line' for r in batch), 1)
        contacts.import_reviewed(self.conn)
        for item in batch:
            with self.subTest(circle=item['circle_name']):
                ident = item['circle_id']
                self.conn.execute('update circle_public_contacts set enabled=0 where circle_id=?', (ident,))
                contacts.import_reviewed(self.conn)
                target = contacts.attach(self.conn, [{'circle_id': ident, 'public_contact_email': ''}])[0]
                self.assertFalse(target.get('public_contact_email') or target.get('contact_url'))
                self.conn.execute('update circle_public_contacts set enabled=1 where circle_id=?', (ident,))
                self.conn.execute('insert into circle_public_profiles values(?,0,1)', (ident,))
                contacts.import_reviewed(self.conn)
                target = contacts.attach(self.conn, [{'circle_id': ident, 'public_contact_email': ''}])[0]
                self.assertFalse(target.get('public_contact_email') or target.get('contact_url'))

    def test_october_20_scopes_do_not_publish_placeholders_or_reply_only_addresses(self):
        batch = [r for r in self.seed if r['checked_at'] == '2026-10-20']
        by_name = {r['circle_name']: r for r in batch}
        yamate = by_name['山手クラブ']
        self.assertEqual(yamate['email'], 'tshirata@outlook.com')
        self.assertIn('通常ブラウザ', yamate['purpose'])
        self.assertIn('男性参加は対象外', yamate['purpose'])
        self.assertEqual(by_name['JAY BLACKS（ジェイ ブラックス）']['contact_url'],
                         'https://bb.miguee.net/j-wings/contact')
        self.assertIn('対戦問合せ', by_name['JAY BLACKS（ジェイ ブラックス）']['purpose'])
        self.assertIn('夢野球', by_name['プリヨシ']['purpose'])
        abendrot = by_name['Abendrot(登山サークル、東京支部)']
        self.assertEqual(abendrot['contact_url'], 'https://lin.ee/T51LLK0')
        self.assertIn('初心者不可', abendrot['purpose'])
        self.assertFalse({'hi@example.com', 'recnad2012@gmail.com'} & {r['email'] for r in batch})
        self.assertFalse({'BLANK since2024', '護身空手木村塾', 'RECNAD（レクナッド）活動１１周年'} & set(by_name))
        self.assertTrue(all(r['circle_source_url'] and r['source_url'] and r['purpose']
                            and '社会人サークル' in r['circle_id'] for r in batch))

    def test_october_23_contacts_keep_exact_sources_and_prior_reviews(self):
        batch = [row for row in self.seed if row['checked_at'] == '2026-10-23']
        self.assertEqual(len(batch), 4)
        self.assertEqual(sum(bool(row['email']) for row in batch), 2)
        self.assertEqual(sum(row.get('contact_method') == 'form' for row in batch), 2)
        by_source = {row['circle_source_url']: row for row in batch}
        roadro = by_source['https://www.net-menber.com/look/data/145847.html']
        self.assertEqual(roadro['email'], 'roadro.common@gmail.com')
        self.assertIn('あっとまーく', roadro['purpose'])
        self.assertIn('20歳以上', roadro['purpose'])
        stellar = by_source['https://www.net-menber.com/look/data/227308.html']
        self.assertEqual(stellar['email'], 'stellarcyclingclub@gmail.com')
        self.assertIn('別フォーム', stellar['purpose'])
        self.assertIn('事前質問', stellar['purpose'])
        sea = by_source['https://www.net-menber.com/look/data/197244.html']
        self.assertEqual(sea['contact_url'], 'https://seacats.vercel.app/contact?tab=game')
        self.assertIn('取材・その他', sea['purpose'])
        mitt = by_source['https://www.net-menber.com/look/data/18669.html']
        self.assertEqual(mitt['contact_url'], 'https://dcbsky2010.wixsite.com/mysite/contact')
        self.assertIn('西スポーツセンター', mitt['purpose'])
        self.assertNotIn('info@bubble-web.work', {row['email'] for row in batch})
        self.assertTrue(all(row['circle_source_url'] and row['source_url'] and row['purpose']
                            and '社会人サークル' in row['circle_id'] for row in batch))
        root = contacts.SEED_PATH.parents[1]
        baseline = json.loads(subprocess.check_output(
            ['git', 'show', 'f2d0f21124bad1854d3cdd6a2f515fcda44ad983:outputs/circle_public_contacts.json'], cwd=root))
        self.assertEqual(len(baseline), 469)
        self.assertEqual(self.seed[:len(baseline)], baseline)
        self.assertEqual(self.seed[len(baseline):len(baseline) + len(batch)], batch)

    def test_october_24_contacts_preserve_sources_and_restricted_purposes(self):
        batch = [row for row in self.seed if row['checked_at'] == '2026-10-24']
        self.assertEqual(len(batch), 7)
        self.assertEqual(sum(bool(row['email']) for row in batch), 2)
        self.assertEqual(sum(row.get('contact_method') == 'form' for row in batch), 5)
        by_source = {row['circle_source_url']: row for row in batch}
        soldiers = by_source['https://www.net-menber.com/look/data/91432.html']
        self.assertEqual(soldiers['email'], 'kawasakisol_danshi@yahoo.co.jp')
        self.assertIn('小学生', soldiers['purpose'])
        self.assertIn('募集一時停止', soldiers['purpose'])
        nisshin = by_source['https://www.net-menber.com/look/data/121115.html']
        self.assertEqual(nisshin['email'], 'nissinkai.kumagaya@gmail.com')
        self.assertIn('熊谷場所のみ', nisshin['purpose'])
        self.assertIn('募集停止', nisshin['purpose'])
        girasol = by_source['https://www.net-menber.com/look/data/133039.html']
        self.assertEqual(girasol['contact_url'], 'https://girasol.1net.jp/contactus.html')
        self.assertIn('チーム交流希望', girasol['purpose'])
        dance = by_source['https://www.net-menber.com/look/data/49095.html']
        self.assertIn('INDIVITY-Z', dance['purpose'])
        hokuto = by_source['https://www.net-menber.com/look/data/101201.html']
        self.assertIn('画像認証は利用者操作', hokuto['purpose'])
        self.assertNotIn('takahashi@yamato-softvolleyball.com', {row['email'] for row in batch})
        self.assertTrue(all(row['circle_source_url'] and row['source_url'] and row['purpose']
                            and '社会人サークル' in row['circle_id'] for row in batch))
        root = contacts.SEED_PATH.parents[1]
        baseline = json.loads(subprocess.check_output(
            ['git', 'show', 'f6fa710bcb4fb71c0c993b4ff680c0ec0b17b684:outputs/circle_public_contacts.json'], cwd=root))
        self.assertEqual(len(baseline), 473)
        self.assertEqual(self.seed[:len(baseline)], baseline)
        self.assertEqual(self.seed[len(baseline):], batch)

    def test_october_24_opt_outs_and_profile_privacy_survive_reimport(self):
        batch = [row for row in self.seed if row['checked_at'] == '2026-10-24']
        self.assertEqual(len(batch), 7)
        contacts.import_reviewed(self.conn)
        for entry in batch:
            with self.subTest(circle=entry['circle_name']):
                ident = entry['circle_id']
                self.conn.execute('update circle_public_contacts set enabled=0 where circle_id=?', (ident,))
                contacts.import_reviewed(self.conn)
                target = contacts.attach(self.conn, [{'circle_id': ident, 'public_contact_email': ''}])[0]
                self.assertFalse(target.get('public_contact_email') or target.get('contact_url'))
                self.conn.execute('update circle_public_contacts set enabled=1 where circle_id=?', (ident,))
                for consent, published in [(0, 1), (1, 0), (0, 0)]:
                    self.conn.execute('insert into circle_public_profiles values(?,?,?)', (ident, consent, published))
                    contacts.import_reviewed(self.conn)
                    target = contacts.attach(self.conn, [{'circle_id': ident, 'public_contact_email': ''}])[0]
                    self.assertFalse(target.get('public_contact_email') or target.get('contact_url'))
                    self.assertEqual(tuple(self.conn.execute('select public_contact_consent,is_published from circle_public_profiles where circle_id=?', (ident,)).fetchone()), (consent, published))
                    self.conn.execute('delete from circle_public_profiles where circle_id=?', (ident,))

    def test_october_23_disabled_and_both_profile_privacy_flags_survive_reimport(self):
        batch = [row for row in self.seed if row['checked_at'] == '2026-10-23']
        self.assertEqual(len(batch), 4)
        contacts.import_reviewed(self.conn)
        for entry in batch:
            with self.subTest(circle=entry['circle_name']):
                ident = entry['circle_id']
                self.conn.execute('update circle_public_contacts set enabled=0 where circle_id=?', (ident,))
                contacts.import_reviewed(self.conn)
                target = contacts.attach(self.conn, [{'circle_id': ident, 'public_contact_email': ''}])[0]
                self.assertFalse(target.get('public_contact_email') or target.get('contact_url'))
                self.conn.execute('update circle_public_contacts set enabled=1 where circle_id=?', (ident,))
                for consent, published in [(0, 1), (1, 0), (0, 0)]:
                    self.conn.execute('insert into circle_public_profiles values(?,?,?)', (ident, consent, published))
                    contacts.import_reviewed(self.conn)
                    target = contacts.attach(self.conn, [{'circle_id': ident, 'public_contact_email': ''}])[0]
                    self.assertFalse(target.get('public_contact_email') or target.get('contact_url'))
                    self.assertEqual(tuple(self.conn.execute('select public_contact_consent,is_published from circle_public_profiles where circle_id=?', (ident,)).fetchone()), (consent, published))
                    self.conn.execute('delete from circle_public_profiles where circle_id=?', (ident,))

    def test_october_22_contacts_preserve_opt_outs_and_organizational_scope(self):
        batch = [row for row in self.seed if row['checked_at'] == '2026-10-22']
        self.assertEqual(len(batch), 9)
        self.assertEqual(sum(bool(row['email']) for row in batch), 1)
        self.assertEqual(sum(row.get('contact_method') == 'form' for row in batch), 6)
        self.assertEqual(sum(row.get('contact_method') == 'line' for row in batch), 2)
        by_source = {row['circle_source_url']: row for row in batch}
        nexus = by_source['https://www.net-menber.com/look/data/127659.html']
        self.assertEqual(nexus['email'], '2020yokosukabbc@gmail.com')
        self.assertIn('中学生', nexus['purpose'])
        self.assertIn('成人向け大会の参加先とは扱いません', nexus['purpose'])
        girasol = by_source['https://www.net-menber.com/look/data/208946.html']
        self.assertIn('チーム交流希望', girasol['purpose'])
        self.assertIn('新規個人参加は停止中', girasol['purpose'])
        turtles = by_source['https://www.net-menber.com/look/data/137689.html']
        self.assertEqual(turtles['contact_url'], 'https://lin.ee/WQmUTkKI')
        self.assertIn('勧誘は禁止', turtles['purpose'])
        one = by_source['https://www.net-menber.com/look/data/194975.html']
        self.assertIn('出演依頼・指導支援', one['purpose'])
        self.assertIn('全社の共通窓口ではありません', one['purpose'])
        dance = by_source['https://www.net-menber.com/look/data/49094.html']
        self.assertIn('営利目的での参加は禁止', dance['purpose'])
        self.assertEqual(dance['source_url'], 'https://lah731.wixsite.com/chimpanzee731')
        contacts.import_reviewed(self.conn)
        for entry in batch:
            with self.subTest(circle=entry['circle_name']):
                ident = entry['circle_id']
                self.conn.execute('update circle_public_contacts set enabled=0 where circle_id=?', (ident,))
                contacts.import_reviewed(self.conn)
                target = contacts.attach(self.conn, [{'circle_id': ident, 'public_contact_email': ''}])[0]
                self.assertFalse(target.get('public_contact_email') or target.get('contact_url'))
                self.conn.execute('update circle_public_contacts set enabled=1 where circle_id=?', (ident,))
                self.conn.execute('insert into circle_public_profiles values(?,0,1)', (ident,))
                contacts.import_reviewed(self.conn)
                target = contacts.attach(self.conn, [{'circle_id': ident, 'public_contact_email': ''}])[0]
                self.assertFalse(target.get('public_contact_email') or target.get('contact_url'))

    def test_october_21_contacts_preserve_both_suppression_settings(self):
        batch = [row for row in self.seed if row['checked_at'] == '2026-10-21']
        self.assertEqual(len(batch), 8)
        self.assertEqual(sum(bool(row['email']) for row in batch), 2)
        self.assertEqual(sum(row.get('contact_method') == 'form' for row in batch), 5)
        self.assertEqual(sum(row.get('contact_method') == 'line' for row in batch), 1)
        contacts.import_reviewed(self.conn)
        for entry in batch:
            with self.subTest(circle=entry['circle_name']):
                ident = entry['circle_id']
                self.conn.execute('update circle_public_contacts set enabled=0 where circle_id=?', (ident,))
                contacts.import_reviewed(self.conn)
                target = contacts.attach(self.conn, [{'circle_id': ident, 'public_contact_email': ''}])[0]
                self.assertFalse(target.get('public_contact_email') or target.get('contact_url'))
                self.conn.execute('update circle_public_contacts set enabled=1 where circle_id=?', (ident,))
                self.conn.execute('insert into circle_public_profiles values(?,0,1)', (ident,))
                contacts.import_reviewed(self.conn)
                target = contacts.attach(self.conn, [{'circle_id': ident, 'public_contact_email': ''}])[0]
                self.assertFalse(target.get('public_contact_email') or target.get('contact_url'))

    def test_october_21_shared_inbox_and_contact_restrictions_are_explicit(self):
        batch = [row for row in self.seed if row['checked_at'] == '2026-10-21']
        by_name = {row['circle_name']: row for row in batch}
        team = by_name['東京チュウナマイツ']
        dads = next(row for row in batch if '/202612.html' in row['circle_source_url'])
        self.assertEqual(team['email'], 'chunamaits@gmail.com')
        self.assertEqual(team['email'], dads['email'])
        self.assertNotEqual(team['circle_id'], dads['circle_id'])
        self.assertIn('同じ運営', dads['purpose'])
        self.assertIn('ビジネス勧誘禁止', team['purpose'])
        tnb = by_name['TNBスケボー部']
        self.assertEqual(tnb['contact_url'], 'https://3cmsr.jp/inquirybu/')
        self.assertIn('商品・サービスの紹介を含む営業メールは禁止', tnb['purpose'])
        self.assertIn('HTTP', by_name['SPICYCANDYダンスサークル']['purpose'])
        self.assertIn('幼児から高校生中心', by_name['T-FAM DANCE SCHOOL']['purpose'])
        self.assertIn('質問回答', by_name['神奈川ランニングクラブKRC']['purpose'])
        self.assertFalse({'sigasugao013@gmail.com', 'hi@example.com'} & {row['email'] for row in batch})
        self.assertTrue(all(row['circle_source_url'] and row['source_url'] and row['purpose']
                            and '社会人サークル' in row['circle_id'] for row in batch))

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

    def test_october_24_contacts_reach_real_seed_api_html_and_invitation(self):
        batch = [row for row in json.loads(contacts.SEED_PATH.read_text(encoding='utf-8'))
                 if row['checked_at'] == '2026-10-24']
        self.assertEqual(len(batch), 7)
        for entry in batch:
            with self.subTest(circle=entry['circle_name']):
                query = quote(entry['circle_name'])
                soup = BeautifulSoup(self.request('/?tab=db&audience=social&q=' + query)[1].decode(), 'html.parser')
                self.assertIn(entry['circle_name'], soup.get_text())
                self.assertIsNotNone(soup.find('a', href='/invitations/new?circle_id=' + quote(entry['circle_id'], safe='')))
                if entry['email']:
                    self.assertIn('公開メールあり', soup.get_text())
                else:
                    self.assertIsNotNone(soup.find('a', href=entry['contact_url']))
                rows = json.loads(self.request('/api/circles?audience=social&q=' + query)[1])
                target = next(row for row in rows if row['circle_id'] == entry['circle_id'])
                for key, value in [('public_contact_email', entry['email']), ('contact_source_url', entry['source_url']),
                                   ('contact_purpose', entry['purpose']), ('contact_checked_at', entry['checked_at']),
                                   ('contact_method', entry.get('contact_method', 'email')), ('contact_url', entry.get('contact_url', ''))]:
                    self.assertEqual(target[key], value)
                self.assertNotIn('claimant_email', target)
                self.assertNotIn('user_id', target)
                markup, _ = ui.compose(target, [], {'authenticated': True})
                self.assertIn(entry['purpose'], BeautifulSoup(markup, 'html.parser').get_text())
                self.assertIn(entry['source_url'].replace('&', '&amp;'), markup)

    def test_october_23_contacts_reach_real_seed_api_html_and_invitation(self):
        batch = [row for row in json.loads(contacts.SEED_PATH.read_text(encoding='utf-8'))
                 if row['checked_at'] == '2026-10-23']
        self.assertEqual(len(batch), 4)
        for entry in batch:
            with self.subTest(circle=entry['circle_name']):
                query = quote(entry['circle_name'])
                soup = BeautifulSoup(self.request('/?tab=db&audience=social&q=' + query)[1].decode(), 'html.parser')
                self.assertIn(entry['circle_name'], soup.get_text())
                self.assertIsNotNone(soup.find('a', href='/invitations/new?circle_id=' + quote(entry['circle_id'], safe='')))
                if entry['email']:
                    self.assertIn('公開メールあり', soup.get_text())
                else:
                    self.assertIsNotNone(soup.find('a', href=entry['contact_url']))
                rows = json.loads(self.request('/api/circles?audience=social&q=' + query)[1])
                target = next(row for row in rows if row['circle_id'] == entry['circle_id'])
                for key, value in [('public_contact_email', entry['email']), ('contact_source_url', entry['source_url']),
                                   ('contact_purpose', entry['purpose']), ('contact_checked_at', entry['checked_at']),
                                   ('contact_method', entry.get('contact_method', 'email')), ('contact_url', entry.get('contact_url', ''))]:
                    self.assertEqual(target[key], value)
                self.assertNotIn('claimant_email', target)
                self.assertNotIn('user_id', target)
                markup, _ = ui.compose(target, [], {'authenticated': True})
                self.assertIn(entry['purpose'], BeautifulSoup(markup, 'html.parser').get_text())
                self.assertIn(entry['source_url'].replace('&', '&amp;'), markup)

    def test_october_22_contacts_reach_real_seed_api_html_and_invitation(self):
        batch = [row for row in json.loads(contacts.SEED_PATH.read_text(encoding='utf-8'))
                 if row['checked_at'] == '2026-10-22']
        self.assertEqual(len(batch), 9)
        for entry in batch:
            with self.subTest(circle=entry['circle_name']):
                query = quote(entry['circle_name'])
                soup = BeautifulSoup(self.request('/?tab=db&audience=social&q=' + query)[1].decode(), 'html.parser')
                self.assertIn(entry['circle_name'], soup.get_text())
                self.assertIsNotNone(soup.find('a', href='/invitations/new?circle_id=' + quote(entry['circle_id'], safe='')))
                if entry['email']:
                    self.assertIn('公開メールあり', soup.get_text())
                else:
                    self.assertIsNotNone(soup.find('a', href=entry['contact_url']))
                rows = json.loads(self.request('/api/circles?audience=social&q=' + query)[1])
                target = next(row for row in rows if row['circle_id'] == entry['circle_id'])
                for key, value in [('public_contact_email', entry['email']), ('contact_source_url', entry['source_url']),
                                   ('contact_purpose', entry['purpose']), ('contact_checked_at', entry['checked_at'])]:
                    self.assertEqual(target[key], value)
                self.assertNotIn('claimant_email', target)
                self.assertNotIn('user_id', target)
                markup, _ = ui.compose(target, [], {'authenticated': True})
                self.assertIn(entry['purpose'], BeautifulSoup(markup, 'html.parser').get_text())
                self.assertIn(entry['source_url'].replace('&', '&amp;'), markup)

    def test_october_21_contacts_reach_real_seed_and_invitation_with_scope(self):
        batch = [row for row in json.loads(contacts.SEED_PATH.read_text(encoding='utf-8'))
                 if row['checked_at'] == '2026-10-21']
        self.assertEqual(len(batch), 8)
        for entry in batch:
            with self.subTest(circle=entry['circle_name']):
                query = quote(entry['circle_name'])
                soup = BeautifulSoup(self.request('/?tab=db&audience=social&q=' + query)[1].decode(), 'html.parser')
                self.assertIsNotNone(soup.find('a', href='/invitations/new?circle_id=' + quote(entry['circle_id'], safe='')))
                if entry['email']:
                    self.assertIn('公開メールあり', soup.get_text())
                else:
                    self.assertIsNotNone(soup.find('a', href=entry['contact_url']))
                rows = json.loads(self.request('/api/circles?audience=social&q=' + query)[1])
                target = next(row for row in rows if row['circle_id'] == entry['circle_id'])
                for key, value in [('public_contact_email', entry['email']), ('contact_source_url', entry['source_url']),
                                   ('contact_purpose', entry['purpose']), ('contact_checked_at', entry['checked_at'])]:
                    self.assertEqual(target[key], value)
                self.assertNotIn('claimant_email', target)
                self.assertNotIn('user_id', target)
                markup, _ = ui.compose(target, [], {'authenticated': True})
                self.assertIn(entry['purpose'], BeautifulSoup(markup, 'html.parser').get_text())
                self.assertIn(entry['source_url'].replace('&', '&amp;'), markup)

    def test_october_20_contacts_reach_seed_api_initial_html_and_invitation(self):
        batch = [r for r in json.loads(contacts.SEED_PATH.read_text(encoding='utf-8'))
                 if r['checked_at'] == '2026-10-20']
        self.assertEqual(len(batch), 16)
        for entry in batch:
            with self.subTest(circle=entry['circle_name']):
                query = quote(entry['circle_name'])
                soup = BeautifulSoup(self.request('/?tab=db&audience=social&q=' + query)[1].decode(), 'html.parser')
                self.assertIn(entry['circle_name'], soup.get_text())
                self.assertIsNotNone(soup.find('a', href='/invitations/new?circle_id=' + quote(entry['circle_id'], safe='')))
                if entry['email']:
                    self.assertIn('公開メールあり', soup.get_text())
                else:
                    self.assertIsNotNone(soup.find('a', href=entry['contact_url']))
                rows = json.loads(self.request('/api/circles?audience=social&q=' + query)[1])
                target = next(row for row in rows if row['circle_id'] == entry['circle_id'])
                for key, value in [('public_contact_email', entry['email']), ('contact_source_url', entry['source_url']),
                                   ('contact_purpose', entry['purpose']), ('contact_checked_at', entry['checked_at'])]:
                    self.assertEqual(target[key], value)
                self.assertNotIn('claimant_email', target)
                self.assertNotIn('user_id', target)
                markup, _ = ui.compose(target, [], {'authenticated': True})
                self.assertIn(entry['purpose'], BeautifulSoup(markup, 'html.parser').get_text())
                self.assertIn(entry['source_url'].replace('&', '&amp;'), markup)
                self.assertIn((entry['email'] or entry['contact_url']).replace('&', '&amp;'), markup)

    def test_october_19_contacts_reach_real_seed_api_ssr_and_invitation(self):
        batch = [entry for entry in json.loads(contacts.SEED_PATH.read_text(encoding='utf-8'))
                 if entry['checked_at'] == '2026-10-19']
        self.assertEqual(len(batch), 12)
        for entry in batch:
            with self.subTest(circle=entry['circle_name']):
                query = quote(entry['circle_name'])
                markup = self.request('/?tab=db&audience=social&q=' + query)[1].decode()
                soup = BeautifulSoup(markup, 'html.parser')
                self.assertIn(entry['circle_name'], soup.get_text())
                self.assertIsNotNone(soup.find('a', href='/invitations/new?circle_id=' + quote(entry['circle_id'], safe='')))
                if entry['email']:
                    self.assertIn('公開メールあり', soup.get_text())
                else:
                    self.assertIsNotNone(soup.find('a', href=entry['contact_url']))
                rows = json.loads(self.request('/api/circles?audience=social&q=' + query)[1])
                target = next(row for row in rows if row['circle_id'] == entry['circle_id'])
                self.assertEqual(target['public_contact_email'], entry['email'])
                self.assertEqual(target['contact_source_url'], entry['source_url'])
                self.assertEqual(target['contact_purpose'], entry['purpose'])
                self.assertEqual(target['contact_checked_at'], entry['checked_at'])
                self.assertNotIn('claimant_email', target)
                self.assertNotIn('user_id', target)
                invitation, _ = ui.compose(target, [], {'authenticated': True})
                self.assertIn(entry['purpose'], BeautifulSoup(invitation, 'html.parser').get_text())
                self.assertIn(entry['source_url'].replace('&', '&amp;'), invitation)
                self.assertIn((entry['email'] or entry['contact_url']).replace('&', '&amp;'), invitation)

    def test_october_18_contacts_reach_real_seed_api_ssr_and_invitation(self):
        batch = [entry for entry in json.loads(contacts.SEED_PATH.read_text(encoding='utf-8'))
                 if entry['checked_at'] == '2026-10-18']
        self.assertEqual(len(batch), 10)
        for entry in batch:
            with self.subTest(circle=entry['circle_name']):
                query = quote(entry['circle_name'])
                markup = self.request('/?tab=db&audience=social&q=' + query)[1].decode()
                soup = BeautifulSoup(markup, 'html.parser')
                self.assertIn(entry['circle_name'], soup.get_text())
                self.assertIsNotNone(soup.find('a', href='/invitations/new?circle_id=' + quote(entry['circle_id'], safe='')))
                if entry['email']:
                    self.assertIn('公開メールあり', soup.get_text())
                else:
                    self.assertIsNotNone(soup.find('a', href=entry['contact_url']))
                rows = json.loads(self.request('/api/circles?audience=social&q=' + query)[1])
                target = next(row for row in rows if row['circle_id'] == entry['circle_id'])
                self.assertEqual(target['public_contact_email'], entry['email'])
                self.assertEqual(target['contact_source_url'], entry['source_url'])
                self.assertEqual(target['contact_purpose'], entry['purpose'])
                self.assertEqual(target['contact_checked_at'], entry['checked_at'])
                self.assertNotIn('claimant_email', target)
                self.assertNotIn('user_id', target)
                invitation, _ = ui.compose(target, [], {'authenticated': True})
                self.assertIn(entry['purpose'], BeautifulSoup(invitation, 'html.parser').get_text())
                self.assertIn(entry['source_url'].replace('&', '&amp;'), invitation)
                if entry['email']:
                    self.assertIn(entry['email'], invitation)
                else:
                    self.assertIn(entry['contact_url'].replace('&', '&amp;'), invitation)

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
