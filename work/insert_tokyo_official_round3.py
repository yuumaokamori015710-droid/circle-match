import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


DB_PATH = Path(__file__).resolve().parents[1] / "outputs" / "circlematch.sqlite"


SOURCE_URL = "https://www.thu.ac.jp/campuslife/club/"


CLUBS = {
    "帝京平成大学": [
        "スポーツ局 メディア部",
        "eスポーツ部",
        "軽音楽サークル",
        "少林寺拳法会",
        "スキースノーボードサークル",
        "帝京平成大学公認サークルENJ∞Y",
        "ハンドボール部",
        "吹奏楽部",
        "バドミントン部",
        "地域連携部",
        "合唱部",
        "生薬サークル",
        "帝京平成大学バーベルクラブ",
        "舞台芸術サークル",
        "福祉サークル Can plus+",
        "ゴルフ部",
        "バレーボール部",
        "硬式テニス部",
        "陸上競技部 長距離ブロック",
        "陸上競技部 短距離ブロック",
        "パラスポーツサポート部",
        "バスケサークル",
        "軟式テニスサークル",
    ],
}


def now():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def slug(prefix, text):
    base = "".join(ch.lower() if ch.isalnum() else "_" for ch in text).strip("_")
    return f"{prefix}_{base[:96]}"


def sport_category(name):
    rules = [
        ("テニス", ["テニス"]), ("バスケットボール", ["バスケ", "バスケット"]),
        ("バレーボール", ["バレーボール"]), ("バドミントン", ["バドミントン"]),
        ("陸上競技", ["陸上"]), ("ハンドボール", ["ハンドボール"]), ("ゴルフ", ["ゴルフ"]),
        ("スキー", ["スキー", "スノーボード"]), ("武道", ["少林寺拳法"]),
        ("音楽", ["軽音", "吹奏楽", "合唱"]), ("演劇", ["舞台芸術", "演劇"]),
        ("ボランティア", ["福祉", "地域連携", "パラスポーツ"]), ("ゲーム", ["eスポーツ"]),
    ]
    for category, needles in rules:
        if any(needle in name for needle in needles):
            return category
    return "その他"


def organization_type(name):
    if any(word in name for word in ["局", "地域連携", "サポート"]):
        return "学生団体"
    if "部" in name or "クラブ" in name:
        return "部活"
    return "公認サークル"


def audit(conn, action, entity_type, entity_id, payload, timestamp):
    conn.execute(
        "insert into audit_logs(action, entity_type, entity_id, payload, created_at) values(?,?,?,?,?)",
        (action, entity_type, entity_id, json.dumps(payload, ensure_ascii=False), timestamp),
    )


def upsert(conn, university_name, circle_name, timestamp):
    university = conn.execute(
        "select university_id from universities where university_name=? order by campus_name limit 1",
        (university_name,),
    ).fetchone()
    if not university:
        raise RuntimeError(f"university not found: {university_name}")
    circle_name = re.sub(r"\s+", " ", circle_name).strip()
    existing = conn.execute(
        "select circle_id from circles where university_id=? and circle_name=?",
        (university["university_id"], circle_name),
    ).fetchone()
    circle_id = existing["circle_id"] if existing else slug("c", f"{university['university_id']}_{circle_name}")
    memo = "帝京平成大学公式サイトの部活・サークルページで確認。団体名、活動区分、出典URLのみ登録。"
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
            circle_id, university["university_id"], circle_name, organization_type(circle_name),
            sport_category(circle_name), "東京都", "university_official", SOURCE_URL,
            "university_verified", "published", timestamp[:10], "", memo, timestamp, timestamp,
        ),
    )
    conn.execute(
        """
        insert or replace into data_sources(
          source_id, entity_type, entity_id, source_type, source_url, memo, checked_at, created_at
        )
        values(?,?,?,?,?,?,?,?)
        """,
        (slug("src", f"{circle_id}_{SOURCE_URL}"), "circle", circle_id, "university_official", SOURCE_URL, memo, timestamp[:10], timestamp),
    )
    audit(conn, "official_tokyo_round3_import", "circle", circle_id, {
        "university": university_name,
        "circle_name": circle_name,
        "source_url": SOURCE_URL,
    }, timestamp)
    return 0 if existing else 1


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    timestamp = now()
    inserted = 0
    updated = 0
    for university_name, names in CLUBS.items():
        for name in names:
            is_insert = upsert(conn, university_name, name, timestamp)
            inserted += is_insert
            updated += 1 - is_insert
    conn.execute(
        """
        insert into collection_runs(run_id, target_scope, status, collected_count, candidate_count, memo, started_at, finished_at)
        values(?,?,?,?,?,?,?,?)
        """,
        (
            slug("run", f"tokyo_official_round3_{timestamp}"),
            "Tokyo official zero-count universities round 3",
            "completed",
            inserted + updated,
            0,
            "帝京平成大学の公式部活・サークルページに表示された主要団体名のみ登録。",
            timestamp,
            now(),
        ),
    )
    conn.commit()
    print(json.dumps({
        "inserted": inserted,
        "updated": updated,
        "total_circles": conn.execute("select count(*) from circles").fetchone()[0],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
