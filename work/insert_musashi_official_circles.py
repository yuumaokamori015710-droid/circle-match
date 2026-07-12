from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path


DB_PATH = Path("outputs/circlematch.sqlite")
SOURCE_URL = "https://www.musashi.ac.jp/campuslife/club_circle/list.html"
UNIVERSITY_NAME = "武蔵大学"
NOTE = "武蔵大学公式のクラブ・サークル一覧から団体名のみ登録"


class TextParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.parts: list[str] = []

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if text:
            self.parts.append(text)


def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def slug(prefix: str, text: str) -> str:
    base = "".join(ch.lower() if ch.isalnum() else "_" for ch in text).strip("_")
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]
    return f"{prefix}_{base[:40]}_{digest}"


def sport_category(name: str) -> str:
    rules = [
        ("サッカー", ["サッカー", "蹴球"]),
        ("フットサル", ["フットサル"]),
        ("バスケットボール", ["バスケット"]),
        ("テニス", ["テニス", "庭球"]),
        ("バレーボール", ["バレーボール"]),
        ("野球", ["野球"]),
        ("バドミントン", ["バドミントン"]),
        ("ラグビー", ["ラグビー"]),
        ("アメリカンフットボール", ["アメリカンフットボール"]),
        ("ラクロス", ["ラクロス"]),
        ("ハンドボール", ["ハンドボール"]),
        ("ホッケー", ["ホッケー"]),
        ("卓球", ["卓球"]),
        ("陸上競技", ["陸上"]),
        ("水泳", ["水泳", "スキューバ"]),
        ("武道", ["合気道", "空手", "弓道", "剣道", "柔道", "少林寺", "テコンドー"]),
    ]
    for category, needles in rules:
        if any(needle in name for needle in needles):
            return category
    return "その他"


def organization_type(name: str) -> str:
    return "部活" if name.endswith("部") or "應援団" in name else "公認サークル"


def fetch_parts() -> list[str]:
    request = urllib.request.Request(SOURCE_URL, headers={"User-Agent": "Mozilla/5.0"})
    html = urllib.request.urlopen(request, timeout=30).read().decode("utf-8", "ignore")
    parser = TextParser()
    parser.feed(html)
    return parser.parts


def extract_names(parts: list[str]) -> list[str]:
    stopwords = {
        "体育連合会（部）",
        "文化団体連合会（部）",
        "学友会公認団体（体育系サークル）",
        "学友会公認団体（文化系サークル）",
        "学友会登録団体（体育系サークル）",
        "学友会登録団体（文化系サークル）",
        "独立団体など",
        "研究会",
        "（ポーカー）",
        "All in Musashi",
        "TRPG&",
        "Web",
        "マガジン編集部",
        "お散歩サークル（旧：文化研究会）",
        "武蔵",
        "e",
        "スポーツサークル",
        "A’t",
        "（ボランティア）",
    }
    raw = parts[100:216]
    names: list[str] = []
    for name in raw:
        name = re.sub(r"\s+", " ", name).strip()
        if not name or name in stopwords:
            continue
        if len(name) > 70:
            continue
        names.append(name)
    names.extend(
        [
            "TRPG&ボードゲーム同好会",
            "All in Musashi（ポーカー）",
            "武蔵eスポーツサークル",
            "Webマガジン編集部",
            "お散歩サークル",
            "A't（ボランティア）",
        ]
    )
    return list(dict.fromkeys(names))


def delete_noise(conn: sqlite3.Connection, university_id: str) -> int:
    noise_names = [
        "All in Musashi",
        "TRPG&",
        "Web",
        "マガジン編集部",
        "Web展覧会",
        "利用可能団体",
        "舞踏研究部（白雉祭）",
        "モダンジャズ研究会（白雉祭）",
    ]
    deleted = 0
    for name in noise_names:
        rows = conn.execute(
            "select circle_id from circles where university_id=? and circle_name=?",
            (university_id, name),
        ).fetchall()
        for (circle_id,) in rows:
            conn.execute("delete from data_sources where entity_type='circle' and entity_id=?", (circle_id,))
            conn.execute("delete from circles where circle_id=?", (circle_id,))
            deleted += 1
    return deleted


def audit(conn: sqlite3.Connection, action: str, entity_id: str, payload: dict[str, str]) -> None:
    conn.execute(
        "insert into audit_logs(action, entity_type, entity_id, payload, created_at) values(?,?,?,?,?)",
        (action, "circle", entity_id, json.dumps(payload, ensure_ascii=False), now()),
    )


def upsert_circle(conn: sqlite3.Connection, university_id: str, circle_name: str) -> int:
    timestamp = now()
    circle_id = slug("c", f"{university_id}_{circle_name}")
    before = conn.execute(
        "select circle_id from circles where university_id=? and circle_name=?",
        (university_id, circle_name),
    ).fetchone()
    conn.execute(
        """
        insert into circles(
          circle_id, university_id, circle_name, sport_category, activity_area,
          source_type, source_url, verification_status, public_status, last_checked_at,
          sns_url, owner_notes, created_at, updated_at, organization_type
        )
        values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        on conflict(university_id, circle_name) do update set
          sport_category=excluded.sport_category,
          source_type=excluded.source_type,
          source_url=excluded.source_url,
          verification_status=excluded.verification_status,
          public_status=excluded.public_status,
          last_checked_at=excluded.last_checked_at,
          owner_notes=excluded.owner_notes,
          updated_at=excluded.updated_at,
          organization_type=excluded.organization_type
        """,
        (
            circle_id,
            university_id,
            circle_name,
            sport_category(circle_name),
            "東京都 練馬区",
            "university_official",
            SOURCE_URL,
            "university_verified",
            "published",
            now()[:10],
            "",
            NOTE,
            timestamp,
            timestamp,
            organization_type(circle_name),
        ),
    )
    saved_id = conn.execute(
        "select circle_id from circles where university_id=? and circle_name=?",
        (university_id, circle_name),
    ).fetchone()[0]
    conn.execute(
        "insert or replace into data_sources(source_id, entity_type, entity_id, source_type, source_url, memo, checked_at, created_at) values(?,?,?,?,?,?,?,?)",
        (slug("src", saved_id + SOURCE_URL), "circle", saved_id, "university_official", SOURCE_URL, NOTE, now()[:10], timestamp),
    )
    if before:
        return 0
    audit(conn, "musashi_official_import", saved_id, {"university": UNIVERSITY_NAME, "circle_name": circle_name, "source_url": SOURCE_URL})
    return 1


def main() -> None:
    parts = fetch_parts()
    names = extract_names(parts)
    conn = sqlite3.connect(DB_PATH)
    university = conn.execute(
        "select university_id from universities where university_name=? order by campus_name limit 1",
        (UNIVERSITY_NAME,),
    ).fetchone()
    if not university:
        raise RuntimeError(f"university not found: {UNIVERSITY_NAME}")
    deleted = delete_noise(conn, university[0])
    inserted = sum(upsert_circle(conn, university[0], name) for name in names)
    conn.commit()
    total = conn.execute(
        """
        select count(*)
        from circles c
        join universities u on u.university_id = c.university_id
        where u.university_name = ? and c.public_status = 'published'
        """,
        (UNIVERSITY_NAME,),
    ).fetchone()[0]
    print(json.dumps({"names": len(names), "inserted": inserted, "deleted_noise": deleted, "total": total}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
