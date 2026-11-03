"""Organizer-fee rollout policy, stored in the existing app_state table."""

import html
import json

from circlematch_payments import PaymentError, stamp

KEY = "organizer_fee_campaign:v1"
EVENT_PREFIX = "organizer_fee_publication:v1:"


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


def admin_page(state, csrf, readiness):
    import circlematch_payment_ui as payment_ui
    checked = " checked" if state["enabled"] else ""
    label = "ON / 新規公開分から10%" if state["enabled"] else "OFF / キャンペーン免除"
    warning = ('<p role="alert">既存決済画面の停止・照合待ち：' + str(state["pending_checkouts"])
        + '件。完了するまでONへ戻せません。結果不明の支払いは再請求しないでください。</p>') if state["stopping"] else ""
    checks = ''.join('<li>' + html.escape(item["label"]) + '：' + ('設定済み' if item["ok"] else '未設定・要確認') + '</li>'
                     for item in readiness)
    body = ('<section class="payment-shell"><a href="/admin/payments">決済運営管理へ</a>'
        '<h1>主催者利用料</h1><p id="campaignStatus" role="status">' + label + '</p>' + warning
        + '<form id="feeCampaignForm"><label class="campaign-switch"><input id="campaignEnabled" type="checkbox" role="switch"'
        + checked + '><span>主催者利用料の徴収</span></label>'
        '<p>ONにした後で新規公開し、主催者が条件に同意した大会だけが対象です。'
        '開催確定後、入金確認済み参加費売上の10%を主催者が支払います。</p>'
        '<p>OFF中の公開分・既存大会・今回の駒沢大会は免除を継続します。参加者の支払方法とConnect受付は変更しません。</p>'
        '<label class="payment-consent" id="campaignConsent"><input id="campaignAccepted" type="checkbox">'
        'ON後に新規公開する大会への10%徴収開始を確認しました</label>'
        '<button class="button primary" type="submit">変更を保存</button><p id="campaignError" role="alert" hidden></p></form>'
        '<h2>接続設定</h2><ul>' + checks + '</ul><p>OFFにしても既存の入金・Webhook照合は継続します。'
        '既存の未完了決済は終了を確認するまで停止処理中になります。支払い済みの自動返金は行いません。</p></section>')
    script = '''<style>.campaign-switch{display:flex;gap:12px;align-items:center;font-weight:700;min-height:48px}
.campaign-switch input{appearance:auto;width:24px;height:24px;accent-color:#187551;flex:0 0 24px}
#campaignStatus{font-weight:700}#campaignError{color:#b42318;overflow-wrap:anywhere}</style><script>(()=>{
const form=document.getElementById('feeCampaignForm'),toggle=document.getElementById('campaignEnabled'),
consent=document.getElementById('campaignConsent'),accepted=document.getElementById('campaignAccepted'),error=document.getElementById('campaignError');
const update=()=>{consent.hidden=!toggle.checked;accepted.required=toggle.checked;accepted.checked=false};toggle.onchange=update;update();
form.onsubmit=async e=>{e.preventDefault();if(!form.reportValidity()||form.dataset.busy)return;
form.dataset.busy='1';const button=form.querySelector('button');button.disabled=true;error.hidden=true;
try{const response=await fetch('/api/payments/admin/host-fees/campaign',{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':__CSRF__},
body:JSON.stringify({enabled:toggle.checked,revision:__REVISION__,accepted:accepted.checked})});const data=await response.json();
if(!response.ok)throw Error(data.error||'設定を保存できませんでした');location.reload()}
catch(e){error.textContent=e.message;error.hidden=false;delete form.dataset.busy;button.disabled=false}};
if(__STOPPING__)setTimeout(()=>location.reload(),15000);
})();</script>'''.replace('__CSRF__', json.dumps(csrf)).replace('__REVISION__', str(state["revision"])).replace('__STOPPING__', json.dumps(state["stopping"]))
    return body, payment_ui.script(csrf) + script
