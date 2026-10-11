"""Private, account-to-account introductions addressed to public DB circles.

A link lets its holder read the introduction and reply from their own account.
It never grants circle ownership, admits event participants, or sends email.
The caller supplies its existing public-circle policy and event availability check.
"""
from datetime import datetime, timedelta, timezone
import secrets
from urllib.parse import quote


def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def init_schema(conn):
    conn.executescript("""
    create table if not exists circle_invitations (
      invitation_id text primary key,
      sender_user_id text not null references user_accounts(user_id),
      recipient_user_id text references user_accounts(user_id),
      target_circle_id text not null references circles(circle_id),
      target_circle_name text not null,
      kind text not null check(kind in ('event','consultation')),
      event_id text references event_posts(event_id),
      subject text not null,
      sender_label text not null,
      activity text not null,
      proposed_date text not null default '',
      location text not null default '',
      body text not null,
      reply_name text not null default '',
      status text not null default 'pending' check(status in ('pending','interested','declined','withdrawn')),
      created_at text not null,
      updated_at text not null,
      expires_at text not null
    );
    create table if not exists circle_invitation_messages (
      message_id integer primary key,
      invitation_id text not null references circle_invitations(invitation_id) on delete cascade,
      sender_user_id text not null references user_accounts(user_id),
      display_name text not null,
      body text not null,
      created_at text not null
    );
    create index if not exists idx_circle_invites_sender on circle_invitations(sender_user_id,created_at);
    create index if not exists idx_circle_invites_recipient on circle_invitations(recipient_user_id,updated_at);
    create index if not exists idx_circle_invite_messages on circle_invitation_messages(invitation_id,message_id);
    """)


def authenticated(user):
    if not user.get("authenticated") or not user.get("user_id"):
        raise PermissionError("ログインが必要です")
    return user["user_id"]


def text(data, key, limit, required=False):
    if not isinstance(data, dict):
        raise ValueError("入力形式が正しくありません")
    value = data.get(key, "")
    if not isinstance(value, str):
        raise ValueError("入力形式が正しくありません")
    value = value.strip()
    if len(value) > limit or (required and not value) or any(ord(ch) < 32 and ch not in "\n\r\t" for ch in value):
        raise ValueError("入力内容と文字数を確認してください")
    return value


def target(conn, circle_id, public_clause):
    row = conn.execute("""select c.circle_id,c.circle_name,c.sport_category,c.source_url,
        u.university_name,u.prefecture,p.profile_slug,
        case when p.public_contact_consent=1 then p.public_contact_email else '' end as public_contact_email
        from circles c join universities u on u.university_id=c.university_id
        left join circle_public_profiles p on p.circle_id=c.circle_id and p.is_published=1
        where c.circle_id=? and """ + public_clause, (circle_id,)).fetchone()
    if not row:
        raise ValueError("招待先の団体が見つからないか、現在掲載されていません")
    result = dict(row)
    result["profile_url"] = "/circles/" + quote(result["profile_slug"], safe="") if result.get("profile_slug") else ""
    result.pop("profile_slug", None)
    return result


def create(conn, data, user, public_clause, event_check):
    uid = authenticated(user)
    conn.execute("begin immediate")
    circle = target(conn, text(data, "target_circle_id", 120, True), public_clause)
    kind = text(data, "kind", 20, True)
    if kind not in {"event", "consultation"}:
        raise ValueError("招待の種類を選んでください")
    event_id = text(data, "event_id", 120) if kind == "event" else ""
    event = event_check(conn, event_id, uid) if kind == "event" else None
    if kind == "event" and not event:
        raise ValueError("ご自身が主催する、受付中の公開イベントを選んでください")
    activity = text(data, "activity", 20) or "交流"
    if activity not in {"練習試合", "合同練習", "交流", "その他"}:
        raise ValueError("交流内容を選んでください")
    values = {key: text(data, key, limit, required) for key, limit, required in (
        ("subject", 120, True), ("sender_label", 80, True), ("proposed_date", 240, False),
        ("location", 240, False), ("body", 2000, True))}
    created = timestamp()
    if conn.execute("select count(*) from circle_invitations where sender_user_id=? and created_at>=?",
                    (uid, (datetime.now(timezone.utc) - timedelta(days=1)).isoformat(timespec="seconds"))).fetchone()[0] >= 50:
        raise ValueError("本日の招待作成数の上限に達しました。時間をおいてください")
    invitation_id = secrets.token_urlsafe(24)
    expires = (datetime.now(timezone.utc) + timedelta(days=30)).isoformat(timespec="seconds")
    conn.execute("""insert into circle_invitations
        (invitation_id,sender_user_id,target_circle_id,target_circle_name,kind,event_id,subject,
         sender_label,activity,proposed_date,location,body,created_at,updated_at,expires_at)
        values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)""", (invitation_id,uid,circle["circle_id"],circle["circle_name"],kind,
         event_id or None,values["subject"],values["sender_label"],activity,values["proposed_date"],
         values["location"],values["body"],created,created,expires))
    return invitation_id


def row_for(conn, invitation_id):
    row = conn.execute("select * from circle_invitations where invitation_id=?", (invitation_id,)).fetchone()
    if not row:
        raise ValueError("招待が見つかりません")
    return dict(row)


def status(row):
    return "expired" if row["status"] != "withdrawn" and row["expires_at"] <= timestamp() else row["status"]


def detail(conn, invitation_id, user, event_check):
    row = row_for(conn, invitation_id)
    uid = user.get("user_id") if user.get("authenticated") else None
    sender, recipient = bool(uid and uid == row["sender_user_id"]), bool(uid and uid == row["recipient_user_id"])
    current_status = status(row)
    active = current_status not in {"withdrawn", "expired"}
    public_keys = ("invitation_id", "target_circle_name", "kind", "subject", "sender_label", "activity",
                   "proposed_date", "location", "body", "created_at", "expires_at")
    result = {key: row[key] for key in public_keys}
    result.update(status=current_status, is_sender=sender, is_recipient=recipient,
                  can_respond=active and not sender and not row["recipient_user_id"],
                  can_message=active and (sender or recipient) and bool(row["recipient_user_id"]),
                  can_withdraw=active and sender, reply_name=row["reply_name"] if sender or recipient else "", messages=[])
    if not sender and not recipient and not active:
        # Revoking a shared link removes the private invitation text from guests.
        for key in ("body", "sender_label", "proposed_date", "location", "subject", "target_circle_name"):
            result[key] = ""
        result["can_respond"] = False
    result.update(event_id=None, event_title="", event_url="", event_available=False)
    if active and row["event_id"]:
        event = event_check(conn, row["event_id"], None)
        if event:
            result.update(event_id=event["event_id"],event_title=event["title"],
                          event_url="/events/" + quote(event["event_id"], safe=""),event_available=True)
    if sender or recipient:
        result["messages"] = [{"body": msg["body"], "display_name": msg["display_name"], "created_at": msg["created_at"],
                               "is_self": msg["sender_user_id"] == uid} for msg in conn.execute(
            "select * from circle_invitation_messages where invitation_id=? order by message_id limit 200", (invitation_id,))]
    return result


def notify(conn, recipient_id, title):
    # In-app only: do not queue unsolicited mail to DB-listed organizations.
    conn.execute("""insert into event_notifications(notification_id,recipient_user_id,event_id,
        notification_type,title,body,email_status,created_at) values(?,?,null,'circle_invitation',?,?,'not_configured',?)""",
        (secrets.token_urlsafe(18),recipient_id,title,"交流招待の一覧で内容をご確認ください。",timestamp()))


def respond(conn, invitation_id, data, user):
    uid = authenticated(user)
    response = text(data, "response", 20, True)
    if response not in {"interested", "declined"} or data.get("affiliation_confirmed") is not True:
        raise ValueError("回答内容と、招待先団体の関係者であることを確認してください")
    name, body = text(data, "display_name", 80, True), text(data, "body", 2000)
    conn.execute("begin immediate")
    row = row_for(conn, invitation_id)
    if row["sender_user_id"] == uid:
        raise PermissionError("ご自身の招待には回答できません")
    if status(row) in {"withdrawn", "expired"}:
        raise ValueError("この招待は取り下げ済みか、期限切れです")
    if row["recipient_user_id"]:
        if row["recipient_user_id"] != uid:
            raise PermissionError("この招待は別のアカウントが回答済みです")
        return row["status"]
    conn.execute("update circle_invitations set recipient_user_id=?,reply_name=?,status=?,updated_at=? where invitation_id=?",
                 (uid,name,response,timestamp(),invitation_id))
    if body:
        conn.execute("insert into circle_invitation_messages(invitation_id,sender_user_id,display_name,body,created_at) values(?,?,?,?,?)",
                     (invitation_id,uid,name,body,timestamp()))
    notify(conn,row["sender_user_id"],"交流招待への回答が届きました")
    return response


def message(conn, invitation_id, data, user):
    uid = authenticated(user)
    body = text(data, "body", 2000, True)
    conn.execute("begin immediate")
    row = row_for(conn, invitation_id)
    if uid not in {row["sender_user_id"], row["recipient_user_id"]}:
        raise PermissionError("この相談を閲覧する権限がありません")
    if not row["recipient_user_id"] or status(row) in {"withdrawn", "expired"}:
        raise ValueError("現在この招待ではメッセージを送れません")
    count = conn.execute("select count(*) from circle_invitation_messages where invitation_id=?", (invitation_id,)).fetchone()[0]
    if count >= 200:
        raise ValueError("この相談のメッセージ数の上限に達しました")
    recent = conn.execute("select count(*) from circle_invitation_messages where sender_user_id=? and created_at>=?",
        (uid,(datetime.now(timezone.utc)-timedelta(hours=1)).isoformat(timespec="seconds"))).fetchone()[0]
    if recent >= 60:
        raise ValueError("メッセージが多すぎます。時間をおいてください")
    name = row["sender_label"] if uid == row["sender_user_id"] else row["reply_name"]
    conn.execute("insert into circle_invitation_messages(invitation_id,sender_user_id,display_name,body,created_at) values(?,?,?,?,?)",
                 (invitation_id,uid,name,body,timestamp()))
    conn.execute("update circle_invitations set updated_at=? where invitation_id=?", (timestamp(),invitation_id))
    other = row["recipient_user_id"] if uid == row["sender_user_id"] else row["sender_user_id"]
    notify(conn,other,"交流招待にメッセージが届きました")


def withdraw(conn, invitation_id, user):
    uid = authenticated(user)
    row = row_for(conn, invitation_id)
    if row["sender_user_id"] != uid:
        raise PermissionError("この招待を取り下げる権限がありません")
    conn.execute("update circle_invitations set status='withdrawn',updated_at=? where invitation_id=?", (timestamp(),invitation_id))


def listing(conn, user, event_check):
    uid = authenticated(user)
    ids = conn.execute("select invitation_id from circle_invitations where sender_user_id=? or recipient_user_id=? order by updated_at desc limit 100", (uid,uid))
    return [detail(conn,row[0],user,event_check) for row in ids]
