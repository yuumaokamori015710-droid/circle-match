"""Guest admission uses event-scoped capabilities, never membership cookies or live mail."""
import json
import re
from concurrent.futures import ThreadPoolExecutor
from urllib.error import HTTPError
from urllib.parse import quote, urlencode
from urllib.request import Request
from unittest.mock import patch

from bs4 import BeautifulSoup
from test_event_flow import user, create_account, event_payload
from test_venues import IsolatedAppHttpCase


class GuestFlowTests(IsolatedAppHttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.app.init_db()
        cls.host = user('guest_test_host','host@example.test','Host')
        create_account(cls.app,cls.host)

    def setUp(self):
        self.ready = patch.object(self.app,'email_notifications_ready',return_value=True).start()
        self.addCleanup(patch.stopall)
        self.mail = patch.object(self.app,'send_notification_email',return_value='mock').start()
        self.eid = self.event(self._testMethodName)
        self.path = self.app.guests.path(self.eid)
        with self.app.connect() as conn:
            conn.execute("delete from app_state where state_key glob 'event-guest:v1:rate:*'")

    def event(self,title):
        with self.app.connect() as conn:
            return self.app.save_event_post(conn, dict(event_payload(title),minimum_participants=1,
                participation_type='both',individual_fee_amount=2500,team_fee_amount=15000,
                allow_on_site_payment=True,payment_method='bank_transfer'),self.host)

    def post(self,path,data,cookie='',origin=None):
        req = Request(self.base+path,data=json.dumps(data).encode(),headers={
            'Content-Type':'application/json','Origin':origin or self.base,'Cookie':cookie})
        try:
            response = self.opener.open(req,timeout=10)
        except HTTPError as exc:
            response = exc
        with response:
            return response.status,json.load(response),response.headers

    def request_link(self,email):
        self.assertEqual(self.post(self.path+'/request',dict(email=email))[0],200)
        body = json.loads(self.mail.call_args.args[1])
        self.assertEqual(body['to'],[email])
        return re.search(r'/verify#([A-Za-z0-9_-]{43})',body['text'])[1]

    def session(self,email):
        token = self.request_link(email)
        status,_,headers = self.post(self.path+'/redeem',dict(token=token))
        self.assertEqual(status,200)
        self.assertIn('HttpOnly',headers['Set-Cookie'])
        self.assertIn('Path='+self.path,headers['Set-Cookie'])
        self.assertNotIn('cm_session=',headers['Set-Cookie'])
        return headers['Set-Cookie'].split(';')[0]

    def answers(self,kind='individual'):
        return dict(participation_type=kind,participant_count=1,applicant_name='Guest',team_name='Friends',
                    representative_name='Captain',payment_method='bank_transfer',conditions_accepted=True)

    def test_member_signin_keeps_a_direct_guest_exit_for_the_same_event(self):
        target = self.path.removesuffix('/guest') + '/apply'
        signin = '/signin?' + urlencode({'return_to':target})
        status, body, _ = self.request(signin)
        self.assertEqual(status,200)
        page = BeautifulSoup(body,'html.parser')
        guest = page.find('a',href=self.path)
        self.assertIsNotNone(guest, 'An applicant must not be trapped at the member login gate')
        self.assertEqual(guest.get_text(strip=True),'ログインなしで参加を申し込む')
        self.assertIn('Google でログイン',page.get_text())
        status, _, headers = self.request(target)
        self.assertEqual(status,302)
        self.assertEqual(headers['Location'],self.path)
        guest_page = BeautifulSoup(self.request(self.path)[1],'html.parser')
        self.assertIsNotNone(guest_page.select_one('#guestEmail input[name="name"][required]'))
        self.assertIsNotNone(guest_page.select_one('#guestEmail input[name="email"][type="email"]'))
        self.assertIsNone(guest_page.select_one('#googleButton'))

    def test_signin_does_not_offer_guest_for_other_gates_or_ineligible_events(self):
        for target in ('/mypage','/events/new','/events/not-a-real-event/apply'):
            page = self.app.render_signin_html(target).decode()
            self.assertNotIn('id="guestEntryLink"',page)
        target = self.path.removesuffix('/guest') + '/apply'
        for column, value in (('payment_method','online'),('status','closed')):
            with self.app.connect() as conn:
                conn.execute(f'update event_posts set {column}=? where event_id=?',(value,self.eid))
            self.assertNotIn('id="guestEntryLink"',self.app.render_signin_html(target).decode())
            with self.app.connect() as conn:
                conn.execute("update event_posts set payment_method='bank_transfer',status='published' where event_id=?",(self.eid,))
        self.ready.return_value=False
        self.assertNotIn('id="guestEntryLink"',self.app.render_signin_html(target).decode())

    def test_guest_name_is_carried_only_after_mail_verification_and_prefills_application(self):
        name = '山田 <ゲスト>'
        self.assertEqual(self.post(self.path+'/request',dict(email='named@example.test',name=name))[0],200)
        mail = json.loads(self.mail.call_args.args[1])
        token = re.search(r'/verify#([A-Za-z0-9_-]{43})',mail['text'])[1]
        self.assertNotIn(name,mail['text'])
        self.assertEqual(self.post(self.path+'/apply',self.answers())[0],401)
        status,_,headers = self.post(self.path+'/redeem',dict(token=token))
        self.assertEqual(status,200)
        cookie = headers['Set-Cookie'].split(';')[0]
        page = BeautifulSoup(self.request(self.path,cookie=cookie)[1],'html.parser')
        self.assertEqual(page.select_one('#applicant_name')['value'],name)
        self.assertEqual(page.select_one('#representative_name')['value'],name)
        self.assertIsNone(page.select_one('#googleButton'))
        with self.app.connect() as conn:
            self.assertEqual(conn.execute('select count(*) from event_applications where event_id=?',(self.eid,)).fetchone()[0],0)
            self.assertEqual(conn.execute("select count(*) from user_sessions s join user_accounts u using(user_id) where u.provider='event_guest'").fetchone()[0],0)
        self.mail.reset_mock()
        self.assertEqual(self.post(self.path+'/request',dict(email='invalidname@example.test',name='a'*81))[0],400)
        self.mail.assert_not_called()

    def test_two_entries_and_email_link_not_account_or_booking(self):
        detail = BeautifulSoup(self.request(self.path.removesuffix('/guest'))[1],'html.parser')
        self.assertIsNotNone(detail.find('a',href=self.path))
        member = detail.find('a',string='ログインして参加を申し込む')
        self.assertTrue(member['href'].startswith('/signin?return_to='))
        signin = self.request(member['href'])[1].decode()
        self.assertIn('ログインなしで参加を申し込む',signin)
        self.assertNotIn('申込、募集掲載、受付管理を行う時だけログイン',signin)
        self.assertEqual(self.request(self.path+'/verify')[0],200)
        self.assertNotIn('googlesyndication',self.request(self.path+'/verify')[1].decode())
        token = self.request_link('one@example.test')
        self.assertEqual(self.post(self.path+'/redeem',dict(token=token),origin='https://other.example')[0],403)
        other_path = self.app.guests.path(self.event('Other event for scope'))
        self.assertEqual(self.post(other_path+'/redeem',dict(token=token))[0],400)
        status,_,headers = self.post(self.path+'/redeem',dict(token=token))
        self.assertEqual(status,200)
        self.assertEqual(self.post(self.path+'/redeem',dict(token=token))[0],400)
        cookie = headers['Set-Cookie'].split(';')[0]
        self.assertEqual(self.post(other_path+'/apply',self.answers(),cookie)[0],401)
        self.assertEqual(self.post('/api/events/'+quote(self.eid)+'/applications',self.answers(),cookie)[0],401)
        with self.app.connect() as conn:
            self.assertEqual(conn.execute('select count(*) from event_applications where event_id=?',(self.eid,)).fetchone()[0],0)
            self.assertEqual(conn.execute("select count(*) from user_sessions s join user_accounts u using(user_id) where u.provider='event_guest'").fetchone()[0],0)

    def test_team_application_attendance_bank_messages_cancel_and_recovery(self):
        cookie = self.session('captain@example.test')
        data = self.answers('team')
        self.assertEqual(self.post(self.path+'/apply',dict(data,conditions_accepted=False),cookie)[0],400)
        self.assertEqual(self.post(self.path+'/apply',data,cookie)[0],200)
        self.assertEqual(self.post(self.path+'/apply',data,cookie)[0],400)
        page = self.request(self.path,cookie=cookie)[1].decode()
        self.assertIn('15,000円',page)
        self.assertIn('Friends',page)
        with self.app.connect() as conn:
            self.app.announce_event(conn,self.eid,dict(version=0,starts_at='2030-06-01T10:00',location='Court',
                announcement_details='Meet here',attendance_deadline='2030-05-31T10:00',payment_deadline='2030-05-31T12:00',
                bank_transfer_details='TEST-ONLY-BANK'),self.host)
        self.assertNotIn('TEST-ONLY-BANK',self.request(self.path,cookie=cookie)[1].decode())
        self.assertEqual(self.post(self.path+'/attendance',{'version':1},cookie)[0],200)
        self.assertIn('TEST-ONLY-BANK',self.request(self.path,cookie=cookie)[1].decode())
        self.assertNotIn('TEST-ONLY-BANK',self.request(self.path)[1].decode())
        self.assertEqual(self.post(self.path+'/message',{'body':'Where is reception?'},cookie)[0],200)
        self.assertIn('Where is reception?',self.request(self.path+'/contact',cookie=cookie)[1].decode())
        self.assertEqual(self.post(self.path+'/exit',{},cookie)[0],200)
        self.assertEqual(self.post(self.path+'/cancel',{'accept':'yes'},cookie)[0],401)
        with self.app.connect() as conn:
            conn.execute("delete from app_state where state_key glob 'event-guest:v1:rate:cooldown:*'")
        replacement = self.session('captain@example.test')
        self.assertEqual(self.post(self.path+'/cancel',{'accept':'yes'},replacement)[0],200)
        self.assertIn('取消済み',self.request(self.path,cookie=replacement)[1].decode())
        with self.app.connect() as conn:
            payloads = [json.loads(r[0]) for r in conn.execute('select payload_json from event_email_outbox')]
        self.assertTrue(any(p['to']==['captain@example.test'] and self.path in p['text'] for p in payloads))

    def test_rate_expiry_owner_and_duplicate_member(self):
        email='cross@example.test'
        token=self.request_link(email)
        self.assertEqual(self.post(self.path+'/request',dict(email=email))[0],400)
        self.mail.assert_called_once()
        with self.app.connect() as conn:
            conn.execute("update app_state set updated_at='0' where state_key glob 'event-guest:v1:link:*'")
        self.assertEqual(self.post(self.path+'/redeem',dict(token=token))[0],400)
        member=user('member_cross',email,'Member')
        create_account(self.app,member)
        with self.app.connect() as conn:
            self.app.submit_event_application(conn,self.eid,self.answers(),member)
            conn.execute("delete from app_state where state_key glob 'event-guest:v1:rate:cooldown:*'")
        cookie=self.session(email)
        self.assertEqual(self.post(self.path+'/apply',self.answers(),cookie)[0],400)
        owner=self.session(self.host['email'])
        self.assertNotEqual(self.post(self.path+'/apply',self.answers(),owner)[0],200)

    def test_guest_then_member_cannot_double_book_and_capacity_is_shared(self):
        email='guestfirst@example.test'
        cookie=self.session(email)
        self.assertEqual(self.post(self.path+'/apply',dict(self.answers(),participant_count=2),cookie)[0],200)
        member=user('member_second',email,'Member')
        create_account(self.app,member)
        with self.assertRaisesRegex(ValueError,'既存の申込'),self.app.connect() as conn:
            self.app.submit_event_application(conn,self.eid,self.answers(),member)
        second=user('another_member','second@example.test','Second')
        create_account(self.app,second)
        with self.assertRaisesRegex(ValueError,'定員'),self.app.connect() as conn:
            self.app.submit_event_application(conn,self.eid,self.answers(),second)

    def test_delivery_failure_leaves_no_application(self):
        self.mail.side_effect=RuntimeError('mock provider error')
        self.assertEqual(self.post(self.path+'/request',dict(email='test@example.test'))[0],503)
        self.ready.return_value=False
        self.assertNotIn('会員登録なしで申し込む',self.request(self.path.removesuffix('/guest'))[1].decode())
        self.assertEqual(self.post(self.path+'/request',dict(email='test@example.test'))[0],503)

    def test_sessions_expire_and_never_authenticate_as_members(self):
        cookie = self.session('limited@example.test')
        with self.app.connect() as conn:
            guest = self.app.guests.actor(conn,self.eid,cookie.split('=',1)[1])
            member_token = self.app.create_user_session(conn,guest['user_id'])
        self.assertFalse(self.app.current_user(member_token)['authenticated'])
        with self.app.connect() as conn:
            conn.execute('delete from user_sessions where session_id=?',(member_token,))
            conn.execute("update app_state set updated_at='0' where state_key glob 'event-guest:v1:session:*'")
        self.assertEqual(self.post(self.path+'/apply',self.answers(),cookie)[0],401)

    def test_closed_recovery_and_cancellation_receipt_remain_available(self):
        cookie = self.session('recovery@example.test')
        self.assertEqual(self.post(self.path+'/apply',self.answers(),cookie)[0],200)
        with self.app.connect() as conn:
            conn.execute("update event_posts set status='closed' where event_id=?",(self.eid,))
            conn.execute("delete from app_state where state_key glob 'event-guest:v1:rate:cooldown:*'")
        replacement = self.session('recovery@example.test')
        self.assertIn('ゲスト申込の管理',self.request(self.path,cookie=replacement)[1].decode())
        self.assertEqual(self.post(self.path+'/cancel',{'accept':'yes'},replacement)[0],200)
        receipt = self.request(self.path,cookie=replacement)[1].decode()
        self.assertIn('ゲスト申込の管理',receipt)
        self.assertIn('取消',receipt)
        self.assertEqual(self.post(self.path+'/apply',self.answers(),replacement)[0],400)
        self.mail.reset_mock()
        self.assertEqual(self.post(self.path+'/request',{'email':'newwhenclosed@example.test'})[0],200)
        self.mail.assert_not_called()

    def test_guest_messages_and_cancellation_are_owned_by_the_current_guest(self):
        first = self.session('firstguest@example.test')
        second = self.session('secondguest@example.test')
        self.assertEqual(self.post(self.path+'/apply',self.answers(),first)[0],200)
        self.assertEqual(self.post(self.path+'/apply',dict(self.answers(),applicant_name='Other guest'),second)[0],200)
        self.assertEqual(self.post(self.path+'/message',{'body':'Private first message'},first)[0],200)
        self.assertNotIn('Private first message',self.request(self.path+'/contact',cookie=second)[1].decode())
        self.assertEqual(self.post(self.path+'/cancel',{'accept':'yes'},second)[0],200)
        self.assertNotIn('再申込',self.request(self.path,cookie=first)[1].decode())
        with self.app.connect() as conn:
            first_actor = self.app.guests.actor(conn,self.eid,first.split('=',1)[1])
            row = conn.execute('select status from event_applications where event_id=? and applicant_user_id=?',
                               (self.eid,first_actor['user_id'])).fetchone()
        self.assertEqual(row['status'],'confirmed')

    def test_concurrent_guests_share_capacity_transactionally(self):
        cookies = [self.session('raceone@example.test'),self.session('racetwo@example.test')]
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(lambda cookie:self.post(self.path+'/apply',
                dict(self.answers(),participant_count=2),cookie)[0],cookies))
        self.assertCountEqual(outcomes,[200,400])
        with self.app.connect() as conn:
            total = conn.execute("select sum(participant_count) from event_applications where event_id=? and status='confirmed'",
                                 (self.eid,)).fetchone()[0]
        self.assertEqual(total,2)

    def test_cancelled_unsettled_application_shows_payment_receipt(self):
        cookie = self.session('unsettled@example.test')
        self.assertEqual(self.post(self.path+'/apply',self.answers(),cookie)[0],200)
        with self.app.connect() as conn:
            conn.execute("update event_applications set status='cancelled',payment_status='refund_pending' where event_id=?",(self.eid,))
        page = self.request(self.path,cookie=cookie)[1].decode()
        self.assertIn('ゲスト申込の管理',page)
        self.assertIn('返金',page)
        self.assertNotIn('再申込',page)
        self.assertEqual(self.post(self.path+'/apply',self.answers(),cookie)[0],400)

    def test_free_approval_guest_and_online_event_stays_member_only(self):
        with self.app.connect() as conn:
            conn.execute("update event_posts set acceptance_mode='approval',fee_amount=0,individual_fee_amount=0,team_fee_amount=0,payment_method='free' where event_id=?",(self.eid,))
        cookie = self.session('freeapproval@example.test')
        self.assertEqual(self.post(self.path+'/apply',self.answers(),cookie)[0],200)
        with self.app.connect() as conn:
            row = conn.execute('select status from event_applications where event_id=?',(self.eid,)).fetchone()
            self.assertEqual(row['status'],'pending')
            conn.execute("update event_posts set payment_method='online' where event_id=?",(self.eid,))
        self.assertNotIn('会員登録なしで申し込む',self.request(self.path.removesuffix('/guest'))[1].decode())
        self.mail.reset_mock()
        self.assertEqual(self.post(self.path+'/request',{'email':'newonline@example.test'})[0],200)
        self.mail.assert_not_called()
