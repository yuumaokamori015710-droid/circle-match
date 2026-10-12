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
    from .venues.sports_catalog import get_catalog as get_venue_catalog, supports_catalog, filter_catalog, selected, SPORTS
    from .venues.search_facets import VENUE_TYPES, CHANNELS
    from .venues.region_map import render as render_region_map
else:
    from venues.tennis_catalog import get_catalog
    from venues.sports_catalog import get_catalog as get_venue_catalog, supports_catalog, filter_catalog, selected, SPORTS
    from venues.search_facets import VENUE_TYPES, CHANNELS
    from venues.region_map import render as render_region_map


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
    amount = lambda value: f'<span class="venue-price-amount">{value:,}円</span>'
    plans = row.get('fee_options', [])
    if plans:
        price = ''.join(f'<span class="venue-rate-preview"><span>{escape(p["label"])}</span>{amount(p["amount"])}</span>' for p in plans[:2])
    elif row['price_from'] is None:
        price = '<span class="venue-unconfirmed">金額未取得</span>'
    elif row.get('price_to') == row['price_from']:
        price = amount(row['price_from'])
    elif row.get('price_to') is not None:
        price = amount(row['price_from']) + f'<span class="venue-price-amount"><small>〜</small>{row["price_to"]:,}円</span>'
    else:
        price = amount(row['price_from'])
    fee_source = ({'url': plans[0]['source_url']} if plans else next((s for s in row['sources'] if '公式料金表' in s['title']), None))
    fee_link = _link(fee_source['url'], '公式料金表', 'venue-fee-link') if fee_source and (plans or row['price_from'] is not None) else ''
    sources = ''.join('<li>' + _link(s['url'], s['title']) + '</li>' for s in row['sources'])
    booking = _link(row['official_url'] if suspended else row['booking_url'],
                    '営業案内' if suspended else '公式予約先', 'venue-primary-link')
    create_url = '/events/new?' + urlencode({'venue': row['id'], 'sport': sport or row['sports'][0], 'prefecture': '東京都'})
    create = '' if suspended else f'<a class="venue-secondary-link" href="{escape(create_url, quote=True)}">この会場で募集を作る</a>'
    official = '' if suspended or row['booking_url'] == row['official_url'] else _link(row['official_url'], '公式案内')
    warning = f'<p class="venue-availability-note">休止中：{e("availability_note")}</p>' if suspended else ''
    registration = {True: '必要', False: '不要', None: '未確認'}[row.get('registration_required')]
    hours = (e('opening_hours') + ' ' + e('opening_note')) if row.get('opening_hours') else '利用時間は未確認'
    hours_link = _link(row['official_url'], '利用時間の公式案内') if row.get('opening_hours') else ''
    rates = ''.join(f'<tr><th scope="row">{escape(p["label"])}</th><td>{p["amount"]:,}円</td><td>{escape(p["unit"])}</td><td>{escape(p["conditions"])}</td></tr>' for p in plans)
    tariff = f'<table class="venue-tariff"><caption>条件別料金</caption><thead><tr><th>利用区分</th><th>金額</th><th>単位</th><th>適用条件</th></tr></thead><tbody>{rates}</tbody></table>' if rates else ''
    channels = '・'.join(dict(CHANNELS).get(c, c) for c in row.get('booking_channels', [])) or '公式案内'
    unit = escape(plans[0]['unit']) if plans else e('price_unit')
    more = f'<a class="venue-tariff-more" href="#venue-details-{index}">全{len(plans)}区分の料金</a>' if plans else ''
    return f'''<tr class="venue-court-card" aria-labelledby="venue-court-title-{index}">
<th scope="row" class="venue-court-main"><h3 id="venue-court-title-{index}">{e('name')}</h3>{warning}<p class="venue-court-features">{badges}</p></th>
<td class="venue-location-cell" data-label="所在地">{e('municipality')}</td>
<td class="venue-court-price" data-label="料金"><div class="venue-original-price">{price}</div><p class="venue-price-unit">{unit}</p>{more}{fee_link}</td>
<td class="venue-booking-cell" data-label="予約方法">{escape(channels)}</td><td class="venue-registration-cell" data-label="事前登録">{registration}</td>
<td class="venue-action-cell"><div class="venue-court-links">{booking}{create}</div></td></tr>
<tr class="venue-details-row"><td colspan="6"><details id="venue-details-{index}" class="venue-court-details"><summary>料金表・施設詳細</summary><div class="venue-detail-content"><div>{tariff}<p class="venue-court-note">{e('price_note')}</p><p class="venue-court-note">{escape(row.get('fee_note', ''))}</p><p class="venue-opening-hours"><strong>通常利用時間</strong> {hours} {hours_link}</p></div><div><dl><dt>住所</dt><dd>{e('address')}</dd><dt>予約方法</dt><dd>{e('booking_method')}</dd><dt>利用条件</dt><dd>{e('booking_note')}</dd><dt>施設</dt><dd>{e('facility_label')}</dd><dt>運営</dt><dd>{e('operator')}（{'公営' if row['operator_type']=='PUBLIC' else '民営'}）</dd><dt>確認日</dt><dd>{e('checked_at')}</dd></dl>{official}<ul class="venue-source-list">{sources}</ul></div></div></details></td></tr>'''


def _filters(params, catalog):
    def value(key):
        return selected(params, 'v_' + key) if 'v_' + key in params else selected(params, key)
    def select(name, label, options, ident=''):
        items = ''.join(f'<option value="{escape(v, quote=True)}"' + (' selected' if value(name) == v else '') + f'>{escape(text)}</option>' for v, text in options)
        return f'<label><span>{label}</span><select name="{name}" id="{ident}">{items}</select></label>'
    region = '東京都 / ' + (value('municipality') or value('area')) if value('municipality') or value('area') else '東京都全域'
    fields = '<div class="venue-region-field"><label for="venue-open-region">地域</label><button id="venue-open-region" type="button" aria-haspopup="dialog" aria-controls="venue-region-dialog"><span id="venue-region-label">' + escape(region) + '</span><span aria-hidden="true">&#9662;</span></button></div>'
    fields += '<label class="venue-search-field"><span>施設名・地名</span><input name="q" type="search" placeholder="施設名・住所で検索" maxlength="200" value="' + escape(value('q')[:200], quote=True) + '"></label>'
    geography = select('area', 'エリア', [('', '都内すべて'), ('23区', '23区'), ('多摩', '多摩'), ('島しょ', '島しょ')], 'venue-area-filter')
    municipalities = catalog['meta']['municipalities_by_area'].get(value('area'), catalog['meta']['municipalities'])
    geography += select('municipality', '自治体', [('', 'すべての自治体')] + [(m, m) for m in municipalities], 'venue-municipality-filter')
    fields += select('booking_channel', '予約方法', [('', 'すべての予約方法')] + list(CHANNELS) + [('unknown', '予約方法は未確認')])
    registration = select('registration', '施設の利用者登録', [('', '登録条件すべて'), ('required', '必要（確認済み）'), ('not_required', '不要（確認済み）'), ('unknown', '要否は未確認')])
    fields += '<label><span>料金上限 <small>コート1面・1時間換算</small></span><div class="venue-price-input"><input name="price_max" type="text" inputmode="numeric" maxlength="12" placeholder="例：3000" value="' + escape(value('price_max'), quote=True) + '"><span>円</span></div></label>'
    legacy = ''.join(f'<input type="hidden" name="{key}" value="{escape(value(key), quote=True)}">' for key in ('venue_type', 'operator_type', 'open_from', 'open_until'))
    toggles = ''.join(f'<label class="venue-checkbox-label"><input name="{key}" type="checkbox" value="1"' + (' checked' if value(key) in {'1', 'true', 'on'} else '') + f'><span>{label}</span></label>' for key, label in [('night_lighting', '夜間照明あり'), ('indoor', '屋内施設あり'), ('show_suspended', '休止中の施設も表示')])
    context = ''.join(f'<input type="hidden" name="{key}" value="{escape(selected(params, key), quote=True)}">' for key in ('sport', 'region', 'prefecture') if selected(params, key))
    context += f'<input type="hidden" name="facility_kind" value="{escape(value("facility_kind"), quote=True)}"><input type="hidden" name="map" value="{escape(value("map"), quote=True)}">'
    active = '<p class="venue-filter-note">以前のURLの追加条件を適用中です。「条件をリセット」で解除できます。</p>' if any(value(key) for key in ('venue_type', 'operator_type', 'facility_kind', 'open_from', 'open_until')) else ''
    return context + legacy + f'<fieldset id="venue-filter-fields"><legend class="venue-visually-hidden">会場の絞り込み条件</legend><div class="venue-filter-grid">{fields}</div><div class="venue-filter-footer"><details class="venue-extra-filters"><summary>追加条件</summary><div class="venue-extra-registration">{registration}</div><div class="venue-filter-options">{toggles}</div><p class="venue-filter-note">料金上限・安い順は、条件が一定のコート1面・1時間に換算できる施設が対象です。空き状況・最終料金は公式予約先で確認してください。</p></details><button class="venue-apply" type="submit">条件を適用</button></div><div class="venue-geography-state">{geography}</div><noscript><style>.venue-directory .venue-geography-state{{display:grid!important}}</style></noscript>{active}</fieldset>'


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
        values = {'TITLE': escape(title), 'FILTERS': _filters(params, catalog), 'REGION_MAP': render_region_map(params, catalog['courts']),
                  'SORT_NAME': 'selected' if (selected(params, 'v_sort') or selected(params, 'sort')) != 'price' else '',
                  'SORT_PRICE': 'selected' if (selected(params, 'v_sort') or selected(params, 'sort')) == 'price' else '',
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
                query = {k: v[0] if isinstance(v, list) else v for k, v in params.items()}
                query['v_page'] = number
                pager.append(f'<a href="/venues?{escape(urlencode(query), quote=True)}">{label}</a>')
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
