"""Inline circle geography, using the same boundary assets as venue search."""
from html import escape
import json
from pathlib import Path
import re
from urllib.parse import urlencode

from venues.geography import maps, parents as tokyo_parents, AREA_STAGES

ROOT = Path(__file__).resolve().parent
ASSET_PATHS = {
    '/assets/regions/map.css': (ROOT / 'regions/map.css', 'text/css; charset=utf-8'),
    '/assets/regions/map.js': (ROOT / 'regions/map.js', 'application/javascript; charset=utf-8'),
}
RESOURCES = '<link rel="stylesheet" href="/assets/regions/map.css?v=20261012"><script src="/assets/regions/map.js?v=20261012" defer></script>'


def value(params, key):
    item = params.get(key, [''])
    return (item[0] if isinstance(item, (tuple, list)) and item else item) or ''


def hierarchy(regions):
    result = dict(tokyo_parents())
    result.update({pref: data['label'] for data in regions.values() for pref in data['prefectures']
                   if pref != data['label']})
    return result


def selected(params, regions):
    if 'places' in params:
        parts = params['places'] if isinstance(params['places'], (list, tuple)) else [params['places']]
        return list(dict.fromkeys(p.strip()[:80] for part in parts for p in part.split(',') if p.strip()))[:100]
    if value(params, 'prefecture'):
        return [value(params, 'prefecture')]
    region = regions.get(value(params, 'region'))
    return [region['label']] if region else []


def toggle(places, place, regions):
    tree = hierarchy(regions)
    def ancestors(item):
        result = []
        while item in tree:
            item = tree[item]
            result.append(item)
        return result
    if place in places:
        return [item for item in places if item != place]
    return [item for item in places if item not in ancestors(place) and place not in ancestors(item)] + [place]


def clause(places, regions):
    """All location comparisons remain bound SQL parameters, including LIKE."""
    predicates, args = [], []
    prefectures = {p for data in regions.values() for p in data['prefectures']}
    by_label = {data['label']: data['prefectures'] for data in regions.values()}
    for place in places:
        if place in by_label:
            prefs = by_label[place]
            predicates.append('u.prefecture in (' + ','.join('?' for _ in prefs) + ')')
            args.extend(prefs)
        elif place in prefectures:
            predicates.append('u.prefecture=?')
            args.append(place)
        else:
            cities = list(dict.fromkeys(e['key'] for e in maps()['maps'][AREA_STAGES[place]])) if place in AREA_STAGES else [place]
            parts = []
            args.append('東京都')
            for city in cities:
                parts.append('(u.city like ? escape \'\\\' or c.activity_area like ? escape \'\\\')')
                token = city.replace('\\', '\\\\').replace('%', '\\%').replace('_', '\\_')
                args.extend(['%' + token + '%'] * 2)
            predicates.append('(u.prefecture=? and (' + ' or '.join(parts) + '))')
    return ('(' + ' or '.join(predicates) + ')', args) if predicates else ('', [])


def stage_for(params, regions):
    requested = value(params, 'c_map')
    if requested in {'japan', 'tokyo', *AREA_STAGES.values(), *regions}:
        return requested
    places = selected(params, regions)
    tree = hierarchy(regions)
    if len(places) == 1:
        place = places[0]
        if place in AREA_STAGES:
            return AREA_STAGES[place]
        if tree.get(place) in AREA_STAGES:
            return AREA_STAGES[tree[place]]
        if place == '東京都':
            return 'tokyo'
        for key, data in regions.items():
            if place == data['label'] or place in data['prefectures']:
                return key
    return 'japan'


def destination(params, path, stage, places):
    query = {k: v for k, v in params.items() if k in {'tab', 'audience', 'q', 'sport', 'status', 'sort', 'organization_type'}}
    query.update(c_map=stage, places=','.join(places))
    return path + '?' + urlencode(query, doseq=True)


def render(params, grouped, regions, path='/', error=False):
    path = path if path in {'/', '/circles', '/social/circles'} else '/'
    places, stage = selected(params, regions), stage_for(params, regions)
    tree = hierarchy(regions)
    if stage == 'japan':
        entries = maps()['maps']['japan']
        keys = [data['label'] for data in regions.values()]
        title = '日本'
    elif stage in regions:
        entries = maps()['maps']['kanto'] if stage == 'kanto' else [dict(e, key=e['name']) for e in maps()['maps']['japan'] if e['name'] in regions[stage]['prefectures']]
        keys, title = regions[stage]['prefectures'], regions[stage]['label']
    else:
        entries = maps()['maps'][stage]
        keys = list(dict.fromkeys(e['key'] for e in entries))
        if stage == 'tokyo':
            keys.append('島しょ')
        title = '東京都' if stage == 'tokyo' else next(area for area, name in AREA_STAGES.items() if name == stage)
    counts = {}
    prefectures = {p for data in regions.values() for p in data['prefectures']}
    by_label = {data['label']: data['prefectures'] for data in regions.values()}
    for key in keys:
        def matches(row):
            if key in by_label:
                return row['prefecture'] in by_label[key]
            if key in prefectures:
                return row['prefecture'] == key
            cities = [e['key'] for e in maps()['maps'][AREA_STAGES[key]]] if key in AREA_STAGES else [key]
            return row['prefecture'] == '東京都' and any(city in (row.get('city') or '') or city in (row.get('activity_area') or '') for city in cities)
        counts[key] = sum(row['count'] for row in grouped if matches(row))
    def zoom(key):
        if stage == 'japan':
            return next(name for name, data in regions.items() if data['label'] == key)
        if key == '東京都':
            return 'tokyo'
        return AREA_STAGES.get(key)
    def active(key):
        ancestor = key
        while ancestor:
            if ancestor in places:
                return True
            ancestor = tree.get(ancestor)
        return False
    shapes, choices = [], []
    for key in keys:
        href = escape(destination(params, path, stage, toggle(places, key, regions)), quote=True)
        checked = active(key)
        attrs = f'data-place="{escape(key, quote=True)}"'
        css = ' is-active' if checked else ''
        amount = '取得失敗' if error else f'{counts[key]:,}団体'
        group = [e for e in entries if e['key'] == key]
        if group:
            shapes.append(f'<a class="circle-map-shape{css}" {attrs} href="{href}" role="checkbox" aria-checked="{str(checked).lower()}" aria-label="{escape(key)} {amount}"><title>{escape(key)}</title>' + ''.join(f'<path d="{e["d"]}"/>' for e in group) + '</a>')
        detail = zoom(key)
        arrow = f'<a class="circle-map-zoom" href="{escape(destination(params, path, detail, places), quote=True)}" aria-label="{escape(key)}を詳しく選ぶ" title="{escape(key)}を詳しく選ぶ">&#8250;</a>' if detail else ''
        choices.append(f'<div class="circle-map-item"><a class="circle-map-choice{css}" {attrs} href="{href}" role="checkbox" aria-checked="{str(checked).lower()}"><span class="circle-map-check" aria-hidden="true">{"&#10003;" if checked else ""}</span><span>{escape(key)}</span><small>{amount}</small></a>{arrow}</div>')
    viewbox = '0 0 640 320'
    if stage in regions and stage != 'kanto' and entries:
        points = [float(n) for e in entries for n in re.findall(r'-?\d+(?:\.\d+)?', e['d'])]
        xs, ys = points[::2], points[1::2]
        viewbox = f'{min(xs)-3} {min(ys)-3} {max(xs)-min(xs)+6} {max(ys)-min(ys)+6}'
    trail = [('japan', '日本')]
    if stage in regions:
        trail.append((stage, title))
    elif stage != 'japan':
        trail += [('kanto', '関東'), ('tokyo', '東京都')]
        if stage != 'tokyo':
            trail.append((stage, title))
    breadcrumbs = '<span aria-hidden="true">/</span>'.join(f'<a href="{escape(destination(params, path, name, places), quote=True)}"' + (' aria-current="page"' if name == stage else '') + f'>{label}</a>' for name, label in trail)
    clear = escape(destination(params, path, stage, []), quote=True)
    data = escape(json.dumps({'selected': places, 'parents': tree, 'stage': stage}, ensure_ascii=False), quote=True)
    return f'''<section id="circle-region-picker" class="circle-region-picker" data-state="{data}" aria-labelledby="circle-region-heading">
<div class="circle-region-heading"><h2 id="circle-region-heading">地域から探す</h2><nav class="circle-map-breadcrumbs" aria-label="地域の階層">{breadcrumbs}</nav></div>
<div class="circle-map-layout"><svg class="circle-region-map" viewBox="{viewbox}" role="group" aria-label="{escape(title)}の地域選択地図">{''.join(shapes)}</svg><div class="circle-map-choices" data-stage="{stage}">{''.join(choices)}</div></div>
<div class="circle-region-selection"><p>選択地域：<strong>{escape('・'.join(places) or '全国')}</strong></p><a href="{clear}" class="circle-region-clear">選択を解除</a></div>
<p class="circle-map-credit"><a href="https://nlftp.mlit.go.jp/ksj/" target="_blank" rel="noopener noreferrer">国土数値情報（行政区域）</a>を加工。境界は2021年版。</p></section>'''
