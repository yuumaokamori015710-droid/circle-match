"""Append November 6 official tariffs; keep uncertain eligibility and prices unknown."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'outputs'))
from venues.fees import validate
from venues.sports_catalog import get_catalog, has_price
from record_venue_fee_review_20261018 import append_reviews, entry as old_entry

CHECKED = '2026-11-06'
BASE = '9ef2bbeee940bac1418379dbb776fdffa7347c27'
CATALOGS = ROOT / 'outputs/venues/catalogs'
TACHI = 'https://www.city.tachikawa.lg.jp/'
TACHI_FEES = TACHI + '_res/projects/default_project/_page_/001/008/085/tebiki_20260801.pdf'
TACHI_CANCEL = TACHI + 'kanko/sports/1002923/1002944/1025596.html'
JIJI = 'tokyo-venue-8a29b57a2a95'
TACHIKAWA = [JIJI, 'tachikawa-izumi', 'tachikawa-sunagawa', 'tachikawa-nishisuna', 'tachikawa-nishiki']
MUSA = 'https://musashimurayama-gym.jp/'
MUSA_FEES = MUSA + 'news/info/5717'
MUSA_GUIDE = MUSA + 'sports-facilities/tennis'
MUSASHI = ['musashimurayama-ominami', 'musashimurayama-kaminarizuka', 'musashimurayama-mitsugi']
FUSSA_BASE = 'https://www.city.fussa.tokyo.jp/map/sports/'
FUSSA = [('fussa-sdfield', '1001680.html', 500, True), ('fussa-minami', '1001670.html', 500, False),
         ('fussa-musashinodai', '1001677.html', 800, True), ('fussa-fukuto', '1001666.html', 800, False)]
HINO_FEES = 'https://hino-playground.com/facility/tennis'
HINO_CHANGE = 'https://www.city.hino.lg.jp/shisetsu/sports/1032278.html'
HINO_CANCEL = 'https://www.city.hino.lg.jp/bunka/yoyaku/1007380.html'
HINO = ['hino-tamadaira', 'hino-asahigaoka', 'hino-nanao']
KIYOSE_BASE = 'https://www.city.kiyose.lg.jp/shisetsu/riyouyoyaku/'
KIYOSE = ['kiyose-uchiyama', 'kiyose-chuo', 'kiyose-shimokiyoto', 'kiyose-himawari']
MITAKA_BASE = 'https://mitaka-sportsandculture.or.jp/zaidan/other/'
MITAKA_REGISTER = 'https://www.mitakagenki-plaza.jp/sports/dantai_20260223101459.html'
MITAKA = [('mitaka-osawa', 'ground/', 1500), ('mitaka-shinkawa', 'tennis/', 700),
          ('mitaka-nogawa', 'ground/nogawa.html', 700)]
CLOSED = 'mitaka-nogawa'
CLOSURE_NOTE = ('大雨による冠水・復旧作業のためテニスコート全4面を当面使用中止。'
                '2026年11月6日に市と指定管理者の休止告知を確認。再開日未確認のため通常検索から除外。')
CLOSURE_EVIDENCE = {'title': '大沢野川グラウンド・冠水による使用中止（2026年11月6日確認）',
                    'url': MITAKA_BASE + 'ground/nogawa.html'}
HOLDS = ['tokyo-venue-2b0bbd7157ff', 'tokyo-venue-c282bded258a', 'tokyo-venue-205d87234dd3',
         'tokyo-gym-a231878afdcf', MUSASHI[2]]
REVIEWED_IDS = TACHIKAWA + MUSASHI + [r[0] for r in FUSSA] + HINO + KIYOSE + [r[0] for r in MITAKA] + HOLDS[:4]


def entry(ident, source, note, rows):
    return dict(old_entry(ident, source, note, rows), checked_at=CHECKED)


def reviewed_fees():
    result = []
    for ident in TACHIKAWA:
        if ident == JIJI:
            note = ('自治大学校専用登録をした市内在住・在勤・在学の5人以上の団体のみ。土曜9～17時の1面2時間。'
                    '市外料金・一般個人利用を推測しません。現金の支払場所・期限は施設別案内を確認。'
                    '不特定多数への参加費付き募集は営利のおそれとしてペナルティ対象。' + TACHI_CANCEL)
            rows = [('市内登録団体・基本料金', 800, 'テニスコート1面・2時間（市内登録団体）')]
        elif ident in ('tachikawa-sunagawa', 'tachikawa-nishisuna'):
            note = ('市内個人専用のクレーコート1面2時間。現地当日払い。市外向け料金を推測しません。'
                    '11～3月は10～16時。事前登録・予約が必要。参加費付き一般公募等の制限は' + TACHI_CANCEL)
            rows = [('市内登録個人・基本料金', 100, 'テニスコート1面・2時間（市内登録個人）')]
        else:
            note = ('1面2時間の基本料金。登録・予約が必要で現地当日払い。市内・市外を別の課金区分として表示。'
                    '17～19時内の照明加算は1面1時間につき市内700円・市外1400円、19～21時の2時間分は市内1400円・市外2800円。'
                    '照明加算だけをコートの最安値にせず、錦町フットサル料金とも分離。'
                    '参加費付き不特定多数の募集は営利のおそれとして制限されるため商用利用の許可を意味しません。' + TACHI_CANCEL)
            rows = [('市内・基本料金（照明別）', 800, 'テニスコート1面・2時間（市内・照明別）'),
                    ('市外・基本料金（照明別）', 1600, 'テニスコート1面・2時間（市外・照明別）')]
        result.append(entry(ident, TACHI_FEES, note, rows))
    for ident in MUSASHI[:2]:
        note = ('2026年7月1日利用分からの改定料金。登録団体のコート1面2時間と、4・5・9・10月の17～18時だけの1時間枠を分離。'
                '市内・市外を混ぜず、旧640円を採用しません。営利目的利用不可。利用方法・返還：' + MUSA_GUIDE)
        result.append(entry(ident, MUSA_FEES, note, [
            ('市内・通常枠', 1020, 'テニスコート1面・2時間（市内登録団体）'),
            ('市外・通常枠', 2040, 'テニスコート1面・2時間（市外登録団体）'),
            ('市内・4/5/9/10月17～18時', 510, 'テニスコート1面・1時間（市内登録団体・季節限定）'),
            ('市外・4/5/9/10月17～18時', 1020, 'テニスコート1面・1時間（市外登録団体・季節限定）')]))
    for ident, slug, amount, lit in FUSSA:
        note = ('テニスコート1面1時間の基本料金。市内・市外を別区分で表示。事前利用者登録・施設窓口への申請と審査が必要。'
                '取消期限・取消料・天候時の還付は今回の取得範囲では未確認。予約方法：'
                'https://www.city.fussa.tokyo.jp/1021105/index.html')
        if lit:
            note += '照明は別途1面1時間・市内1000円、市外3000円。'
        if ident == 'fussa-musashinodai':
            note += 'フットサルはテニス2面分・窓口予約のみで別料金のため、このテニス料金へ混ぜません。'
        result.append(entry(ident, FUSSA_BASE + slug, note, [
            ('市内・基本料金', amount, 'テニスコート1面・1時間（市内・照明別）'),
            ('市外・基本料金', amount * 3, 'テニスコート1面・1時間（市外・照明別）')]))
    for ident in HINO:
        note = ('登録個人の通常貸切基本料金。市内外の登録・予約時期は別条件。市外加算・入場料徴収加算・備品を含まず、'
                '市外割増を推測しません。現地当日払いで、事前納付後は不使用でも原則返還なし。')
        if ident == 'hino-nanao':
            rows = [('通常2時間枠', 2100, 'テニスコート1面・2時間（通常基本）'),
                    ('一部の3時間枠', 3150, 'テニスコート1面・3時間（通常基本・指定枠）')]
        else:
            note += '2027年3月31日利用分まで700円。2027年4月1日から980円に改定予定（現行最安最高には混ぜません）。' + HINO_CHANGE
            rows = [('通常基本・2027年3月31日利用分まで', 700, 'テニスコート1面・2時間以内（通常基本・2027年3月まで）')]
            if ident == 'hino-tamadaira':
                note += '夜間照明は別途1面2時間以内600円（照明のあるコートのみ）。'
        result.append(entry(ident, HINO_FEES, note, rows))
    for ident in KIYOSE:
        if ident in ('kiyose-chuo', 'kiyose-shimokiyoto'):
            continue
        source = KIYOSE_BASE + ('1005439.html' if ident == 'kiyose-himawari' else '1005433.html')
        note = ('1面2時間の基本料金。市外は公式の50%加算に従い600円×1.5＝900円で、市内と別区分に表示。'
                '事前登録・予約が必要。減免・用途別割増は除き、備品の無料料金を施設料に流用しません。')
        if ident == 'kiyose-himawari':
            note += '対象は中学生以上、サブコートは奥行きが狭い点に注意。'
        else:
            note += '1日4時間まで。抽選は市内在住者のみ、市外は使用月の前月1日から予約可能。'
        result.append(entry(ident, source, note, [
            ('市内・通常基本', 600, 'テニスコート1面・2時間（市内通常）'),
            ('市外・50%加算', 900, 'テニスコート1面・2時間（市外通常）')]))
    for ident, slug, amount in MITAKA:
        note = ('登録市内団体のコート1面2時間の通常貸切料金のみ。1人あたりの共用個人開放料金とは分離。'
                '市外団体・入場料徴収・照明・備品・減免の料金は推測しません。'
                '2026年10月利用分からテニス団体は4人以上、市内団体は市民半数以上等の要件があり、'
                '利用者全員登録・当日使用責任者の本人確認が必要。転貸不可。新制度：' + MITAKA_REGISTER)
        if ident == CLOSED:
            note += CLOSURE_NOTE + ' 公表料金は再開や予約可能を保証しません。'
        result.append(entry(ident, MITAKA_BASE + slug, note,
                            [('市内登録団体・通常貸切', amount, 'テニスコート1面・2時間（市内登録団体・照明別）')]))
    return result


def reviewed_policies():
    def policy(ident, source, summary):
        return dict(id=ident, checked_at=CHECKED, status='conditional', source_url=source, summary=summary)
    result = []
    for ident in TACHIKAWA:
        if ident == JIJI:
            summary = ('使用14日前までのシステム取消・支払いをせず自動取消となると無断キャンセルに該当。'
                       '直前取消ペナルティは適用外だが、無断は1回で翌々月から2か月新規予約停止。')
        else:
            summary = ('現地払い施設は前日までのシステム取消が原則。当日でも開始前までに管理人へ連絡すれば直前取消の制裁は適用外。'
                       '開始前までに連絡しない・開始後の連絡は無断キャンセルで、1回で翌々月から2か月新規予約停止。')
        summary += 'これは予約制裁で金銭の取消料ではありません。既払分の還付率・天候時の免除条件は未確認。'
        result.append(policy(ident, TACHI_CANCEL, summary))
    text = ('利用開始前までに総合体育館窓口で取り消した場合、または天候・施設不良等で使用を見合わせた場合は返還対象。'
            '雨天等は前日又は当日の開始予定時刻から1時間以内までに総合体育館へ申出が必要。'
            '申出が開始後1時間を過ぎた場合、許可書兼領収書がない場合、申出から1か月を過ぎた場合は対象外。'
            '返還申請書と許可書兼領収書を窓口へ提出。返還割合・別途取消手数料は本文で未確認のため全額無料とは表示しません。')
    result += [policy(ident, MUSA_GUIDE, text) for ident in MUSASHI]
    text = ('システム取消が可能。ただし前日・当日は施設受付へ電話。取消料は取らない一方、既に納付した使用料は返還不可。'
            '無断キャンセル3回で3か月利用停止。通常雨天の免除・返還の例外は共通案内では未確認。')
    result += [policy(ident, HINO_CANCEL, text) for ident in HINO]
    for ident in KIYOSE:
        source = KIYOSE_BASE + ('1005439.html' if ident == 'kiyose-himawari' else '1005433.html')
        text = ('自己都合の既払使用料は30日前まで80%、20日前まで60%、前日まで30%還付。'
                'これは還付割合で、取消料の割合ではありません。納付後の日付・時間・施設変更不可。')
        if ident == 'kiyose-himawari':
            text += '当日還付なし。施設窓口で印鑑を持参して取消、現金還付。通常雨天の還付条件は未確認。'
        else:
            text += '下宿地域市民センター窓口で承認書と印鑑を持参して取消。天候中止は同センターへ連絡後還付手続き（割合未確認）。当日の自己都合還付率は未確認。'
        result.append(policy(ident, source, text))
    for ident, slug, _ in MITAKA:
        text = ('団体予約は使用7日前（直近同曜日23:59）までにシステム取消。7日前を過ぎると使用料発生。'
                '期限後又は事前納付済の取消は施設又はSUBARU総合スポーツセンターへ連絡が必要。'
                '事前納付分の還付率、通常雨天の具体的期限・割合はこの記録では未確認。')
        if ident == CLOSED:
            text += '冠水による現行休止は指定管理者が取消処理を行い、利用者から取消連絡は不要。'
        result.append(policy(ident, MITAKA_BASE + slug, text))
    return result


def update_closure():
    path = CATALOGS / 'tokyo_tennis.json'
    rows = json.loads(path.read_text(encoding='utf-8'))
    row, = [r for r in rows if r['id'] == CLOSED]
    before = json.loads(json.dumps(row))
    row.update(availability_status='SUSPENDED', availability_note=CLOSURE_NOTE, checked_at=CHECKED)
    if CLOSURE_EVIDENCE not in row['sources']:
        row['sources'].append(CLOSURE_EVIDENCE)
    if row == before:
        return
    rendered = json.dumps(rows, ensure_ascii=False, indent=2) + '\n'
    assert json.loads(rendered) == rows
    path.write_text(rendered, encoding='utf-8')


def main():
    fees, policies = reviewed_fees(), reviewed_policies()
    validate(fees)
    assert len(REVIEWED_IDS) == len(set(REVIEWED_IDS)) == 26
    assert len(fees) == 19 and len(policies) == 18 and len(HOLDS) == 5
    catalog = {r['id']: r for r in get_catalog()['courts']}
    assert set(REVIEWED_IDS) <= catalog.keys()
    for fee in fees:
        if catalog[fee['id']].get('fee_checked_at') != CHECKED and has_price(catalog[fee['id']]):
            raise ValueError('Refusing to replace priced venue: ' + fee['id'])
    for name, additions in [('fee_plans.json', fees), ('cancellation_policies.json', policies)]:
        existing = {r['id']: r for r in json.loads((CATALOGS / name).read_text(encoding='utf-8'))}
        for row in additions:
            if row['id'] in existing and existing[row['id']] != row:
                raise ValueError('Refusing to replace prior review: ' + row['id'])
    update_closure()
    append_reviews(CATALOGS / 'fee_plans.json', fees)
    append_reviews(CATALOGS / 'cancellation_policies.json', policies)
    print(json.dumps(dict(reviewed=26, prices_added=19, policies_added=18, holds=5, existing_prices_rechecked=2)))


if __name__ == '__main__':
    main()
