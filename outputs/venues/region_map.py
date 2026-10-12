"""SSR geographic drill-down. Generated SVG boundaries require no map service."""
from collections import Counter
from functools import lru_cache
from html import escape
import json
from pathlib import Path
from urllib.parse import urlencode

MAP_PATH = Path(__file__).resolve().parent / 'catalogs' / 'region_maps.json'
STAGES = {'japan': '日本', 'kanto': '関東', 'tokyo': '東京都',
          'wards': '23区', 'tama': '多摩', 'islands': '島しょ'}
AREA_STAGES = {'23区': 'wards', '多摩': 'tama', '島しょ': 'islands'}


@lru_cache(maxsize=1)
def maps():
    return json.loads(MAP_PATH.read_text(encoding='utf-8'))


def value(params, key):
    item = params.get('v_' + key, params.get(key, ''))
    return (item[0] if isinstance(item, list) and item else item) or ''


def stage_for(params):
    stage, area = value(params, 'map'), value(params, 'area')
    if stage in AREA_STAGES.values() and area in AREA_STAGES and STAGES[stage] != area:
        return AREA_STAGES[area]
    return stage if stage in STAGES else AREA_STAGES.get(area, 'tokyo')


def target(stage, key):
    if stage == 'japan':
        return ('kanto', '', '') if key == '関東' else None
    if stage == 'kanto':
        return ('tokyo', '', '') if key == '東京都' else None
    if stage == 'tokyo':
        return (AREA_STAGES[key], key, '') if key in AREA_STAGES else None
    return (stage, STAGES[stage], key)


def destination(params, stage, area='', municipality=''):
    query = {k: v[0] if isinstance(v, list) else v for k, v in params.items()
             if k not in {'area', 'municipality', 'v_area', 'v_municipality', 'v_map', 'map', 'v_page'}}
    query['v_map'] = stage
    if area:
        query['v_area'] = area
    if municipality:
        query['v_municipality'] = municipality
    return '/venues?' + urlencode(query)


def render(params, rows):
    stage = stage_for(params)
    counts = Counter(row['municipality'] for row in rows if row['availability_status'] != 'SUSPENDED')
    area_counts = Counter(row['area'] for row in rows if row['availability_status'] != 'SUSPENDED')
    total = sum(counts.values())
    entries = maps()['maps'][stage]
    keys = list(dict.fromkeys(entry['key'] for entry in entries))
    if stage == 'tokyo':
        keys.append('島しょ')
    def count(key):
        return (total if key in {'関東', '東京都'} else area_counts[key]) if stage in {'japan', 'kanto', 'tokyo'} else counts[key]
    def anchor(key, shape=False):
        dest = target(stage, key)
        disabled = dest is None or count(key) == 0
        active = value(params, 'municipality') == key
        label = f'{key} {count(key):,}施設' if dest else f'{key} 掲載準備中'
        cls = 'venue-map-shape' if shape else 'venue-map-choice'
        cls += ' is-disabled' if disabled else ' is-active' if active else ''
        attrs = (f'class="{cls}" data-region="{escape(key, quote=True)}" aria-label="{escape(label, quote=True)}"')
        if disabled:
            return 'g' if shape else 'span', attrs + ' aria-disabled="true"'
        href = escape(destination(params, *dest), quote=True)
        return 'a', attrs + f' href="{href}"' + (' aria-current="true"' if active else '')
    paths, choices = [], []
    for key in keys:
        group = [e for e in entries if e['key'] == key]
        if group:
            tag, attrs = anchor(key, True)
            paths.append(f'<{tag} {attrs}><title>{escape(key)}</title>' + ''.join(f'<path d="{e["d"]}"/>' for e in group) + f'</{tag}>')
        tag, attrs = anchor(key)
        choices.append(f'<{tag} {attrs}><span>{escape(key)}</span><small>{f"{count(key):,}施設" if target(stage, key) else "準備中"}</small></{tag}>')
    trail = ['japan', 'kanto', 'tokyo'] + ([stage] if stage not in {'japan', 'kanto', 'tokyo'} else [])
    trail = trail[:trail.index(stage)+1]
    separator = '<span class="venue-map-separator" aria-hidden="true">/</span>'
    breadcrumbs = separator.join(f'<a href="{escape(destination(params, key, STAGES[key] if key in AREA_STAGES.values() else ""), quote=True)}"' + (' aria-current="page"' if key == stage else '') + f'>{STAGES[key]}</a>' for key in trail)
    selected = value(params, 'municipality')
    if selected:
        breadcrumbs += separator + f'<span aria-current="location">{escape(selected)}</span>'
    return f'''<section class="venue-region-panel" aria-labelledby="venue-region-heading" data-stage="{stage}" data-area="{escape(value(params, 'area'), quote=True)}" data-municipality="{escape(selected, quote=True)}">
<div class="venue-region-heading"><h3 id="venue-region-heading">地域から探す</h3><nav class="venue-map-breadcrumbs" aria-label="選択した地域">{breadcrumbs}</nav></div>
<div class="venue-map-layout"><div class="venue-map-wrap"><svg class="venue-region-map" viewBox="0 0 640 320" role="group" aria-label="{STAGES[stage]}の地域選択地図">{''.join(paths)}</svg></div><div class="venue-map-choices" aria-label="{STAGES[stage]}の地域候補">{''.join(choices)}</div></div>
<p class="venue-map-credit"><a href="https://nlftp.mlit.go.jp/ksj/" target="_blank" rel="noopener noreferrer">国土数値情報（行政区域）</a>を加工。境界は2021年版。掲載対象は東京都です。</p></section>'''
