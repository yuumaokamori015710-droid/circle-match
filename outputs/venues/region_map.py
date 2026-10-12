"""SSR geographic drill-down. Generated SVG boundaries require no map service."""
from collections import Counter
from html import escape
from urllib.parse import urlencode
from .geography import maps, value, selection, toggle, ancestors, AREA_STAGES, PREFECTURES

STAGES = {'japan': '日本', 'kanto': '関東', 'tokyo': '東京都',
          'wards': '23区', 'tama': '多摩', 'islands': '島しょ'}


def stage_for(params):
    stage, area = value(params, 'map'), value(params, 'area')
    if stage in AREA_STAGES.values() and area in AREA_STAGES and STAGES[stage] != area:
        return AREA_STAGES[area]
    if stage in STAGES:
        return stage
    places = selection(params)
    stages = {next((AREA_STAGES[p] for p in [place, *ancestors(place)] if p in AREA_STAGES), None) for place in places}
    if len(stages) == 1 and None not in stages:
        return stages.pop()
    if places and all(place in PREFECTURES for place in places):
        return 'kanto'
    return AREA_STAGES.get(area, 'tokyo')


def target(stage, key):
    if stage == 'japan':
        return ('kanto', '', '') if key == '関東' else None
    if stage == 'kanto':
        return ('tokyo', '', '') if key == '東京都' else None
    if stage == 'tokyo':
        return (AREA_STAGES[key], key, '') if key in AREA_STAGES else None
    return (stage, STAGES[stage], key)


def destination(params, stage, area='', municipality='', places=None):
    query = {k: v[0] if isinstance(v, list) else v for k, v in params.items()
             if k not in {'area', 'municipality', 'v_area', 'v_municipality', 'v_map', 'map', 'v_page', 'places', 'v_places'}}
    query['v_map'] = stage
    selected = selection(params) if places is None else places
    if selected:
        query['v_places'] = ','.join(selected)
    return '/venues?' + urlencode(query)


def render(params, rows):
    stage = stage_for(params)
    selected = selection(params)
    counts = Counter(row['municipality'] for row in rows if row['availability_status'] != 'SUSPENDED')
    area_counts = Counter(row['area'] for row in rows if row['availability_status'] != 'SUSPENDED')
    total = sum(counts.values())
    entries = maps()['maps'][stage]
    keys = list(dict.fromkeys(entry['key'] for entry in entries))
    if stage == 'tokyo':
        keys.append('島しょ')
    def count(key):
        return (total if key in {'関東', '東京都'} else area_counts[key]) if stage in {'japan', 'kanto', 'tokyo'} else counts[key]
    def anchor(key):
        dest = target(stage, key)
        selectable = stage != 'japan'
        disabled = not selectable and dest is None
        active = key in selected
        label = f'{key} {count(key):,}施設' if selectable or dest else f'{key} 掲載準備中'
        cls = 'venue-map-shape'
        cls += ' is-disabled' if disabled else ' is-active' if active else ''
        attrs = (f'class="{cls}" data-region="{escape(key, quote=True)}" aria-label="{escape(label, quote=True)}"')
        if disabled:
            return 'g', attrs + ' aria-disabled="true"'
        href = destination(params, stage, places=toggle(selected, key)) if selectable else destination(params, *dest)
        if selectable:
            attrs += f' data-place="{escape(key, quote=True)}" role="checkbox" aria-checked="{str(active).lower()}"'
        return 'a', attrs + f' href="{escape(href, quote=True)}"'
    paths, choices = [], []
    for key in keys:
        group = [e for e in entries if e['key'] == key]
        if group:
            tag, attrs = anchor(key)
            paths.append(f'<{tag} {attrs}><title>{escape(key)}</title>' + ''.join(f'<path d="{e["d"]}"/>' for e in group) + f'</{tag}>')
        dest = target(stage, key)
        if stage == 'japan':
            href = f' href="{escape(destination(params, *dest), quote=True)}"' if dest else ' aria-disabled="true"'
            tag = 'a' if dest else 'span'
            cls = 'venue-map-choice' + (' is-disabled' if not dest else '')
            choices.append(f'<{tag} class="{cls}"{href}><span>{escape(key)}</span><small>{f"{count(key):,}施設" if dest else "準備中"}</small></{tag}>')
            continue
        checked = ' checked' if key in selected else ''
        active = ' is-active' if checked else ''
        checkbox = f'<label class="venue-map-choice{active}" data-region="{escape(key, quote=True)}"><input type="checkbox" data-place="{escape(key, quote=True)}"{checked}><span>{escape(key)}</span><small>{count(key):,}施設</small></label>'
        zoom = f'<a class="venue-map-zoom" href="{escape(destination(params, *dest), quote=True)}" aria-label="{escape(key)}を詳しく選ぶ" title="{escape(key)}を詳しく選ぶ">&#8250;</a>' if dest and stage in {'kanto', 'tokyo'} else ''
        fallback = f'<noscript><a class="venue-map-choice" href="{escape(destination(params, stage, places=toggle(selected, key)), quote=True)}">{escape(key)}</a></noscript>'
        choices.append(f'<div class="venue-map-item">{checkbox}{zoom}{fallback}</div>')
    trail = ['japan', 'kanto', 'tokyo'] + ([stage] if stage not in {'japan', 'kanto', 'tokyo'} else [])
    trail = trail[:trail.index(stage)+1]
    separator = '<span class="venue-map-separator" aria-hidden="true">/</span>'
    breadcrumbs = separator.join(f'<a href="{escape(destination(params, key, STAGES[key] if key in AREA_STAGES.values() else ""), quote=True)}"' + (' aria-current="page"' if key == stage else '') + f'>{STAGES[key]}</a>' for key in trail)
    return f'''<section class="venue-region-panel" aria-labelledby="venue-region-heading" data-stage="{stage}">
<div class="venue-region-heading"><h3 id="venue-region-heading">地域から探す</h3><nav class="venue-map-breadcrumbs" aria-label="選択した地域">{breadcrumbs}</nav></div>
<div class="venue-map-layout"><div class="venue-map-wrap"><svg class="venue-region-map" viewBox="0 0 640 320" role="group" aria-label="{STAGES[stage]}の地域選択地図">{''.join(paths)}</svg></div><div class="venue-map-choices" data-stage="{stage}" aria-label="{STAGES[stage]}の地域候補">{''.join(choices)}</div></div>
<p class="venue-map-credit"><a href="https://nlftp.mlit.go.jp/ksj/" target="_blank" rel="noopener noreferrer">国土数値情報（行政区域）</a>を加工。境界は2021年版。掲載対象は東京都です。</p></section>'''
