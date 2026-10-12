"""Reviewed conditional tariffs, separate from the preserved legacy catalog."""
from datetime import date
from functools import lru_cache
import json
from pathlib import Path
from urllib.parse import urlsplit

FEE_PATH = Path(__file__).resolve().parent / 'catalogs' / 'fee_plans.json'


def validate(entries):
    if not isinstance(entries, list):
        raise ValueError('Venue tariffs must be a list')
    result = {}
    for entry in entries:
        ident = entry.get('id')
        if not isinstance(ident, str) or not ident or ident in result:
            raise ValueError('Missing or duplicate venue tariff id')
        date.fromisoformat(entry['checked_at'])
        plans = entry.get('fee_options')
        if not isinstance(plans, list) or not plans:
            raise ValueError('Missing conditional venue tariffs: ' + ident)
        for plan in plans:
            if type(plan.get('amount')) is not int or plan['amount'] < 0:
                raise ValueError('Invalid venue tariff amount: ' + ident)
            for key in ('label', 'unit', 'conditions', 'source_url'):
                if not isinstance(plan.get(key), str) or not plan[key].strip():
                    raise ValueError('Missing tariff ' + key + ': ' + ident)
            url = urlsplit(plan['source_url'])
            if url.scheme != 'https' or not url.hostname or url.username or url.password:
                raise ValueError('Unsafe tariff source URL')
        result[ident] = entry
    return result


@lru_cache(maxsize=1)
def load(modified):
    return validate(json.loads(FEE_PATH.read_text(encoding='utf-8')))


def attach(rows):
    tariffs = load(FEE_PATH.stat().st_mtime_ns)
    unknown = set(tariffs) - {row['id'] for row in rows}
    if unknown:
        raise ValueError('Tariffs reference unknown venue ids: ' + ','.join(sorted(unknown)))
    return [dict(row, fee_options=tariffs[row['id']]['fee_options'],
                 fee_note=tariffs[row['id']].get('fee_note', ''),
                 fee_checked_at=tariffs[row['id']]['checked_at'])
            if row['id'] in tariffs else row for row in rows]
