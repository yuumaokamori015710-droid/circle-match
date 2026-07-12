import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


DB_PATH = Path(__file__).resolve().parents[1] / "outputs" / "circlematch.sqlite"


SOURCES = {
    "多摩美術大学": "https://www.tamabi.ac.jp/campus-life/extracurricular-activities/club/",
    "武蔵野大学": "https://www.musashino-u.ac.jp/student-life/campus_life/club/index.html",
    "和光大学": "https://www.wako.ac.jp/campuslife/extracurriculars/club-introduction.html",
}


CLUBS = {
    "多摩美術大学": [
        "WESTERN", "ジャズ研究会", "ジャンベ民族楽器部", "音多摩",
        "東京五美術大学管弦楽団", "和太鼓研究会", "テクノ研究会", "演劇部",
        "フラメンコ部", "ダンス部", "テキスタイルパフォーマンス", "陶芸部",
        "版画部", "絵本創作研究会", "新聞部", "映像演出研究会", "漫画部",
        "写真部", "虫部", "デジタル研究部", "ポケモン大好きクラ部",
        "オカルト研究会", "ハンドメイド部", "特殊撮影技術研究部",
        "美大生アイドル実行委員会", "硬式テニス部", "バスケットボール部",
        "バドミントン部", "野球部", "フットサル部", "相生道部", "山岳部",
        "スキー部", "Road Attack Club",
    ],
    "武蔵野大学": [
        "学友会執行部", "大学祭実行委員会", "駅伝部", "ソフトテニス部",
        "武蔵野大学弓道部紫月会", "サイクリングクラブ", "卓球部", "硬式庭球部",
        "社交舞踏研究部", "男子バスケットボール部", "武蔵野大学バレーボール部（女子）",
        "武蔵野大学バレーボール部（男子）", "Dance Club Alpha", "武蔵野大学水泳部",
        "武蔵野大学バドミントン部", "武蔵野大学サッカー部", "武蔵野大学軟式野球部",
        "武蔵野大学合気道部", "漣～SAZANAMI～", "武蔵野大学KPOPカバーダンスサークルMiix",
        "武蔵野大学ソサイチサークル", "アカペラサークルMAM", "ハワイアンクラブ",
        "武蔵野大学管弦楽団", "エコの民", "Hand Language Club", "武蔵野大学漫画研究部",
        "書道部", "ピアノコンチェルト", "武蔵野大学マンドリンクラブ", "こどもボランティア部",
        "美術部", "文学研究部", "写真技術研究部", "武蔵野大学ウインドアンサンブル",
        "武蔵野大学邦楽部琴之音会", "お茶同好会", "演劇研究部 def's drop",
        "和太鼓 隼", "武蔵野大学紅茶研究部", "武蔵野大学音楽部ルンビニー合唱団",
        "国際交流の会", "サブカル研究部", "武蔵野大学放送研究部", "BohPJ 同好会",
        "武蔵野大学裏千家茶道部", "映像研究同好会スタジオマーリン",
        "武蔵野大学ボードゲーム同好会 いるでぃ", "武蔵野大学武蔵野生の遊び場",
        "放課後秘密基地 たまごまなぼ", "学生団体CREATORS", "武蔵野大学おさがりモンスター",
        "ネイル同好会《nailer》", "情報部", "清談会", "料理同好会", "武蔵野大学お笑いサークルMOS",
    ],
    "和光大学": ["全学サークル連合"],
}


def now():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def slug(prefix, text):
    base = "".join(ch.lower() if ch.isalnum() else "_" for ch in text).strip("_")
    return f"{prefix}_{base[:96]}"


def sport_category(name):
    rules = [
        ("野球", ["野球"]), ("サッカー", ["サッカー", "フットサル", "ソサイチ"]),
        ("テニス", ["テニス", "庭球"]), ("バスケットボール", ["バスケット"]),
        ("バレーボール", ["バレーボール"]), ("バドミントン", ["バドミントン"]),
        ("陸上競技", ["駅伝"]), ("卓球", ["卓球"]), ("水泳", ["水泳"]),
        ("スキー", ["スキー"]), ("自転車", ["サイクリング", "Road Attack"]),
        ("アウトドア", ["山岳"]), ("武道", ["弓道", "合気道", "相生道"]),
        ("ダンス", ["ダンス", "フラメンコ", "社交舞踏", "KPOP"]),
        ("音楽", ["音多摩", "ジャズ", "ジャンベ", "管弦楽", "和太鼓", "アカペラ", "ピアノ", "マンドリン", "ウインドアンサンブル", "邦楽", "音楽", "テクノ"]),
        ("写真", ["写真"]), ("演劇", ["演劇"]), ("漫画", ["漫画", "ポケモン", "サブカル"]),
        ("映画", ["映像"]), ("美術", ["陶芸", "版画", "絵本", "ハンドメイド", "美術", "書道"]),
        ("ゲーム", ["ボードゲーム"]), ("ボランティア", ["ボランティア", "エコ"]),
        ("茶道", ["お茶", "茶道", "紅茶"]), ("料理", ["料理"]), ("放送", ["放送"]),
    ]
    for category, needles in rules:
        if any(needle in name for needle in needles):
            return category
    return "その他"


def organization_type(name):
    if any(word in name for word in ["委員会", "執行部", "学生団体", "連合"]):
        return "学生団体"
    if "部" in name:
        return "部活"
    return "公認サークル"


def audit(conn, action, entity_type, entity_id, payload, timestamp):
    conn.execute(
        "insert into audit_logs(action, entity_type, entity_id, payload, created_at) values(?,?,?,?,?)",
        (action, entity_type, entity_id, json.dumps(payload, ensure_ascii=False), timestamp),
    )


def upsert(conn, university_name, circle_name, timestamp):
    source_url = SOURCES[university_name]
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
    memo = f"{university_name}公式サイトの課外活動・クラブ団体一覧で確認。団体名、活動区分、出典URLのみ登録。"
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
            sport_category(circle_name), "東京都", "university_official", source_url,
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
        (slug("src", f"{circle_id}_{source_url}"), "circle", circle_id, "university_official", source_url, memo, timestamp[:10], timestamp),
    )
    audit(conn, "official_tokyo_round7_import", "circle", circle_id, {
        "university": university_name,
        "circle_name": circle_name,
        "source_url": source_url,
    }, timestamp)
    return 0 if existing else 1


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    timestamp = now()
    inserted = 0
    updated = 0
    per_university = {}
    for university_name, names in CLUBS.items():
        before_inserted = inserted
        for name in names:
            is_insert = upsert(conn, university_name, name, timestamp)
            inserted += is_insert
            updated += 1 - is_insert
        per_university[university_name] = {
            "source_url": SOURCES[university_name],
            "processed": len(names),
            "inserted": inserted - before_inserted,
        }
    conn.execute(
        """
        insert into collection_runs(run_id, target_scope, status, collected_count, candidate_count, memo, started_at, finished_at)
        values(?,?,?,?,?,?,?,?)
        """,
        (
            slug("run", f"tokyo_official_round7_{timestamp}"),
            "Tokyo official zero-count universities round 7",
            "completed",
            inserted + updated,
            0,
            "多摩美術大学、武蔵野大学、和光大学の公式課外活動ページから団体名のみ登録。和光大学は公認サークルなしのため全学サークル連合を学生団体として登録。",
            timestamp,
            now(),
        ),
    )
    conn.commit()
    print(json.dumps({
        "inserted": inserted,
        "updated": updated,
        "per_university": per_university,
        "total_circles": conn.execute("select count(*) from circles").fetchone()[0],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
