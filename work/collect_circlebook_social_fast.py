import html
import os
import re
import sys
import time
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "outputs"))

import circlematch_db_app as app  # noqa: E402
from collect_circlebook_social_circles import (  # noqa: E402
    BASE_URL,
    LIST_URL,
    PREFECTURES,
    REQUEST_DELAY_SECONDS,
    USER_AGENT,
    clean_text,
    ensure_social_parent,
    infer_social_sport,
    is_valid_name,
    normalize_existing_social_rows,
)


TARGET_NEW_ROWS = int(os.environ.get("CIRCLEMATCH_COLLECT_TARGET", "1000"))
MAX_LIST_PAGES = int(os.environ.get("CIRCLEMATCH_COLLECT_MAX_LIST_PAGES", "260"))
SOCIAL_LIST_URL = os.environ.get("CIRCLEMATCH_SOCIAL_LIST_URL", f"{BASE_URL}/tags/4?page={{page}}")

NOISE_PHRASES = [
    "telegram",
    "line：",
    "line:",
    "副業",
    "投資",
    "出会い系",
    "付き添いサービス",
    "高品質で安心",
    "占い",
    "レンタル",
    "ビジネス",
    "稼げ",
    "風俗",
    "カジノ",
    "ギャンブル",
    "情報商材",
    "nhacai",
    "nhà cái",
    "casino",
    "kubet",
    "sunwin",
    "f8bet",
    "j9bet",
    "shbet",
    "oxbet",
    "kbet",
    "nbet",
    "cbet",
    "debet",
    "pagbet",
    "uwin",
    "mubet",
    "nohu88",
    "mu88",
    "u88",
    "uu88",
    "jd88",
    "888bet",
    "789win",
    "555win",
    "80win",
    "88win",
    "98win",
    "23win",
    "12win",
    "277bet",
    "1xbet",
    "growlancerr",
]

SPAM_PATTERNS = [
    re.compile(r"\b[a-z]*bet[a-z0-9]*\b", re.I),
    re.compile(r"\b\d+[a-z]*(?:bet|win)[a-z0-9]*\b", re.I),
    re.compile(r"\b[a-z]+88[a-z0-9]*\b", re.I),
    re.compile(r"\b[a-z]+com\d*\b", re.I),
]

SPAM_NAME_WHITELIST = {"blowing", "kobe musicada wind"}


def is_noise_blob(text):
    lowered = text.lower()
    normalized = re.sub(r"\s+", " ", lowered).strip()
    if normalized in SPAM_NAME_WHITELIST:
        return False
    if any(phrase in lowered for phrase in NOISE_PHRASES):
        return True
    return any(pattern.search(lowered) for pattern in SPAM_PATTERNS)


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    last_error = None
    for attempt in range(1, 4):
        try:
            with urllib.request.urlopen(req, timeout=35) as response:
                return response.read().decode("utf-8", "ignore")
        except TimeoutError as exc:
            last_error = exc
            time.sleep(2 * attempt)
    raise last_error


def card_blocks(list_html):
    parts = list_html.split("<li class='user_item_wrap'>")
    for part in parts[1:]:
        yield "<li class='user_item_wrap'>" + part.split("<li class='user_item_wrap'>", 1)[0]


def extract_first(pattern, text):
    match = re.search(pattern, text)
    return clean_text(match.group(1)) if match else ""


def parse_card(block):
    href_match = re.search(r'<a href="/circles/([0-9]+)">', block)
    if not href_match:
        return None
    source_url = f"{BASE_URL}/circles/{href_match.group(1)}"
    tags = re.findall(r'<a href="/tags/[0-9]+">([\s\S]*?)</a>', block)
    tags = [clean_text(tag) for tag in tags]
    if "社会人サークル" not in tags and "社会人サークル" not in clean_text(block):
        return None
    name = extract_first(r"<h2 class='user_name'>([\s\S]*?)</h2>", block)
    name = app.clean_circle_name(name)
    category = extract_first(r"<i class='fa fa-tags icon_c'></i>([\s\S]*?)</span>", block)
    area = extract_first(r"<span class='user_area'>([\s\S]*?)</span>", block).replace("：", " / ")
    recruitment = extract_first(r"<span class='user_recruitment'>([\s\S]*?)</span>", block)
    blob = " ".join([name, category, area, recruitment, " ".join(tags)]).lower()
    if is_noise_blob(blob):
        return None
    if not is_valid_name(name):
        return None
    prefecture = next((pref for pref in PREFECTURES if pref in area), "")
    if not prefecture:
        prefecture = next((pref for pref in PREFECTURES if pref in " ".join(tags)), "東京都")
    city = ""
    city_match = re.search(r"/cities/[^\"']+\">([\s\S]*?)</a>", block)
    if city_match:
        city = clean_text(city_match.group(1))[:40]
    activity_area = area
    activity_area = re.sub(r"^" + re.escape(prefecture) + r"\s*/?\s*", "", activity_area).strip()
    activity_area = activity_area[:80]
    return {
        "source_url": source_url,
        "name": name,
        "category": category,
        "tags": tags,
        "prefecture": prefecture,
        "city": city,
        "activity_area": activity_area,
        "sport": infer_social_sport(name, category, tags),
    }


def source_exists(conn, source_url):
    row = conn.execute("select circle_id from circles where source_url=?", (source_url,)).fetchone()
    return bool(row)


def import_card(conn, item):
    if source_exists(conn, item["source_url"]):
        return "exists"
    university_id = ensure_social_parent(conn, item["prefecture"], "")
    app.upsert_circle(
        conn,
        {
            "university_id": university_id,
            "circle_name": item["name"],
            "organization_type": "社会人サークル",
            "sport_category": item["sport"],
            "activity_area": item["activity_area"],
            "source_type": "public_sns",
            "source_url": item["source_url"],
            "verification_status": "admin_verified",
            "public_status": "published",
            "last_checked_at": app.now(),
        },
        audit_entry=False,
    )
    return "inserted"


def delete_existing_noise(conn):
    rows = conn.execute(
        """
        select c.circle_id, c.circle_name, c.activity_area, c.source_url
        from circles c
        where c.organization_type='社会人サークル'
        """
    ).fetchall()
    deleted = 0
    for row in rows:
        blob = " ".join(str(value or "") for value in row[1:])
        if is_noise_blob(blob):
            conn.execute("delete from circles where circle_id=?", (row[0],))
            deleted += 1
    return deleted


def main():
    app.init_db()
    inserted = 0
    checked = 0
    skipped = {}
    with app.connect() as conn:
        normalize_existing_social_rows(conn)
        removed = delete_existing_noise(conn)
        if removed:
            conn.commit()
            print(f"removed_noise={removed}")
        before = conn.execute("select count(*) from circles where organization_type='社会人サークル'").fetchone()[0]
        for page in range(1, MAX_LIST_PAGES + 1):
            list_html = fetch(SOCIAL_LIST_URL.format(page=page))
            cards = list(card_blocks(list_html))
            if not cards:
                break
            for block in cards:
                checked += 1
                item = parse_card(block)
                if not item:
                    skipped["not_social_or_noise"] = skipped.get("not_social_or_noise", 0) + 1
                    continue
                result = import_card(conn, item)
                if result == "inserted":
                    inserted += 1
                    if inserted % 100 == 0:
                        conn.commit()
                        print(f"inserted={inserted} checked={checked} page={page}")
                else:
                    skipped[result] = skipped.get(result, 0) + 1
                if inserted >= TARGET_NEW_ROWS:
                    break
            conn.commit()
            print(f"page={page} inserted={inserted} checked={checked} skipped={skipped}")
            if inserted >= TARGET_NEW_ROWS:
                break
            time.sleep(REQUEST_DELAY_SECONDS)
        normalize_existing_social_rows(conn)
        removed = delete_existing_noise(conn)
        if removed:
            print(f"removed_noise={removed}")
        conn.commit()
        after = conn.execute("select count(*) from circles where organization_type='社会人サークル'").fetchone()[0]
    print({"before": before, "after": after, "inserted": inserted, "checked": checked, "skipped": skipped})


if __name__ == "__main__":
    main()
