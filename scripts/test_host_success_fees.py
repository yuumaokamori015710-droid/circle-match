"""Organizer success fees: consent, exact balances, private access and safe checkout."""
import json
import re
import sqlite3
import subprocess
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from test_event_flow import load_app, user, create_account, event_payload


class HostSuccessFeeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.app = load_app(Path(cls.temp.name) / 'host-fees.sqlite')
        cls.app.HOST_FEES_ENABLED = True
        cls.app.init_db()
        cls.app.EMAIL_NOTIFICATIONS_ENABLED = False
        cls.host = user('fee_host', 'host@example.test', 'Fee Host')
        cls.guest = user('fee_guest', 'guest@example.test', 'Fee Guest')
        cls.other = user('fee_other', 'other@example.test', 'Other Host')
        cls.sessions = {}
        for account in [cls.host, cls.guest, cls.other]:
            create_account(cls.app, account)
            with cls.app.connect() as conn:
                cls.sessions[account['user_id']] = cls.app.create_user_session(conn, account['user_id'])
        cls.server = ThreadingHTTPServer(('127.0.0.1', 0), cls.app.Handler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.base = f'http://127.0.0.1:{cls.server.server_port}'

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()
        cls.temp.cleanup()

    def event(self, prefix=''):
        payload = event_payload(prefix+self.id(), capacity='')
        payload.update(participation_type='both', individual_fee_amount=2500, team_fee_amount=15000,
                       minimum_participants=2, payment_method='on_site',
                       host_fee_accepted=True, host_fee_policy_version=self.app.host_fees.POLICY_VERSION)
        with self.app.connect() as conn:
            return self.app.save_event_post(conn, payload, self.host)

    def apply(self, eid):
        with self.app.connect() as conn:
            return self.app.submit_event_application(conn, eid, dict(participation_type='individual',
                applicant_name='Guest', participant_count=2), self.guest)

    def announce(self, eid):
        with self.app.connect() as conn:
            return self.app.announce_event(conn, eid, dict(version=0, starts_at='2030-06-01T10:00',
                location='Test court', announcement_details='Meet at the gate', attendance_deadline='2030-05-31T10:00'), self.host)

    def get(self, path, account=None):
        headers = {'Cookie': 'cm_session=' + self.sessions[account['user_id']]} if account else {}
        return urlopen(Request(self.base + path, headers=headers), timeout=10)

    def test_integer_rounding_is_exact(self):
        fees = self.app.host_fees
        for gross, expected in [(0, 0), (1, 1), (2500, 250), (15000, 1500), (2501, 251), (999999999, 100000000)]:
            self.assertEqual(fees.fee(gross), expected)
        for invalid in [True, -1, 1.5, '2500', None]:
            with self.assertRaises(ValueError):
                fees.fee(invalid)

    def test_mixed_tariffs_no_cap_counts_team_once(self):
        event = dict(status='published', participation_type='both', capacity_unit='人', minimum_participants=2,
                     announcement_version=1, individual_fee_amount=2500, team_fee_amount=15000)
        apps = [dict(status='confirmed', participation_type='individual', participant_count=2),
                dict(status='confirmed', participation_type='team', participant_count=11),
                dict(status='pending', participation_type='team', participant_count=12)]
        result = self.app.host_fees.estimate(event, apps)
        self.assertEqual((result['forecast_gross'], result['forecast_fee']), (20000, 2000))
        self.assertEqual(result['proposed_additional_fee'], 2000)
        self.assertIsNone(result['charge_due'])
        self.assertFalse(result['billing_enabled'])

    def test_threshold_is_not_billing_or_formation(self):
        eid = self.event()
        self.apply(eid)
        _, result = self.app.host_fee_estimate(eid, self.host)
        self.assertEqual(result['state'], 'pending')
        self.assertEqual(result['forecast_fee'], 500)
        self.assertEqual(result['proposed_additional_fee'], 0)
        self.assertEqual(result['charge_due'], 0)
        self.announce(eid)
        _, formed = self.app.host_fee_estimate(eid, self.host)
        self.assertEqual(formed['state'], 'announced')
        self.assertEqual(formed['proposed_additional_fee'], 500)
        self.assertEqual(formed['charge_due'], 0)
        with self.app.connect() as conn:
            conn.execute("update event_applications set payment_status='paid' where event_id=?", (eid,))
        _, collected = self.app.host_fee_estimate(eid, self.host)
        self.assertEqual(collected['charge_due'], 500)

    def test_free_unknown_cancelled_and_below_minimum(self):
        event = dict(status='published', participation_type='individual', capacity_unit='人',
                     minimum_participants=2, announcement_version=1, fee_unit='1人', fee_amount=0)
        apps = [dict(status='confirmed', participation_type='individual', participant_count=2)]
        fees = self.app.host_fees
        self.assertEqual(fees.estimate(event, apps)['forecast_fee'], 0)
        unknown = fees.estimate(dict(event, fee_amount=None), apps)
        self.assertIsNone(unknown['forecast_gross'])
        self.assertIsNone(unknown['forecast_fee'])
        self.assertIsNone(unknown['proposed_additional_fee'])
        self.assertEqual(fees.estimate(dict(event, status='cancelled', fee_amount=2500), apps)['proposed_additional_fee'], 0)
        below = fees.estimate(dict(event, fee_amount=2500, minimum_participants=3), apps)
        self.assertEqual((below['state'], below['proposed_additional_fee']), ('review', 0))

    def test_live_withheld_fees_are_not_charged_twice_and_test_funds_ignored(self):
        event = dict(status='published', participation_type='individual', capacity_unit='人',
                     minimum_participants=1, announcement_version=1, fee_unit='1人', fee_amount=2500)
        apps = [dict(status='confirmed', participation_type='individual', participant_count=2)]
        orders = [dict(fee=500, fee_refunded=0, paid_at='2030-01-01', mode='live'),
                  dict(fee=500, fee_refunded=0, paid_at='2030-01-01', mode='test')]
        result = self.app.host_fees.estimate(event, apps, orders)
        self.assertEqual((result['online_fee_withheld'], result['proposed_additional_fee']), (500, 0))

    def test_host_page_and_api_reject_other_users_and_anonymous(self):
        eid = self.event()
        for account in [self.guest, self.other]:
            with self.assertRaises(PermissionError):
                self.app.host_fee_estimate(eid, account)
            for suffix in [f'/events/{eid}/host-fee', f'/api/events/{eid}/host-fee']:
                with self.assertRaises(HTTPError) as error:
                    self.get(suffix, account)
                self.assertEqual(error.exception.code, 403)
                error.exception.close()
        with self.assertRaises(HTTPError) as error:
            self.get(f'/api/events/{eid}/host-fee')
        self.assertEqual(error.exception.code, 401)
        error.exception.close()
        with self.get(f'/events/{eid}/host-fee', self.host) as response:
            self.assertIn('no-store', response.headers['Cache-Control'])
            page = response.read().decode()
        self.assertIn('主催者のみ / 利用料10%', page)
        self.assertIn('オンライン決済は接続準備中', page)
        self.assertIn('noindex', page)

    def test_owner_disclosure_never_enters_participant_views_or_public_api(self):
        eid = self.event()
        self.apply(eid)
        self.announce(eid)
        for page in [self.app.render_event_detail_html(eid, self.guest), self.app.render_event_apply_html(eid, self.other),
                     self.app.render_event_attendance_html(eid, self.guest), self.app.render_mypage_html(self.guest),
                     json.dumps(self.app.get_event(eid)), json.dumps(self.app.search_events({}))]:
            self.assertNotIn('data-host-fee-private', page)
            self.assertNotIn('success-fee-proposal', page)
            self.assertNotIn('forecast_fee', page)
        markup, script = self.app.event_share_dialog(self.app.get_event(eid))
        self.assertNotIn('主催者利用料', markup + script)
        self.assertNotIn('料金案', json.dumps(self.app.notifications_for_user(self.guest), ensure_ascii=False))
        self.assertIn('data-host-fee-private', self.app.render_mypage_html(self.host))
        self.assertIn('data-host-fee-private', self.app.render_event_organize_html(eid, self.host))

    def test_preview_reads_do_not_create_invoices_payments_or_change_schema(self):
        eid = self.event()
        self.apply(eid)
        self.announce(eid)
        with self.app.connect() as conn:
            before_schema = list(conn.execute('select name,sql from sqlite_master order by name'))
            before_orders = conn.execute('select count(*) from payment_orders').fetchone()[0]
        for _ in range(3):
            self.app.host_fee_estimate(eid, self.host)
            self.app.render_host_fee_html(eid, self.host)
        with self.app.connect() as conn:
            self.assertEqual(before_schema, list(conn.execute('select name,sql from sqlite_master order by name')))
            self.assertEqual(before_orders, conn.execute('select count(*) from payment_orders').fetchone()[0])

    def test_disabled_by_default_has_no_host_fee_markup_or_route(self):
        eid = self.event()
        try:
            self.app.HOST_FEES_ENABLED = False
            self.assertNotIn('data-host-fee-private', self.app.render_event_form_html({}, self.host))
            self.assertNotIn('data-host-fee-private', self.app.render_mypage_html(self.host))
            with self.assertRaises(HTTPError) as error:
                self.get(f'/events/{eid}/host-fee', self.host)
            self.assertEqual(error.exception.code, 404)
            error.exception.close()
        finally:
            self.app.HOST_FEES_ENABLED = True

    def test_form_javascript_parses_and_requires_prior_fee_consent(self):
        page = self.app.render_event_form_html({}, self.host)
        self.assertIn('hostFeeUnitPreview', page)
        self.assertIn('data-host-fee-private', page)
        self.assertIn('10%', page)
        self.assertIn('host_fee_accepted', page)
        self.assertIn('id="hostFeeConsent"', page)
        for script in re.findall(r'<script>(.*?)</script>', page, re.S):
            result = subprocess.run(['node', '--check'], input=script, encoding='utf-8', capture_output=True)
            self.assertEqual(result.returncode, 0, result.stderr)

    def billing(self):
        class Gateway:
            def __init__(self):
                self.sessions, self.keys, self.created = {}, {}, 0

            def platform(inner):
                return dict(id='acct_Local',country='JP',default_currency='jpy',charges_enabled=True)

            def create_session(inner, params, key):
                if key not in inner.keys:
                    inner.created += 1
                    sid = 'cs_host_' + params['client_reference_id']
                    inner.keys[key] = sid
                    inner.sessions[sid] = dict(id=sid,mode='payment',currency='jpy',livemode=False,
                        amount_total=params['line_items'][0]['price_data']['unit_amount'],
                        client_reference_id=params['client_reference_id'], metadata=params['metadata'],
                        payment_status='unpaid',status='open',url='https://checkout.stripe.com/c/pay/'+sid)
                    self.assertNotIn('application_fee_amount', params['payment_intent_data'])
                    self.assertNotIn('transfer_data', params['payment_intent_data'])
                return json.loads(json.dumps(inner.sessions[inner.keys[key]]))

            def session(inner, sid):
                return json.loads(json.dumps(inner.sessions[sid]))

            def expire(inner, sid):
                inner.sessions[sid]['status'] = 'expired'

            def paid(inner, sid, *, wrong_amount=False):
                current = inner.sessions[sid]
                amount = current['amount_total']
                current.update(payment_status='paid',status='complete',payment_intent=dict(id='pi_'+sid,
                    status='succeeded',currency='jpy',livemode=False,amount=amount,
                    amount_received=amount + int(wrong_amount),
                    latest_charge=dict(id='ch_'+sid,payment_intent='pi_'+sid,paid=True,captured=True,
                        amount=amount,currency='jpy',livemode=False,amount_refunded=0)))

            def verify(inner, body, signature, connected=False):
                if signature != 'signed':
                    raise ValueError('bad signature')
                return json.loads(body)

        gateway = Gateway()
        config = self.app.online_payments.Config(enabled=True,mode='test',key='sk_test_local',
            webhook_secret='whsec_platform',platform='acct_Local',base_url='http://127.0.0.1:8930',
            connect_webhook_secret='whsec_connect')
        payments = self.app.online_payments.Payments(self.app.connect,self.app.add_event_notification,config,gateway)
        billing = self.app.host_billing.Billing(self.app.connect,payments,self.app.add_event_notification)
        payments.unmatched_webhook = billing.webhook_job
        return billing, gateway, payments

    def paid_event(self):
        eid = self.event()
        self.apply(eid)
        self.announce(eid)
        with self.app.connect() as conn:
            conn.execute("update event_applications set payment_status='paid' where event_id=?", (eid,))
        return eid

    def test_fee_consent_cannot_be_bypassed_and_legacy_events_are_exempt(self):
        payload = event_payload(self.id(),capacity='')
        payload.update(minimum_participants=1)
        with self.app.connect() as conn:
            with self.assertRaisesRegex(ValueError, '同意'):
                self.app.save_event_post(conn,payload,self.host)
        eid = self.event()
        with self.app.connect() as conn:
            self.assertIsNotNone(self.app.host_billing.agreement(conn,eid)['accepted_at'])
            conn.execute('delete from host_fee_agreements where event_id=?', (eid,))
        _, balance = self.app.host_fee_estimate(eid,self.host)
        self.assertTrue(balance['legacy_event'])
        self.assertEqual(balance['charge_due'],0)
        form = self.app.render_event_form_html({'event_id':[eid]},self.host)
        self.assertIn('この募集は利用料導入前のため対象外',form)
        self.assertNotIn('id="hostFeeConsent"',form)
        self.assertNotIn('成立した有料大会には、参加費売上の10%',form)

    def test_unknown_create_retries_the_same_order_and_key(self):
        eid = self.paid_event()
        billing, gateway, _ = self.billing()
        with self.app.connect() as conn:
            _, balance = billing.balance(conn,eid,self.host['user_id'])
        data = dict(accepted=True,quote_token=balance['quote_token'])
        create = gateway.create_session
        def interrupted(params,key):
            create(params,key)
            raise TimeoutError('response lost after provider created the session')
        gateway.create_session = interrupted
        with self.assertRaises(TimeoutError):
            billing.checkout(eid,self.host['user_id'],data)
        gateway.create_session = create
        self.assertTrue(billing.checkout(eid,self.host['user_id'],data)['url'].startswith('https://checkout.stripe.com/'))
        self.assertEqual(gateway.created,1)
        with self.app.connect() as conn:
            self.assertEqual(conn.execute('select count(*) from host_fee_orders where event_id=?',(eid,)).fetchone()[0],1)

    def test_legacy_opt_in_requires_owner_csrf_and_current_explicit_consent(self):
        eid = self.event()
        with self.app.connect() as conn:
            conn.execute('delete from host_fee_agreements where event_id=?', (eid,))
        path = f'/events/{eid}/host-fee'
        with self.get(path, self.host) as response:
            page = response.read().decode()
        self.assertIn('この大会への適用は任意', page)
        self.assertIn('type="checkbox" name="accepted" required', page)
        self.assertNotIn(' checked', page.split('data-pay=')[-1].split('</form>')[0])
        data = dict(accepted=True, policy_version=self.app.host_fees.POLICY_VERSION)

        def post(account, payload, csrf=True):
            cookie = 'cm_session=' + self.sessions[account['user_id']] if account else ''
            headers = {'Cookie':cookie, 'Content-Type':'application/json'}
            if csrf:
                import hmac, hashlib
                identity = self.sessions[account['user_id']] if account else ''
                headers['X-CSRF-Token'] = hmac.new(self.app.SESSION_SECRET.encode(),
                    ('payments:'+identity).encode(), hashlib.sha256).hexdigest()
            req = Request(self.base+f'/api/payments/host-fees/{eid}/opt-in',
                          data=json.dumps(payload).encode(),headers=headers)
            try:
                with urlopen(req,timeout=10) as response:
                    return response.status
            except HTTPError as error:
                error.close()
                return error.code

        self.assertEqual(post(None,data),401)
        self.assertEqual(post(self.other,data),403)
        self.assertEqual(post(self.host,data,False),403)
        for invalid in [dict(data,accepted=False), dict(data,accepted=1),
                        dict(data,policy_version='old'), dict(data,amount=0)]:
            self.assertEqual(post(self.host,invalid),400)
        with self.app.connect() as conn:
            self.assertIsNone(self.app.host_billing.agreement(conn,eid))
        self.assertEqual(post(self.host,data),200)
        with self.app.connect() as conn:
            accepted = self.app.host_billing.agreement(conn,eid)
        self.assertEqual(post(self.host,data),200)
        with self.app.connect() as conn:
            self.assertEqual(accepted,self.app.host_billing.agreement(conn,eid))
            self.assertEqual(accepted['organizer_id'],self.host['user_id'])
            self.assertTrue(accepted['accepted_at'])
            self.assertEqual(conn.execute('select count(*) from host_fee_orders where event_id=?',(eid,)).fetchone()[0],0)
        self.assertNotIn('/opt-in',self.app.render_host_fee_html(eid,self.host))
        self.assertNotIn('/opt-in',self.app.render_event_detail_html(eid,self.guest))
        self.apply(eid)
        self.announce(eid)
        self.assertEqual(self.app.host_fee_estimate(eid,self.host)[1]['charge_due'],0)
        with self.app.connect() as conn:
            conn.execute("update event_applications set payment_status='paid' where event_id=?", (eid,))
        self.assertEqual(self.app.host_fee_estimate(eid,self.host)[1]['charge_due'],500)

    def test_legacy_consent_rechecks_formation_and_existing_payments(self):
        for reason in ['announced','paid','cancelled','past','free']:
            with self.subTest(reason=reason):
                eid = self.event(reason)
                self.apply(eid)
                with self.app.connect() as conn:
                    conn.execute('delete from host_fee_agreements where event_id=?',(eid,))
                self.assertIn('/opt-in',self.app.render_host_fee_html(eid,self.host))
                with self.app.connect() as conn:
                    if reason == 'paid':
                        conn.execute("update event_applications set payment_status='paid' where event_id=?",(eid,))
                    else:
                        update = {'announced':'announcement_version=1', 'cancelled':"status='cancelled'",
                                  'past':"starts_at='2020-01-01T09:00'", 'free':'individual_fee_amount=0,team_fee_amount=0'}[reason]
                        conn.execute('update event_posts set '+update+' where event_id=?',(eid,))
                self.assertNotIn('/opt-in',self.app.render_host_fee_html(eid,self.host))
                with self.assertRaises(ValueError), self.app.connect() as conn:
                    self.app.host_billing.opt_in_legacy(conn,eid,self.host['user_id'],
                        dict(accepted=True,policy_version=self.app.host_fees.POLICY_VERSION),self.app.event_local_now())
                with self.app.connect() as conn:
                    self.assertIsNone(self.app.host_billing.agreement(conn,eid))

    def test_uncertain_creation_beyond_idempotency_window_requires_review(self):
        eid = self.paid_event()
        billing, gateway, _ = self.billing()
        with self.app.connect() as conn:
            _, balance = billing.balance(conn,eid,self.host['user_id'])
        data = dict(accepted=True,quote_token=balance['quote_token'])
        create = gateway.create_session
        def interrupted(params,key):
            create(params,key)
            raise TimeoutError('response lost')
        gateway.create_session = interrupted
        with self.assertRaises(TimeoutError):
            billing.checkout(eid,self.host['user_id'],data)
        gateway.create_session = create
        with self.app.connect() as conn:
            conn.execute('update host_fee_orders set created_epoch=0 where event_id=?',(eid,))
        with self.assertRaisesRegex(ValueError,'結果が不明'):
            billing.checkout(eid,self.host['user_id'],data)
        self.assertEqual(gateway.created,1)
        with self.app.connect() as conn:
            _, balance = billing.balance(conn,eid,self.host['user_id'])
        self.assertIsNone(balance['charge_due'])

    def test_cancelled_event_expires_open_checkout_without_a_second_payment(self):
        eid = self.paid_event()
        billing, gateway, _ = self.billing()
        with self.app.connect() as conn:
            _, balance = billing.balance(conn,eid,self.host['user_id'])
        data = dict(accepted=True,quote_token=balance['quote_token'])
        billing.checkout(eid,self.host['user_id'],data)
        with self.app.connect() as conn:
            self.app.set_event_status(conn,eid,'cancelled',self.host)
        with self.assertRaisesRegex(ValueError,'成立状態が変わり'):
            billing.checkout(eid,self.host['user_id'],data)
        sid = next(iter(gateway.sessions))
        self.assertEqual(gateway.sessions[sid]['status'],'expired')
        self.assertEqual(gateway.created,1)

    def test_paid_order_review_blocks_later_checkout(self):
        eid = self.paid_event()
        billing, gateway, _ = self.billing()
        with self.app.connect() as conn:
            _, balance = billing.balance(conn,eid,self.host['user_id'])
        billing.checkout(eid,self.host['user_id'],dict(accepted=True,quote_token=balance['quote_token']))
        with self.app.connect() as conn:
            old = dict(conn.execute('select * from host_fee_orders where event_id=?',(eid,)).fetchone())
        gateway.paid(old['session_id'])
        billing.resume(old['order_id'],self.host['user_id'],create=False)
        with self.app.connect() as conn:
            self.app.submit_event_application(conn,eid,dict(participation_type='individual',
                applicant_name='Another Guest',participant_count=1),self.other)
            conn.execute("update event_applications set payment_status='paid' where event_id=?",(eid,))
        with self.app.connect() as conn:
            _, balance = billing.balance(conn,eid,self.host['user_id'])
        self.assertEqual(balance['charge_due'],250)
        billing.checkout(eid,self.host['user_id'],dict(accepted=True,quote_token=balance['quote_token']))
        gateway.sessions[old['session_id']]['payment_intent']['latest_charge']['amount_refunded'] = 100
        billing.resume(old['order_id'],self.host['user_id'],create=False)
        with self.app.connect() as conn:
            _, balance = billing.balance(conn,eid,self.host['user_id'])
            self.assertEqual(conn.execute('select count(*) from host_fee_orders where event_id=? and active=1',(eid,)).fetchone()[0],1)
        self.assertIsNone(balance['charge_due'])

    def test_checkout_is_idempotent_and_collects_only_the_site_fee(self):
        eid = self.paid_event()
        billing, gateway, _ = self.billing()
        with self.app.connect() as conn:
            _, balance = billing.balance(conn,eid,self.host['user_id'])
        data = dict(accepted=True,quote_token=balance['quote_token'])
        first = billing.checkout(eid,self.host['user_id'],data)
        second = billing.checkout(eid,self.host['user_id'],data)
        self.assertEqual(first,second)
        self.assertEqual(gateway.created,1)
        with self.app.connect() as conn:
            order = dict(conn.execute('select * from host_fee_orders where event_id=?',(eid,)).fetchone())
        self.assertEqual(order['amount'],500)
        gateway.paid(order['session_id'])
        billing.resume(order['order_id'],self.host['user_id'],create=False)
        billing.resume(order['order_id'],self.host['user_id'],create=False)
        with self.app.connect() as conn:
            _, settled = billing.balance(conn,eid,self.host['user_id'])
            self.assertEqual((settled['charge_due'],settled['fee_paid']),(0,500))
            notes = conn.execute("select count(*) from event_notifications where event_id=? and notification_type='host_fee_paid'",(eid,)).fetchone()[0]
        self.assertEqual(notes,1)
        with self.assertRaises(ValueError):
            billing.checkout(eid,self.host['user_id'],dict(accepted=True,quote_token=settled['quote_token']))
        self.assertEqual(gateway.created,1)

    def test_signed_webhook_reconciles_host_fee_and_replays_do_not_double_count(self):
        eid = self.paid_event()
        billing, gateway, payments = self.billing()
        with self.app.connect() as conn:
            _, balance = billing.balance(conn,eid,self.host['user_id'])
        billing.checkout(eid,self.host['user_id'],dict(accepted=True,quote_token=balance['quote_token']))
        sid = next(iter(gateway.sessions))
        gateway.paid(sid)
        body = json.dumps(dict(id='evt_host_fee_'+eid,type='checkout.session.completed',livemode=False,
                               data={'object':{'id':sid,'payment_intent':'pi_'+sid}})).encode()
        with self.assertRaises(ValueError):
            payments.receive_webhook(body,'wrong')
        payments.receive_webhook(body,'signed')
        self.assertTrue(payments.webhook_job())
        payments.receive_webhook(body,'signed')
        self.assertFalse(payments.webhook_job())
        with self.app.connect() as conn:
            _, balance = billing.balance(conn,eid,self.host['user_id'])
        self.assertEqual((balance['charge_due'],balance['fee_paid']),(0,500))

    def test_amount_tampering_stale_quotes_and_wrong_payer_are_rejected(self):
        eid = self.paid_event()
        billing, gateway, _ = self.billing()
        with self.app.connect() as conn:
            _, balance = billing.balance(conn,eid,self.host['user_id'])
        with self.assertRaises(ValueError):
            billing.checkout(eid,self.host['user_id'],dict(accepted=True,quote_token=balance['quote_token'],amount=1))
        with self.assertRaises(PermissionError):
            billing.checkout(eid,self.other['user_id'],dict(accepted=True,quote_token=balance['quote_token']))
        with self.app.connect() as conn:
            conn.execute("update event_applications set payment_status='unpaid' where event_id=?",(eid,))
        with self.assertRaises(ValueError):
            billing.checkout(eid,self.host['user_id'],dict(accepted=True,quote_token=balance['quote_token']))
        self.assertEqual(gateway.created,0)

    def test_wrong_remote_amount_requires_review_instead_of_marking_paid(self):
        eid = self.paid_event()
        billing, gateway, _ = self.billing()
        with self.app.connect() as conn:
            _, balance = billing.balance(conn,eid,self.host['user_id'])
        billing.checkout(eid,self.host['user_id'],dict(accepted=True,quote_token=balance['quote_token']))
        with self.app.connect() as conn:
            order = dict(conn.execute('select * from host_fee_orders where event_id=?',(eid,)).fetchone())
        gateway.paid(order['session_id'],wrong_amount=True)
        with self.assertRaises(self.app.online_payments.VerificationError):
            billing.resume(order['order_id'],self.host['user_id'],create=False)
        with self.app.connect() as conn:
            _, balance = billing.balance(conn,eid,self.host['user_id'])
        self.assertIsNone(balance['charge_due'])
        self.assertEqual(balance['fee_paid'],0)

    def test_http_payment_requires_owner_and_csrf_and_keeps_price_server_side(self):
        eid = self.paid_event()
        billing, gateway, payments = self.billing()
        previous = self.app._payments
        self.app._payments = payments
        self.addCleanup(setattr,self.app,'_payments',previous)
        with self.get(f'/events/{eid}/host-fee',self.host) as response:
            page = response.read().decode()
        csrf = json.loads(re.search(r"'X-CSRF-Token':(\"[^\"]+\")",page).group(1))
        with self.app.connect() as conn:
            _, balance = billing.balance(conn,eid,self.host['user_id'])
        endpoint = self.base+f'/api/payments/host-fees/{eid}/checkout'
        data = json.dumps(dict(accepted=True,quote_token=balance['quote_token'])).encode()
        headers = {'Content-Type':'application/json','Cookie':'cm_session='+self.sessions[self.host['user_id']]}
        with self.assertRaises(HTTPError) as error:
            urlopen(Request(endpoint,data=data,headers=headers))
        self.assertEqual(error.exception.code,403)
        error.exception.close()
        headers['X-CSRF-Token'] = csrf
        with urlopen(Request(endpoint,data=data,headers=headers)) as response:
            self.assertEqual(response.status,200)
            self.assertTrue(json.load(response)['url'].startswith('https://checkout.stripe.com/'))
        self.assertEqual(gateway.created,1)

    def test_invoice_snapshot_is_immutable_and_cancellation_requires_refund_review(self):
        eid = self.paid_event()
        billing, gateway, _ = self.billing()
        with self.app.connect() as conn:
            _, balance = billing.balance(conn,eid,self.host['user_id'])
        billing.checkout(eid,self.host['user_id'],dict(accepted=True,quote_token=balance['quote_token']))
        with self.app.connect() as conn:
            order = dict(conn.execute('select * from host_fee_orders where event_id=?',(eid,)).fetchone())
            with self.assertRaises(sqlite3.IntegrityError):
                conn.execute('update host_fee_orders set amount=1 where order_id=?',(order['order_id'],))
        gateway.paid(order['session_id'])
        billing.resume(order['order_id'],self.host['user_id'],create=False)
        with self.app.connect() as conn:
            self.app.set_event_status(conn,eid,'cancelled',self.host)
        with self.app.connect() as conn:
            _, balance = billing.balance(conn,eid,self.host['user_id'])
        self.assertEqual((balance['charge_due'],balance['refund_review_amount']),(0,500))

    def test_participant_checkout_does_not_show_organizer_fee_allocation(self):
        snapshot = dict(title='Event',organizer_name='Host',starts_at='2030-06-01',prefecture='東京都',location='Court',
                        unit_amount=2500,fee_unit='1人',quantity=1,payment_deadline='',gross=2500,
                        cancellation_policy='Conditions',refund_policy='Full refund policy')
        payer = self.app.payment_ui.recap(snapshot)
        owner = self.app.payment_ui.recap(snapshot,owner=True)
        self.assertNotIn('10％',payer)
        self.assertNotIn('主催者向け利用料',payer)
        self.assertIn('2,500円',payer)
        self.assertIn('10％',owner)


if __name__ == '__main__':
    unittest.main()
