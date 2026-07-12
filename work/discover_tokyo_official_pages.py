import json
import re
import sqlite3
import urllib.parse
import urllib.request
from html.parser import HTMLParser
from pathlib import Path


DB_PATH = Path("outputs/circlematch.sqlite")


COMMON_PATHS = [
    "campuslife/club/",
    "campuslife/clubs/",
    "campuslife/activity/",
    "campuslife/activities/",
    "campuslife/circle/",
    "campus-life/club/",
    "campus-life/clubs/",
    "campus-life/activity/",
    "campus-life/activities/",
    "campus_life/club/",
    "campus_life/activity/",
    "campus_life/activities/",
    "campus_life/circle/",
    "campus_life/circles/",
    "campus_support/campuslife/club/",
    "campus_support/campuslife/circle/",
    "campus_support/club/",
    "campus_support/circle/",
    "unv/campuslife/club/",
    "unv/campuslife/circle/",
    "unv/campuslife/activity/",
    "univ/campuslife/club/",
    "univ/campuslife/circle/",
    "univ/campuslife/activity/",
    "student_life/club/",
    "student_life/circle/",
    "student_life/activity/",
    "schoollife/club/",
    "schoollife/circle/",
    "schoollife/activity/",
    "life/activities/",
    "life/circle/",
    "student/club/",
    "student/clubs/",
    "student/activity/",
    "students/club/",
    "students/activity/",
    "life/club/",
    "life/activity/",
    "club/",
    "clubs/",
    "circle/",
    "activity/",
]


class Parser(HTMLParser):
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
    html = urllib.request.urlopen(req, timeout=6).read().decode("utf-8", "ignore")
    parser = Parser()
    parser.feed(html)
    return parser


def same_site(base, url):
    b = urllib.parse.urlparse(base)
    u = urllib.parse.urlparse(url)
    return u.netloc == b.netloc or u.netloc.endswith("." + b.netloc)


def looks_like_name(text):
    if not text or len(text) < 2 or len(text) > 70:
        return False
    bad_words = [
        "入試", "資料請求", "アクセス", "お問い合わせ", "ニュース", "詳細",
        "English", "キャンパス", "プライバシ", "Cookie", "サイト", "奨学金",
        "学生生活", "学部", "大学院", "研究", "就職", "キャリア", "留学",
    ]
    if any(word in text for word in bad_words):
        return False
    return any(word in text for word in ["部", "会", "団", "サークル", "同好", "愛好", "研究", "委員", "クラブ", "隊"])


def score(parser):
    names = list(dict.fromkeys([p for p in parser.parts if looks_like_name(p)]))
    return len(names), names[:30]


def discover(row):
    official_url = row["official_url"]
    candidates = {}
    try:
        top = fetch(official_url)
        for text, href in top.links:
            full = urllib.parse.urljoin(official_url, href)
            if not full.startswith("http") or not same_site(official_url, full):
                continue
            haystack = f"{text} {full}".lower()
            if any(key in haystack for key in ["club", "circle", "サークル", "クラブ", "課外", "団体", "部活"]):
                candidates[full.split("#")[0]] = text
    except Exception as exc:
        top_error = str(exc)
    else:
        top_error = ""

    base = official_url.rstrip("/") + "/"
    for path in COMMON_PATHS:
        candidates[urllib.parse.urljoin(base, path)] = path

    pages = []
    for url, label in candidates.items():
        try:
            parser = fetch(url)
        except Exception:
            continue
        page_score, sample = score(parser)
        if page_score >= 8:
            pages.append({"url": url, "label": label, "score": page_score, "sample": sample})
    pages.sort(key=lambda item: item["score"], reverse=True)
    return {
        "university": row["university_name"],
        "existing": row["n"],
        "official_url": official_url,
        "top_error": top_error,
        "pages": pages[:10],
    }


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        select u.university_name, u.official_url, count(c.circle_id) n
        from universities u
        left join circles c on c.university_id=u.university_id
        where u.prefecture='東京都'
        group by u.university_id
        having n <= 2
        order by n asc, u.university_name
        """
    ).fetchall()
    for row in rows:
        result = discover(row)
        print(json.dumps(result, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
