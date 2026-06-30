import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DB_PATH = Path("outputs/circlematch.sqlite")


def now():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def slug(prefix, text):
    base = "".join(ch.lower() if ch.isalnum() else "_" for ch in text).strip("_")
    return f"{prefix}_{base[:48]}"


def sport_category(name):
    rules = [
        ("サッカー", ["サッカー", "ソッカー", "蹴球", "Association Football"]),
        ("フットサル", ["フットサル"]),
        ("バスケットボール", ["バスケット"]),
        ("テニス", ["庭球", "Tennis"]),
        ("バレーボール", ["バレーボール", "VOLLEYBALL"]),
        ("野球", ["野球", "Baseball"]),
        ("バドミントン", ["バドミントン", "Badminton"]),
        ("ラグビー", ["ラグビー", "Rugby"]),
        ("アメリカンフットボール", ["アメリカンフットボール", "American Football"]),
        ("ラクロス", ["ラクロス", "Lacrosse"]),
        ("ハンドボール", ["ハンドボール", "Handball"]),
        ("ホッケー", ["ホッケー", "Hockey"]),
        ("卓球", ["卓球", "Table Tennis"]),
        ("水泳", ["水泳", "Aquatics"]),
        ("陸上競技", ["競走", "Athletic Club"]),
        ("武道", ["柔道", "剣道", "弓術", "空手", "合氣道", "少林寺拳法", "拳法", "Judo", "Kendo", "Kyudo", "Karate", "Aikido", "Kempo"]),
        ("その他", []),
    ]
    for category, needles in rules:
        if any(needle in name for needle in needles):
            return category
    return "その他"


SOURCE_NOTES = {
    "waseda": {
        "source_url": "https://www.waseda.jp/inst/athletic/en/club/",
        "source_type": "university_official",
        "verification_status": "university_verified",
        "note": "早稲田大学競技スポーツセンター公式クラブ一覧から、団体名と競技カテゴリのみ登録",
    },
    "keio": {
        "source_url": "https://www.uaa.keio.ac.jp/club/index.html",
        "source_type": "university_official",
        "verification_status": "university_verified",
        "note": "慶應義塾体育会公式の各部紹介から、団体名と競技カテゴリのみ登録",
    },
    "kobe": {
        "source_url": "https://en.wikipedia.org/wiki/Kansai_Collegiate_American_Football_League",
        "source_type": "other",
        "verification_status": "admin_verified",
        "note": "関西学生アメリカンフットボールリーグの公開情報で神戸大学Ravensを確認。大学公式確認は追加調査待ち",
    },
}


DATA = [
    {
        "university": "早稲田大学",
        "source": "waseda",
        "activity_area": "東京都新宿区",
        "circles": [
            "Baseball Club",
            "Tennis Team",
            "Rowing Club",
            "Kendo Club",
            "Judo Club",
            "Kyudo Club",
            "Waseda Aquatics Team",
            "Athletic Club",
            "Sumo Club",
            "Rugby Football Club",
            "Alpine Club",
            "Ski Team",
            "Skate Club",
            "Basketball Dept",
            "Association Football Club",
            "Equestrian Team",
            "Table Tennis Club",
            "Boxing Club",
            "Gymnastics Club",
            "Karate Club",
            "VOLLEYBALL TEAM",
            "Wrestling Team",
            "Automobile Driving Club",
            "American Football Team",
            "Sailing Team",
            "Handball Club",
            "Hockey Club",
            "Fencing Club",
            "Cheer Leading Club",
            "Soft Tennis Club",
            "Junko Baseball Club",
            "Cycling Club",
            "Badminton Club",
            "Aviation Club",
            "Wandervogel Club",
            "Golf Team",
            "Weightlifting Team",
            "Shooting Club",
            "Aikido Club",
            "Archery Club",
            "Softball Teams",
            "Nippon Kempo Club",
            "Lacrosse Team",
            "Shorinji Kempo Club",
        ],
    },
    {
        "university": "慶應義塾大学",
        "source": "keio",
        "activity_area": "東京都港区・神奈川県横浜市ほか",
        "circles": [
            "柔道部",
            "剣道部",
            "弓術部",
            "端艇部（ボート）",
            "端艇部（カヌー）",
            "水泳部（競泳部門）",
            "水泳部（飛込部門）",
            "水泳部（水球部門）",
            "水泳部（葉山部門）",
            "野球部",
            "蹴球部",
            "庭球部（男子）",
            "庭球部（女子）",
            "器械体操部",
            "競走部",
            "馬術部",
            "ホッケー部（男子）",
            "ホッケー部（女子）",
            "相撲部",
            "山岳部",
            "ソッカー部（男子）",
            "ソッカー部（女子）",
            "スケート部（スピード部門）",
            "スケート部（フィギュア部門）",
            "スケート部（ホッケー部門）",
            "バスケットボール部（男子）",
            "バスケットボール部（女子）",
            "スキー部",
            "空手部",
            "卓球部",
            "ヨット部",
            "射撃部",
            "バレーボール部（男子）",
            "バレーボール部（女子）",
            "レスリング部",
            "ボクシング部",
            "アメリカンフットボール部",
            "ハンドボール部（男子）",
            "ハンドボール部（女子）",
            "フェンシング部",
            "ソフトテニス部（男子）",
            "ソフトテニス部（女子）",
            "バドミントン部",
            "自動車部",
            "準硬式野球部",
            "重量挙部",
            "航空部",
            "ゴルフ部（男子）",
            "ゴルフ部（女子）",
            "合氣道部",
            "洋弓部",
            "少林寺拳法部",
            "拳法部",
            "ラクロス部（男子）",
            "ラクロス部（女子）",
            "自転車競技部",
            "軟式野球部",
            "水上スキー部",
            "應援指導部",
        ],
    },
    {
        "university": "神戸大学",
        "source": "kobe",
        "activity_area": "兵庫県神戸市",
        "circles": [
            "アメリカンフットボール部 RAVENS",
        ],
    },
]


def audit(conn, action, entity_type, entity_id, payload):
    conn.execute(
        "insert into audit_logs(action, entity_type, entity_id, payload, created_at) values(?,?,?,?,?)",
        (action, entity_type, entity_id, json.dumps(payload, ensure_ascii=False), now()),
    )


def insert_source(conn, circle_id, source):
    source_id = slug("src", circle_id + source["source_url"])
    conn.execute(
        """
        insert or replace into data_sources(source_id, entity_type, entity_id, source_type, source_url, memo, checked_at, created_at)
        values(?,?,?,?,?,?,?,?)
        """,
        (
            source_id,
            "circle",
            circle_id,
            source["source_type"],
            source["source_url"],
            source["note"],
            now()[:10],
            now(),
        ),
    )


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    inserted = 0
    updated = 0
    missing_universities = []

    for block in DATA:
        uni = conn.execute(
            "select university_id from universities where university_name=? order by campus_name limit 1",
            (block["university"],),
        ).fetchone()
        if not uni:
            missing_universities.append(block["university"])
            continue
        university_id = uni["university_id"]
        source = SOURCE_NOTES[block["source"]]
        for circle_name in block["circles"]:
            existing = conn.execute(
                "select circle_id from circles where university_id=? and circle_name=?",
                (university_id, circle_name),
            ).fetchone()
            circle_id = existing["circle_id"] if existing else slug("c", university_id + "_" + circle_name)
            timestamp = now()
            conn.execute(
                """
                insert into circles(circle_id, university_id, circle_name, sport_category, activity_area, source_type, source_url,
                  verification_status, public_status, last_checked_at, sns_url, owner_notes, created_at, updated_at)
                values(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                on conflict(university_id, circle_name) do update set
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
                    university_id,
                    circle_name,
                    sport_category(circle_name),
                    block["activity_area"],
                    source["source_type"],
                    source["source_url"],
                    source["verification_status"],
                    "published",
                    now()[:10],
                    "",
                    source["note"],
                    timestamp,
                    timestamp,
                ),
            )
            insert_source(conn, circle_id, source)
            audit(conn, "real_data_import", "circle", circle_id, {
                "university": block["university"],
                "circle_name": circle_name,
                "source_url": source["source_url"],
            })
            if existing:
                updated += 1
            else:
                inserted += 1

    conn.commit()
    summary = {
        "inserted": inserted,
        "updated": updated,
        "missing_universities": missing_universities,
        "total_circles": conn.execute("select count(*) from circles").fetchone()[0],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
