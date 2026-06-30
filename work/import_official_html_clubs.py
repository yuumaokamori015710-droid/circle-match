import json
import re
import hashlib
import sqlite3
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

DB_PATH = Path("outputs/circlematch.sqlite")


class TextParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        text = " ".join(data.split())
        if text:
            self.parts.append(text)


def now():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def slug(prefix, text):
    base = "".join(ch.lower() if ch.isalnum() else "_" for ch in text).strip("_")
    digest = hashlib.sha1(text.encode("utf-8")).hexdigest()[:8]
    return f"{prefix}_{base[:40]}_{digest}"


def fetch_parts(url):
    data = urllib.request.urlopen(url, timeout=30).read().decode("utf-8", "ignore")
    parser = TextParser()
    parser.feed(data)
    return parser.parts


def sport_category(name):
    rules = [
        ("サッカー", ["サッカー", "蹴球", "ソッカー", "フースバル"]),
        ("フットサル", ["フットサル"]),
        ("バスケットボール", ["バスケット"]),
        ("テニス", ["テニス", "庭球", "TENNIS", "ローンテニス"]),
        ("バレーボール", ["バレーボール", "VOLLEYBALL", "排球"]),
        ("野球", ["野球"]),
        ("バドミントン", ["バドミントン"]),
        ("ラグビー", ["ラグビー"]),
        ("アメリカンフットボール", ["アメリカンフットボール"]),
        ("ラクロス", ["ラクロス"]),
        ("ハンドボール", ["ハンドボール"]),
        ("ホッケー", ["ホッケー"]),
        ("卓球", ["卓球"]),
        ("陸上競技", ["陸上"]),
        ("水泳", ["水泳", "ドルフィン"]),
        ("武道", ["合気道", "空手", "弓道", "剣道", "拳法", "柔道", "少林寺", "居合", "太極拳"]),
        ("その他", []),
    ]
    for category, needles in rules:
        if any(needle in name for needle in needles):
            return category
    return "その他"


def clean_name(name):
    return re.sub(r"\s+", " ", name).strip()


def audit(conn, action, entity_type, entity_id, payload):
    conn.execute(
        "insert into audit_logs(action, entity_type, entity_id, payload, created_at) values(?,?,?,?,?)",
        (action, entity_type, entity_id, json.dumps(payload, ensure_ascii=False), now()),
    )


def upsert_circle(conn, university_name, circle_name, source_url, note):
    uni = conn.execute(
        "select university_id from universities where university_name=? order by campus_name limit 1",
        (university_name,),
    ).fetchone()
    if not uni:
        raise ValueError(f"university not found: {university_name}")
    circle_name = clean_name(circle_name)
    circle_id = slug("c", uni["university_id"] + "_" + circle_name)
    timestamp = now()
    before = conn.execute(
        "select circle_id from circles where university_id=? and circle_name=?",
        (uni["university_id"], circle_name),
    ).fetchone()
    conn.execute(
        """
        insert into circles(circle_id, university_id, circle_name, sport_category, activity_area, source_type, source_url,
          verification_status, public_status, last_checked_at, sns_url, owner_notes, created_at, updated_at)
        values(?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        on conflict(university_id, circle_name) do update set
          sport_category=excluded.sport_category,
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
            uni["university_id"],
            circle_name,
            sport_category(circle_name),
            "",
            "university_official",
            source_url,
            "university_verified",
            "published",
            now()[:10],
            "",
            note,
            timestamp,
            timestamp,
        ),
    )
    saved_id = conn.execute(
        "select circle_id from circles where university_id=? and circle_name=?",
        (uni["university_id"], circle_name),
    ).fetchone()["circle_id"]
    conn.execute(
        "insert or replace into data_sources(source_id, entity_type, entity_id, source_type, source_url, memo, checked_at, created_at) values(?,?,?,?,?,?,?,?)",
        (slug("src", saved_id + source_url), "circle", saved_id, "university_official", source_url, note, now()[:10], timestamp),
    )
    if not before:
        audit(conn, "official_html_import", "circle", saved_id, {"university": university_name, "circle_name": circle_name, "source_url": source_url})
        return 1
    return 0


def extract_chuo():
    url = "https://www.chuo-u.ac.jp/activities/club/"
    parts = fetch_parts(url)
    # Official Chuo page lists sports clubs at 871-984 and culture/academic clubs at 996-1116.
    names = []
    for start, end in [(871, 984), (996, 1003), (1007, 1042), (1046, 1083), (1087, 1116)]:
        names.extend(parts[start : end + 1])
    stopwords = {"全て見る"}
    names = [n for n in names if n not in stopwords and not n.startswith("全て")]
    return "中央大学", url, names, "中央大学公式のサークル・部会一覧から団体名のみ登録"


def extract_nihon():
    url = "https://www.nihon-u.ac.jp/campuslife/club/"
    parts = fetch_parts(url)
    names = parts[15:25] + parts[33:40]
    return "日本大学", url, names, "日本大学公式のサークル紹介ページから本部所属団体名のみ登録"


def extract_meiji_pages():
    urls = [
        "https://www.meiji.ac.jp/campus/circle/rikaren.html",
        "https://www.meiji.ac.jp/campus/circle/taidouren.html",
        "https://www.meiji.ac.jp/campus/circle/og.html",
        "https://www.meiji.ac.jp/campus/circle/jg.html",
        "https://www.meiji.ac.jp/campus/circle/rg.html",
        "https://www.meiji.ac.jp/campus/circle/doukoukai_bun.html",
        "https://www.meiji.ac.jp/campus/circle/doukoukai_sp.html",
    ]
    heading_stopwords = {
        "本部", "研究", "（理系）", "アウトドア", "ウインター", "格闘技", "武道", "球技", "マリン",
        "その他", "音楽", "芸術", "芸能", "教養", "文化", "自然科学", "言語", "ボランティア",
        "レクリエーション", "スポーツ", "サッカー", "フットサル", "テニス", "バドミントン",
        "バスケット", "ボール", "バレーボール", "ハンドボール", "野球", "ダンス", "ゴルフ",
        "スカッシュ", "ビリヤード", "オールラウンド", "ピックルボール",
        "公認サークル一覧", "学生生活", "奨学金", "体育会", "サークル活動",
    }
    names = []
    for url in urls:
        parts = fetch_parts(url)
        start = 135
        end = next((idx for idx, value in enumerate(parts) if idx > start and value == "学生生活"), len(parts))
        for name in parts[start:end]:
            name = clean_name(name)
            if not name or name in heading_stopwords:
                continue
            if len(name) > 60:
                continue
            if name.startswith("一覧") or name.endswith("一覧"):
                continue
            names.append(name)
    deduped = list(dict.fromkeys(names))
    return "明治大学", "https://www.meiji.ac.jp/campus/circle/", deduped, "明治大学公式の公認サークル一覧から団体名のみ登録"


def extract_ritsumeikan_pages():
    pages = [
        ("https://www.ritsumei.ac.jp/sports-culture/sports/group/", 55, 145),
        ("https://www.ritsumei.ac.jp/sports-culture/culture/group/", 55, 241),
    ]
    heading_stopwords = {
        "野球", "ソフトボール", "サッカー系", "フットサル", "バスケットボール", "テニス",
        "バトミントン", "バレーボール", "その他球技系", "武道系", "マリン・スノー系",
        "アウトドア・ツーリング系", "スポーツ系 オールジャンル", "スポーツ系その他",
        "SPORTS", "体育会公認クラブ", "体育会同好会", "登録団体", "学芸総部 公認団体",
        "学芸総部 同好会", "学芸総部 任意団体", "中央パート", "研究系", "ボランティア系",
        "伝統系", "音楽系", "表現系", "文芸系", "文化系その他", "料理系", "社会・環境系",
    }
    names = []
    opener = urllib.request.build_opener()
    opener.addheaders = [("User-Agent", "Mozilla/5.0")]
    for url, start, end in pages:
        data = opener.open(url, timeout=30).read().decode("utf-8", "ignore")
        parser = TextParser()
        parser.feed(data)
        for name in parser.parts[start : end + 1]:
            name = clean_name(name)
            if not name or name in heading_stopwords or len(name) > 70:
                continue
            names.append(name)
    deduped = list(dict.fromkeys(names))
    return "立命館大学", "https://www.ritsumei.ac.jp/sports-culture/", deduped, "立命館大学公式のスポーツ・文化団体一覧から団体名のみ登録"


def extract_kwansei_pages():
    pages = [
        ("https://www.kwansei.ac.jp/campuslife/club/taiikukai.html", 40, 94),
        ("https://www.kwansei.ac.jp/campuslife/club/bunkasoubu.html", 40, 80),
        ("https://www.kwansei.ac.jp/campuslife/club/tourokudantai.html", 40, 109),
    ]
    heading_stopwords = {
        "体育会", "文化総部", "大学登録団体：西宮上ケ原キャンパス", "大学登録団体：神戸三田キャンパス",
        "大学登録団体：西宮聖和キャンパス", "News", "お知らせ", "About KG",
    }
    names = []
    opener = urllib.request.build_opener()
    opener.addheaders = [("User-Agent", "Mozilla/5.0")]
    for url, start, end in pages:
        data = opener.open(url, timeout=30).read().decode("utf-8", "ignore")
        parser = TextParser()
        parser.feed(data)
        for name in parser.parts[start : min(end + 1, len(parser.parts))]:
            name = clean_name(name)
            if not name or name in heading_stopwords or len(name) > 70:
                continue
            if name in {"関西学院大学について", "Academics", "Research", "Admissions", "Global", "Career", "Life at KG"}:
                continue
            names.append(name)
    deduped = list(dict.fromkeys(names))
    return "関西学院大学", "https://www.kwansei.ac.jp/campuslife/club", deduped, "関西学院大学公式の課外活動団体一覧から団体名のみ登録"


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    inserted = 0
    extractors = [
        extract_chuo(),
        extract_nihon(),
        extract_meiji_pages(),
        extract_ritsumeikan_pages(),
        extract_kwansei_pages(),
    ]
    for university_name, source_url, names, note in extractors:
        for name in names:
            if len(name) > 60:
                continue
            inserted += upsert_circle(conn, university_name, name, source_url, note)
    conn.commit()
    print(json.dumps({
        "inserted": inserted,
        "total_circles": conn.execute("select count(*) from circles").fetchone()[0],
        "verified": conn.execute("select count(*) from circles where verification_status in ('claimed','university_verified','admin_verified')").fetchone()[0],
    }, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
