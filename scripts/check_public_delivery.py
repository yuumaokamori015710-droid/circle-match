"""Bounded read-only delivery checks. No sessions, mail, applications or payments."""
import argparse
from datetime import datetime, timezone
import gzip
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, *args):
        return None


def check(base, expected_commit=''):
    report = {'checked_at': datetime.now(timezone.utc).isoformat(), 'checks': []}

    def get(path, extra=None):
        headers = {'User-Agent': 'CircleMatch-Access-Check/1.0', 'Accept-Encoding': 'gzip',
                   'Cache-Control': 'no-cache', **(extra or {})}
        try:
            response = build_opener(NoRedirect()).open(Request(base + path, headers=headers), timeout=30)
        except HTTPError as error:
            response = error
        with response:
            raw = response.read()
            body = gzip.decompress(raw) if response.headers.get('Content-Encoding') == 'gzip' and raw else raw
            return response.status, body, response.headers, len(raw)

    status, body, _, _ = get('/healthz')
    assert status == 200 and json.loads(body)['ok'] is True
    report['commit'] = json.loads(body).get('revision', '')
    assert not expected_commit or report['commit'] == expected_commit
    for path in ('/privacy', '/terms', '/guides/tokyo-venue-costs',
                 '/api/venues?view=page&limit=50', '/assets/venues/tennis.js'):
        status, body, headers, wire = get(path)
        assert status == 200 and headers.get('Content-Encoding') == 'gzip', path
        assert 'public' in headers.get('Cache-Control', '') and 'Set-Cookie' not in headers, path
        assert 'Accept-Encoding' in headers.get('Vary', ''), path
        if path.startswith('/api/venues'):
            assert len(json.loads(body)['courts']) == 50
        tag = headers['ETag']
        same_status, same_body, _, same_wire = get(path, {'If-None-Match': tag})
        assert (same_status, same_body, same_wire) == (304, b'', 0), path
        report['checks'].append({'path': path, 'status': status, 'plain_bytes': len(body),
                                 'wire_bytes': wire, 'conditional_status': same_status})
    event = '/events/event_user_supabase_fe23d660_0d10_49cc_ae6_f42c6bd8fd'
    for path in ('/signin', '/api/me', '/api/notifications/unread', event, event + '/apply', event + '/guest'):
        status, _, headers, _ = get(path, {'If-None-Match': '*'})
        assert status in (200, 302, 401, 404), path
        if expected_commit and path == event:
            assert status == 200, path
        assert 'ETag' not in headers and 'public' not in headers.get('Cache-Control', ''), path
        if status == 200:
            assert 'no-store' in headers.get('Cache-Control', ''), path
        report['checks'].append({'path': path, 'status': status, 'public_cache': False})
    status, _, headers, _ = get('/privacy', {'Cookie': 'cm_session=delivery-check-invalid', 'If-None-Match': '*'})
    assert status == 200 and 'no-store' in headers.get('Cache-Control', '') and 'ETag' not in headers
    report['credential_bearing_html_no_store'] = True
    report['ok'] = True
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', required=True)
    parser.add_argument('--expected-commit', default='')
    parser.add_argument('--report', type=Path, default=Path('work/public-delivery-report.json'))
    args = parser.parse_args()
    target = urlsplit(args.base_url)
    if (target.username or target.password or target.query or target.fragment or target.path not in {'', '/'}
            or not target.hostname or (target.scheme != 'https' and not
                (target.scheme == 'http' and target.hostname in {'127.0.0.1', 'localhost', '::1'}))):
        parser.error('Use an HTTPS origin or a local test server without credentials')
    report = check(args.base_url.rstrip('/'), args.expected_commit)
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
