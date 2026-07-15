import html
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "outputs"))

import circlematch_db_app as app  # noqa: E402


BASE_URL = "https://circle-book.com"
LIST_URL = BASE_URL + "/circles?page={page}"
USER_AGENT = "CircleMatchBot/0.1 (+https://circle-match.onrender.com/contact)"
REQUEST_DELAY_SECONDS = float(os.environ.get("CIRCLEMATCH_COLLECT_DELAY_SECONDS", "0.35"))
TARGET_NEW_ROWS = int(os.environ.get("CIRCLEMATCH_COLLECT_TARGET", "1000"))
MAX_LIST_PAGES = int(os.environ.get("CIRCLEMATCH_COLLECT_MAX_LIST_PAGES", "120"))


PREFECTURES = sorted(app.PREFECTURES, key=len, reverse=True)
NOISE_NAMES = {
    "募集中",
    "メンバー募集",
    "サークルメンバー募集",
    "社会人サークル",
    "イベント",
}

SOCIAL_SPORT_ALIASES = [
    ("バスケットボール", ["バスケ", "バスケット"]),
    ("バレーボール", ["バレー", "バレーボール", "ソフトバレー"]),
    ("バドミントン", ["バドミントン", "バド"]),
    ("テニス", ["テニス"]),
    ("サッカー", ["サッカー"]),
    ("フットサル", ["フットサル"]),
    ("野球", ["野球", "草野球"]),
    ("卓球", ["卓球"]),
    ("ランニング", ["ランニング", "マラソン", "ジョギング"]),
    ("アウトドア", ["登山", "山歩", "トレッキング", "ハイキング", "アウトドア", "キャンプ"]),
    ("ダンス", ["ダンス"]),
    ("ヨガ", ["ヨガ"]),
    ("料理", ["料理"]),
    ("写真", ["写真", "カメラ"]),
    ("音楽", ["音楽", "軽音", "バンド"]),
    ("ゲーム", ["ゲーム"]),
]


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    with urllib.request.urlopen(req, timeout=25) as response:
        return response.read().decode("utf-8", "ignore")


def clean_text(value):
    value = re.sub(r"<script[\s\S]*?</script>", " ", value, flags=re.I)
    value = re.sub(r"<style[\s\S]*?</style>", " ", value, flags=re.I)
    value = re.sub(r"<[^>]+>", " ", value)
    value = html.unescape(value)
    return re.sub(r"\s+", " ", value).strip()


def extract_ids(list_html):
    ids = []
    seen = set()
    patterns = [
        r'"url"\s*:\s*"/circles/([0-9]+)"',
        r'href="/circles/([0-9]+)"',
    ]
    for pattern in patterns:
        for match in re.finditer(pattern, list_html):
            circle_id = match.group(1)
            if circle_id not in seen:
                seen.add(circle_id)
                ids.append(circle_id)
    return ids


def extract_name(page_html):
    match = re.search(r"<h1 class='user_name'>([\s\S]*?)</h1>", page_html)
    if not match:
        match = re.search(r"<meta property=\"og:title\" content=\"([^\"]+)\"", page_html)
    if not match:
        return ""
    name = clean_text(match.group(1))
    name = re.sub(r"｜.*$", "", name).strip()
    return app.clean_circle_name(name)


def extract_tags(page_html):
    return [clean_text(value) for value in re.findall(r'href="/tags/[0-9]+">([\s\S]*?)</a>', page_html)]


def extract_category(page_html, name):
    schedules = re.findall(r"<div class='user_schedule slide_content'>([\s\S]*?)</div>", page_html)
    if schedules:
        category = clean_text(schedules[0])
        category = re.sub(r"^.*?([^\s]+(?:サークル|チーム|クラブ|会|部|教室|交流会|バスケ|テニス|フットサル|バドミントン|登山|野球|サッカー|バレー|ダンス|卓球|ランニング|ヨガ|料理|写真|音楽|ゲーム|アウトドア))$", r"\1", category)
        if category:
            return category
    title = name
    for suffix in ["サークル", "チーム", "クラブ", "会"]:
        if suffix in title:
            return title
    return "その他"


def extract_area(page_html):
    area = ""
    city = ""
    match = re.search(r"<div class='user_area slide_content'>([\s\S]*?)</div>", page_html)
    if match:
        area = clean_text(match.group(1))
        area = area.replace("：", " / ")
    cities = [clean_text(v) for v in re.findall(r"/cities/[^\"']+\">([\s\S]*?)</a>", page_html)]
    if cities:
        city = cities[0]
    blob = " ".join([area, city])
    prefecture = next((pref for pref in PREFECTURES if pref in blob), "")
    if not prefecture:
        prefecture = "東京都"
    activity_area = city or area
    activity_area = re.sub(r"^" + re.escape(prefecture) + r"\s*/?\s*", "", activity_area).strip()
    activity_area = activity_area[:80]
    return prefecture, city[:40], activity_area


def infer_social_sport(name, category, tags):
    text = " ".join([name or "", category or "", " ".join(tags or [])])
    for sport, keywords in SOCIAL_SPORT_ALIASES:
        if any(keyword in text for keyword in keywords):
            return sport
    return app.infer_sport_category(text, "その他")


def is_social_circle(page_html, tags):
    if "社会人サークル" in tags:
        return True
    return "社会人サークル" in clean_text(page_html[:60000])


def is_valid_name(name):
    if not name or len(name) < 2 or len(name) > 80:
        return False
    if name in NOISE_NAMES:
        return False
    if app.is_invalid_circle_name(name, ""):
        return False
    if any(token in name for token in ["問い合わせ", "ログイン", "サークル検索", "利用規約"]):
        return False
    return True


def ensure_social_parent(conn, prefecture, city):
    university_name = f"社会人サークル（{prefecture}）"
    row = conn.execute(
        "select university_id from universities where university_name=? and campus_name='社会人サークル'",
        (university_name,),
    ).fetchone()
    if row:
        return row["university_id"]
    return app.upsert_university(
        conn,
        {
            "university_name": university_name,
            "prefecture": prefecture,
            "city": "",
            "campus_name": "社会人サークル",
            "official_url": "",
            "source_url": BASE_URL,
        },
        audit=False,
    )


def source_exists(conn, source_url):
    row = conn.execute("select circle_id from circles where source_url=?", (source_url,)).fetchone()
    return bool(row)


def import_one(conn, circlebook_id):
    source_url = f"{BASE_URL}/circles/{circlebook_id}"
    if source_exists(conn, source_url):
        return "exists"
    page_html = fetch(source_url)
    tags = extract_tags(page_html)
    if not is_social_circle(page_html, tags):
        return "not_social"
    name = extract_name(page_html)
    if not is_valid_name(name):
        return "invalid"
    category = extract_category(page_html, name)
    prefecture, city, activity_area = extract_area(page_html)
    sport = infer_social_sport(name, category, tags)
    university_id = ensure_social_parent(conn, prefecture, city)
    app.upsert_circle(
        conn,
        {
            "university_id": university_id,
            "circle_name": name,
            "organization_type": "社会人サークル",
            "sport_category": sport,
            "activity_area": activity_area,
            "source_type": "public_sns",
            "source_url": source_url,
            "verification_status": "admin_verified",
            "public_status": "published",
            "last_checked_at": app.now(),
        },
        audit_entry=False,
    )
    return "inserted"


def normalize_existing_social_rows(conn):
    conn.execute(
        """
        update universities
        set city='', updated_at=?
        where campus_name='社会人サークル' and university_name like '社会人サークル（%'
        """,
        (app.now(),),
    )
    for row in conn.execute(
        """
        select circle_id, circle_name, sport_category
        from circles
        where organization_type='社会人サークル'
        """
    ).fetchall():
        normalized = infer_social_sport(row["circle_name"], row["sport_category"], [])
        if normalized != row["sport_category"]:
            conn.execute(
                "update circles set sport_category=?, updated_at=? where circle_id=?",
                (normalized, app.now(), row["circle_id"]),
            )


def main():
    app.init_db()
    inserted = 0
    checked = 0
    skipped = {}
    seen_ids = set()
    with app.connect() as conn:
        normalize_existing_social_rows(conn)
        before = conn.execute(
            "select count(*) from circles where organization_type='社会人サークル'"
        ).fetchone()[0]
        for page in range(1, MAX_LIST_PAGES + 1):
            list_html = fetch(LIST_URL.format(page=page))
            ids = [circle_id for circle_id in extract_ids(list_html) if circle_id not in seen_ids]
            if not ids:
                break
            seen_ids.update(ids)
            for circlebook_id in ids:
                checked += 1
                try:
                    result = import_one(conn, circlebook_id)
                except (urllib.error.URLError, TimeoutError, ValueError) as exc:
                    result = f"error:{type(exc).__name__}"
                if result == "inserted":
                    inserted += 1
                    if inserted % 50 == 0:
                        conn.commit()
                        print(f"inserted={inserted} checked={checked} page={page}")
                else:
                    skipped[result] = skipped.get(result, 0) + 1
                if inserted >= TARGET_NEW_ROWS:
                    break
                time.sleep(REQUEST_DELAY_SECONDS)
            conn.commit()
            print(f"page={page} inserted={inserted} checked={checked} skipped={skipped}")
            if inserted >= TARGET_NEW_ROWS:
                break
            time.sleep(REQUEST_DELAY_SECONDS)
        after = conn.execute(
            "select count(*) from circles where organization_type='社会人サークル'"
        ).fetchone()[0]
        normalize_existing_social_rows(conn)
        conn.commit()
    print({"before": before, "after": after, "inserted": inserted, "checked": checked, "skipped": skipped})


if __name__ == "__main__":
    main()
