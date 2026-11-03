"""Reviewed public guidance, source transparency, and conservative ad eligibility."""
from html import escape
from html.parser import HTMLParser
import json
from urllib.parse import parse_qs, urlencode, urlsplit


UPDATED = '2026-11-04'
SOURCE_LABELS = {'university_official': '大学公式掲載情報', 'self_registered': '団体登録情報'}
GUIDES = {
    'practice-match-how-to': {
        'title': '練習試合の組み方：会場・費用・雨天対応まで',
        'lead': '相手探しの前に、開催できる条件を決める。代表者同士で共有する順番と、初めてでも使える費用分担の例をまとめました。',
        'sections': [
            ('1. 変更できない条件を先に決める', [
                '競技、希望日時、人数、経験レベル、会場を確保済みかを一枚のメモにまとめます。「土日ならいつでも」ではなく、第一・第二候補と回答期限を決めると調整の往復を減らせます。',
                '試合形式、交代人数、審判・得点係、ボールやビブスの用意を分けて記載します。初心者を含む場合は、接触やプレー強度についても先にすり合わせます。']),
            ('2. 会場の条件と予算を確定する', [
                '貸切と個人開放は別です。団体登録、区内・区外の条件、営利利用や参加費徴収の可否を公式案内で確認します。予約名義を借りたり、登録条件を満たすように名簿を偽ったりしないでください。',
                '利用枠には準備・片付けが含まれる場合があります。2時間借りた会場で2時間の試合を組まず、受付、ウォームアップ、撤収の時間を差し引いて進行を作ります。',
                '以下は計算方法の例示で、実在施設の料金ではありません。会場6,000円＋照明1,000円＋用具1,000円＝8,000円なら、2チーム均等負担で各4,000円。各チーム8人なら1人500円です。人数が減った場合の負担も決めます。']),
            ('3. 候補団体に同じ条件を伝える', [
                '活動地域・競技・団体種別で候補を絞り、掲載元で現在の活動と窓口を確認します。DB掲載は代表者の本人確認や現在の募集を保証するものではありません。',
                '初回連絡には候補日時、場所、レベル、費用見込み、試合形式、返信期限を含めます。複数団体と調整中なら、その旨と確定の順序を明記し、重複して開催を約束しないようにします。']),
            ('4. 合意内容を記録してから開催を確定する', [
                '両者の代表連絡先、参加人数、集合場所、持ち物、費用の支払先・期限、キャンセル時の負担を書面やメッセージに残します。「予約できた」と「対戦相手が確定した」は分けて管理します。',
                '申込を集める場合は最低開催人数と開催判断の日時を決め、不成立時の扱いを募集に書きます。会場の取消料発生日より早く人数を判断できる日程が望ましいです。']),
            ('5. 雨天と人数不足の判断を分ける', [
                '雨天時は施設が使用中止と判断した場合と、主催者の都合で中止する場合で返金条件が異なることがあります。「雨なら必ず無料」とは扱わず、施設の公式規定を確認します。',
                '例示：当日朝8時に施設の判断を確認し、8時30分までに両代表から参加者へ連絡する。連絡が届かなかった人の確認方法も用意します。人数不足、対戦相手の辞退、交通機関の乱れは別の中止条件として整理します。']),
            ('6. 当日と終了後の確認', [
                '受付時にルール、緊急時の連絡、撮影可否、利用終了時刻を確認します。初参加者を含め、参加費と追加費用の有無を再確認してから始めます。',
                '終了後は清掃・備品返却と費用精算を行い、実費と集金額の差があれば扱いを共有します。写真や動画の公開は、撮影への同意とは別に確認してください。']),
        ],
    },
    'recruiting-template': {
        'title': '練習試合・個人参加・チーム参加の募集テンプレート',
        'lead': '参加者が判断するために必要なのは、日時だけでなく費用、成立条件、中止時の扱いです。用途別に埋められる募集文と確認事項を用意しました。',
        'sections': [
            ('練習試合・合同練習のテンプレート', [
                '【団体名】／【競技】／【候補日時】／【会場・最寄り駅】／【予約済み・調整中の別】／【試合形式・レベル】／【予定人数・交代要員】／【会場費・審判代などの負担】／【ボール・用具の担当】／【返信期限】／【連絡窓口】を記入します。',
                '「会場確保済み」と書けるのは予約内容を確認できているときだけです。未確保の場合は、相手が決まってから予約するのか、抽選結果を待つのかを書き分けます。']),
            ('個人参加とチーム参加を同時に受け付ける場合', [
                '【個人参加費：1人あたり○円】と【チーム参加費：1チームあたり○円】を分けます。チームの人数範囲、個人参加者のチーム分け、同伴者や見学者の扱いも記載してください。',
                '参加費に含む費用、現地払い・振込などの支払方法と支払期限、追加費用の有無を揃えます。申込受付、主催者承認、入金確認、参加確定は異なる段階なので、どの時点で枠が確保されるかも明記します。']),
            ('メンバー募集・体験参加のテンプレート', [
                '【活動地域・施設】／【曜日・頻度】／【対象者・競技レベル】／【1回の費用・月会費・初期費用】／【体験参加の可否】／【持ち物・貸出】／【申込から参加までの流れ】／【勧誘・営業活動への方針】を記入します。',
                '架空の参加人数、未確認の活動実績、本人の同意がない写真は掲載しません。年齢層や経験者割合も、確認できる範囲に限定し、分からない情報は未確認とします。']),
            ('募集文の末尾に加える開催条件', [
                '【最低開催人数・チーム数】／【開催判断日】／【定員・先着順・承認制】／【雨天判断の時刻と連絡方法】／【自己都合キャンセルの期限・負担】／【主催者中止時の返金方法・時期】を記入します。',
                '定員なしでも最低開催条件は別に決められます。参加者向けの取消条件と、主催者が施設へ負う取消料は同じとは限らないため、それぞれ確認します。']),
            ('公開前の読み合わせ', [
                '初めて読む人に「いつ・どこで・いくら・何をする・どう確定する・中止時はどうなる」を答えてもらいます。一つでも不明なら公開前に補います。',
                '公開後の日時・会場・費用の変更は、ページの修正だけで終えず、既に申し込んだ参加者にも知らせます。申込時の条件と変更後の条件を区別して保存してください。']),
        ],
    },
    'circle-database-guide': {
        'title': 'サークル選びの確認表：活動日・会費・出典を見比べる',
        'lead': '大学・社会人サークルの一覧は候補探しの入口です。公開情報で分かることと、参加前に団体へ確認することを分け、同名団体の取り違えも防ぎます。',
        'sections': [
            ('1. 通える範囲と参加条件で候補を絞る', [
                '競技と活動地域を決め、大学団体と社会人団体を切り替えて探します。大学の所在地と実際の練習場所は一致しない場合があるため、通学先だけで移動時間を判断しないでください。',
                '候補ごとに「活動日・集合時刻」「実際の会場」「初心者・経験者の条件」「学外参加の可否」「体験参加」「費用」の6項目をメモします。空欄は無料・参加可と解釈せず、未確認のまま残します。']),
            ('2. 出典の種類と日付を読む', [
                '大学公式掲載情報は大学の公開ページで団体情報を確認したこと、団体登録情報は団体側の申請情報、公開情報は公開サイト等を基にした情報であることを示します。これらは現在の活動や公認を保証する表示ではありません。',
                '掲載元の確認日は、DBで情報源を確認した日です。その日に練習を実施した、今も募集中である、料金が最新であるという意味ではありません。最新の投稿・公式案内を別途確認します。']),
            ('3. 同じ名前の団体を区別する', [
                '団体名だけでなく、大学・活動地域・競技・掲載元URLを照合します。別地域の同名団体、個人の投稿、プラットフォーム運営者の共通窓口を、その団体の連絡先と取り違えないようにします。',
                '掲載元が消えている、名称や活動内容が一致しない場合は、参加費を送る前に確認してください。対象の団体名とURLを添えて訂正を依頼できます。']),
            ('4. 総額で会費を比較する', [
                '入会金、年会費・月会費、1回の参加費、施設費、用具代、遠征費を分けます。「1回○円」だけでは、初回と継続参加の負担を比較できません。',
                '例示：月会費2,000円＋参加ごと500円で月4回なら4,000円です。毎回1,000円で月2回なら2,000円。これは計算例であり、掲載団体の実際の会費ではありません。']),
            ('5. 体験前に確認すること', [
                '活動日、集合場所、当日の責任者、持ち物、参加費の支払時期、欠席・中止時の扱いを公式窓口へ確認します。公開メールの掲載は営業連絡や一斉送信への同意を意味しません。',
                '必要のない身分証の画像や個人情報は送らず、問い合わせは団体の公式フォームや公開された用途に合う窓口を使います。見学時は施設の利用規則と撮影可否も確認してください。']),
            ('6. 掲載情報の限界と訂正', [
                'Circle Matchの掲載・出典・代表申請は、団体の公認、活動の安全性、参加受入れを保証しません。現在募集中か、誰が窓口かは参加前に確認してください。',
                '活動停止、名称変更、誤った競技分類、古い連絡先などを見つけた場合は、団体名、掲載元URL、訂正内容、確認できる公開根拠を添えてお問い合わせください。非公開情報を募集文に書く必要はありません。']),
        ],
    },
    'tokyo-venue-costs': {
        'title': '東京都の会場費を比較する：料金・登録・キャンセル',
        'lead': 'テニス、フットサル、体育館では「1時間」「2時間」「半面」「全面」の意味が違います。料金だけで並べず、利用条件と合計負担を同じ順序で確認します。',
        'sections': [
            ('比較の前に揃える5つの条件', [
                '①競技と使用する面数・部屋、②曜日と時間帯、③利用時間と準備・撤収、④区内外・会員などの利用区分、⑤照明・備品・登録料を揃えます。条件付きの最安値を、そのまま自分に適用される料金とは考えないでください。',
                '1面2時間と体育室半面3時間を無条件に1時間単価へ変換すると、予約できる単位や使用範囲が見えなくなります。以下では公式資料で確認した課金単位を保ち、異なる単位を合算・順位付けしません。']),
            ('テニスは照明と冬季の営業時間を確認する', [
                '昼間の使用料が安くても、夜間照明や希望時間帯の営業があるとは限りません。仕事後の参加なら、料金より先に利用終了時刻と予約枠を確認します。照明料金が別の場合は予約する時間分を加算します。',
                '駒沢の公式案内では冬季のテニス利用は16時30分まで、1面2時間2,900円です。夜の候補として扱わないことが重要です。制度・営業時間は改定されるため、利用日には公式案内を再確認してください。']),
            ('フットサルは会員料と指定時間枠を分ける', [
                'Bonfim落合南長崎は曜日・時間帯・メンバー／ビジターで料金が変わり、指定の1.5時間枠もあります。会員価格だけで予算を作らず、登録料を含む初回総額と継続利用を分けて検討します。大会・個サル開催には事前申請が必要です。',
                '参加費を集めるイベントでは通常の練習利用と条件が違う場合があります。会場が決まる前に、主催内容と料金徴収の扱いが施設の利用条件に合うか確認します。']),
            ('体育館は部屋・面積・団体区分を確認する', [
                '「体育館」と同じ施設名でも大体育室、小体育室、会議室、個人開放で料金も使える種目も異なります。バスケやバレーのコートが必要なら、部屋名・全面／半面・用具の貸出条件まで照合します。',
                '区外団体の登録可否、抽選への参加可否、空き枠受付の開始日は別の条件です。「登録できるから抽選も同じ」とは考えず、参加者名簿と当日の利用条件も確認します。']),
            ('取消料を含む予算の決め方', [
                'キャンセル条件が未確認の施設を「取消無料」と扱わないでください。無償取消の期限、以降の割合、雨天時の判断者、返金手続きと振込手数料を確認します。',
                '例示：会場代10,000円、用具代2,000円、予備費1,000円なら必要額は13,000円。10人で均等負担する場合は1人1,300円です。実際の料金ではなく計算例です。最低人数が集まらない場合に誰が取消料を負担するかも、申込受付前に決めます。']),
        ],
        'sources': [
            ('都立公園の施設・使用料金', 'https://www.tokyo-park.or.jp/park/sports/index.html'),
            ('駒沢テニスの利用時間・料金・申込', 'https://www.tef.or.jp/kopgp/tennis/'),
            ('Bonfim落合南長崎の料金・キャンセル条件', 'https://bonfim.co.jp/ochiai/court_price/'),
        ],
    },
}

COMPARISON_IDS = ('metro-sarue', 'metro-kiba', 'tef-komazawa-tennis',
                  'tokyo-sports-019', 'tokyo-gym-5074f6b079ec')

CSS = '''
.cm-public-footer{max-width:1180px;margin:28px auto 0;padding:24px 20px 32px;border-top:1px solid #bcc7be;display:block;font-size:13px;line-height:1.7;color:#536057;letter-spacing:0}
.cm-public-footer strong{display:block;color:inherit;font-size:16px}.cm-public-footer nav{display:flex;flex-wrap:wrap;gap:8px 20px;margin:12px 0}.cm-public-footer a{color:inherit;text-underline-offset:4px;overflow-wrap:anywhere}.cm-public-footer p{margin:8px 0;max-width:72ch}
.cm-reading{margin:28px 0;padding:24px 0;border-top:1px solid #bcc7be;border-bottom:1px solid #bcc7be}.cm-reading h2{font-size:21px;margin:0 0 16px}.cm-reading-list{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:20px}.cm-reading-item{min-width:0}.cm-reading-item a{display:block;font-size:17px;font-weight:800;line-height:1.6;text-underline-offset:4px}.cm-reading-item p{font-size:14px;line-height:1.8;margin:8px 0;color:#536057}
.cm-article{max-width:820px;margin:0 auto;line-height:1.95;overflow-wrap:anywhere}.cm-article h1{font-size:30px;line-height:1.5;margin:20px 0}.cm-article h2{font-size:22px;line-height:1.6;margin:36px 0 14px}.cm-article p,.cm-article li{font-size:16px}.cm-article li+li{margin-top:14px}.cm-article ul{padding-left:1.4em}.cm-article section,.cm-article h2[id]{scroll-margin-top:104px}.cm-article-meta{font-size:13px!important;color:#536057}.cm-article a{text-underline-offset:4px}.cm-article-toc{border-block:1px solid #bcc7be;padding:16px 0;margin:24px 0}.cm-article-toc a{display:block;padding:5px 0}.cm-guide-list{list-style:none;padding:0!important}.cm-guide-list li{padding:18px 0;border-bottom:1px solid #bcc7be}.cm-guide-list a{font-size:19px;font-weight:800}.cm-guide-list p{margin:6px 0}
.cm-comparison{margin:24px 0}.cm-venue-example{padding:20px 0;border-bottom:1px solid #bcc7be}.cm-venue-example h3{font-size:18px;line-height:1.6;margin:0 0 12px}.cm-venue-example dl{display:grid;grid-template-columns:100px minmax(0,1fr);gap:8px;margin:0}.cm-venue-example dt{font-weight:800;font-size:14px}.cm-venue-example dd{margin:0;font-size:14px}.cm-venue-example details{margin-top:12px}.cm-venue-example summary{cursor:pointer;font-weight:700;padding:8px 0}.cm-venue-example a{overflow-wrap:anywhere}.cm-venue-price{font-weight:800}.cm-empty-options{margin-top:16px;display:flex;gap:12px 20px;flex-wrap:wrap}.cm-source-note{display:block;margin-top:6px;font-size:12px;color:#536057;line-height:1.7}
.cm-club .cm-public-footer,.cm-club .cm-reading,.cm-club .cm-article{color:var(--ink)}.cm-club .cm-reading-item p,.cm-club .cm-article-meta,.cm-club .cm-source-note{color:var(--muted)}.cm-club .cm-public-footer,.cm-club .cm-reading,.cm-club .cm-article-toc,.cm-club .cm-guide-list li,.cm-club .cm-venue-example{border-color:var(--line)}
@media(max-width:699px){.cm-reading-list{grid-template-columns:1fr;gap:20px}.cm-article h1{font-size:25px}.cm-article h2{font-size:20px}.cm-public-footer{padding:20px 16px 100px}.cm-venue-example dl{grid-template-columns:88px minmax(0,1fr)}.cm-article-toc a{padding:7px 0}}
'''


def footer():
    links = [('/guides', '活動ガイド'), ('/operator', '運営者情報'),
             ('/about-data', '掲載・編集方針'), ('/contact', 'お問い合わせ・訂正'),
             ('/terms', '利用規約'), ('/privacy', 'プライバシー')]
    return ('<footer id="cm-public-footer" class="cm-public-footer"><strong>Circle Match</strong>'
            '<nav aria-label="サイト情報">' + ''.join(f'<a href="{url}">{label}</a>' for url, label in links)
            + '</nav><p>掲載情報は確認時点の情報です。参加・予約前に、主催者や施設の公式案内で最新条件をご確認ください。</p></footer>')


class FooterBounds(HTMLParser):
    def __init__(self, page):
        super().__init__()
        self.offsets, self.start, self.end = [0], None, None
        # HTMLParser counts LF only, not CR or Unicode paragraph separators.
        for line in page.split('\n')[:-1]:
            self.offsets.append(self.offsets[-1] + len(line) + 1)
        self.feed(page)

    def position(self):
        line, column = self.getpos()
        return self.offsets[line - 1] + column

    def handle_starttag(self, tag, attrs):
        if tag == 'footer' and self.start is None:
            self.start = self.position()

    def handle_endtag(self, tag):
        if tag == 'footer' and self.start is not None and self.end is None:
            self.end = self.position() + len('</footer>')


def decorate(body, request_path, status=200):
    page = body.decode('utf-8') if isinstance(body, bytes) else body
    path = urlsplit(request_path).path
    public = path in {'/', '/events', '/venues', '/tennis', '/circles', '/social', '/social/circles',
                      '/signin', '/settings', '/guides', '/privacy', '/terms', '/operator', '/about-data', '/contact'}
    public = public or (path.startswith('/guides/') or (path.startswith('/events/') and len(path.split('/')) == 3 and path != '/events/new'))
    if status != 200 or not public:
        return body
    if 'id="cm-public-footer"' not in page:
        bounds = FooterBounds(page)
        if bounds.start is not None and bounds.end is not None:
            page = page[:bounds.start] + footer() + page[bounds.end:]
        else:
            page = page.replace('</body>', footer() + '</body>', 1)
    return page.replace('</head>', '<style id="cm-content-style">' + CSS + '</style>' + source_note_script() + '</head>', 1).encode('utf-8')


def reading_links():
    items = [('tokyo-venue-costs', '会場費・登録条件を比較する'),
             ('practice-match-how-to', '練習試合の準備を進める'),
             ('circle-database-guide', '参加前の確認項目を揃える')]
    return ('<section class="cm-reading" aria-labelledby="cm-reading-title"><h2 id="cm-reading-title">会場選び・活動ガイド</h2>'
            '<div class="cm-reading-list">' + ''.join(
                f'<article class="cm-reading-item"><a href="/guides/{slug}">{label}</a><p>{escape(GUIDES[slug]["lead"])}</p></article>'
                for slug, label in items) + '</div></section>')


def empty_options(params):
    context = {key: params[key][0] for key in ('sport', 'region', 'prefecture') if params.get(key) and params[key][0]}
    venue_context = dict(context)
    if venue_context.get('sport') in {'サッカー', 'フットサル'}:
        venue_context['sport'] = 'サッカー・フットサル'
    venue = '/venues' + ('?' + urlencode(venue_context) if venue_context else '')
    db = '/?' + urlencode({**context, 'tab': 'db', 'audience': 'university'})
    return ('<div class="cm-empty-options"><a href="' + escape(venue, quote=True) + '">この競技の会場を探す</a>'
            '<a href="' + escape(db, quote=True) + '">この競技の団体を探す</a>'
            '<a href="/guides/practice-match-how-to">練習試合の組み方を読む</a></div>')


def source_note(circle):
    label = SOURCE_LABELS.get(circle.get('source_type'), '公開掲載情報')
    date = str(circle.get('last_checked_at') or '')[:10]
    checked = escape(date) if date else '未確認'
    return ('<small class="cm-source-note">' + label + ' / 掲載元の確認日：' + checked
            + '<br>活動日・会費・募集中かは掲載元で確認</small>')


def source_note_script():
    labels = json.dumps(SOURCE_LABELS, ensure_ascii=False)
    return r'''<script>function sourceNote(c){const e=v=>String(v??'').replace(/[&<>"']/g,x=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#039;'}[x]));const label=(__LABELS__)[c.source_type]||'公開掲載情報';return `<small class="cm-source-note">${label} / 掲載元の確認日：${e(String(c.last_checked_at||'').slice(0,10)||'未確認')}<br>活動日・会費・募集中かは掲載元で確認</small>`}</script>'''.replace('__LABELS__', labels)


def comparison(catalog):
    rows = {row['id']: row for row in catalog['courts']}
    rendered = []
    for ident in COMPARISON_IDS:
        row = rows.get(ident)
        if not row or row.get('availability_status') == 'SUSPENDED':
            continue
        ranges = row.get('fee_ranges') or []
        prices = []
        for bounds in ranges:
            amount = f'{bounds["minimum"]:,}円'
            if bounds['maximum'] != bounds['minimum']:
                amount += f'〜{bounds["maximum"]:,}円'
            prices.append('<div><span class="cm-venue-price">' + amount + '</span> / ' + escape(bounds['unit']) + '</div>')
        plans = row.get('fee_options') or []
        conditions = list(dict.fromkeys(plan['conditions'] for plan in plans))
        conditions = conditions or [row.get('price_note') or '適用条件は公式案内で確認してください。']
        sources = {plan['source_url']: '公式料金表' for plan in plans}
        for source in row.get('sources', []):
            sources.setdefault(source['url'], source['title'])
        links = ''.join('<li><a href="' + escape(url, quote=True) + '" target="_blank" rel="noopener noreferrer">' + escape(label) + '</a></li>' for url, label in sources.items())
        policy = row.get('cancellation')
        cancel = (escape(policy['summary']) + '（確認日 ' + escape(policy['checked_at']) + '）<a href="'
                  + escape(policy['source_url'], quote=True) + '" target="_blank" rel="noopener noreferrer">公式取消規定</a>') if policy else '未確認。予約前に公式の取消期限・返金条件をご確認ください。'
        registration = {True: '登録が必要（区内外・抽選条件は別途確認）', False: '登録不要（確認済み条件の範囲）', None: '下記利用条件・公式案内で確認'}[row.get('registration_required')]
        target = '/venues?' + urlencode({'v_q': row['name']}) + '#venue-court-results'
        rendered.append('<section class="cm-venue-example"><h3>' + escape(row['name']) + '</h3><dl><dt>確認済み料金</dt><dd>'
                        + (''.join(prices) or '金額未確認') + '</dd><dt>料金確認日</dt><dd>' + escape(row.get('fee_checked_at') or row['checked_at'])
                        + '</dd><dt>適用条件</dt><dd>' + '<br>'.join(escape(item) for item in conditions) + '</dd><dt>利用登録</dt><dd>'
                        + registration + '</dd><dt>利用条件</dt><dd>' + escape(row.get('booking_note') or '未確認')
                        + '</dd><dt>条件確認日</dt><dd>' + escape(row['checked_at'])
                        + '</dd><dt>キャンセル</dt><dd>' + cancel + '</dd></dl><details><summary>料金区分・公式出典</summary><ul>'
                        + ''.join('<li>' + escape(plan['label']) + '：' + f'{plan["amount"]:,}円 / ' + escape(plan['unit']) + '</li>' for plan in plans)
                        + links + '</ul></details><p><a href="' + escape(target, quote=True) + '">施設の詳細・公式予約先を確認</a></p></section>')
    if not rendered:
        return '<p class="error-box" role="status">公開中の比較例を取得できませんでした。会場一覧で最新情報をご確認ください。</p>'
    return ('<section class="cm-comparison" aria-labelledby="comparison-heading"><h2 id="comparison-heading">条件の違いを見比べる' + str(len(rendered)) + '施設</h2>'
            '<p>編集上の比較例で、安い順のランキングではありません。カタログの確認済み料金を参照し、空き状況や利用可否は保証しません。料金区分と適用条件を開いて確認できます。</p>'
            + ''.join(rendered) + '</section>')


class AdSignals(HTMLParser):
    def __init__(self, page):
        super().__init__()
        self.indexable = False
        self.classes = set()
        self.feed(page)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        self.classes.update(attrs.get('class', '').split())
        if tag == 'meta' and attrs.get('name') == 'robots':
            self.indexable = attrs.get('content', '').startswith('index,')


def apply_ad_policy(body, request_path, status, loader, event=None):
    page = body.decode('utf-8') if isinstance(body, bytes) else body
    if not loader or loader not in page:
        return body
    parsed = urlsplit(request_path)
    params = parse_qs(parsed.query)
    path = parsed.path
    signals = AdSignals(page)
    home = path == '/' and not params.get('tab') and not params.get('sport')
    article = path.startswith('/guides/') and path.removeprefix('/guides/') in GUIDES and 'cm-article' in signals.classes
    public_event = event is not None and event.get('status') == 'published' and event.get('visibility', 'public') == 'public'
    # Search results can become empty in-place, after the initial HTTP response.
    allowed = status == 200 and signals.indexable and (home or article or public_event)
    if not allowed or 'error-box' in signals.classes:
        page = page.replace(loader, '')
    return page.encode('utf-8')
