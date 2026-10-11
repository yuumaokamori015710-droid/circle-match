"""Resumable, private research of public club contact details. Never sends mail.

Run with --directory outside the git checkout. The SQLite cache and JSON/CSV
contain contact data and must not be published as a public seed.
Optional lxml and pypdf improve HTML/PDF parsing; no hosted paid API is used.
"""
import argparse
import concurrent.futures
import csv
import hashlib
import io
import ipaddress
import json
import re
import socket
import sqlite3
import sys
import threading
import time
import unicodedata
from functools import lru_cache
from collections import Counter, defaultdict, deque
from datetime import datetime, timezone
from pathlib import Path
from urllib import error, parse, request, robotparser

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'outputs'))
import circlematch_contact_research as contact_store

try:
    from lxml import html as dom
except ImportError:
    dom = None

EMAIL = re.compile(r"[A-Za-z0-9.!#$%&'*+/=?^_`{|}~-]{1,64}@[A-Za-z0-9](?:[A-Za-z0-9.-]{0,251}[A-Za-z0-9])?\.[A-Za-z]{2,24}")
UA = 'CircleMatchContactResearch/1.0 (+https://circle-match.onrender.com/about-data)'
MAX_BYTES = 8 * 1024 * 1024
SOCIAL = {'x.com', 'twitter.com', 'instagram.com', 'facebook.com', 'youtube.com', 'youtu.be', 't.co', 'line.me', 'lin.ee'}
SKIP_EXT = ('.jpg', '.jpeg', '.png', '.gif', '.svg', '.zip', '.mp4', '.xlsx', '.docx', '.css', '.js')


def now():
    return datetime.now(timezone.utc).isoformat(timespec='seconds')


@lru_cache(maxsize=32768)
def norm(value):
    return re.sub(r'[\s\W_]+', '', unicodedata.normalize('NFKC', value or '')).casefold()


def clean(value):
    return re.sub(r'\s+', ' ', re.sub(r'[\x00-\x1f\x7f]', ' ', value or '')).strip()


def safe_url(value, resolve=False):
    try:
        u = parse.urlsplit(value)
        if u.scheme not in {'http', 'https'} or not u.hostname or u.username or u.password or u.port not in {None, 80, 443}:
            return ''
        host = u.hostname.lower()
        if host in {'localhost', 'metadata.google.internal'} or host.endswith(('.local', '.internal', '.localhost')):
            return ''
        try:
            if not ipaddress.ip_address(host).is_global:
                return ''
        except ValueError:
            pass
        if resolve:
            addresses = socket.getaddrinfo(host, u.port or (443 if u.scheme == 'https' else 80), type=socket.SOCK_STREAM)
            if not addresses or any(not ipaddress.ip_address(x[4][0]).is_global for x in addresses):
                return ''
        path = parse.quote(u.path or '/', safe="/%:@!$&'()*+,;=-._~")
        query = parse.quote(u.query, safe="%=&?/:@!$'()*+,;~-._")
        return parse.urlunsplit((u.scheme, u.netloc, path, query, ''))
    except (ValueError, OSError):
        return ''


def is_social(url):
    host = (parse.urlsplit(url).hostname or '').lower()
    return any(host == h or host.endswith('.' + h) for h in SOCIAL)


class CheckedRedirect(request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        if not safe_url(newurl, resolve=True):
            raise ValueError('unsafe redirect')
        return super().redirect_request(req, fp, code, msg, headers, newurl)


class Fetcher:
    def __init__(self, path, delay=1.0):
        self.path = path
        self.delay = delay
        self.lock = threading.Lock()
        self.host_locks = defaultdict(threading.Lock)
        self.last = {}
        self.robots = {}
        self.opener = request.build_opener(CheckedRedirect())
        with self.db() as c:
            c.execute('create table if not exists pages(url text primary key, final_url text, status text, body blob, kind text, checked_at text)')

    def db(self):
        return sqlite3.connect(self.path, timeout=60)

    def fetch(self, url):
        url = safe_url(url)
        if not url:
            return {'url': '', 'status': 'unsafe_url', 'body': b'', 'kind': ''}
        with self.db() as c:
            row = c.execute('select final_url,status,body,kind,checked_at from pages where url=?', (url,)).fetchone()
        if row:
            return dict(zip(('url', 'status', 'body', 'kind', 'checked_at'), row))
        host = parse.urlsplit(url).netloc.lower()
        with self.host_locks[host]:
            # Another worker may have fetched this shared URL while we waited.
            with self.db() as c:
                row = c.execute('select final_url,status,body,kind,checked_at from pages where url=?', (url,)).fetchone()
            if row:
                return dict(zip(('url', 'status', 'body', 'kind', 'checked_at'), row))
            out = {'url': url, 'status': 'fetch_error', 'body': b'', 'kind': '', 'checked_at': now()}
            try:
                if not safe_url(url, resolve=True):
                    raise ValueError('unsafe or unresolved host')
                if is_social(url):
                    out['status'] = 'social_not_accessed'
                else:
                    base = parse.urlsplit(url)
                    origin = base.scheme + '://' + base.netloc
                    if origin not in self.robots:
                        rp = robotparser.RobotFileParser()
                        try:
                            req = request.Request(origin + '/robots.txt', headers={'User-Agent': UA})
                            with self.opener.open(req, timeout=12) as res:
                                rp.parse(res.read(256000).decode('utf-8', 'replace').splitlines())
                        except error.HTTPError as exc:
                            if exc.code in {401, 403, 429}:
                                rp.parse(['User-agent: *', 'Disallow: /'])
                            else:
                                rp.parse([])
                        except Exception:
                            rp.parse([])
                        self.robots[origin] = rp
                    rp = self.robots[origin]
                    if not rp.can_fetch(UA, url):
                        out['status'] = 'robots_blocked'
                    else:
                        pause = max(self.delay, rp.crawl_delay(UA) or rp.crawl_delay('*') or 0)
                        time.sleep(max(0, pause - (time.monotonic() - self.last.get(host, 0))))
                        self.last[host] = time.monotonic()
                        req = request.Request(url, headers={'User-Agent': UA, 'Accept': 'text/html,application/pdf;q=0.8'})
                        with self.opener.open(req, timeout=20) as res:
                            content = res.read(MAX_BYTES + 1)
                            if len(content) > MAX_BYTES:
                                out['status'] = 'too_large'
                            else:
                                out.update(url=res.url, body=content, kind=res.headers.get('Content-Type', ''), status='ok')
            except error.HTTPError as exc:
                out['status'] = 'http_' + str(exc.code)
            except Exception as exc:
                out['status'] = type(exc).__name__
            with self.db() as c:
                c.execute('insert or replace into pages values(?,?,?,?,?,?)', (url, out['url'], out['status'], out['body'], out['kind'], out['checked_at']))
            return out

    @lru_cache(maxsize=128)
    def parsed(self, url):
        return parse_page(self.fetch(url))


def decoded_text(data, kind=''):
    encodings = re.findall(r'charset=["\s\x27]*([\w-]+)', kind + ' ' + data[:1500].decode('ascii', 'ignore'))
    for enc in encodings + ['utf-8', 'cp932', 'euc-jp']:
        try:
            return data.decode(enc)
        except (LookupError, UnicodeDecodeError):
            continue
    return data.decode('utf-8', 'replace')


def parse_page(page):
    if page['status'] != 'ok':
        return None
    if 'pdf' in page['kind'].lower() or page['body'].startswith(b'%PDF'):
        try:
            from pypdf import PdfReader
            reader = PdfReader(io.BytesIO(page['body']))
            return {'text': '\n'.join((p.extract_text() or '') for p in list(reader.pages)[:200]), 'tree': None, 'links': [], 'pdf': True}
        except Exception:
            return None
    if dom is None:
        raise RuntimeError('Install lxml in the local research runtime to parse HTML')
    try:
        tree = dom.fromstring(decoded_text(page['body'], page['kind']))
        for bad in tree.xpath('//script|//style|//noscript|//template'):
            bad.drop_tree()
        links = [(safe_url(parse.urljoin(page['url'], a.get('href', ''))), clean(a.text_content()), a) for a in tree.xpath('//a[@href]')]
        email_nodes = []
        for node in tree.iter():
            direct = ' '.join([node.text or ''] + [child.tail or '' for child in node])
            if node.tag == 'a' and (node.get('href') or '').lower().startswith('mailto:'):
                direct += ' ' + parse.unquote(node.get('href')[7:].split('?')[0])
            direct = unicodedata.normalize('NFKC', direct)
            direct = re.sub(r'(?:\[at\]|\(at\)|【at】|＠)', '@', direct, flags=re.I)
            direct = re.sub(r'([A-Za-z0-9._%+-])\s*@\s*([A-Za-z0-9])', r'\1@\2', direct)
            mails = EMAIL.findall(direct)
            if mails:
                email_nodes.append((node, mails))
        return {'tree': tree, 'text': tree.text_content(), 'links': links, 'pdf': False, 'email_nodes': email_nodes}
    except Exception:
        return None


def names_match(name, text):
    n, t = norm(name), norm(text)
    return len(n) >= 3 and n in t


def extract_contacts(circle, page, parsed, peer_names):
    """Require a bounded DOM context explicitly naming exactly one club.

    Unattributed site footer, university office and other clubs are not contacts.
    Obfuscated emails are decoded only for common explicitly written separators.
    """
    name = circle['circle_name']
    found, candidates = [], []
    if not parsed:
        return found, candidates
    blocks = []
    if parsed['tree'] is not None:
        tree = parsed['tree']
        for node, mails in parsed['email_nodes']:
            for address in mails:
                context_node = node
                evidence = ''
                for _ in range(5):
                    text = clean(context_node.text_content())
                    if len(text) > 1600:
                        break
                    named_text = EMAIL.sub('', text)
                    if re.search(r'学生課|学生支援課|教務課|広報課|入試課|情報システム|学生生活課|サイト管理', named_text):
                        break
                    if names_match(name, named_text):
                        others = [n for n in peer_names if norm(n) != norm(name) and len(norm(n)) >= 4 and names_match(n, text)]
                        # Broad enclosing containers may mention many clubs; don't guess.
                        if not others:
                            evidence = text[:1600]
                            break
                    context_node = context_node.getparent()
                    if context_node is None or context_node.tag in {'body', 'html', 'footer', 'nav'}:
                        break
                if evidence:
                    blocks.append((address, evidence))
                else:
                    candidates.append(address)
    else:
        lines = parsed['text'].splitlines()
        for index, line in enumerate(lines):
            if not EMAIL.search(line):
                continue
            context = ' '.join(lines[max(0, index - 2):index + 2])
            other = [n for n in peer_names if norm(n) != norm(name) and len(norm(n)) >= 4 and names_match(n, context)]
            if len(context) <= 1600 and names_match(name, EMAIL.sub('', context)) and not other:
                blocks.extend((m, context) for m in EMAIL.findall(line))
            else:
                candidates.extend(EMAIL.findall(line))
    for address, evidence in blocks:
        address = address.rstrip('.,;:')
        if address.lower().endswith(('.png', '.jpg', '.gif', '.webp')) or address.lower().startswith(('example@', 'test@', 'noreply@', 'no-reply@')):
            continue
        if any(x['email'].lower() == address.lower() for x in found):
            continue
        found.append({'email': address, 'source_url': page['url'], 'evidence': evidence, 'attribution': 'club_context'})
    return found, sorted(set(candidates))


def next_links(circle, parsed, base, dedicated=False):
    links, forms = [], []
    if not parsed:
        return links, forms
    base_host = (parse.urlsplit(base).hostname or '').removeprefix('www.')
    aggregator = base_host in {'circle-book.com', 'net-menber.com'}
    initial_path = parse.urlsplit(circle.get('source_url', '')).path.rstrip('/')
    for url, label, node in parsed['links']:
        if not url or url.lower().split('?')[0].endswith(SKIP_EXT) or is_social(url):
            continue
        if node is not None:
            ancestors = [node] + list(node.iterancestors())
            if any(n.tag in {'header', 'footer', 'nav', 'aside'} or re.search(r'footer|header|recommend|related|sidebar|ranking', (n.get('class') or '') + ' ' + (n.get('id') or ''), re.I) for n in ancestors):
                continue
        target_host = (parse.urlsplit(url).hostname or '').removeprefix('www.')
        target_path = parse.urlsplit(url).path.rstrip('/')
        if aggregator:
            # Listing recommendations often repeat the same generic club name.
            # Never navigate to another aggregator profile or private messaging.
            if target_host in {'circle-book.com', 'net-menber.com'}:
                if target_host != base_host or target_path != initial_path:
                    continue
        exact = norm(label) == norm(circle['circle_name']) or (names_match(circle['circle_name'], label) and len(norm(label)) <= len(norm(circle['circle_name'])) + 12)
        contact = bool(re.search(r'contact|問い合わせ|問合せ|連絡|メール|公式サイト|ホームページ|website|公式HP', label + ' ' + url, re.I))
        same_host = parse.urlsplit(url).hostname == parse.urlsplit(base).hostname
        contextual = False
        if node is not None:
            parent = node.getparent()
            if parent is not None:
                text = clean(parent.text_content())
                contextual = len(text) < 600 and names_match(circle['circle_name'], text)
        # A generic university /contact or aggregator /help is not a club form.
        official_link = bool(re.search(r'公式サイト|ホームページ|website|公式HP', label, re.I))
        club_contact = contact and contextual and (same_host or aggregator or official_link)
        if exact or club_contact:
            links.append(url)
            if club_contact and re.search(r'form|問い合わせ|問合せ', label + url, re.I) and not re.search(r'/other/|/help|/info-contact/?$', target_path):
                forms.append(url)
    return list(dict.fromkeys(links))[:5], list(dict.fromkeys(forms))


def research_one(circle, fetcher, peers):
    initial = safe_url(circle.get('source_url', ''))
    out = {'circle_id': circle['circle_id'], 'status': 'source_missing', 'checked_at': now(), 'sources': [], 'contacts': [], 'note': '', 'contact_form_url': ''}
    if not initial:
        out['note'] = '登録された出典URLがありません。追加の公開情報調査が必要です。'
        return out
    pending, seen, candidates, failures = [initial], set(), [], []
    while pending and len(seen) < 6:
        url = pending.pop(0)
        if url in seen:
            continue
        seen.add(url)
        page = fetcher.fetch(url)
        out['sources'].append({'url': url, 'evidence': page['status']})
        if page['status'] != 'ok':
            failures.append(page['status'])
            continue
        parsed = fetcher.parsed(url)
        if not parsed:
            failures.append('parse_error')
            continue
        emails, uncertain = extract_contacts(circle, page, parsed, peers)
        out['contacts'].extend(emails)
        candidates.extend(uncertain)
        dedicated = url != initial
        if parsed['tree'] is not None:
            headings = ' '.join(parsed['tree'].xpath('//title/text()|//h1//text()'))
            dedicated = dedicated or names_match(circle['circle_name'], headings)
        follow, forms = next_links(circle, parsed, page['url'], dedicated)
        if forms:
            out['contact_form_url'] = forms[0]
        if not out['contacts']:
            pending.extend(x for x in follow if x not in seen)
        else:
            break
    out['contacts'] = list({x['email'].lower(): x for x in out['contacts']}.values())
    if out['contacts']:
        out['status'] = 'email_found'
        out['note'] = '公開ページの団体名を含む連絡先欄で対応を確認。送信・配信同意は未確認。'
    elif out['contact_form_url']:
        out['status'] = 'contact_form'
        out['note'] = 'メール未取得。問い合わせページ候補あり。'
    elif candidates:
        out['status'] = 'review_needed'
        out['note'] = 'ページ内にメールはありますが団体との対応を確認できません。手動確認が必要。'
    elif failures:
        out['status'] = 'blocked'
        out['note'] = '一部または全部のページを確認できません: ' + ','.join(sorted(set(failures)))
    else:
        out['status'] = 'no_email'
        out['note'] = '登録出典と団体リンクを確認した範囲では公開メール未発見。ウェブ全体で非公開と断定するものではありません。'
    return out


def inventory(base, directory):
    path = directory / 'circles.json'
    if path.exists():
        return json.loads(path.read_text(encoding='utf-8'))
    rows = []
    for offset in range(0, 1000000, 200):
        url = base.rstrip('/') + '/api/circles?' + parse.urlencode({'audience': 'all', 'limit': 200, 'offset': offset, 'sort': 'circle'})
        with request.urlopen(request.Request(url, headers={'User-Agent': UA}), timeout=40) as res:
            batch = json.load(res)
        rows.extend(batch)
        if len(batch) < 200:
            break
    if len({x['circle_id'] for x in rows}) != len(rows):
        raise RuntimeError('Inventory changed during pagination; retry snapshot')
    path.write_text(json.dumps(rows, ensure_ascii=False), encoding='utf-8')
    return rows


def export(directory, circles, results):
    ordered = [results[x['circle_id']] for x in circles if x['circle_id'] in results]
    # Recheck persisted rows too, so a resumed research run applies stricter
    # attribution to previously saved results without re-downloading sources.
    for row in ordered:
        usable = []
        for contact in row['contacts']:
            contact['evidence'] = clean(contact['evidence'])
            try:
                contact['email'] = contact_store.contact_email(contact['email'])
                contact['source_url'] = contact_store.public_url(contact['source_url'], True)
            except ValueError:
                continue
            if not re.search(r'学生課|学生支援課|教務課|広報課|入試課|情報システム|学生生活課|サイト管理', contact['evidence']):
                usable.append(contact)
        if len(usable) < len(row['contacts']):
            row['contacts'] = usable
            if not usable:
                row['status'] = 'review_needed'
                row['note'] = '大学の共通窓口、または形式不正の可能性があるため団体メールとして自動採用しません。'
    # A single shared email used by unrelated clubs may be a university office.
    by_mail = defaultdict(list)
    for row in ordered:
        for item in row['contacts']:
            by_mail[item['email'].lower()].append(row)
    shared = {m for m, rows in by_mail.items() if len({r['circle_id'] for r in rows}) > 1}
    for row in ordered:
        if any(x['email'].lower() in shared for x in row['contacts']):
            row = dict(row)
            row['contacts'] = [x for x in row['contacts'] if x['email'].lower() not in shared]
            if not row['contacts']:
                row['status'] = 'review_needed'
                row['note'] = '複数団体に同じメールが現れたため窓口共有か要確認。自動採用しません。'
            results[row['circle_id']] = row
    ordered = [results[x['circle_id']] for x in circles if x['circle_id'] in results]
    payload = {'job_id': directory.name, 'results': ordered}
    (directory / 'results.json').write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding='utf-8')
    with (directory / 'contacts.csv').open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.writer(f)
        writer.writerow(['circle_id', 'university', 'circle', 'status', 'email', 'source_url', 'checked_at', 'note'])
        for circle in circles:
            row = results.get(circle['circle_id'])
            if not row:
                writer.writerow([csv_cell(x) for x in [circle['circle_id'], circle['university_name'], circle['circle_name'], 'pending', '', '', '', '']])
            else:
                for email in row['contacts'] or [{}]:
                    writer.writerow([csv_cell(x) for x in [circle['circle_id'], circle['university_name'], circle['circle_name'], row['status'], email.get('email', ''), email.get('source_url', circle.get('source_url', '')), row['checked_at'], row['note']]])
    stats = {'total': len(circles), 'researched': len(ordered), 'pending': len(circles) - len(ordered), 'statuses': dict(Counter(r['status'] for r in ordered)), 'updated_at': now()}
    (directory / 'progress.json').write_text(json.dumps(stats, ensure_ascii=False, indent=2), encoding='utf-8')
    return stats


def csv_cell(value):
    value = str(value or '')
    return "'" + value if value.lstrip().startswith(('=', '+', '-', '@')) or value.startswith(('\t', '\r', '\n')) else value


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--directory', type=Path, required=True)
    p.add_argument('--base-url', default='https://circle-match.onrender.com')
    p.add_argument('--workers', type=int, default=12)
    p.add_argument('--limit', type=int, default=0)
    args = p.parse_args()
    directory = args.directory.resolve()
    directory.mkdir(parents=True, exist_ok=True)
    circles = inventory(args.base_url, directory)
    results = {}
    journal = directory / 'results.jsonl'
    if journal.exists():
        for line in journal.read_text(encoding='utf-8').splitlines():
            try:
                row = json.loads(line)
                results[row['circle_id']] = row
            except json.JSONDecodeError:
                continue
    peers = defaultdict(list)
    for circle in circles:
        peers[circle['university_id']].append(circle['circle_name'])
    todo = [x for x in circles if x['circle_id'] not in results]
    # Mix source hosts so a long queue for one listing site cannot occupy all
    # workers while unrelated university pages wait behind it.
    groups = defaultdict(deque)
    for circle in todo:
        groups[parse.urlsplit(circle.get('source_url', '')).netloc].append(circle)
    todo = []
    while groups:
        for host in list(groups):
            todo.append(groups[host].popleft())
            if not groups[host]:
                del groups[host]
    if args.limit:
        todo = todo[:args.limit]
    print(json.dumps({'total': len(circles), 'todo': len(todo), 'unique_source_urls': len({x['source_url'] for x in circles})}), flush=True)
    fetcher = Fetcher(directory / 'pages.sqlite')
    with journal.open('a', encoding='utf-8') as out, concurrent.futures.ThreadPoolExecutor(max_workers=max(1, min(args.workers, 20))) as pool:
        tasks = {pool.submit(research_one, c, fetcher, peers[c['university_id']]): c for c in todo}
        last_print = time.monotonic()
        for task in concurrent.futures.as_completed(tasks):
            circle = tasks[task]
            try:
                row = task.result()
            except Exception as exc:
                row = {'circle_id': circle['circle_id'], 'status': 'blocked', 'checked_at': now(), 'sources': [], 'contacts': [], 'note': '研究処理エラー: ' + type(exc).__name__, 'contact_form_url': ''}
            results[row['circle_id']] = row
            out.write(json.dumps(row, ensure_ascii=False) + '\n')
            out.flush()
            if time.monotonic() - last_print >= 20:
                print(json.dumps(export(directory, circles, results), ensure_ascii=False), flush=True)
                last_print = time.monotonic()
    print(json.dumps(export(directory, circles, results), ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
