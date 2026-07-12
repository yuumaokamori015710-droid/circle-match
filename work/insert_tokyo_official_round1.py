import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


DB_PATH = Path(__file__).resolve().parents[1] / "outputs" / "circlematch.sqlite"


SOURCES = {
    "亜細亜大学": "https://www.asia-u.ac.jp/campuslife/club/",
    "日本社会事業大学": "https://www.jcsw.ac.jp/campuslife/kagai/",
    "デジタルハリウッド大学": "https://www.dhw.ac.jp/life/club/",
    "共立女子大学": "https://www.kyoritsu-wu.ac.jp/campus/circle/",
    "東京富士大学": "https://www.fuji.ac.jp/life/circle/",
}


CLUBS = {
    "亜細亜大学": [
        "中央執行委員会", "アジア祭実行委員会", "学生健康保険委員会", "新聞委員会",
        "体育祭実行委員会", "新入生研修委員会", "学術文化連合会執行委員会", "届出団体本部",
        "財務局", "福利厚生局協助会", "音響技術委員会", "県人会連合会", "体育会本部",
        "卒業アルバム委員会", "硬式野球部", "陸上競技部", "女子陸上競技部", "硬式庭球部",
        "アジア女子ローンテニス部", "サッカー部", "バレーボール部", "剣道部", "柔道部",
        "吹奏楽団", "応援指導部", "アメリカンフットボール部", "居合道部", "空手道部",
        "弓道部", "ゴルフ部", "自動車部", "社会体育研究会", "準硬式野球部",
        "女子バレーボール部", "水泳部", "セパタクロー部", "軟式野球部", "日本拳法部",
        "バスケットボール部", "バドミントン部", "ボクシング部", "洋弓部", "ワンダーフォーゲル部",
        "スペイン語・文化研究会（休会）", "経済学会", "ハワイアン研究会", "世界民謡研究会",
        "写真部", "演劇研究会劇団『つた』", "放送研究会", "探検部", "ユースホステルクラブ",
        "一般奉仕会「細流（せせらぎ）」", "フランス語研究会", "法律学特別研究会", "漫画研究会",
        "A.U.NET", "ガムラン研究会", "亜細亜大学ボランティアセンター（AUVC）",
        "ラテンアメリカ研究会", "将棋研究会（休会）", "FAITH", "文連祭実行委員会",
        "インド研究会", "古典研究会", "コスプレ研究会「Cielo」",
    ],
    "日本社会事業大学": [
        "なかよしぐる～ぷ", "ボランティアサークル Hi-Ho！", "さんさんさん", "社大BBS会",
        "プレイケアサークル おもちゃばこ", "被災地支援団体Cocoa", "ステップタイム",
        "新聞サークル\"さざんか\"", "混声合唱団 菩提樹（ぼだいじゅ）", "ブラスバンドサークル",
        "マンドリンアンサンブル", "軽音楽サークル", "華道部ちろる", "手話サークルいちご",
        "オレンジクレヨン", "バスケットボールサークル\"GO-Getters\"", "ダンスサークル\"Nexus\"",
        "バレーボールサークル", "バドミントンサークル", "準硬式野球部", "フットサルサークル ぷちとまと",
        "硬式テニスサークル", "卓球サークル", "ワンダーフォーゲルサークル", "文武両道同好会",
        "多世代交流同好会", "読書マラソン委員会", "日本社会事業大学ヤギ部", "手話おしゃべり会",
        "お料理部", "カードゲーム同好会", "懐かしゲーム同好会", "宵の鷹兎", "軟硬テニス同好会",
    ],
    "デジタルハリウッド大学": [
        "キャンパスPRプロジェクト【学内インターンシップ】", "MVide", "DGGAサークル (DHU GOOD GAME AWARDS) MVide",
        "90PROJECT", "TtT", "プリティーサークル", "コメハリ", "DHUアイドル研究会", "Buff",
        "vente us", "DHU International Club（English Club）", "NaN", "HCUP", "てらこや",
        "MELIES", "駄弁を貪る", "MULTICUT", "ZERO", "アメコミ・ハリウッド",
        "DHUホビー司令部 Hobby ON", "Physical Hollywood", "でさいん〈ゆ〉", "DHU 写真部",
        "REP", "INME", "DHU Audio Club", "ポケモンサークル",
        "デジタルハリウッド特撮文化研究隊（DTCG） 通称：デ特隊", "ふてさぁ。",
    ],
    "共立女子大学": [
        "共立祭運営委員会", "サークル連合会", "アートワークスラボLimetta", "アイドル研究会",
        "英語研究会", "演劇研究部", "共立Bouquet", "雑学研究会", "社会福祉サークル",
        "写真部", "手話サークル薫会", "食で世界を笑顔にする会くすくす", "美術部",
        "ファッション研究会", "文芸制作サークル", "文士会", "放送研究部", "まんが研究会",
        "ミュージカル研究部", "ユースホステルサークル", "TRPG研究会 さくらこねこ",
        "華道部池坊", "華道部小原流", "きもの着付け倶楽部", "狂言研究会", "香道部",
        "茶道部表千家不白流", "日本舞踊研究会", "フラ部", "フラワーデザイン研究会",
        "合唱団", "サウンドクリエイティブ", "室内楽団", "吹奏楽団", "筝曲部", "二胡サークル",
        "フォークソングクラブ", "マンドリンクラブ", "カヌー部", "競技ダンス部", "剣道部",
        "ダンスサークル FLAVA", "チアリーダー部", "テコンドー部", "バスケットボール部",
        "バドミントン部", "バレーボール部", "フィギュアスケートクラブ", "ボート部",
        "ラクロス部", "茶道部 裏千家", "よさこいサークル心恋連",
    ],
    "東京富士大学": [
        "女子ソフトボール部", "バスケットボール部", "バドミントン部", "ダーツ部", "ダンス部",
        "少林寺拳法同好会", "卓球同好会", "ボウリング同好会", "ストリートダンス同好会",
        "バレーボール同好会", "サッカー・フットサル同好会", "軽音楽部", "企業ビジネス研究同好会",
        "クオリア部", "演劇部", "馬頭琴同好会", "麻雀同好会",
    ],
}


def now():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def slug(prefix, text):
    base = "".join(ch.lower() if ch.isalnum() else "_" for ch in text).strip("_")
    return f"{prefix}_{base[:96]}"


def sport_category(name):
    rules = [
        ("野球", ["野球"]), ("サッカー", ["サッカー", "フットサル"]), ("テニス", ["テニス", "庭球"]),
        ("バスケットボール", ["バスケット"]), ("バレーボール", ["バレーボール"]), ("バドミントン", ["バドミントン"]),
        ("ラグビー", ["ラグビー"]), ("アメリカンフットボール", ["アメリカンフットボール"]),
        ("陸上競技", ["陸上"]), ("水泳", ["水泳"]), ("卓球", ["卓球"]), ("ダンス", ["ダンス", "フラ"]),
        ("武道", ["剣道", "柔道", "空手", "弓道", "拳法", "居合", "テコンドー"]),
        ("音楽", ["吹奏楽", "軽音", "合唱", "バンド", "マンドリン", "二胡", "筝曲", "音楽", "ガムラン"]),
        ("写真", ["写真"]), ("演劇", ["演劇", "劇団", "ミュージカル"]), ("放送", ["放送"]),
        ("ボランティア", ["ボランティア", "奉仕", "福祉"]), ("茶道", ["茶道"]), ("華道", ["華道"]),
        ("法律", ["法律"]), ("漫画", ["漫画", "まんが"]), ("ゲーム", ["ゲーム", "ポケモン"]),
    ]
    for category, needles in rules:
        if any(needle in name for needle in needles):
            return category
    return "その他"


def organization_type(name):
    if any(word in name for word in ["委員会", "本部", "局", "連合会"]):
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
    audit(conn, "official_tokyo_round1_import", "circle", circle_id, {
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
            slug("run", f"tokyo_official_round1_{timestamp}"),
            "Tokyo official low-coverage universities round 1",
            "completed",
            inserted + updated,
            0,
            "亜細亜大学、日本社会事業大学、デジタルハリウッド大学、共立女子大学、東京富士大学の公式サークル一覧から団体名のみ登録。",
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
