import json
import re
import sqlite3
import ssl
import sys
import urllib.parse
import urllib.request
from collections import deque
from html.parser import HTMLParser
from pathlib import Path


DB_PATH = Path(__file__).resolve().parents[1] / "outputs" / "circlematch.sqlite"

KEYWORDS = [
    "公認サークル", "サークル", "クラブ", "課外活動", "学生団体", "部活動",
    "同好会", "学友会", "自治会", "委員会", "文化会", "体育会",
]
BAD_KEYWORDS = [
    "説明会", "講演会", "入試", "入園", "高校", "中学校", "幼稚園", "採用",
    "研究活動", "公開講座", "受験生", "保護者", "寄付",
]


class Parser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links = []
        self.parts = []
        self._href = None
        self._skip = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self._skip += 1
        if tag == "a":
            self._href = dict(attrs).get("href")

    def handle_endtag(self, tag):
        if tag in {"script", "style"} and self._skip:
            self._skip -= 1
        if tag == "a":
            self._href = None

    def handle_data(self, data):
        if self._skip:
            return
        text = " ".join(data.split())
        if not text:
            return
        self.parts.append(text)
        if self._href:
            self.links.append((text, self._href))


def opener():
    context = ssl.create_default_context()
    try:
        context.set_ciphers("DEFAULT:@SECLEVEL=1")
    except ssl.SSLError:
        pass
    return context


def decode(raw, headers):
    content_type = headers.get("content-type", "")
    charset = "utf-8"
    match = re.search(r"charset=([\w-]+)", content_type, re.I)
    if match:
        charset = match.group(1)
    else:
        head = raw[:4096].decode("ascii", "ignore")
        match = re.search(r"charset=['\"]?([\w-]+)", head, re.I)
        if match:
            charset = match.group(1)
    return raw.decode(charset, "ignore")


def fetch(url, context):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    with urllib.request.urlopen(req, timeout=12, context=context) as response:
        raw = response.read(900_000)
        return decode(raw, response.headers), response.geturl()


def same_site(url, root):
    parsed = urllib.parse.urlparse(url)
    base = urllib.parse.urlparse(root)
    return parsed.netloc == base.netloc and parsed.scheme in {"http", "https"}


def score(parts):
    text = "\n".join(parts[:500])
    keyword_score = sum(text.count(word) for word in KEYWORDS)
    bad_score = sum(text.count(word) for word in BAD_KEYWORDS)
    # Pages that actually list many short items are more likely to be usable.
    short_items = sum(1 for part in parts if 2 <= len(part) <= 35 and any(k in part for k in KEYWORDS))
    return keyword_score * 3 + short_items - bad_score * 2


def crawl(root, max_pages=260):
    context = opener()
    seen = set()
    queue = deque([(root, 0)])
    candidates = []
    while queue and len(seen) < max_pages:
        url, depth = queue.popleft()
        url = urllib.parse.urldefrag(url)[0]
        if url in seen or not same_site(url, root):
            continue
        seen.add(url)
        try:
            html, final_url = fetch(url, context)
        except Exception as exc:
            continue
        parser = Parser()
        parser.feed(html)
        page_score = score(parser.parts)
        if page_score >= 8:
            candidates.append({
                "url": final_url,
                "score": page_score,
                "sample": [p for p in parser.parts if any(k in p for k in KEYWORDS)][:30],
            })
        if depth >= 4:
            continue
        for text, href in parser.links:
            full = urllib.parse.urljoin(final_url, href)
            link_text = text + " " + href
            if any(k in link_text for k in KEYWORDS) or any(k in full for k in ["club", "circle", "activity", "campuslife", "student"]):
                queue.append((full, depth + 1))
    candidates.sort(key=lambda item: item["score"], reverse=True)
    return candidates[:10]


def targets():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        select u.university_name, u.official_url
        from universities u
        left join circles c on c.university_id=u.university_id and c.public_status='published'
        where u.prefecture='東京都'
        group by u.university_id
        having count(c.circle_id)=0
        order by u.university_name
        """
    )
    return [dict(row) for row in rows]


def main():
    names = set(sys.argv[1:])
    for target in targets():
        if names and target["university_name"] not in names:
            continue
        print(json.dumps({
            "university": target["university_name"],
            "official_url": target["official_url"],
            "candidates": crawl(target["official_url"]),
        }, ensure_ascii=False))


if __name__ == "__main__":
    main()
