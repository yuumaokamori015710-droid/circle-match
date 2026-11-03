"""Credential-free production access checks. Reports only status codes, never bodies."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import time
from urllib.error import HTTPError, URLError
from urllib.parse import urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

PROTECTED_PATHS = (
    '/admin', '/admin/payments', '/admin/security', '/admin/contact-research',
    '/admin/contact-research.csv', '/api/admin/contact-research', '/api/admin_metrics',
    '/api/audit_logs', '/api/privacy_metrics', '/api/collection_status', '/api/candidates', '/api/claims',
)
RETIRED_PATHS = ('/admin/payments/host-fees', '/api/payments/admin/host-fees/campaign')


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def clean_request(base, path, method='GET'):
    # A fresh opener has neither a cookie jar nor cached Basic authentication.
    request = Request(base+path, method=method, data=b'{}' if method == 'POST' else None,
        headers={'Cache-Control':'no-cache', 'Content-Type':'application/json', 'User-Agent':'CircleMatch-Access-Check/1.0'})
    try:
        response = build_opener(NoRedirect()).open(request, timeout=15)
    except HTTPError as error:
        response = error
    with response:
        return response.status, response.read(65536)


def wait_for_revision(base, expected, seconds):
    deadline = time.monotonic()+seconds
    while True:
        try:
            code, body = clean_request(base, '/healthz')
            health = json.loads(body) if code == 200 else {}
            if health.get('ok') is True and (not expected or health.get('revision') == expected):
                return health.get('revision', '')
        except (OSError, URLError, ValueError):
            pass
        if time.monotonic() >= deadline:
            raise TimeoutError('Expected deployment did not become healthy')
        time.sleep(min(20, max(0, deadline-time.monotonic())))


def probe(base):
    checks = []
    for path in PROTECTED_PATHS:
        code, _ = clean_request(base, path)
        checks.append(dict(profile='anonymous', method='GET', path=path, status=code, expected=401, ok=code == 401))
    for path in RETIRED_PATHS:
        for method in ('GET', 'POST'):
            code, _ = clean_request(base, path, method)
            checks.append(dict(profile='anonymous', method=method, path=path, status=code, expected=404, ok=code == 404))
    return checks


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url', default='https://circle-match.jp')
    parser.add_argument('--expected-commit', default='')
    parser.add_argument('--wait-seconds', type=int, default=0)
    parser.add_argument('--report', type=Path, default=Path('work/admin-access-report.json'))
    args = parser.parse_args(argv)
    target = urlsplit(args.base_url)
    if (target.username or target.password or target.query or target.fragment or target.path not in {'', '/'}
            or not target.hostname or (target.scheme != 'https' and not
                (target.scheme == 'http' and target.hostname in {'127.0.0.1', 'localhost', '::1'}))):
        parser.error('Use an HTTPS origin or a local test server without credentials')
    report = dict(checked_at=datetime.now(timezone.utc).isoformat(), expected_commit=args.expected_commit,
        profile='anonymous', member_checks='Separate temporary-DB integration tests; no production member credentials used', checks=[], ok=False)
    try:
        report['deployed_commit'] = wait_for_revision(args.base_url.rstrip('/'), args.expected_commit, max(0,args.wait_seconds))
        report['checks'] = probe(args.base_url.rstrip('/'))
        report['ok'] = all(item['ok'] for item in report['checks'])
    except Exception as error:
        report['error_type'] = type(error).__name__
    args.report.parent.mkdir(parents=True, exist_ok=True)
    args.report.write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    if summary := os.getenv('GITHUB_STEP_SUMMARY'):
        with open(summary, 'a', encoding='utf-8') as stream:
            stream.write('## Production Admin Access\n\nResult: '+('PASS' if report['ok'] else 'FAIL')+'\n\n')
            stream.write('Unauthenticated live requests use no cookies or Basic credentials. Valid ordinary-account checks run against a temporary DB in the integration job.\n\n')
            stream.write('| Method | Path | HTTP | Result |\n|---|---|---|---|\n')
            for item in report['checks']:
                stream.write(f"| {item['method']} | `{item['path']}` | {item['status']} | {'PASS' if item['ok'] else 'FAIL'} |\n")
    print(json.dumps(report, indent=2))
    return 0 if report['ok'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
