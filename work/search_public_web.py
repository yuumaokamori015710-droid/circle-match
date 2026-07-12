from __future__ import annotations

import html
import re
import sys
import urllib.parse
import urllib.request


def main() -> None:
    query = " ".join(sys.argv[1:]) or "東京家政大学 サークル"
    url = "https://www.bing.com/search?q=" + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    data = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")
    blocks = re.findall(r'<li class="b_algo".*?</li>', data, flags=re.S)
    for block in blocks[:10]:
        link = re.search(r'<a href="(http[^"]+)"', block)
        text = re.sub(r"<.*?>", " ", block)
        text = html.unescape(re.sub(r"\s+", " ", text)).strip()
        print((link.group(1) if link else "").strip())
        print(text[:500])
        print()


if __name__ == "__main__":
    main()
