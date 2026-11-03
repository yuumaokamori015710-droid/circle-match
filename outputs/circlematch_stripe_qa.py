"""Opt-in, expiring sandbox webhook verification; never uses the application DB."""

import hashlib
import os
import re
import sqlite3
import tempfile
import time
from contextlib import closing
from dataclasses import dataclass, field
from pathlib import Path

from circlematch_payments import API_VERSION

WEBHOOK_PATH = "/api/payments/sandbox-verification/webhook"
MAX_BODY = 65536
MAX_WINDOW = 6 * 3600


class Disabled(Exception):
    pass


@dataclass(frozen=True)
class Config:
    until: int
    session_id: str
    secret: str = field(repr=False)
    key: str = field(repr=False)


def settings(environ=None, now=None):
    env = os.environ if environ is None else environ
    now = time.time() if now is None else now
    prefix = "CIRCLEMATCH_STRIPE_QA_"
    try:
        until = int(env.get(prefix + "WEBHOOK_UNTIL", "0"))
    except (TypeError, ValueError):
        raise Disabled("sandbox_verification_disabled") from None
    secret = env.get(prefix + "WEBHOOK_SECRET", "")
    key = env.get(prefix + "SECRET_KEY", "")
    session_id = env.get(prefix + "CHECKOUT_SESSION", "")
    if (not now < until <= now + MAX_WINDOW or not secret.startswith("whsec_")
            or len(secret) < 16 or not key.startswith("rk_test_")
            or not re.fullmatch(r"cs_test_[A-Za-z0-9_]{1,200}", session_id)
            or secret in {env.get("CIRCLEMATCH_STRIPE_WEBHOOK_SECRET", ""),
                          env.get("CIRCLEMATCH_STRIPE_CONNECT_WEBHOOK_SECRET", "")}
            or env.get("CIRCLEMATCH_ONLINE_PAYMENTS_ENABLED", "false") != "false"
            or env.get("CIRCLEMATCH_STRIPE_LIVE_APPROVED", "false") != "false"):
        raise Disabled("sandbox_verification_disabled")
    return Config(until, session_id, secret, key)


def database_path(config):
    ident = hashlib.sha256(config.session_id.encode()).hexdigest()[:16]
    return Path(tempfile.gettempdir()) / ("circlematch-stripe-qa-" + ident + ".sqlite3")


def _connect(path):
    path = Path(path)
    if path.is_symlink():
        raise Disabled("sandbox_verification_disabled")
    conn = sqlite3.connect(path, timeout=3)
    conn.row_factory = sqlite3.Row
    try:
        path.chmod(0o600)
        conn.execute("""create table if not exists qa_receipts (
            event_id text primary key, event_type text not null, session_id text not null,
            first_received integer not null, last_received integer not null,
            deliveries integer not null default 1, state text not null default 'queued',
            attempts integer not null default 0, processed_count integer not null default 0,
            lease_until integer not null default 0, checked_at integer, last_error text not null default '',
            unique(event_type,session_id))""")
        conn.commit()
        return conn
    except Exception:
        conn.close()
        raise


def receive(body, signature, *, config=None, path=None):
    config = config or settings()
    if not isinstance(body, bytes) or not 0 < len(body) <= MAX_BODY:
        raise ValueError("invalid_sandbox_payload")
    import stripe
    try:
        event = stripe.Webhook.construct_event(body, signature, config.secret, tolerance=300).to_dict()
    except Exception:
        raise ValueError("invalid_sandbox_signature") from None
    data = event.get("data")
    obj = data.get("object") if isinstance(data, dict) else None
    if (not re.fullmatch(r"evt_[A-Za-z0-9_]{1,200}", str(event.get("id", "")))
            or event.get("livemode") is not False or event.get("account")
            or event.get("type") != "checkout.session.completed" or not isinstance(obj, dict)
            or obj.get("object") != "checkout.session" or obj.get("livemode") is not False
            or obj.get("id") != config.session_id or not isinstance(obj.get("metadata"), dict)
            or obj["metadata"].get("purpose") != "circlematch_qa_only"):
        raise ValueError("unexpected_sandbox_event")
    epoch = int(time.time())
    with closing(_connect(path or database_path(config))) as conn, conn:
        conn.execute("begin immediate")
        inserted = conn.execute("""insert or ignore into qa_receipts
            (event_id,event_type,session_id,first_received,last_received) values(?,?,?,?,?)""",
            (event["id"], event["type"], obj["id"], epoch, epoch)).rowcount
        if not inserted:
            conn.execute("update qa_receipts set deliveries=deliveries+1,last_received=? where event_type=? and session_id=?",
                         (epoch, event["type"], obj["id"]))
    return {"received": True, "sandbox_verification": True, "duplicate": not bool(inserted)}


def _retrieve(config):
    import stripe
    client = stripe.StripeClient(config.key, stripe_version=API_VERSION, max_network_retries=0,
                                http_client=stripe.RequestsClient(timeout=10))
    return client.v1.checkout.sessions.retrieve(config.session_id,
        {"expand": ["payment_intent.latest_charge"]}).to_dict()


def _assert_paid(session, expected):
    intent = session.get("payment_intent") or {}
    charge = intent.get("latest_charge") or {}
    three_ds = ((charge.get("payment_method_details") or {}).get("card") or {}).get("three_d_secure") or {}
    if (session.get("id") != expected or session.get("livemode") is not False
            or session.get("status") != "complete" or session.get("payment_status") != "paid"
            or session.get("currency") != "jpy" or session.get("amount_total") != 500
            or (session.get("metadata") or {}).get("purpose") != "circlematch_qa_only"
            or intent.get("livemode") is not False or intent.get("status") != "succeeded"
            or intent.get("amount_received") != 500 or intent.get("currency") != "jpy"
            or charge.get("livemode") is not False or charge.get("status") != "succeeded"
            or charge.get("paid") is not True or charge.get("amount") != 500
            or charge.get("captured") is not True or charge.get("amount_refunded") != 0
            or charge.get("payment_intent") != intent.get("id") or not intent.get("id")
            or charge.get("currency") != "jpy" or three_ds.get("result") != "authenticated"
            or three_ds.get("authentication_flow") != "challenge"):
        raise ValueError("sandbox_payment_not_verified")


def reconcile(*, config=None, path=None, retrieve=None):
    """Run explicitly from the private shell, never from a public request/worker."""
    config = config or settings()
    path = path or database_path(config)
    if not Path(path).exists():
        return {"verified": 0, "failed": 0}
    counts = {"verified": 0, "failed": 0}
    for _ in range(10):
        epoch = int(time.time())
        with closing(_connect(path)) as conn, conn:
            conn.execute("begin immediate")
            row = conn.execute("""select * from qa_receipts where processed_count=0
                and lease_until<=? and attempts<3 order by first_received limit 1""", (epoch,)).fetchone()
            if not row:
                break
            ident = row["event_id"]
            conn.execute("""update qa_receipts set state='processing',lease_until=?,attempts=attempts+1
                where event_id=?""", (epoch + 120, ident))
        try:
            _assert_paid((retrieve or _retrieve)(config), config.session_id)
        except Exception as exc:
            with closing(_connect(path)) as conn, conn:
                conn.execute("update qa_receipts set state='failed',lease_until=0,last_error=? where event_id=?",
                             (type(exc).__name__, ident))
            counts["failed"] += 1
            break
        with closing(_connect(path)) as conn, conn:
            conn.execute("""update qa_receipts set state='verified',processed_count=1,
                checked_at=?,lease_until=0,last_error='' where event_id=? and processed_count=0""",
                (int(time.time()), ident))
        counts["verified"] += 1
    return counts


def report(*, config=None, path=None):
    config = config or settings()
    path = path or database_path(config)
    if not Path(path).exists():
        return {"receipts": []}
    with closing(_connect(path)) as conn:
        rows = conn.execute("select * from qa_receipts order by first_received limit 20").fetchall()
    return {"receipts": [dict(r) for r in rows]}
