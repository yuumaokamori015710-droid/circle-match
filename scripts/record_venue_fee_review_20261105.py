"""Append official room/court tariffs without changing venue identity or bookings."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'outputs'))
from venues.fees import validate
from venues.sports_catalog import get_catalog, has_price
from record_venue_fee_review_20261018 import append_reviews, entry as old_entry

CHECKED = '2026-11-05'
BASE = '3007990a47317c0ec591bfe7b10b825b60c6ea86'
CATALOGS = ROOT / 'outputs/venues/catalogs'
SUGINAMI_GUIDE = 'https://www.city.suginami.tokyo.jp/documents/658/07guide.pdf'
SUGINAMI = [
    ('tokyo-venue-f974be791e64', 'https://www.city.suginami.tokyo.jp/s025/shisetsu/13888.html', '集会室', 800, 500),
    ('tokyo-venue-ea84b99ae578', 'https://www.city.suginami.tokyo.jp/s026/shisetsu/13885.html', '第1集会室', 1700, 1100),
    ('tokyo-venue-8a552aa23372', 'https://www.city.suginami.tokyo.jp/s023/shisetsu/13889.html', '第1集会室', 1000, 700),
    ('tokyo-venue-1f805e4e165d', 'https://ochk-asagaya-center.jp/top/facility-introduction/', '第1集会室', 2100, 1400),
]
MACHIDA_BASE = 'https://www.city.machida.tokyo.jp/bunka/sport/sport/tenniscourt/'
MACHIDA_REGISTER = 'https://www.city.machida.tokyo.jp/bunka/riyou/snet/snet04.html'
MACHIDA_CANCEL = 'https://www.city.machida.tokyo.jp/bunka/riyou/snet/snet05.html'
MACHIDA = [
    ('machida-nozutakita', 'nodutakouenkita.html', True),
    ('machida-chuo', 'machidachuoukouen.html', False),
    ('machida-nozuta', 'nodutakouen.html', False),
    ('machida-naruse', 'narusekurinsenta.html', True),
    ('machida-tsurukawa2', 'tsurukawa2.html', False),
    ('machida-tsurukawachuo', 'tsurukawachuo.html', False),
    ('machida-aihara', 'aiharachuo.html', True),
]
TSURUMA = 'machida-tsuruma'
INAGI_BASE = 'https://www.city.inagi.tokyo.jp/shisetsu/sports/1004857/1004871/'
INAGI_WEATHER = 'https://inagisoutai.jp/request/'
INAGI = [
    ('inagi-shiroyama', '1004874.html', True),
    ('inagi-daimaru', '1004873.html', False),
    ('inagi-kitamidori', '1004872.html', False),
    ('inagi-wakabadai', '1004875.html', True),
]
MINAMITAMA = 'inagi-minamitama'
PRIORITY_HOLDS = ['tokyo-venue-2b0bbd7157ff', 'tokyo-venue-c282bded258a',
                  'tokyo-venue-205d87234dd3', 'tokyo-gym-a231878afdcf']
HOLDS = PRIORITY_HOLDS + [TSURUMA]
REVIEWED_IDS = HOLDS + [r[0] for r in SUGINAMI + MACHIDA + INAGI] + [MINAMITAMA]


def entry(ident, source, note, rows):
    return dict(old_entry(ident, source, note, rows), checked_at=CHECKED)


def reviewed_fees():
    result = []
    for ident, source, room, morning, other in SUGINAMI:
        note = (room + '単室の通常料金のみ。全室の最安値ではありません。午前9～12時の3時間と、'
                '午後13～15時・16～18時・夜間19～21時の各2時間を分離。延長・中間時間・備品・他室・減免は別。'
                'さざんかねっとの事前利用者登録が必要。転貸・権利譲渡不可、不特定多数の催しは事前相談。'
                'この通常料金の掲載は商用利用の承認を意味しません。共通案内：' + SUGINAMI_GUIDE)
        rows = [(room + ' / 午前9～12時', morning, room + '・3時間（通常）')]
        rows += [(room + ' / ' + label, other, room + '・2時間（通常）')
                 for label in ['午後13～15時', '午後16～18時', '夜間19～21時']]
        if ident == 'tokyo-venue-ea84b99ae578':
            rows += [('体育室 / 全面', 800, '体育室全面・1時間（通常）'),
                     ('体育室 / 半面', 400, '体育室半面・1時間（通常）')]
            note += '体育室は運動利用の全面・半面1時間枠を別単位で掲載し、集会使用料金とは混ぜません。種目別利用可否は施設確認。'
        elif ident == 'tokyo-venue-1f805e4e165d':
            rows.append(('体育室', 500, '体育室・1時間（通常）'))
            note += '体育室（122.19平方メートル）の1時間料金も別単位で掲載。競技用の大体育館料金ではなく、種目別利用可否は施設確認。'
        result.append(entry(ident, source, note, rows))
    for ident, slug, lit in MACHIDA:
        note = ('テニスコート1面2時間の通常料金のみ。照明・駐車場・備品を含まず、1時間単価へ換算しません。'
                '利用者登録は15歳以上（中学生除く）の市内在住・在勤・在学の個人。市内在住の抽選と在勤在学の先着申込は別条件。'
                '鶴間公園の区分・料金へ流用しません。登録案内：' + MACHIDA_REGISTER)
        if lit:
            note += '照明は別途30分410円。照明だけの額をコートの最低料金にしません。'
        else:
            note += 'この記録では夜間照明の料金を確認していません。'
        result.append(entry(ident, MACHIDA_BASE + slug, note,
                            [('コート1面 / 2時間', 1040, 'テニスコート1面・2時間（登録個人・通常・照明別）')]))
    for ident, slug, lit in INAGI:
        note = ('テニスコート1面2時間の公表通常料金のみ。市外・未登録者の区分や申込時期は公式案内を確認。'
                '割増・照明・駐車場・備品はこの額に含まず、1時間単価へ換算しません。予約システム利用には事前登録が必要。'
                '通常料金の掲載は転貸・商用イベントの許可を意味しません。')
        if ident == 'inagi-kitamidori':
            note += '市外料金は2倍と明記。未登録者の窓口予約にも2倍の案内がありますが、通常区分と混ぜず割増額は未掲載。'
        if lit:
            note += '照明は別途1時間780円。照明だけの額をコートの最低料金にしません。'
        result.append(entry(ident, INAGI_BASE + slug, note,
                            [('コート1面 / 2時間', 1580, 'テニスコート1面・2時間（通常・照明別）')]))
    note = ('公式が明示するテニスコート1面2時間の無料利用。登録料や駐車料を施設料へ流用したものではありません。'
            '登録済みの個人・団体のみ利用でき、未登録者は利用不可。団体登録には年2回（6月・12月）のコート整備参加が必要。'
            '他の稲城市有料コートの料金・利用条件とは分離。')
    result.append(entry(MINAMITAMA, INAGI_BASE + '1004876.html', note,
                        [('コート1面 / 2時間', 0, 'テニスコート1面・2時間（登録個人・団体・無料）')]))
    return result


def reviewed_policies():
    def policy(ident, source, summary):
        return dict(id=ident, checked_at=CHECKED, status='conditional', source_url=source, summary=summary)
    text = ('地域区民センター・区民集会所の共通案内を適用。未払いの取消は原則7日前までシステム、当日は施設窓口。'
            '6日前以降の取消・無断不使用は利用制限の対象となる場合あり。現金支払後は施設窓口で手続きし、還付条件は施設確認。'
            'カード支払後は7日前までのシステム取消は還付、6日前以降は還付なし（利用制限解除料に充当）。'
            '現金払いにも一律全額還付とはしません。屋内施設の通常雨天免除は未確認。')
    result = [policy(ident, SUGINAMI_GUIDE, text) for ident, *_ in SUGINAMI]
    text = ('取消は前日まで予約システム、当日は利用開始前に施設連絡。利用日の3週間前を過ぎた取消は1点、無断不使用は2点。'
            '予約後60分以内の取消は対象外。1点の制限は団体のみ、2点以上は利用日2週間前からの予約以外に制限あり。'
            '適用は利用月の翌々月。料金支払は利用当日。取消料・既払い分の還付額は共通案内では未確認。'
            '天候による可否は開始30分前に施設判断し、使用不可なら取消操作不要・ペナルティなし。自己判断の雨天取消とは区別。')
    result += [policy(ident, MACHIDA_CANCEL, text) for ident in [r[0] for r in MACHIDA] + [TSURUMA]]
    text = ('2025年2月利用分から、雨・雪・雷・強風で屋外体育施設を使用できなかった場合は還付対象。'
            '報告期間は開始1時間前から翌日23時59分まで。専用WEBフォームによる報告が必要で電話不可、未報告は還付不可。'
            'これは悪天候時の還付条件で、自己都合の取消期限・手数料・還付率は未確認。予約そのものの取消操作と混同しません。')
    result += [policy(ident, INAGI_WEATHER, text) for ident, *_ in INAGI]
    return result


def main():
    fees, policies = reviewed_fees(), reviewed_policies()
    validate(fees)
    assert len(REVIEWED_IDS) == len(set(REVIEWED_IDS)) == 21
    assert len(fees) == 16 and len(policies) == 16 and len(HOLDS) == 5
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
    append_reviews(CATALOGS / 'fee_plans.json', fees)
    append_reviews(CATALOGS / 'cancellation_policies.json', policies)
    print(json.dumps(dict(reviewed=21, prices_added=16, policies_added=16, holds=5)))


if __name__ == '__main__':
    main()
