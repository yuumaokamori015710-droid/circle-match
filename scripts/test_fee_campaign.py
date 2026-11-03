"""Campaign rollout and stopping safety; temporary DB and synthetic Stripe only."""
import base64
from dataclasses import replace
import hashlib
import hmac
import json
import threading
import time
import unittest
from unittest.mock import patch
from urllib.error import HTTPError
from urllib.request import Request, urlopen

from test_event_flow import event_payload
import test_host_success_fees as fixtures
import manage_host_fee_campaign as operator


class FeeCampaignTests(unittest.TestCase):
    event = fixtures.HostSuccessFeeTests.event
    apply = fixtures.HostSuccessFeeTests.apply
    announce = fixtures.HostSuccessFeeTests.announce
    paid_event = fixtures.HostSuccessFeeTests.paid_event
    billing = fixtures.HostSuccessFeeTests.billing

    @classmethod
    def setUpClass(cls):
        fixtures.HostSuccessFeeTests.setUpClass.__func__(cls)

    @classmethod
    def tearDownClass(cls):
        fixtures.HostSuccessFeeTests.tearDownClass.__func__(cls)

    def setUp(self):
        with self.app.connect() as conn:
            conn.execute('delete from host_fee_orders')
            conn.execute('delete from payment_webhooks')
            conn.execute('delete from payment_rate_limits')
            conn.execute('delete from app_state where state_key=?', (self.app.fee_campaign.KEY,))
        _, self.gateway, payments = self.billing()
        payments.config = replace(payments.config, enabled=False, live_approved=False)
        self.app._payments = payments

    def toggle(self, enabled):
        with self.app.connect() as conn:
            current = self.app.fee_campaign.status(conn)
            return self.app.fee_campaign.change(conn, dict(enabled=enabled,
                revision=current['revision'], accepted=enabled))

    def balance(self, eid):
        with self.app.connect() as conn:
            return self.app.host_fee_service().balance(conn,eid,self.host['user_id'])[1]

    def checkout(self, eid, quote=None):
        return self.app.host_fee_service().checkout(eid,self.host['user_id'],
            dict(accepted=True,quote_token=quote or self.balance(eid)['quote_token']))

    def request(self, path, data=None, *, admin=False, member=False, csrf=True, headers=None):
        headers = dict(headers or {})
        identity = ''
        if admin:
            identity = 'Basic '+base64.b64encode((self.app.ADMIN_USERNAME+':'+self.app.ADMIN_PASSWORD).encode()).decode()
            headers['Authorization'] = identity
        elif member:
            identity = self.sessions[self.host['user_id']]
            headers['Cookie'] = 'cm_session='+identity
        if data is not None:
            headers['Content-Type'] = 'application/json'
            if csrf:
                headers['X-CSRF-Token'] = hmac.new(self.app.SESSION_SECRET.encode(),
                    ('payments:'+identity).encode(),hashlib.sha256).hexdigest()
            if isinstance(data,dict):
                data = json.dumps(data).encode()
        try:
            response = urlopen(Request(self.base+path,data=data,headers=headers),timeout=10)
        except HTTPError as error:
            response = error
        with response:
            body = response.read().decode()
            return response.code, json.loads(body) if 'application/json' in response.headers.get('Content-Type','') else body

    def test_default_off_freezes_exemption_and_never_records_stale_consent(self):
        with self.app.connect() as conn:
            schema = list(conn.execute('select name,sql from sqlite_master order by name'))
        eid = self.paid_event()
        self.assertEqual((self.balance(eid)['fee_total'],self.balance(eid)['charge_due']),(0,0))
        with self.app.connect() as conn:
            self.assertIsNone(self.app.host_billing.agreement(conn,eid)['accepted_at'])
            frozen = self.app.fee_campaign.publication(conn,eid)
        for enabled in [True,False,True]:
            self.toggle(enabled)
            self.assertTrue(self.balance(eid)['fee_waived'])
            self.assertEqual(self.balance(eid)['charge_due'],0)
            with self.assertRaises(ValueError):
                self.checkout(eid)
        with self.app.connect() as conn:
            self.assertEqual(frozen,self.app.fee_campaign.publication(conn,eid))
            self.assertEqual(conn.execute('select count(*) from host_fee_orders').fetchone()[0],0)
            self.assertEqual(schema,list(conn.execute('select name,sql from sqlite_master order by name')))

    def manage(self, command, revision, confirm=False):
        return operator.run(command,self.app.connect,revision=revision,confirm=confirm,actor='test-render-shell',
            config=self.app.payment_service().config,gateway=self.gateway,app=self.app)

    def test_shell_requires_explicit_consent_revision_audit_and_separate_switches(self):
        with self.app.connect() as conn:
            before = conn.execute("select count(*) from audit_logs where action='host_fee_campaign_change'").fetchone()[0]
        for revision,confirm in [(0,False),(True,True),(None,True)]:
            with self.assertRaises(ValueError):
                self.manage('on',revision,confirm)
        self.assertTrue(self.manage('on',0,True)['enabled'])
        with self.assertRaises(ValueError):
            self.manage('on',0,True)
        self.assertFalse(self.app.payment_service().config.enabled)
        self.assertFalse(self.app.payment_service().config.live_approved)
        self.assertTrue(self.app.host_fee_service().config.enabled)
        with self.app.connect() as conn:
            self.assertEqual(conn.execute("select count(*) from audit_logs where action='host_fee_campaign_change'").fetchone()[0],before+1)
            payload = json.loads(conn.execute("select payload from audit_logs where action='host_fee_campaign_change' order by rowid desc limit 1").fetchone()[0])
            self.assertEqual(payload['source'],'render_shell')
        self.assertFalse(self.manage('off',1)['enabled'])

    def test_first_publication_requires_new_consent_after_on_even_if_form_was_off(self):
        payload = event_payload(self.id(),capacity='')
        self.assertNotIn('id="hostFeeConsent"',self.app.render_event_form_html({},self.host))
        self.toggle(True)
        with self.app.connect() as conn,self.assertRaisesRegex(ValueError,'同意'):
            self.app.save_event_post(conn,payload,self.host)
        eid = self.paid_event()
        self.assertFalse(self.balance(eid)['fee_waived'])
        self.assertEqual(self.balance(eid)['charge_due'],500)
        self.toggle(False)
        self.assertEqual(self.balance(eid)['charge_due'],0)
        self.toggle(True)
        self.assertEqual(self.balance(eid)['charge_due'],500)

    def test_draft_uses_first_publication_policy_not_draft_creation(self):
        payload = event_payload(self.id(),capacity='')
        payload['status'] = 'draft'
        with self.app.connect() as conn:
            eid = self.app.save_event_post(conn,payload,self.host)
        self.toggle(True)
        payload.update(event_id=eid,status='published')
        with self.app.connect() as conn,self.assertRaisesRegex(ValueError,'同意'):
            self.app.save_event_post(conn,payload,self.host)
        payload.update(host_fee_accepted=True,host_fee_policy_version=self.app.host_fees.POLICY_VERSION)
        with self.app.connect() as conn:
            self.app.save_event_post(conn,payload,self.host)
            self.assertFalse(self.app.fee_campaign.terms(conn,eid)['waived'])
            self.assertTrue(self.app.host_billing.agreement(conn,eid)['accepted_at'])

    def test_existing_event_with_even_prior_consent_is_permanently_exempt(self):
        self.toggle(True)
        eid = self.paid_event()
        with self.app.connect() as conn:
            conn.execute('delete from app_state where state_key=?',(self.app.fee_campaign.EVENT_PREFIX+eid,))
        self.assertTrue(self.balance(eid)['fee_waived'])
        self.assertEqual(self.balance(eid)['fee_total'],0)
        with self.assertRaises(ValueError):
            self.checkout(eid)
        self.toggle(False)
        self.toggle(True)
        self.assertTrue(self.balance(eid)['fee_waived'])

    def open_order(self):
        self.toggle(True)
        eid = self.paid_event()
        self.checkout(eid)
        with self.app.connect() as conn:
            order = dict(conn.execute('select * from host_fee_orders where event_id=?',(eid,)).fetchone())
        return eid,order

    def test_off_expires_link_and_blocks_old_quote_without_creating_invoice(self):
        eid,order = self.open_order()
        quote = self.balance(eid)['quote_token']
        result = self.manage('off',1)
        self.assertFalse(result['stopping'])
        self.assertEqual(self.gateway.sessions[order['session_id']]['status'],'expired')
        with self.assertRaises(ValueError):
            self.checkout(eid,quote)
        with self.app.connect() as conn:
            self.assertEqual(conn.execute('select count(*) from host_fee_orders').fetchone()[0],1)

    def test_off_during_creation_never_returns_payable_url(self):
        self.toggle(True)
        eid = self.paid_event()
        create = self.gateway.create_session
        def race(params,key):
            session = create(params,key)
            self.toggle(False)
            return session
        self.gateway.create_session = race
        with self.assertRaises(ValueError):
            self.checkout(eid)
        self.assertEqual(next(iter(self.gateway.sessions.values()))['status'],'expired')
        self.app.host_fee_service().stop_open_checkouts()
        with self.app.connect() as conn:
            self.assertFalse(self.app.fee_campaign.status(conn)['stopping'])

    def test_unknown_create_recovers_only_same_key_then_expires(self):
        self.toggle(True)
        eid = self.paid_event()
        create = self.gateway.create_session
        def lost(params,key):
            create(params,key)
            raise TimeoutError('synthetic response loss')
        self.gateway.create_session = lost
        with self.assertRaises(TimeoutError):
            self.checkout(eid)
        self.gateway.create_session = create
        self.toggle(False)
        self.app.host_fee_service().stop_open_checkouts()
        self.assertEqual(self.gateway.created,1)
        self.assertEqual(next(iter(self.gateway.sessions.values()))['status'],'expired')

    def test_off_during_final_platform_check_expires_before_returning_url(self):
        self.toggle(True)
        eid = self.paid_event()
        service = self.app.host_fee_service()
        original = service.payments.platform_check
        calls = []
        def racing(*args,**kwargs):
            result = original(*args,**kwargs)
            calls.append(kwargs.get('accepting_payments',False))
            if len(calls) == 3:
                self.toggle(False)
            return result
        service.payments.platform_check = racing
        with self.assertRaisesRegex(ValueError,'徴収設定'):
            service.checkout(eid,self.host['user_id'],dict(accepted=True,quote_token=self.balance(eid)['quote_token']))
        self.assertEqual(next(iter(self.gateway.sessions.values()))['status'],'expired')

    def test_unknown_old_attempt_holds_off_and_does_not_starve_other_links(self):
        eid,order = self.open_order()
        second = self.event('Second event ')
        self.apply(second)
        self.announce(second)
        with self.app.connect() as conn:
            conn.execute("update event_applications set payment_status='paid' where event_id=?",(second,))
        self.checkout(second)
        with self.app.connect() as conn:
            conn.execute("update host_fee_orders set session_id=null,state='creating',created_epoch=0 where order_id=?",(order['order_id'],))
        self.toggle(False)
        service = self.app.host_fee_service()
        service.stop_open_checkouts(limit=1)
        service.stop_open_checkouts(limit=1)
        with self.app.connect() as conn:
            current = self.app.fee_campaign.status(conn)
            self.assertTrue(current['stopping'])
            other = conn.execute('select session_id,state from host_fee_orders where event_id=?',(second,)).fetchone()
            self.assertEqual(other['state'],'expired')
        with self.assertRaisesRegex(ValueError,'照合待ち'):
            self.toggle(True)
        self.assertEqual(self.gateway.created,2)

    def test_provider_failure_remains_visibly_stopping_and_retryable(self):
        _,order = self.open_order()
        self.toggle(False)
        expire = self.gateway.expire
        with patch.object(self.gateway,'expire',side_effect=TimeoutError('synthetic')):
            self.app.host_fee_service().stop_open_checkouts()
        with self.app.connect() as conn:
            self.assertTrue(self.app.fee_campaign.status(conn)['stopping'])
            conn.execute('update host_fee_orders set next_sync_at=0')
        self.gateway.expire = expire
        self.app.host_fee_service().stop_open_checkouts()
        self.assertEqual(self.gateway.sessions[order['session_id']]['status'],'expired')

    def test_paid_race_and_duplicate_webhooks_reconcile_while_off(self):
        eid,order = self.open_order()
        self.gateway.paid(order['session_id'])
        self.toggle(False)
        self.app.host_fee_service().stop_open_checkouts()
        self.assertEqual(self.balance(eid)['fee_paid'],500)
        body = json.dumps(dict(id='evt_campaign_off',type='checkout.session.completed',livemode=False,
            data={'object':dict(id=order['session_id'],object='checkout.session')})).encode()
        payments = self.app.payment_service()
        for _ in range(2):
            payments.receive_webhook(body,'signed')
            payments.webhook_job()
        with self.app.connect() as conn:
            self.assertEqual(conn.execute('select count(*) from payment_webhooks').fetchone()[0],1)
            self.assertEqual(conn.execute("select count(*) from event_notifications where event_id=? and notification_type='host_fee_paid'",(eid,)).fetchone()[0],1)

    def test_signature_verification_does_not_require_live_creation_approval(self):
        config = replace(self.app.payment_service().config,mode='live',key='rk_live_synthetic',live_approved=False)
        service = self.app.online_payments.Payments(self.app.connect,self.app.add_event_notification,config)
        body = json.dumps(dict(id='evt_campaign_live_signature',type='checkout.session.expired',livemode=True,
            data={'object':dict(id='cs_live_synthetic',object='checkout.session')})).encode()
        timestamp = str(int(time.time()))
        signature = 't='+timestamp+',v1='+hmac.new(config.webhook_secret.encode(),timestamp.encode()+b'.'+body,hashlib.sha256).hexdigest()
        with patch.object(self.app.online_payments,'StripeGateway',side_effect=AssertionError('must not create gateway')):
            self.assertTrue(service.receive_webhook(body,signature)['received'])
        self.assertIsNone(service._gateway)

    def test_private_disclosure_and_corrupt_policy_fail_closed(self):
        eid = self.event()
        owner = self.app.render_host_fee_html(eid,self.host)
        self.assertIn('利用料0円・免除',owner)
        self.assertNotIn('Stripeの利用料支払確認へ',owner)
        for page in [self.app.render_event_detail_html(eid,self.guest),self.app.render_event_apply_html(eid,self.guest)]:
            self.assertNotIn('data-host-fee-private',page)
        self.toggle(True)
        with self.app.connect() as conn:
            conn.execute('update app_state set state_value=? where state_key=?',('[]',self.app.fee_campaign.EVENT_PREFIX+eid))
        self.assertTrue(self.balance(eid)['fee_waived'])

    def test_publication_and_toggle_are_serialized(self):
        started,finished = threading.Event(),threading.Event()
        failures = []
        def enable():
            started.set()
            try:
                self.toggle(True)
            except Exception as error:
                failures.append(error)
            finally:
                finished.set()
        with self.app.connect() as conn:
            conn.execute('begin immediate')
            thread = threading.Thread(target=enable)
            thread.start()
            self.assertTrue(started.wait(2))
            eid = self.app.save_event_post(conn,event_payload(self.id(),capacity=''),self.host)
            self.assertFalse(finished.is_set())
        thread.join(10)
        self.assertFalse(thread.is_alive())
        self.assertEqual(failures,[])
        self.assertTrue(self.balance(eid)['campaign_enabled'])
        self.assertTrue(self.balance(eid)['fee_waived'])


if __name__ == '__main__':
    unittest.main()
