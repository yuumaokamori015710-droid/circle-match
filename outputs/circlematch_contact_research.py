"""Private research of publicly listed club contact details.

This module owns only the circle_contact_research* tables. Finding an address
does not grant public-display consent, create a notification, or send mail.
The HTTP caller must enforce its existing administrator authorization.
"""
import csv
from datetime import datetime, timezone
import hashlib
from html import escape
from io import StringIO
import ipaddress
import json
import math
import re
from urllib.parse import quote, urlsplit, urlunsplit


STATUSES = ("email_found", "no_email", "contact_form", "blocked", "source_missing", "review_needed")
STATUS_LABELS = {"unresearched": "未調査", "email_found": "メールあり", "no_email": "確認範囲で未発見",
                 "contact_form": "問い合わせ先候補", "blocked": "取得できず", "source_missing": "参照先なし",
                 "review_needed": "要確認"}
MAX_BATCH = 1000
MAX_PAYLOAD_BYTES = 8 * 1024 * 1024
EMAIL_LOCAL = re.compile(r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~.-]+\Z")
DOMAIN_LABEL = re.compile(r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\Z")


def timestamp():
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _text(value, name, limit, required=False):
    if not isinstance(value, str):
        raise ValueError(name + " は文字列で指定してください")
    value = value.strip()
    if len(value) > limit or (required and not value) or any(ord(ch) < 32 and ch not in "\n\r\t" for ch in value):
        raise ValueError(name + " の内容と文字数を確認してください")
    return value


def _domain(value):
    try:
        value = value.encode("idna").decode("ascii").lower()
    except (UnicodeError, ValueError):
        raise ValueError("公開サイトのホスト名が正しくありません") from None
    if len(value) > 253 or "." not in value or not all(DOMAIN_LABEL.fullmatch(label) for label in value.split(".")):
        raise ValueError("公開サイトのホスト名が正しくありません")
    if value.endswith((".local", ".localhost", ".internal", ".lan", ".home", ".arpa")):
        raise ValueError("ローカルな参照先は保存できません")
    return value


def public_url(value, required=False):
    value = _text(value, "参照URL", 2048, required)
    if not value:
        return ""
    if any(ch.isspace() for ch in value) or "\\" in value:
        raise ValueError("参照URLが正しくありません")
    try:
        parsed = urlsplit(value)
        hostname = parsed.hostname
        port = parsed.port
    except ValueError:
        raise ValueError("参照URLが正しくありません") from None
    if parsed.scheme.lower() not in {"http", "https"} or not hostname or parsed.username is not None or parsed.password is not None:
        raise ValueError("公開されたHTTP/HTTPSの参照URLを指定してください")
    try:
        address = ipaddress.ip_address(hostname)
    except ValueError:
        # Reject alternate numeric IPv4 forms that URL clients can interpret as
        # loopback, even though ipaddress correctly rejects their spelling.
        if re.fullmatch(r"(?:0x[0-9a-fA-F]+|[0-9]+)(?:\.(?:0x[0-9a-fA-F]+|[0-9]+))*", hostname):
            raise ValueError("数値形式の参照先が正しくありません") from None
        hostname = _domain(hostname)
    else:
        if not address.is_global:
            raise ValueError("ローカルな参照先は保存できません")
        hostname = "[" + address.compressed + "]" if address.version == 6 else address.compressed
    if port is not None and port not in {80, 443}:
        raise ValueError("参照URLのポートが正しくありません")
    netloc = hostname + (":" + str(port) if port is not None else "")
    return urlunsplit((parsed.scheme.lower(), netloc, parsed.path or "/", parsed.query, parsed.fragment))


def contact_email(value):
    value = _text(value, "メールアドレス", 254, True)
    if value.count("@") != 1:
        raise ValueError("メールアドレスが正しくありません")
    local, domain = value.rsplit("@", 1)
    if (len(local) > 64 or not EMAIL_LOCAL.fullmatch(local) or local.startswith(".")
            or local.endswith(".") or ".." in local):
        raise ValueError("メールアドレスが正しくありません")
    domain = _domain(domain)
    # Domains for addresses are DNS names, never IP literals or numeric hosts.
    if not re.search(r"[a-z]", domain.rsplit(".", 1)[-1]):
        raise ValueError("メールアドレスが正しくありません")
    return local + "@" + domain


def ensure_tables(conn):
    # execute(), unlike executescript(), does not commit the caller's transaction.
    conn.execute("""create table if not exists circle_contact_research (
        circle_id text primary key references circles(circle_id) on delete cascade,
        status text not null check(status in ('email_found','no_email','contact_form','blocked','source_missing','review_needed')),
        checked_at text not null,
        job_id text not null,
        sources_json text not null default '[]',
        note text not null default '',
        contact_form_url text not null default '',
        result_hash text not null,
        updated_at text not null
    )""")
    conn.execute("""create table if not exists circle_contact_research_emails (
        circle_id text not null references circle_contact_research(circle_id) on delete cascade,
        email text not null,
        source_url text not null,
        evidence text not null,
        attribution text not null check(attribution in ('club_context','club_page')),
        primary key(circle_id,email,source_url)
    )""")
    conn.execute("""create table if not exists circle_contact_research_history (
        revision_id integer primary key,
        circle_id text not null references circles(circle_id) on delete cascade,
        job_id text not null,
        checked_at text not null,
        result_json text not null,
        saved_at text not null
    )""")
    conn.execute("create index if not exists idx_contact_research_status on circle_contact_research(status,checked_at)")
    conn.execute("create index if not exists idx_contact_research_email on circle_contact_research_emails(email)")
    conn.execute("create index if not exists idx_contact_research_history on circle_contact_research_history(circle_id,revision_id)")


def _checked_at(value):
    if value is None:
        return timestamp()
    value = _text(value, "調査日時", 64, True)
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if parsed.tzinfo is None:
            raise ValueError()
        return parsed.astimezone(timezone.utc).isoformat(timespec="seconds")
    except ValueError:
        raise ValueError("調査日時はタイムゾーン付きISO日時で指定してください") from None


def _record(raw):
    if not isinstance(raw, dict):
        raise ValueError("調査結果はオブジェクトで指定してください")
    allowed = {"circle_id", "status", "checked_at", "sources", "contacts", "note", "research_note", "contact_form_url"}
    if set(raw) - allowed:
        raise ValueError("調査結果に未対応の項目があります")
    circle_id = _text(raw.get("circle_id"), "団体ID", 120, True)
    status = _text(raw.get("status"), "調査状況", 30, True)
    if status not in STATUSES:
        raise ValueError("調査状況が正しくありません")
    sources = raw.get("sources", [])
    contacts = raw.get("contacts", [])
    if not isinstance(sources, list) or len(sources) > 20 or not isinstance(contacts, list) or len(contacts) > 20:
        raise ValueError("参照先とメールの件数を確認してください")
    clean_sources = []
    for source in sources:
        if isinstance(source, str):
            source = {"url": source}
        if not isinstance(source, dict) or set(source) - {"url", "evidence"}:
            raise ValueError("参照先の形式が正しくありません")
        entry = {"url": public_url(source.get("url"), True), "evidence": _text(source.get("evidence", ""), "根拠", 2000)}
        if entry not in clean_sources:
            clean_sources.append(entry)
    clean_contacts, seen = [], set()
    for contact in contacts:
        if not isinstance(contact, dict) or set(contact) - {"email", "source_url", "evidence", "attribution"}:
            raise ValueError("メールの調査結果が正しくありません")
        attribution = _text(contact.get("attribution"), "団体との対応", 30, True)
        if attribution not in {"club_context", "club_page"}:
            raise ValueError("団体に対応する公開根拠が必要です")
        entry = {"email": contact_email(contact.get("email")), "source_url": public_url(contact.get("source_url"), True),
                 "evidence": _text(contact.get("evidence"), "メールの根拠", 2000, True), "attribution": attribution}
        key = (entry["email"].casefold(), entry["source_url"])
        if key not in seen:
            clean_contacts.append(entry)
            seen.add(key)
    if status == "email_found" and not clean_contacts:
        raise ValueError("メールありには公開根拠付きメールが必要です")
    if status != "email_found" and clean_contacts:
        raise ValueError("未確認のメールは連絡先として保存できません")
    contact_form_url = public_url(raw.get("contact_form_url", ""))
    if status == "contact_form" and not contact_form_url:
        raise ValueError("問い合わせフォームのURLが必要です")
    return {"circle_id": circle_id, "status": status, "checked_at": _checked_at(raw.get("checked_at")),
            "sources": clean_sources, "contacts": clean_contacts,
            "note": _text(raw.get("note", raw.get("research_note", "")), "調査メモ", 4000),
            "contact_form_url": contact_form_url}


def import_results(conn, payload):
    """Atomically replace research results only; caller owns the outer commit.

    Accepts {job_id, results:[...]} or a bare list. At most 1,000 results per
    request. Repeating the same job and result does not create a revision.
    """
    if isinstance(payload, list):
        payload = {"results": payload}
    if not isinstance(payload, dict) or set(payload) - {"job_id", "results"}:
        raise ValueError("取り込みデータが正しくありません")
    results = payload.get("results")
    if not isinstance(results, list) or not results or len(results) > MAX_BATCH:
        raise ValueError("1回に1〜1,000件の調査結果を指定してください")
    try:
        size = len(json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8"))
    except (TypeError, ValueError, UnicodeError):
        raise ValueError("取り込みデータが正しくありません") from None
    if size > MAX_PAYLOAD_BYTES:
        raise ValueError("取り込みデータが大きすぎます")
    job_id = _text(payload.get("job_id", "manual"), "調査ジョブID", 120, True)
    records = [_record(raw) for raw in results]
    ids = [record["circle_id"] for record in records]
    if len(set(ids)) != len(ids):
        raise ValueError("同じ団体の結果が重複しています")
    # Validate before writing. This query is chunked below the common SQLite
    # 999-parameter limit, including a full 1,000-item batch.
    known = set()
    for start in range(0, len(ids), 500):
        chunk = ids[start:start + 500]
        known.update(row[0] for row in conn.execute("select circle_id from circles where circle_id in (" + ",".join("?" for _ in chunk) + ")", chunk))
    if known != set(ids):
        raise ValueError("存在しない団体IDが含まれています")
    updated, unchanged = 0, 0
    if not conn.in_transaction:
        conn.execute("begin")
    conn.execute("savepoint contact_research_import")
    try:
        for record in records:
            canonical = dict(record, job_id=job_id)
            # A retry without an explicit timestamp must also be idempotent.
            fingerprint = dict(canonical)
            fingerprint.pop("checked_at")
            result_hash = hashlib.sha256(json.dumps(fingerprint, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
            previous = conn.execute("select result_hash from circle_contact_research where circle_id=?", (record["circle_id"],)).fetchone()
            if previous and previous[0] == result_hash:
                unchanged += 1
                continue
            now = timestamp()
            conn.execute("""insert into circle_contact_research
                (circle_id,status,checked_at,job_id,sources_json,note,contact_form_url,result_hash,updated_at)
                values(?,?,?,?,?,?,?,?,?) on conflict(circle_id) do update set
                status=excluded.status,checked_at=excluded.checked_at,job_id=excluded.job_id,
                sources_json=excluded.sources_json,note=excluded.note,contact_form_url=excluded.contact_form_url,
                result_hash=excluded.result_hash,updated_at=excluded.updated_at""",
                (record["circle_id"], record["status"], record["checked_at"], job_id,
                 json.dumps(record["sources"], ensure_ascii=False), record["note"], record["contact_form_url"], result_hash, now))
            conn.execute("delete from circle_contact_research_emails where circle_id=?", (record["circle_id"],))
            conn.executemany("""insert into circle_contact_research_emails
                (circle_id,email,source_url,evidence,attribution) values(?,?,?,?,?)""",
                [(record["circle_id"], item["email"], item["source_url"], item["evidence"], item["attribution"]) for item in record["contacts"]])
            conn.execute("""insert into circle_contact_research_history(circle_id,job_id,checked_at,result_json,saved_at)
                values(?,?,?,?,?)""", (record["circle_id"], job_id, record["checked_at"], json.dumps(canonical, ensure_ascii=False), now))
            updated += 1
        conn.execute("release savepoint contact_research_import")
    except Exception:
        conn.execute("rollback to savepoint contact_research_import")
        conn.execute("release savepoint contact_research_import")
        raise
    return {"job_id": job_id, "received": len(records), "updated": updated, "unchanged": unchanged}


def summary(conn):
    total = conn.execute("select count(*) from circles").fetchone()[0]
    counts = {status: 0 for status in ("unresearched",) + STATUSES}
    for status, count in conn.execute("select r.status,count(*) from circle_contact_research r join circles c on c.circle_id=r.circle_id group by r.status"):
        counts[status] = count
    researched = sum(counts.values())
    counts["unresearched"] = max(0, total - researched)
    emails, distinct_emails = conn.execute("""select count(*),count(distinct lower(e.email)) from circle_contact_research_emails e
        join circles c on c.circle_id=e.circle_id""").fetchone()
    return {"total": total, "researched": researched, "remaining": counts["unresearched"],
            "with_email": counts["email_found"], "email_records": emails, "distinct_emails": distinct_emails, "statuses": counts}


def _dict_rows(cursor):
    columns = [item[0] for item in cursor.description]
    return [dict(zip(columns, row)) for row in cursor]


def query_results(conn, status="", q="", page=1, page_size=50):
    status = _text(status, "絞り込み", 30)
    q = _text(q, "検索", 200)
    if status and status not in ("unresearched",) + STATUSES:
        raise ValueError("絞り込みが正しくありません")
    if isinstance(page, bool) or isinstance(page_size, bool) or not isinstance(page, int) or not isinstance(page_size, int) or not 1 <= page <= 100000 or not 1 <= page_size <= 200:
        raise ValueError("ページの指定が正しくありません")
    conditions, values = [], []
    if status:
        conditions.append("r.circle_id is null" if status == "unresearched" else "r.status=?")
        if status != "unresearched":
            values.append(status)
    if q:
        conditions.append("(c.circle_name like ? or c.circle_id like ? or exists (select 1 from circle_contact_research_emails e where e.circle_id=c.circle_id and e.email like ?))")
        values.extend(["%" + q + "%"] * 3)
    joins = " from circles c left join circle_contact_research r on r.circle_id=c.circle_id"
    where = " where " + " and ".join(conditions) if conditions else ""
    total = conn.execute("select count(*)" + joins + where, values).fetchone()[0]
    rows = _dict_rows(conn.execute("""select c.circle_id,c.circle_name,c.source_url,
        coalesce(r.status,'unresearched') as status,coalesce(r.checked_at,'') as checked_at,
        coalesce(r.job_id,'') as job_id,coalesce(r.note,'') as note,
        coalesce(r.contact_form_url,'') as contact_form_url,coalesce(r.sources_json,'[]') as sources_json""" + joins + where +
        " order by c.circle_name,c.circle_id limit ? offset ?", values + [page_size, (page - 1) * page_size]))
    by_id = {row["circle_id"]: row for row in rows}
    for row in rows:
        row["sources"] = json.loads(row.pop("sources_json"))
        row["contacts"] = []
    if rows:
        for email in _dict_rows(conn.execute("select circle_id,email,source_url,evidence,attribution from circle_contact_research_emails where circle_id in (" + ",".join("?" for _ in rows) + ") order by email,source_url", list(by_id))):
            by_id[email.pop("circle_id")]["contacts"].append(email)
    return {"summary": summary(conn), "status": status, "q": q, "page": page, "page_size": page_size,
            "total": total, "pages": max(1, math.ceil(total / page_size)), "results": rows}


def _link(url, label):
    try:
        url = public_url(url, True)
    except ValueError:
        return escape(str(label))
    return '<a href="' + escape(url, quote=True) + '" target="_blank" rel="noopener noreferrer">' + escape(str(label)) + '</a>'


def render_admin_html(data, base_path="/admin/contact-research"):
    """Render a standalone admin document; authorization is the caller's job."""
    overview = data["summary"]
    options = '<option value="">すべて</option>' + "".join('<option value="' + code + '"' + (' selected' if data.get("status") == code else '') + '>' + label + '</option>' for code, label in STATUS_LABELS.items())
    rows = []
    for row in data["results"]:
        contacts = []
        for contact in row["contacts"]:
            address = contact_email(contact["email"])
            contacts.append('<div><a href="mailto:' + escape(quote(address, safe="@.+-"), quote=True) + '">' + escape(address) + '</a><br>' +
                            _link(contact["source_url"], "掲載元") + '<details><summary>公開根拠</summary><p>' + escape(contact["evidence"]) + '</p></details></div>')
        if row["contact_form_url"]:
            contacts.append(_link(row["contact_form_url"], "問い合わせフォーム"))
        evidence = "".join('<li>' + _link(source["url"], source["url"]) + ('<p>' + escape(source["evidence"]) + '</p>' if source.get("evidence") else '') + '</li>' for source in row["sources"])
        rows.append('<tr><td><strong>' + escape(row["circle_name"] or row["circle_id"]) + '</strong><br><small>' + escape(row["circle_id"]) + '</small><br>' +
                    (_link(row["source_url"], "DBの参照先") if row["source_url"] else '') + '</td><td><span class="badge">' + escape(STATUS_LABELS.get(row["status"], row["status"])) + '</span><br><small>' + escape(row["checked_at"]) + '</small></td><td>' +
                    ('<div class="contacts">' + "".join(contacts) + '</div>' if contacts else '—') + '</td><td>' +
                    ('<details><summary>調査した参照先</summary><ul>' + evidence + '</ul></details>' if evidence else '') +
                    ('<p>' + escape(row["note"]) + '</p>' if row["note"] else '') + '<small>' + escape(row["job_id"]) + '</small></td></tr>')
    pager = []
    for number, label in ((data["page"] - 1, "前のページ"), (data["page"] + 1, "次のページ")):
        if 1 <= number <= data["pages"]:
            href = base_path + "?page=" + str(number) + "&status=" + quote(data.get("status", "")) + "&q=" + quote(data.get("q", ""))
            pager.append('<a href="' + escape(href, quote=True) + '">' + label + '</a>')
    return '''<!doctype html><html lang="ja"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex,nofollow"><meta name="referrer" content="no-referrer"><title>サークル連絡先の調査 | Circle Match 管理</title><style>
body{font:15px/1.6 system-ui,sans-serif;color:#172b3a;background:#f5f7fa;margin:0;padding:24px}main{max-width:1400px;margin:auto}a{color:#096cb0}h1{font-size:24px;margin:0 0 8px}.summary{display:flex;gap:12px;flex-wrap:wrap;margin:20px 0}.summary span,form{background:white;border:1px solid #dce3eb;border-radius:8px;padding:12px}form{display:flex;align-items:center;gap:10px;flex-wrap:wrap}input,select,button{font:inherit;padding:7px;border:1px solid #c7d2de;border-radius:5px}.table-wrap{overflow:auto;margin-top:18px}table{width:100%;border-collapse:collapse;background:white}th,td{text-align:left;vertical-align:top;border:1px solid #dce3eb;padding:12px}th{background:#edf2f7}.badge{display:inline-block;border-radius:20px;background:#e8f0f6;padding:2px 10px;white-space:nowrap}small{color:#526676}td p{max-width:420px;white-space:pre-wrap;overflow-wrap:anywhere}td a,li{overflow-wrap:anywhere}.contacts{min-width:220px}.contacts>div+div{margin-top:12px}nav{display:flex;gap:16px;margin:18px 0}@media(max-width:600px){body{padding:12px}th,td{padding:8px}}
</style></head><body><main><h1>サークル連絡先の調査</h1><p>管理者専用。公式ページ等に掲載された連絡先と公開根拠を記録します。調査したメールは公開プロフィールへ追加されません。</p><div class="summary">''' + "".join('<span>' + label + ' <strong>' + str(overview[key]) + '</strong></span>' for key, label in (("total", "対象団体"), ("researched", "調査済み"), ("remaining", "未調査"), ("with_email", "メールあり"), ("distinct_emails", "メール数"))) + '</div><form method="get" action="' + escape(base_path, quote=True) + '"><label>調査状況 <select name="status">' + options + '</select></label><label>団体・メール <input name="q" value="' + escape(data.get("q", ""), quote=True) + '"></label><button>絞り込む</button><a href="' + escape(base_path + '.csv', quote=True) + '">CSVを保存</a></form><p>' + str(data["total"]) + '件・' + str(data["page"]) + ' / ' + str(data["pages"]) + 'ページ</p><div class="table-wrap"><table><thead><tr><th>団体</th><th>調査状況</th><th>公開されている連絡先</th><th>根拠・調査メモ</th></tr></thead><tbody>' + ("".join(rows) or '<tr><td colspan="4">該当する団体はありません。</td></tr>') + '</tbody></table></div><nav>' + "".join(pager) + '</nav></main></body></html>'


def _csv_cell(value):
    value = str(value or "")
    # Spreadsheet exports must not execute club-provided names or snippets.
    return "'" + value if value.lstrip().startswith(("=", "+", "-", "@")) or value.startswith(("\t", "\r", "\n")) else value


def export_csv(conn):
    """Export all circles, including unresearched ones, for authenticated admins."""
    output = StringIO(newline="")
    writer = csv.writer(output)
    writer.writerow(("circle_id", "circle_name", "status", "checked_at", "email", "source_url", "evidence", "attribution", "contact_form_url", "research_note", "job_id"))
    page = 1
    while True:
        data = query_results(conn, page=page, page_size=200)
        for row in data["results"]:
            for contact in row["contacts"] or [{}]:
                writer.writerow([_csv_cell(value) for value in (row["circle_id"], row["circle_name"], row["status"], row["checked_at"],
                    contact.get("email", ""), contact.get("source_url", ""), contact.get("evidence", ""), contact.get("attribution", ""),
                    row["contact_form_url"], row["note"], row["job_id"])])
        if page >= data["pages"]:
            break
        page += 1
    return output.getvalue()
