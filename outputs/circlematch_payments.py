"""Durable Checkout/Connect boundary. Network I/O never runs inside a DB transaction."""

import hashlib
import json
import os
import re
import secrets
import sqlite3
import time
from dataclasses import dataclass
from datetime import datetime, timezone, timedelta
from pathlib import Path

API_VERSION = "2026-09-30.endive"
FEE_BPS = 1000
MAX_JPY = 99_999_999
MIN_JPY = 50
ACTIVE_STATES = ("creating", "open", "review")


class PaymentError(ValueError):
    pass


class Unavailable(PaymentError):
    pass


class VerificationError(PaymentError):
    pass


def integer(value, label="金額", maximum=MAX_JPY):
    if isinstance(value, bool) or not re.fullmatch(r"[0-9]+", str(value)):
        raise PaymentError(f"{label}は整数で入力してください")
    value = int(value)
    if value > maximum:
        raise PaymentError(f"{label}は{maximum:,}以下にしてください")
    return value


def quote_price(value, mode="gross", quantity=1):
    value, quantity = integer(value), integer(quantity, "数量", 100000)
    if not quantity or mode not in {"net", "gross"}:
        raise PaymentError("料金方式・数量が正しくありません")
    unit = (value * 10000 + 8999) // 9000 if mode == "net" else value
    gross = unit * quantity
    if gross > MAX_JPY or (gross and gross < MIN_JPY):
        raise PaymentError(f"オンライン決済の総額は{MIN_JPY}〜{MAX_JPY:,}円です（無料は0円）")
    fee = (gross * FEE_BPS + 9999) // 10000
    return dict(unit_amount=unit, quantity=quantity, gross=gross, fee=fee, net=gross-fee)


def stamp():
    return datetime.now(timezone.utc).isoformat()


def object_id(obj):
    return obj.get("id") if isinstance(obj, dict) else obj


def rowdict(row):
    return dict(row) if row else None


@dataclass(frozen=True)
class Config:
    enabled: bool = False
    mode: str = "test"
    key: str = ""
    webhook_secret: str = ""
    platform: str = ""
    base_url: str = "http://127.0.0.1:8787"
    live_approved: bool = False
    connect_webhook_secret: str = ""

    @classmethod
    def env(cls):
        prefix = "CIRCLEMATCH_"
        return cls(os.getenv(prefix+"ONLINE_PAYMENTS_ENABLED", "false") == "true",
                   os.getenv(prefix+"STRIPE_MODE", "test"), os.getenv(prefix+"STRIPE_SECRET_KEY", ""),
                   os.getenv(prefix+"STRIPE_WEBHOOK_SECRET", ""), os.getenv(prefix+"STRIPE_PLATFORM_ACCOUNT", ""),
                   os.getenv(prefix+"SITE_BASE_URL", "http://127.0.0.1:8787").rstrip("/"),
                   os.getenv(prefix+"STRIPE_LIVE_APPROVED", "false") == "true",
                   os.getenv(prefix+"STRIPE_CONNECT_WEBHOOK_SECRET", ""))

    def validate(self):
        if self.mode not in {"test", "live"} or not self.platform.startswith("acct_"):
            raise Unavailable("Stripeの接続設定が未完了です")
        if not self.key.startswith("sk_"+self.mode+"_"):
            raise Unavailable("Stripeのキーと動作モードが一致していません")
        if self.mode == "live" and (not self.live_approved or not self.base_url.startswith("https://")):
            raise Unavailable("本番決済は承認・設定されていません")


SCHEMA = [
    """create table if not exists payment_accounts (
      user_id text not null references user_accounts(user_id), mode text not null, platform text not null,
      account_id text unique, create_key text not null unique, created_epoch integer not null,
      state text not null default 'incomplete', checked_at integer not null default 0,
      lease_until integer not null default 0, primary key(user_id,mode,platform))""",
    """create table if not exists payment_orders (
      order_id text primary key, application_id text not null references event_applications(application_id),
      event_id text not null references event_posts(event_id), payer_id text not null references user_accounts(user_id),
      organizer_id text not null references user_accounts(user_id), destination text not null,
      mode text not null, platform text not null, currency text not null check(currency='jpy'),
      unit_amount integer not null, quantity integer not null check(quantity>0), gross integer not null,
      fee_bps integer not null check(fee_bps=1000), fee integer not null, net integer not null,
      snapshot_json text not null, state text not null default 'creating', active integer not null default 1,
      paid_at text, session_id text unique, intent_id text unique, charge_id text unique,
      refund_state text not null default 'none', refund_amount integer not null default 0,
      fee_refunded integer not null default 0, transfer_amount integer, transfer_reversed integer,
      processor_fee integer, dispute_state text not null default 'none',
      needs_review integer not null default 0, last_error text not null default '',
      next_sync_at integer not null default 0, created_epoch integer not null,
      updated_at text not null, check(gross=unit_amount*quantity and gross=fee+net))""",
    "create unique index if not exists idx_payment_active on payment_orders(application_id) where active=1",
    "create index if not exists idx_payment_owner on payment_orders(organizer_id,created_epoch)",
    "create index if not exists idx_payment_event on payment_orders(event_id,state)",
    """create table if not exists payment_attempts (
      order_id text primary key references payment_orders(order_id), idempotency_key text not null unique,
      params_json text not null, state text not null default 'pending', lease_until integer not null default 0,
      lease_token text, created_epoch integer not null, last_error text not null default '')""",
    """create table if not exists payment_refunds (
      refund_job_id text primary key, order_id text not null unique references payment_orders(order_id),
      requested_by text not null, reason text not null, approved_by text,
      idempotency_key text not null unique, stripe_refund_id text unique,
      state text not null default 'requested', lease_until integer not null default 0,
      lease_token text, attempts integer not null default 0, next_attempt_at integer not null default 0,
      first_attempt_at integer, last_error text not null default '', created_at text not null)""",
    """create table if not exists payment_webhooks (
      event_id text primary key, kind text not null, object_id text not null, related_id text,
      account_id text, mode text not null, platform text not null, state text not null default 'queued',
      attempts integer not null default 0, lease_until integer not null default 0,
      next_attempt_at integer not null default 0, last_error text not null default '', created_at text not null)""",
    """create table if not exists payment_audit (
      audit_id integer primary key, order_id text references payment_orders(order_id),
      effect_key text unique, actor text not null, action text not null, detail text not null, created_at text not null)""",
    """create table if not exists payment_rate_limits (
      actor text not null, window integer not null, count integer not null, primary key(actor,window))""",
    """create trigger if not exists payment_snapshot_immutable before update of
      application_id,event_id,payer_id,organizer_id,destination,mode,platform,currency,unit_amount,quantity,
      gross,fee_bps,fee,net,snapshot_json on payment_orders
      begin select raise(abort,'payment snapshot is immutable'); end""",
]


def migrate(conn, database_path):
    schema = conn.execute("select sql from sqlite_master where name='event_posts'").fetchone()[0]
    columns = {r[1] for r in conn.execute("pragma table_info(event_posts)")}
    exists = conn.execute("select 1 from sqlite_master where name='payment_orders'").fetchone()
    if exists and "online_price_input" in columns and "'online'" in schema:
        return
    if conn.in_transaction:
        raise RuntimeError("Payment migration requires an idle connection")
    existing_fk_errors = {tuple(row) for row in conn.execute("pragma foreign_key_check")}
    path = Path(database_path)
    backup_path = path.with_name(path.name + ".pre-online-payments-" + str(time.time_ns()) + ".sqlite")
    backup = sqlite3.connect(backup_path)
    try:
        conn.backup(backup)
    finally:
        backup.close()
    conn.execute("pragma foreign_keys=off")
    try:
        conn.execute("begin immediate")
        if "'online'" not in schema:
            old = "check(payment_method in ('free','on_site','bank_transfer'))"
            if old not in schema:
                raise RuntimeError("Unexpected payment constraint; restore is not automatic")
            objects = conn.execute("select sql from sqlite_master where tbl_name='event_posts' and type in ('index','trigger') and sql is not null").fetchall()
            new_schema, n = re.subn(r'(?i)^CREATE TABLE\s+"?event_posts"?', "CREATE TABLE event_posts_online_v1", schema, count=1)
            if n != 1:
                raise RuntimeError("Unknown event schema")
            conn.execute(new_schema.replace(old, "check(payment_method in ('free','on_site','bank_transfer','online'))"))
            names = ','.join('"'+r[1].replace('"','""')+'"' for r in conn.execute("pragma table_info(event_posts)"))
            conn.execute(f"insert into event_posts_online_v1 ({names}) select {names} from event_posts")
            conn.execute("drop table event_posts")
            conn.execute("alter table event_posts_online_v1 rename to event_posts")
            for obj in objects:
                conn.execute(obj[0])
        if "online_pricing_mode" not in columns:
            conn.execute("alter table event_posts add column online_pricing_mode text not null default 'net'")
        if "online_price_input" not in columns:
            conn.execute("alter table event_posts add column online_price_input integer")
        for statement in SCHEMA:
            conn.execute(statement)
        new_fk_errors = {tuple(row) for row in conn.execute("pragma foreign_key_check")} - existing_fk_errors
        if new_fk_errors:
            raise RuntimeError("Payment migration introduced foreign key errors")
        if conn.execute("pragma integrity_check").fetchone()[0] != "ok":
            raise RuntimeError("Payment migration integrity check failed")
        conn.commit()
    except BaseException:
        conn.rollback()
        raise
    finally:
        conn.execute("pragma foreign_keys=on")


def guard_mutation(conn, application_id=None, event_id=None, financial=False):
    """Must be called under the same write lock as the protected mutation."""
    field, value = ("application_id", application_id) if application_id else ("event_id", event_id)
    orders = conn.execute(f"select * from payment_orders where {field}=? and (active=1 or paid_at is not null)", (value,)).fetchall()
    for order in orders:
        if order["state"] in ACTIVE_STATES:
            raise PaymentError("決済処理を先に確認・終了してください。マイページのオンライン決済から操作できます")
        if financial and order["paid_at"]:
            raise PaymentError("オンライン支払履歴があるため人数・料金は変更できません。返金は注文単位で申請してください")


class StripeGateway:
    def __init__(self, config):
        config.validate()
        import stripe
        self.config, self.stripe = config, stripe
        self.client = stripe.StripeClient(config.key, stripe_version=API_VERSION, max_network_retries=2,
                                          http_client=stripe.RequestsClient(timeout=15))

    @staticmethod
    def plain(obj):
        return obj.to_dict()

    def platform(self):
        return self.plain(self.client.v1.accounts.retrieve_current())

    def create_account(self, key):
        return self.plain(self.client.v1.accounts.create({"country":"JP", "controller": {
            "fees":{"payer":"application"}, "losses":{"payments":"application"},
            "stripe_dashboard":{"type":"express"}},
            "capabilities":{"card_payments":{"requested":True},"transfers":{"requested":True}},
            "metadata":{"circlematch_create_key":key}},
            options={"idempotency_key":key}))

    def account(self, account_id):
        return self.plain(self.client.v1.accounts.retrieve(account_id))

    def account_link(self, account_id):
        return self.plain(self.client.v1.account_links.create({"account":account_id,
            "type":"account_onboarding", "collection_options":{"fields":"eventually_due"},
            "return_url":self.config.base_url+"/payments/connect", "refresh_url":self.config.base_url+"/payments/connect"}))

    def create_session(self, params, key):
        return self.plain(self.client.v1.checkout.sessions.create(params, options={"idempotency_key":key}))

    def session(self, session_id):
        return self.plain(self.client.v1.checkout.sessions.retrieve(session_id, {"expand":["payment_intent.latest_charge"]}))

    def expire(self, session_id):
        return self.plain(self.client.v1.checkout.sessions.expire(session_id))

    def charge(self, charge_id):
        return self.plain(self.client.v1.charges.retrieve(charge_id, {"expand":["balance_transaction","application_fee","transfer","refunds"]}))

    def refund(self, charge_id, key):
        return self.plain(self.client.v1.refunds.create({"charge":charge_id,"reverse_transfer":True,"refund_application_fee":True}, options={"idempotency_key":key}))

    def refund_status(self, refund_id):
        return self.plain(self.client.v1.refunds.retrieve(refund_id))

    def dispute(self, dispute_id):
        return self.plain(self.client.v1.disputes.retrieve(dispute_id))

    def payout(self, payout_id, account_id):
        return self.plain(self.client.v1.payouts.retrieve(payout_id, options={"stripe_account":account_id}))

    def verify(self, body, signature, connected=False):
        secret = self.config.connect_webhook_secret if connected else self.config.webhook_secret
        return self.plain(self.stripe.Webhook.construct_event(body, signature, secret, tolerance=300))


class Payments:
    def __init__(self, connect, notify, config=None, gateway=None):
        self.connect, self.notify = connect, notify
        self.config = config or Config.env()
        self._gateway = gateway

    @property
    def gateway(self):
        if self._gateway is None:
            self._gateway = StripeGateway(self.config)
        return self._gateway

    def platform_check(self):
        platform = self.gateway.platform()
        if platform.get("id") != self.config.platform or platform.get("country") != "JP" or platform.get("default_currency") != "jpy":
            raise Unavailable("Stripeプラットフォーム・日本円の設定が一致しません")

    def new_allowed(self):
        if not self.config.enabled:
            raise Unavailable("オンライン決済の新規受付は停止中です。既存の支払いは引き続き確認できます")

    def audit(self, conn, order_id, action, actor="system", detail="", effect=None):
        return conn.execute("insert or ignore into payment_audit(order_id,effect_key,actor,action,detail,created_at) values(?,?,?,?,?,?)",
                            (order_id,effect,actor,action,detail[:500],stamp())).rowcount

    def rate_limit(self, actor):
        window = int(time.time()) // 60
        with self.connect() as conn:
            conn.execute("begin immediate")
            count = conn.execute("select count from payment_rate_limits where actor=? and window=?", (actor,window)).fetchone()
            if count and count[0] >= 15:
                raise PaymentError("操作が多すぎます。1分後に再試行してください")
            conn.execute("insert into payment_rate_limits values(?,?,1) on conflict(actor,window) do update set count=count+1", (actor,window))
            conn.execute("delete from payment_rate_limits where window<?", (window-60,))

    def account_row(self, user_id):
        with self.connect() as conn:
            return rowdict(conn.execute("select * from payment_accounts where user_id=? and mode=? and platform=?", (user_id,self.config.mode,self.config.platform)).fetchone())

    def refresh_account(self, user_id):
        account = self.account_row(user_id)
        if not account or not account["account_id"]:
            return account
        self.platform_check()
        value = self.gateway.account(account["account_id"])
        req = value.get("requirements") or {}
        caps = value.get("capabilities") or {}
        controller = value.get("controller") or {}
        if value.get("id") != account["account_id"] or value.get("country") != "JP":
            raise PaymentError("主催者の受取口座設定が一致しません")
        state = "incomplete"
        if req.get("disabled_reason"):
            state = "reviewing" if req["disabled_reason"] == "requirements.pending_verification" else "restricted"
        elif req.get("currently_due") or req.get("past_due"):
            state = "action_required" if value.get("details_submitted") else "incomplete"
        elif req.get("pending_verification"):
            state = "reviewing"
        elif value.get("charges_enabled") and value.get("payouts_enabled") and caps.get("card_payments") == caps.get("transfers") == "active":
            state = "ready" if controller.get("fees",{}).get("payer") == "application" and controller.get("losses",{}).get("payments") == "application" else "restricted"
        with self.connect() as conn:
            conn.execute("update payment_accounts set state=?,checked_at=? where account_id=?", (state,int(time.time()),account["account_id"]))
        return self.account_row(user_id)

    def onboard(self, user_id):
        self.new_allowed()
        self.platform_check()
        epoch = int(time.time())
        with self.connect() as conn:
            conn.execute("begin immediate")
            conn.execute("insert or ignore into payment_accounts(user_id,mode,platform,create_key,created_epoch) values(?,?,?,?,?)",
                         (user_id,self.config.mode,self.config.platform,"cm-account-"+secrets.token_hex(20),epoch))
            row = dict(conn.execute("select * from payment_accounts where user_id=? and mode=? and platform=?", (user_id,self.config.mode,self.config.platform)).fetchone())
            if not row["account_id"]:
                if row["lease_until"] > epoch:
                    raise PaymentError("受取設定を準備中です。少し待って再試行してください")
                if epoch-row["created_epoch"] > 23*3600:
                    raise PaymentError("口座作成の結果が不明です。運営による照合が必要です")
                conn.execute("update payment_accounts set lease_until=? where create_key=?", (epoch+900,row["create_key"]))
        if not row["account_id"]:
            try:
                account = self.gateway.create_account(row["create_key"])
                with self.connect() as conn:
                    conn.execute("update payment_accounts set account_id=?,lease_until=0 where create_key=?", (account["id"],row["create_key"]))
            except Exception:
                with self.connect() as conn:
                    conn.execute("update payment_accounts set lease_until=0 where create_key=?", (row["create_key"],))
                raise Unavailable("Stripeの受取設定を作成できませんでした。同じ操作で再試行できます") from None
        account = self.refresh_account(user_id)
        return {"url":self.gateway.account_link(account["account_id"])["url"]}

    def ready_cached(self, conn, user_id):
        row = conn.execute("select * from payment_accounts where user_id=? and mode=? and platform=?",
                           (user_id,self.config.mode,self.config.platform)).fetchone()
        if not row or row["state"] != "ready" or int(time.time())-row["checked_at"] > 300:
            raise Unavailable("主催者の売上受取設定を確認・更新してください")
        return dict(row)

    def load_application(self, conn, app_id, user_id=None):
        app = rowdict(conn.execute("select * from event_applications where application_id=?", (app_id,)).fetchone())
        if not app or (user_id and app["applicant_user_id"] != user_id):
            raise PermissionError("この申込の決済権限がありません")
        event = dict(conn.execute("select * from event_posts where event_id=?", (app["event_id"],)).fetchone())
        return app,event

    def payable(self, conn, app, event):
        local_now = datetime.now(timezone(timedelta(hours=9))).strftime("%Y-%m-%d %H:%M")
        if app["status"] != "confirmed" or event["status"] not in {"published","closed"}:
            raise PaymentError("受付確定後の開催予定イベントだけ決済できます")
        if app["requested_participant_count"]:
            raise PaymentError("人数変更の承認待ちです")
        if ((event["minimum_participants"] and not event["announcement_version"])
                or (event["announcement_version"] and app["attendance_version"] != event["announcement_version"])):
            raise PaymentError("最新の開催案内で最終参加を確認してください")
        deadlines = [v for v in (event["starts_at"],event["payment_deadline"]) if v]
        deadline = min(deadlines)
        if deadline <= local_now:
            raise PaymentError("支払期限または開催日時を過ぎています")
        count = conn.execute("select coalesce(sum(case when ?='team' and ?='チーム' then 1 else participant_count end),0) from event_applications where event_id=? and status='confirmed'", (event["participation_type"],event["capacity_unit"],event["event_id"])).fetchone()[0]
        if event["capacity"] and count > event["capacity"]:
            raise PaymentError("定員の整合性確認が必要です")
        if event["payment_method"] != "online":
            raise PaymentError("この募集はオンライン決済ではありません")
        quantity = 1 if event["fee_unit"] == "1チーム" else app["participant_count"]
        amounts = quote_price(event["fee_amount"], quantity=quantity)
        if event["online_price_input"] is not None:
            expected = quote_price(event["online_price_input"], event["online_pricing_mode"])
            if expected["unit_amount"] != amounts["unit_amount"]:
                raise PaymentError("保存された料金設定が一致しません")
        return amounts, int(datetime.strptime(deadline,"%Y-%m-%d %H:%M").replace(tzinfo=timezone(timedelta(hours=9))).timestamp())

    def checkout(self, app_id, user_id, data):
        if set(data) - {"accepted", "quote_token"} or data.get("accepted") is not True:
            raise PaymentError("支払内容とキャンセル条件の確認が必要です。金額・送金先は指定できません")
        self.new_allowed()
        with self.connect() as conn:
            app,event = self.load_application(conn, app_id, user_id)
            old = conn.execute("select * from payment_orders where application_id=? and (active=1 or paid_at is not null) order by paid_at is not null desc", (app_id,)).fetchone()
        if old:
            if old["paid_at"]:
                return {"url":"/payments/orders/"+old["order_id"]}
            return self.resume_checkout(old["order_id"], user_id)
        self.refresh_account(event["organizer_user_id"])
        epoch = int(time.time())
        with self.connect() as conn:
            conn.execute("begin immediate")
            app,event = self.load_application(conn,app_id,user_id)
            old = conn.execute("select order_id from payment_orders where application_id=? and (active=1 or paid_at is not null) order by paid_at is not null desc", (app_id,)).fetchone()
            if old:
                order_id = old[0]
            else:
                amounts, deadline = self.payable(conn,app,event)
                if not amounts["gross"]:
                    return {"free":True,"url":"/mypage"}
                account = self.ready_cached(conn,event["organizer_user_id"])
                if deadline-epoch < 31*60:
                    raise PaymentError("支払期限まで31分未満のため、新しい決済画面を開けません。主催者へご連絡ください")
                snapshot = self.snapshot(app,event,amounts)
                if data.get("quote_token") != self.quote_token(snapshot):
                    raise PaymentError("料金・開催案内が変わりました。支払内容を再確認してください")
                order_id = "po_"+secrets.token_hex(16)
                params = {"mode":"payment","payment_method_types":["card"],"locale":"ja",
                    "client_reference_id":order_id,"metadata":{"order_id":order_id},
                    "line_items":[{"price_data":{"currency":"jpy","unit_amount":amounts["unit_amount"],
                    "product_data":{"name":event["title"]}},"quantity":amounts["quantity"]}],
                    "payment_intent_data":{"application_fee_amount":amounts["fee"],
                    "transfer_data":{"destination":account["account_id"]},"metadata":{"order_id":order_id}},
                    "expires_at":min(epoch+3600,deadline),
                    "success_url":self.config.base_url+"/payments/orders/"+order_id,
                    "cancel_url":self.config.base_url+"/payments/orders/"+order_id}
                conn.execute("""insert into payment_orders(order_id,application_id,event_id,payer_id,organizer_id,
                    destination,mode,platform,currency,unit_amount,quantity,gross,fee_bps,fee,net,snapshot_json,created_epoch,updated_at)
                    values(?,?,?,?,?,?,?,?,'jpy',?,?,?,?,?,?,?,?,?)""",
                    (order_id,app_id,event["event_id"],user_id,event["organizer_user_id"],account["account_id"],
                     self.config.mode,self.config.platform,amounts["unit_amount"],amounts["quantity"],amounts["gross"],
                     FEE_BPS,amounts["fee"],amounts["net"],json.dumps(snapshot,ensure_ascii=False),epoch,stamp()))
                conn.execute("insert into payment_attempts(order_id,idempotency_key,params_json,created_epoch) values(?,?,?,?)",
                             (order_id,"cm-checkout-"+order_id,json.dumps(params,ensure_ascii=False),epoch))
                self.audit(conn,order_id,"checkout_requested",user_id)
        return self.resume_checkout(order_id,user_id)

    @staticmethod
    def snapshot(app,event,amounts):
        return {**amounts, **{k:event[k] for k in ("title","organizer_name","starts_at","location","prefecture","cancellation_policy","announcement_version","announcement_details","fee_unit","payment_deadline")},
                "application_revision":app["operation_revision"],"participant_count":app["participant_count"],
                "fee_bps":FEE_BPS,"rounding":"ceil_order_total","refund_policy_version":"test-full-order-v1",
                "refund_policy":"主催者都合の中止は利用料を含め全額返金。参加者都合は記載のキャンセル条件に基づき主催者が判断します。"}

    @staticmethod
    def quote_token(snapshot):
        return hashlib.sha256(json.dumps(snapshot,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

    def order(self, order_id, user_id=None, admin=False):
        with self.connect() as conn:
            row = rowdict(conn.execute("select * from payment_orders where order_id=?",(order_id,)).fetchone())
        if not row or (not admin and user_id not in {row["payer_id"],row["organizer_id"]}):
            raise PermissionError("この決済を確認する権限がありません")
        if row["mode"] != self.config.mode or row["platform"] != self.config.platform:
            raise PaymentError("別モード・プラットフォームの注文です")
        return row

    def claim_order(self, order_id):
        token,epoch = secrets.token_hex(16),int(time.time())
        with self.connect() as conn:
            conn.execute("begin immediate")
            row = conn.execute("select * from payment_attempts where order_id=?",(order_id,)).fetchone()
            if row["lease_until"] > epoch:
                raise PaymentError("決済を確認中です。少し待って再試行してください")
            conn.execute("update payment_attempts set lease_until=?,lease_token=? where order_id=?",(epoch+900,token,order_id))
        return token

    def release_order(self, order_id, token):
        with self.connect() as conn:
            conn.execute("update payment_attempts set lease_until=0 where order_id=? and lease_token=?",(order_id,token))

    def resume_checkout(self, order_id, user_id=None):
        order = self.order(order_id,user_id,admin=user_id is None)
        if user_id and order["payer_id"] != user_id:
            raise PermissionError("支払者本人だけが決済画面を開けます")
        if order["paid_at"]:
            return {"url":"/payments/orders/"+order_id}
        if user_id:
            self.new_allowed()
        if order["state"] == "review":
            raise PaymentError("運営による照合が必要です。新しい決済は作成していません")
        token = self.claim_order(order_id)
        try:
            self.platform_check()
            if order["session_id"]:
                session = self.gateway.session(order["session_id"])
            else:
                with self.connect() as conn:
                    attempt = dict(conn.execute("select * from payment_attempts where order_id=?",(order_id,)).fetchone())
                # Stripe may prune idempotency keys after 24h: never create again after uncertainty.
                if int(time.time())-attempt["created_epoch"] > 23*3600:
                    self.mark_review(order_id,"checkout_result_unknown",terminal=True)
                    raise PaymentError("決済作成の結果が不明です。運営の照合が必要です")
                session = self.gateway.create_session(json.loads(attempt["params_json"]),attempt["idempotency_key"])
                self.validate_session(order,session)
                with self.connect() as conn:
                    conn.execute("update payment_orders set session_id=? where order_id=? and session_id is null",(session["id"],order_id))
                    conn.execute("update payment_attempts set state='created' where order_id=?",(order_id,))
                order = self.order(order_id,admin=True)
            self.apply_session(order,session,token)
            if session.get("status") == "open" and session.get("url"):
                account = self.refresh_account(order["organizer_id"])
                blocked = not self.config.enabled or not account or account["state"] != "ready" or account["account_id"] != order["destination"]
                with self.connect() as conn:
                    app,event = self.load_application(conn,order["application_id"])
                    try:
                        self.payable(conn,app,event)
                    except PaymentError:
                        blocked = True
                if blocked:
                    try:
                        self.gateway.expire(session["id"])
                    except Exception:
                        pass
                    self.apply_session(order,self.gateway.session(session["id"]),token)
                    raise PaymentError("決済の受付条件・受取設定を確認できません。支払状況を確認してください")
                if not session["url"].startswith("https://checkout.stripe.com/"):
                    raise PaymentError("決済先URLが正しくありません")
                return {"url":session["url"]}
            return {"url":"/payments/orders/"+order_id}
        except VerificationError:
            self.mark_review(order_id,"verification_mismatch",terminal=True)
            raise
        finally:
            self.release_order(order_id,token)

    def validate_session(self, order, session):
        if (session.get("livemode") != (order["mode"] == "live") or session.get("mode") != "payment"
                or session.get("currency") != "jpy" or session.get("amount_total") != order["gross"]
                or session.get("client_reference_id") != order["order_id"]
                or (order["session_id"] and session.get("id") != order["session_id"])):
            raise VerificationError("Stripe決済内容の照合不一致")

    @staticmethod
    def check_lease(conn, order_id, token):
        if token and not conn.execute("select 1 from payment_attempts where order_id=? and lease_token=? and lease_until>?",(order_id,token,int(time.time()))).fetchone():
            raise PaymentError("処理権限が更新されました。支払状況を再確認してください")

    def apply_session(self, order, session, token=None):
        self.validate_session(order,session)
        intent = session.get("payment_intent")
        if session.get("payment_status") == "paid":
            if not isinstance(intent,dict):
                session = self.gateway.session(session["id"])
                intent = session.get("payment_intent")
            charge = intent.get("latest_charge") if isinstance(intent,dict) else None
            if not isinstance(charge,dict):
                raise PaymentError("支払照合に必要なChargeが未取得です")
            if (intent.get("status") != "succeeded" or intent.get("currency") != "jpy"
                    or intent.get("amount") != order["gross"] or intent.get("amount_received") != order["gross"]
                    or intent.get("application_fee_amount") != order["fee"]
                    or object_id((intent.get("transfer_data") or {}).get("destination")) != order["destination"]
                    or intent.get("on_behalf_of") or intent.get("livemode") != (order["mode"] == "live")
                    or charge.get("payment_intent") != intent.get("id")
                    or not charge.get("paid") or not charge.get("captured") or charge.get("amount") != order["gross"]
                    or charge.get("currency") != "jpy" or charge.get("livemode") != (order["mode"] == "live")):
                raise VerificationError("PaymentIntent・Charge・手数料・送金先の照合不一致")
            with self.connect() as conn:
                conn.execute("begin immediate")
                self.check_lease(conn,order["order_id"],token)
                current = dict(conn.execute("select * from payment_orders where order_id=?",(order["order_id"],)).fetchone())
                app,event = self.load_application(conn,order["application_id"])
                anomaly = app["status"] != "confirmed" or event["status"] == "cancelled" or not current["active"]
                conn.execute("update payment_orders set state=?,paid_at=coalesce(paid_at,?),intent_id=?,charge_id=?,needs_review=max(needs_review,?),updated_at=? where order_id=?",
                             ("review" if anomaly else "paid",stamp(),intent["id"],charge["id"],int(anomaly),stamp(),order["order_id"]))
                if self.audit(conn,order["order_id"],"paid_verified",effect="paid:"+intent["id"]):
                    for recipient in (order["payer_id"],order["organizer_id"]):
                        self.notify(conn,recipient,order["event_id"],"online_payment","オンライン支払いを確認しました",f"{order['gross']:,}円の支払いを確認しました。銀行への入金完了を示すものではありません。マイページのオンライン決済をご確認ください。")
                if anomaly:
                    self.audit(conn,order["order_id"],"paid_after_cancellation",effect="anomaly:"+intent["id"])
                    self.request_refund_tx(conn,current,"system","取消・中止後の入金確認",approve=event["status"]=="cancelled")
            self.sync_money(self.order(order["order_id"],admin=True))
        elif session.get("status") == "expired":
            with self.connect() as conn:
                conn.execute("begin immediate")
                self.check_lease(conn,order["order_id"],token)
                conn.execute("update payment_orders set state='expired',active=0,updated_at=? where order_id=? and paid_at is null and state!='review'",(stamp(),order["order_id"]))
        elif session.get("status") == "open":
            with self.connect() as conn:
                conn.execute("begin immediate")
                self.check_lease(conn,order["order_id"],token)
                conn.execute("update payment_orders set state='open',updated_at=? where order_id=? and state='creating' and paid_at is null",(stamp(),order["order_id"]))

    def mark_review(self, order_id, code, terminal=False):
        with self.connect() as conn:
            conn.execute("begin immediate")
            conn.execute("update payment_orders set needs_review=1,last_error=?,next_sync_at=? where order_id=?",(code,int(time.time())+300,order_id))
            if terminal:
                conn.execute("update payment_orders set state='review' where order_id=?",(order_id,))
            order = conn.execute("select * from payment_orders where order_id=?",(order_id,)).fetchone()
            if self.audit(conn,order_id,"needs_review",detail=code,effect="review:"+order_id+":"+code):
                self.notify(conn,order["organizer_id"],order["event_id"],"online_review","決済の確認が必要です","自動処理を完了できませんでした。オンライン決済の状態をご確認ください。運営管理画面にも記録しています。")

    def reconcile(self, order_id, user_id=None, expire=False):
        order = self.order(order_id,user_id,admin=user_id is None)
        if not order["session_id"]:
            self.resume_checkout(order_id,user_id if user_id == order["payer_id"] else None)
            order = self.order(order_id,user_id,admin=user_id is None)
        token = self.claim_order(order_id)
        try:
            self.platform_check()
            session = self.gateway.session(order["session_id"])
            if expire and session.get("status") == "open":
                try:
                    self.gateway.expire(order["session_id"])
                except Exception:
                    # A racing success may make expire fail; retrieve the authoritative state.
                    pass
                session = self.gateway.session(order["session_id"])
            self.apply_session(order,session,token)
            with self.connect() as conn:
                conn.execute("update payment_orders set next_sync_at=? where order_id=?",(int(time.time())+300,order_id))
            if expire and session.get("status") == "open":
                raise PaymentError("Stripe側の決済終了を確認できません。枠は解放していません")
            return self.order(order_id,user_id,admin=user_id is None)
        except VerificationError:
            self.mark_review(order_id,"verification_mismatch",terminal=True)
            raise
        finally:
            self.release_order(order_id,token)

    def sync_money(self, order):
        charge = self.gateway.charge(order["charge_id"])
        if (charge.get("id") != order["charge_id"] or object_id(charge.get("payment_intent")) != order["intent_id"]
                or charge.get("amount") != order["gross"] or charge.get("currency") != "jpy"
                or charge.get("livemode") != (order["mode"] == "live")):
            raise VerificationError("資金照合の対象が一致しません")
        balance = charge.get("balance_transaction")
        fee,transfer = charge.get("application_fee"),charge.get("transfer")
        processor_fee = None
        if isinstance(balance,dict) and balance.get("currency") == "jpy":
            details = balance.get("fee_details")
            if details is not None:
                processor_fee = sum(d["amount"] for d in details if d.get("type") in {"stripe_fee","payment_method_passthrough_fee"})
        fee_refunded = fee.get("amount_refunded",0) if isinstance(fee,dict) else 0
        transferred = transfer.get("amount") if isinstance(transfer,dict) else None
        reversed_amount = transfer.get("amount_reversed",0) if isinstance(transfer,dict) else None
        refunds = charge.get("refunds")
        refund_rows = refunds.get("data",[]) if isinstance(refunds,dict) else []
        for refund in refund_rows:
            if (object_id(refund.get("charge")) != order["charge_id"] or refund.get("currency") != "jpy"
                    or not isinstance(refund.get("amount"),int) or refund["amount"] < 0):
                raise VerificationError("返金照合の対象が一致しません")
        # Charge totals alone do not prove that a pending card refund succeeded.
        refund_amount = sum(r["amount"] for r in refund_rows if r.get("status") == "succeeded")
        pending = any(r.get("status") == "pending" for r in refund_rows)
        failed = any(r.get("status") in {"failed","canceled"} for r in refund_rows)
        uncertain = (not isinstance(refunds,dict) or bool(refunds.get("has_more"))
                     or any(r.get("status") not in {"succeeded","pending","failed","canceled"} for r in refund_rows))
        disputed = bool(charge.get("disputed"))
        refund_state = order["refund_state"]
        review = False
        if uncertain or refund_amount > order["gross"]:
            refund_state,review = "review",True
        elif 0 < refund_amount < order["gross"]:
            refund_state,review = "partial",True
        elif refund_amount == order["gross"]:
            if (not pending and fee_refunded == order["fee"] and transferred is not None
                    and reversed_amount == transferred and charge.get("amount_refunded") == refund_amount):
                refund_state = "succeeded"
            else:
                refund_state,review = "review",True
        elif pending:
            refund_state = "processing"
        elif failed:
            refund_state,review = "failed",True
        elif charge.get("amount_refunded",0) != refund_amount:
            refund_state,review = "review",True
        if not isinstance(fee,dict) or not isinstance(transfer,dict):
            review = True
        elif (fee.get("amount") != order["fee"] or object_id(fee.get("account")) != order["destination"]
              or object_id(transfer.get("destination")) != order["destination"]
              or transferred != order["gross"] or fee.get("currency") != "jpy" or transfer.get("currency") != "jpy"):
            review = True
        with self.connect() as conn:
            conn.execute("begin immediate")
            conn.execute("""update payment_orders set processor_fee=?,refund_amount=?,
              fee_refunded=max(fee_refunded,?),transfer_amount=?,transfer_reversed=max(coalesce(transfer_reversed,0),coalesce(?,0)),
              refund_state=?,
              dispute_state=case when ? and dispute_state='none' then 'open' else dispute_state end,
              needs_review=max(needs_review,?),updated_at=? where order_id=?""",
              (processor_fee,refund_amount,fee_refunded,transferred,reversed_amount,refund_state,disputed,int(review),stamp(),order["order_id"]))
            if refund_state == "succeeded":
                conn.execute("update payment_refunds set state='succeeded' where order_id=?",(order["order_id"],))
                if self.audit(conn,order["order_id"],"refund_succeeded",effect="refunded:"+order["order_id"]):
                    for recipient in (order["payer_id"],order["organizer_id"]):
                        self.notify(conn,recipient,order["event_id"],"online_refund","全額返金処理を確認しました","利用料を含む全額の返金処理を確認しました。カード明細への反映時期はカード会社によって異なります。")
            if disputed:
                conn.execute("update payment_refunds set state='review',last_error='dispute' where order_id=? and state!='succeeded'",(order["order_id"],))
                if self.audit(conn,order["order_id"],"dispute_detected",effect="dispute:"+order["order_id"]):
                    self.notify(conn,order["organizer_id"],order["event_id"],"online_dispute","カード支払いの異議申立てを確認しました","通常の返金と別の対応が必要です。運営へご連絡ください。自動返金は停止しました。")
        if review:
            self.mark_review(order["order_id"],"refund_or_transfer_reconciliation")

    def request_refund_tx(self, conn, order, actor, reason, approve=False):
        if not reason or len(reason) > 500:
            raise PaymentError("返金理由を500文字以内で入力してください")
        current = dict(conn.execute("select * from payment_orders where order_id=?",(order["order_id"],)).fetchone())
        if not current["paid_at"] or current["dispute_state"] != "none" or current["refund_amount"]:
            if current["refund_state"] == "succeeded":
                return
            raise PaymentError("未払い・返金済み・紛争中の注文はこの操作で返金できません")
        existing = conn.execute("select * from payment_refunds where order_id=?",(order["order_id"],)).fetchone()
        if existing:
            if approve and existing["state"] == "requested":
                conn.execute("update payment_refunds set state='queued',approved_by=? where order_id=?",(actor,order["order_id"]))
                conn.execute("update payment_orders set refund_state='processing' where order_id=?",(order["order_id"],))
                self.audit(conn,order["order_id"],"refund_approved",actor,reason)
            return
        conn.execute("""insert into payment_refunds(refund_job_id,order_id,requested_by,reason,approved_by,
          idempotency_key,state,created_at) values(?,?,?,?,?,?,?,?)""",
          ("pr_"+secrets.token_hex(16),order["order_id"],actor,reason,actor if approve else None,
           "cm-refund-"+order["order_id"],"queued" if approve else "requested",stamp()))
        conn.execute("update payment_orders set refund_state=? where order_id=?",("processing" if approve else "requested",order["order_id"]))
        self.audit(conn,order["order_id"],"refund_requested",actor,reason)
        for recipient in (order["payer_id"],order["organizer_id"]):
            self.notify(conn,recipient,order["event_id"],"online_refund_requested","返金の申請・処理を受け付けました","返金はまだ完了していません。オンライン決済画面で処理状況をご確認ください。")

    def request_refund(self, order_id, user_id, reason, approve=False, admin=False):
        order = self.order(order_id,user_id,admin)
        if approve and not (admin or order["organizer_id"] == user_id):
            raise PermissionError("返金の承認権限がありません")
        with self.connect() as conn:
            conn.execute("begin immediate")
            self.request_refund_tx(conn,order,user_id,reason,approve)

    def cancellation_preview(self, event_id, user_id):
        with self.connect() as conn:
            event = conn.execute("select organizer_user_id from event_posts where event_id=?",(event_id,)).fetchone()
            if not event or event[0] != user_id:
                raise PermissionError("この募集を管理する権限がありません")
            return self.cancel_summary(conn,event_id)

    @staticmethod
    def cancel_summary(conn,event_id):
        rows = [dict(r) for r in conn.execute("select order_id,state,paid_at,gross,refund_state,refund_amount,dispute_state from payment_orders where event_id=?",(event_id,))]
        due = [r for r in rows if r["paid_at"] and r["refund_state"] != "succeeded"]
        return {"count":len(due),"gross":sum(r["gross"]-r["refund_amount"] for r in due),
                "token":hashlib.sha256(json.dumps(rows,sort_keys=True).encode()).hexdigest()}

    def event_cancel_tx(self,conn,event_id,user_id,token):
        summary = self.cancel_summary(conn,event_id)
        if summary["token"] != token:
            raise PaymentError("返金対象が変わりました。中止確認画面を再読み込みしてください")
        guard_mutation(conn,event_id=event_id)
        for row in conn.execute("select * from payment_orders where event_id=? and paid_at is not null and refund_state!='succeeded'",(event_id,)).fetchall():
            if row["dispute_state"] != "none" or row["refund_amount"]:
                conn.execute("update payment_orders set needs_review=1 where order_id=?",(row["order_id"],))
                self.audit(conn,row["order_id"],"cancellation_manual_refund_review",user_id)
            else:
                self.request_refund_tx(conn,row,user_id,"主催者によるイベント中止",True)

    def refund_job(self):
        epoch,token = int(time.time()),secrets.token_hex(16)
        with self.connect() as conn:
            conn.execute("begin immediate")
            row = conn.execute("""select r.* from payment_refunds r join payment_orders o on o.order_id=r.order_id
                where o.mode=? and o.platform=? and r.state in ('queued','processing','retry')
                and r.next_attempt_at<=? and r.lease_until<=? order by r.created_at limit 1""",
                (self.config.mode,self.config.platform,epoch,epoch)).fetchone()
            if not row:
                return False
            job = dict(row)
            conn.execute("update payment_refunds set lease_until=?,lease_token=?,attempts=attempts+1,first_attempt_at=coalesce(first_attempt_at,?),state='processing' where order_id=?",(epoch+900,token,epoch,job["order_id"]))
        order = self.order(job["order_id"],admin=True)
        try:
            self.reconcile(order["order_id"])
            order = self.order(order["order_id"],admin=True)
            if order["refund_state"] == "succeeded":
                return True
            if order["dispute_state"] != "none" or order["refund_amount"]:
                raise PaymentError("refund_manual_review")
            if job["stripe_refund_id"]:
                refund = self.gateway.refund_status(job["stripe_refund_id"])
            else:
                if job["first_attempt_at"] and epoch-job["first_attempt_at"] > 23*3600:
                    raise PaymentError("refund_result_unknown")
                refund = self.gateway.refund(order["charge_id"],job["idempotency_key"])
            if object_id(refund.get("charge")) != order["charge_id"] or refund.get("amount") != order["gross"] or refund.get("currency") != "jpy":
                raise PaymentError("refund_mismatch")
            with self.connect() as conn:
                conn.execute("update payment_refunds set stripe_refund_id=? where order_id=? and lease_token=?",(refund["id"],order["order_id"],token))
            self.reconcile(order["order_id"])
            state = "failed" if refund.get("status") in {"failed","canceled"} else "processing"
            with self.connect() as conn:
                conn.execute("update payment_refunds set state=?,next_attempt_at=?,last_error=? where order_id=? and state!='succeeded' and lease_token=?",(state,epoch+300,"provider_refund_failed" if state=="failed" else "",order["order_id"],token))
                if state == "failed":
                    conn.execute("update payment_orders set refund_state='failed',needs_review=1 where order_id=?",(order["order_id"],))
            if state == "failed":
                self.mark_review(order["order_id"],"provider_refund_failed")
        except Exception as exc:
            code = type(exc).__name__
            terminal = isinstance(exc,PaymentError) and str(exc) in {"refund_manual_review","refund_result_unknown","refund_mismatch"}
            with self.connect() as conn:
                conn.execute("update payment_refunds set state=?,next_attempt_at=?,last_error=? where order_id=? and state!='succeeded' and lease_token=?",("review" if terminal else "retry",epoch+300,code,order["order_id"],token))
            self.mark_review(order["order_id"],"refund_"+code)
        finally:
            with self.connect() as conn:
                conn.execute("update payment_refunds set lease_until=0 where order_id=? and lease_token=?",(order["order_id"],token))
        return True

    def receive_webhook(self,body,signature,connected=False):
        if not (self.config.connect_webhook_secret if connected else self.config.webhook_secret):
            raise Unavailable("Webhookは未設定です")
        try:
            event = self.gateway.verify(body,signature,connected=connected)
        except Exception:
            raise PaymentError("Webhook署名が正しくありません") from None
        if event.get("livemode") != (self.config.mode == "live") or not event.get("id"):
            raise PaymentError("Webhookの動作モードが一致しません")
        kind,obj = event["type"],event["data"]["object"]
        account = event.get("account")
        if not connected and account:
            raise PaymentError("プラットフォームの決済通知ではありません")
        if connected:
            if kind not in {"account.updated","payout.failed"} or not account or (kind == "account.updated" and obj["id"] != account):
                raise PaymentError("主催者口座の通知ではありません")
            with self.connect() as conn:
                known = conn.execute("select 1 from payment_accounts where account_id=? and mode=? and platform=?",(account,self.config.mode,self.config.platform)).fetchone()
            if not known:
                raise PaymentError("登録されていない主催者の通知です")
        elif kind == "account.updated" or kind.startswith("payout."):
            raise PaymentError("口座通知は専用のWebhookに送信してください")
        # Persist only routing IDs, not the webhook's customer/card/KYC payload.
        related = object_id(obj.get("charge")) or object_id(obj.get("payment_intent"))
        with self.connect() as conn:
            conn.execute("insert or ignore into payment_webhooks(event_id,kind,object_id,related_id,account_id,mode,platform,created_at) values(?,?,?,?,?,?,?,?)",
                         (event["id"],kind,obj["id"],related,account,self.config.mode,self.config.platform,stamp()))
        return {"received":True}

    def webhook_job(self):
        epoch = int(time.time())
        with self.connect() as conn:
            conn.execute("begin immediate")
            row = conn.execute("select * from payment_webhooks where mode=? and platform=? and state in ('queued','retry','processing') and next_attempt_at<=? and lease_until<=? order by created_at limit 1",(self.config.mode,self.config.platform,epoch,epoch)).fetchone()
            if not row:
                return False
            job = dict(row)
            conn.execute("update payment_webhooks set state='processing',attempts=attempts+1,lease_until=? where event_id=?",(epoch+900,job["event_id"]))
        try:
            kind = job["kind"]
            if kind == "account.updated":
                with self.connect() as conn:
                    account = conn.execute("select user_id from payment_accounts where account_id=?",(job["object_id"],)).fetchone()
                self.refresh_account(account[0])
                current = self.account_row(account[0])
                if current["state"] != "ready":
                    with self.connect() as conn:
                        opens = conn.execute("select order_id from payment_orders where destination=? and active=1 and paid_at is null and session_id is not null",(current["account_id"],)).fetchall()
                    for item in opens:
                        self.reconcile(item[0],expire=True)
            elif kind == "payout.failed":
                self.platform_check()
                payout = self.gateway.payout(job["object_id"],job["account_id"])
                if payout.get("id") != job["object_id"] or payout.get("livemode") != (self.config.mode == "live"):
                    raise VerificationError("銀行入金の照合不一致")
                if payout.get("status") == "failed":
                    with self.connect() as conn:
                        conn.execute("begin immediate")
                        account = conn.execute("select user_id from payment_accounts where account_id=?",(job["account_id"],)).fetchone()
                        if self.audit(conn,None,"payout_failed",detail=job["object_id"],effect="payout:"+job["object_id"]):
                            self.notify(conn,account[0],None,"online_payout_failed","銀行への入金に失敗しました","支払確認とは別の銀行入金エラーです。Stripeの受取設定をご確認のうえ運営へご連絡ください。")
            elif kind.startswith(("checkout.session.","payment_intent.","charge.","refund.","application_fee.")):
                with self.connect() as conn:
                    order = conn.execute("select order_id from payment_orders where session_id=? or intent_id=? or charge_id=? or charge_id=? or intent_id=?",
                                         (job["object_id"],job["object_id"],job["object_id"],job["related_id"],job["related_id"])).fetchone()
                if not order:
                    raise PaymentError("注文が未照合です。決済作成の復旧後に再処理します")
                self.reconcile(order[0])
                if kind.startswith("refund."):
                    refund = self.gateway.refund_status(job["object_id"])
                    if refund.get("status") in {"failed","canceled"}:
                        with self.connect() as conn:
                            conn.execute("update payment_orders set refund_state='failed',needs_review=1 where order_id=? and refund_state!='succeeded'",(order[0],))
                        self.mark_review(order[0],"external_refund_failed")
                if kind.startswith("charge.dispute."):
                    dispute = self.gateway.dispute(job["object_id"])
                    with self.connect() as conn:
                        conn.execute("update payment_orders set dispute_state=?,needs_review=1 where order_id=?",(dispute.get("status","open"),order[0]))
            with self.connect() as conn:
                conn.execute("update payment_webhooks set state='done',lease_until=0,last_error='' where event_id=?",(job["event_id"],))
        except Exception as exc:
            with self.connect() as conn:
                conn.execute("update payment_webhooks set state=?,lease_until=0,next_attempt_at=?,last_error=? where event_id=?",("failed" if job["attempts"]>=9 else "retry",epoch+min(3600,30*2**min(job["attempts"],7)),type(exc).__name__,job["event_id"]))
        return True

    def tick(self):
        if not self.config.key or not self.config.platform:
            return False
        self.webhook_job()
        self.refund_job()
        with self.connect() as conn:
            rows = conn.execute("select order_id from payment_orders where mode=? and platform=? and next_sync_at<=? and (state in ('creating','open','review') or (paid_at is not null and refund_state!='succeeded')) order by next_sync_at limit 3",(self.config.mode,self.config.platform,int(time.time()))).fetchall()
        for row in rows:
            try:
                self.reconcile(row[0])
            except Exception as exc:
                self.mark_review(row[0],type(exc).__name__)
        return True

    def replay_webhook(self,event_id,actor):
        with self.connect() as conn:
            conn.execute("begin immediate")
            if not conn.execute("update payment_webhooks set state='queued',next_attempt_at=0,lease_until=0 where event_id=? and state in ('failed','done','retry') and mode=? and platform=?",(event_id,self.config.mode,self.config.platform)).rowcount:
                raise PaymentError("再処理できる通知がありません")
            self.audit(conn,None,"webhook_replay",actor,event_id)

    def recover_order(self,order_id,session_id,actor):
        """Operator-only recovery: bind an existing remote result, never create a payment."""
        order = self.order(order_id,admin=True)
        self.platform_check()
        session = self.gateway.session(session_id)
        self.validate_session(order,session)
        token = self.claim_order(order_id)
        try:
            with self.connect() as conn:
                conn.execute("begin immediate")
                self.check_lease(conn,order_id,token)
                conn.execute("update payment_orders set session_id=?,state=case when paid_at is null then 'creating' else state end where order_id=? and (session_id is null or session_id=?)",(session_id,order_id,session_id))
                self.audit(conn,order_id,"recovery_bound",actor,session_id)
            self.apply_session(self.order(order_id,admin=True),session,token)
        finally:
            self.release_order(order_id,token)

    def recover_account(self,user_id,account_id,actor):
        row = self.account_row(user_id)
        if not row or row["account_id"]:
            raise PaymentError("未確定の口座作成履歴だけ復旧できます")
        self.platform_check()
        account = self.gateway.account(account_id)
        if account.get("country") != "JP" or account.get("metadata",{}).get("circlematch_create_key") != row["create_key"]:
            raise VerificationError("口座作成履歴との照合不一致")
        with self.connect() as conn:
            conn.execute("begin immediate")
            if not conn.execute("update payment_accounts set account_id=?,lease_until=0 where user_id=? and mode=? and platform=? and account_id is null and lease_until<=?",(account_id,user_id,self.config.mode,self.config.platform,int(time.time()))).rowcount:
                raise PaymentError("口座作成を処理中です")
            self.audit(conn,None,"account_recovery_bound",actor,account_id)
        return self.refresh_account(user_id)
