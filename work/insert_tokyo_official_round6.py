import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


DB_PATH = Path(__file__).resolve().parents[1] / "outputs" / "circlematch.sqlite"
SOURCE_URL = "https://www.jwu.ac.jp/unv/campuslife/extracurricular/circle/index.html"


CLUBS = {
    "日本女子大学": [
        "CHSボランティアサークル", "NEJIRO", "WASA", "青空子ども会Ⅱ", "駒場子ども会",
        "仙人掌", "史学舎", "児童文学研究会ひなぎく", "手話サークル HAND IN HAND",
        "日本女子大学映画研究会", "日本女子大学かるた会", "日本女子大学レゴサークル",
        "ぱすます", "放送研究会（J.W.B.C.）", "漫画研究会まるぼつ", "メディア研究会Plus",
        "みっふぃー", "Theatre MERCURY", "池坊華道部", "観世流能楽研究会",
        "劇団ピアチェーレ", "茶道部表千家", "茶道部裏千家", "写真部", "書道研究会",
        "草月流華道部", "日本女子大学短歌会", "美術サークル", "BANDS'",
        "軽音楽研究会", "シャンソン研究会", "箏曲研究会", "日本女子大学オーケストラ",
        "日本女子大学合唱団", "日本女子大学コール・クライネス", "日本女子大学緑会合唱団",
        "マンドリンクラブ", "合気道部", "弓道部", "競技ダンス部", "剣道部",
        "硬式庭球部", "ゴルフ部", "少林寺拳法部", "水泳部", "バスケットボール部",
        "バレーボール部", "フィギュアスケート部", "ラクロス部", "陸上競技部",
        "F.S.S.テニスクラブ", "T.E.A.", "TECK2（テクテク）", "オリエンテーリング・クラブ",
        "卓球部", "日本女子大学フィールドアーチェリー同好会", "バドミントンサークルbitter-ender",
        "ワンダーフォーゲル部", "JWUフットサルサークル",
    ],
}


def now():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def slug(prefix, text):
    base = "".join(ch.lower() if ch.isalnum() else "_" for ch in text).strip("_")
    return f"{prefix}_{base[:96]}"


def sport_category(name):
    rules = [
        ("サッカー", ["フットサル"]), ("テニス", ["テニス", "庭球"]),
        ("バスケットボール", ["バスケット"]), ("バレーボール", ["バレーボール"]),
        ("バドミントン", ["バドミントン"]), ("ラクロス", ["ラクロス"]), ("陸上競技", ["陸上"]),
        ("水泳", ["水泳"]), ("卓球", ["卓球"]), ("ゴルフ", ["ゴルフ"]), ("スキー", ["フィギュアスケート"]),
        ("アウトドア", ["登山", "ワンダーフォーゲル", "オリエンテーリング"]),
        ("武道", ["合気道", "弓道", "剣道", "少林寺拳法"]), ("ダンス", ["ダンス"]),
        ("音楽", ["軽音", "シャンソン", "箏曲", "オーケストラ", "合唱", "コール", "マンドリン", "BANDS"]),
        ("写真", ["写真"]), ("演劇", ["Theatre", "劇団", "能楽"]), ("放送", ["放送"]),
        ("ボランティア", ["ボランティア", "子ども会"]), ("茶道", ["茶道"]), ("華道", ["華道"]),
        ("漫画", ["漫画"]), ("映画", ["映画"]), ("美術", ["美術", "書道"]), ("文学", ["短歌", "児童文学"]),
        ("ゲーム", ["レゴ"]),
    ]
    for category, needles in rules:
        if any(needle in name for needle in needles):
            return category
    return "その他"


def organization_type(name):
    if "部" in name:
        return "部活"
    if "同好会" in name:
        return "公認サークル"
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
    memo = "日本女子大学公式サイトの公認サークル一覧で確認。団体名、活動区分、出典URLのみ登録。"
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
    audit(conn, "official_tokyo_round6_import", "circle", circle_id, {
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
            slug("run", f"tokyo_official_round6_{timestamp}"),
            "Tokyo official zero-count universities round 6",
            "completed",
            inserted + updated,
            0,
            "日本女子大学公式公認サークル一覧から団体名のみ登録。",
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
