import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path("outputs/circlematch.sqlite")
UNIVERSITY_NAME = "中央大学"
SOURCE_URL = "https://www.chuo-u.ac.jp/activities/club/"
SOURCE_MEMO = "中央大学公式サイトの部会活動ページで、体育連盟所属部会として確認。紹介文・画像は保存せず、団体名、競技、出典URLのみ登録。"


def now():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def slug(prefix, text):
    base = "".join(ch.lower() if ch.isalnum() else "_" for ch in text).strip("_")
    return f"{prefix}_{base[:80]}"


OFFICIAL_CLUBS = [
    ("硬式野球部", "野球"),
    ("サッカー部", "サッカー"),
    ("硬式庭球部", "テニス"),
    ("バスケットボール部", "バスケットボール"),
    ("バレーボール部", "バレーボール"),
    ("バレーボール部(女子)", "バレーボール"),
    ("バドミントン部", "バドミントン"),
    ("ラグビー部", "ラグビー"),
    ("アメリカンフットボール部", "アメリカンフットボール"),
    ("ラクロス部", "ラクロス"),
    ("女子ラクロス部", "ラクロス"),
    ("水泳部", "水泳"),
    ("卓球部", "卓球"),
    ("女子卓球部", "卓球"),
    ("ハンドボール部", "ハンドボール"),
    ("陸上競技部", "陸上競技"),
    ("女子陸上競技部", "陸上競技"),
    ("ホッケー部", "ホッケー"),
]


def audit(conn, action, entity_type, entity_id, payload):
    conn.execute(
        "insert into audit_logs(action, entity_type, entity_id, payload, created_at) values(?,?,?,?,?)",
        (action, entity_type, entity_id, json.dumps(payload, ensure_ascii=False), now()),
    )


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    timestamp = now()

    uni = conn.execute(
        "select university_id from universities where university_name=? order by campus_name limit 1",
        (UNIVERSITY_NAME,),
    ).fetchone()
    if not uni:
        raise SystemExit(f"university not found: {UNIVERSITY_NAME}")

    inserted = 0
    updated = 0
    for circle_name, sport_category in OFFICIAL_CLUBS:
        existing = conn.execute(
            "select circle_id from circles where university_id=? and circle_name=?",
            (uni["university_id"], circle_name),
        ).fetchone()
        circle_id = existing["circle_id"] if existing else slug("c", f"{uni['university_id']}_{circle_name}")
        conn.execute(
            """
            insert into circles(
              circle_id, university_id, circle_name, sport_category, activity_area,
              source_type, source_url, verification_status, public_status,
              last_checked_at, sns_url, owner_notes, created_at, updated_at
            )
            values(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            on conflict(university_id, circle_name) do update set
              sport_category=excluded.sport_category,
              activity_area=excluded.activity_area,
              source_type=excluded.source_type,
              source_url=excluded.source_url,
              verification_status=excluded.verification_status,
              public_status=excluded.public_status,
              last_checked_at=excluded.last_checked_at,
              owner_notes=excluded.owner_notes,
              updated_at=excluded.updated_at
            """,
            (
                circle_id,
                uni["university_id"],
                circle_name,
                sport_category,
                "中央大学",
                "university_official",
                SOURCE_URL,
                "university_verified",
                "published",
                timestamp[:10],
                "",
                SOURCE_MEMO,
                timestamp,
                timestamp,
            ),
        )
        conn.execute(
            """
            insert or replace into data_sources(
              source_id, entity_type, entity_id, source_type, source_url, memo, checked_at, created_at
            )
            values(?,?,?,?,?,?,?,?)
            """,
            (
                slug("src", f"{circle_id}_{SOURCE_URL}"),
                "circle",
                circle_id,
                "university_official",
                SOURCE_URL,
                SOURCE_MEMO,
                timestamp[:10],
                timestamp,
            ),
        )
        audit(
            conn,
            "official_university_club_import",
            "circle",
            circle_id,
            {
                "university": UNIVERSITY_NAME,
                "circle_name": circle_name,
                "sport_category": sport_category,
                "source_url": SOURCE_URL,
            },
        )
        if existing:
            updated += 1
        else:
            inserted += 1

    conn.execute(
        """
        insert into collection_targets(
          university_id, collection_status, priority, source_search_query,
          source_url, notes, last_checked_at, updated_at
        )
        values(?,?,?,?,?,?,?,?)
        on conflict(university_id) do update set
          collection_status=excluded.collection_status,
          source_url=excluded.source_url,
          notes=excluded.notes,
          last_checked_at=excluded.last_checked_at,
          updated_at=excluded.updated_at
        """,
        (
            uni["university_id"],
            "completed",
            1,
            "中央大学 体育連盟 主要競技",
            SOURCE_URL,
            "主要競技の体育連盟部会を大学公式ページから登録済み。同好会・理工連盟・準公認部会は未収集。",
            timestamp[:10],
            timestamp,
        ),
    )
    conn.execute(
        """
        insert into collection_runs(
          run_id, target_scope, status, collected_count, candidate_count, memo, started_at, finished_at
        )
        values(?,?,?,?,?,?,?,?)
        """,
        (
            slug("run", f"chuo_official_sports_{timestamp}"),
            "Phase 1: 中央大学 x 主要競技",
            "completed",
            inserted + updated,
            0,
            "大学公式の部会活動ページから体育連盟の主要競技のみ登録。紹介文・画像・レビュー・ランキングは未使用。",
            timestamp,
            now(),
        ),
    )
    conn.commit()
    summary = {
        "university": UNIVERSITY_NAME,
        "inserted": inserted,
        "updated": updated,
        "source_url": SOURCE_URL,
        "total_circles": conn.execute("select count(*) from circles").fetchone()[0],
        "verified_circles": conn.execute(
            "select count(*) from circles where verification_status in ('university_verified','admin_verified')"
        ).fetchone()[0],
        "candidates": conn.execute("select count(*) from circle_candidates").fetchone()[0],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
