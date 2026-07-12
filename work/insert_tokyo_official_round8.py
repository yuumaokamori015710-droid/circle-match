from __future__ import annotations

import sqlite3
from datetime import datetime, timezone


DB = "outputs/circlematch.sqlite"
TODAY = datetime.now(timezone.utc).date().isoformat()


SPORT_KEYWORDS = [
    ("野球", "野球"),
    ("準硬式野球", "野球"),
    ("軟式野球", "野球"),
    ("サッカー", "サッカー"),
    ("フットサル", "フットサル"),
    ("バスケット", "バスケットボール"),
    ("バレー", "バレーボール"),
    ("テニス", "テニス"),
    ("庭球", "テニス"),
    ("バドミントン", "バドミントン"),
    ("バトミントン", "バドミントン"),
    ("アメリカンフットボール", "アメリカンフットボール"),
    ("ラグビー", "ラグビー"),
    ("剣道", "剣道"),
    ("少林寺拳法", "少林寺拳法"),
    ("弓道", "弓道"),
    ("陸上", "陸上競技"),
    ("水泳", "水泳"),
    ("ゴルフ", "ゴルフ"),
    ("スキー", "スキー"),
    ("山岳", "山岳"),
    ("ボッチャ", "ボッチャ"),
    ("ダンス", "ダンス"),
    ("アイスホッケー", "アイスホッケー"),
    ("ライフセービング", "ライフセービング"),
    ("ハンドボール", "ハンドボール"),
    ("卓球", "卓球"),
    ("柔道", "柔道"),
    ("端艇", "ボート"),
    ("アーチェリー", "アーチェリー"),
]


def sport_for(name: str) -> str:
    for keyword, sport in SPORT_KEYWORDS:
        if keyword in name:
            return sport
    return "その他"


def org_type_for(name: str) -> str:
    if "部" in name and not any(token in name for token in ["同好会", "サークル", "クラブ"]):
        return "部活"
    if "同好会" in name:
        return "同好会"
    if "サークル" in name or "クラブ" in name:
        return "公認サークル"
    return "公認サークル"


def circle_id(university: str, name: str) -> str:
    safe = "".join(ch if ch.isalnum() else "_" for ch in name).strip("_")
    return f"c_u_{university}_{safe}"


def upsert(cur: sqlite3.Cursor, university: str, name: str, source_url: str) -> bool:
    university_id = cur.execute(
        "select university_id from universities where university_name = ?",
        (university,),
    ).fetchone()[0]
    row = (
        circle_id(university, name),
        university_id,
        name,
        sport_for(name),
        None,
        "university_official",
        source_url,
        "university_verified",
        "published",
        TODAY,
        None,
        "official Tokyo zero-count reduction",
        TODAY,
        TODAY,
        org_type_for(name),
    )
    before = cur.execute(
        "select circle_id from circles where university_id = ? and circle_name = ?",
        (university_id, name),
    ).fetchone()
    cur.execute(
        """
        insert into circles (
          circle_id, university_id, circle_name, sport_category, activity_area,
          source_type, source_url, verification_status, public_status,
          last_checked_at, sns_url, owner_notes, created_at, updated_at,
          organization_type
        )
        values (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        on conflict(university_id, circle_name) do update set
          sport_category = excluded.sport_category,
          source_type = excluded.source_type,
          source_url = excluded.source_url,
          verification_status = excluded.verification_status,
          public_status = excluded.public_status,
          last_checked_at = excluded.last_checked_at,
          updated_at = excluded.updated_at,
          organization_type = excluded.organization_type
        """,
        row,
    )
    return before is None


KYORIN = [
    "ライフセービング部",
    "軟式野球部",
    "ハンドボール部",
    "バスケットボール部",
    "アイスホッケー部",
    "華道部",
    "Street Trickers（マジッククラブ）",
    "杏林大学井の頭管弦楽団",
    "Slave To The Rhythm（ダンス部）",
    "硬式野球部",
    "男子バスケットボール部",
    "女子バスケットボール部",
    "アメリカンフットボール部",
    "ソフトテニス部",
    "ラグビーフットボール部",
    "剣道部",
    "少林寺拳法部",
    "杏林大学サッカー部",
    "ＫＨＢＣ(バスケットボール)",
    "アプリコットＢＣ(バドミントン)",
    "硬式テニス部",
    "弓道部",
    "陸上競技部",
    "杏林大学フットサル部",
    "ボッチャ部",
    "かながな〜とぅ(軟式野球)",
    "ボランティア団体feel",
    "マンガ研究部",
    "杏林大学吹奏楽団",
    "軽音楽部",
    "救急救命クラブ（KELC）",
    "杏林大学ボランティア部",
    "写真部",
    "asobi基地・関東学生部@杏林大学",
    "ボードゲームサークル",
    "杏林書道会",
    "バレーボール部",
    "柔道部",
    "軟式庭球部",
    "サッカー部",
    "準硬式野球部",
    "アーチェリー部",
    "端艇部",
    "管弦楽団",
    "メディカルイラストレーション部",
    "バドミントン部",
    "卓球部",
    "硬式庭球部",
    "フットサル部",
    "水泳部",
    "ゴルフ部",
    "スキー部",
    "ダンス部",
    "ESS",
    "ぬいぐるみ病院部",
    "統合医療研究部",
]


TEU = [
    "アメリカンフットボール部",
    "バトミントン部",
    "剣道部",
    "赤平",
    "クロイツェル室内管弦楽団",
    "化学サークル",
    "ロボット研究部",
    "写真部",
    "茶道同好会",
    "工業・空間デザイン研究同好会",
    "天文同好会",
    "漫画研究同好会",
    "ワークショップデザイン同好会",
    "軽音楽部",
    "Creation",
    "M.R.E（インターネットラジオ）",
    "クリエイティブスタッフ",
    "化粧品サークルLCC",
]


TOKYO_KASEI = [
    "茶道部",
    "演劇部",
    "マンドリンクラブ",
    "フラウエンコール",
    "華道部草月流",
    "箏曲部",
    "軽音楽部",
    "吹奏楽部",
    "文芸部",
    "児童音楽研究会",
    "漫画研究会",
    "ユースホステルクラブ",
    "自然研究会",
    "学生赤十字奉仕団",
    "写真部",
    "池袋子ども会",
    "グラフィックデザインサークル",
    "料理研究会",
    "ジャズ研究会",
    "バスケットボール部",
    "バレーボール部",
    "ソフトテニス部",
    "ダンス部",
    "剣道部",
    "ラクロス部",
    "チアリーディング部",
    "ストリートダンスサークル",
    "ワンダーフォーゲル部",
    "シュナイツスキークラブ",
    "フラサークルPuaLani",
    "競技ダンス",
    "スカッシュラケット部",
    "卓球部",
    "弓道部",
    "チアダンスチームQuartz",
    "スポーツ栄養研究会",
    "Space designサークル",
    "手芸同好会",
    "水泳同好会",
    "書道同好会",
    "パンサー",
    "ボラガール",
    "アニメ・声優研究会",
    "ヨガサークル～Mind Body～",
    "陸上競技部",
    "crocus（クロッカス）",
    "競技かるた同好会",
    "ボードゲーム",
    "バドミントン同好会",
    "日本茶サークル",
    "G&E",
    "音楽サークル",
    "看護ボランティアサークル",
    "保育ボランティアサークル ぴっちーな",
    "造形コミュニケーション同好会",
    "ユニバーサルコミュニケーション同好会",
    "球技同好会 Star Lights",
    "SDgirls",
    "TEAra～紅茶部～",
    "韓国文化研究同好会",
    "エンターテイメントサークル",
    "国際交流同好会",
    "狭山ボードゲーム同好会",
    "Child Care Circle (C.C.C）",
]


def main() -> None:
    con = sqlite3.connect(DB)
    cur = con.cursor()
    inserted = 0
    for name in KYORIN:
        inserted += upsert(
            cur,
            "杏林大学",
            name,
            "http://www.kyorin-u.ac.jp/univ/student/campuslife/circle/index.html",
        )
    for name in TEU:
        inserted += upsert(
            cur,
            "東京工科大学",
            name,
            "https://www.teu.ac.jp/student/circle/index.html",
        )
    for name in TOKYO_KASEI:
        inserted += upsert(
            cur,
            "東京家政大学",
            name,
            "https://www.tokyo-kasei.ac.jp/campus_support/campus_life/club.html",
        )
    con.commit()
    total = cur.execute("select count(*) from circles").fetchone()[0]
    print({"inserted": inserted, "total_circles": total})
    for university in ["杏林大学", "東京工科大学"]:
        count = cur.execute(
            """
            select count(*)
            from circles c
            join universities u on u.university_id = c.university_id
            where u.university_name = ? and c.public_status = 'published'
            """,
            (university,),
        ).fetchone()[0]
        print(university, count)


if __name__ == "__main__":
    main()
