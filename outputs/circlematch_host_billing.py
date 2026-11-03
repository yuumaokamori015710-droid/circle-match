"""Contingent organizer fees, isolated from participant payments and transfers."""
import hashlib
import json
from pathlib import Path
import secrets
import sqlite3
import time
from urllib.parse import quote

import circlematch_event_pricing as pricing
import circlematch_host_fees as policy
import circlematch_fee_campaign as campaign
from circlematch_payments import PaymentError, Unavailable, VerificationError, stamp


SCHEMA = [
    '''create table if not exists host_fee_agreements (
        event_id text primary key references event_posts(event_id),
        organizer_id text not null references user_accounts(user_id),
        policy_version text not null, fee_bps integer not null check(fee_bps=1000),
        accepted_at text, created_at text not null)''',
    '''create table if not exists host_fee_orders (
        order_id text primary key, event_id text not null references event_posts(event_id),
        organizer_id text not null references user_accounts(user_id),
        mode text not null, platform text not null, amount integer not null check(amount>0),
        snapshot_json text not null, params_json text not null, create_key text not null unique,
        state text not null default 'creating', active integer not null default 1,
        session_id text unique, intent_id text unique, charge_id text unique, paid_at text,
        refund_amount integer not null default 0, needs_review integer not null default 0,
        lease_token text, lease_until integer not null default 0, next_sync_at integer not null default 0,
        created_epoch integer not null, updated_at text not null)''',
    'create unique index if not exists idx_host_fee_active on host_fee_orders(event_id,mode,platform) where active=1',
    '''create trigger if not exists host_fee_snapshot_immutable before update of
       event_id,organizer_id,mode,platform,amount,snapshot_json,params_json,create_key on host_fee_orders
       begin select raise(abort,'host fee snapshot is immutable'); end''',
]


def migrate(conn, path):
    if conn.execute("select 1 from sqlite_master where name='host_fee_orders'").fetchone():
        return
    if conn.in_transaction:
        raise RuntimeError('Host fee migration requires an idle connection')
    backup = sqlite3.connect(str(Path(path)) + '.pre-host-fees-' + str(time.time_ns()) + '.sqlite')
    try:
        conn.backup(backup)
    finally:
        backup.close()
    conn.execute('begin immediate')
    try:
        for sql in SCHEMA:
            conn.execute(sql)
        conn.commit()
    except BaseException:
        conn.rollback()
        raise


def agreement(conn, event_id):
    row = conn.execute('select * from host_fee_agreements where event_id=?', (event_id,)).fetchone()
    return dict(row) if row else None


def validate_consent(conn, event_id, payload, data):
    if campaign.terms(conn, event_id)["waived"]:
        return
    existing = agreement(conn, event_id) if event_id else None
    # Legacy events are never silently enrolled by an edit or re-announcement.
    if existing and existing['accepted_at']:
        return
    if payload['status'] == 'published' and not pricing.is_free(payload):
        if data.get('host_fee_accepted') is not True or data.get('host_fee_policy_version') != policy.POLICY_VERSION:
            raise PaymentError('公開前に主催者利用料10%と発生条件を確認し、同意してください')


def enroll(conn, event_id, user_id, data, *, is_new):
    row = agreement(conn, event_id)
    if not is_new and not row and campaign.terms(conn, event_id)['waived']:
        return
    if not row:
        conn.execute('insert into host_fee_agreements values(?,?,?,?,null,?)',
                     (event_id, user_id, policy.POLICY_VERSION, policy.FEE_BPS, stamp()))
    if campaign.terms(conn, event_id)["waived"]:
        return False
    if data.get('host_fee_accepted') is True and data.get('host_fee_policy_version') == policy.POLICY_VERSION:
        return bool(conn.execute('update host_fee_agreements set accepted_at=? where event_id=? and organizer_id=? and accepted_at is null',
                                 (stamp(), event_id, user_id)).rowcount)
    return False


def legacy_opt_in_blocker(conn, event, local_now):
    if campaign.terms(conn, event['event_id'])["waived"]:
        return '免除対象の大会です。徴収再開後も遡って利用料を適用しません。'
    if event['status'] not in {'published', 'closed'} or event['starts_at'] <= local_now or event['announcement_version']:
        return '開催決定前の、開催予定の公開大会だけが対象です。'
    if pricing.is_free(event):
        return '無料大会の利用料は0円です。'
    eid = event['event_id']
    if (conn.execute("select 1 from event_applications where event_id=? and payment_status!='unpaid' limit 1", (eid,)).fetchone()
            or conn.execute('select 1 from payment_orders where event_id=? limit 1', (eid,)).fetchone()):
        return '入金・決済の記録があるため、後から利用料を適用できません。'
    return ''


def opt_in_legacy(conn, event_id, user_id, data, local_now):
    # Serialize consent with formation and payment writes: a previously shown form may be stale.
    conn.execute('begin immediate')
    event = conn.execute('select * from event_posts where event_id=? and organizer_user_id=?',
                         (event_id, user_id)).fetchone()
    if not event:
        raise PermissionError('この大会の主催者本人だけが同意できます')
    if set(data) != {'accepted', 'policy_version'} or data['accepted'] is not True or data['policy_version'] != policy.POLICY_VERSION:
        raise PaymentError('最新の主催者利用料の条件を確認し、明示的に同意してください')
    existing = agreement(conn, event_id)
    if existing:
        if existing['accepted_at'] and existing['policy_version'] == policy.POLICY_VERSION and existing['organizer_id'] == user_id:
            return False
        raise PaymentError('この大会は既存募集の任意適用の対象ではありません')
    blocker = legacy_opt_in_blocker(conn, event, local_now)
    if blocker:
        raise PaymentError(blocker)
    now = stamp()
    conn.execute('''insert into host_fee_agreements
                    (event_id,organizer_id,policy_version,fee_bps,accepted_at,created_at)
                    values(?,?,?,?,?,?)''', (event_id, user_id, policy.POLICY_VERSION, policy.FEE_BPS, now, now))
    return True


class Billing:
    def __init__(self, connect, payments, notify):
        self.connect, self.payments, self.notify = connect, payments, notify
        self.config = payments.config

    def balance(self, conn, event_id, user_id):
        row = conn.execute('select * from event_posts where event_id=? and organizer_user_id=?', (event_id, user_id)).fetchone()
        if not row:
            raise PermissionError('主催者本人だけが利用料を確認できます')
        event = dict(row)
        applications = [dict(r) for r in conn.execute('select * from event_applications where event_id=?', (event_id,))]
        orders = [dict(r) for r in conn.execute('select * from payment_orders where event_id=? and mode=? and platform=?',
                                               (event_id, self.config.mode, self.config.platform))]
        result = policy.estimate(event, applications, orders)
        current_campaign = campaign.status(conn)
        publication = campaign.terms(conn, event_id)
        accepted = agreement(conn, event_id)
        covered = bool(accepted and accepted['accepted_at'])
        collected, unknown = 0, False
        for application in applications:
            if event['payment_method'] != 'online' and application['payment_status'] == 'paid' and application['status'] == 'confirmed':
                amount = pricing.amount_due(event, application)
                unknown |= amount is None
                collected += amount or 0
        relevant = [r for r in orders if r['paid_at']]
        collected += sum(max(0, r['gross'] - r['refund_amount']) for r in relevant)
        withheld = sum(max(0, r['fee'] - r['fee_refunded']) for r in relevant)
        unsafe = unknown or any(r['needs_review'] or r['refund_state'] not in {'none', 'succeeded'}
                               or r['dispute_state'] != 'none' for r in relevant)
        eligible = covered and not publication['waived'] and result['state'] == 'announced'
        total = 0 if publication['waived'] else None if unsafe else policy.fee(collected) if eligible else 0
        paid = conn.execute('''select coalesce(sum(amount-refund_amount),0) from host_fee_orders
                              where event_id=? and mode=? and platform=? and paid_at is not null''',
                            (event_id, self.config.mode, self.config.platform)).fetchone()[0]
        pending = conn.execute('''select order_id,state from host_fee_orders where event_id=? and mode=? and platform=? and active=1''',
                               (event_id, self.config.mode, self.config.platform)).fetchone()
        needs_review = conn.execute('''select 1 from host_fee_orders where event_id=? and mode=? and platform=?
                                     and needs_review=1 limit 1''',
                                    (event_id,self.config.mode,self.config.platform)).fetchone()
        if needs_review:
            total = None
        result.update(preview_only=self.config.mode != 'live', billing_enabled=current_campaign['enabled'],
                      campaign_enabled=current_campaign['enabled'], campaign_revision=current_campaign['revision'],
                      fee_waived=publication['waived'], waiver_reason=publication['reason'],
                      agreement_accepted=covered, legacy_event=accepted is None, mode=self.config.mode,
                      collected_gross=collected, fee_total=total, online_fee_withheld=withheld, fee_paid=paid,
                      charge_due=None if total is None else max(0, total-withheld-paid) if current_campaign['enabled'] else 0,
                      refund_review_amount=0 if total is None else max(0, paid-max(0,total-withheld)),
                      pending_order=dict(pending) if pending else None)
        digest = json.dumps({k: result[k] for k in ('policy_version','collected_gross','fee_total','online_fee_withheld','fee_paid','charge_due','state','campaign_revision')}, sort_keys=True)
        result['quote_token'] = hashlib.sha256((event_id+user_id+digest).encode()).hexdigest()
        return event, result

    def checkout(self, event_id, user_id, data):
        if set(data) != {'accepted','quote_token'} or data.get('accepted') is not True:
            raise PaymentError('利用料の総額と対象大会を確認してください。金額は指定できません')
        self.payments.new_allowed()
        self.payments.platform_check(accepting_payments=True)
        with self.connect() as conn:
            conn.execute('begin immediate')
            if not campaign.status(conn)['enabled']:
                raise PaymentError('キャンペーン中のため主催者利用料の徴収は停止しています')
            event, balance = self.balance(conn, event_id, user_id)
            existing = balance['pending_order']
            if existing:
                order_id = existing['order_id']
            else:
                if data['quote_token'] != balance['quote_token']:
                    raise PaymentError('利用料の内訳が更新されました。再読み込みして確認してください')
                if balance['charge_due'] is None or balance['charge_due'] < 50 or not balance['agreement_accepted']:
                    raise PaymentError('現在決済できる利用料はありません。未入金分は請求しません')
                if balance['charge_due'] > 99_999_999:
                    raise PaymentError('利用料の総額が決済上限を超えています。運営へ連絡してください')
                order_id = 'hf_' + secrets.token_hex(16)
                destination = self.config.base_url+'/events/'+quote(event_id, safe='')+'/host-fee'
                params = dict(mode='payment', allowed_payment_method_types=['card'], client_reference_id=order_id,
                              managed_payments={'enabled':False},
                              success_url=destination, cancel_url=destination,
                              metadata={'host_fee_order_id':order_id},
                              payment_intent_data={'metadata':{'host_fee_order_id':order_id}},
                              line_items=[{'quantity':1,'price_data':{'currency':'jpy','unit_amount':balance['charge_due'],
                                          'product_data':{'name':'Circle Match 主催者利用料 / '+event['title']}}}])
                conn.execute('''insert into host_fee_orders(order_id,event_id,organizer_id,mode,platform,amount,
                             snapshot_json,params_json,create_key,created_epoch,updated_at) values(?,?,?,?,?,?,?,?,?,?,?)''',
                             (order_id,event_id,user_id,self.config.mode,self.config.platform,balance['charge_due'],
                              json.dumps(balance,ensure_ascii=False),json.dumps(params,ensure_ascii=False),
                              'cm-host-fee-'+secrets.token_hex(20),int(time.time()),stamp()))
        return self.resume(order_id, user_id)

    def order(self, conn, order_id, user_id):
        row = conn.execute('select * from host_fee_orders where order_id=? and organizer_id=? and mode=? and platform=?',
                           (order_id,user_id,self.config.mode,self.config.platform)).fetchone()
        if not row:
            raise PermissionError('この利用料の確認権限がありません')
        return dict(row)

    def resume(self, order_id, user_id, *, create=True, recover=False):
        if create:
            self.payments.new_allowed()
        token = secrets.token_hex(16)
        with self.connect() as conn:
            conn.execute('begin immediate')
            if create and not campaign.status(conn)['enabled']:
                raise PaymentError('主催者利用料の徴収は停止しています')
            order = self.order(conn, order_id, user_id)
            if order['lease_until'] > int(time.time()):
                raise PaymentError('利用料決済を確認中です。重ねて支払わず少し待ってください')
            if order['state'] == 'review':
                raise PaymentError('運営による照合が必要です。新たな支払いはしないでください')
            conn.execute('update host_fee_orders set lease_token=?,lease_until=? where order_id=?', (token,int(time.time())+900,order_id))
        try:
            self.payments.platform_check()
            if order['session_id']:
                session = self.payments.gateway.session(order['session_id'])
            else:
                if not create and not recover:
                    raise PaymentError('決済作成の確認待ちです')
                if int(time.time())-order['created_epoch'] > 23*3600:
                    with self.connect() as conn:
                        conn.execute("update host_fee_orders set state='review',needs_review=1 where order_id=?", (order_id,))
                    raise PaymentError('決済作成の結果が不明です。運営の照合が必要です')
                session = self.payments.gateway.create_session(json.loads(order['params_json']), order['create_key'])
            self.verify(order, session)
            intent = session.get('payment_intent')
            if session.get('payment_status') == 'paid' and (not isinstance(intent,dict) or not isinstance(intent.get('latest_charge'),dict)):
                session = self.payments.gateway.session(session['id'])
                self.verify(order,session)
            with self.connect() as conn:
                conn.execute('begin immediate')
                current = self.order(conn, order_id, user_id)
                if current['lease_token'] != token or current['lease_until'] <= int(time.time()):
                    raise PaymentError('処理権限が更新されました。再確認してください')
                _, balance = self.balance(conn, order['event_id'], user_id)
                state = 'open' if session.get('status') == 'open' else 'expired' if session.get('status') == 'expired' else 'review'
                paid, intent, charge = None, None, None
                refunded = 0
                if session.get('payment_status') == 'paid':
                    intent = session.get('payment_intent')
                    charge = intent.get('latest_charge') if isinstance(intent,dict) else None
                    self.verify_paid(order, intent, charge)
                    paid, state = stamp(), 'paid'
                    refunded = charge.get('amount_refunded', 0)
                    if not isinstance(refunded,int) or not 0 <= refunded <= order['amount']:
                        raise VerificationError('返金額の照合不一致')
                    if charge.get('disputed') or refunded not in {0,order['amount']}:
                        state = 'review'
                    elif refunded == order['amount']:
                        state = 'refunded'
                conn.execute('''update host_fee_orders set session_id=?,state=?,active=?,paid_at=coalesce(paid_at,?),
                             intent_id=coalesce(intent_id,?),charge_id=coalesce(charge_id,?),refund_amount=?,needs_review=?,
                             next_sync_at=?,updated_at=? where order_id=?''',
                             (session['id'],state,int(state not in {'paid','refunded','expired'} and not paid),paid,
                              intent['id'] if intent else None,charge['id'] if charge else None,refunded,
                              int(state=='review'),int(time.time())+300,stamp(),order_id))
                newly_paid = paid and not current['paid_at']
                if newly_paid:
                    self.notify(conn,user_id,order['event_id'],'host_fee_paid','主催者利用料の支払いを確認しました',
                                f"Circle Matchへの利用料 {order['amount']:,}円を確認しました。参加者の参加費とは別の支払いです。")
            if state == 'open' and create:
                if balance['charge_due'] is None or balance['charge_due'] < order['amount'] or not balance['campaign_enabled'] or not self.config.enabled:
                    self.payments.gateway.expire(session['id'])
                    with self.connect() as conn:
                        conn.execute('update host_fee_orders set next_sync_at=0 where order_id=?',(order_id,))
                    raise PaymentError('対象売上・成立状態が変わりました。支払状況を更新してください')
                self.payments.platform_check(accepting_payments=True)
                url = session.get('url') or ''
                if not url.startswith('https://checkout.stripe.com/'):
                    raise VerificationError('決済先URLが正しくありません')
                with self.connect() as conn:
                    conn.execute('begin immediate')
                    _, latest = self.balance(conn, order['event_id'], user_id)
                    if latest['campaign_enabled'] and latest['charge_due'] is not None and latest['charge_due'] >= order['amount']:
                        return {'url':url}
                self.payments.gateway.expire(session['id'])
                with self.connect() as conn:
                    conn.execute('update host_fee_orders set next_sync_at=0 where order_id=?',(order_id,))
                raise PaymentError('徴収設定・対象売上が更新されました。支払状況を更新してください')
            return {'url':'/events/'+quote(order['event_id'], safe='')+'/host-fee'}
        except VerificationError:
            with self.connect() as conn:
                conn.execute("update host_fee_orders set state='review',needs_review=1 where order_id=?", (order_id,))
            raise
        finally:
            with self.connect() as conn:
                conn.execute('update host_fee_orders set lease_until=0 where order_id=? and lease_token=?', (order_id,token))

    def verify(self, order, session):
        if (session.get('mode') != 'payment' or session.get('currency') != 'jpy'
                or session.get('amount_total') != order['amount'] or session.get('client_reference_id') != order['order_id']
                or session.get('livemode') != (order['mode']=='live')
                or (order['session_id'] and session.get('id') != order['session_id'])
                or not str(session.get('id','')).startswith('cs_')):
            raise VerificationError('利用料決済の照合不一致')

    def verify_paid(self, order, intent, charge):
        if (not isinstance(intent,dict) or not isinstance(charge,dict) or intent.get('status') != 'succeeded'
                or intent.get('amount') != order['amount'] or intent.get('amount_received') != order['amount']
                or intent.get('currency') != 'jpy' or intent.get('livemode') != (order['mode']=='live')
                or intent.get('transfer_data') or intent.get('application_fee_amount') or intent.get('on_behalf_of')
                or charge.get('payment_intent') != intent.get('id') or not charge.get('paid') or not charge.get('captured')
                or charge.get('amount') != order['amount'] or charge.get('currency') != 'jpy'
                or charge.get('livemode') != (order['mode']=='live')):
            raise VerificationError('Circle Matchへの利用料入金の照合不一致')

    def webhook_job(self, job):
        with self.connect() as conn:
            row = conn.execute('''select order_id,organizer_id from host_fee_orders where mode=? and platform=?
                and (session_id=? or intent_id=? or charge_id=? or intent_id=? or charge_id=?)''',
                (self.config.mode,self.config.platform,job['object_id'],job['object_id'],job['object_id'],job['related_id'],job['related_id'])).fetchone()
        if not row:
            return False
        self.resume(row['order_id'],row['organizer_id'],create=False)
        return True

    def tick(self):
        if not self.config.key or not self.config.platform:
            return
        with self.connect() as conn:
            paused = not campaign.status(conn)['enabled']
        if paused:
            self.stop_open_checkouts()
        with self.connect() as conn:
            rows = conn.execute('''select order_id,organizer_id from host_fee_orders where mode=? and platform=?
                and state in ('open','paid') and session_id is not null and next_sync_at<=? limit 3''',
                (self.config.mode,self.config.platform,int(time.time()))).fetchall()
        for row in rows:
            try:
                self.resume(row['order_id'],row['organizer_id'],create=False)
            except Exception:
                with self.connect() as conn:
                    conn.execute('update host_fee_orders set next_sync_at=? where order_id=?', (int(time.time())+300,row['order_id']))

    def stop_open_checkouts(self, limit=3):
        with self.connect() as conn:
            if campaign.status(conn)['enabled']:
                return
            rows = conn.execute('''select order_id,organizer_id from host_fee_orders
                where mode=? and platform=? and active=1 and state!='review'
                and lease_until<=? and next_sync_at<=? order by next_sync_at,created_epoch limit ?''',
                (self.config.mode,self.config.platform,int(time.time()),int(time.time()),limit)).fetchall()
        for row in rows:
            try:
                # Recover only the durable attempt/key; never create another invoice.
                self.resume(row['order_id'], row['organizer_id'], create=False, recover=True)
                with self.connect() as conn:
                    order = self.order(conn, row['order_id'], row['organizer_id'])
                if order['state'] == 'open' and order['session_id']:
                    self.payments.gateway.expire(order['session_id'])
                    self.resume(row['order_id'], row['organizer_id'], create=False)
            except Exception:
                # The admin screen retains the pending count until remotely verified.
                with self.connect() as conn:
                    conn.execute('update host_fee_orders set next_sync_at=? where order_id=?',
                                 (int(time.time())+300,row['order_id']))
