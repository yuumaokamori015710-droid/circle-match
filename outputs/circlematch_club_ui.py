"""Public Club Edit presentation. No account, payment or reservation state."""
from hashlib import sha256
from html import escape
import json
from pathlib import Path
from urllib.parse import urlencode, urlparse, parse_qs

STATIC = Path(__file__).resolve().parent / 'club_static'
ICONS = json.loads((STATIC / 'icons.json').read_text(encoding='utf-8'))
SPORTS = (
    ('', 'すべて', 'other'), ('サッカー', 'サッカー', 'soccer'),
    ('フットサル', 'フットサル', 'futsal'), ('テニス', 'テニス', 'tennis'),
    ('バスケットボール', 'バスケ', 'basketball'), ('バレーボール', 'バレー', 'volleyball'),
    ('バドミントン', 'バドミントン', 'badminton'), ('野球', '野球', 'baseball'),
    ('卓球', '卓球', 'table-tennis'), ('ピックルボール', 'ピックルボール', 'pickleball'),
    ('ランニング', 'ランニング', 'running'), ('ゴルフ', 'ゴルフ', 'golf'),
    ('ラグビー', 'ラグビー', 'rugby'), ('ボードゲーム', 'ボードゲーム', 'board-games'),
    ('カラオケ', 'カラオケ', 'karaoke'), ('イベント', 'イベント', 'events'),
    ('その他', 'その他', 'other'),
)
ASSET_PATHS = {
    '/assets/club/' + path.name: (path, 'text/css; charset=utf-8' if path.suffix == '.css' else
        'application/javascript; charset=utf-8' if path.suffix == '.js' else 'image/webp')
    for path in STATIC.iterdir() if path.suffix in {'.css', '.js', '.webp'}
}


def icon(name):
    return ICONS[name]


def photo(sport):
    matches = [item for item in SPORTS[1:] if item[0] in (sport or '')]
    return matches[0][2] if matches else 'other'


def media(sport, *, detail=False):
    key = photo(sport)
    return (f'<figure class="club-event-photo{" club-detail-photo" if detail else ""}">'
            f'<img src="/assets/club/{key}.webp" alt="" width="960" height="540" '
            f'loading="{"eager" if detail else "lazy"}" decoding="async">'
            '<figcaption>競技イメージ</figcaption></figure>')


def sport_rail(params, tab='events'):
    current = params.get('sport', [''])[0]
    path = {'events': '/events', 'venues': '/venues', 'db': '/'}[tab]
    links = []
    choices = list(SPORTS)
    if tab == 'venues':
        # The verified venue catalog intentionally groups football and futsal.
        choices = [choices[0], ('サッカー・フットサル', 'サッカー・フットサル', 'soccer'), *choices[3:]]
    if current and current not in {item[0] for item in choices}:
        choices.insert(1, (current, current, photo(current)))
    for name, label, image in choices:
        shared_keys = {'region', 'prefecture', 'q', 'audience', 'date_from', 'date_to',
                       'event_type', 'participation', 'places', 'c_map', 'sort'}
        venue_keys = {'v_' + key for key in ('q', 'name', 'price_status', 'municipality', 'area',
            'map', 'places', 'operator_type', 'facility_kind', 'venue_type', 'booking_channel',
            'registration', 'open_from', 'open_until', 'price_max', 'sort', 'night_lighting',
            'indoor', 'show_suspended')}
        values = {key: value[0] for key, value in params.items() if value and key in shared_keys | venue_keys}
        if tab == 'db':
            values['tab'] = 'db'
        if name:
            values['sport'] = name
        href = path + ('?' + urlencode(values) if values else '')
        selected = ' aria-current="true"' if current == name else ''
        check = '<span class="club-sport-check">' + icon('check') + '</span>' if current == name else ''
        picture = (f'<img src="/assets/club/{image}-thumb.webp" alt="" width="156" height="140" loading="lazy">'
                   if name else icon('layout-grid'))
        links.append(f'<a data-directory-link class="club-sport" href="{escape(href, quote=True)}"{selected}>'
                     f'<span class="club-sport-photo">{picture}{check}</span><span>{escape(label)}</span></a>')
    return ('<section id="sports-list" class="club-sport-section" aria-labelledby="home-sports-heading">'
            '<div class="club-section-head"><h2 id="home-sports-heading">スポーツから探す</h2><div class="club-sport-tools">'
            '<button class="club-icon club-rail-arrow" type="button" data-rail-direction="-1" aria-label="前の競技" title="前の競技" hidden>' + icon('chevron-left') + '</button>'
            '<button class="club-icon club-rail-arrow" type="button" data-rail-direction="1" aria-label="次の競技" title="次の競技" hidden>' + icon('chevron-right') + '</button>'
            '<button class="club-all-sports" type="button" data-all-sports aria-expanded="false" aria-controls="clubSports" hidden>' + icon('layout-grid') + '一覧</button>'
            '</div></div><nav id="clubSports" class="club-sports" aria-label="スポーツを選ぶ">' + ''.join(links) + '</nav></section>')


def search(params):
    hidden = ''.join(f'<input type="hidden" name="{key}" value="{escape(params[key][0], quote=True)}">'
                     for key in ('sport', 'region', 'prefecture', 'event_type', 'date_from', 'date_to', 'participation') if params.get(key))
    return ('<form class="club-search" action="/events" role="search">' + hidden +
            '<label for="clubQuery" class="club-sr-only">大会名・会場・主催者を検索</label>' +
            icon('search') + '<input id="clubQuery" type="search" name="q" placeholder="大会名・会場・主催者で検索" '
            f'maxlength="200" value="{escape(params.get("q", [""])[0], quote=True)}">'
            '<button class="club-icon" aria-label="検索する" title="検索する">' + icon('arrow-right') + '</button></form>')


def decorate(body, request_path):
    page = body.decode('utf-8') if isinstance(body, bytes) else body
    signin = '<main class="signin-main">' in page
    if signin:
        page = page.replace('<body>', '<body class="cm-club">', 1)
    if '<body class="cm-club">' not in page:
        return body
    parsed = urlparse(request_path)
    params = parse_qs(parsed.query)
    shared = {key: params[key][0] for key in ('sport', 'region', 'prefecture') if params.get(key)}
    current = ('venues' if parsed.path.startswith(('/venues', '/tennis')) else
               'db' if params.get('tab') == ['db'] or parsed.path.startswith(('/circles', '/social')) else
               'account' if parsed.path.startswith(('/mypage', '/settings', '/notifications', '/invitations')) else 'events')
    links = []
    for key, label, symbol, path in (('events', '探す', 'search', '/events'),
            ('venues', '会場', 'map-pin', '/venues'), ('db', 'サークル', 'users', '/'),
            ('account', 'マイページ', 'user-round', '/mypage')):
        values = dict(shared) if key != 'account' else {}
        if key == 'venues' and values.get('sport') in {'サッカー', 'フットサル'}:
            values['sport'] = 'サッカー・フットサル'
        if key == 'db':
            values['tab'] = 'db'
        href = path + ('?' + urlencode(values) if values else '')
        active = ' aria-current="page"' if current == key else ''
        links.append(f'<a data-directory-link href="{escape(href, quote=True)}"{active}>' + icon(symbol) + f'<span>{label}</span></a>')
    page = page.replace('<nav class="main-nav">', '<nav class="club-top-links" aria-label="主要メニュー">' + ''.join(links[:3]) + '</nav><nav class="main-nav">', 1)
    if not signin:
        page = page.replace('</body>', '<nav class="club-bottom-nav" aria-label="主要メニュー">' + ''.join(links) + '</nav></body>', 1)
    resources = ''
    for name in ('styles.css', 'app.js'):
        path = STATIC / name
        url = f'/assets/club/{name}?v={sha256(path.read_bytes()).hexdigest()[:12]}'
        resources += f'<link rel="stylesheet" href="{url}">' if name.endswith('.css') else f'<script src="{url}" defer></script>'
    return page.replace('</head>', resources + '</head>', 1).encode('utf-8')
