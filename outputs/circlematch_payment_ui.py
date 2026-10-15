"""Server-rendered payment screens, using the existing Circle Match page shell."""

import html
import json
from urllib.parse import quote

from circlematch_payments import PaymentError, quote_price

STATES = {"creating":"決済画面を準備中", "open":"支払い待ち", "paid":"支払確認済み",
          "expired":"決済画面終了・未払い", "review":"要確認", "none":"なし",
          "requested":"返金申請中", "processing":"返金処理中", "succeeded":"全額返金処理済み",
          "failed":"失敗・要対応", "partial":"一部返金・要確認", "retry":"再処理待ち",
          "queued":"処理待ち", "done":"処理済み", "incomplete":"登録途中",
          "reviewing":"確認中", "ready":"利用可能", "action_required":"追加対応が必要", "restricted":"制限中"}


def esc(value):
    return html.escape(str(value if value is not None else ""), quote=True)


def money(value):
    return "未確定" if value is None else f"{value:,}円"


def action(path, label, fields="", values=None, confirm=False):
    hidden = ''.join(f'<input type="hidden" name="{esc(k)}" value="{esc(v)}">' for k,v in (values or {}).items())
    check = '<label class="payment-consent"><input type="checkbox" name="accepted" required> 内容・総額・キャンセル条件を確認しました</label>' if confirm else ''
    return f'<form data-pay="{esc(path)}">{hidden}{fields}{check}<button class="button primary" type="submit">{esc(label)}</button><p role="alert" class="error-box" hidden></p></form>'


def details(values):
    return '<dl class="payment-details">'+''.join(f'<div><dt>{esc(k)}</dt><dd>{esc(v)}</dd></div>' for k,v in values)+'</dl>'


def script(csrf):
    return r'''<style>
.payment-shell{max-width:820px;margin:24px auto;padding:0 4px;overflow-wrap:anywhere}
.payment-shell h1{font-size:28px}.payment-shell h2{font-size:21px;margin-top:28px}
.payment-shell p,.payment-shell label{font-size:16px;line-height:1.7}
.payment-shell form{margin:18px 0}.payment-shell button{min-height:48px;max-width:100%;white-space:normal}
.payment-shell textarea{display:block;width:100%;max-width:100%;min-height:90px;margin:8px 0}
.payment-details{margin:20px 0}.payment-details>div{display:grid;grid-template-columns:180px minmax(0,1fr);gap:16px;padding:12px 0;border-bottom:1px solid #dce2e8}
.payment-details dt{color:#4a5968}.payment-details dd{margin:0;font-weight:600;white-space:pre-wrap}
.payment-total{font-size:24px!important;font-weight:800}.payment-consent{display:flex;gap:12px;margin-bottom:18px;align-items:flex-start}
.payment-consent input{width:22px;height:22px;flex:0 0 22px;margin-top:4px}
.payment-order{border-bottom:1px solid #dce2e8;padding:18px 0}.payment-order h2{margin:0;font-size:19px}
@media(max-width:600px){.payment-shell{margin:16px 0}.payment-shell h1{font-size:24px}.payment-details>div{grid-template-columns:1fr;gap:4px}.payment-shell form>.button{width:100%}}
</style><script>
document.querySelectorAll('form[data-pay]').forEach(form=>form.onsubmit=async e=>{
 e.preventDefault();if(!form.reportValidity()||form.dataset.busy)return;
 const button=form.querySelector('button'),error=form.querySelector('[role=alert]');
 const data=Object.fromEntries(new FormData(form));if('accepted' in data)data.accepted=true;
 form.dataset.busy='1';button.disabled=true;error.hidden=true;
 try{const response=await fetch(form.dataset.pay,{method:'POST',headers:{'Content-Type':'application/json','X-CSRF-Token':__CSRF__},body:JSON.stringify(data)});
 const result=await response.json();if(!response.ok)throw Error(result.error||'通信に失敗しました。支払状態を再確認してください');
 if(result.connection_status){
   const output=document.getElementById('payment-connection-status');output.replaceChildren();
   result.connection_status.checks.forEach(check=>{const row=document.createElement('p');row.textContent=check.label+'：'+(check.ok?'確認済み':'未完了・要確認');output.append(row)});
   if(!result.connection_status.stripe_checked){const row=document.createElement('p');row.textContent='Stripe APIの状態は未確認です。接続設定を完了して再確認してください。';output.append(row)}
   delete form.dataset.busy;button.disabled=false;
 }else if(result.url)location.assign(result.url);else location.reload();
 }catch(err){error.hidden=false;error.textContent=err.message;delete form.dataset.busy;button.disabled=false}
});</script>'''.replace("__CSRF__", json.dumps(csrf))


def render(service, kind, identifier, user, page, csrf, admin=False):
    uid = user.get("user_id", "admin")
    body = '<nav><a href="/mypage">マイページ</a> / <a href="/payments">オンライン決済</a></nav>'
    if service.config.mode == "test":
        body += '<p class="notice">テストモードです。実際の請求・銀行送金は行いません。</p>'
    if kind == "connect":
        title = "売上の受取設定"
        account = service.account_row(uid)
        state = account["state"] if account else "incomplete"
        body += '<h1>'+title+'</h1><p>現在の状態：'+esc(STATES.get(state,state))+'</p>'
        body += '<p>本人確認・銀行口座はStripeの画面で登録します。戻ってきた場合も、利用状態の確認が必要です。</p>'
        if service.config.enabled:
            body += action("/api/payments/connect/onboard","Stripeで受取設定を進める")
        else:
            body += '<p>新しいオンライン決済・受取設定の受付は停止中です。</p>'
        if account and account["account_id"]:
            body += action("/api/payments/connect/refresh","利用状態を確認する")
        body += '<p>分配先はログイン中の主催者本人の口座です。サークルDBの掲載とは別の設定です。Stripe残高への分配と銀行への入金は異なり、入金日程はStripeの設定に従います。</p>'
    elif kind == "applications":
        title = "お支払い内容の確認"
        with service.connect() as conn:
            app,event = service.load_application(conn,identifier,uid)
            existing = conn.execute("select order_id from payment_orders where application_id=? and (active=1 or paid_at is not null) order by paid_at is not null desc",(identifier,)).fetchone()
            if existing:
                return render(service,"orders",existing[0],user,page,csrf)
            try:
                amounts,_ = service.payable(conn,app,event)
                error = ""
            except PaymentError as exc:
                amounts = quote_price(event["fee_amount"] or 0,quantity=1 if event["fee_unit"]=="1チーム" else app["participant_count"])
                error = str(exc)
        snap = service.snapshot(app,event,amounts)
        body += '<h1>'+title+'</h1>'+recap(snap)
        if error:
            body += '<p class="error-box">'+esc(error)+'</p><p><a href="/events/'+quote(event["event_id"])+'/attendance">開催案内・最終参加確認へ</a></p>'
        elif not service.config.enabled:
            body += '<p class="error-box">オンライン決済の新規受付は停止中です。主催者へご連絡ください。</p>'
        elif amounts["gross"]:
            body += action("/api/payments/applications/"+quote(identifier)+"/checkout","Stripeの支払確定画面へ進む",
                           values={"quote_token":service.quote_token(snap)},confirm=True)
            body += '<p>次のStripe画面で「支払う」を押すとカード決済を実行します。この画面ではまだ支払いは確定しません。</p>'
        else:
            body += '<p>参加費は0円です。カード決済は不要です。</p>'
    elif kind == "orders":
        title = "オンライン決済の確認"
        order = service.order(identifier,uid,admin)
        snap = json.loads(order["snapshot_json"])
        body += '<h1>'+title+'</h1><p><strong>'+esc(STATES.get(order["state"],order["state"]))+'</strong></p>'
        if not order["paid_at"]:
            body += '<p>決済画面から戻っただけでは支払完了になりません。未反映の場合は確認を更新してください。</p>'
        if order["needs_review"]:
            body += '<p class="error-box">運営による照合が必要です。重ねて支払わず、主催者へご連絡ください。</p>'
        if order["refund_state"] != "none":
            body += '<p>返金状況：'+esc(STATES.get(order["refund_state"],order["refund_state"]))+' / 確認した返金額：'+money(order["refund_amount"])+'</p>'
            body += '<p>返金申請と返金完了は異なります。カード明細への反映にはカード会社側の時間がかかります。</p>'
        if order["dispute_state"] != "none":
            body += '<p class="error-box">カード支払いの異議申立てあり。通常の返金は停止しています。</p>'
        body += recap(snap)
        prefix = "/api/payments/"+("admin/" if admin else "")+"orders/"+quote(identifier)
        body += action(prefix+"/reconcile","支払・返金状態を更新する")
        if order["state"] in {"creating","open"} and not order["paid_at"]:
            if uid == order["payer_id"] and service.config.enabled:
                body += action(prefix+"/resume","同じ決済画面を開く")
            body += action(prefix+"/expire","決済画面を終了する")
            body += '<p>人数変更・申込取消の前に、決済画面の終了を確認します。支払完了と同時だった場合は返金申請が必要です。</p>'
        owner = admin or uid == order["organizer_id"]
        if (order["paid_at"] and order["dispute_state"] == "none"
                and (order["refund_state"] == "none" or (owner and order["refund_state"] == "requested"))):
            body += action(prefix+("/refund-approve" if owner else "/refund"),"全額返金を承認・処理待ちにする" if owner else "全額返金を申請する",
                           '<label>返金理由<textarea name="reason" maxlength="500" required></textarea></label>',confirm=True)
        if admin or uid == order["organizer_id"]:
            body += '<h2>主催者向け内訳</h2>'+details([("支払総額",money(order["gross"])),("サービス利用料",money(order["fee"])),("分配見込額",money(order["net"])),
              ("Stripe分配実績（銀行入金ではありません）",money(None if order["transfer_amount"] is None else order["transfer_amount"]-order["fee"]+order["fee_refunded"]-(order["transfer_reversed"] or 0)))])
        body += '<p><a href="/events/'+quote(order["event_id"])+('/applications' if uid == order["organizer_id"] else '/applications/'+quote(order["application_id"]))+'">申込管理へ</a></p>'
    elif kind == "cancel":
        title = "開催中止・返金対象の確認"
        summary = service.cancellation_preview(identifier,uid)
        body += '<h1>'+title+'</h1>'+details([("返金対象",str(summary["count"])+"件"),("未返金総額",money(summary["gross"]))])
        body += '<p>中止を確定すると、全額返金の処理を予約します。完了まで「返金処理中」と表示します。決済中の注文がある場合は先に決済画面を終了してください。部分返金・紛争のある注文は運営の確認対象になります。</p>'
        body += action("/api/payments/events/"+quote(identifier)+"/cancel","開催を中止して返金処理を予約する",values={"refund_token":summary["token"]},confirm=True)
    else:
        title = "決済運営管理" if admin else "オンライン決済"
        body += '<h1>'+title+'</h1>'
        if admin:
            status = service.connection_status()
            body += '<h2>オンライン決済の接続確認</h2><p>新規受付：'+('有効' if status['enabled'] else '停止中')+'</p>'
            body += '<div id="payment-connection-status" role="status">'+''.join('<p>'+esc(check['label'])+'：'+('設定済み' if check['ok'] else '未設定・要確認')+'</p>' for check in status['checks'])+'</div>'
            body += action('/api/payments/admin/connection-status','Stripeの利用状態を確認する')
            body += '<p>この確認では課金・送金は行いません。Webhookの実配信、主催者の受取設定、テスト決済の完了は別途確認が必要です。</p>'
            body += '<p><a href="https://dashboard.stripe.com/account/status" target="_blank" rel="noopener noreferrer">Stripeの必須タスクを確認する</a></p>'
        if not admin:
            body += '<p><a class="button" href="/payments/connect">売上の受取設定</a></p>'
        with service.connect() as conn:
            scope = "mode=? and platform=?"
            args = [service.config.mode,service.config.platform]
            if not admin:
                scope += " and (payer_id=? or organizer_id=?)"
                args.extend([uid,uid])
            orders = [dict(r) for r in conn.execute("select * from payment_orders where "+scope+" order by created_epoch desc,order_id desc limit 200",args)]
            host_scope = "mode=? and platform=?"+("" if admin else " and organizer_id=?")
            host_args = args[:2]+([] if admin else [uid])
            totals = conn.execute("""select sum(case when paid_at is not null then gross else 0 end) as gross,
              sum(case when paid_at is not null then fee else 0 end) as fee,
              sum(fee_refunded) as fee_refunded, sum(refund_amount) as refunds,
              sum(case when paid_at is null and state in ('creating','open') then 1 else 0 end) as unpaid,
              sum(case when paid_at is not null then 1 else 0 end) as paid,
              sum(case when refund_state!='none' or needs_review=1 or dispute_state!='none' then 1 else 0 end) as review,
              sum(processor_fee) as processor_fee,
              sum(case when paid_at is not null and processor_fee is null then 1 else 0 end) as cost_unknown
              from payment_orders where """+host_scope,host_args).fetchone()
            unpaid = conn.execute("""select count(*) from event_applications a join event_posts e on e.event_id=a.event_id
              where e.payment_method='online' and e.status in ('published','closed') and a.status='confirmed'
              and not exists(select 1 from payment_orders o where o.application_id=a.application_id and o.paid_at is not null)"""
              +("" if admin else " and e.organizer_user_id=?"),([] if admin else [uid])).fetchone()[0]
            accounts = [dict(r) for r in conn.execute("select user_id,state,checked_at from payment_accounts where mode=? and platform=?",args[:2])] if admin else []
            hooks = [dict(r) for r in conn.execute("select event_id,state,last_error from payment_webhooks where mode=? and platform=? and state!='done' order by created_at limit 100",args[:2])] if admin else []
            pending = [dict(r) for r in conn.execute("""select a.application_id,e.title from event_applications a join event_posts e on e.event_id=a.event_id
              where a.applicant_user_id=? and e.payment_method='online' and a.status in ('confirmed','pending')
              and not exists(select 1 from payment_orders o where o.application_id=a.application_id and (o.active=1 or o.paid_at is not null)) limit 100""",(uid,))] if not admin else []
        body += '<h2>'+('運営集計' if admin else '主催するイベントの集計')+'</h2>'+details([
          ("取扱高（確認済み支払総額）",money(totals["gross"] or 0)),("サービス利用料",money(totals["fee"] or 0)),
          ("返金したサービス利用料",money(totals["fee_refunded"] or 0)),("返金処理済み総額",money(totals["refunds"] or 0)),
          ("分配見込額（返金前）",money((totals["gross"] or 0)-(totals["fee"] or 0))),
          ("未払いの受付確定申込 / 支払確認済み / 返金・要対応",f'{unpaid}件 / {totals["paid"] or 0}件 / {totals["review"] or 0}件')])
        if admin:
            body += details([("取得済みの決済処理費",money(totals["processor_fee"])),("決済処理費が未確定の注文",str(totals["cost_unknown"] or 0)+"件")])
            body += '<p>取扱高・利用料は利益ではありません。Connect・振込・紛争等の別途費用はStripeの請求明細との照合が必要です。</p>'
        for item in pending:
            body += '<article class="payment-order"><h2>'+esc(item["title"])+'</h2><a class="button" href="/payments/applications/'+quote(item["application_id"])+'">参加費・支払条件を確認する</a></article>'
        body += '<h2>注文履歴（最新200件）</h2>'
        for order in orders:
            snapshot = json.loads(order["snapshot_json"])
            body += '<article class="payment-order"><h2>'+esc(snapshot["title"])+'</h2><p>'+money(order["gross"])+' / '+esc(STATES.get(order["state"],order["state"]))+' / 返金：'+esc(STATES.get(order["refund_state"],order["refund_state"]))+'</p><a class="button" href="'+('/admin' if admin else '')+'/payments/orders/'+quote(order["order_id"])+'">決済の詳細を確認する</a></article>'
        if not orders:
            body += '<p>オンライン決済履歴はありません。</p>'
        if admin:
            body += '<h2>受取設定</h2>'+''.join('<p>'+esc(a["user_id"])+': '+esc(STATES.get(a["state"],a["state"]))+'</p>' for a in accounts)
            body += '<h2>未処理・失敗Webhook</h2>'
            for hook in hooks:
                body += '<p>'+esc(hook["event_id"])+': '+esc(hook["state"])+" / "+esc(hook["last_error"])+'</p>'
                body += action('/api/payments/admin/webhooks/'+quote(hook["event_id"])+"/replay","通知を再処理する")
    return page(title,'<section class="payment-shell">'+body+'</section>',script(csrf))


def recap(snap):
    return ('<h2>'+esc(snap["title"])+'</h2>'+details([
        ("主催者",snap["organizer_name"]),("開催日時",snap["starts_at"]),("会場",snap["prefecture"]+" / "+snap["location"]),
        ("参加費単価",money(snap["unit_amount"])+" / "+snap["fee_unit"]),
        ("課金数量",str(snap["quantity"])+("チーム" if snap["fee_unit"]=="1チーム" else "人")),
        ("単価 × 数量",money(snap["unit_amount"])+" × "+str(snap["quantity"])),
        ("支払期限",snap["payment_deadline"] or snap["starts_at"])])+
        '<p class="payment-total">お支払総額：'+money(snap["gross"])+'</p><p>サービス利用料込み・追加手数料なし</p>'+
        '<details><summary>サービス利用料について</summary><p>参加費総額の10％（1円未満切り上げ）を主催者への分配前に控除します。決済処理費とサイト利用料に係る消費税を含み、別途の追加請求はありません。</p></details>'+
        '<h2>キャンセル・返金条件</h2><p style="white-space:pre-wrap">'+esc(snap["cancellation_policy"])+
        '</p><p>'+esc(snap["refund_policy"])+'</p>')
