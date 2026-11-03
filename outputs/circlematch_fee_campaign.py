"""Organizer-fee rollout policy, stored in the existing app_state table."""

import json

from circlematch_payments import PaymentError, stamp

KEY = "organizer_fee_campaign:v1"
EVENT_PREFIX = "organizer_fee_publication:v1:"
REMOVED_HTTP_PATHS = frozenset({"/admin/payments/host-fees", "/api/payments/admin/host-fees/campaign"})


def _read(conn, key):
    row = conn.execute("select state_value from app_state where state_key=?", (key,)).fetchone()
    return json.loads(row[0]) if row else None


def _write(conn, key, value):
    conn.execute("""insert into app_state values(?,?,?) on conflict(state_key) do update
        set state_value=excluded.state_value,updated_at=excluded.updated_at""",
        (key, json.dumps(value, ensure_ascii=False, sort_keys=True), stamp()))


def status(conn):
    try:
        value = _read(conn, KEY)
        valid = value is None or (isinstance(value, dict) and type(value.get("enabled")) is bool
            and type(value.get("revision")) is int and value["revision"] >= 0)
    except (ValueError, TypeError):
        value, valid = None, False
    pending = conn.execute("select count(*) from host_fee_orders where active=1").fetchone()[0]
    enabled = bool(valid and value and value["enabled"])
    return dict(enabled=enabled, revision=value["revision"] if valid and value else 0,
                valid=valid, pending_checkouts=pending, stopping=not enabled and bool(pending),
                updated_at=value.get("updated_at") if valid and value else None)


def change(conn, data):
    if (not isinstance(data, dict) or set(data) != {"enabled", "revision", "accepted"}
            or type(data["enabled"]) is not bool or type(data["revision"]) is not int
            or type(data["accepted"]) is not bool or (data["enabled"] and not data["accepted"])):
        raise PaymentError("変更内容とON後の適用条件を確認してください")
    if not conn.in_transaction:
        conn.execute("begin immediate")
    previous = status(conn)
    if not previous["valid"] or data["revision"] != previous["revision"]:
        raise PaymentError("設定が更新されています。再読み込みして確認してください")
    if data["enabled"] and previous["stopping"]:
        raise PaymentError("既存決済画面の終了・照合待ちです。ONへ戻す前に確認してください")
    if previous["enabled"] == data["enabled"]:
        return previous
    _write(conn, KEY, dict(enabled=data["enabled"], revision=previous["revision"] + 1, updated_at=stamp()))
    if not data['enabled']:
        conn.execute('update host_fee_orders set next_sync_at=0 where active=1')
    return status(conn)


def publication(conn, event_id):
    try:
        value = _read(conn, EVENT_PREFIX + event_id) if event_id else None
        if value is not None and (not isinstance(value, dict) or type(value.get("waived")) is not bool
                or not isinstance(value.get("reason"), str)):
            return {"waived": True, "reason": "unverified"}
        return value
    except (ValueError, TypeError):
        return {"waived": True, "reason": "unverified"}


def terms(conn, event_id=""):
    frozen = publication(conn, event_id)
    if frozen:
        return frozen
    if event_id:
        event = conn.execute("select published_at,status from event_posts where event_id=?", (event_id,)).fetchone()
        if event and (event[0] or event[1] != "draft"):
            return {"waived": True, "reason": "existing"}
    return {"waived": not status(conn)["enabled"], "reason": "campaign"}


def freeze(conn, event_id):
    # Called in the publication transaction, never by a GET or later edit.
    if publication(conn, event_id) is None:
        current = status(conn)
        _write(conn, EVENT_PREFIX + event_id, dict(waived=not current["enabled"],
            reason="campaign" if not current["enabled"] else "standard",
            revision=current["revision"], published_at=stamp()))


def notice(conn, event_id="", *, compact=False):
    condition = terms(conn, event_id)
    if not condition["waived"]:
        return ""
    reason = "既存大会のため免除" if condition["reason"] == "existing" else "キャンペーン対象・主催者利用料0円"
    return ('<section class="host-fee-note" data-host-fee-private><h3>' + reason + '</h3>'
        '<p>この大会の主催者利用料は0円です。徴収を再開しても後から請求しません。</p>'
        '<p>参加者の参加費・振込・現地払いは変更ありません。</p></section>')
