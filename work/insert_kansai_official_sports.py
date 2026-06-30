import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


DB_PATH = Path("outputs/circlematch.sqlite")
UNIVERSITY_NAME = "関西大学"
SOURCE_URL = "https://www.kansai-u.ac.jp/sports/activity/group/"
SOURCE_MEMO = (
    "関西大学スポーツ振興グループ公式のクラブ一覧で確認。"
    "紹介文・画像・レビュー・ランキングは保存せず、団体名、競技、出典URLのみ登録。"
)


OFFICIAL_CLUBS = [
    ("アーチェリー部", "アーチェリー"),
    ("合気道部", "武道"),
    ("アイススケート部", "スケート"),
    ("アイスホッケー部", "ホッケー"),
    ("アメリカンフットボール部", "アメリカンフットボール"),
    ("空手道部", "武道"),
    ("器械体操部", "体操"),
    ("弓道部", "武道"),
    ("剣道部", "武道"),
    ("拳法部", "武道"),
    ("航空部", "航空"),
    ("古武道部", "武道"),
    ("ゴルフ部", "ゴルフ"),
    ("サッカー部", "サッカー"),
    ("自転車部", "自転車"),
    ("自動車部", "自動車"),
    ("射撃部", "射撃"),
    ("柔道部", "武道"),
    ("重量挙部", "重量挙"),
    ("準硬式野球部", "野球"),
    ("少林寺拳法部", "武道"),
    ("水上競技部", "水泳"),
    ("スキー競技部", "スキー"),
    ("相撲部", "武道"),
    ("漕艇部", "ボート"),
    ("ソフトテニス部", "テニス"),
    ("ソフトボール部", "ソフトボール"),
    ("卓球部", "卓球"),
    ("テニス部", "テニス"),
    ("なぎなた部", "武道"),
    ("馬術部", "馬術"),
    ("バスケットボール部", "バスケットボール"),
    ("バドミントン部", "バドミントン"),
    ("バレーボール部", "バレーボール"),
    ("ハンドボール部", "ハンドボール"),
    ("フェンシング部", "フェンシング"),
    ("ボクシング部", "ボクシング"),
    ("ホッケー部", "ホッケー"),
    ("野球部", "野球"),
    ("ヨット部", "ヨット"),
    ("ラグビー部", "ラグビー"),
    ("陸上競技部", "陸上競技"),
    ("レスリング部", "レスリング"),
    ("ワンダーフォーゲル部", "アウトドア"),
]


def now():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def slug(prefix, text):
    base = "".join(ch.lower() if ch.isalnum() else "_" for ch in text).strip("_")
    return f"{prefix}_{base[:80]}"


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
              circle_id, university_id, circle_name, organization_type, sport_category, activity_area,
              source_type, source_url, verification_status, public_status,
              last_checked_at, sns_url, owner_notes, created_at, updated_at
            )
            values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            on conflict(university_id, circle_name) do update set
              organization_type=excluded.organization_type,
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
                "体育会",
                sport_category,
                UNIVERSITY_NAME,
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
          priority=excluded.priority,
          source_url=excluded.source_url,
          notes=excluded.notes,
          last_checked_at=excluded.last_checked_at,
          updated_at=excluded.updated_at
        """,
        (
            uni["university_id"],
            "partial",
            2,
            "関西大学 体育会 クラブ一覧 公式",
            SOURCE_URL,
            "公式スポーツ振興グループの体育会44クラブを登録済み。文化系・公認サークルは未収集。",
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
            slug("run", f"kansai_official_sports_{timestamp}"),
            "Phase 1: 関西大学 x 体育会主要競技",
            "completed",
            inserted + updated,
            0,
            "関西大学公式スポーツ振興グループのクラブ一覧から体育会44クラブを登録。紹介文・画像・レビュー・ランキングは未使用。",
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
        "total_universities": conn.execute("select count(*) from universities").fetchone()[0],
        "total_circles": conn.execute("select count(*) from circles").fetchone()[0],
        "verified_circles": conn.execute(
            "select count(*) from circles where verification_status in ('university_verified','admin_verified')"
        ).fetchone()[0],
        "candidates": conn.execute("select count(*) from circle_candidates").fetchone()[0],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
