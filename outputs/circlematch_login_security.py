"""Optional login observations. Uses existing state, audit and notification tables."""
from datetime import datetime, timedelta, timezone
import hashlib
import hmac
from html import escape
import json
import time

WINDOW = 600
LABELS = {'google':'Google','supabase_google':'Google','supabase_email':'メール認証','supabase':'Supabase認証'}
EVENTS = {'login_success':'ログイン成功','rapid_logins':'短時間のログイン急増',
          'exchange_burst':'認証情報の繰り返し使用','failure_burst':'認証失敗の集中'}


def digest(secret, value):
    return hmac.new(secret.encode(),value.encode(),hashlib.sha256).hexdigest()


def source_key(secret, peer, timestamp):
    # Do not trust forwarded headers or treat a proxy peer as a client identity.
    return digest(secret,f'login-source:{timestamp // 86400}:{peer}')


def mark_once(conn, key, timestamp):
    return bool(conn.execute("""insert into app_state values(?, '{}', ?)
                on conflict(state_key) do nothing""",
                (key,datetime.fromtimestamp(timestamp,timezone.utc).isoformat())).rowcount)


def count_attempt(conn, scope, kind, timestamp):
    start = timestamp // WINDOW * WINDOW
    key = f'login-security:counter:{kind}:{scope}:{start}'
    row = conn.execute('select state_value from app_state where state_key=?',(key,)).fetchone()
    count = min(json.loads(row['state_value'])['count']+1,1000000) if row else 1
    conn.execute("""insert into app_state values(?,?,?) on conflict(state_key) do update set
                    state_value=excluded.state_value,updated_at=excluded.updated_at""",
                 (key,json.dumps({'count':count}),datetime.fromtimestamp(timestamp,timezone.utc).isoformat()))
    return count,start


def record_failure(conn, secret, peer, method, audit, timestamp=None):
    timestamp = int(time.time()) if timestamp is None else timestamp
    scope = source_key(secret,peer,timestamp)
    count,_ = count_attempt(conn,scope,'failure',timestamp)
    if count != 5:
        return False
    audit(conn,'login_security','auth_source',scope,
          {'kind':'failure_burst','method':method,'occurred_at':timestamp,'count':count})
    return True


def record_login(conn, user_id, method, proof, secret, notify, audit, *, email_allowed=True, timestamp=None):
    """Called after provider verification; never grants or denies login."""
    timestamp = int(time.time()) if timestamp is None else timestamp
    identifier = digest(secret,f'login:{user_id}:{method}:{proof}')
    fresh = mark_once(conn,'login-security:proof:'+identifier,timestamp)
    count,start = count_attempt(conn,digest(secret,'login-user:'+user_id),'exchange',timestamp)
    if fresh:
        notify(conn,user_id,None,'login_success','ログインを確認しました',
               f'日時: {time_label(timestamp)} JST\nログイン方法: {LABELS.get(method,"認証サービス")}\n'
               '心当たりがない場合は、ログイン元の認証サービスのアカウントを確認し、Circle Matchの窓口へご連絡ください。',
               dedupe_key='login:'+identifier,email_allowed=email_allowed)
        audit(conn,'login_security','user',user_id,
              {'kind':'login_success','method':method,'occurred_at':timestamp,'count':1})
    recent = conn.execute("""select count(*) from event_notifications where recipient_user_id=?
               and notification_type='login_success' and datetime(created_at)>=datetime(?, 'unixepoch')""",
               (user_id,timestamp-WINDOW)).fetchone()[0]
    kind = 'rapid_logins' if recent >= 5 else 'exchange_burst' if count >= 10 else None
    if kind and mark_once(conn,f'login-security:alert:{digest(secret,user_id)}:{start}',timestamp):
        audit(conn,'login_security','user',user_id,
              {'kind':kind,'method':method,'occurred_at':timestamp,'count':max(count,recent)})
        notify(conn,user_id,None,'login_security_alert','ログイン状況を確認してください',
               '短時間にログインや認証情報の使用が繰り返されました。不正利用と確定したわけではありません。'
               '心当たりがない場合は、ログイン元の認証サービスのアカウントを確認し、Circle Matchの窓口へご連絡ください。',
               dedupe_key=f'login-alert:{user_id}:{start}',email_allowed=email_allowed)
    return fresh,kind


def observe_login(conn, user_id, method, proof, secret, notify, audit, log, *, email_allowed=True):
    # Roll back observation only, preserving the existing account and session writes.
    conn.execute('savepoint login_observation')
    try:
        result = record_login(conn,user_id,method,proof,secret,notify,audit,email_allowed=email_allowed)
    except Exception as exc:
        conn.execute('rollback to login_observation')
        try:
            log('login security observation failed: '+type(exc).__name__)
        except Exception:
            pass
        result = None
    finally:
        conn.execute('release login_observation')
    return result


def recent_events(conn, user_id=None):
    sql = "select payload from audit_logs where action='login_security'"
    args = ()
    if user_id is not None:
        sql += " and entity_type='user' and entity_id=?"
        args = (user_id,)
    result = []
    for row in conn.execute(sql+' order by audit_id desc limit 200',args):
        value = json.loads(row['payload'])
        if user_id is None and value['kind'] == 'login_success':
            continue
        if value['kind'] in EVENTS:
            result.append(value)
        if len(result) == 30:
            break
    return result


def prune(conn):
    conn.execute("delete from app_state where state_key like 'login-security:counter:%' and datetime(updated_at)<datetime('now','-1 day')")
    conn.execute("delete from app_state where state_key like 'login-security:%' and datetime(updated_at)<datetime('now','-30 days')")
    conn.execute("delete from audit_logs where action='login_security' and datetime(created_at)<datetime('now','-30 days')")


def time_label(timestamp):
    return datetime.fromtimestamp(timestamp,timezone.utc).astimezone(timezone(timedelta(hours=9))).strftime('%Y/%m/%d %H:%M:%S')


def render(events, active_sessions, email_ready, *, admin=False):
    status = ('送信設定あり。送信サービスの受付と受信箱への到着は異なります。' if email_ready else
              'メール配信は未設定です。現在はアプリ内通知のみです。')
    rows = ''.join('<li><strong>'+escape(EVENTS[row['kind']])+'</strong><p>'+
                   time_label(row['occurred_at'])+' JST / '+escape(LABELS.get(row['method'],'認証サービス'))+
                   (' / '+str(row['count'])+'回' if row['kind'] != 'login_success' else '')+'</p></li>' for row in events)
    if admin:
        title = 'ログインの検知記録'
        content = '<p>不正利用の確定ではありません。認証失敗はサーバーが観測した接続元の単位で集計するため、プロキシ配下では複数の利用者を含みます。自動的なアカウント停止は行いません。</p>'
    else:
        title = 'ログインとセキュリティ'
        content = ('<h2>ログイン通知</h2><p>ログイン成功をアプリ内に通知し、メール送信設定と認証済みの宛先がある場合はメールでも通知します。</p>'
                   '<p>'+status+'</p><h2>有効なログイン</h2><p>'+str(active_sessions)+'件</p>'
                   '<p>心当たりがない場合は、ログイン元のGoogleなどのアカウントを確認し、<a href="/contact">お問い合わせ窓口</a>へご連絡ください。</p>')
    return ('<style>.login-security{max-width:760px;margin:auto;overflow-wrap:anywhere}.login-security h1{font-size:24px;letter-spacing:0}.login-security h2{font-size:18px;letter-spacing:0}.security-events{padding:0;list-style:none}.security-events li{padding:14px 0;border-bottom:1px solid #dce6de}.security-events p{margin:4px 0}</style>'
            '<section class="panel login-security"><a href="/settings">設定へ</a><h1>'+title+'</h1>'+content+
            '<h2>最近30日間の記録</h2><ol class="security-events">'+(rows or '<li>記録はありません。</li>')+'</ol></section>')
