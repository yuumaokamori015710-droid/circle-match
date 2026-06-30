import html
import re
import sys
import urllib.parse
import urllib.request

sys.stdout.reconfigure(encoding="utf-8")

queries = [
    'site:ac.jp "課外活動団体紹介"',
    'site:ac.jp "公認課外活動団体"',
    'site:ac.jp "クラブ・サークル活動"',
    'site:ac.jp "自治会・クラブ・サークル"',
    'site:ac.jp "体育会" "文化会" "サークル"',
    'site:ac.jp "公認団体" "体育会" "文化"',
]

for query in queries:
    print(f"\nQUERY {query}")
    url = "https://www.bing.com/search?format=rss&q=" + urllib.parse.quote(query)
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    text = urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")
    for item in re.findall(r"<item>(.*?)</item>", text, re.S):
        title = html.unescape(re.search(r"<title>(.*?)</title>", item, re.S).group(1))
        link = html.unescape(re.search(r"<link>(.*?)</link>", item, re.S).group(1))
        if ".ac.jp" in link:
            print(title[:120], link)
