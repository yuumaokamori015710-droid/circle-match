"""Append the November 8 official-source venue review without replacing existing data."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'outputs'))
from venues.fees import validate
from venues.sports_catalog import get_catalog, has_price
from record_venue_fee_review_20261018 import append_reviews, entry as previous_entry

CHECKED = '2026-11-08'
BASE = '4de262d7bc6452bc61dc4e4e2441ec520322a02e'
CATALOGS = ROOT / 'outputs/venues/catalogs'
KOGANEI = ('https://www.city.koganei.lg.jp/kosodatekyoiku/kyoikuiinkai/kakusyuzigyou/'
           'R6koganeinokyouiku.files/R6koganeinokyouiku.pdf')
KOGANEI_CANCEL = ('https://www.city.koganei.lg.jp/kurashi/455/shiryo/yokuarutoiawasesport.files/'
                  'soutaikuriyamayoyakunittei.pdf')
AKIRUNO = 'https://www.city.akiruno.tokyo.jp/0000007644.html'
HACHIOJI = 'https://www.city.hachioji.tokyo.jp/kurashi/kyoiku/002/011/p031243_d/fil/shisetsuichiran.pdf'
KUNITACHI = 'https://kuzaidan.or.jp/gym/park/shisetsu-k3/'
BUNKYO = 'https://www.city.bunkyo.lg.jp/documents/6499/shiseturyoukinnitirann.pdf'
HIGASHIYAMATO = 'https://static.wixstatic.com/media/21c974_2487df7908744b339379387542e7a10c~mv2.png'
MUSASHIMURAYAMA = 'https://www2.city.musashimurayama.lg.jp/reiki/H353901010031/H353901010031_j.html'
KIYOSE = 'https://www.city.kiyose.lg.jp/shisetsu/riyouyoyaku/1005434.html'
INAGI = 'https://www.city.inagi.tokyo.jp/shisetsu/sports/1004857/1004868/1004869.html'
TACHIKAWA = ('https://www.city.tachikawa.lg.jp/_res/projects/default_project/_page_/001/008/085/'
             'sportsshisetsu_20260201.pdf')
TACHIKAWA_CANCEL = 'https://www.city.tachikawa.lg.jp/kanko/sports/1002923/1002944/1025596.html'

HOLDS = [
    'tokyo-venue-2b0bbd7157ff', 'tokyo-venue-205d87234dd3', 'tokyo-sports-025',
    'tokyo-venue-b350e0713b8e', 'tokyo-venue-74f8af5c1bc3',
]


def venue(suffix):
    return 'tokyo-venue-' + suffix


def entry(ident, source, note, rows):
    return dict(previous_entry(ident, source, note, rows), checked_at=CHECKED)


def reviewed_fees():
    rows = [entry('tokyo-gym-a231878afdcf', KOGANEI,
        '大体育室の団体貸切。利用者登録が必要。3時間枠は9～12時、12～15時、15～18時、18～21時。'
        '市の料金表に沿って面積と時間を区分。個人利用・小体育室・入場料を徴収する利用は対象外。',
        [(area, amount, f'大体育室{area}・{duration}（団体貸切）')
         for area, base in [('全面', 6600), ('2/3面', 4400), ('半面', 3300), ('1/3面', 2200)]
         for duration, amount in [('3時間', base), ('12時間', base * 4)]])]
    rows.append(entry(venue('9385bad84a18'), AKIRUNO,
        '市内料金は当日の構成員の半数以上が市内在住・在勤・在学の場合。照明は別途1時間あたり、'
        '半点灯は市内1600円・市外3200円、全点灯は市内3200円・市外6400円。',
        [('市内・基本', 1800, '野球場1面・2時間（市内・照明別）'),
         ('市外・基本', 5400, '野球場1面・2時間（市外・照明別）')]))
    rows.append(entry(venue('17f2a6ab5bfc'),
        'https://www.city.chuo.lg.jp/a0015/bunkakankou/sports/mosikomihoho/undouzyou.html',
        '月島運動場の野球場利用。事前に団体登録。夜間8000円は照明込みの合計で、照明の追加料金ではありません。',
        [('昼間', 2000, '野球場1面・2時間（昼間）'),
         ('夜間', 8000, '野球場1面・2時間（夜間・照明込み）')]))
    for suffix, name, note in [
        ('c282bded258a', '少年野球場', '中学生以下対象。水・木曜の無人開場は事前申請した登録団体に限ります。隣接サッカー場の料金ではありません。'),
        ('456ad6cd0311', '少年野球場', '少年野球場の料金。隣接する庭球場・少年サッカー場とは別です。'),
        ('40fd2672b512', '野球場', '軟式野球・ソフトボール用。予約後、使用の1週間前までに富士森体育館窓口で利用申請が必要。未申請は取消・ペナルティの対象です。'),
    ]:
        rows.append(entry(venue(suffix), HACHIOJI, '市の施設一覧で無料と明記。' + note,
                          [('予約利用', 0, name + '1面・予約利用')]))
    rows.append(entry(venue('a933f2959eeb'), KUNITACHI,
        '野球場1面1時間。登録が必要。市内・市外を分離し、学生については指定管理者の対象条件を確認してください。',
        [('市内', 650, '野球場1面・1時間（市内）'),
         ('市外', 975, '野球場1面・1時間（市外）')]))
    rows.append(entry(venue('7b029d9557da'), BUNKYO,
        '2026年4月改定後の少年野球場全面。事前登録が必要。区内在住・在勤が対象で、学生は区内在住のみ。'
        'ソフトボールは抽選後に空きがある場合のみ。',
        [('全面・通常枠', 1200, '少年野球場全面・2時間（登録団体）')]))
    rows.append(entry(venue('1990d1bb3cff'), 'https://www.city.hino.lg.jp/shisetsu/sports/ground/1001001.html',
        '少年野球・ソフトボール用。事前登録が必要。障害者手帳等による減免は通常料金に含みません。芝生養生のため1～2月は休場。',
        [('通常枠', 1000, 'グラウンド1面・2時間（登録団体）')]))
    rows.append(entry(venue('1687c06f7eb7'), HIGASHIYAMATO,
        '野球場（陸上競技場を含む）の1枠2時間。陸上競技場のみの料金とは別。ナイター照明は別途1枠6000円。'
        '利用者登録が必要。中学生以下の利用は保護者同伴。',
        [('大人', 2400, '野球場1面・2時間（大人・照明別）'),
         ('中学生以下', 600, '野球場1面・2時間（中学生以下・照明別）')]))
    for suffix in ['81b1c0e602be', '94d26ef99463']:
        is_onan = suffix == '81b1c0e602be'
        note = '市内料金は市内在住・在勤・在学者が構成員の半数以上を占める団体に適用。市外・市内を分けて表示。'
        options = [('市内・照明なし', 750, '野球場1面・1時間（市内・照明なし）'),
                   ('市外・照明なし', 1500, '野球場1面・1時間（市外・照明なし）')]
        if is_onan:
            note += '大南の夜間照明使用時は照明込み総額。昼間と照明を使わない夜間の料金は同じ。'
            options += [('市内・夜間照明込み', 3830, '野球場1面・1時間（市内・夜間照明込み）'),
                        ('市外・夜間照明込み', 7660, '野球場1面・1時間（市外・夜間照明込み）')]
        rows.append(entry(venue(suffix), MUSASHIMURAYAMA, note, options))
    rows.append(entry(venue('4f32c019760c'), KIYOSE,
        '下宿第二運動公園の野球場1面2時間。市外は料金表の50%増し。減免は通常料金に含みません。',
        [('中学生以下・市内', 1200, '野球場1面・2時間（市内・中学生以下）'),
         ('中学生以下・市外', 1800, '野球場1面・2時間（市外・中学生以下）'),
         ('大人・市内平日', 3500, '野球場1面・2時間（市内・大人）'),
         ('大人・市内土日祝', 4600, '野球場1面・2時間（市内・大人）'),
         ('大人・市外平日', 5250, '野球場1面・2時間（市外・大人）'),
         ('大人・市外土日祝', 6900, '野球場1面・2時間（市外・大人）')]))
    rows.append(entry(venue('d7f8d384bd4b'),
        'https://www.city.shibuya.tokyo.jp/shisetsu/sports-shisetsu/sports-center/sp3_oyama.html',
        '少年野球場の予約利用は区の施設案内で無料と明記。大人の野球や他の用途に適用される料金ではありません。',
        [('少年野球・予約利用', 0, '少年野球場1面・予約利用')]))
    rows.append(entry(venue('2304376db3f5'),
        'https://www.town.mizuho.tokyo.jp/kyoikuiinkai/about/007/002/p010807.html',
        '町営グランドの野球場1面、1枠2時間30分。町内在住・在勤・在学とその他を分離。照明は別料金。',
        [('町内', 1200, '野球場1面・2時間30分（町内・照明別）'),
         ('その他', 3600, '野球場1面・2時間30分（町外・照明別）')]))
    rows.append(entry(venue('9f9cb61f606a'), INAGI,
        '軟式野球場。市登録団体は通常料金、未登録団体は窓口申込で2倍。中学生以上と小学生以下を分け、'
        '大会本部室の利用料は含みません。',
        [('登録・中学生以上', 4530, '野球場1面・2時間（登録・中学生以上）'),
         ('登録・小学生以下', 2260, '野球場1面・2時間（登録・小学生以下）'),
         ('未登録・中学生以上', 9060, '野球場1面・2時間（未登録・中学生以上）'),
         ('未登録・小学生以下', 4520, '野球場1面・2時間（未登録・小学生以下）')]))
    for suffix, prices in [
        ('aed3f0dc916c', [(3200, 6400), (6400, 15200), (9600, 24000)]),
        ('336735e641ac', [(400, 1000), (1200, 2600), (2000, 4200)]),
    ]:
        rows.append(entry(venue(suffix), TACHIKAWA,
            '野球場1面2時間。市内・市外を分離。夜間は照明込み合計で、開始時刻ごとに別の料金です。'
            '夜間枠の有無は季節の開場時間を確認してください。',
            [(f'{region}・{slot}', amount, f'野球場1面・2時間（{region}・{slot}）')
             for slot, amounts in zip(('通常', '17～19時・照明込み', '19～21時・照明込み'), prices)
             for region, amount in zip(('市内', '市外'), amounts)]))
    rows.append(entry(venue('25810e9403da'), TACHIKAWA,
        '中里野球場は市内登録団体のみ。市外の料金はありません。',
        [('市内・通常', 400, '野球場1面・2時間（市内登録のみ）')]))
    rows.append(entry(venue('14d1b8c3ab17'),
        'https://www.city.arakawa.tokyo.jp/documents/1537/114_137.pdf',
        '軟式野球場1面2時間。区外在住も利用可、チーム登録が必要。照明は別途1面1時間あたり大人6500円・中学生以下2500円。',
        [('大人・基本', 2600, '野球場1面・2時間（大人・照明別）'),
         ('中学生以下・基本', 1000, '野球場1面・2時間（中学生以下・照明別）')]))
    return rows


def reviewed_policies():
    def policy(ident, source, summary):
        return dict(id=ident, checked_at=CHECKED, status='conditional', source_url=source, summary=summary)

    rows = [
        policy('tokyo-gym-a231878afdcf', KOGANEI_CANCEL,
               '利用日の1か月前まで全額還付、それを過ぎて10日前まで半額還付、9日前以降は還付なし。'
               '取消料が発生する場合は予約システムで取り消せないため施設窓口へ。荒天時の別条件は未確認。'),
        policy(venue('9385bad84a18'), 'https://www.city.akiruno.tokyo.jp/0000018371.html',
               '施設使用日の15日前まで予約システムで取消可。14日前以降は施設に連絡し、取消日で使用料の負担が変わります。'
               'この案内には日数別の具体額や雨天還付率の記載なし。'),
        policy(venue('a933f2959eeb'), KUNITACHI,
               '自己都合は使用日の5日前までに手続きで全額還付。雨天中止は使用日を含め14日以内に手続きで全額還付。'
               '利用者カードと使用承認書兼領収書を総合体育館へ持参。'),
        policy(venue('7b029d9557da'), 'https://www.city.bunkyo.lg.jp/b015/p004395.html',
               '雨天時は施設が利用可否を判断。中止なら振替または還付の手続きが可能。'
               '自己都合の取消期限・還付率は施設案内で未確認。'),
        policy(venue('1687c06f7eb7'), 'https://www.higashiyamato-taiikukan.com/'
               '%E6%96%BD%E8%A8%AD%E5%88%A9%E7%94%A8%E6%96%B9%E6%B3%95-%E6%B3%A8%E6%84%8F%E4%BA%8B%E9%A0%85',
               '支払済み予約は使用7日前まで（休館日はその前日）に窓口で取消・還付または充当を申請。'
               '以降も取消可だが原則還付なし。施設が雨など不可抗力と判断した場合は窓口申請で還付・充当の対象。'),
        policy(venue('4f32c019760c'), KIYOSE,
               '自己都合の還付率は使用30日前まで80%、20日前まで60%、前日まで30%。下宿地域市民センター窓口で手続き。'
               '入金後の日時・施設変更は不可。天候不順で中止の場合も同センターで還付手続き。天候時の還付率はこの案内では未記載。'),
        policy(venue('9f9cb61f606a'), 'https://www.city.inagi.tokyo.jp/shisetsu/shisetsuinfo/uten_alert.html',
               '雨天等で利用できない場合、暑さ指数31以上の場合は市の案内に沿って未使用を申告し、返金可否の案内後に申請。'
               '振込返金の申請には予約システムへのメール登録が必要。自己都合の取消・還付とは別の制度。'),
    ]
    restriction = '不特定多数を対象に、料金を提示し日時・会場を指定する募集は、立川市の営利行為等のペナルティ対象になり得ます。'
    rows.append(policy(venue('aed3f0dc916c'), TACHIKAWA_CANCEL,
        '前払い施設。使用7日前までにシステムで取消。支払期限内に管理者へ連絡した場合と、'
        '無連絡の自動取消は別扱い。直前取消・同一枠の反復取消は新規予約1か月停止、無断は2か月停止。'
        '金銭還付率・雨天時の条件はこの案内では未確認。' + restriction))
    for suffix in ['25810e9403da', '336735e641ac']:
        rows.append(policy(venue(suffix), TACHIKAWA_CANCEL,
            '現地払い施設。前日までにシステムで取消。当日に管理人へ開始前までに連絡した場合は直前取消扱いで新規予約1か月停止、'
            '開始後の連絡または無連絡は無断扱いで2か月停止。金銭取消料・雨天時の条件はこの案内では未確認。' + restriction))
    return rows


REVIEWED_IDS = HOLDS + [row['id'] for row in reviewed_fees()]


def main():
    fees, policies = reviewed_fees(), reviewed_policies()
    validate(fees)
    assert len(REVIEWED_IDS) == len(set(REVIEWED_IDS)) == 25
    assert len(fees) == 20 and len(policies) == 10
    rows = {r['id']: r for r in get_catalog()['courts']}
    assert set(REVIEWED_IDS) <= rows.keys()
    assert {r['id'] for r in policies} <= set(REVIEWED_IDS)
    for fee in fees:
        row = rows[fee['id']]
        if has_price(row) and row.get('fee_checked_at') != CHECKED:
            raise ValueError('Refusing to replace priced venue: ' + fee['id'])
    for name, additions in [('fee_plans.json', fees), ('cancellation_policies.json', policies)]:
        old = {r['id']: r for r in json.loads((CATALOGS / name).read_bytes())}
        for row in additions:
            if row['id'] in old and old[row['id']] != row:
                raise ValueError('Refusing to replace prior review: ' + row['id'])
    append_reviews(CATALOGS / 'fee_plans.json', fees)
    append_reviews(CATALOGS / 'cancellation_policies.json', policies)
    print(json.dumps(dict(reviewed=len(REVIEWED_IDS), prices_added=len(fees), policies_added=len(policies), holds=len(HOLDS))))


if __name__ == '__main__':
    main()
