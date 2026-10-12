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
else:
    from venues.tennis_catalog import get_catalog
    from venues.sports_catalog import get_catalog as get_venue_catalog, supports_catalog, filter_catalog, selected, SPORTS
    from venues.search_facets import VENUE_TYPES, CHANNELS


VENUE_DIR = Path(__file__).resolve().parent / "venues"
VENUE_CSS_URL = "/assets/venues/tennis.css"
VENUE_JS_URL = "/assets/venues/tennis.js"
ASSET_PATHS = {
    VENUE_CSS_URL: (VENUE_DIR / "static" / "tennis.css", "text/css; charset=utf-8"),
    VENUE_JS_URL: (VENUE_DIR / "static" / "tennis.js", "application/javascript; charset=utf-8"),
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
    badges = ''.join(f'<li>{escape(s)}</li>' for s in row['sports'])
    amount = lambda value: f'<span class="venue-price-amount">{value:,}円</span>'
    if row['price_from'] is None:
        price = '<span class="venue-unconfirmed">料金は要確認</span>'
    elif row.get('price_to') == row['price_from']:
        price = amount(row['price_from'])
    elif row.get('price_to') is not None:
        price = amount(row['price_from']) + f'<span class="venue-price-amount"><small>〜</small>{row["price_to"]:,}円</span>'
    else:
        price = f'<span class="venue-price-amount">¥{row["price_from"]:,}<small>〜</small></span>'
    fee_source = next((s for s in row['sources'] if '公式料金表' in s['title']), None)
    fee_link = _link(fee_source['url'], '公式料金表', 'venue-fee-link') if fee_source and row['price_from'] is not None else ''
    sources = ''.join('<li>' + _link(s['url'], s['title']) + '</li>' for s in row['sources'])
    booking = _link(row['official_url'] if suspended else row['booking_url'],
                    '公式の営業案内' if suspended else '予約先・利用条件を確認', 'venue-primary-link')
    create_url = '/events/new?' + urlencode({'venue': row['id'], 'sport': sport or row['sports'][0], 'prefecture': '東京都'})
    create = '' if suspended else f'<a class="venue-secondary-link" href="{escape(create_url, quote=True)}">この会場で募集を作る</a>'
    official = '' if suspended or row['booking_url'] == row['official_url'] else _link(row['official_url'], '公式案内')
    warning = f'<p class="venue-availability-note">休止中：{e("availability_note")}</p>' if suspended else ''
    registration = {True: '利用者登録が必要', False: '利用者登録は不要', None: '利用者登録の要否は未確認'}[row.get('registration_required')]
    hours = (e('opening_hours') + ' ' + e('opening_note')) if row.get('opening_hours') else '利用時間は未確認'
    hours_link = _link(row['official_url'], '利用時間の公式案内') if row.get('opening_hours') else ''
    return f'''<article class="venue-court-card" aria-labelledby="venue-court-title-{index}">
<div class="venue-court-main"><div class="venue-court-location"><span class="venue-operator-badge">{'公営' if row['operator_type'] == 'PUBLIC' else '民営'}</span><span>{e('municipality')} · {e('facility_label')}</span></div><h3 id="venue-court-title-{index}">{e('name')}</h3>{warning}<p class="venue-court-address">{e('address')}</p><ul class="venue-court-features">{badges}</ul></div>
<div class="venue-court-price"><p class="venue-column-label">掲載の参考料金</p><p class="venue-original-price">{price}</p><p class="venue-price-unit">{e('price_unit')}</p>{fee_link}<p class="venue-court-note">{e('price_note')}</p></div>
<div class="venue-court-booking"><p class="venue-column-label">予約方法</p><p class="venue-booking-method">{e('booking_method')}</p><p class="venue-registration">{registration}</p><p class="venue-court-note">{e('booking_note')}</p><div class="venue-court-links">{booking}{official}{create}</div></div>
<p class="venue-opening-hours"><strong>通常利用時間</strong> {hours} {hours_link}</p>
<details class="venue-court-details"><summary>施設情報・根拠を確認</summary><div class="venue-detail-content"><dl><dt>運営</dt><dd>{e('operator')}</dd><dt>情報確認日</dt><dd>{e('checked_at')}</dd></dl><ul class="venue-source-list">{sources}</ul></div></details></article>'''


def _filters(params, catalog):
    def value(key):
        return selected(params, 'v_' + key) if 'v_' + key in params else selected(params, key)
    def select(name, label, options, ident=''):
        items = ''.join(f'<option value="{escape(v, quote=True)}"' + (' selected' if value(name) == v else '') + f'>{escape(text)}</option>' for v, text in options)
        return f'<label><span>{label}</span><select name="{name}" id="{ident}">{items}</select></label>'
    fields = '<label class="venue-search-field"><span>キーワード</span><input name="q" type="search" placeholder="施設名、エリア、住所など" maxlength="200" value="' + escape(value('q')[:200], quote=True) + '"></label>'
    fields += select('area', 'エリア', [('', '都内すべて'), ('23区', '23区'), ('多摩', '多摩'), ('島しょ', '島しょ')], 'venue-area-filter')
    municipalities = catalog['meta']['municipalities_by_area'].get(value('area'), catalog['meta']['municipalities'])
    fields += select('municipality', '自治体', [('', 'すべての自治体')] + [(m, m) for m in municipalities], 'venue-municipality-filter')
    fields += select('venue_type', '施設の種類', [('', 'すべての種類')] + list(VENUE_TYPES))
    fields += select('operator_type', '運営', [('', '公営・民営すべて'), ('PUBLIC', '公営'), ('PRIVATE', '民営')])
    fields += select('booking_channel', '予約方法', [('', 'すべての予約方法')] + list(CHANNELS) + [('unknown', '予約方法は未確認')])
    fields += select('registration', '施設の利用者登録', [('', '登録条件すべて'), ('required', '必要（確認済み）'), ('not_required', '不要（確認済み）'), ('unknown', '要否は未確認')])
    fields += '<label><span>料金上限 <small>コート1面・1時間換算</small></span><div class="venue-price-input"><input name="price_max" type="text" inputmode="numeric" maxlength="12" placeholder="例：3000" value="' + escape(value('price_max'), quote=True) + '"><span>円</span></div></label>'
    for key, label in [('open_from', '利用開始時刻'), ('open_until', '利用終了時刻')]:
        fields += f'<label><span>{label}</span><input type="time" name="{key}" value="{escape(value(key), quote=True)}"></label>'
    toggles = ''.join(f'<label class="venue-checkbox-label"><input name="{key}" type="checkbox" value="1"' + (' checked' if value(key) in {'1', 'true', 'on'} else '') + f'><span>{label}</span></label>' for key, label in [('night_lighting', '夜間照明あり'), ('indoor', '屋内施設あり'), ('show_suspended', '休止中の施設も表示')])
    context = ''.join(f'<input type="hidden" name="{key}" value="{escape(selected(params, key), quote=True)}">' for key in ('sport', 'region', 'prefecture') if selected(params, key))
    context += f'<input type="hidden" name="facility_kind" value="{escape(value("facility_kind"), quote=True)}">'
    return context + f'<fieldset id="venue-filter-fields"><legend class="venue-visually-hidden">会場の絞り込み条件</legend><div class="venue-filter-grid">{fields}</div><div class="venue-filter-options">{toggles}</div></fieldset><button class="venue-apply" type="submit">条件を適用</button>'


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
        values = {'TITLE': escape(title), 'FILTERS': _filters(params, catalog),
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
