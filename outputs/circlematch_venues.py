"""Public venue directory embedded in the native Circle Match page shell.

``render_venue_body(params)`` returns only the directory section, without navigation.
Pass the same parse_qs parameters to ``render_venue_head(params)`` so unlisted
sports or regions receive only the stylesheet, without a catalog request.
Serve the exact ``ASSET_PATHS`` entries as their (Path, Content-Type) tuple, and
Serve ``get_venue_catalog(params)`` at GET /api/venues. The legacy tennis-only
``get_catalog()`` remains available at /api/tennis-courts. No database is used.
"""
from html import escape
from hashlib import sha256
from pathlib import Path
from urllib.parse import urlencode
import logging

if __package__:
    from .venues.tennis_catalog import get_catalog
    from .venues.sports_catalog import get_catalog as get_venue_catalog, supports_catalog, filter_catalog, selected, SPORTS, SORTS
    from .venues.search_facets import VENUE_TYPES, CHANNELS
    from .venues.fees import price_ranges
    from .venues.region_map import render as render_region_map
    from .venues.geography import selection as selected_places, label as region_label, parents as place_parents, PREFECTURES
else:
    from venues.tennis_catalog import get_catalog
    from venues.sports_catalog import get_catalog as get_venue_catalog, supports_catalog, filter_catalog, selected, SPORTS, SORTS
    from venues.search_facets import VENUE_TYPES, CHANNELS
    from venues.fees import price_ranges
    from venues.region_map import render as render_region_map
    from venues.geography import selection as selected_places, label as region_label, parents as place_parents, PREFECTURES


VENUE_DIR = Path(__file__).resolve().parent / "venues"
VENUE_CSS_URL = "/assets/venues/tennis.css"
VENUE_JS_URL = "/assets/venues/tennis.js"
ASSET_PATHS = {
    VENUE_CSS_URL: (VENUE_DIR / "static" / "tennis.css", "text/css; charset=utf-8"),
    VENUE_JS_URL: (VENUE_DIR / "static" / "tennis.js", "application/javascript; charset=utf-8"),
    '/assets/venues/region_maps.json': (VENUE_DIR / 'catalogs' / 'region_maps.json', 'application/json; charset=utf-8'),
}
ASSET_VERSIONS = {url: sha256(path.read_bytes()).hexdigest()[:12] for url, (path, _) in ASSET_PATHS.items()}


def _selected(params, key: str) -> str:
    value = (params or {}).get(key, "")
    if isinstance(value, (list, tuple)):
        value = value[0] if value else ""
    return value.strip() if isinstance(value, str) else ""


def venue_defaults(venue_id, sport=''):
    row = next((row for row in get_venue_catalog()['courts'] if row['id'] == venue_id), None)
    if not row or row['availability_status'] == 'SUSPENDED':
        return {}
    return {'location': f"{row['name']} / {row['address']}", 'prefecture': '東京都',
            'sport_category': sport if sport in row['sports'] else row['sports'][0]}


def _link(url, label, css='venue-secondary-link'):
    return f'<a href="{escape(url, quote=True)}" class="{css}" target="_blank" rel="noopener noreferrer">{escape(label)} ↗</a>'


def _card(row, index, sport):
    e = lambda key: escape(str(row.get(key) or ''))
    suspended = row['availability_status'] == 'SUSPENDED'
    badges = ' / '.join(escape(s) for s in row['sports'])
    plans = row.get('fee_options', [])
    ranges = price_ranges(row)
    price = ''
    for bounds in ranges[:2]:
        text = f'{bounds["minimum"]:,}円'
        if bounds['maximum'] != bounds['minimum']:
            text += f'〜{bounds["maximum"]:,}円'
        price += f'<div class="venue-rate-preview"><span class="venue-price-amount">{text}</span><p class="venue-price-unit">{escape(bounds["unit"])}</p></div>'
    if not ranges:
        price = '<span class="venue-unconfirmed">金額未取得</span>'
    fee_source = ({'url': plans[0]['source_url']} if plans else next((s for s in row['sources'] if '公式料金表' in s['title']), None))
    fee_link = _link(fee_source['url'], '公式料金表', 'venue-fee-link') if fee_source and (plans or row['price_from'] is not None) else ''
    sources = ''.join('<li>' + _link(s['url'], s['title']) + '</li>' for s in row['sources'])
    booking = _link(row['official_url'] if suspended else row['booking_url'],
                    '営業案内' if suspended else '公式予約先', 'venue-primary-link')
    create_url = '/events/new?' + urlencode({'venue': row['id'], 'sport': sport or row['sports'][0], 'prefecture': '東京都'})
    create = '' if suspended else f'<a class="venue-secondary-link" href="{escape(create_url, quote=True)}" aria-label="この会場で募集を作る"><span class="venue-create-prefix">この会場で</span>募集を作る</a>'
    official = '' if suspended or row['booking_url'] == row['official_url'] else _link(row['official_url'], '公式案内')
    warning = f'<p class="venue-availability-note">休止中：{e("availability_note")}</p>' if suspended else ''
    registration = {True: '必要', False: '不要', None: '未確認'}[row.get('registration_required')]
    hours = (e('opening_hours') + ' ' + e('opening_note')) if row.get('opening_hours') else '利用時間は未確認'
    hours_link = _link(row['official_url'], '利用時間の公式案内') if row.get('opening_hours') else ''
    rates = ''.join(f'<tr><th scope="row">{escape(p["label"])}</th><td class="venue-tariff-amount">{p["amount"]:,}円</td><td>{escape(p["unit"])}</td><td>{escape(p["conditions"])}</td></tr>' for p in plans)
    tariff = f'<table class="venue-tariff"><caption>条件別料金</caption><thead><tr><th>利用区分</th><th>金額</th><th>単位</th><th>適用条件</th></tr></thead><tbody>{rates}</tbody></table>' if rates else ''
    policy = row.get('cancellation')
    cancellation = (escape(policy['summary']) + ' ' + _link(policy['source_url'], '公式キャンセル規定')
                    + '（確認日：' + escape(policy['checked_at']) + '）') if policy else '条件は未確認です。予約前に公式予約先でご確認ください。'
    tariff += '<p class="venue-cancellation"><strong>キャンセル条件</strong><br>' + cancellation + '</p>'
    channels = '・'.join(dict(CHANNELS).get(c, c) for c in row.get('booking_channels', [])) or '公式案内'
    return f'''<tr class="venue-court-card" aria-labelledby="venue-court-title-{index}">
<th scope="row" class="venue-court-main"><h3 id="venue-court-title-{index}">{e('name')}</h3>{warning}<p class="venue-court-features">{badges}</p></th>
<td class="venue-location-cell" data-label="所在地">{e('municipality')}</td>
<td class="venue-court-price" data-label="料金"><div class="venue-original-price">{price}</div>{fee_link}</td>
<td class="venue-booking-cell" data-label="予約方法">{escape(channels)}</td><td class="venue-registration-cell" data-label="事前登録">{registration}</td>
<td class="venue-action-cell"><div class="venue-court-links">{booking}{create}</div></td></tr>
<tr class="venue-details-row"><td colspan="6"><details id="venue-details-{index}" class="venue-court-details"><summary aria-label="料金表・施設詳細"><span class="venue-details-prefix">料金表・施設</span>詳細</summary><div class="venue-detail-content"><div>{tariff}<p class="venue-court-note">{e('price_note')}</p><p class="venue-court-note">{escape(row.get('fee_note', ''))}</p><p class="venue-opening-hours"><strong>通常利用時間</strong> {hours} {hours_link}</p></div><div><dl><dt>住所</dt><dd>{e('address')}</dd><dt>予約方法</dt><dd>{e('booking_method')}</dd><dt>利用条件</dt><dd>{e('booking_note')}</dd><dt>施設</dt><dd>{e('facility_label')}</dd><dt>運営</dt><dd>{e('operator')}（{'公営' if row['operator_type']=='PUBLIC' else '民営'}）</dd><dt>確認日</dt><dd>{e('checked_at')}</dd></dl>{official}<ul class="venue-source-list">{sources}</ul></div></div></details></td></tr>'''


def _filters(params, catalog):
    def value(key):
        return selected(params, 'v_' + key) if 'v_' + key in params else selected(params, key)
    def select(name, label, options, ident=''):
        items = ''.join(f'<option value="{escape(v, quote=True)}"' + (' selected' if value(name) == v else '') + f'>{escape(text)}</option>' for v, text in options)
        return f'<label><span>{label}</span><select name="{name}" id="{ident}">{items}</select></label>'
    places = selected_places(params)
    fields = '<label class="venue-search-field"><span>施設名・地名</span><input name="q" type="search" placeholder="施設名・住所で検索" maxlength="200" value="' + escape(value('q')[:200], quote=True) + '"></label>'
    fields += '<div class="venue-region-field"><label for="venue-open-region">地域</label><button id="venue-open-region" type="button" aria-haspopup="dialog" aria-controls="venue-region-dialog"><span id="venue-region-label">' + escape(region_label(places)) + '</span><span aria-hidden="true">&#9662;</span></button></div>'
    parent_map = place_parents()
    options = ''.join(f'<option value="{escape(place, quote=True)}" data-parent="{escape(parent_map.get(place, ""), quote=True)}"' + (' selected' if place in places else '') + f'>{escape(place)}</option>' for place in dict.fromkeys([*PREFECTURES, *parent_map, *places]))
    geography = f'<label><span>地域（複数選択可）</span><select name="places" id="venue-places-filter" multiple size="8">{options}</select></label>'
    fields += select('booking_channel', '予約方法', [('', 'すべての予約方法')] + list(CHANNELS) + [('unknown', '予約方法は未確認')])
    registration = select('registration', '施設の利用者登録', [('', '登録条件すべて'), ('required', '必要（確認済み）'), ('not_required', '不要（確認済み）'), ('unknown', '要否は未確認')])
    fields += '<label><span>料金上限</span><div class="venue-price-input"><input name="price_max" type="text" inputmode="numeric" maxlength="12" placeholder="例：3000" aria-describedby="venue-price-help" title="コート1面・1時間換算" value="' + escape(value('price_max'), quote=True) + '"><span>円</span></div></label>'
    legacy = ''.join(f'<input type="hidden" name="{key}" value="{escape(value(key), quote=True)}">' for key in ('venue_type', 'operator_type', 'open_from', 'open_until'))
    toggles = ''.join(f'<label class="venue-checkbox-label"><input name="{key}" type="checkbox" value="1"' + (' checked' if value(key) in {'1', 'true', 'on'} else '') + f'><span>{label}</span></label>' for key, label in [('night_lighting', '夜間照明あり'), ('indoor', '屋内施設あり'), ('show_suspended', '休止中の施設も表示')])
    context = ''.join(f'<input type="hidden" name="{key}" value="{escape(selected(params, key), quote=True)}">' for key in ('sport', 'region', 'prefecture') if selected(params, key))
    context += f'<input type="hidden" name="facility_kind" value="{escape(value("facility_kind"), quote=True)}"><input type="hidden" name="map" value="{escape(value("map"), quote=True)}">'
    context += f'<input type="hidden" name="price_status" value="{escape(value("price_status"), quote=True)}">'
    active = '<p class="venue-filter-note">以前のURLの追加条件を適用中です。「条件をリセット」で解除できます。</p>' if any(value(key) for key in ('venue_type', 'operator_type', 'facility_kind', 'open_from', 'open_until')) else ''
    return context + legacy + f'<fieldset id="venue-filter-fields"><legend class="venue-visually-hidden">会場の絞り込み条件</legend><div class="venue-filter-grid">{fields}</div><div class="venue-filter-footer"><details class="venue-extra-filters"><summary>追加条件</summary><div class="venue-extra-registration">{registration}</div><div class="venue-filter-options">{toggles}</div><p id="venue-price-help" class="venue-filter-note">料金上限・安い順は、条件が一定のコート1面・1時間に換算できる施設が対象です。空き状況・最終料金は公式予約先で確認してください。</p></details><button class="venue-apply" type="submit">条件を適用</button></div><div class="venue-geography-state">{geography}</div><noscript><style>.venue-directory .venue-geography-state{{display:grid!important}}</style></noscript>{active}</fieldset>'


def _column_headers(params):
    def value(key):
        return selected(params, 'v_' + key) if 'v_' + key in params else selected(params, key)
    def option(key, choice, label):
        query = {k: v for k, v in params.items() if k not in {key, 'v_' + key, 'v_page'}}
        if key == 'places':
            query = {k: v for k, v in query.items() if k not in {'area', 'v_area', 'municipality', 'v_municipality'}}
        if choice:
            query['v_' + key] = choice
        href = '/venues?' + urlencode(query, doseq=True) + '#venue-court-results'
        return (f'<a href="{escape(href, quote=True)}" data-venue-control="{key}" '
                f'data-value="{escape(choice, quote=True)}">{escape(label)}</a>')
    def sorts(ascending, descending):
        labels = dict(SORTS)
        return '<div class="venue-column-sorts">' + option('sort', ascending, labels[ascending]) + option('sort', descending, labels[descending]) + '</div>'
    name = (f'<label>施設名<input name="name" type="search" form="venue-court-filters" maxlength="200" '
            f'value="{escape(value("name")[:200], quote=True)}" placeholder="施設名で絞る"></label>'
            '<button type="submit" form="venue-court-filters">反映する</button>' + option('name', '', '施設名の絞り込みを解除'))
    location = '<a href="#venue-places-filter" data-venue-open-region>地図から地域を選ぶ</a>' + option('places', '', '地域の絞り込みを解除')
    prices = ''.join(option('price_status', key, label) for key, label in [('', '料金の有無すべて'), ('available', '料金掲載あり'), ('missing', '金額未取得'), ('hourly', '1面1時間で比較できる施設')])
    prices += option('sort', 'available', '料金掲載あり優先')
    booking = ''.join(option('booking_channel', key, label) for key, label in [('', 'すべての予約方法'), *CHANNELS, ('unknown', '予約方法は未確認')])
    registration = ''.join(option('registration', key, label) for key, label in [('', '登録条件すべて'), ('not_required', '登録不要'), ('required', '登録必要'), ('unknown', '要否は未確認')])
    actions = option('show_suspended', '', '休止中の施設を除く') + option('show_suspended', '1', '休止中の施設も表示')
    columns = [('施設名', 'name', 'name_desc', name), ('所在地', 'location', 'location_desc', location),
               ('料金・適用区分', 'price', 'price_desc', prices), ('予約方法', 'booking', 'booking_desc', booking),
               ('事前登録', 'registration', 'registration_desc', registration), ('予約・募集', 'checked_asc', 'checked', actions)]
    result = []
    for label, ascending, descending, filters in columns:
        order = value('sort') or 'available'
        aria = 'ascending' if order == ascending else 'descending' if order == descending else 'other' if label.startswith('料金') and order == 'available' else 'none'
        result.append(f'<th scope="col" data-venue-column="{ascending}" aria-sort="{aria}"><details class="venue-column-menu">'
                      f'<summary title="{label}の絞り込み・並べ替え"><span>{label}</span><span aria-hidden="true">&#9662;</span></summary>'
                      f'<div class="venue-column-options"><strong>{label}</strong>{sorts(ascending, descending)}{filters}</div></details></th>')
    return ''.join(result)


def render_venue_body(params=None) -> str:
    """Return native content; the caller owns the shared heading, selectors and tabs."""
    if supports_catalog(params):
        params = params or {}
        try:
            catalog = get_venue_catalog(params)
        except (OSError, ValueError):
            logging.exception('Unable to load public venue catalog')
            return '<section class="venue-directory"><div class="venue-message-panel" role="alert"><h2>会場データを取得できませんでした</h2><a href="/venues">もう一度読み込む</a></div></section>'
        area = selected(params, 'v_area') if 'v_area' in params else selected(params, 'area')
        municipality = selected(params, 'v_municipality') if 'v_municipality' in params else selected(params, 'municipality')
        if area in catalog['meta']['municipalities_by_area'] and municipality not in catalog['meta']['municipalities_by_area'][area]:
            params = {key: value for key, value in params.items() if key not in {'municipality', 'v_municipality'}}
        matches = filter_catalog(catalog['courts'], params)
        sport = selected(params, 'sport')
        title = f'{sport}の会場を探す' if sport else '東京都の会場を探す'
        try:
            page = min(max(int(selected(params, 'v_page') or '1'), 1), max(1, (len(matches) + 49) // 50))
        except ValueError:
            page = 1
        shown = matches[(page-1)*50:page*50]
        body = (VENUE_DIR / 'static' / 'tennis.html').read_text(encoding='utf-8')
        order = selected(params, 'v_sort') or selected(params, 'sort') or 'available'
        sort_options = ''.join(f'<option value="{key}"' + (' selected' if key == order else '') + f'>{escape(label)}</option>' for key, label in SORTS)
        values = {'TITLE': escape(title), 'FILTERS': _filters(params, catalog), 'REGION_MAP': render_region_map(params, catalog['courts']),
                  'SORT_OPTIONS': sort_options, 'COLUMN_HEADERS': _column_headers(params),
                  'HOURS_COUNT': str(catalog['meta']['hours_verified']),
                  'TOTAL': f"掲載 {catalog['meta']['total']:,} 施設", 'CHECKED': escape(catalog['meta']['checked_at']),
                  'COVERAGE': escape(catalog['meta']['coverage_note']), 'COUNT': f'{len(matches):,} 件',
                  'VISIBLE': f'{len(shown):,} / {len(matches):,} 件を表示',
                  'CARDS': ''.join(_card(row, index, sport) for index, row in enumerate(shown)),
                  'EMPTY_HIDDEN': 'hidden' if matches else '',
                  'CATALOG_URL': escape('/api/venues' + ('?' + urlencode({'sport': sport}) if sport else ''), quote=True)}
        pager = []
        for number, label in ((page-1, '前へ'), (page+1, '次へ')):
            if 1 <= number <= (len(matches)+49)//50:
                query = dict(params)
                query['v_page'] = number
                pager.append(f'<a href="/venues?{escape(urlencode(query, doseq=True), quote=True)}">{label}</a>')
        values['PAGER'] = '<noscript><nav class="venue-pagination" aria-label="会場一覧ページ">' + ' '.join(pager) + '</nav></noscript>'
        for key, value in values.items():
            body = body.replace('__VENUE_' + key + '__', value)
        return body
    sport = _selected(params, "sport")
    message = (f"{sport}の会場は掲載準備中" if sport and sport not in SPORTS
               else "この地域の会場は掲載準備中")
    return ('<section class="venue-directory" aria-labelledby="venue-page-title">'
            '<section class="venue-intro"><p class="venue-eyebrow">公式情報から探す</p>'
            '<h2 id="venue-page-title">会場を探す</h2></section>'
            '<div class="venue-message-panel venue-unavailable">'
            f'<h3>{escape(message)}</h3>'
            '<p>現在は東京都内のスポーツ施設・交流会場を掲載しています。'
            '上の競技・地域の条件を変更してお探しください。</p>'
            '</div></section>')


def render_venue_head(params=None) -> str:
    """Return scoped CSS and, only for supported selections, the catalog script."""
    head = f'<link rel="stylesheet" href="{VENUE_CSS_URL}?v={ASSET_VERSIONS[VENUE_CSS_URL]}">'
    if supports_catalog(params):
        head += f'\n<script src="{VENUE_JS_URL}?v={ASSET_VERSIONS[VENUE_JS_URL]}" defer></script>'
    return head


__all__ = ["render_venue_body", "render_venue_head", "supports_catalog", "get_catalog", "ASSET_PATHS",
           "get_venue_catalog", "venue_defaults", "VENUE_CSS_URL", "VENUE_JS_URL"]
