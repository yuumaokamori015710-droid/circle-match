import html
import hashlib
import json
import re
import sqlite3
import sys
import time
import urllib.parse
import urllib.request
from collections import deque
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
DB_PATH = ROOT / "outputs" / "circlematch.sqlite"

KANTO = {"東京都", "神奈川県", "埼玉県", "千葉県", "茨城県", "栃木県", "群馬県"}
LINK_KEYWORDS = [
    "club",
    "circle",
    "activity",
    "activities",
    "campuslife",
    "student",
    "students",
    "サークル",
    "クラブ",
    "課外",
    "体育会",
    "文化会",
    "部活",
    "公認",
    "団体",
]
NAME_MARKERS = ["部", "会", "サークル", "クラブ", "同好会", "研究会", "委員会", "団", "隊", "局"]
EXCLUDE_WORDS = [
    "大学",
    "学部",
    "研究科",
    "入試",
    "採用",
    "資料請求",
    "お問い合わせ",
    "アクセス",
    "キャンパス",
    "ニュース",
    "イベント",
    "説明会",
    "後援会",
    "保護者",
    "卒業生",
    "学生生活",
    "在学生",
    "受験生",
    "個人情報",
    "サイト",
    "ページ",
    "トップ",
    "メニュー",
    "一覧へ",
    "もっと見る",
    "詳細",
    "続きを読む",
    "規則",
    "証明書",
    "奨学金",
    "授業",
    "履修",
    "成績",
    "お知らせ",
    "募集",
    "大会",
    "選手権",
    "リーグ戦",
    "トーナメント",
    "試合",
    "戦績",
    "順位",
    "結果",
    "速報",
    "場所",
    "活動場所",
    "活動日",
    "選手",
    "実施",
    "開催",
    "支給",
    "申請",
    "参考",
    "案内",
    "昇格",
    "金メダル",
    "講習会",
    "活躍",
    "一覧",
    "こちら",
    "について",
    "もっと知る",
    "紹介動画",
    "認定証",
    "補助金",
    "住所変更",
    "研究データ",
    "倫理委員会",
    "令和",
    "年度",
    "全ての方向け",
]
SPORT_RULES = [
    ("サッカー", ["サッカー", "蹴球", "ソッカー"]),
    ("フットサル", ["フットサル"]),
    ("バスケットボール", ["バスケット", "バスケ", "籠球"]),
    ("テニス", ["テニス", "庭球"]),
    ("バレーボール", ["バレーボール", "排球"]),
    ("野球", ["野球", "ベースボール"]),
    ("バドミントン", ["バドミントン", "羽球"]),
    ("ラグビー", ["ラグビー"]),
    ("アメリカンフットボール", ["アメリカンフットボール", "アメフト"]),
    ("ラクロス", ["ラクロス"]),
    ("ハンドボール", ["ハンドボール"]),
    ("ホッケー", ["ホッケー"]),
    ("卓球", ["卓球"]),
    ("陸上競技", ["陸上"]),
    ("水泳", ["水泳", "泳"]),
    ("武道", ["柔道", "空手", "剣道", "合気", "弓道", "少林寺", "拳法"]),
    ("ダンス", ["ダンス", "Dance"]),
    ("音楽", ["合唱", "吹奏楽", "管弦楽", "軽音", "ギター", "ジャズ", "マンドリン"]),
]

MANUAL_SEEDS = {
    "青山学院大学": ["https://www.aoyama.ac.jp/life/activity/club/"],
    "駒澤大学": ["https://www.komazawa-u.ac.jp/campuslife/club/"],
    "お茶の水女子大学": ["https://www.ocha.ac.jp/campuslife/circle/r_extracurricular-activities.html"],
    "神奈川大学": ["https://www.kanagawa-u.ac.jp/campuslife/activities/club/"],
    "茨城大学": ["https://www.ibaraki.ac.jp/m/lifesupport/activity/circle/index.html"],
    "横浜国立大学": ["https://www.ynu.ac.jp/campus/club/"],
}
TEXT_SEED_URLS = {
    "https://www.kanagawa-u.ac.jp/campuslife/activities/club/",
    "https://www.ibaraki.ac.jp/m/lifesupport/activity/circle/index.html",
    "https://www.ynu.ac.jp/campus/club/",
}


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.text = []
        self._href = None
        self._anchor = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._href = dict(attrs).get("href", "")
            self._anchor = []

    def handle_endtag(self, tag):
        if tag == "a" and self._href is not None:
            label = clean(" ".join(self._anchor))
            if label:
                self.links.append((self._href, label))
            self._href = None
            self._anchor = []

    def handle_data(self, data):
        text = clean(data)
        if text:
            self.text.append(text)
            if self._href is not None:
                self._anchor.append(text)


def now():
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def slug(prefix, text):
    base = "".join(ch.lower() if ch.isalnum() else "_" for ch in text).strip("_")
    return f"{prefix}_{base[:80]}"


def unique_circle_id(conn, university_id, name):
    base = slug("c", f"{university_id}_{name}")
    existing = conn.execute("select 1 from circles where circle_id=?", (base,)).fetchone()
    if not existing:
        return base
    digest = hashlib.sha1(f"{university_id}_{name}".encode("utf-8")).hexdigest()[:10]
    return f"{base[:69]}_{digest}"


def clean(value):
    return re.sub(r"\s+", " ", html.unescape(value or "")).strip()


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 CircleMatchBot/0.1"})
    with urllib.request.urlopen(req, timeout=20) as res:
        ctype = res.headers.get("content-type", "").lower()
        raw = res.read()
        final_url = res.geturl()
    if "pdf" in ctype or final_url.lower().endswith(".pdf"):
        return None
    body = raw.decode("utf-8", "ignore")
    parser = PageParser()
    parser.feed(body)
    return final_url, parser


def same_site(url, root_netloc):
    parsed = urllib.parse.urlparse(url)
    return parsed.scheme in {"http", "https"} and parsed.netloc.endswith(root_netloc)


def link_score(url, label):
    blob = f"{url} {label}".lower()
    score = 0
    for keyword in LINK_KEYWORDS:
        if keyword.lower() in blob:
            score += 1
    return score


def is_candidate_name(text):
    text = clean(text)
    if not (2 <= len(text) <= 45):
        return False
    if any(word in text for word in EXCLUDE_WORDS):
        return False
    if re.search(r"^\d{1,2}\.\d{1,2}\s*(Mon|Tue|Wed|Thu|Fri|Sat|Sun|月|火|水|木|金|土|日|\()", text, re.I):
        return False
    if re.search(r"(TOP|一覧|こちら|を見る|について|もっと知る|ご確認ください|活動場所[:：]|活動日[:：])", text):
        return False
    if re.search(r"[。！？、:：/\\]|\\d{4}|http|www\\.|^[A-Z]{3}\\s+\\d+", text, re.I):
        return False
    if re.search(r"[0-9０-９]+月|[0-9０-９]+日|（.*年.*月.*日", text):
        return False
    if not any(marker in text for marker in NAME_MARKERS):
        return False
    if text in {"部", "会", "サークル", "クラブ", "団体", "体育会", "文化会", "同好会"}:
        return False
    return True


def sport_category(name):
    for category, needles in SPORT_RULES:
        if any(needle in name for needle in needles):
            return category
    return "その他"


def organization_type(name):
    if "体育会" in name or name.endswith("部") or "部(" in name or "部（" in name:
        return "部活"
    if "同好会" in name:
        return "同好会"
    if "サークル" in name or "クラブ" in name:
        return "公認サークル"
    if "委員会" in name or "学生会" in name:
        return "学生団体"
    return "公認団体"


def extract_names(parser, source_url=""):
    names = []
    for href, label in parser.links:
        if link_score(href, label) and is_candidate_name(label):
            names.append(label)
    if source_url in TEXT_SEED_URLS:
        for text in parser.text:
            for part in re.split(r"[｜|／/・,、　]{1,}", text):
                part = clean(part)
                if is_candidate_name(part):
                    names.append(part)
    deduped = []
    seen = set()
    for name in names:
        name = re.sub(r"^(体育会|文化会|公認団体|公認サークル)[：:・ ]*", "", name)
        name = clean(name)
        if name not in seen and is_candidate_name(name):
            seen.add(name)
            deduped.append(name)
    return deduped


def crawl_university(university_name, official_url):
    root = urllib.parse.urlparse(official_url)
    root_netloc = root.netloc.replace("www.", "")
    seeds = [official_url]
    seeds.extend(MANUAL_SEEDS.get(university_name, []))
    queue = deque((url, 0) for url in dict.fromkeys(seeds))
    visited = set()
    pages = []
    names_by_page = {}
    while queue and len(visited) < 80:
        url, depth = queue.popleft()
        if url in visited:
            continue
        visited.add(url)
        try:
            result = fetch(url)
        except Exception:
            continue
        if not result:
            continue
        final_url, parser = result
        page_names = extract_names(parser, final_url)
        if page_names:
            names_by_page[final_url] = page_names
        pages.append(final_url)
        if depth >= 2:
            continue
        scored = []
        for href, label in parser.links:
            full = urllib.parse.urljoin(final_url, href).split("#", 1)[0]
            if full in visited or not same_site(full, root_netloc):
                continue
            score = link_score(full, label)
            if score:
                scored.append((score, full))
        for _, full in sorted(scored, reverse=True)[:35]:
            queue.append((full, depth + 1))
        time.sleep(0.15)
    return pages, names_by_page


def upsert_circle(conn, university_id, university_name, name, source_url):
    existing = conn.execute(
        "select circle_id from circles where university_id=? and circle_name=?",
        (university_id, name),
    ).fetchone()
    circle_id = existing["circle_id"] if existing else unique_circle_id(conn, university_id, name)
    timestamp = now()
    conn.execute(
        """
        insert into circles(
          circle_id, university_id, circle_name, organization_type, sport_category, activity_area,
          source_type, source_url, verification_status, public_status,
          last_checked_at, sns_url, owner_notes, created_at, updated_at
        )
        values(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        on conflict(university_id, circle_name) do update set
          source_type=excluded.source_type,
          source_url=excluded.source_url,
          verification_status=excluded.verification_status,
          public_status=excluded.public_status,
          last_checked_at=excluded.last_checked_at,
          updated_at=excluded.updated_at
        """,
        (
            circle_id,
            university_id,
            name,
            organization_type(name),
            sport_category(name),
            university_name,
            "university_official",
            source_url,
            "university_verified",
            "published",
            timestamp[:10],
            "",
            "",
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
            slug("src", f"{circle_id}_{source_url}"),
            "circle",
            circle_id,
            "university_official",
            source_url,
            f"{university_name}公式サイトから団体名のみ登録",
            timestamp[:10],
            timestamp,
        ),
    )
    if not existing:
        conn.execute(
            "insert into audit_logs(action, entity_type, entity_id, payload, created_at) values(?,?,?,?,?)",
            (
                "kanto_official_crawl_import",
                "circle",
                circle_id,
                json.dumps({"university": university_name, "circle_name": name, "source_url": source_url}, ensure_ascii=False),
                timestamp,
            ),
        )
        return 1
    return 0


def main():
    max_existing = int(sys.argv[1]) if len(sys.argv) > 1 else 120
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        select u.university_id, u.university_name, u.prefecture, u.official_url, count(c.circle_id) existing
        from universities u
        left join circles c on c.university_id = u.university_id
        group by u.university_id
        order by existing asc, u.prefecture, u.university_name
        """
    ).fetchall()
    targets = [r for r in rows if r["prefecture"] in KANTO and r["existing"] < max_existing and r["official_url"]]
    total_inserted = 0
    detail = []
    for uni in targets:
        pages, names_by_page = crawl_university(uni["university_name"], uni["official_url"])
        inserted = 0
        candidate_count = sum(len(v) for v in names_by_page.values())
        for source_url, names in names_by_page.items():
            for name in names:
                inserted += upsert_circle(conn, uni["university_id"], uni["university_name"], name, source_url)
        conn.commit()
        total_inserted += inserted
        item = {
            "university": uni["university_name"],
            "prefecture": uni["prefecture"],
            "existing_before": uni["existing"],
            "pages_seen": len(pages),
            "candidate_names": candidate_count,
            "inserted": inserted,
        }
        detail.append(item)
        print(json.dumps(item, ensure_ascii=False), flush=True)
    print(json.dumps({"inserted": total_inserted, "detail": detail}, ensure_ascii=False))


if __name__ == "__main__":
    main()
