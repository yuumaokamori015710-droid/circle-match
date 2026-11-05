"""Public-response caching and bounded, credential-free delivery diagnostics."""
from collections import defaultdict, OrderedDict
import hashlib
import ipaddress
import json
import os
import threading
import time
from urllib.parse import urlsplit


def etag(body):
    return '"' + hashlib.sha256(body).hexdigest() + '"'


def unchanged(header, tag):
    return any(value.strip().removeprefix('W/') in {tag, '*'} for value in header.split(','))


def route_group(path):
    path = urlsplit(path).path
    if path.startswith('/assets/'):
        extension = path.rsplit('.', 1)[-1]
        return '/assets/' + (extension if extension in {'css', 'js', 'json', 'png', 'webp', 'svg', 'woff2'} else 'other')
    if path in {'/', '/venues', '/api/venues', '/api/tennis-courts', '/healthz',
                '/api/circles', '/api/circle-stats', '/api/region-counts',
                '/api/events', '/robots.txt', '/sitemap.xml', '/ads.txt'}:
        return path
    if path.startswith('/events/'):
        return '/events/:event'
    if path.startswith('/api/'):
        return '/api/other'
    return '/other'


def client_group(user_agent):
    agent = user_agent.lower()
    if 'circlematch-access-check' in agent:
        return 'release-check'
    if any(word in agent for word in ('circlematchcontactresearch', 'circlematchdatabot', 'circlematchbot')):
        return 'research'
    if any(word in agent for word in ('render/', 'render-health', 'go-http-client')):
        return 'health-or-go-client'
    if any(word in agent for word in ('bot', 'crawler', 'spider')):
        return 'crawler'
    if any(word in agent for word in ('python', 'curl', 'wget', 'node', 'undici', 'codex')):
        return 'script'
    return 'browser' if 'mozilla/' in agent else 'other'


class DeliveryStats:
    def __init__(self, interval=60, clock=time.monotonic, emit=None):
        self.interval, self.clock = interval, clock
        self.emit = emit or (lambda value: print(json.dumps(value, separators=(',', ':')), flush=True))
        self.lock = threading.Lock()
        self.since = clock()
        self.rows = defaultdict(lambda: [0, 0])

    def record(self, path, status, size, user_agent):
        with self.lock:
            key = (route_group(path), int(status), client_group(user_agent))
            self.rows[key][0] += 1
            self.rows[key][1] += max(0, int(size))
            if self.clock() - self.since < self.interval:
                return
            report = {'type': 'delivery_summary', 'seconds': round(self.clock() - self.since),
                      'rows': [{'route': key[0], 'status': key[1], 'client': key[2],
                                'requests': value[0], 'body_bytes': value[1]}
                               for key, value in sorted(self.rows.items())]}
            self.rows.clear()
            self.since = self.clock()
        # Diagnostics must never interrupt a login, application or webhook.
        try:
            self.emit(report)
        except Exception:
            pass


class CatalogLimiter:
    """Only public catalog GETs are limited; no account or payment routes enter here."""
    def __init__(self, clock=time.monotonic, capacity=4096):
        self.clock, self.capacity = clock, capacity
        self.lock = threading.Lock()
        self.clients = OrderedDict()

    def allow(self, address, paginated):
        now = self.clock()
        with self.lock:
            key = (address, bool(paginated))
            tokens, updated = self.clients.pop(key, (240 if paginated else 30, now))
            limit = 240 if paginated else 30
            tokens = min(limit, tokens + (now - updated) * limit / 60)
            allowed = tokens >= 1
            self.clients[key] = (tokens - int(allowed), now)
            while len(self.clients) > self.capacity:
                self.clients.popitem(last=False)
            return allowed


def client_address(peer, forwarded='', on_render=False, connecting_ip=''):
    # Public Render traffic traverses Cloudflare. Its overwritten client header
    # avoids grouping unrelated users under a shared proxy address. If proxy
    # provenance is ambiguous, fail open instead of limiting the whole site.
    if on_render:
        candidate = connecting_ip or (forwarded.strip() if ',' not in forwarded else '')
        if not candidate:
            return None
    else:
        candidate = peer
    try:
        return str(ipaddress.ip_address(candidate))
    except ValueError:
        return None


class _MeteredWriter:
    def __init__(self, writer, handler):
        self.writer, self.handler = writer, handler

    def write(self, value):
        result = self.writer.write(value)
        if getattr(self.handler, '_delivery_body', False):
            self.handler._delivery_bytes += len(value) if result is None else result
        return result

    def __getattr__(self, name):
        return getattr(self.writer, name)


STATS = DeliveryStats()
LIMITER = CatalogLimiter()


class DeliveryMixin:
    def setup(self):
        super().setup()
        self.wfile = _MeteredWriter(self.wfile, self)

    def handle_one_request(self):
        self._delivery_status = None
        self._delivery_body = False
        self._delivery_bytes = 0
        try:
            return super().handle_one_request()
        finally:
            if self._delivery_status is not None:
                try:
                    STATS.record(getattr(self, 'path', ''), self._delivery_status,
                                 self._delivery_bytes, self.headers.get('User-Agent', ''))
                except Exception:
                    pass

    def send_response(self, code, message=None):
        self._delivery_status = code
        return super().send_response(code, message)

    def end_headers(self):
        super().end_headers()
        self._delivery_body = True

    def send_public(self, body, content_type, max_age=300):
        tag = etag(body)
        same = unchanged(self.headers.get('If-None-Match', ''), tag)
        self.send_response(304 if same else 200)
        self.send_header('Cache-Control', f'public, max-age={max_age}, must-revalidate')
        self.send_header('ETag', tag)
        if not same:
            self.send_header('Content-Type', content_type)
            self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        if not same:
            self.wfile.write(body)

    def catalog_allowed(self, paginated):
        if not os.environ.get('RENDER'):
            return True
        address = client_address(self.client_address[0], self.headers.get('X-Forwarded-For', ''),
                                 True, self.headers.get('CF-Connecting-IP', ''))
        if address is None or LIMITER.allow(address, paginated):
            return True
        body = b'{"error":"catalog_rate_limit","retry_after":2}'
        self.send_response(429)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('Retry-After', '2')
        self.send_header('Content-Length', str(len(body)))
        self.end_headers()
        self.wfile.write(body)
        return False
