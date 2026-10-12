"""Shared geographic selections for server HTML, forms and map controls."""
from functools import lru_cache
import json
from pathlib import Path

MAP_PATH = Path(__file__).resolve().parent / 'catalogs' / 'region_maps.json'
AREA_STAGES = {'23区': 'wards', '多摩': 'tama', '島しょ': 'islands'}
PREFECTURES = ('茨城県', '栃木県', '群馬県', '埼玉県', '千葉県', '東京都', '神奈川県')


@lru_cache(maxsize=1)
def maps():
    return json.loads(MAP_PATH.read_text(encoding='utf-8'))


@lru_cache(maxsize=1)
def parents():
    result = {area: '東京都' for area in AREA_STAGES}
    for area, stage in AREA_STAGES.items():
        result.update({entry['key']: area for entry in maps()['maps'][stage]})
    return result


def value(params, key):
    item = (params or {}).get('v_' + key, (params or {}).get(key, ''))
    return (item[0] if isinstance(item, (tuple, list)) and item else item) or ''


def selection(params):
    params = params or {}
    if 'v_places' in params or 'places' in params:
        raw = params.get('v_places', params.get('places', ''))
        parts = raw if isinstance(raw, (tuple, list)) else [raw]
        return list(dict.fromkeys(token.strip()[:80] for part in parts if isinstance(part, str)
                                 for token in part.split(',') if token.strip()))[:100]
    return [value(params, 'municipality') or value(params, 'area')] if value(params, 'municipality') or value(params, 'area') else []


def ancestors(place):
    result = []
    while place in parents():
        place = parents()[place]
        result.append(place)
    return result


def toggle(selected, place):
    if place in selected:
        return [item for item in selected if item != place]
    # Selecting a child refines its parent; siblings and other prefectures remain.
    return [item for item in selected if item not in ancestors(place) and place not in ancestors(item)] + [place]


def matches(row, selected):
    return not selected or any(place in {row.get('prefecture', '東京都'), row['area'], row['municipality']}
                               for place in selected)


def label(selected):
    if not selected:
        return '地域指定なし'
    if len(selected) == 1 and selected[0] not in PREFECTURES:
        return '東京都 / ' + selected[0]
    return '・'.join(selected)
