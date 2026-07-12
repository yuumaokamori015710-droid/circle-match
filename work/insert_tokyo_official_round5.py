import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


DB_PATH = Path(__file__).resolve().parents[1] / "outputs" / "circlematch.sqlite"


SOURCES = {
    "日本文化大学": "https://www.nihonbunka-u.ac.jp/campus-life/activities/",
    "明星大学": "https://www.meisei-u.ac.jp/support/student/club/",
    "武蔵野美術大学": "https://www.musabi.ac.jp/student_life/activity/club/",
    "立正大学": "https://www.ris.ac.jp/campus_life/extracurricular_activities/index.html",
    "桜美林大学": "https://www.obirin.ac.jp/sports/",
}


CLUBS = {
    "日本文化大学": [
        "剣道部", "柔道部", "弓道部", "サッカー部", "バスケットボール部",
        "バトミントン", "バレーボール", "野球", "ボランティア", "軽音楽",
        "写真", "トレーニング", "ダンス", "合気道", "法律研究",
    ],
    "明星大学": [
        "執行委員会", "体育会本部", "文化会本部", "星友祭実行委員会", "吹奏楽団",
        "アメリカンフットボール部", "空手道部", "弓道部（和弓班）", "剣道部",
        "ゴルフ部", "蹴球部", "自転車競技部", "自動車部", "柔道部",
        "器械体操部", "卓球部", "ダンス部「DASH!」", "硬式庭球部", "軟式庭球部",
        "男子籠球部", "女子籠球部", "バドミントン部", "男子排球部", "女子排球部",
        "男子送球部", "女子送球部", "硬式野球部", "軟式野球部", "男子ラクロス部",
        "女子ラクロス部", "陸上競技部", "アイススケート部", "アルティメットフリスビー”SPARKS\"",
        "チアリーディング同好会Miracle☆Stars", "インパクトテニス同好会", "MAJESTIC",
        "ダブルダッチ同好会「Shakin Key!!」", "囲碁部", "映画研究部",
        "演劇部「劇団時間ドロボウ」", "ギター・マンドリン部", "軽音楽部", "混声合唱部",
        "フォークソング部", "教育研究部", "へき地教育研究部", "茶道部", "写真部",
        "鉄道研究部", "電気部", "天文部", "美術部", "文学研究部", "漫画研究部",
        "アカペラ同好会カラフル", "明星フィルハーモニー管弦楽団", "いけばなさつき会",
        "パフォーマンスサークルTRY CUBE", "明星大学防災ボランティア隊「MCAT」",
        "天文同好会「すばる」", "和太鼓集団鼓蝶", "アウトドア愛好会", "Freedom Music",
        "Fretless", "初等教育研究会どろんこの会", "テーブルゲーム研究会",
        "トレーディングカードゲームサークル", "メイセイシティポケモンジム～MPG～",
        "明星大学就活応援サークルEADS", "国際交流会", "日本拳法愛好会", "VALIENTE",
        "おもいやりサークルSMILY", "SEASON", "Gaily washlets", "ハートフルサークル「Merci」",
        "明星大学学生赤十字奉仕団", "中国文化愛好会", "マシン工作サークル", "New colors",
        "けもの道探検隊", "フィットネスサークル", "明星バレーボールサークルＭＶＣ",
        "明星大学スキー愛好会", "明星大学FCマーズ", "明星かるた会", "CHAL BALL",
        "クイズ研究会Qulet", "明星大学eスポーツサークル翡翠會", "ピアノ同好会",
        "麻雀研究会", "ハイキングサークルCANVAS", "留星会",
    ],
    "武蔵野美術大学": [
        "イラスト研究会", "映画研究会MUSA☆CINE", "epa!", "MKP", "ガラス研究会",
        "競技かるた", "劇団むさび", "写真部", "造形教育研究会・アトリエちびくろ",
        "東京五美術大学管弦楽団", "人形劇団ダニ族", "ねこ部", "ポケモン部",
        "MAUコーラス", "漫画研究会", "MODERN JAZZ SOCIETY", "モンスタレーションクラブ",
        "窯工研究会", "ロック研究会", "シルクスクリーン倶楽部", "ムサビゲームラボ",
        "書道サークル知風", "Object（デッサンサークル）", "武蔵野美術大学模型同好会",
        "弓道部", "競技ダンス部", "剣道部", "硬式テニス部", "サイクリング部",
        "サッカー部", "卓球部", "バスケットボール部", "バドミントン部", "バレーボール部",
        "パンチスタ", "ワンダーフォーゲル部", "野球サークル",
    ],
    "立正大学": ["硬式野球部", "ラグビー部", "サッカー部", "陸上競技部駅伝部門"],
    "桜美林大学": [
        "弓道部", "野球部", "駅伝部", "アメリカンフットボール部", "ソングリーディング部",
        "チアリーディング部", "男子バレーボール部", "女子バレーボール部", "サッカー部",
    ],
}


def now():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def slug(prefix, text):
    base = "".join(ch.lower() if ch.isalnum() else "_" for ch in text).strip("_")
    return f"{prefix}_{base[:96]}"


def sport_category(name):
    rules = [
        ("野球", ["野球"]), ("サッカー", ["サッカー", "蹴球", "FC"]), ("テニス", ["テニス", "庭球"]),
        ("バスケットボール", ["バスケット", "籠球"]), ("バレーボール", ["バレーボール", "排球"]),
        ("バドミントン", ["バドミントン", "バトミントン"]), ("ラグビー", ["ラグビー"]),
        ("アメリカンフットボール", ["アメリカンフットボール"]), ("ラクロス", ["ラクロス"]),
        ("ハンドボール", ["送球"]), ("陸上競技", ["陸上", "駅伝"]), ("卓球", ["卓球"]),
        ("スキー", ["スキー", "アイススケート"]), ("武道", ["剣道", "柔道", "弓道", "空手", "合気道", "拳法"]),
        ("ダンス", ["ダンス", "チア", "ソングリーディング", "ダブルダッチ"]),
        ("音楽", ["吹奏楽", "軽音", "合唱", "フォークソング", "マンドリン", "管弦楽", "アカペラ", "ピアノ", "和太鼓", "コーラス", "JAZZ", "ロック"]),
        ("写真", ["写真"]), ("演劇", ["演劇", "劇団", "映画"]), ("漫画", ["漫画", "マンガ", "イラスト"]),
        ("ゲーム", ["ゲーム", "ポケモン", "麻雀", "eスポーツ", "囲碁", "TRPG", "クイズ"]),
        ("ボランティア", ["ボランティア", "赤十字", "防災", "奉仕", "おもいやり"]),
        ("茶道", ["茶道"]), ("華道", ["いけばな"]), ("法律", ["法律"]), ("建築", ["建築"]),
    ]
    for category, needles in rules:
        if any(needle in name for needle in needles):
            return category
    return "その他"


def organization_type(name):
    if any(word in name for word in ["委員会", "本部", "国際交流会", "執行委員会"]):
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
    memo = f"{university_name}公式サイトの課外活動・サークル一覧で確認。団体名、活動区分、出典URLのみ登録。"
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
    audit(conn, "official_tokyo_round5_import", "circle", circle_id, {
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
            slug("run", f"tokyo_official_round5_{timestamp}"),
            "Tokyo official low-count universities round 5",
            "completed",
            inserted + updated,
            0,
            "日本文化大学、明星大学、武蔵野美術大学、立正大学、桜美林大学の公式課外活動ページから団体名のみ登録。",
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
