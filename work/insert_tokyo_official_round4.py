import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


DB_PATH = Path(__file__).resolve().parents[1] / "outputs" / "circlematch.sqlite"
SOURCE_URL = "https://www.t-kougei.ac.jp/campuslife/club/"


CLUBS = {
    "東京工芸大学": [
        "厚木学友会本部", "中野学友会本部", "学園祭実行委員会", "中野祭実行委員会",
        "厚木体育部協議会本部", "中野体育部協議会", "厚木文化部協議会本部", "中野文化部協議会",
        "学生生協委員会", "弓道部", "剣道部", "硬式庭球部", "硬式野球部", "卓球部",
        "ダンス部（Polytechnics）", "バドミントン部", "モーターサイクル部", "演劇部（劇団茶柱）",
        "からくり工房", "軽音楽部", "K.A.F.建築サークル", "コスプレ部", "サウンド研究会",
        "茶道部", "JAZZ研究会", "報道写真部", "カラー写真部", "学友会写真部", "FOTO.ism",
        "学友会吹奏楽団", "TRPG-club", "TPU映像制作サークル", "天文部", "特撮研究部",
        "プログラミング研究会", "マンガ・デザイン研究会", "服飾同好会", "ドローンサイエンス研究会",
        "カラオーケストラ同好会", "アニメ漫画サークル", "競技麻雀同好会", "スポーツサークル",
        "デザイン研究会", "バトミントンサークル", "フットサルサークル", "アウトドアサークル",
        "バスケ＆サッカー", "勉強会サークル", "颯と愉快な仲間たち", "ソフトテニスサークル",
        "軟式野球サークル", "フットボールサークル", "現代視覚文化研究会",
        "DAG(DeepLearningStudy Group)", "アクティブスポーツ", "ハードソフト研究会",
        "ゲーム制作同好会 TRacKer", "軌道空間研究会", "ボードゲームサークル",
        "バレーボールサークル", "Ske部(同好会)", "ゲーム研究会「Unlimited Advance」",
        "バスケットボール同好会", "ホラー研究会", "紅芸館", "自主制作同好会",
        "e-sports同好会", "BDH (Be-Do-Have)", "スキー同好会", "ショートフィルム同好会",
        "演技映画同好会", "建築研究会",
    ],
}


def now():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def slug(prefix, text):
    base = "".join(ch.lower() if ch.isalnum() else "_" for ch in text).strip("_")
    return f"{prefix}_{base[:96]}"


def sport_category(name):
    rules = [
        ("野球", ["野球"]), ("サッカー", ["サッカー", "フットサル", "フットボール"]),
        ("テニス", ["テニス", "庭球"]), ("バスケットボール", ["バスケ", "バスケット"]),
        ("バレーボール", ["バレーボール"]), ("バドミントン", ["バドミントン", "バトミントン"]),
        ("卓球", ["卓球"]), ("スキー", ["スキー"]), ("武道", ["弓道", "剣道"]),
        ("ダンス", ["ダンス"]), ("音楽", ["軽音", "吹奏楽", "JAZZ", "サウンド", "カラオーケストラ"]),
        ("写真", ["写真", "FOTO"]), ("演劇", ["演劇", "劇団", "演技映画", "ショートフィルム"]),
        ("漫画", ["漫画", "マンガ", "アニメ"]), ("ゲーム", ["ゲーム", "TRPG", "e-sports", "麻雀"]),
        ("建築", ["建築"]), ("プログラミング", ["プログラミング", "DeepLearning", "ハードソフト"]),
        ("茶道", ["茶道"]),
    ]
    for category, needles in rules:
        if any(needle in name for needle in needles):
            return category
    return "その他"


def organization_type(name):
    if any(word in name for word in ["本部", "委員会", "協議会", "学友会"]):
        return "学生団体"
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
    memo = "東京工芸大学公式サイトのクラブ・サークル紹介で確認。団体名、活動区分、出典URLのみ登録。"
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
    audit(conn, "official_tokyo_round4_import", "circle", circle_id, {
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
            slug("run", f"tokyo_official_round4_{timestamp}"),
            "Tokyo official zero-count universities round 4",
            "completed",
            inserted + updated,
            0,
            "東京工芸大学公式クラブ・サークル紹介から学友会所属団体名のみ登録。",
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
