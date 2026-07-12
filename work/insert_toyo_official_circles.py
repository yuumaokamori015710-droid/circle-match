from __future__ import annotations

import sqlite3
from datetime import datetime, timezone


DB = "outputs/circlematch.sqlite"
TODAY = datetime.now(timezone.utc).date().isoformat()
SOURCE_URL = "https://www.toyo.ac.jp/club/"


SPORT_MAP = [
    ("野球", "野球"), ("ラクロス", "ラクロス"), ("サッカー", "サッカー"), ("フット", "フットサル"),
    ("バドミントン", "バドミントン"), ("バスケット", "バスケットボール"), ("バレー", "バレーボール"),
    ("卓球", "卓球"), ("ゴルフ", "ゴルフ"), ("弓道", "弓道"), ("空手", "空手"), ("剣道", "剣道"),
    ("柔道", "柔道"), ("少林寺拳法", "少林寺拳法"), ("合気道", "武道"), ("日本拳法", "武道"),
    ("アーチェリー", "アーチェリー"), ("ヨット", "ヨット"), ("山岳", "山岳"), ("ワンダーフォーゲル", "アウトドア"),
    ("自転車", "自転車"), ("自動車", "自動車"), ("ハンドボール", "ハンドボール"),
    ("アメリカンフットボール", "アメリカンフットボール"), ("ローラースケート", "ローラースケート"),
    ("キックボクシング", "キックボクシング"), ("カバディ", "カバディ"), ("陸上", "陸上競技"),
    ("将棋", "将棋"), ("ボードゲーム", "ゲーム"), ("ゲーム", "ゲーム"), ("ダンス", "ダンス"),
    ("音楽", "音楽"), ("Rock", "音楽"), ("Voci", "音楽"), ("I.D.S", "音楽"), ("映画", "映画"),
    ("シネマ", "映画"), ("英語", "英語"), ("English", "英語"), ("国際", "国際交流"), ("SDGs", "ボランティア"),
    ("ボランティア", "ボランティア"), ("環境", "環境"), ("情報技術", "プログラミング"), ("組み込み", "プログラミング"),
]


GROUPS = [
    ("体育会弓道部", "部活", "白山キャンパス", "https://www.toyo.ac.jp/club/hakusan/club/"),
    ("應援指導部", "部活", "白山キャンパス", "https://www.toyo.ac.jp/club/hakusan/club/"),
    ("ゴルフ部", "部活", "白山キャンパス", "https://www.toyo.ac.jp/club/hakusan/club/"),
    ("Ⅰ部バドミントン部", "部活", "白山キャンパス", "https://www.toyo.ac.jp/club/hakusan/club/"),
    ("山岳部", "部活", "白山キャンパス", "https://www.toyo.ac.jp/club/hakusan/club/"),
    ("二部体育会空手道部", "部活", "白山キャンパス", "https://www.toyo.ac.jp/club/hakusan/club/"),
    ("Ⅱ部卓球部", "部活", "白山キャンパス", "https://www.toyo.ac.jp/club/hakusan/club/"),
    ("ローラースケート部", "部活", "白山キャンパス", "https://www.toyo.ac.jp/club/hakusan/club/"),
    ("アメリカンフットボール部", "部活", "白山キャンパス", "https://www.toyo.ac.jp/club/hakusan/club/"),
    ("キックボクシング部", "部活", "白山キャンパス", "https://www.toyo.ac.jp/club/hakusan/club/"),
    ("ハンドボール部", "部活", "白山キャンパス", "https://www.toyo.ac.jp/club/hakusan/club/"),
    ("ローバースカウト部", "部活", "白山キャンパス", "https://www.toyo.ac.jp/club/hakusan/club/"),
    ("少林寺拳法部", "部活", "白山キャンパス", "https://www.toyo.ac.jp/club/hakusan/club/"),
    ("Ⅰ部合気道部", "部活", "白山キャンパス", "https://www.toyo.ac.jp/club/hakusan/club/"),
    ("日本拳法部", "部活", "白山キャンパス", "https://www.toyo.ac.jp/club/hakusan/club/"),
    ("体育会ヨット部", "部活", "白山キャンパス", "https://www.toyo.ac.jp/club/hakusan/club/"),
    ("ラクロス部（男子）", "部活", "白山キャンパス", "https://www.toyo.ac.jp/club/hakusan/club/"),
    ("一部体育会アーチェリー部", "部活", "白山キャンパス", "https://www.toyo.ac.jp/club/hakusan/club/"),
    ("軟式野球部", "部活", "白山キャンパス", "https://www.toyo.ac.jp/club/hakusan/club/"),
    ("ラクロス部（女子）", "部活", "白山キャンパス", "https://www.toyo.ac.jp/club/hakusan/club/"),
    ("自転車愛好会", "同好会", "白山キャンパス", "https://www.toyo.ac.jp/club/hakusan/club/?pageID=2"),
    ("第１部ワンダーフォーゲル部", "部活", "白山キャンパス", "https://www.toyo.ac.jp/club/hakusan/club/?pageID=2"),
    ("バドミントン部", "部活", "川越キャンパス", "https://www.toyo.ac.jp/club/kawagoe/club/"),
    ("ボディビル部", "部活", "川越キャンパス", "https://www.toyo.ac.jp/club/kawagoe/club/"),
    ("バレーボール部", "部活", "川越キャンパス", "https://www.toyo.ac.jp/club/kawagoe/club/"),
    ("バスケットボール部", "部活", "川越キャンパス", "https://www.toyo.ac.jp/club/kawagoe/club/"),
    ("卓球部", "部活", "川越キャンパス", "https://www.toyo.ac.jp/club/kawagoe/club/"),
    ("柔道部", "部活", "川越キャンパス", "https://www.toyo.ac.jp/club/kawagoe/club/"),
    ("自動車部", "部活", "川越キャンパス", "https://www.toyo.ac.jp/club/kawagoe/club/"),
    ("剣道部", "部活", "川越キャンパス", "https://www.toyo.ac.jp/club/kawagoe/club/"),
    ("弓道部", "部活", "川越キャンパス", "https://www.toyo.ac.jp/club/kawagoe/club/"),
    ("空手道部", "部活", "川越キャンパス", "https://www.toyo.ac.jp/club/kawagoe/club/"),
    ("Belle Voci", "公認サークル", "朝霞キャンパス", "https://www.toyo.ac.jp/club/asaka/circle/"),
    ("iPS", "公認サークル", "朝霞キャンパス", "https://www.toyo.ac.jp/club/asaka/circle/"),
    ("Lucky Strike", "公認サークル", "朝霞キャンパス", "https://www.toyo.ac.jp/club/asaka/circle/"),
    ("Joy.Rock.Junkie", "公認サークル", "朝霞キャンパス", "https://www.toyo.ac.jp/club/asaka/circle/"),
    ("ミントン", "公認サークル", "朝霞キャンパス", "https://www.toyo.ac.jp/club/asaka/circle/"),
    ("PEANUTS", "公認サークル", "朝霞キャンパス", "https://www.toyo.ac.jp/club/asaka/circle/"),
    ("陸上同好会", "同好会", "朝霞キャンパス", "https://www.toyo.ac.jp/club/asaka/circle/"),
    ("朝霞キャンパスSDGsアンバサダー", "学生団体", "朝霞キャンパス", "https://www.toyo.ac.jp/club/asaka/circle/"),
    ("女子ラクロス部", "部活", "朝霞キャンパス", "https://www.toyo.ac.jp/club/asaka/circle/"),
    ("Clorets", "公認サークル", "朝霞キャンパス", "https://www.toyo.ac.jp/club/asaka/circle/"),
    ("English Study Circle", "公認サークル", "朝霞キャンパス", "https://www.toyo.ac.jp/club/asaka/circle/"),
    ("LOT", "公認サークル", "朝霞キャンパス", "https://www.toyo.ac.jp/club/asaka/circle/"),
    ("霞祭実行委員", "学生団体", "朝霞キャンパス", "https://www.toyo.ac.jp/club/asaka/circle/"),
    ("学ボラ", "学生団体", "朝霞キャンパス", "https://www.toyo.ac.jp/club/asaka/circle/"),
    ("StellaHerb", "公認サークル", "朝霞キャンパス", "https://www.toyo.ac.jp/club/asaka/circle/"),
    ("大道芸サークルPASTIME", "公認サークル", "朝霞キャンパス", "https://www.toyo.ac.jp/club/asaka/circle/"),
    ("シネマ受容体", "公認サークル", "朝霞キャンパス", "https://www.toyo.ac.jp/club/asaka/circle/"),
    ("環境保全研究会", "公認サークル", "朝霞キャンパス", "https://www.toyo.ac.jp/club/asaka/circle/"),
    ("朝霞将棋研究会", "公認サークル", "朝霞キャンパス", "https://www.toyo.ac.jp/club/asaka/circle/"),
    ("VABO", "公認サークル", "朝霞キャンパス", "https://www.toyo.ac.jp/club/asaka/circle/"),
    ("いたばん", "公認サークル", "朝霞キャンパス", "https://www.toyo.ac.jp/club/asaka/circle/"),
    ("エンジョイフットライン", "公認サークル", "朝霞キャンパス", "https://www.toyo.ac.jp/club/asaka/circle/"),
    ("b-jam", "公認サークル", "朝霞キャンパス", "https://www.toyo.ac.jp/club/asaka/circle/"),
    ("I.D.S", "公認サークル", "朝霞キャンパス", "https://www.toyo.ac.jp/club/asaka/circle/"),
    ("Toyo Red Birds", "公認サークル", "赤羽台キャンパス", "https://www.toyo.ac.jp/club/akabanedai1/"),
    ("秘密基地 きりがく", "公認サークル", "赤羽台キャンパス", "https://www.toyo.ac.jp/club/akabanedai1/"),
    ("ボードゲーム地域交流団体ほどのわ", "公認サークル", "赤羽台キャンパス", "https://www.toyo.ac.jp/club/akabanedai1/"),
    ("東洋大学カバディサークル", "公認サークル", "赤羽台キャンパス", "https://www.toyo.ac.jp/club/akabanedai1/"),
    ("Wing!!", "公認サークル", "赤羽台キャンパス", "https://www.toyo.ac.jp/club/akabanedai1/"),
    ("FLUGEL", "公認サークル", "赤羽台キャンパス", "https://www.toyo.ac.jp/club/akabanedai1/"),
    ("English Community Initiative(ECI)", "公認サークル", "赤羽台キャンパス", "https://www.toyo.ac.jp/club/akabanedai1/"),
    ("Iris", "公認サークル", "赤羽台キャンパス", "https://www.toyo.ac.jp/club/akabanedai1/"),
    ("disegnare", "公認サークル", "赤羽台キャンパス", "https://www.toyo.ac.jp/club/akabanedai1/"),
    ("エアロビックダンスサークルACE", "公認サークル", "赤羽台キャンパス", "https://www.toyo.ac.jp/club/akabanedai1/"),
    ("Tomboys☆", "公認サークル", "赤羽台キャンパス", "https://www.toyo.ac.jp/club/akabanedai1/"),
    ("てのりぴーたん", "公認サークル", "赤羽台キャンパス", "https://www.toyo.ac.jp/club/akabanedai1/"),
    ("跳舞人", "公認サークル", "赤羽台キャンパス", "https://www.toyo.ac.jp/club/akabanedai1/"),
    ("SeaD", "公認サークル", "赤羽台キャンパス", "https://www.toyo.ac.jp/club/akabanedai1/"),
    ("学ボラてって", "学生団体", "赤羽台キャンパス", "https://www.toyo.ac.jp/club/akabanedai1/"),
    ("ほーろっく☆よーがっく", "公認サークル", "赤羽台キャンパス", "https://www.toyo.ac.jp/club/akabanedai1/"),
    ("東洋大学WELLB-FES実行委員会", "学生団体", "赤羽台キャンパス", "https://www.toyo.ac.jp/club/akabanedai1/"),
    ("IGC 2", "公認サークル", "赤羽台キャンパス", "https://www.toyo.ac.jp/club/akabanedai2/"),
    ("RAISON DÊTRE", "公認サークル", "赤羽台キャンパス", "https://www.toyo.ac.jp/club/akabanedai2/"),
    ("TokyoDeeps", "公認サークル", "赤羽台キャンパス", "https://www.toyo.ac.jp/club/akabanedai2/"),
    ("SHARK", "公認サークル", "赤羽台キャンパス", "https://www.toyo.ac.jp/club/akabanedai2/"),
    ("情報技術メディア研究会（GeeKEN）", "公認サークル", "赤羽台キャンパス", "https://www.toyo.ac.jp/club/akabanedai2/"),
    ("Noah's Ark", "公認サークル", "赤羽台キャンパス", "https://www.toyo.ac.jp/club/akabanedai2/"),
    ("にゃっ卓", "公認サークル", "赤羽台キャンパス", "https://www.toyo.ac.jp/club/akabanedai2/"),
    ("BTL", "公認サークル", "赤羽台キャンパス", "https://www.toyo.ac.jp/club/akabanedai2/"),
    ("赤羽台祭実行委員会INIAD部門", "学生団体", "赤羽台キャンパス", "https://www.toyo.ac.jp/club/akabanedai2/"),
    ("INIActors", "公認サークル", "赤羽台キャンパス", "https://www.toyo.ac.jp/club/akabanedai2/"),
    ("INIAD組み込み研究会", "公認サークル", "赤羽台キャンパス", "https://www.toyo.ac.jp/club/akabanedai2/"),
]


def sport_for(name: str) -> str:
    for keyword, sport in SPORT_MAP:
        if keyword in name:
            return sport
    return "その他"


def main() -> None:
    con = sqlite3.connect(DB)
    cur = con.cursor()
    university_id = cur.execute("select university_id from universities where university_name='東洋大学'").fetchone()[0]
    inserted = 0
    for name, org_type, area, url in GROUPS:
        circle_id = "c_u_東洋大学_" + "".join(ch if ch.isalnum() else "_" for ch in name).strip("_")
        before = cur.execute(
            "select circle_id from circles where university_id=? and circle_name=?",
            (university_id, name),
        ).fetchone()
        cur.execute(
            """
            insert into circles (
              circle_id, university_id, circle_name, organization_type, sport_category,
              activity_area, source_type, source_url, verification_status, public_status,
              last_checked_at, created_at, updated_at
            ) values (?, ?, ?, ?, ?, ?, 'university_official', ?, 'university_verified', 'published', ?, ?, ?)
            on conflict(university_id, circle_name) do update set
              organization_type=excluded.organization_type,
              sport_category=excluded.sport_category,
              activity_area=excluded.activity_area,
              source_type=excluded.source_type,
              source_url=excluded.source_url,
              verification_status=excluded.verification_status,
              public_status=excluded.public_status,
              last_checked_at=excluded.last_checked_at,
              updated_at=excluded.updated_at
            """,
            (circle_id, university_id, name, org_type, sport_for(name), area, url, TODAY, TODAY, TODAY),
        )
        inserted += before is None
    con.commit()
    count = cur.execute(
        """
        select count(*)
        from circles c
        join universities u on u.university_id=c.university_id
        where u.university_name='東洋大学' and c.public_status='published'
        """
    ).fetchone()[0]
    print({"inserted": inserted, "published": count})


if __name__ == "__main__":
    main()
