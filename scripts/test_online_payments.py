"""Isolated SQLite and fake Stripe; no external charges, users, or emails."""

import copy
import hashlib
import hmac
import json
import re
import sqlite3
import tempfile
import threading
import time
import unittest
import urllib.error
import urllib.request
from contextlib import closing, contextmanager
from dataclasses import replace
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest.mock import patch

from test_event_flow import load_app, create_account, event_payload, user


class FakeStripe:
    """Script-only provider simulator, with idempotency and injectable failures."""
    def __init__(self):
        self.sessions, self.keys, self.charges, self.refunds, self.accounts = {}, {}, {}, {}, {}
        self.create_calls = self.refund_calls = self.account_calls = 0
        self.timeout_create = self.timeout_refund = self.pay_on_expire = False
        self.refund_failure = False
        self.on_create = None
        self.platform_id = "acct_platform"
        self.charges_enabled = self.payouts_enabled = True

    def platform(self):
        return {"id":self.platform_id,"country":"JP","default_currency":"jpy",
                "charges_enabled":self.charges_enabled,"payouts_enabled":self.payouts_enabled}

    def create_account(self,key):
        self.account_calls += 1
        aid = "acct_"+hashlib.sha256(key.encode()).hexdigest()[:16]
        self.accounts.setdefault(aid,{"id":aid,"country":"JP","details_submitted":True,
            "charges_enabled":True,"payouts_enabled":True,"requirements":{},
            "capabilities":{"card_payments":"active","transfers":"active"},
            "controller":{"fees":{"payer":"application"},"losses":{"payments":"application"}},
            "metadata":{"circlematch_create_key":key}})
        return copy.deepcopy(self.accounts[aid])

    def account(self,aid):
        return copy.deepcopy(self.accounts[aid])

    def account_link(self,aid):
        return {"url":"https://connect.stripe.com/setup/mock/"+aid}

    def create_session(self,params,key):
        self.create_calls += 1
        if key not in self.keys:
            sid = "cs_test_"+str(len(self.sessions)+1)
            price = params["line_items"][0]
            self.keys[key] = sid
            self.sessions[sid] = {"id":sid,"mode":"payment","livemode":False,"currency":"jpy",
                "amount_total":price["price_data"]["unit_amount"]*price["quantity"],
                "client_reference_id":params["client_reference_id"],"payment_status":"unpaid",
                "status":"open","url":"https://checkout.stripe.com/c/pay/"+sid,
                "params":copy.deepcopy(params),"payment_intent":None}
        if self.on_create:
            self.on_create()
        if self.timeout_create:
            self.timeout_create = False
            raise TimeoutError("simulated lost response")
        return self.session(self.keys[key])

    def session(self,sid):
        return copy.deepcopy(self.sessions[sid])

    def pay(self,sid):
        s = self.sessions[sid]
        intent_id,charge_id = "pi_"+sid,"ch_"+sid
        payment = s["params"]["payment_intent_data"]
        fee,amount = payment["application_fee_amount"],s["amount_total"]
        self.charges[charge_id] = {"id":charge_id,"payment_intent":intent_id,"paid":True,"captured":True,
            "livemode":False,"amount":amount,"currency":"jpy","amount_refunded":0,"disputed":False,
            "balance_transaction":{"currency":"jpy","fee_details":[{"type":"stripe_fee","amount":72}]},
            "application_fee":{"amount":fee,"amount_refunded":0,"account":payment["transfer_data"]["destination"],"currency":"jpy"},
            "transfer":{"amount":amount,"amount_reversed":0,"destination":payment["transfer_data"]["destination"],"currency":"jpy"}}
        s.update(status="complete",payment_status="paid",payment_intent={"id":intent_id,
            "status":"succeeded","currency":"jpy","amount":amount,"amount_received":amount,
            "application_fee_amount":fee,"transfer_data":copy.deepcopy(payment["transfer_data"]),
            "on_behalf_of":None,"livemode":False,"latest_charge":copy.deepcopy(self.charges[charge_id])})

    def expire(self,sid):
        if self.pay_on_expire:
            self.pay(sid)
            raise ValueError("complete")
        if self.sessions[sid]["status"] != "open":
            raise ValueError("not open")
        self.sessions[sid]["status"] = "expired"
        return self.session(sid)

    def charge(self,cid):
        result=copy.deepcopy(self.charges[cid])
        result["refunds"]={"data":[copy.deepcopy(r) for r in self.refunds.values() if r["charge"]==cid],"has_more":False}
        return result

    def refund(self,cid,key):
        self.refund_calls += 1
        rid = "re_"+cid
        if rid not in self.refunds:
            c = self.charges[cid]
            self.refunds[rid] = {"id":rid,"charge":cid,"amount":c["amount"],"currency":"jpy","status":"failed" if self.refund_failure else "succeeded"}
            c["transfer"]["amount_reversed"] = c["amount"]
            c["application_fee"]["amount_refunded"] = c["application_fee"]["amount"]
            if not self.refund_failure:
                c["amount_refunded"] = c["amount"]
        if self.timeout_refund:
            self.timeout_refund=False
            raise TimeoutError("simulated refund response loss")
        return self.refund_status(rid)

    def refund_status(self,rid):
        return copy.deepcopy(self.refunds[rid])

    def dispute(self,did):
        return {"id":did,"status":"needs_response"}

    def payout(self,pid,aid):
        return {"id":pid,"status":"failed","livemode":False}

    def verify(self,body,signature,connected=False):
        parts = dict(v.split("=",1) for v in signature.split(","))
        expected = hmac.new(b"whsec_local_mock",parts["t"].encode()+b"."+body,hashlib.sha256).hexdigest()
        if not hmac.compare_digest(expected,parts["v1"]) or abs(int(time.time())-int(parts["t"]))>300:
            raise ValueError("bad signature")
        return json.loads(body)


class PaymentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = tempfile.TemporaryDirectory()
        cls.base = Path(cls.root.name)/"base.sqlite"
        cls.app = load_app(cls.base)
        cls.app.init_db()
        cls.app.EMAIL_NOTIFICATIONS_ENABLED = False
        cls.host=user("host","host@example.test","テスト主催者")
        cls.person=user("person","person@example.test","参加者")
        cls.other=user("other","other@example.test","別の参加者")
        for u in (cls.host,cls.person,cls.other):
            create_account(cls.app,u)

    @classmethod
    def tearDownClass(cls):
        cls.root.cleanup()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.path = Path(self.temp.name)/"payment.sqlite"
        with closing(sqlite3.connect(self.base)) as src,closing(sqlite3.connect(self.path)) as dst:
            src.backup(dst)
        self.app.DB_PATH=self.path
        self.mod=self.app.online_payments
        self.config=self.mod.Config(True,"test","sk_test_local_mock","whsec_local_mock","acct_platform","http://127.0.0.1:8896",connect_webhook_secret="whsec_connect_mock")
        self.gateway=FakeStripe()
        self.service=self.mod.Payments(self.app.connect,self.app.add_event_notification,self.config,self.gateway)
        self.app._payments=self.service
        self.service.onboard("host")

    def tearDown(self):
        self.app._payments=None
        self.temp.cleanup()

    def save(self,**kwargs):
        p=event_payload("ローカル決済テスト "+str(time.time_ns()),capacity="20")
        p.update(payment_method="online",online_pricing_mode="net",online_price_input=1800,fee_amount=999)
        p.update(kwargs)
        with self.app.connect() as conn:
            return self.app.save_event_post(conn,p,self.host)

    def apply(self,eid,count=1,person=None,mode=None):
        person=person or self.person
        event=self.app.get_event(eid)
        with self.app.connect() as conn:
            return self.app.submit_event_application(conn,eid,{"participation_type":mode or event["participation_type"],"applicant_name":"参加者","team_name":"テストチーム","representative_name":"代表者","participant_count":count},person)["application_id"]

    def quote_data(self,aid):
        with self.app.connect() as conn:
            app,event=self.service.load_application(conn,aid)
            amounts,_=self.service.payable(conn,app,event)
        return {"accepted":True,"quote_token":self.service.quote_token(self.service.snapshot(app,event,amounts))}

    def checkout(self,aid,person="person"):
        self.service.checkout(aid,person,self.quote_data(aid))
        with self.app.connect() as conn:
            return dict(conn.execute("select * from payment_orders where application_id=? and active=1",(aid,)).fetchone())

    def paid(self,**event_kwargs):
        eid=self.save(**event_kwargs)
        aid=self.apply(eid)
        order=self.checkout(aid)
        self.gateway.pay(order["session_id"])
        self.service.reconcile(order["order_id"])
        return eid,aid,self.service.order(order["order_id"],admin=True)

    def webhook(self,kind,obj,event_id="evt_test",connected=False,**extra):
        body=json.dumps({"id":event_id,"type":kind,"livemode":False,"data":{"object":obj},**extra}).encode()
        t=str(int(time.time()))
        sig="t="+t+",v1="+hmac.new(b"whsec_local_mock",t.encode()+b"."+body,hashlib.sha256).hexdigest()
        return self.service.receive_webhook(body,sig,connected=connected)

    def test_integer_amounts_rounding_and_team(self):
        q=self.mod.quote_price
        self.assertEqual(q(2000),dict(unit_amount=2000,quantity=1,gross=2000,fee=200,net=1800))
        self.assertEqual(q(1800,"net")["gross"],2000)
        self.assertEqual(q(2000,"net"),dict(unit_amount=2223,quantity=1,gross=2223,fee=223,net=2000))
        self.assertEqual(q(2000,quantity=3)["net"],5400)
        self.assertEqual(q(2223,quantity=3)["fee"],667)
        self.assertNotEqual(q(2223,quantity=3)["fee"],q(2223)["fee"]*3)
        self.assertEqual(q(0)["fee"],0)
        for v in (-1,1.2,"1.0",True,"-0",49,100_000_000,"nan"):
            with self.subTest(v=v),self.assertRaises(ValueError):q(v)
        self.assertEqual(q(50)["gross"],50)
        self.assertEqual(q(99_999_999)["gross"],99_999_999)
        with self.assertRaises(ValueError):q(99_999_999,quantity=2)
        eid=self.save(participation_type="team",capacity="2")
        order=self.checkout(self.apply(eid,12))
        self.assertEqual((order["quantity"],order["gross"]),(1,2000))

    def test_group_charge_and_manual_status_is_separate(self):
        eid=self.save();aid=self.apply(eid,3);o=self.checkout(aid)
        self.assertEqual((o["gross"],o["fee"],o["net"]),(6000,600,5400))
        self.gateway.pay(o["session_id"]);self.service.reconcile(o["order_id"])
        with self.app.connect() as conn:
            self.assertEqual(conn.execute("select payment_status from event_applications where application_id=?",(aid,)).fetchone()[0],"unpaid")
        with self.app.connect() as conn,self.assertRaises(ValueError):
            self.app.set_application_payment(conn,eid,aid,{"revision":0,"payment_status":"paid"},self.host)
        self.assertEqual(self.service.order(o["order_id"],admin=True)["processor_fee"],72)

    def test_amount_tampering_and_stale_quote(self):
        eid=self.save();aid=self.apply(eid);data=self.quote_data(aid)
        for key in ("gross","fee","destination","amount"):
            with self.subTest(key=key),self.assertRaises(ValueError):self.service.checkout(aid,"person",{**data,key:1})
        with self.app.connect() as conn:
            self.app.change_application_count(conn,eid,aid,{"revision":0,"participant_count":2},self.person)
        with self.assertRaises(ValueError):self.service.checkout(aid,"person",data)
        self.assertEqual(self.gateway.create_calls,0)

    def test_duplicate_tabs_and_timeout_use_one_session(self):
        eid=self.save();aid=self.apply(eid);data=self.quote_data(aid)
        self.gateway.timeout_create=True
        with self.assertRaises(TimeoutError):self.service.checkout(aid,"person",data)
        self.service.checkout(aid,"person",data)
        self.service.checkout(aid,"person",data)
        self.assertEqual(len(self.gateway.sessions),1)
        with self.app.connect() as conn:
            self.assertEqual(conn.execute("select count(*) from payment_orders").fetchone()[0],1)

    def test_simultaneous_checkout_does_not_hold_database_lock(self):
        eid=self.save();aid=self.apply(eid);data=self.quote_data(aid)
        entered,release=threading.Event(),threading.Event()
        def network_wait():
            with self.app.connect() as conn:
                conn.execute("begin immediate")
                conn.execute("insert into payment_audit(actor,action,detail,created_at) values('test','network_probe','','now')")
            entered.set();release.wait(3)
        self.gateway.on_create=network_wait
        errors=[]
        def run():
            try:self.service.checkout(aid,"person",data)
            except Exception as e:errors.append(e)
        first=threading.Thread(target=run);first.start();self.assertTrue(entered.wait(4))
        run();release.set();first.join()
        self.assertEqual(len(errors),1)
        self.assertEqual(len(self.gateway.sessions),1)

    def test_approval_and_formation_gate(self):
        eid=self.save(acceptance_mode="approval",minimum_participants=1);aid=self.apply(eid)
        with self.assertRaises(ValueError):self.quote_data(aid)
        with self.app.connect() as conn:self.app.set_event_application_status(conn,eid,aid,"confirm",self.host)
        with self.assertRaises(ValueError):self.quote_data(aid)
        with self.app.connect() as conn:
            self.app.announce_event(conn,eid,{"version":0,"starts_at":"2030-06-01T10:00","location":"会場","announcement_details":"集合案内","attendance_deadline":"2030-05-29T18:00","payment_deadline":"2030-05-30T18:00"},self.host)
        with self.assertRaises(ValueError):self.quote_data(aid)
        with self.app.connect() as conn:self.app.confirm_event_attendance(conn,eid,{"version":1},self.person)
        o=self.checkout(aid);self.gateway.pay(o["session_id"]);self.service.reconcile(o["order_id"])
        with self.app.connect() as conn:
            self.app.announce_event(conn,eid,{"version":1,"starts_at":"2030-06-01T10:00","location":"別の会場","announcement_details":"案内更新","attendance_deadline":"2030-05-29T18:00","payment_deadline":"2030-05-30T18:00"},self.host)
        result=self.service.checkout(aid,"person",{"accepted":True,"quote_token":"unused"})
        self.assertIn(o["order_id"],result["url"])
        self.assertEqual(len(self.gateway.sessions),1)

    def test_active_checkout_blocks_changes_and_cancel_until_expired(self):
        eid=self.save();aid=self.apply(eid);o=self.checkout(aid)
        for op in (lambda c:self.app.change_application_count(c,eid,aid,{"revision":0,"participant_count":2},self.person),
                   lambda c:self.app.cancel_event_application(c,eid,aid,self.person),
                   lambda c:self.app.set_event_status(c,eid,"cancelled",self.host)):
            with self.app.connect() as conn,self.assertRaises(ValueError):op(conn)
        self.service.reconcile(o["order_id"],"person",expire=True)
        with self.app.connect() as conn:self.app.change_application_count(conn,eid,aid,{"revision":0,"participant_count":2},self.person)
        new=self.checkout(aid)
        self.assertNotEqual(new["order_id"],o["order_id"])
        self.assertEqual(new["gross"],4000)

    def test_expire_success_race_keeps_payment_and_refund_request(self):
        eid=self.save();aid=self.apply(eid);o=self.checkout(aid)
        self.gateway.pay_on_expire=True
        result=self.service.reconcile(o["order_id"],"person",expire=True)
        self.assertEqual(result["state"],"paid")
        with self.app.connect() as conn:self.app.cancel_event_application(conn,eid,aid,self.person)
        self.assertEqual(self.service.order(o["order_id"],admin=True)["refund_state"],"requested")
        with self.app.connect() as conn,self.assertRaises(ValueError):self.app.submit_event_application(conn,eid,{"participation_type":"individual","applicant_name":"再申込","participant_count":1},self.person)

    def test_expire_failure_keeps_reservation(self):
        eid=self.save(capacity="1");aid=self.apply(eid);o=self.checkout(aid)
        with patch.object(self.gateway,"expire",side_effect=TimeoutError),self.assertRaises(ValueError):
            self.service.reconcile(o["order_id"],"person",expire=True)
        with self.app.connect() as conn:self.assertEqual(self.app.active_confirmed_capacity(conn,eid),1)
        with self.assertRaises(ValueError):self.apply(eid,person=self.other)

    def test_webhooks_without_browser_duplicates_and_reverse_order(self):
        eid=self.save();aid=self.apply(eid);o=self.checkout(aid);self.gateway.pay(o["session_id"])
        for kind,event_id in (("checkout.session.expired","evt_expired"),("checkout.session.completed","evt_paid"),("checkout.session.completed","evt_paid")):
            self.webhook(kind,{"id":o["session_id"]},event_id);self.service.webhook_job()
        self.webhook("payment_intent.succeeded",{"id":"pi_"+o["session_id"]},"evt_intent");self.service.webhook_job()
        self.assertEqual(self.service.order(o["order_id"],admin=True)["state"],"paid")
        with self.app.connect() as conn:
            self.assertEqual(conn.execute("select count(*) from payment_audit where action='paid_verified'").fetchone()[0],1)
            self.assertEqual(conn.execute("select count(*) from event_notifications where notification_type='online_payment'").fetchone()[0],2)

    def test_invalid_signature_and_mode_and_connected_charge(self):
        with self.assertRaises(ValueError):self.service.receive_webhook(b'{}',"t=1,v1=bad")
        with self.assertRaises(ValueError):self.webhook("checkout.session.completed",{"id":"cs_invalid"},livemode=True)
        with self.assertRaises(ValueError):self.webhook("checkout.session.completed",{"id":"cs_invalid"},account="acct_evil")
        with self.app.connect() as conn:self.assertEqual(conn.execute("select count(*) from payment_webhooks").fetchone()[0],0)

    def test_webhook_storage_failure_is_not_success(self):
        with patch.object(self.service,"connect",side_effect=sqlite3.OperationalError("test")),self.assertRaises(sqlite3.OperationalError):
            self.webhook("checkout.session.completed",{"id":"cs_test"})

    def test_paid_db_failure_recovered_by_same_session(self):
        eid=self.save();aid=self.apply(eid);o=self.checkout(aid);self.gateway.pay(o["session_id"])
        original=self.service.audit
        def broken(conn,oid,action,*a,**kw):
            if action=="paid_verified":raise sqlite3.OperationalError("test commit failure")
            return original(conn,oid,action,*a,**kw)
        with patch.object(self.service,"audit",side_effect=broken),self.assertRaises(sqlite3.OperationalError):self.service.reconcile(o["order_id"])
        self.assertIsNone(self.service.order(o["order_id"],admin=True)["paid_at"])
        self.service.reconcile(o["order_id"])
        self.assertEqual(self.service.order(o["order_id"],admin=True)["state"],"paid")

    def test_mismatch_not_paid_or_credited(self):
        eid=self.save();aid=self.apply(eid);o=self.checkout(aid);self.gateway.pay(o["session_id"])
        s=self.gateway.sessions[o["session_id"]]
        for field,bad in (("amount_total",1),("currency","usd"),("livemode",True)):
            previous=s[field];s[field]=bad
            with self.subTest(field=field),self.assertRaises(ValueError):self.service.reconcile(o["order_id"])
            s[field]=previous
        for field,bad in (("application_fee_amount",1),("transfer_data",{"destination":"acct_evil"}),("on_behalf_of","acct_other")):
            previous=s["payment_intent"][field];s["payment_intent"][field]=bad
            with self.subTest(field=field),self.assertRaises(ValueError):self.service.reconcile(o["order_id"])
            s["payment_intent"][field]=previous
        self.assertIsNone(self.service.order(o["order_id"],admin=True)["paid_at"])

    def test_full_refund_with_fee_and_transfer_reversal(self):
        _,_,o=self.paid()
        self.service.request_refund(o["order_id"],"person","参加できない")
        self.assertFalse(self.service.refund_job())
        self.service.request_refund(o["order_id"],"host","条件を確認",True)
        self.assertTrue(self.service.refund_job())
        actual=self.service.order(o["order_id"],admin=True)
        self.assertEqual((actual["refund_state"],actual["refund_amount"],actual["fee_refunded"],actual["transfer_reversed"]),("succeeded",2000,200,2000))
        self.service.request_refund(o["order_id"],"host","再度",True)
        self.assertFalse(self.service.refund_job())
        self.assertEqual(self.gateway.refund_calls,1)

    def test_refund_timeout_and_restart(self):
        _,_,o=self.paid();self.gateway.timeout_refund=True
        self.service.request_refund(o["order_id"],"host","中止",True);self.service.refund_job()
        with self.app.connect() as conn:conn.execute("update payment_refunds set next_attempt_at=0,lease_until=0")
        restarted=self.mod.Payments(self.app.connect,self.app.add_event_notification,self.config,self.gateway)
        restarted.refund_job()
        self.assertEqual(restarted.order(o["order_id"],admin=True)["refund_state"],"succeeded")
        self.assertEqual(len(self.gateway.refunds),1)

    def test_failed_refund_records_reversals_not_success(self):
        _,_,o=self.paid();self.gateway.refund_failure=True
        self.service.request_refund(o["order_id"],"host","中止",True);self.service.refund_job()
        result=self.service.order(o["order_id"],admin=True)
        self.assertEqual((result["refund_state"],result["refund_amount"],result["transfer_reversed"]),("failed",0,2000))

    def test_external_partial_refund_and_dispute_are_not_full_refund(self):
        _,_,o=self.paid();c=self.gateway.charges[o["charge_id"]]
        c["amount_refunded"]=100
        self.gateway.refunds["re_partial"]={"id":"re_partial","charge":o["charge_id"],"amount":100,"currency":"jpy","status":"succeeded"}
        self.service.reconcile(o["order_id"])
        self.assertEqual(self.service.order(o["order_id"],admin=True)["refund_state"],"partial")
        with self.assertRaises(ValueError):self.service.request_refund(o["order_id"],"host","全額",True)
        c["disputed"]=True
        self.service.reconcile(o["order_id"])
        self.assertEqual(self.service.order(o["order_id"],admin=True)["dispute_state"],"open")
        self.assertEqual(self.gateway.refund_calls,0)

    def test_pending_refund_totals_do_not_mean_succeeded(self):
        _,_,o=self.paid()
        self.service.request_refund(o["order_id"],"host","中止",True)
        refund=self.gateway.refund(o["charge_id"],"external-result")
        self.gateway.refunds[refund["id"]]["status"]="pending"
        with self.app.connect() as conn:
            conn.execute("update payment_refunds set stripe_refund_id=?",(refund["id"],))
        self.service.refund_job()
        result=self.service.order(o["order_id"],admin=True)
        self.assertEqual((result["refund_state"],result["refund_amount"]),("processing",0))
        with self.app.connect() as conn:
            self.assertFalse(conn.execute("select 1 from payment_audit where action='refund_succeeded'").fetchone())
        self.gateway.refunds[refund["id"]]["status"]="succeeded"
        self.service.reconcile(o["order_id"])
        self.assertEqual(self.service.order(o["order_id"],admin=True)["refund_state"],"succeeded")
        self.assertEqual(self.gateway.refund_calls,1)

    def test_incomplete_or_requires_action_refund_is_review(self):
        _,_,o=self.paid()
        refund=self.gateway.refund(o["charge_id"],"external-result")
        self.gateway.refunds[refund["id"]]["status"]="requires_action"
        self.service.reconcile(o["order_id"])
        self.assertEqual(self.service.order(o["order_id"],admin=True)["refund_state"],"review")
        self.gateway.refunds[refund["id"]]["status"]="succeeded"
        charge=self.gateway.charge(o["charge_id"]);charge["refunds"]["has_more"]=True
        with patch.object(self.gateway,"charge",return_value=charge):
            self.service.reconcile(o["order_id"])
        self.assertNotEqual(self.service.order(o["order_id"],admin=True)["refund_state"],"succeeded")

    def test_event_cancel_previews_and_queues_not_sync_refund(self):
        eid,_,o=self.paid();preview=self.service.cancellation_preview(eid,"host")
        self.assertEqual((preview["count"],preview["gross"]),(1,2000))
        with self.app.connect() as conn,self.assertRaises(ValueError):self.app.set_event_status(conn,eid,"cancelled",self.host)
        with self.app.connect() as conn:self.app.set_event_status(conn,eid,"cancelled",self.host,preview["token"])
        self.assertEqual(self.gateway.refund_calls,0)
        self.assertEqual(self.service.order(o["order_id"],admin=True)["refund_state"],"processing")
        self.service.refund_job();self.assertEqual(self.gateway.refund_calls,1)

    def test_flag_off_stops_new_but_keeps_reconcile_refund_webhooks(self):
        eid=self.save();aid=self.apply(eid);o=self.checkout(aid);self.gateway.pay(o["session_id"])
        self.service.config=replace(self.config,enabled=False)
        with self.assertRaises(ValueError):self.service.checkout(aid,"person",{"accepted":True})
        self.webhook("checkout.session.completed",{"id":o["session_id"]});self.service.webhook_job()
        self.service.request_refund(o["order_id"],"host","中止",True);self.service.refund_job()
        self.assertEqual(self.service.order(o["order_id"],admin=True)["refund_state"],"succeeded")

    def test_connect_restricted_and_ownership(self):
        eid=self.save();aid=self.apply(eid);data=self.quote_data(aid)
        account=self.service.account_row("host");self.gateway.accounts[account["account_id"]]["requirements"]={"disabled_reason":"requirements.past_due"}
        with self.assertRaises(ValueError):self.service.checkout(aid,"person",data)
        self.gateway.accounts[account["account_id"]]["requirements"]={}
        o=self.checkout(aid)
        for op in (lambda:self.service.order(o["order_id"],"other"),lambda:self.service.checkout(aid,"other",data),lambda:self.service.request_refund(o["order_id"],"other","理由",True)):
            with self.assertRaises(PermissionError):op()
        with self.assertRaises(PermissionError):self.service.resume_checkout(o["order_id"],"host")

    def test_snapshot_immutable_and_no_order_recipient_rewrite(self):
        eid=self.save();aid=self.apply(eid);o=self.checkout(aid)
        with self.app.connect() as conn,self.assertRaises(sqlite3.IntegrityError):conn.execute("update payment_orders set destination='acct_other'")
        with self.app.connect() as conn:conn.execute("update event_posts set organizer_user_id='other' where event_id=?",(eid,))
        self.assertEqual(self.service.order(o["order_id"],admin=True)["organizer_id"],"host")

    def test_minimum_checkout_window_and_expired_payment(self):
        eid=self.save();aid=self.apply(eid)
        with self.app.connect() as conn:conn.execute("update event_posts set payment_deadline=datetime('now','+9 hours','+15 minutes') where event_id=?",(eid,))
        with self.assertRaises(ValueError):self.checkout(aid)
        with self.app.connect() as conn:conn.execute("update event_posts set payment_deadline='2020-01-01 00:00' where event_id=?",(eid,))
        with self.assertRaises(ValueError):self.quote_data(aid)
        self.assertEqual(self.gateway.create_calls,0)

    def test_zero_and_legacy_events_stay_unchanged(self):
        for method,fee in (("free",0),("on_site",1234),("bank_transfer",5678)):
            eid=self.save(payment_method=method,fee_amount=fee)
            self.apply(eid)
            event=self.app.get_event(eid)
            self.assertEqual((event["payment_method"],event["fee_amount"]),(method,fee))
        eid=self.save(online_price_input=0)
        self.assertEqual(self.app.get_event(eid)["payment_method"],"free")

    def test_dual_prices_checkout_correct_quantity_and_refund(self):
        eid=self.save(participation_type='both',individual_fee_amount=2500,team_fee_amount=15000,online_pricing_mode='gross')
        individual=self.apply(eid,count=2,mode='individual')
        team=self.apply(eid,count=11,person=self.other,mode='team')
        person_order=self.checkout(individual)
        team_order=self.checkout(team,'other')
        self.assertEqual((person_order['quantity'],person_order['gross']),(2,5000))
        self.assertEqual((team_order['quantity'],team_order['gross']),(1,15000))
        self.assertEqual(json.loads(team_order['snapshot_json'])['fee_unit'],'1チーム')
        self.gateway.pay(team_order['session_id'])
        self.service.reconcile(team_order['order_id'])
        with self.app.connect() as conn:
            self.mod.guard_mutation(conn,application_id=team,financial=False)
        with self.assertRaises(ValueError),self.app.connect() as conn:
            self.mod.guard_mutation(conn,application_id=team,financial=True)
        self.service.request_refund(team_order['order_id'],'other','test')
        self.service.request_refund(team_order['order_id'],'host','test',True)
        self.service.refund_job()
        result=self.service.order(team_order['order_id'],admin=True)
        self.assertEqual((result['refund_state'],result['refund_amount']),('succeeded',15000))

    def test_dual_net_prices_keep_source_inputs(self):
        eid=self.save(participation_type='both',individual_fee_amount=2500,team_fee_amount=15000)
        event=self.app.get_event(eid)
        self.assertEqual((event['individual_fee_amount'],event['team_fee_amount']),(2778,16667))
        person=self.apply(eid,count=2,mode='individual')
        team=self.apply(eid,count=11,person=self.other,mode='team')
        self.assertEqual(self.checkout(person)['gross'],5556)
        self.assertEqual(self.checkout(team,'other')['gross'],16667)

    def test_dual_online_edit_without_prices_does_not_reprice(self):
        eid=self.save(participation_type='both',individual_fee_amount=2500,team_fee_amount=15000)
        data=event_payload('Title edit',participation_type='both',capacity='20')
        data.update(event_id=eid,payment_method='online')
        with self.app.connect() as conn:
            self.app.save_event_post(conn,data,self.host)
        event=self.app.get_event(eid)
        self.assertEqual((event['individual_fee_amount'],event['team_fee_amount']),(2778,16667))

    def test_dual_free_individual_has_no_checkout_or_payment_button(self):
        eid=self.save(participation_type='both',individual_fee_amount=0,team_fee_amount=15000,online_pricing_mode='gross')
        aid=self.apply(eid,mode='individual')
        result=self.service.checkout(aid,'person',self.quote_data(aid))
        self.assertTrue(result['free'])
        self.assertEqual(self.gateway.create_calls,0)
        self.assertNotIn('/payments/applications/'+aid,self.app.render_mypage_html(self.person))

    def test_dual_payment_blocked_preview_keeps_application_tariff(self):
        eid=self.save(participation_type='both',individual_fee_amount=2500,team_fee_amount=15000,online_pricing_mode='gross',minimum_participants=1)
        aid=self.apply(eid,count=11,mode='team')
        page=self.app.payment_ui.render(self.service,'applications',aid,self.person,self.app.event_page,'test')
        self.assertIn('15,000',page)
        self.assertNotIn('165,000',page)
        self.assertEqual(self.gateway.create_calls,0)

    def test_no_sdk_configuration_does_not_fake_success(self):
        config=self.mod.Config(enabled=True)
        with self.assertRaises(ValueError):self.mod.StripeGateway(config)
        with self.assertRaises(ValueError):replace(self.config,mode="live",key="sk_live_notreal").validate()

    def test_missing_webhook_keys_block_checkout_before_creating_order(self):
        eid=self.save();aid=self.apply(eid);data=self.quote_data(aid)
        for changes in ({"webhook_secret":""},{"connect_webhook_secret":""},
                        {"connect_webhook_secret":self.config.webhook_secret}):
            self.service.config=replace(self.config,**changes)
            with self.assertRaises(self.mod.Unavailable):self.service.checkout(aid,"person",data)
        self.assertEqual(self.gateway.create_calls,0)
        with self.app.connect() as conn:
            self.assertEqual(conn.execute("select count(*) from payment_orders").fetchone()[0],0)

    def test_platform_payment_pause_blocks_new_but_not_reconciliation_or_refund(self):
        eid,aid,order=self.paid()
        self.gateway.charges_enabled=False
        self.service.reconcile(order["order_id"])
        self.service.request_refund(order["order_id"],"host","中止",True)
        self.service.refund_job()
        self.assertEqual(self.service.order(order["order_id"],admin=True)["refund_state"],"succeeded")
        eid=self.save();aid=self.apply(eid);data=self.quote_data(aid)
        with self.assertRaisesRegex(self.mod.Unavailable,"停止中"):
            self.service.checkout(aid,"person",data)
        self.assertEqual(self.gateway.create_calls,1)

    def test_connection_status_is_read_only_and_never_returns_secrets_or_provider_errors(self):
        status=self.service.connection_status(check_stripe=True)
        self.assertTrue(status["stripe_checked"])
        self.assertTrue(all(c["ok"] for c in status["checks"]))
        self.gateway.charges_enabled=False
        status=self.service.connection_status(check_stripe=True)
        self.assertFalse(next(c["ok"] for c in status["checks"] if c["label"]=="Stripe決済受付"))
        with patch.object(self.gateway,"platform",side_effect=RuntimeError("secret="+self.config.key)):
            status=self.service.connection_status(check_stripe=True)
        self.assertFalse(all(c["ok"] for c in status["checks"]))
        self.assertNotIn(self.config.key,json.dumps(status))
        self.assertNotIn(self.config.webhook_secret,json.dumps(status))
        self.assertEqual((self.gateway.create_calls,self.gateway.refund_calls,self.gateway.account_calls),(0,0,1))

    def test_connection_url_and_live_approval_guard(self):
        for url in ("https://user:pass@example.test","https://example.test/?key=secret","http://example.test","https://example.test/path","https://[broken"):
            with self.assertRaises(self.mod.Unavailable):replace(self.config,base_url=url).validate_new_payments()
        live=replace(self.config,mode="live",key="sk_live_local_mock",base_url="https://circle-match.jp")
        with self.assertRaises(self.mod.Unavailable):live.validate_new_payments()
        replace(live,live_approved=True).validate_new_payments()
        unconfigured=self.mod.Payments(None,None,self.mod.Config())
        self.assertFalse(unconfigured.connection_status(check_stripe=True)["stripe_checked"])

    def test_no_expired_idempotency_key_is_reused_for_create(self):
        eid=self.save();aid=self.apply(eid);self.gateway.timeout_create=True
        with self.assertRaises(TimeoutError):self.checkout(aid)
        with self.app.connect() as conn:
            conn.execute("update payment_attempts set created_epoch=0")
            oid=conn.execute("select order_id from payment_orders").fetchone()[0]
        with self.assertRaises(ValueError):self.service.resume_checkout(oid,"person")
        self.assertEqual(self.gateway.create_calls,1)
        sid=next(iter(self.gateway.sessions))
        self.service.recover_order(oid,sid,"operator")
        self.assertEqual(self.service.order(oid,admin=True)["session_id"],sid)
        self.assertEqual(self.gateway.create_calls,1)

    def test_capacity_race_reserves_once(self):
        eid=self.save(capacity="1")
        barrier=threading.Barrier(2);results=[]
        def apply(person):
            barrier.wait()
            try:results.append(self.apply(eid,person=person))
            except ValueError:results.append(None)
        threads=[threading.Thread(target=apply,args=(u,)) for u in (self.person,self.other)]
        for thread in threads:thread.start()
        for thread in threads:thread.join()
        self.assertEqual(sum(x is not None for x in results),1)
        with self.app.connect() as conn:self.assertEqual(self.app.active_confirmed_capacity(conn,eid),1)

    def test_existing_session_restricted_account_is_expired(self):
        eid=self.save();aid=self.apply(eid);o=self.checkout(aid)
        account=self.service.account_row("host")
        self.gateway.accounts[account["account_id"]]["requirements"]={"disabled_reason":"requirements.past_due"}
        with self.assertRaises(ValueError):self.service.resume_checkout(o["order_id"],"person")
        self.assertEqual(self.gateway.sessions[o["session_id"]]["status"],"expired")

    def test_connected_account_hook_is_separate_and_expires_open_sessions(self):
        eid=self.save();aid=self.apply(eid);o=self.checkout(aid)
        account=self.service.account_row("host")
        self.service.config=replace(self.config,connect_webhook_secret="whsec_local_mock")
        self.gateway.accounts[account["account_id"]]["requirements"]={"disabled_reason":"requirements.past_due"}
        with self.assertRaises(ValueError):self.webhook("account.updated",{"id":account["account_id"]})
        self.webhook("account.updated",{"id":account["account_id"]},account=account["account_id"],connected=True)
        self.service.webhook_job()
        self.assertEqual(self.service.order(o["order_id"],admin=True)["state"],"expired")

    def test_paid_inactive_history_never_recharged_and_closed_dispute_preserved(self):
        _,aid,o=self.paid()
        with self.app.connect() as conn:
            conn.execute("update payment_orders set active=0,dispute_state='won' where order_id=?",(o["order_id"],))
        result=self.service.checkout(aid,"person",{"accepted":True,"quote_token":"unused"})
        self.assertIn(o["order_id"],result["url"])
        self.assertEqual(self.gateway.create_calls,1)
        self.gateway.charges[o["charge_id"]]["disputed"]=True
        self.service.sync_money(self.service.order(o["order_id"],admin=True))
        self.assertEqual(self.service.order(o["order_id"],admin=True)["dispute_state"],"won")

    def test_expired_processing_lease_cannot_mutate_state(self):
        eid=self.save();aid=self.apply(eid);o=self.checkout(aid)
        token=self.service.claim_order(o["order_id"])
        with self.app.connect() as conn:conn.execute("update payment_attempts set lease_token='new-worker'")
        self.gateway.expire(o["session_id"])
        with self.assertRaises(ValueError):self.service.apply_session(o,self.gateway.session(o["session_id"]),token)
        self.assertEqual(self.service.order(o["order_id"],admin=True)["active"],1)

    def test_external_failed_refund_is_detected(self):
        _,_,o=self.paid();self.gateway.refund_failure=True
        refund=self.gateway.refund(o["charge_id"],"external")
        self.webhook("refund.failed",refund)
        self.service.webhook_job()
        result=self.service.order(o["order_id"],admin=True)
        self.assertEqual((result["refund_state"],result["refund_amount"],result["transfer_reversed"]),("failed",0,2000))

    def test_bank_payout_failure_notifies_host_not_unpaid(self):
        _,_,o=self.paid()
        account=self.service.account_row("host")
        self.service.config=replace(self.config,connect_webhook_secret="whsec_local_mock")
        self.webhook("payout.failed",{"id":"po_bank_test"},account=account["account_id"],connected=True)
        self.service.webhook_job()
        result=self.service.order(o["order_id"],admin=True)
        self.assertEqual(result["state"],"paid")
        with self.app.connect() as conn:
            self.assertEqual(conn.execute("select count(*) from payment_audit where action='payout_failed'").fetchone()[0],1)
        self.service.replay_webhook("evt_test","operator");self.service.webhook_job()
        with self.app.connect() as conn:
            self.assertEqual(conn.execute("select count(*) from payment_audit where action='payout_failed'").fetchone()[0],1)

    def test_late_payment_after_cancellation_is_review_and_queued_refund(self):
        eid=self.save();aid=self.apply(eid);o=self.checkout(aid)
        # Simulate an out-of-band legacy/admin change, not an allowed application action.
        with self.app.connect() as conn:
            conn.execute("update event_posts set status='cancelled' where event_id=?",(eid,))
            conn.execute("update event_applications set status='cancelled' where application_id=?",(aid,))
        self.gateway.pay(o["session_id"])
        self.service.reconcile(o["order_id"])
        result=self.service.order(o["order_id"],admin=True)
        self.assertEqual((result["state"],result["refund_state"]),("review","processing"))
        self.service.refund_job()
        self.assertEqual(self.service.order(o["order_id"],admin=True)["refund_state"],"succeeded")

    def test_account_recovery_and_failed_migration_rollback(self):
        account=self.service.account_row("host")
        with self.app.connect() as conn:conn.execute("update payment_accounts set account_id=null,created_epoch=0 where user_id='host'")
        with self.assertRaises(ValueError):self.service.onboard("host")
        self.service.recover_account("host",account["account_id"],"operator")
        self.assertEqual(self.service.account_row("host")["state"],"ready")
        path=Path(self.temp.name)/"legacy.sqlite"
        with closing(sqlite3.connect(path)) as conn:
            conn.execute("create table event_posts(event_id text primary key,payment_method text check(payment_method in ('free','on_site','bank_transfer')))")
            conn.execute("insert into event_posts values('keep','bank_transfer')");conn.commit()
            with patch.object(self.mod,"SCHEMA",self.mod.SCHEMA+["not valid SQL"]),self.assertRaises(sqlite3.OperationalError):
                self.mod.migrate(conn,path)
            self.assertEqual(conn.execute("select * from event_posts").fetchall(),[("keep","bank_transfer")])
            self.assertFalse(conn.execute("select 1 from sqlite_master where name='payment_orders'").fetchone())
            self.assertNotIn("online_price_input",[r[1] for r in conn.execute("pragma table_info(event_posts)")])

    def test_operator_review_and_rate_limit(self):
        with patch.object(self.mod.time, "time", return_value=60_000):
            for _ in range(15):self.service.rate_limit("person")
            with self.assertRaises(ValueError):self.service.rate_limit("person")
            self.service.rate_limit("host")
        with patch.object(self.mod.time, "time", return_value=60_060):
            self.service.rate_limit("person")
        eid=self.save();aid=self.apply(eid);o=self.checkout(aid)
        self.gateway.sessions[o["session_id"]]["amount_total"]=1
        with self.assertRaises(ValueError):self.service.reconcile(o["order_id"])
        self.assertEqual(self.service.order(o["order_id"],admin=True)["state"],"review")
        with self.assertRaises(ValueError):self.service.resume_checkout(o["order_id"],"person")

    def test_schema_migration_idempotent_and_backup_integrity(self):
        eid=self.save(payment_method="on_site");aid=self.apply(eid)
        with self.app.connect() as conn:
            before=[tuple(r) for r in conn.execute("select * from event_applications")]
            self.mod.migrate(conn,self.path);self.mod.migrate(conn,self.path)
            self.assertEqual(before,[tuple(r) for r in conn.execute("select * from event_applications")])
            self.assertEqual(conn.execute("pragma foreign_key_check").fetchall(),[])
        backups=list(Path(self.root.name).glob('*.pre-online-payments-*.sqlite'))
        self.assertTrue(backups)
        for path in backups:
            with closing(sqlite3.connect(path)) as conn:self.assertEqual(conn.execute("pragma integrity_check").fetchone()[0],"ok")

    def test_migration_preserves_unrelated_legacy_foreign_key_errors(self):
        path = Path(self.temp.name) / "legacy-orphan.sqlite"
        with closing(sqlite3.connect(path)) as conn:
            conn.executescript("""create table parent(id text primary key);
                create table legacy_child(parent_id text references parent(id));
                insert into legacy_child values('missing');
                create table event_posts(event_id text primary key,
                  payment_method text check(payment_method in ('free','on_site','bank_transfer')));
                insert into event_posts values('keep','bank_transfer');""")
            before = {tuple(row) for row in conn.execute("pragma foreign_key_check")}
            self.assertTrue(before)
            self.mod.migrate(conn, path)
            self.assertEqual(before, {tuple(row) for row in conn.execute("pragma foreign_key_check")})
            self.assertEqual(conn.execute("select payment_method from event_posts").fetchone()[0], "bank_transfer")
            self.assertTrue(conn.execute("select 1 from sqlite_master where name='payment_orders'").fetchone())

    def test_http_success_get_does_not_pay_csrf_and_privacy(self):
        eid=self.save();aid=self.apply(eid);o=self.checkout(aid)
        self.gateway.pay(o["session_id"])
        with self.app.connect() as conn:
            session=self.app.create_user_session(conn,"person")
            other=self.app.create_user_session(conn,"other")
        server=ThreadingHTTPServer(("127.0.0.1",0),self.app.Handler)
        thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
        base=f"http://127.0.0.1:{server.server_address[1]}"
        def request(path,method="GET",body=None,sid=session,headers=None):
            h={"Cookie":"cm_session="+sid,"Content-Type":"application/json",**(headers or {})}
            req=urllib.request.Request(base+path,data=json.dumps(body).encode() if body is not None else None,method=method,headers=h)
            try:
                with urllib.request.urlopen(req) as response:return response.status,response.read().decode()
            except urllib.error.HTTPError as response:
                with response:return response.code,response.read().decode()
        try:
            status,body=request("/payments/orders/"+o["order_id"])
            self.assertEqual(status,200);self.assertIn("支払い待ち",body)
            self.assertIsNone(self.service.order(o["order_id"],admin=True)["paid_at"])
            self.assertNotIn(self.config.key,body)
            csrf=hmac.new(self.app.SESSION_SECRET.encode(),("payments:"+session).encode(),hashlib.sha256).hexdigest()
            path="/api/payments/orders/"+o["order_id"]+"/reconcile"
            self.assertEqual(request(path,"POST",{})[0],403)
            self.assertEqual(request(path,"POST",{},headers={"X-CSRF-Token":csrf,"Origin":"https://evil.example"})[0],403)
            self.assertEqual(request("/payments/orders/"+o["order_id"],sid=other)[0],403)
            self.assertEqual(request(path,"POST",{},headers={"X-CSRF-Token":csrf})[0],200)
            self.assertEqual(self.service.order(o["order_id"],admin=True)["state"],"paid")
            admin_path="/api/payments/admin/connection-status"
            with patch.object(self.app,"ADMIN_PASSWORD","local-admin-password"):
                self.assertEqual(request(admin_path,"POST",{})[0],401)
                auth="Basic "+self.app.base64.b64encode((self.app.ADMIN_USERNAME+":local-admin-password").encode()).decode()
                admin_csrf=hmac.new(self.app.SESSION_SECRET.encode(),("payments:"+auth).encode(),hashlib.sha256).hexdigest()
                self.assertEqual(request(admin_path,"POST",{},headers={"Authorization":auth})[0],403)
                status,body=request(admin_path,"POST",{},headers={"Authorization":auth,"X-CSRF-Token":admin_csrf})
                self.assertEqual(status,200)
                self.assertTrue(json.loads(body)["connection_status"]["stripe_checked"])
                self.assertNotIn(self.config.key,body)
                self.assertNotIn(self.config.webhook_secret,body)
                status,body=request("/admin/payments",headers={"Authorization":auth})
                self.assertEqual(status,200)
                self.assertIn("オンライン決済の接続確認",body)
        finally:
            server.shutdown();server.server_close();thread.join()


if __name__=="__main__":
    unittest.main()
