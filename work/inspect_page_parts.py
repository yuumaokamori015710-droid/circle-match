import sys
import re
import ssl
import urllib.request
from html.parser import HTMLParser


class Parser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []
        self._skip_depth = 0

    def handle_starttag(self, tag, attrs):
        if tag in {"script", "style"}:
            self._skip_depth += 1

    def handle_endtag(self, tag):
        if tag in {"script", "style"} and self._skip_depth:
            self._skip_depth -= 1

    def handle_data(self, data):
        if self._skip_depth:
            return
        text = " ".join(data.split())
        if text:
            self.parts.append(text)


def main():
    url = sys.argv[1]
    start = int(sys.argv[2]) if len(sys.argv) > 2 else 0
    count = int(sys.argv[3]) if len(sys.argv) > 3 else 250
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
    context = ssl.create_default_context()
    try:
        context.set_ciphers("DEFAULT:@SECLEVEL=1")
    except ssl.SSLError:
        pass
    response = urllib.request.urlopen(req, timeout=30, context=context)
    raw = response.read()
    content_type = response.headers.get("content-type", "")
    charset = "utf-8"
    match = re.search(r"charset=([\w-]+)", content_type, re.I)
    if match:
        charset = match.group(1)
    else:
        head = raw[:4096].decode("ascii", "ignore")
        match = re.search(r"charset=['\"]?([\w-]+)", head, re.I)
        if match:
            charset = match.group(1)
    html = raw.decode(charset, "ignore")
    parser = Parser()
    parser.feed(html)
    for idx, text in enumerate(parser.parts[start : start + count], start):
        print(idx, repr(text))


if __name__ == "__main__":
    main()
