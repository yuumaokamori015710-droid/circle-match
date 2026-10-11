"""Upload private research results to the existing administrator-only API.

Credentials are read from a local file, never command-line args or logged.
No emails or notifications are sent. Re-running a batch is idempotent.
"""
import argparse
import base64
import json
from pathlib import Path
import sys
import time
from urllib import request, error, parse

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'outputs'))
import circlematch_contact_research as research


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--file', type=Path, required=True)
    p.add_argument('--credentials-file', type=Path)
    p.add_argument('--base-url', default='https://circle-match.onrender.com')
    p.add_argument('--validate-only', action='store_true')
    args = p.parse_args()
    payload = json.loads(args.file.read_text(encoding='utf-8'))
    records = payload['results']
    errors = []
    for row in records:
        try:
            research._record(row)
        except ValueError as exc:
            errors.append({'circle_id': row.get('circle_id'), 'error': str(exc)})
    if errors:
        print(json.dumps({'validation_errors': errors}, ensure_ascii=False))
        raise SystemExit(1)
    print(json.dumps({'validated': len(records)}), flush=True)
    if args.validate_only:
        return
    if not args.credentials_file:
        p.error('--credentials-file is required for upload')
    base = parse.urlsplit(args.base_url)
    if base.scheme != 'https' or base.username or base.password or base.hostname != 'circle-match.onrender.com':
        p.error('Production upload destination must be the existing Circle Match HTTPS service')
    creds = json.loads(args.credentials_file.read_text(encoding='utf-8'))
    auth = 'Basic ' + base64.b64encode((creds['username'] + ':' + creds['password']).encode()).decode()
    # No redirects: credentials must never follow a changed destination.
    class NoRedirect(request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None
    opener = request.build_opener(NoRedirect())
    for offset in range(0, len(records), 250):
        batch = {'job_id': payload['job_id'], 'results': records[offset:offset + 250]}
        encoded = json.dumps(batch, ensure_ascii=False).encode('utf-8')
        req = request.Request(args.base_url.rstrip('/') + '/api/admin/contact-research/import', data=encoded, headers={'Authorization': auth, 'Content-Type': 'application/json'}, method='POST')
        for attempt in range(3):
            try:
                with opener.open(req, timeout=60) as res:
                    result = json.load(res)
                if not result.get('ok'):
                    raise RuntimeError('Import did not succeed')
                print(json.dumps({'uploaded': min(offset + 250, len(records)), 'summary': result.get('summary')}), flush=True)
                break
            except error.HTTPError as exc:
                if exc.code < 500 or attempt == 2:
                    print(json.dumps({'error': 'HTTP ' + str(exc.code), 'batch_offset': offset}), flush=True)
                    raise SystemExit(1) from None
                time.sleep(5)
            except error.URLError:
                if attempt == 2:
                    raise SystemExit('Network error; re-run safely to resume') from None
                time.sleep(5)


if __name__ == '__main__':
    main()
