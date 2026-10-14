"""Pure, escaped invitation fragments for the native Circle Match page shell.

The calling application owns authorization, persistence, headers and page wrapping.
No database access, network requests or account identifiers belong in this module.
"""
from datetime import datetime, timedelta, timezone
from html import escape
from urllib.parse import quote, urlencode, urlsplit


STATUS_LABELS = {
    "pending": "未回答", "interested": "相談を進めたい", "declined": "今回は見送る",
    "withdrawn": "取り下げ済み", "expired": "有効期限切れ",
}
ACTIVITIES = ("練習試合", "合同練習", "交流", "その他")
INVITATION_KINDS = {"event": "イベントへの招待", "consultation": "交流の相談"}


def _s(value):
    return "" if value is None else str(value)


def _e(value):
    return escape(_s(value), quote=True)


def _path(invitation_id):
    return "/invitations/" + quote(_s(invitation_id), safe="")


def _href(value, external=False):
    value = _s(value).strip()
    if not value or any(ord(char) < 32 for char in value) or "\\" in value:
        return ""
    if value.startswith("/") and not value.startswith("//"):
        return value
    if external:
        try:
            parsed = urlsplit(value)
            if parsed.scheme in {"http", "https"} and parsed.hostname and not parsed.username and not parsed.password:
                return value
        except ValueError:
            pass
    return ""


def _origin(value):
    try:
        parsed = urlsplit(_s(value))
        if parsed.scheme in {"http", "https"} and parsed.hostname and not parsed.username and not parsed.password:
            return parsed.scheme + "://" + parsed.netloc
    except ValueError:
        pass
    return ""


def _when(value):
    original = _s(value)
    try:
        parsed = datetime.fromisoformat(original.strip())
        jst = timezone(timedelta(hours=9))
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=jst)
        return _e(parsed.astimezone(jst).strftime("%Y/%m/%d %H:%M") + "（日本時間）")
    except (ValueError, OverflowError):
        return _e(original)


def _status(value):
    return STATUS_LABELS.get(value, "状態を確認")


def _contact(target, subject='', body=''):
    email = _s(target.get('public_contact_email'))
    method = _s(target.get('contact_method'))
    contact_url = _href(target.get('contact_url'), external=True)
    source = _href(target.get('contact_source_url') or target.get('source_url'), external=True)
    if email:
        href = 'mailto:' + quote(email, safe='@') + '?' + urlencode({'subject': subject, 'body': body}, quote_via=quote)
        result = '<p class="invite-help">公開連絡先：' + _e(email) + '</p><p class="invite-help">' + _e(target.get('contact_purpose') or '団体が公開した連絡先') + '</p>'
        if body:
            result += '<a class="invite-button invite-primary" href="' + _e(href) + '">招待メールを作成</a><p class="invite-help">メールアプリで宛先と文面を確認して送信してください。この画面では送信されません。</p>'
    elif contact_url and method in {'form', 'line'}:
        label = '問い合わせフォームを開く' if method == 'form' else '公式LINEの案内を見る'
        result = '<p class="invite-help">' + _e(target.get('contact_purpose') or '団体が案内する公開窓口') + '</p>'
        result += '<a class="invite-button invite-primary" href="' + _e(contact_url) + '" target="_blank" rel="noopener noreferrer">' + label + ' ↗</a>'
        if body:
            result += '<p class="invite-help">下の招待文をコピーし、相手先の窓口で用途を確認してから送ってください。この画面では送信されません。</p>'
    else:
        result = '<p class="invite-help">確認済みの公開連絡窓口はまだありません。掲載元で現在の連絡方法を確認してください。</p>'
    if source and source != contact_url:
        result += '<a class="invite-text-link" href="' + _e(source) + '" target="_blank" rel="noopener noreferrer">' + ('連絡先の掲載元' if email else '掲載元を確認') + ' ↗</a>'
    if target.get('contact_checked_at'):
        result += '<p class="invite-help">掲載確認：' + _e(target['contact_checked_at']) + '（到達・招待受入は未確認）</p>'
    return result


def _back(target=None):
    query = {"tab": "db"}
    for key in ("sport", "prefecture"):
        value = (target or {}).get("sport_category" if key == "sport" else key)
        if value:
            query[key] = value
    return '<nav class="invite-nav" aria-label="招待のナビゲーション"><a href="/?' + _e(urlencode(query)) + '">サークルDBへ</a><a href="/invitations">招待一覧</a></nav>'


def _start(title, intro, target=None):
    return CSS + '<section class="invite-ui" id="invite-root">' + _back(target) + '<header class="invite-heading"><p class="invite-eyebrow">CIRCLE MATCH INVITATION</p><h1>' + _e(title) + '</h1><p>' + _e(intro) + '</p></header>'


def _error():
    return '<div id="invite-error" class="invite-error" role="alert" tabindex="-1" hidden></div>'


def _no_script():
    return '<noscript><p class="invite-note">招待の作成・返信にはJavaScriptを有効にしてください。招待内容や共有する文面は、このページで確認できます。</p></noscript>'


def _form(action, fields, submit, extra=""):
    return ('<form class="invite-form" data-invite-action="' + _e(action) + '" ' + extra + '>'
            '<fieldset disabled>' + fields + '<div class="invite-actions"><button class="invite-button invite-primary" type="submit">'
            + _e(submit) + '</button></div></fieldset></form>')


def _field(name, label, value="", limit=240, required=False, multiline=False, help_text="", placeholder=""):
    identity = "invite-" + name.replace("_", "-")
    attrs = ' id="' + identity + '" name="' + name + '" maxlength="' + str(limit) + '"'
    attrs += ' required' if required else ''
    if help_text:
        attrs += ' aria-describedby="' + identity + '-help"'
    if placeholder:
        attrs += ' placeholder="' + _e(placeholder) + '"'
    control = ('<textarea' + attrs + ' rows="5">' + _e(value) + '</textarea>' if multiline
               else '<input type="text"' + attrs + ' value="' + _e(value) + '">')
    return ('<div class="invite-field"><label for="' + identity + '">' + _e(label) + '</label>' + control
            + ('<p class="invite-help" id="' + identity + '-help">' + _e(help_text) + '</p>' if help_text else '') + '</div>')


def compose(target, events, user):
    """Compose an event invitation or an individual exchange consultation."""
    target = target or {}
    events = [event for event in (events or []) if isinstance(event, dict)]
    name = target.get("circle_name") or "この団体"
    body = _start("交流相手への招待を作成", "内容を決めて招待リンクを作成し、メールやSNSで相手へ渡せます。", target)
    context = " · ".join(_s(target.get(key)) for key in ("university_name", "prefecture", "sport_category") if target.get(key))
    body += '<section class="invite-card"><p class="invite-label">招待したい相手</p><h2>' + _e(name) + '</h2><p class="invite-help">' + _e(context) + '</p>'
    profile = _href(target.get("profile_url"))
    source = _href(target.get("source_url"), external=True)
    if profile:
        body += '<a class="invite-text-link" href="' + _e(profile) + '">団体の紹介を確認する</a>'
    elif source:
        body += '<a class="invite-text-link" href="' + _e(source) + '" target="_blank" rel="noopener noreferrer">公開情報を確認する ↗</a>'
    body += _contact(target)
    body += '</section><section class="invite-card"><h2>招待の内容</h2>' + _error() + _no_script()
    fields = '<input type="hidden" name="target_circle_id" value="' + _e(target.get("circle_id")) + '">'
    fields += '<div class="invite-field"><p class="invite-label" id="invite-kind-label">招待の種類</p><div class="invite-choices" role="group" aria-labelledby="invite-kind-label"><label><input type="radio" name="kind" value="consultation" checked>交流の相談</label><label><input type="radio" name="kind" value="event"' + ('' if events else ' disabled') + '>自分のイベントに招待</label></div></div>'
    options = '<option value="">イベントを選んでください</option>' + ''.join('<option value="' + _e(event.get("event_id")) + '">' + _e(event.get("title")) + (' / ' + _when(event.get("starts_at")) if event.get("starts_at") else '') + '</option>' for event in events)
    fields += '<div id="invite-event-panel" class="invite-field" hidden><label for="invite-event">招待するイベント（必須）</label><select id="invite-event" name="event_id" disabled>' + options + '</select><p class="invite-help">自分が公開している、開催前のイベントから選べます。</p></div>'
    if not events:
        event_query = {"sport": target["sport_category"]} if target.get("sport_category") else {}
        event_url = "/events/new" + ("?" + urlencode(event_query) if event_query else "")
        fields += '<p class="invite-help">招待できる公開イベントがまだありません。<a href="' + _e(event_url) + '">イベントを作成する</a>か、交流の相談から始められます。</p>'
    fields += _field("sender_label", "相手に公開する名前・団体名（必須）", limit=80, required=True,
                     help_text="招待リンクを開いた相手に表示されます。活動名や団体名など、公開してよい名前を入力してください。", placeholder="例：〇〇大学テニスサークル")
    fields += _field("subject", "件名（必須）", _s(target.get("sport_category") or "交流") + "の交流のご相談", limit=120, required=True)
    fields += '<div class="invite-field"><label for="invite-activity">希望する活動</label><select id="invite-activity" name="activity">' + ''.join('<option value="' + _e(activity) + '">' + _e(activity) + '</option>' for activity in ACTIVITIES) + '</select></div>'
    fields += '<div class="invite-two-columns">' + _field("proposed_date", "希望日時（任意）", placeholder="例：11月の土日、ご相談して決めたい") + _field("location", "希望する場所（任意）", placeholder="例：東京都内、場所は相談可") + '</div>'
    fields += _field("body", "相手へのメッセージ（必須）", "はじめまして。Circle Matchで活動情報を拝見しました。\nぜひ一緒に活動できればと思い、ご相談しました。\nご都合やご希望をお聞かせください。", limit=2000, required=True, multiline=True,
                     help_text="この内容は招待リンクを開いた人が読めます。個人の電話番号や非公開の情報は含めないでください。")
    fields += '<p class="invite-note">リンクの作成後、共有する文面をコピーできます。相手の返信から日程や内容の相談を始めましょう。</p>'
    body += _form("create", fields, "招待リンクを作成", 'data-invite-endpoint="/api/invitations"') + '</section></section>'
    return body, SCRIPT


def _shared_url(data, origin):
    origin = _origin(origin)
    supplied = _href(data.get("share_url"), external=True)
    if supplied.startswith("/"):
        return origin + supplied if origin else supplied
    if supplied and origin and _origin(supplied) == origin:
        return supplied
    return origin + _path(data.get("invitation_id"))


def _share_text(data, share_url):
    lines = [_s(data.get("target_circle_name") or "ご担当者") + "の皆さまへ", "",
             _s(data.get("sender_label")) + "からのお誘いです。", _s(data.get("subject")), "",
             _s(data.get("body"))]
    for label, key in (("希望する活動", "activity"), ("希望日時", "proposed_date"), ("希望する場所", "location")):
        if data.get(key):
            lines.append(label + "：" + _s(data[key]))
    if data.get("kind") == "event" and data.get("event_title"):
        lines.append("イベント：" + _s(data["event_title"]))
    lines += ["", "Circle Matchで作成した交流のご相談です。", "内容の確認・返信はこちら", share_url]
    return "\n".join(lines)


def detail(data, user, origin):
    """Public initial preview, sender sharing and private two-person follow-up."""
    data, user = data or {}, user or {}
    path = _path(data.get("invitation_id"))
    status = data.get("status", "pending")
    authenticated = bool(user.get("authenticated"))
    sender = authenticated and bool(data.get("is_sender"))
    recipient = authenticated and bool(data.get("is_recipient"))
    party = sender or recipient
    active = status in {"pending", "interested", "declined"}
    body = _start(data.get("subject") or "交流への招待", "招待の内容を確認して、活動の相談を始めましょう。")
    body += '<section class="invite-card"><div class="invite-card-top"><span class="invite-kind">' + _e(INVITATION_KINDS.get(data.get("kind"), "交流への招待")) + '</span><span class="invite-status">' + _e(_status(status)) + '</span></div>'
    body += '<p class="invite-recipient">' + _e(data.get("target_circle_name") or "招待先の団体") + 'へのお誘い</p><p class="invite-from">' + _e(data.get("sender_label") or "招待を作成した人") + 'より</p>'
    body += '<p class="invite-prose">' + _e(data.get("body")) + '</p><dl class="invite-facts">'
    for label, key in (("希望する活動", "activity"), ("希望日時", "proposed_date"), ("希望する場所", "location")):
        if data.get(key):
            body += '<dt>' + label + '</dt><dd>' + _e(data[key]) + '</dd>'
    if data.get("expires_at"):
        body += '<dt>招待の有効期限</dt><dd>' + _when(data["expires_at"]) + '</dd>'
    body += '</dl>'
    if data.get("kind") == "event":
        event_url = _href(data.get("event_url"))
        body += '<div class="invite-event-summary"><p class="invite-label">招待されているイベント</p><p>' + _e(data.get("event_title") or "イベント") + '</p>'
        if event_url and data.get("event_available"):
            body += '<a class="invite-text-link" href="' + _e(event_url) + '">イベントの詳細・参加条件を確認する</a>'
        else:
            body += '<p class="invite-help">このイベントは現在、参加受付の対象外です。招待への返信とイベントへの参加申込はそれぞれのページで確認してください。</p>'
        body += '</div>'
    body += '</section>' + _error() + _no_script()
    if sender and active:
        share_url = _shared_url(data, origin)
        share_text = _share_text(data, share_url)
        body += '<section class="invite-card"><h2>相手の連絡窓口</h2>' + _contact(data.get('contact') or {}, data.get('subject') or 'Circle Matchから交流のご相談', share_text) + '</section>'
        line_text = _s(data.get("target_circle_name") or "ご担当者") + "の皆さまへ\n" + _s(data.get("sender_label")) + "より：" + _s(data.get("subject"))
        line_url = "https://social-plugins.line.me/lineit/share?" + urlencode({"url": share_url, "text": line_text})
        body += '<section class="invite-card"><h2>招待を相手へ渡す</h2><p>招待リンクを作成しました。下の文面をメールやSNSのメッセージに貼り付けて、相手へ渡せます。</p><div class="invite-field"><label for="invite-share-text">相手へ渡す招待文</label><textarea id="invite-share-text" rows="8" readonly>' + _e(share_text) + '</textarea></div><div class="invite-actions"><button class="invite-button invite-primary" type="button" id="invite-copy" disabled>招待文とリンクをコピー</button><a class="invite-button" href="' + _e(line_url) + '" target="_blank" rel="noopener noreferrer">LINEで渡す ↗</a></div><p id="invite-copy-status" class="invite-help" role="status" aria-live="polite"></p><div class="invite-field"><label for="invite-share-url">招待リンク</label><input id="invite-share-url" type="url" value="' + _e(share_url) + '" readonly></div><p class="invite-note">リンクを受け取った人は招待内容を確認できます。返信できるのは、最初にログインして本人として回答した1人です。</p></section>'
    can_respond = bool(data.get("can_respond")) and user.get("authenticated") and not sender and active
    if can_respond:
        body += '<section class="invite-card"><h2>この招待に返信する</h2><p class="invite-note">個人としてのお返事です。団体代表者の確認、参加申込、席の確保、費用のお約束は別途行ってください。</p>'
        fields = _field("display_name", "相手に公開する名前（必須）", limit=80, required=True,
                        help_text="この招待を作成した人に表示されます。公開してよい名前を入力してください。")
        fields += '<div class="invite-field"><p class="invite-label" id="invite-response-label">お返事（必須）</p><div class="invite-choices" role="group" aria-labelledby="invite-response-label"><label><input type="radio" name="response" value="interested" required>興味があります・相談したい</label><label><input type="radio" name="response" value="declined">今回は見送ります</label></div></div>'
        fields += _field("body", "ひとこと（任意）", limit=2000, multiline=True, placeholder="希望の日程や質問があれば、こちらにどうぞ。")
        fields += '<label class="invite-confirm"><input type="checkbox" name="affiliation_confirmed" required><span>私はこの団体の活動に関わる本人として返信します。</span></label><p class="invite-help">返信後のやり取りは、招待を作成した人とあなたの間だけに表示されます。</p>'
        body += _form("respond", fields, "返信する", 'data-invite-endpoint="/api' + _e(path) + '/respond"') + '</section>'
    elif not user.get("authenticated") and active and data.get("can_respond"):
        login = "/signin?" + urlencode({"return_to": path})
        body += '<section class="invite-card"><h2>お返事はこちら</h2><p>ログインすると、ご本人としてお返事できます。</p><a class="invite-button invite-primary" href="' + _e(login) + '">ログインして返信する</a><p class="invite-help">団体の代表者確認やイベントへの参加確定は、別途行ってください。</p></section>'
    elif not party and active:
        body += '<section class="invite-card"><h2>このリンクからの新しい返信はできません</h2><p>この招待には、すでに別の方が返信しています。招待を作成した人に新しい招待リンクをご相談ください。</p></section>'
    elif not active:
        body += '<p class="invite-note">この招待の受付は終了しています。新しい相談は、招待を作成した人にご確認ください。</p>'
    if party:
        body += '<section class="invite-card"><h2>二人のやり取り</h2><p class="invite-help">招待を作成した人と、最初に返信した本人だけが閲覧できます。</p>'
        if data.get("reply_name"):
            body += '<p class="invite-help">返信した方：' + _e(data["reply_name"]) + '（個人としての返信）</p>'
        messages = [message for message in (data.get("messages") or []) if isinstance(message, dict)]
        body += '<div class="invite-conversation">'
        for message in messages:
            body += '<article class="invite-message' + (' invite-self' if message.get("is_self") else '') + '"><header><strong>' + ('あなた · ' if message.get("is_self") else '') + _e(message.get("display_name") or "利用者") + '</strong><small>' + _when(message.get("created_at")) + '</small></header><p class="invite-prose">' + _e(message.get("body")) + '</p></article>'
        if not messages:
            body += '<p class="invite-help">' + ('相手の返信が届くと、ここで相談を続けられます。' if status == "pending" else 'まだメッセージはありません。') + '</p>'
        body += '</div>'
        if data.get("can_message") and status in {"interested", "declined"}:
            fields = _field("body", "メッセージ（必須）", limit=2000, required=True, multiline=True)
            body += _form("message", fields, "メッセージを送る", 'data-invite-endpoint="/api' + _e(path) + '/message"')
        body += '</section>'
    if sender and data.get("can_withdraw") and active:
        fields = '<p class="invite-help">取り下げると、この招待への新しい返信やメッセージを受け付けなくなります。</p>'
        body += '<section class="invite-card invite-manage"><h2>招待を管理</h2>' + _form("withdraw", fields, "招待を取り下げる", 'data-invite-endpoint="/api' + _e(path) + '/withdraw"') + '</section>'
    return body + '</section>', SCRIPT


def listing(items):
    """Render the authenticated user's created and personally answered invitations."""
    items = [item for item in (items or []) if isinstance(item, dict)]
    body = _start("招待一覧", "自分で作成した招待と、自分が返信した招待を確認できます。")
    if not items:
        body += '<section class="invite-card"><h2>まだ招待はありません</h2><p>サークルDBで交流したい相手を探して、招待リンクを作成できます。</p><a class="invite-button invite-primary" href="/?tab=db">サークルDBで相手を探す</a></section>'
    for title, selected in (("作成した招待", [item for item in items if item.get("is_sender")]),
                            ("返信した招待", [item for item in items if not item.get("is_sender") and item.get("is_recipient")])):
        if not selected:
            continue
        body += '<section class="invite-list-section"><h2>' + title + '</h2><div class="invite-list">'
        for item in selected:
            body += '<article class="invite-card"><div class="invite-card-top"><span class="invite-kind">' + _e(INVITATION_KINDS.get(item.get("kind"), "交流への招待")) + '</span><span class="invite-status">' + _e(_status(item.get("status"))) + '</span></div><h3><a href="' + _e(_path(item.get("invitation_id"))) + '">' + _e(item.get("subject") or "交流への招待") + '</a></h3><p>' + _e(item.get("target_circle_name") or "招待先の団体") + '</p>'
            if item.get("sender_label"):
                body += '<p class="invite-help">' + _e(item["sender_label"]) + 'より</p>'
            if item.get("created_at"):
                body += '<p class="invite-help">作成：' + _when(item["created_at"]) + '</p>'
            if item.get("expires_at"):
                body += '<p class="invite-help">有効期限：' + _when(item["expires_at"]) + '</p>'
            body += '<a class="invite-text-link" href="' + _e(_path(item.get("invitation_id"))) + '">招待を確認する</a></article>'
        body += '</div></section>'
    return body + '</section>', ""


SCRIPT = r'''<script>
(()=>{
const root=document.getElementById('invite-root');if(!root)return;
const find=selector=>root.querySelector(selector),forms=[...root.querySelectorAll('form[data-invite-action]')];
const error=find('#invite-error');let busy=false;
function showError(message){if(!error)return;error.textContent=message;error.hidden=false;error.focus()}
function value(form,name){const field=form.elements.namedItem(name);return field?String(field.value||'').trim():''}
function setBusy(state){busy=state;forms.forEach(form=>{form.setAttribute('aria-busy',String(state));const fields=form.querySelector('fieldset');if(fields)fields.disabled=state})}
forms.forEach(form=>{const fields=form.querySelector('fieldset');if(fields)fields.disabled=false});
const compose=forms.find(form=>form.dataset.inviteAction==='create');
function selectKind(){if(!compose)return;const event=value(compose,'kind')==='event',panel=find('#invite-event-panel'),select=compose.elements.namedItem('event_id');if(panel)panel.hidden=!event;if(select){select.disabled=!event;select.required=event}}
if(compose){compose.querySelectorAll('[name="kind"]').forEach(field=>field.addEventListener('change',selectKind));selectKind()}
forms.forEach(form=>form.addEventListener('submit',async event=>{
 event.preventDefault();if(busy)return;if(!form.reportValidity())return;
 const action=form.dataset.inviteAction;let payload={};
 if(action==='create'){
  ['target_circle_id','kind','subject','sender_label','activity','proposed_date','location','body'].forEach(key=>payload[key]=value(form,key));payload.event_id=payload.kind==='event'?value(form,'event_id'):'';
 }else if(action==='respond'){
  ['response','display_name','body'].forEach(key=>payload[key]=value(form,key));payload.affiliation_confirmed=Boolean(form.elements.namedItem('affiliation_confirmed')?.checked);
 }else if(action==='message')payload.body=value(form,'body');
 if(error)error.hidden=true;setBusy(true);
 try{
  const response=await fetch(form.dataset.inviteEndpoint,{method:'POST',credentials:'same-origin',headers:{'Content-Type':'application/json',Accept:'application/json'},body:JSON.stringify(payload)});
  let data={};try{data=await response.json()}catch(_){}
  if(response.status===401){location.assign('/signin?return_to='+encodeURIComponent(location.pathname+location.search));return}
  if(!response.ok)throw new Error(typeof data.error==='string'?data.error:'内容を確認して、もう一度お試しください。');
  if(action==='create'){
   if(typeof data.invitation_id!=='string'||!data.invitation_id)throw new Error('招待を作成した結果を確認できませんでした。招待一覧をご確認ください。');
   location.assign('/invitations/'+encodeURIComponent(data.invitation_id));
  }else location.reload();
 }catch(problem){showError(problem instanceof TypeError?'通信できませんでした。入力内容を残しています。もう一度お試しください。':problem.message||'操作できませんでした。もう一度お試しください。');setBusy(false);selectKind()}
}));
const copy=find('#invite-copy'),text=find('#invite-share-text'),copyStatus=find('#invite-copy-status');
if(copy&&text){copy.disabled=false;copy.addEventListener('click',async()=>{
 try{if(!navigator.clipboard?.writeText)throw Error();await navigator.clipboard.writeText(text.value);copyStatus.textContent='招待文とリンクをコピーしました。相手へのメッセージに貼り付けて渡せます。'}
 catch(_){text.focus();text.select();copyStatus.textContent='コピーできませんでした。招待文を選択してコピーしてください。'}
})}
const url=find('#invite-share-url');if(url)url.addEventListener('focus',()=>url.select());
})();
</script>'''


CSS = '''<style>
.invite-ui{max-width:880px;margin:auto;color:var(--ink,#17212f);line-height:1.7;overflow-wrap:anywhere}
.invite-ui .invite-nav{display:flex;gap:20px;flex-wrap:wrap;margin-bottom:18px;font-size:14px}
.invite-ui .invite-nav a,.invite-ui .invite-text-link{display:inline-flex;align-items:center;min-height:44px;color:var(--brand,#0f7a62);text-underline-offset:3px}
.invite-ui .invite-heading{margin-bottom:22px}.invite-ui .invite-heading h1{font-size:clamp(25px,4vw,34px);line-height:1.35;margin:4px 0 12px}
.invite-ui .invite-heading>p:last-child{color:#52657a;margin:0}.invite-ui .invite-eyebrow{color:var(--brand,#0f7a62);font-size:12px;font-weight:800;margin:0}
.invite-ui .invite-card{padding:24px;background:#fff;border:1px solid var(--line,#dbe4ed);border-radius:10px;margin:16px 0;min-width:0}
.invite-ui h2{font-size:21px;line-height:1.45;margin:0 0 14px}.invite-ui h3{font-size:18px;line-height:1.5;margin:12px 0}
.invite-ui .invite-card>p{margin:10px 0}.invite-ui .invite-label,.invite-ui label{font-weight:750;color:#334155;font-size:14px}
.invite-ui .invite-help{font-size:13px;color:#52657a;line-height:1.65;margin:6px 0 0}.invite-ui .invite-field{display:grid;gap:6px;margin:18px 0;min-width:0}
.invite-ui .invite-field:first-child{margin-top:0}.invite-ui .invite-field input,.invite-ui .invite-field select,.invite-ui .invite-field textarea{width:100%;min-width:0;min-height:46px;border:1px solid #aebfce;border-radius:8px;padding:10px 12px;background:#fff;color:#17212f;font:inherit;line-height:1.5}
.invite-ui .invite-field textarea{resize:vertical;min-height:132px}.invite-ui .invite-field [readonly]{background:#f8fafc}
.invite-ui .invite-two-columns{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.invite-ui .invite-two-columns .invite-field{margin:0}
.invite-ui .invite-choices{display:flex;gap:12px 20px;flex-wrap:wrap}.invite-ui .invite-choices label,.invite-ui .invite-confirm{display:flex;gap:10px;align-items:flex-start;min-height:44px;padding:10px 0;font-weight:600;cursor:pointer}
.invite-ui input[type=checkbox],.invite-ui input[type=radio]{width:20px;height:20px;min-height:20px;margin:2px 0 0;flex:0 0 20px;accent-color:var(--brand,#0f7a62)}
.invite-ui label:has(input:disabled){color:#64748b;cursor:default}.invite-ui .invite-form fieldset{border:0;margin:0;padding:0;min-width:0}
.invite-ui .invite-actions{display:flex;gap:12px;flex-wrap:wrap;align-items:center;margin-top:20px}
.invite-ui .invite-button{display:inline-flex;align-items:center;justify-content:center;min-height:46px;padding:10px 18px;border:1px solid #aebfce;border-radius:8px;background:#fff;color:#17212f;font:inherit;font-size:14px;font-weight:750;text-decoration:none;cursor:pointer;line-height:1.5}
.invite-ui .invite-primary{background:var(--accent,#e15b31);border-color:var(--accent,#e15b31);color:#fff}
.invite-ui .invite-button:disabled,.invite-ui fieldset:disabled .invite-button{opacity:.55;cursor:not-allowed}
.invite-ui a:focus-visible,.invite-ui button:focus-visible,.invite-ui input:focus-visible,.invite-ui select:focus-visible,.invite-ui textarea:focus-visible{outline:3px solid #0f7a62;outline-offset:3px}
.invite-ui .invite-note{background:#f1f7f4;border-left:3px solid var(--brand,#0f7a62);padding:14px 16px;color:#365447;font-size:14px;line-height:1.75;margin:18px 0}
.invite-ui .invite-error{padding:16px;margin:18px 0;background:#fff5f2;border:1px solid #e7b9a9;border-radius:8px;color:#962d1a;font-size:14px}
.invite-ui .invite-card-top{display:flex;gap:12px;align-items:center;justify-content:space-between;flex-wrap:wrap}
.invite-ui .invite-kind{font-size:13px;font-weight:750;color:#52657a}.invite-ui .invite-status{padding:4px 10px;border-radius:6px;background:#edf5f1;color:#17604c;font-size:13px;font-weight:750}
.invite-ui .invite-recipient{font-size:20px;font-weight:750}.invite-ui .invite-from{font-size:14px;color:#52657a}
.invite-ui .invite-prose{white-space:pre-wrap;overflow-wrap:anywhere;line-height:1.9}.invite-ui .invite-facts{display:grid;grid-template-columns:145px minmax(0,1fr);gap:8px 16px;margin:20px 0 0;font-size:14px}
.invite-ui .invite-facts dt{color:#52657a}.invite-ui .invite-facts dd{margin:0;white-space:pre-wrap}
.invite-ui .invite-event-summary{padding:16px;background:#f8fafc;border:1px solid var(--line,#dbe4ed);border-radius:8px;margin-top:20px}.invite-ui .invite-event-summary p{margin:0 0 6px}
.invite-ui .invite-conversation{display:grid;gap:12px;margin:18px 0}.invite-ui .invite-message{padding:16px;border:1px solid var(--line,#dbe4ed);border-radius:8px;background:#f8fafc}
.invite-ui .invite-self{background:#f0f7f3;border-color:#d3e6da}.invite-ui .invite-message header{display:flex;gap:8px 16px;justify-content:space-between;flex-wrap:wrap}.invite-ui .invite-message small{color:#64748b;font-size:12px}
.invite-ui .invite-message p{margin:10px 0 0}.invite-ui .invite-manage{border-style:dashed}.invite-ui .invite-manage h2{font-size:18px}.invite-ui .invite-manage .invite-primary{background:#fff;color:#7e4030;border-color:#cba99e}
.invite-ui .invite-list-section{margin-top:26px}.invite-ui .invite-list{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:16px}.invite-ui .invite-list .invite-card{margin:0}
@media(max-width:600px){.invite-ui .invite-card{padding:18px}.invite-ui .invite-two-columns,.invite-ui .invite-list{grid-template-columns:1fr;gap:12px}.invite-ui .invite-two-columns .invite-field{margin:12px 0}.invite-ui .invite-choices{display:grid;gap:0}.invite-ui .invite-facts{grid-template-columns:1fr;gap:2px}.invite-ui .invite-facts dd{margin-bottom:10px}.invite-ui .invite-actions{display:grid;grid-template-columns:1fr}.invite-ui .invite-button{width:100%}.invite-ui .invite-nav{gap:16px}}
</style>'''


__all__ = ["compose", "detail", "listing"]
