"""One-event email capabilities. None of these tokens are Circle Match login sessions."""
import hashlib
import hmac
import json
import re
import secrets
import time
from urllib.parse import quote


PROVIDER = 'event_guest'
COOKIE = 'cm_event_guest'
SESSION_TTL = 7 * 86400
LINK_TTL = 20 * 60
PREFIX = 'event-guest:v1:'
ROUTE = re.compile(r'/events/([^/]+)/guest(?:/(request|verify|redeem|apply|attendance|cancel|contact|message|exit))?/?')


def path(eid):
    return '/events/' + quote(eid, safe='') + '/guest'


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def identity(eid, email):
    return digest(eid + '\0' + email)


def email_address(raw):
    email = str(raw or '').strip().lower()
    if len(email) > 254 or not re.fullmatch(r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]+@[a-z0-9-]+(?:\.[a-z0-9-]+)+", email):
        raise ValueError('メールアドレスを確認してください')
    return email


def reserve_link(conn, eid, email, peer, secret, available, *, name=None):
    name = str(name or '').strip()
    if len(name) > 80 or any(ord(char) < 32 or ord(char) == 127 for char in name):
        raise ValueError('氏名は80文字以内で入力してください')
    conn.execute('begin immediate')
    now = int(time.time())
    for kind in ('rate','link','session'):
        conn.execute('delete from app_state where state_key glob ? and cast(updated_at as integer)<=?',
                     (PREFIX+kind+':*',now))
    for scope, value, window, maximum in [('mail',email,3600,4),('cooldown',email,60,1),
                                          ('peer',peer,900,40),('site','all',3600,180)]:
        key = PREFIX+'rate:'+scope+':'+hmac.new(secret.encode(),value.encode(),hashlib.sha256).hexdigest()
        row = conn.execute('select state_value from app_state where state_key=?',(key,)).fetchone()
        if row and int(row[0]) >= maximum:
            raise ValueError('確認メールの送信が続いています。時間を空けてください')
        conn.execute('''insert into app_state values(?,1,?) on conflict(state_key) do update
                        set state_value=cast(state_value as integer)+1''',(key,now+window))
    if not available and not conn.execute('''select 1 from event_applications a join user_accounts u on
        u.user_id=a.applicant_user_id where a.event_id=? and u.provider=? and u.provider_subject=?''',
        (eid,PROVIDER,identity(eid,email))).fetchone():
        return None
    token = secrets.token_urlsafe(32)
    conn.execute('insert into app_state values(?,?,?)',(PREFIX+'link:'+digest(token),
                 json.dumps([eid,{'email':email,'name':name}] if name else [eid,email]),now+LINK_TTL))
    return token


def lookup(conn, kind, token, eid):
    if not isinstance(token,str) or not re.fullmatch(r'[A-Za-z0-9_-]{43}',token):
        return None
    row = conn.execute('select state_value from app_state where state_key=? and cast(updated_at as integer)>?',
                       (PREFIX+kind+':'+digest(token),int(time.time()))).fetchone()
    if row:
        scope, value = json.loads(row[0])
        if scope == eid:
            return value
    return None


def redeem(conn, eid, token):
    conn.execute('begin immediate')
    proof = lookup(conn,'link',token,eid)
    if not proof:
        raise ValueError('リンクは期限切れ、または使用済みです。確認メールをもう一度受け取ってください')
    # Previously issued email-only proofs remain valid during their existing lifetime.
    email, name = (proof['email'],proof.get('name','')) if isinstance(proof,dict) else (proof,'')
    conn.execute('delete from app_state where state_key=?',(PREFIX+'link:'+digest(token),))
    subject = identity(eid,email)
    conn.execute('''insert into user_accounts(user_id,provider,provider_subject,email,display_name,created_at,updated_at)
        values(?,?,?,?,?,CURRENT_TIMESTAMP,CURRENT_TIMESTAMP) on conflict(provider,provider_subject) do nothing''',
        ('guest_'+secrets.token_hex(16),PROVIDER,subject,email,name or 'ゲスト参加者'))
    uid = conn.execute('select user_id from user_accounts where provider=? and provider_subject=?',(PROVIDER,subject)).fetchone()[0]
    if name:
        conn.execute('update user_accounts set display_name=?,updated_at=CURRENT_TIMESTAMP where user_id=? and provider=?',
                     (name,uid,PROVIDER))
    session = secrets.token_urlsafe(32)
    conn.execute('insert into app_state values(?,?,?)',(PREFIX+'session:'+digest(session),
                 json.dumps([eid,uid]),int(time.time())+SESSION_TTL))
    return session


def actor(conn, eid, session):
    uid = lookup(conn,'session',session,eid)
    if uid:
        row = conn.execute('select user_id,email,display_name from user_accounts where user_id=? and provider=?',(uid,PROVIDER)).fetchone()
        if row:
            data = dict(row)
            if data['display_name'] == 'ゲスト参加者':
                data['display_name'] = ''
            return dict(authenticated=True, guest=True, **data)
    return None


VERIFY_HTML = """<!doctype html><html lang="ja"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="referrer" content="no-referrer"><meta name="robots" content="noindex,nofollow"><title>メールの確認 | Circle Match</title>
<style>body{font:16px/1.7 system-ui,sans-serif;color:#182333;max-width:32rem;margin:3rem auto;padding:1rem}
h1{font-size:1.5rem}button{background:#195d46;color:white;padding:.8rem 1.2rem;border:0;border-radius:6px;font:inherit}a{color:#195d46}</style>
<main><strong>Circle Match</strong><h1>メールアドレスの確認</h1><p>この端末で大会のゲスト申込を開きます。この操作だけでは参加申込は確定しません。</p>
<button type="button">メールを確認して進む</button><p role="alert"></p><a href="./">確認メールをもう一度受け取る</a></main>
<script>const token=location.hash.slice(1),button=document.querySelector('button'),out=document.querySelector('[role=alert]');
history.replaceState(null,'',location.pathname);
button.onclick=async()=>{button.disabled=true;try{const r=await fetch('./redeem',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({token})});
const data=await r.json();if(!r.ok)throw Error(data.error||'確認に失敗しました');location.replace(location.pathname.replace(/\\/verify$/,''))}
catch(e){out.textContent=e.message;button.disabled=false}}</script></html>"""
