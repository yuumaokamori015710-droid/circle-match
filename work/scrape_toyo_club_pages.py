from __future__ import annotations

import html
import re
import urllib.parse
import urllib.request


BASES = [
    "https://www.toyo.ac.jp/club/hakusan/",
    "https://www.toyo.ac.jp/club/kawagoe/",
    "https://www.toyo.ac.jp/club/asaka/",
    "https://www.toyo.ac.jp/club/akabanedai1/",
    "https://www.toyo.ac.jp/club/akabanedai2/",
]


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    return urllib.request.urlopen(req, timeout=20).read().decode("utf-8", "ignore")


def text_lines(url: str) -> list[str]:
    body = fetch(url)
    text = re.sub(r"<(script|style).*?</\1>", " ", body, flags=re.S | re.I)
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.I)
    text = re.sub(r"</(div|p|li|h[1-6]|span|a)>", "\n", text, flags=re.I)
    text = re.sub(r"<.*?>", " ", text)
    lines = []
    for line in text.splitlines():
        cleaned = html.unescape(re.sub(r"\s+", " ", line)).strip()
        if cleaned:
            lines.append(cleaned)
    return lines


def links(url: str) -> list[str]:
    body = fetch(url)
    hrefs = re.findall(r"<a[^>]+href=[\"']([^\"']+)", body, flags=re.I)
    return [urllib.parse.urljoin(url, html.unescape(href)) for href in hrefs]


def extract_names(url: str) -> list[str]:
    lines = text_lines(url)
    names = []
    skip = {
        "詳しく見る", "トップ", "MENU", "2026年度", "東洋大学サークル紹介サイト",
        "白山キャンパス", "川越キャンパス", "朝霞キャンパス", "赤羽台キャンパス",
        "（WELLB・HELSPO）", "（INIAD）", "よくある質問", "当サイト全体に関するお問合せ",
        "Copyright© 2026 東洋大学サークル紹介サイト", "All Rights Reserved.", "managed by", "RCMS",
    }
    campus_labels = {"白山キャンパス", "川越キャンパス", "朝霞キャンパス", "赤羽台キャンパス"}
    for index, line in enumerate(lines):
        if line in skip or line.startswith("・") or line.startswith("Copyright"):
            continue
        if re.search(r"\d+件中|^[0-9]+$|^[>»]$", line):
            continue
        if line.endswith("内検索") or line in ["運動部", "サークル", "本部団体"]:
            continue
        prev = lines[index - 1] if index else ""
        nxt = lines[index + 1] if index + 1 < len(lines) else ""
        if prev in campus_labels or nxt.startswith("・") or nxt == "詳しく見る":
            names.append(line)
    return list(dict.fromkeys(names))


def main() -> None:
    all_urls = set()
    for base in BASES:
        for href in links(base):
            if href.startswith(base) and any(part in href for part in ["/club/", "/circle/"]):
                all_urls.add(href.split("#")[0])
        all_urls.add(base + "club/")
        all_urls.add(base + "circle/")
    for url in sorted(all_urls):
        try:
            names = extract_names(url)
        except Exception as exc:
            print("ERR", url, exc)
            continue
        if names:
            print("URL", url)
            for name in names:
                print(name)
            print()


if __name__ == "__main__":
    main()
