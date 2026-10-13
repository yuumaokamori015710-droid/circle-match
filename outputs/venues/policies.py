"""Source-reviewed reservation cancellation terms; missing is never 'free'."""
from datetime import date
from functools import lru_cache
import json
from pathlib import Path
from urllib.parse import urlsplit

POLICY_PATH = Path(__file__).resolve().parent / 'catalogs' / 'cancellation_policies.json'


@lru_cache(maxsize=1)
def load(modified):
    result = {}
    for entry in json.loads(POLICY_PATH.read_text(encoding='utf-8')):
        ident = entry['id']
        if ident in result or not entry.get('summary'):
            raise ValueError('Invalid cancellation policy: ' + ident)
        date.fromisoformat(entry['checked_at'])
        url = urlsplit(entry['source_url'])
        if url.scheme != 'https' or not url.hostname or url.username or url.password:
            raise ValueError('Invalid cancellation source URL')
        if entry['status'] not in {'conditional', 'not_allowed'}:
            raise ValueError('Invalid cancellation status')
        result[ident] = entry
    return result


def attach(rows):
    policies = load(POLICY_PATH.stat().st_mtime_ns)
    if set(policies) - {row['id'] for row in rows}:
        raise ValueError('Cancellation policy references unknown venue')
    return [dict(row, cancellation=policies.get(row['id'])) for row in rows]
