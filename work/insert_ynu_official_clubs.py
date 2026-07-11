import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path


DB_PATH = Path(__file__).resolve().parents[1] / "outputs" / "circlematch.sqlite"
UNIVERSITY_NAME = "横浜国立大学"
LIST_SOURCE_URL = "https://www.gakuseisupport.ynu.ac.jp/asset/docs/20251204todokededantai_list.pdf"
SOURCE_MEMO = (
    "横浜国立大学公式サイトからリンクされた届出団体リストで確認。"
    "団体名、競技・活動区分、出典URLのみ登録し、紹介文・画像・個人情報は保存しない。"
)


OFFICIAL_CLUBS = [
    ("アイスホッケー部", "アイスホッケー", "部活"),
    ("アメリカンフットボール部", "アメリカンフットボール", "部活"),
    ("男子硬式庭球部", "テニス", "部活"),
    ("女子硬式庭球部", "テニス", "部活"),
    ("硬式野球部", "野球", "部活"),
    ("ゴルフ部", "ゴルフ", "部活"),
    ("サッカー部", "サッカー", "部活"),
    ("準硬式野球部", "野球", "部活"),
    ("ソサイチ部", "サッカー", "部活"),
    ("ソフトテニス部", "ソフトテニス", "部活"),
    ("卓球部", "卓球", "部活"),
    ("男子バスケットボール部", "バスケットボール", "部活"),
    ("女子バスケットボール部", "バスケットボール", "部活"),
    ("バドミントン部", "バドミントン", "部活"),
    ("男子バレーボール部", "バレーボール", "部活"),
    ("女子バレーボール部", "バレーボール", "部活"),
    ("ハンドボール部", "ハンドボール", "部活"),
    ("ラグビー部", "ラグビー", "部活"),
    ("男子ラクロス部", "ラクロス", "部活"),
    ("女子ラクロス部", "ラクロス", "部活"),
    ("合気道部", "合気道", "部活"),
    ("空手道部", "空手", "部活"),
    ("弓道部", "弓道", "部活"),
    ("剣道部", "剣道", "部活"),
    ("柔道部", "柔道", "部活"),
    ("少林寺拳法部", "少林寺拳法", "部活"),
    ("ボディビル部", "ボディビル", "部活"),
    ("ウインドサーフィン部", "ウインドサーフィン", "部活"),
    ("オリエンテーリング部", "オリエンテーリング", "部活"),
    ("水泳部", "水泳", "部活"),
    ("トライアスロン部", "トライアスロン", "部活"),
    ("陸上競技部", "陸上競技", "部活"),
    ("スキンスキューバダイビング部", "スキューバダイビング", "部活"),
    ("ヨット部", "セーリング", "部活"),
    ("体操競技部", "体操", "部活"),
    ("山岳部", "登山", "部活"),
    ("スキー部", "スキー", "部活"),
    ("ワンダーフォーゲル部", "アウトドア", "部活"),
    ("ハング・パラグライダー部", "パラグライダー", "部活"),
    ("アルティメット部", "フライングディスク", "部活"),
    ("横国キャップ野球チーム Sounds on Beach", "キャップ野球", "公認サークル"),
    ("YNUCC", "自転車", "公認サークル"),
    ("フィギュアスケート部", "フィギュアスケート", "部活"),
    ("アコースティックスタイル", "音楽", "公認サークル"),
    ("管弦楽団", "音楽", "公認サークル"),
    ("軽音楽部 YNU Keion", "音楽", "部活"),
    ("吹奏楽団", "音楽", "公認サークル"),
    ("電子音楽研究会", "音楽", "公認サークル"),
    ("Baysound Jazz Orchestra", "音楽", "公認サークル"),
    ("邦楽研究会", "音楽", "公認サークル"),
    ("民謡研究会合唱団", "音楽", "公認サークル"),
    ("モダンジャズ研究会", "音楽", "公認サークル"),
    ("ロック研究会", "音楽", "公認サークル"),
    ("ロバートジョンソン研究会", "音楽", "公認サークル"),
    ("グリークラブ", "合唱", "公認サークル"),
    ("混声合唱団 YNU Mixed Choir", "合唱", "公認サークル"),
    ("女声合唱団Dancing Dolphins", "合唱", "公認サークル"),
    ("Stairways", "アカペラ", "公認サークル"),
    ("囲碁部", "囲碁", "部活"),
    ("競技かるたサークル", "競技かるた", "公認サークル"),
    ("クイズ研究会", "クイズ", "公認サークル"),
    ("将棋サークル若葉会", "将棋", "公認サークル"),
    ("PCサークルSCITEX", "IT", "公認サークル"),
    ("ポーカーサークル Y-nuts", "ポーカー", "公認サークル"),
    ("麻雀部", "麻雀", "部活"),
    ("ルーガルー", "ボードゲーム", "公認サークル"),
    ("茶道研究会", "茶道", "公認サークル"),
    ("モダンダンス部", "ダンス", "部活"),
    ("ダンスサークルLIZ", "ダンス", "公認サークル"),
    ("KPOPダンスサークル popcorn", "ダンス", "公認サークル"),
    ("映画研究部", "映画", "部活"),
    ("お笑いサークルわかば", "演芸", "公認サークル"),
    ("劇団三日月座", "演劇", "公認サークル"),
    ("写真部", "写真", "部活"),
    ("美術部EyeBrows", "美術", "部活"),
    ("現代視覚文化研究会", "サブカルチャー", "公認サークル"),
    ("鉄道旅行研究会", "旅行", "公認サークル"),
    ("読書サークル「こたけ」", "読書", "公認サークル"),
    ("大道芸ジャグリングサークル", "ジャグリング", "公認サークル"),
    ("YDK（横国ディズニーサークル）", "交流", "公認サークル"),
    ("漫画イラスト研究部", "漫画・イラスト", "公認サークル"),
    ("横国うどん部", "料理", "部活"),
    ("新聞会", "新聞", "公認サークル"),
    ("放送研究会", "放送", "公認サークル"),
    ("大学祭実行委員会", "イベント運営", "学生団体"),
    ("留学生支援団体105", "国際交流", "学生団体"),
    ("YNU international students lounge", "国際交流", "学生団体"),
    ("ESS", "英語", "公認サークル"),
    ("韓国人学生会", "国際交流", "学生団体"),
    ("横濱会計會(YKK)", "会計", "公認サークル"),
    ("YNU Capital", "投資", "公認サークル"),
    ("Founders Lab", "起業", "公認サークル"),
    ("国際問題研究会", "国際問題", "公認サークル"),
    ("YBC・YAC実行委員会", "ビジネスコンテスト", "学生団体"),
    ("キュリオシーズ", "科学", "公認サークル"),
    ("CORE", "ロケット", "公認サークル"),
    ("横浜AEROSPACE", "人力飛行機", "公認サークル"),
    ("自動車部", "モータースポーツ", "部活"),
    ("フォーミュラプロジェクト", "モータースポーツ", "公認サークル"),
    ("自作EV公道走行プロジェクト", "EV", "公認サークル"),
    ("Robo+ism", "ロボット", "公認サークル"),
    ("競技プログラミング部", "プログラミング", "部活"),
    ("Lumos", "プログラミング", "公認サークル"),
    ("猫サークル", "ボランティア", "公認サークル"),
]


def now():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def slug(prefix, text):
    base = "".join(ch.lower() if ch.isalnum() else "_" for ch in text).strip("_")
    return f"{prefix}_{base[:96]}"


def audit(conn, action, entity_type, entity_id, payload, timestamp):
    conn.execute(
        "insert into audit_logs(action, entity_type, entity_id, payload, created_at) values(?,?,?,?,?)",
        (action, entity_type, entity_id, json.dumps(payload, ensure_ascii=False), timestamp),
    )


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    timestamp = now()
    university = conn.execute(
        "select university_id from universities where university_name=? order by campus_name limit 1",
        (UNIVERSITY_NAME,),
    ).fetchone()
    if not university:
        raise SystemExit(f"university not found: {UNIVERSITY_NAME}")

    inserted = 0
    updated = 0
    for circle_name, sport_category, organization_type in OFFICIAL_CLUBS:
        existing = conn.execute(
            "select circle_id from circles where university_id=? and circle_name=?",
            (university["university_id"], circle_name),
        ).fetchone()
        circle_id = existing["circle_id"] if existing else slug("c", f"{university['university_id']}_{circle_name}")
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
                university["university_id"],
                circle_name,
                organization_type,
                sport_category,
                "神奈川県横浜市",
                "university_official",
                LIST_SOURCE_URL,
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
                slug("src", f"{circle_id}_{LIST_SOURCE_URL}"),
                "circle",
                circle_id,
                "university_official",
                LIST_SOURCE_URL,
                SOURCE_MEMO,
                timestamp[:10],
                timestamp,
            ),
        )
        audit(conn, "official_university_club_import", "circle", circle_id, {
            "university": UNIVERSITY_NAME,
            "circle_name": circle_name,
            "sport_category": sport_category,
            "source_url": LIST_SOURCE_URL,
        }, timestamp)
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
            university["university_id"],
            "partial",
            2,
            "横浜国立大学 届出団体 サークル活動 公式",
            LIST_SOURCE_URL,
            "公式PDFの届出団体リストを収集。ページ上の説明文・画像は未使用。",
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
            slug("run", f"ynu_official_clubs_{timestamp}"),
            "Phase 1: 横浜国立大学 届出団体",
            "completed",
            inserted + updated,
            0,
            "横浜国立大学公式届出団体リストから団体名・競技区分・出典URLのみ登録。",
            timestamp,
            now(),
        ),
    )
    conn.commit()
    print(json.dumps({
        "university": UNIVERSITY_NAME,
        "inserted": inserted,
        "updated": updated,
        "source_url": LIST_SOURCE_URL,
        "total_circles": conn.execute("select count(*) from circles").fetchone()[0],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
