from __future__ import annotations

import re
import sys
import urllib.parse
import urllib.request


def main() -> None:
    url = sys.argv[1]
    html = urllib.request.urlopen(
        urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"}),
        timeout=20,
    ).read().decode("utf-8", "ignore")
    for pattern in ["api", "json", "contents", "module", "rcms", "group", "search", "topics", "member"]:
        print("---", pattern)
        match = re.search(pattern, html, re.I)
        if match:
            print(html[max(0, match.start() - 400): match.start() + 800].replace("\n", " ")[:1400])
    print("--- scripts")
    for src in re.findall(r"<script[^>]+src=[\"']([^\"']+)", html, re.I):
        print(urllib.parse.urljoin(url, src))
    print("--- links")
    for href in re.findall(r"<a[^>]+href=[\"']([^\"']+)", html, re.I):
        if any(key in href.lower() for key in ["api", "json", "search", "club", "topics", "member"]):
            print(urllib.parse.urljoin(url, href))


if __name__ == "__main__":
    main()
