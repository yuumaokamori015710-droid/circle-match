import json
import re
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


DB_PATH = Path(__file__).resolve().parents[1] / "outputs" / "circlematch.sqlite"


SOURCES = {
    "ルーテル学院大学": "https://www.luther.ac.jp/campuslife/circle.html",
    "昭和女子大学": "https://www.swu.ac.jp/campuslife-project/campuslife/activity/circle.html",
    "東京医療保健大学": "http://www.thcu.ac.jp/nyushi/campuslife/club.html",
    "津田塾大学": "https://www.tsuda.ac.jp/student-life/circle.html",
    "清泉女子大学": "https://www.seisen-u.ac.jp/campuslife/activity/club.html",
}


CLUBS = {
    "ルーテル学院大学": [
        "聖歌隊", "ハンドベル ラウス・アンジェリカ", "楽友会（吹奏楽）", "軽音サークル",
        "手話サークル", "金曜ボランティアサークル", "大沢白球's（野球）",
        "GO TOOTH.FC（フットサル）", "ゴールドブリーズ（テニス）", "愛祭実行委員会",
        "学生広報委員会（LAC）", "学生会執行部", "キャンパスキリスト教センター（CCC）",
    ],
    "昭和女子大学": [
        "Encore", "生田流箏曲部", "池坊華道部", "イラストレーション部", "裏千家茶道部",
        "L.E.C.", "演劇部", "競技かるた部", "軽音楽部", "写真部", "書道部",
        "吹奏楽部", "文芸部", "放送研究会", "マンドリン・ギタークラブ",
        "礼法・和装部葵", "ENVO", "愛茗流煎茶道サークル", "映音学サークル",
        "SWUフェアトレードサークル", "エンパワーメントせたがや",
        "高齢者分野ボランティアサークル「彩り」", "国際貢献サークル", "子ども研究会",
        "手話サークル 手話の輪", "Showa Gleam International", "Sing Song Society",
        "ミステリー研究会", "合気道部", "クリケットクラブ", "剣道部", "硬式テニス部",
        "スイミングクラブ", "ダンス部ＡＵＢＥ", "バスケットボール部", "バドミントン部",
        "バレーボール部", "フィギュアスケート部", "フロアホッケークラブ", "陸上競技部",
        "ワンダーフォーゲル部", "スポーツチャンバラサークル", "卓球サークル",
    ],
    "東京医療保健大学": [
        "女子バスケットボール部", "チアダンス部 Jasmine", "救急救命サークル ACT",
        "ひぃりんぐぽっと", "2SK会/青少年の性と健康を考え活動する会", "羽人",
        "DaCapo", "ボランティアサークル", "Unite", "Blazing Stones", "フラッシュバック",
        "Heart Rhythm Club", "Puppies THCU International club", "アソビバ",
    ],
    "津田塾大学": [
        "バドミントンサークルpumpkin", "一橋Do!tennisteam", "一橋大学・津田塾大学少林寺拳法部",
        "津田塾大学合気道部", "津田塾大学剣道部", "津田塾大学フィールドホッケー部",
        "フラサークルPapalina", "Dance Nuts", "津田塾大学K-POPカバーダンススクール maesil jaem",
        "津田塾大学ソフトテニス部", "津田塾大学体育会ゴルフ部", "津田塾大学卓球部",
        "津田塾大学弓道部", "一橋大学バレーボール同好会", "津田塾大学オリエンテーリングクラブ",
        "一橋硬式庭球同好会", "一橋大学サッカー同好会", "山友会",
        "一橋大学・津田塾大学 体操部", "一橋・津田塾大学 ラフティング部 ストローム会",
        "津田塾大学空手道部", "グラシェールスキーチーム", "一橋大学・津田塾大学写真部",
        "津田塾大学生協学生委員会", "津田軽音楽部", "津田塾大学箏曲部",
        "津田塾大学表千家茶道部", "津田塾大学放送研究会", "津田ラテンアメリカ研究会",
        "津田塾プロジェクションマッピング", "一橋・津田塾・農工大ギター部",
        "津田塾大学草月流華道部", "英語にチャレンジ", "一橋大学津田塾大学吹奏楽団",
        "一橋大学アカペラサークルTheFirstCry", "津田塾大学かるた会", "津田塾祭実行委員会",
        "劇団WICK", "劇団コギト", "学生団体レアスマイル", "一橋大学津田塾大学合唱団ユマニテ",
        "一橋・津田塾ディズニー同好会マウス", "一橋大学管弦楽団", "一橋フォークソングクラブ",
        "フェアトレード推進団体チカス・ウニダス", "国際協力サークルKibo", "GreenTsuda",
        "STUDYFORTWO津田塾大学支部", "TsudaChristianFellowship", "一橋大学モダンジャズ研究会",
        "津田塾大学英語会（TESS）", "大学公式Webマガジンplumgarden編集部", "早大ファンタスティック T.C.",
        "Tsuda Outreach", "千駄ヶ谷書道会", "Uméson-Habitat", "うめりある",
        "津田ヶ谷祭実行委員会", "津田塾大学×住田高校 地域連携プロジェクト", "梅五輪プロジェクト",
        "STEM Leaders",
    ],
    "清泉女子大学": [
        "管弦楽部", "コールクライネス", "茶道部", "ザ☆バンド", "写真部",
        "手話サークル H.A.C.S.", "吹奏楽部", "清泉YMCA", "美術部",
        "フォルクローレ・サークル", "フラメンコクラブ “Las Majas”", "放送研究会",
        "漫画研究会", "合気道部", "硬式庭球部", "スキー部", "ダンス部",
        "チアリーディング部 S.S.S.", "バドミントン部", "K-POPダンスサークル ソンムル",
        "読書会鼠倶楽部", "日本文化愛好会", "福がーる",
    ],
}


def now():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def slug(prefix, text):
    base = "".join(ch.lower() if ch.isalnum() else "_" for ch in text).strip("_")
    return f"{prefix}_{base[:96]}"


def sport_category(name):
    rules = [
        ("野球", ["野球", "白球"]), ("サッカー", ["サッカー", "フットサル"]), ("テニス", ["テニス", "庭球"]),
        ("バスケットボール", ["バスケット", "バスケ"]), ("バレーボール", ["バレーボール"]), ("バドミントン", ["バドミントン"]),
        ("陸上競技", ["陸上"]), ("水泳", ["水泳", "スイミング"]), ("卓球", ["卓球"]), ("ダンス", ["ダンス", "フラ", "チア"]),
        ("武道", ["剣道", "柔道", "空手", "弓道", "拳法", "合気道", "チャンバラ"]),
        ("音楽", ["吹奏楽", "軽音", "合唱", "バンド", "マンドリン", "管弦楽", "箏曲", "音楽", "アカペラ", "コール", "ギター"]),
        ("写真", ["写真"]), ("演劇", ["演劇", "劇団"]), ("放送", ["放送"]),
        ("ボランティア", ["ボランティア", "奉仕", "YMCA", "国際協力", "地域連携", "フェアトレード"]),
        ("茶道", ["茶道", "煎茶"]), ("華道", ["華道"]), ("漫画", ["漫画"]), ("ゲーム", ["ゲーム"]),
    ]
    for category, needles in rules:
        if any(needle in name for needle in needles):
            return category
    return "その他"


def organization_type(name):
    if any(word in name for word in ["委員会", "学生会", "学生団体", "編集部", "プロジェクト"]):
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
    audit(conn, "official_tokyo_round2_import", "circle", circle_id, {
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
            slug("run", f"tokyo_official_round2_{timestamp}"),
            "Tokyo official zero-count universities round 2",
            "completed",
            inserted + updated,
            0,
            "ルーテル学院大学、昭和女子大学、東京医療保健大学、津田塾大学、清泉女子大学の公式サークル一覧から団体名のみ登録。和光大学は公式公開一覧なしのため未登録。",
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
