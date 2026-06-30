import argparse
import json
import re
import sqlite3
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path

DB_PATH = Path("outputs/circlematch.sqlite")


KEYWORDS = [
    "クラブ",
    "サークル",
    "課外",
    "団体",
    "体育会",
    "文化会",
    "部活",
    "club",
    "circle",
    "activity",
    "campuslife",
    "student",
]


class PageParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self.links = []
        self._in_a = False
        self._href = ""
        self._text = []

    def handle_starttag(self, tag, attrs):
        if tag == "a":
            self._in_a = True
            self._href = dict(attrs).get("href", "")
            self._text = []

    def handle_endtag(self, tag):
        if tag == "a" and self._in_a:
            text = clean(" ".join(self._text))
            if text:
                self.links.append((text, self._href))
            self._in_a = False

    def handle_data(self, data):
        text = clean(data)
        if text:
            self.parts.append(text)
            if self._in_a:
                self._text.append(text)


def clean(text):
    return re.sub(r"\s+", " ", text or "").strip()


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    data = urllib.request.urlopen(req, timeout=8).read().decode("utf-8", "ignore")
    parser = PageParser()
    parser.feed(data)
    return parser


def looks_like_name(text):
    if not text or len(text) > 70 or len(text) < 2:
        return False
    if any(bad in text for bad in ["入試", "資料請求", "アクセス", "お問い合わせ", "ニュース", "一覧", "詳細", "English", "SNS"]):
        return False
    return any(word in text for word in ["部", "会", "団", "サークル", "同好", "愛好", "研究", "委員", "クラブ", "隊"])


def score_page(parser):
    names = [p for p in parser.parts if looks_like_name(p)]
    link_names = [t for t, _ in parser.links if looks_like_name(t)]
    return len(set(names + link_names))


def same_site(base, url):
    b = urllib.parse.urlparse(base)
    u = urllib.parse.urlparse(url)
    return u.netloc == b.netloc or u.netloc.endswith("." + b.netloc)


def discover_for(university_name, official_url, existing_count):
    try:
        top = fetch(official_url)
    except Exception as exc:
        return {"university": university_name, "error": str(exc), "existing": existing_count, "pages": []}

    candidates = {}
    for text, href in top.links:
        full = urllib.parse.urljoin(official_url, href)
        if not full.startswith("http") or not same_site(official_url, full):
            continue
        haystack = f"{text} {full}".lower()
        if any(k.lower() in haystack for k in KEYWORDS):
            candidates[full.split("#")[0]] = text

    # Common Japanese university URL patterns. These are intentionally shallow.
    base = official_url.rstrip("/") + "/"
    for path in [
        "campuslife/club/",
        "campuslife/activity/",
        "campus-life/club/",
        "campus-life/activity/",
        "student/club/",
        "students/club/",
        "life/club/",
        "club/",
        "circle/",
    ]:
        candidates[urllib.parse.urljoin(base, path)] = path

    pages = []
    for url, label in list(candidates.items())[:20]:
        try:
            parser = fetch(url)
            score = score_page(parser)
            if score >= 8:
                sample = list(dict.fromkeys([p for p in parser.parts if looks_like_name(p)]))[:15]
                pages.append({"url": url, "label": label, "score": score, "sample": sample})
        except Exception:
            continue
    pages.sort(key=lambda item: item["score"], reverse=True)
    return {"university": university_name, "existing": existing_count, "pages": pages[:8]}


def main():
    argp = argparse.ArgumentParser()
    argp.add_argument("--limit", type=int, default=25)
    argp.add_argument("--offset", type=int, default=0)
    args = argp.parse_args()

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        select u.university_name, u.official_url, count(c.circle_id) as existing_count
        from universities u
        left join circles c on c.university_id = u.university_id
        group by u.university_name, u.official_url
        order by existing_count asc, u.university_name
        """
    ).fetchall()
    results = []
    target_rows = [row for row in rows if row["existing_count"] < 80][args.offset : args.offset + args.limit]
    for row in target_rows:
        result = discover_for(row["university_name"], row["official_url"], row["existing_count"])
        results.append(result)
        print(json.dumps(result, ensure_ascii=False), flush=True)
    print(json.dumps(results, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
