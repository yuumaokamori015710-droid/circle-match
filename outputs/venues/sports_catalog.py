"""Verified Tokyo venues, combined with the unchanged legacy tennis catalog."""
import json
from collections import Counter
from functools import lru_cache
from pathlib import Path
import unicodedata

from .tennis_catalog import CATALOG_PATH as TENNIS_PATH, validate_catalog

CATALOG_PATH = Path(__file__).resolve().parent / 'catalogs' / 'tokyo_sports.json'
SPORTS = ('野球', 'サッカー・フットサル', 'テニス', 'ピックルボール', '卓球', 'ゴルフ',
          'バスケットボール', 'バレーボール', 'バドミントン', 'ランニング', 'ラグビー',
          'カラオケ', 'イベント', 'ボードゲーム')


def selected(params, key):
    value = (params or {}).get(key, '')
    if isinstance(value, (tuple, list)):
        value = value[0] if value else ''
    return value.strip() if isinstance(value, str) else ''


def supports_catalog(params=None):
    return (selected(params, 'sport') in ('', *SPORTS)
            and selected(params, 'prefecture') in ('', '東京都')
            and selected(params, 'region') in ('', 'kanto'))


def validate_sports_catalog(rows):
    # Shared validation enforces safe public URLs, dates and Tokyo addresses.
    public = validate_catalog(rows)
    for raw, row in zip(rows, public):
        sports = raw.get('sports')
        if (not isinstance(sports, list) or not sports or any(not isinstance(sport, str) for sport in sports)
                or len(set(sports)) != len(sports)
                or any(sport not in SPORTS for sport in sports)):
            raise ValueError(f"Invalid venue sports: {row['id']}")
        if not isinstance(raw.get('facility_label'), str) or not raw['facility_label'].strip():
            raise ValueError(f"Missing venue type: {row['id']}")
        row.update(sports=sports, facility_label=raw['facility_label'], facility_kind='VENUE')
    return public


@lru_cache(maxsize=1)
def _load(tennis_modified, sports_modified):
    tennis = validate_catalog(json.loads(TENNIS_PATH.read_text(encoding='utf-8-sig')))
    for row in tennis:
        row.update(sports=['テニス'], facility_label='テニスコート')
    extra = validate_sports_catalog(json.loads(CATALOG_PATH.read_text(encoding='utf-8-sig')))
    rows = extra + tennis
    if len({r['id'] for r in rows}) != len(rows):
        raise ValueError('Duplicate venue id across catalogs')
    return rows


def get_catalog(params=None):
    rows = _load(TENNIS_PATH.stat().st_mtime_ns, CATALOG_PATH.stat().st_mtime_ns)
    sport = selected(params, 'sport')
    scoped = [row for row in rows if not sport or sport in row['sports']] if supports_catalog(params) else []
    counts = Counter(s for row in rows for s in row['sports'])
    return {'courts': scoped, 'meta': {
        'total': len(scoped), 'checked_at': max((row['checked_at'] for row in scoped), default=''),
        'municipalities': sorted({row['municipality'] for row in scoped}),
        'sports': dict(counts), 'sport': sport, 'prefecture': '東京都',
        'coverage_note': '東京都内の公式情報を確認した施設を掲載しています。全施設の網羅・空き状況のリアルタイム照会には対応していません。予約は施設の公式サイト・窓口で行ってください。',
    }}


def filter_catalog(rows, params):
    """Server-side equivalent of the browser filters, including no-JS GET forms."""
    def value(key):
        return selected(params, 'v_' + key) if 'v_' + key in (params or {}) else selected(params, key)
    normalize = lambda text: unicodedata.normalize('NFKC', str(text or '')).lower().strip()
    terms = normalize(value('q')).split()
    try:
        maximum = float(value('price_max')) if value('price_max') else None
        if maximum is not None and (maximum < 0 or not maximum < float('inf')):
            maximum = None
    except ValueError:
        maximum = None
    matches = []
    for row in rows:
        if row['availability_status'] == 'SUSPENDED' and value('show_suspended') not in {'1', 'true', 'on'}:
            continue
        if any(value(key) and row[key] != value(key) for key in ('municipality', 'area', 'operator_type', 'facility_kind')):
            continue
        if any(value(key) in {'1', 'true', 'on'} and row[key] is not True for key in ('indoor', 'night_lighting')):
            continue
        if maximum is not None and (row['price_per_hour'] is None or row['price_per_hour'] > maximum):
            continue
        text = normalize(' '.join(str(row.get(k) or '') for k in ('name', 'operator', 'municipality', 'address', 'surface', 'booking_method', 'booking_note', 'price_note')))
        if all(term in text for term in terms):
            matches.append(row)
    if value('sort') == 'price':
        matches.sort(key=lambda row: (row['price_per_hour'] is None, row['price_per_hour'] or 0, row['name']))
    else:
        matches.sort(key=lambda row: row['name'])
    return matches
