import json
import re
import sqlite3
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from pathlib import Path


DB_PATH = Path("outputs/circlematch.sqlite")


NEEDLES = [
    "club", "circle", "activity", "activities", "campuslife", "campus-life",
    "サークル", "クラブ", "課外", "団体", "部活",
]


def fetch_text(url):
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=10).read().decode("utf-8", "ignore")


def sitemap_urls(base_url):
    parsed = urllib.parse.urlparse(base_url)
    root = f"{parsed.scheme}://{parsed.netloc}/"
    candidates = [urllib.parse.urljoin(root, "sitemap.xml")]
    found = []
    seen = set()
    for sitemap in candidates:
        if sitemap in seen:
            continue
        seen.add(sitemap)
        try:
            text = fetch_text(sitemap)
        except Exception as exc:
            found.append({"sitemap": sitemap, "error": str(exc), "urls": []})
            continue
        urls = re.findall(r"<loc>(.*?)</loc>", text)
        child_maps = [u for u in urls if u.endswith(".xml") and len(candidates) < 25]
        candidates.extend(child_maps[:20])
        hits = [u for u in urls if any(n.lower() in u.lower() for n in NEEDLES)]
        if hits:
            found.append({"sitemap": sitemap, "urls": hits[:80]})
    return found


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
        having n = 0
        order by u.university_name
        """
    ).fetchall()
    for row in rows:
        print(json.dumps({
            "university": row["university_name"],
            "official_url": row["official_url"],
            "sitemaps": sitemap_urls(row["official_url"]),
        }, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    main()
