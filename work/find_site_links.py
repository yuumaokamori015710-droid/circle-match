from __future__ import annotations

import html
import re
import sys
import urllib.parse
import urllib.request


KEYWORDS = [
    "学生",
    "課外",
    "サークル",
    "クラブ",
    "団体",
    "部活",
    "campus",
    "student",
    "club",
    "circle",
]


def main() -> None:
    url = sys.argv[1]
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    data = urllib.request.urlopen(req, timeout=20).read()
    text = data.decode("utf-8", "ignore") or data.decode("cp932", "ignore")
    print("URL", url)
    print("bytes", len(data), "chars", len(text))
    for keyword in KEYWORDS:
        print("find", keyword, text.find(keyword))
    for match in re.finditer(r"<a[^>]+href=[\"']([^\"']+)[\"'][^>]*>(.*?)</a>", text, re.S | re.I):
        href = urllib.parse.urljoin(url, html.unescape(match.group(1)))
        label = re.sub("<.*?>", " ", match.group(2))
        label = html.unescape(re.sub(r"\s+", " ", label)).strip()
        haystack = f"{label} {href}".lower()
        if any(keyword.lower() in haystack for keyword in KEYWORDS):
            print(label, href)


if __name__ == "__main__":
    main()
