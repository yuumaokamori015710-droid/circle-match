import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path("outputs/circlematch.sqlite")
SOURCE_URL = "https://www.kansai-football.jp/division/"
NOTE = "関西学生アメリカンフットボールリーグ公式リーグ情報から、大学名・チーム名のみ登録"

TEAMS = [
    ("神戸大学", "アメリカンフットボール部 レイバンズ", "兵庫県神戸市"),
    ("京都大学", "アメリカンフットボール部 ギャングスターズ", "京都府京都市"),
    ("大阪大学", "アメリカンフットボール部 トライデンツ", "大阪府吹田市"),
    ("和歌山大学", "アメリカンフットボール部 ブラインド シャークス", "和歌山県和歌山市"),
    ("鳥取大学", "アメリカンフットボール部 レイカース", "鳥取県鳥取市"),
    ("滋賀大学", "アメリカンフットボール部 グラディエイターズ", "滋賀県彦根市"),
    ("徳島大学", "アメリカンフットボール部 パイレーツ", "徳島県徳島市"),
    ("岡山大学", "アメリカンフットボール部 バジャーズ", "岡山県岡山市"),
]


def now():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def slug(prefix, text):
    base = "".join(ch.lower() if ch.isalnum() else "_" for ch in text).strip("_")
    return f"{prefix}_{base[:48]}"


def audit(conn, action, entity_type, entity_id, payload):
    conn.execute(
        "insert into audit_logs(action, entity_type, entity_id, payload, created_at) values(?,?,?,?,?)",
        (action, entity_type, entity_id, json.dumps(payload, ensure_ascii=False), now()),
    )


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    inserted = 0
    updated = 0
    for university_name, circle_name, area in TEAMS:
        uni = conn.execute(
            "select university_id from universities where university_name=? order by campus_name limit 1",
            (university_name,),
        ).fetchone()
        if not uni:
            continue
        existing = conn.execute(
            "select circle_id from circles where university_id=? and circle_name=?",
            (uni["university_id"], circle_name),
        ).fetchone()
        circle_id = existing["circle_id"] if existing else slug("c", uni["university_id"] + "_" + circle_name)
        timestamp = now()
        conn.execute(
            """
            insert into circles(circle_id, university_id, circle_name, sport_category, activity_area, source_type, source_url,
              verification_status, public_status, last_checked_at, sns_url, owner_notes, created_at, updated_at)
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
                "アメリカンフットボール",
                area,
                "other",
                SOURCE_URL,
                "admin_verified",
                "published",
                now()[:10],
                "",
                NOTE,
                timestamp,
                timestamp,
            ),
        )
        conn.execute(
            "insert or replace into data_sources(source_id, entity_type, entity_id, source_type, source_url, memo, checked_at, created_at) values(?,?,?,?,?,?,?,?)",
            (slug("src", circle_id + SOURCE_URL), "circle", circle_id, "other", SOURCE_URL, NOTE, now()[:10], timestamp),
        )
        audit(conn, "real_data_import", "circle", circle_id, {
            "university": university_name,
            "circle_name": circle_name,
            "source_url": SOURCE_URL,
        })
        if existing:
            updated += 1
        else:
            inserted += 1
    conn.commit()
    print(json.dumps({
        "inserted": inserted,
        "updated": updated,
        "total_circles": conn.execute("select count(*) from circles").fetchone()[0],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
