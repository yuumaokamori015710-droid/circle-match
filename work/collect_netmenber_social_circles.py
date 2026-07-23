"""Collect public adult-circle listings from Sports Yarouyo into a separate seed.

The collector only stores public listing data and its source URL.  It does not
collect contact details, and keeps every imported record unverified until a
representative claims it or the operator reviews it.
"""

from __future__ import annotations

import csv
import html
import os
import re
import subprocess
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "outputs"))

import circlematch_db_app as app  # noqa: E402


OUTPUT_PATH = ROOT / "outputs" / "social_circles_seed.csv"
PUBLIC_SEED_PATH = ROOT / "outputs" / "public_circles_seed.csv"
BASE_URL = "https://www.net-menber.com"
LIST_URL = BASE_URL + "/list/index.html?ken={code}&p={page}"
DETAIL_URL = BASE_URL + "/look/data/{listing_id}.html"
USER_AGENT = "CircleMatchDataBot/1.0 (+https://circle-match.jp/contact)"

# The service's prefecture codes.  Collection intentionally starts with Kanto.
KANTO = [
    ("神奈川県", 9),
    ("埼玉県", 10),
    ("千葉県", 11),
    ("茨城県", 12),
    ("栃木県", 13),
    ("群馬県", 14),
    ("東京都", 8),
]

TARGET_NEW_ROWS = int(os.environ.get("CIRCLEMATCH_NETMENBER_TARGET", "900"))
MAX_PAGES_PER_PREFECTURE = int(os.environ.get("CIRCLEMATCH_NETMENBER_MAX_PAGES", "160"))
REQUEST_DELAY_SECONDS = float(os.environ.get("CIRCLEMATCH_NETMENBER_DELAY_SECONDS", "0.45"))

FIELDNAMES = [
    "university_name",
    "prefecture",
    "city",
    "campus_name",
    "official_url",
    "circle_name",
    "organization_type",
    "sport_category",
    "activity_area",
    "source_type",
    "source_url",
    "verification_status",
    "public_status",
    "last_checked_at",
]

SPORT_ALIASES = [
    ("バドミントン", ["バドミントン", "バド"]),
    ("バスケットボール", ["バスケット", "バスケ"]),
    ("バレーボール", ["バレーボール", "バレー", "ソフトバレー"]),
    ("フットサル", ["フットサル"]),
    ("サッカー", ["サッカー", "フットボール"]),
    ("野球", ["草野球", "軟式野球", "野球"]),
    ("テニス", ["テニス"]),
    ("卓球", ["卓球"]),
    ("ランニング", ["ランニング", "マラソン", "ジョギング"]),
    ("ゴルフ", ["ゴルフ"]),
    ("登山", ["登山", "トレッキング", "ハイキング", "山登り"]),
    ("ダンス", ["ダンス", "よさこい"]),
    ("水泳", ["水泳", "スイム"]),
    ("格闘技", ["空手", "柔道", "剣道", "ボクシング", "合気道", "格闘"]),
    ("ヨガ", ["ヨガ", "ピラティス"]),
    ("アウトドア", ["アウトドア", "キャンプ", "釣り", "サイクリング", "自転車"]),
]

ADULT_HINTS = [
    "社会人", "大人", "20代", "30代", "40代", "50代", "60代", "会社員", "仕事帰り",
    "男女", "初心者", "経験者", "運動不足", "ブランク", "友達作り",
]
CHILD_ONLY_PATTERNS = [
    re.compile(r"(?:小学生|中学生|高校生|ジュニア).{0,16}(?:限定|のみ|対象)"),
    re.compile(r"(?:学生|生徒).{0,12}(?:限定|のみ)"),
]
BAD_NAME_TERMS = [
    "副業", "投資", "情報商材", "カジノ", "ギャンブル", "オンラインカジノ", "風俗",
    "出会い系", "高収入", "レンタル彼女", "パパ活", "ママ活", "占い師",
]
BAD_CONTENT_TERMS = [
    "online casino", "online-casino", "1xbet", "kubet", "sunwin", "mubet", "casino",
    "賭博", "競馬予想", "情報商材", "アフィリエイト", "投資案件",
]
EVENT_LIKE_NAME_PATTERNS = [
    re.compile(r"^\s*(?:20\d{2}[./年]|[01]?\d[/-][0-3]?\d)"),
    re.compile(r"^\s*(?:次回|今週|本日|明日|募集開始|開催予定)"),
    # A dated phrase combined with recruitment language is a single event,
    # not a durable group name suitable for the master database.
    re.compile(
        r"(?:\d{1,2}[/-]\d{1,2}|(?:[1-9]|1[0-2])月(?:[0-3]?\d日)?)"
        r".*(?:募集|開催|空き|参加|@)"
    ),
]
NON_CIRCLE_NAME_TERMS = ["アカデミー", "スクール", "教室", "レッスン", "講座", "個人指導"]


def clean_text(value: str) -> str:
    value = re.sub(r"<script[\s\S]*?</script>", " ", value, flags=re.I)
    value = re.sub(r"<style[\s\S]*?</style>", " ", value, flags=re.I)
    value = re.sub(r"<[^>]+>", " ", value)
    return re.sub(r"\s+", " ", html.unescape(value)).strip()


def normalize_name(value: str) -> str:
    value = value.lower().replace("　", " ")
    value = re.sub(r"[\s\-_/・☆★!！?？（）()【】\[\]]+", "", value)
    return value


def fetch(url: str) -> str:
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    error: Exception | None = None
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read().decode("utf-8", "ignore")
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            error = exc
            time.sleep(2 * (attempt + 1))
    raise error or RuntimeError("request failed")


def extract_listing_ids(page_html: str) -> list[str]:
    ids: list[str] = []
    seen: set[str] = set()
    for match in re.finditer(r'href="/look/data/([0-9]+)\.html"', page_html):
        listing_id = match.group(1)
        if listing_id not in seen:
            seen.add(listing_id)
            ids.append(listing_id)
    return ids


def extract_meta_description(page_html: str) -> str:
    match = re.search(r'<meta[^>]+name="description"[^>]+content="([^"]*)"', page_html, re.I)
    if not match:
        match = re.search(r'<meta[^>]+content="([^"]*)"[^>]+name="description"', page_html, re.I)
    return html.unescape(match.group(1)).strip() if match else ""


def extract_name(page_html: str) -> str:
    heading = re.search(r"<h1\b[^>]*>(.*?)</h1>", page_html, re.S | re.I)
    if heading:
        match = re.search(
            r"サークル[「『](.*?)[」』]のメンバー募集情報",
            clean_text(heading.group(1)),
        )
        if match:
            return match.group(1).strip()[:100]
    description = extract_meta_description(page_html)
    match = re.search(r"サークル名\s*[:：]\s*(.*?)\s*サークル設立年", description)
    if match:
        return match.group(1).strip()[:100]
    return ""


def infer_sport(name: str, description: str) -> str:
    text = f"{name} {description}".lower()
    for sport, aliases in SPORT_ALIASES:
        if any(alias.lower() in text for alias in aliases):
            return sport
    return "その他"


def looks_like_adult_circle(name: str, description: str) -> bool:
    text = f"{name} {description}"
    lower = text.lower()
    if not name or len(name) < 2 or len(name) > 100:
        return False
    if any(term.lower() in name.lower() for term in BAD_NAME_TERMS):
        return False
    if any(pattern.search(name) for pattern in EVENT_LIKE_NAME_PATTERNS):
        return False
    if any(term in name for term in NON_CIRCLE_NAME_TERMS):
        return False
    if app.is_invalid_circle_name(name, ""):
        return False
    if any(term in lower for term in BAD_CONTENT_TERMS):
        return False
    if any(pattern.search(text) for pattern in CHILD_ONLY_PATTERNS):
        return False
    return any(hint in text for hint in ADULT_HINTS)


def is_seed_name_acceptable(name: str) -> bool:
    return (
        bool(name)
        and not any(pattern.search(name) for pattern in EVENT_LIKE_NAME_PATTERNS)
        and not any(term in name for term in NON_CIRCLE_NAME_TERMS)
        and not any(term.lower() in name.lower() for term in BAD_NAME_TERMS)
        and "settings" not in name.lower()
        and "スポーツやろうよ" not in name
        and not app.is_invalid_circle_name(name, "")
    )


def load_seed_rows(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8", newline="") as handle:
        return list(csv.DictReader(handle))


def load_committed_seed_rows() -> list[dict[str, str]]:
    try:
        raw = subprocess.check_output(["git", "show", "HEAD:outputs/public_circles_seed.csv"], cwd=ROOT)
    except subprocess.CalledProcessError:
        return []
    return list(csv.DictReader(raw.decode("utf-8").splitlines()))


def existing_keys(rows: list[dict[str, str]]) -> tuple[set[str], set[tuple[str, str]]]:
    source_urls = {row.get("source_url", "") for row in rows if row.get("source_url")}
    names = {
        (row.get("prefecture", ""), normalize_name(row.get("circle_name", "")))
        for row in rows
        if row.get("circle_name")
    }
    return source_urls, names


def build_row(prefecture: str, source_url: str, name: str, sport: str) -> dict[str, str]:
    return {
        "university_name": f"社会人サークル（{prefecture}）",
        "prefecture": prefecture,
        "city": "",
        "campus_name": "社会人サークル",
        "official_url": "",
        "circle_name": name,
        "organization_type": "社会人サークル",
        "sport_category": sport,
        "activity_area": prefecture,
        "source_type": "public_sns",
        "source_url": source_url,
        "verification_status": "unverified",
        "public_status": "published",
        "last_checked_at": datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds"),
    }


def write_rows(rows: list[dict[str, str]]) -> None:
    rows.sort(key=lambda row: (row["prefecture"], row["circle_name"].lower(), row["source_url"]))
    with OUTPUT_PATH.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    # Check both the committed seed and the user's current worktree before
    # collecting.  The latter avoids duplicate rows during local review.
    output_rows = [
        row for row in load_seed_rows(OUTPUT_PATH)
        if is_seed_name_acceptable(row.get("circle_name", ""))
    ]
    known_rows = load_committed_seed_rows() + load_seed_rows(PUBLIC_SEED_PATH) + output_rows
    known_sources, known_names = existing_keys(known_rows)
    output_sources, _ = existing_keys(output_rows)
    added = 0
    checked = 0
    skipped: dict[str, int] = {}

    for prefecture, code in KANTO:
        if added >= TARGET_NEW_ROWS:
            break
        for page in range(1, MAX_PAGES_PER_PREFECTURE + 1):
            if added >= TARGET_NEW_ROWS:
                break
            try:
                listing_html = fetch(LIST_URL.format(code=code, page=page))
            except Exception as exc:  # Keep a failed page visible in the report.
                print(f"list_error prefecture={prefecture} page={page} error={type(exc).__name__}")
                break
            listing_ids = extract_listing_ids(listing_html)
            if not listing_ids:
                break
            for listing_id in listing_ids:
                if added >= TARGET_NEW_ROWS:
                    break
                source_url = DETAIL_URL.format(listing_id=listing_id)
                if source_url in known_sources:
                    skipped["known_source"] = skipped.get("known_source", 0) + 1
                    continue
                checked += 1
                try:
                    detail_html = fetch(source_url)
                except Exception as exc:
                    skipped[f"detail_{type(exc).__name__}"] = skipped.get(f"detail_{type(exc).__name__}", 0) + 1
                    continue
                name = extract_name(detail_html)
                description = extract_meta_description(detail_html)
                if not looks_like_adult_circle(name, description):
                    skipped["not_adult_or_noise"] = skipped.get("not_adult_or_noise", 0) + 1
                    continue
                name_key = (prefecture, normalize_name(name))
                if name_key in known_names:
                    skipped["known_name"] = skipped.get("known_name", 0) + 1
                    continue
                sport = infer_sport(name, description)
                output_rows.append(build_row(prefecture, source_url, name, sport))
                output_sources.add(source_url)
                known_sources.add(source_url)
                known_names.add(name_key)
                added += 1
                if added % 25 == 0:
                    write_rows(output_rows)
                    print(f"added={added} checked={checked} prefecture={prefecture} page={page} skipped={skipped}")
                time.sleep(REQUEST_DELAY_SECONDS)
            print(f"page_done prefecture={prefecture} page={page} added={added} checked={checked}")
            time.sleep(REQUEST_DELAY_SECONDS)

    write_rows(output_rows)
    print({"seed_rows": len(output_rows), "new_rows": added, "checked": checked, "skipped": skipped})


if __name__ == "__main__":
    main()
