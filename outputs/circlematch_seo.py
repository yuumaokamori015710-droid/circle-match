"""Public-page metadata. Never derives origins or private data from request headers."""
import html
import json
import re
from datetime import datetime, timezone, timedelta
from html.parser import HTMLParser
from urllib.parse import parse_qs, quote, urlencode, urlsplit


class HeadParser(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.output, self.title = [], []
        self.in_title = False

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == 'title':
            self.in_title = True
            return
        if tag == 'meta' and (values.get('name', '').lower() in {'description', 'robots'}
                or values.get('property', '').startswith('og:')
                or values.get('name', '').startswith('twitter:')):
            return
        if tag == 'link' and values.get('rel', '').lower() == 'canonical':
            return
        self.output.append(self.get_starttag_text())

    def handle_startendtag(self, tag, attrs):
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag):
        if tag == 'title':
            self.in_title = False
        elif not self.in_title:
            self.output.append(f'</{tag}>')

    def handle_data(self, data):
        (self.title if self.in_title else self.output).append(data)

    def handle_entityref(self, name):
        self.handle_data(f'&{name};')

    def handle_charref(self, name):
        self.handle_data(f'&#{name};')

    def handle_comment(self, data):
        self.output.append(f'<!--{data}-->')

    def handle_decl(self, decl):
        self.output.append(f'<!{decl}>')


class VisibleText(HTMLParser):
    def __init__(self):
        super().__init__()
        self.hidden = 0
        self.parts = []

    def handle_starttag(self, tag, attrs):
        if tag in {'script', 'style'}:
            self.hidden += 1

    def handle_endtag(self, tag):
        if tag in {'script', 'style'}:
            self.hidden = max(0, self.hidden - 1)

    def handle_data(self, data):
        if not self.hidden:
            self.parts.append(data)


def public_origin(configured):
    parsed = urlsplit(configured or '')
    if parsed.scheme in {'https', 'http'} and parsed.netloc and not parsed.username and not parsed.password:
        return f'{parsed.scheme}://{parsed.netloc}'
    return 'https://circle-match.jp'


def json_ld(data):
    return '<script type="application/ld+json">' + json.dumps(
        data, ensure_ascii=False, allow_nan=False).replace('<', '\\u003c').replace('>', '\\u003e').replace('&', '\\u0026') + '</script>'


def apply_metadata(body, request_path, configured_origin, sports, regions, status=200, event=None):
    """Decorate the rendered head, without changing body, forms or scripts."""
    text = body.decode('utf-8') if isinstance(body, bytes) else body
    head, separator, rest = text.partition('</head>')
    if not separator:
        return text.encode('utf-8')
    parser = HeadParser()
    parser.feed(head)
    parsed = urlsplit(request_path)
    path, params = parsed.path, parse_qs(parsed.query)
    value = lambda name: params.get(name, [''])[0].strip()
    origin = public_origin(configured_origin)
    visible_parser = VisibleText()
    visible_parser.feed(rest)
    visible = ''.join(visible_parser.parts)
    title = html.unescape(''.join(parser.title)).strip() or 'Circle Match'
    description = 'Circle Matchでスポーツの大会・イベント、大学・社会人サークルの情報を探せます。開催日時・会場・参加条件を確認して参加できます。'
    public = path in {'/', '/events', '/circles', '/social', '/social/circles', '/sports', '/social/sports', '/regions', '/guides', '/operator', '/privacy', '/terms', '/about-data', '/contact'}
    public = public or bool(re.fullmatch(r'/(events|circles|guides)/[^/]+', path) and path != '/events/new')
    canonical_params = {}
    image = origin + '/assets/hero-court.png'
    listing = path in {'/', '/events'}
    if listing:
        db = path == '/' and value('tab') == 'db'
        audience = 'social' if value('audience') == 'social' else 'university'
        sport = value('sport')
        region = regions.get(value('region'), {}).get('label', '')
        prefecture = value('prefecture')
        area = prefecture or region
        category = ('社会人サークルDB' if audience == 'social' else '大学サークルDB') if db else '大会・イベント'
        title = f'{area + "の" if area else ""}{sport + "の" if sport else ""}{category}を探す | Circle Match'
        description = f'{area or "全国"}の{sport or "スポーツ"}の{category}を掲載。' + ('団体名・活動地域・競技・出典を確認して、活動仲間や交流相手を探せます。' if db else '開催日時・会場・参加費・参加条件を確認して、募集詳細から参加を申し込めます。')
        if db:
            canonical_params.update(tab='db', audience=audience)
        for key in ('sport', 'region', 'prefecture', 'page'):
            if value(key):
                canonical_params[key] = value(key)
        allowed = {'sport', 'region', 'prefecture', 'page', 'tab', 'audience', 'utm_source', 'utm_medium', 'utm_campaign', 'utm_content', 'utm_term', 'gclid', 'fbclid'}
        if any(key not in allowed for key in params):
            public = False
        if sport and sport not in sports or value('region') and value('region') not in regions:
            public = False
        if any(len(values) != 1 for values in params.values()):
            public = False
        if value('page') and (not value('page').isdigit() or not 1 <= int(value('page')) <= 10000):
            public = False
        if canonical_params and (re.search(r'(?<!\d)0件を表示', visible) or '条件に合う団体はありません' in visible):
            public = False
        if '取得できませんでした' in visible:
            public = False
        if sport in sports:
            image = origin + '/assets/sports/' + sports[sport]
    elif path in {'/circles', '/social/circles', '/social'}:
        audience = '社会人' if path.startswith('/social') else '大学'
        title = f'{audience}サークルDB・団体一覧 | Circle Match'
        description = f'{audience}サークルの団体名・競技・活動地域・公開情報の出典を確認できます。競技や地域、団体名で検索して交流相手を探せます。'
        # Legacy pages filter in JavaScript; don't claim filtered SSR content.
        if params:
            public = False
    elif path in {'/sports', '/social/sports', '/regions'}:
        # These legacy pages cannot yet expose their filtered records without JS.
        public = False
    elif params:
        public = False
    if listing and path == '/' and value('tab') != 'db' and value('sport'):
        path = '/events'
    descriptions = {
        '/guides':'サークル活動や大会・イベントへの参加、練習試合の準備に役立つガイドを掲載しています。',
        '/about-data':'Circle MatchのサークルDBの収集元・掲載基準・更新方法と、情報の訂正・削除依頼についてご案内します。',
        '/operator':'Circle Matchの運営者情報と連絡窓口をご案内します。',
        '/contact':'Circle Matchへのお問い合わせ、掲載情報の訂正・削除、ご意見・ご要望はこちらからご連絡ください。',
        '/privacy':'Circle Matchにおける個人情報、Cookie、アクセス解析、広告の取り扱いについてご案内します。',
        '/terms':'Circle Matchの利用条件と、イベント掲載・参加申込にあたっての注意事項をご案内します。',
    }
    description = descriptions.get(path, description)
    if event:
        title = f'{event.get("title") or "大会・イベント"} | Circle Match'
        description = ' '.join(str(event.get(key) or '') for key in ('sport_category', 'starts_at', 'prefecture', 'location', 'description'))[:160]
        if event.get('visibility', 'public') != 'public':
            public = False
    canonical = origin + path + ('?' + urlencode(canonical_params) if canonical_params else '')
    robots = 'index, follow, max-image-preview:large' if public and status == 200 else 'noindex, follow'
    escape = lambda v: html.escape(str(v), quote=True)
    tags = [f'<title>{escape(title)}</title>', f'<meta name="description" content="{escape(description)}">',
            f'<meta name="robots" content="{robots}">', f'<link rel="canonical" href="{escape(canonical)}">']
    for key, content in {'type':'website', 'site_name':'Circle Match', 'locale':'ja_JP', 'title':title, 'description':description, 'url':canonical, 'image':image}.items():
        tags.append(f'<meta property="og:{key}" content="{escape(content)}">')
    tags.extend([f'<meta name="twitter:card" content="summary_large_image">', f'<meta name="twitter:title" content="{escape(title)}">', f'<meta name="twitter:description" content="{escape(description)}">', f'<meta name="twitter:image" content="{escape(image)}">'])
    if path == '/' and not canonical_params and public and robots.startswith('index'):
        tags.append(json_ld({'@context':'https://schema.org', '@type':'WebSite', 'name':'Circle Match', 'url':origin + '/', 'inLanguage':'ja'}))
    if event and public and status == 200:
        tags.append(event_schema(event, configured_origin))
    return (''.join(parser.output) + '\n' + '\n'.join(tags) + separator + rest).encode('utf-8')


def event_schema(event, configured_origin):
    """Only participant-visible facts, with no bank details, emails or host revenue."""
    if event.get('status') not in {'published', 'closed', 'cancelled'} or event.get('visibility', 'public') != 'public':
        return ''
    def date(value):
        if not value:
            return None
        try:
            dt = datetime.fromisoformat(value)
            return (dt if dt.tzinfo else dt.replace(tzinfo=timezone(timedelta(hours=9)))).isoformat()
        except ValueError:
            return None
    start = date(event.get('starts_at'))
    if not start or not event.get('title') or not event.get('location'):
        return ''
    url = public_origin(configured_origin) + '/events/' + quote(str(event['event_id']), safe='')
    data = {'@context':'https://schema.org', '@type':'Event', 'name':event['title'], 'url':url,
            'startDate':start, 'description':event.get('description') or '',
            'eventStatus':'https://schema.org/EventCancelled' if event.get('status') == 'cancelled' else 'https://schema.org/EventScheduled',
            'eventAttendanceMode':'https://schema.org/OfflineEventAttendanceMode',
            'location':{'@type':'Place', 'name':event['location'], 'address':{'@type':'PostalAddress', 'addressRegion':event.get('prefecture') or '', 'addressCountry':'JP'}}}
    if date(event.get('ends_at')):
        data['endDate'] = date(event['ends_at'])
    if event.get('organizer_name'):
        data['organizer'] = {'@type':'Organization' if event.get('linked_circle_name') else 'Person', 'name':event.get('linked_circle_name') or event['organizer_name']}
    # No fictitious venue address, event photo, performer or offer is synthesized.
    return json_ld(data)
