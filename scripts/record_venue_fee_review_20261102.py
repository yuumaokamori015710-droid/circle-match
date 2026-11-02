"""Append dated, room-scoped official fees; never replace a prior review."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'outputs'))
from venues.fees import validate
from venues.sports_catalog import get_catalog, has_price
from record_venue_fee_review_20261018 import append_reviews, entry as old_entry

CHECKED = '2026-11-02'
BASE = 'e5119a0eb8568d77a72fc779e12ab4baf357ada1'
CATALOGS = ROOT / 'outputs/venues/catalogs'
SHINA_PAGE = 'https://www.city.shinagawa.tokyo.jp/kurashi/community/1008160/1008162.html'
SHINA_GUIDE = 'https://www.city.shinagawa.tokyo.jp/_res/projects/default_project/_page_/001/008/162/20260105094637_1.pdf'
# First meeting room only. Columns were checked against the rendered official PDF.
SHINA_ROOMS = [
    ('tokyo-venue-0e047848505a', [2000, 2900, 4000], [2400, 3500, 4800]),
    ('tokyo-venue-73c4be46efde', [1900, 2700, 3700], [2300, 3200, 4400]),
    ('tokyo-venue-9839ec6e288d', [800, 1100, 1500], [1000, 1300, 1800]),
    ('tokyo-venue-2d4af20901c0', [1700, 2500, 3400], [2000, 3000, 4100]),
    ('tokyo-venue-b722f4fd36ef', [700, 900, 1300], [800, 1100, 1600]),
    ('tokyo-venue-b1db3e4188ad', [2600, 3800, 5200], [3100, 4600, 6200]),
    ('tokyo-venue-c89b926110f3', [1300, 1800, 2500], [1600, 2200, 3000]),
    ('tokyo-venue-9cfc54c16159', [1700, 2400, 3300], [2100, 2900, 4000]),
    ('tokyo-venue-87814f71523e', [900, 1300, 1800], [1100, 1600, 2200]),
    ('tokyo-venue-d132ad65fdc0', [2300, 3400, 4700], [2800, 4100, 5600]),
]
PERIODS = [('午前9～12時', '3時間'), ('午後13～16時30分', '3時間30分'), ('夜間17時30分～21時30分', '4時間')]
BUNKYO_GUIDE = 'https://www.city.bunkyo.lg.jp/b011/p006655/index.html'
BUNKYO_REGISTER = 'https://www.city.bunkyo.lg.jp/b011/p006767.html'
BUNKYO_ROOMS = [
    ('tokyo-venue-7254c96be928', '洋室A', [1000, 1200, 1200], 'https://www.city.bunkyo.lg.jp/b011/p006665/index.html'),
    ('tokyo-venue-00308c1d485f', '多目的室A', [4800, 5400, 5400], 'https://www.city.bunkyo.lg.jp/b011/p006657.html'),
    ('tokyo-venue-8aa28dc480fa', '洋室A', [700, 700, 700], 'https://www.city.bunkyo.lg.jp/b011/p006662/index.html'),
]
KUDAN = 'tokyo-venue-b2da1c3fd20b'
KUDAN_FEES = 'https://www.kudan-ll.info/guide/price/'
KUDAN_USE = 'https://www.kudan-ll.info/guide/use/'
KUDAN_REGISTER = 'https://www.kudan-ll.info/guide/entry/'
TANSU = 'tokyo-venue-612e43f4ce09'
TANSU_FEES = 'https://shinjuku.hall-info.jp/file/tansu_use_charge.pdf'
TANSU_USE = 'https://shinjuku.hall-info.jp/tansu/riyou.html'
HALL = 'tokyo-venue-8a969b3f87db'
HALL_FEES = 'https://www.city.shinagawa.tokyo.jp/_res/projects/default_project/_page_/001/011/098/hpg000000314_13.txt'
HALL_RULES = 'https://www.city.shinagawa.tokyo.jp/_res/projects/default_project/_page_/001/011/098/hpg000000314_10.pdf'
HALL_PAGE = 'https://www.city.shinagawa.tokyo.jp/shisetsu/bunkasportsshisetsu/1008222/1011097/1011098.html'
PICKLE = 'tokyo-sports-024'
PICKLE_BOOKING = 'https://pacificpickleclub.resv.jp/'
PICKLE_NEWS = 'https://pacificpickleclub.com/news/202610/'
HOLDS = [
    'tokyo-gym-a231878afdcf', 'tokyo-gym-aa77f48e78d0', 'tokyo-venue-2b0bbd7157ff',
    'tokyo-venue-8e6c0f81a52c', 'tokyo-venue-205d87234dd3', 'tokyo-venue-c282bded258a',
    'tokyo-sports-013', 'tokyo-venue-d7b168f67c73', 'tokyo-venue-ecb55dd79d92',
    'tokyo-venue-ec7d0ac023ca', 'tokyo-venue-6b06aed3958d',
    'tokyo-gym-c9fd2d3160d0', 'tokyo-gym-e4c214671936',
]
REVIEWED_IDS = HOLDS + [PICKLE, HALL, KUDAN, TANSU] + [r[0] for r in SHINA_ROOMS + BUNKYO_ROOMS]


def entry(ident, source, note, rows):
    return dict(old_entry(ident, source, note, rows), checked_at=CHECKED)


def reviewed_fees():
    result = []
    for ident, inside, outside in SHINA_ROOMS:
        note = ('第1集会室単室の通常料金のみ。全室の最安値ではありません。区内は事務所等が区内、または構成員半数以上が区内在住在勤在学の団体等で、名簿等による判定が必要。'
                'その他は区外料金。インターネット・電話予約には2名以上の団体登録が必要。5割減額・免除は別途対象判定と窓口申請が必要で、通常料金へ混ぜません。'
                '営利、不特定多数の利用、利用人数未定等は不可。午前3時間・午後3時間30分・夜間4時間を分離。日曜祝日の夜間は施設により利用不可。'
                '附帯設備・他室・併用料金は含みません。登録・利用条件：' + SHINA_PAGE)
        rows = [(group + ' / 第1集会室 / ' + period, amount, '第1集会室・' + duration + '（' + group + '）')
                for group, values in [('区内・通常', inside), ('区外・通常', outside)]
                for (period, duration), amount in zip(PERIODS, values)]
        result.append(entry(ident, SHINA_GUIDE, note, rows))
    for ident, room, values, source in BUNKYO_ROOMS:
        note = (room + '単室の通常料金のみ。全室の最低・最高ではありません。区内在住在勤在学者、区内所在の会社・団体等が対象で、営利目的不可。'
                '事前の利用者登録・確認が必要。併設アカデミー等の別施設や他室、附帯設備、減免料金を含みません。'
                '午前9～12時30分の3時間30分、午後13～17時・夜間17時30分～21時30分の4時間を分離。条件・取消：' + BUNKYO_GUIDE + ' 登録：' + BUNKYO_REGISTER)
        result.append(entry(ident, source, note,
                            [(room + ' / ' + period, amount, room + '・' + duration + '（区内利用資格・通常）')
                             for (period, duration), amount in zip([('午前9～12時30分', '3時間30分'), ('午後13～17時', '4時間'), ('夜間17時30分～21時30分', '4時間')], values)]))
    result.append(entry(KUDAN, KUDAN_FEES,
                        '6階レクリエーションホールのみ。全室の最安値ではありません。5名以上、半数以上が区内在住在勤在学、代表者も該当する生涯学習団体で登録・名簿提出が必要。'
                        '営利利用不可、登録会員以外の利用不可。区民自主・一般の予約開始日は異なります。午前・夜間3時間と午後4時間を分離し、任意の30分延長は別料金のため含めません。'
                        '準備・片付け込み、利用前日までに支払。登録条件：' + KUDAN_REGISTER + ' 利用条件：' + KUDAN_USE,
                        [('6階レクリエーションホール / ' + period, amount, '6階レクリエーションホール・' + duration + '（登録団体・通常）')
                         for (period, duration), amount in zip([('午前9～12時', '3時間'), ('午後13～17時', '4時間'), ('夜間18～21時', '3時間')], [2400, 3100, 3900])]))
    note = ('ホール全体の税込通常料金のみ。楽屋・附帯設備は別途。午前3時間、午後・夜間4時間、全日12時間45分を分離。'
            '入場料なし／ありと平日／土日祝の条件も分離。物品販売・募金等は入場料あり扱い。区民は6か月前、区外は5か月前からで、在勤のみは区外扱い。'
            'システム申請は事前窓口登録が必要。準備撤去込み、利用申請は原則2週間前まで。利用条件：' + TANSU_USE)
    rows = []
    for group, values in [('平日・入場料なし', [13600, 27200, 34000, 67300]),
                          ('土日祝・入場料なし', [16300, 32600, 40400, 80600]),
                          ('平日・入場料あり', [27200, 54400, 68000, 134600]),
                          ('土日祝・入場料あり', [32600, 65200, 81200, 161200])]:
        rows += [(group + ' / ' + period, amount, 'ホール全体・' + duration + '（' + group + '）')
                 for (period, duration), amount in zip([('午前9～12時', '3時間'), ('午後13～17時', '4時間'), ('夜間17時45分～21時45分', '4時間'), ('全日9～21時45分', '12時間45分')], values)]
    result.append(entry(TANSU, TANSU_FEES, note, rows))
    note = ('荏原文化センター大ホール全体のみ。舞台のみの半額、他室、温水プール、附帯設備・人員手配等は含みません。'
            '区民・区民以外と平日・土日祝、3時間・3時間30分・4時間を分離。区民料金の区分判定と予約優先の区民団体要件は同一とは限らず、施設で確認が必要。'
            '日曜祝日の夜間は休館で、掲載料金は空きや予約可能日時を保証しません。準備撤収込み、申込締切は1か月前、電話申込後は翌日から7日以内に正式窓口申請。'
            '大ホールの支払は一般室の7日以内ではなく専用規約に従います。現行施設案内：' + HALL_PAGE + ' 専用規約：' + HALL_RULES)
    rows = []
    for group, values in [('区民・平日', [12600, 19000, 25200]), ('区民以外・平日', [15100, 22800, 30200]),
                          ('区民・土日祝', [13900, 20900, 27700]), ('区民以外・土日祝', [16700, 25100, 33200])]:
        rows += [(group + ' / 大ホール / ' + period, amount, '大ホール全体・' + duration + '（' + group + '）')
                 for (period, duration), amount in zip(PERIODS, values)]
    result.append(entry(HALL, HALL_FEES, note, rows))
    result.append(entry(PICKLE, PICKLE_BOOKING,
                        '屋外ピックルボールコート1面1時間の通常料金。平日と土日祝を分離。18時から夜間料金。10月改定の公式告知と公開予約先を照合。'
                        '体験会・オープンプレイの個人参加費、未発表の会員割引や入会金・年会費は含みません。パドル・ボール1セット800円、ロッカー・シャワー550円は別途。'
                        '対象6歳以上、中学生以下は保護者同伴。完全キャッシュレス、遅刻しても予約分を請求。21名以上は別途相談。料金改定根拠：' + PICKLE_NEWS,
                        [('平日・昼OPEN～18時', 6500, 'コート1面・1時間（平日・通常）'),
                         ('平日・夜18～21時', 9000, 'コート1面・1時間（平日・通常）'),
                         ('土日祝・昼OPEN～18時', 10000, 'コート1面・1時間（土日祝・通常）'),
                         ('土日祝・夜18～21時', 11000, 'コート1面・1時間（土日祝・通常）')]))
    return result


def reviewed_policies():
    def policy(ident, url, summary):
        return dict(id=ident, status='conditional', source_url=url, checked_at=CHECKED, summary=summary)
    result = [policy(ident, SHINA_GUIDE,
                     '取消は利用予定施設へ連絡。支払後の自己都合取消は7日前までに利用施設窓口で手続きすれば全額現金還付。7日前が窓口休業日なら翌営業日まで。'
                     'ネット決済でも還付は窓口のみで、印鑑と承認書（窓口払は原本、ネット払はデータ）が必要。予約翌日起算7日以内の支払・確定がないと自動取消。'
                     '7日前を過ぎた自己都合還付率は当該案内では未確認。災害で利用困難な場合は全額還付（区発信の警戒レベル3以上、震度5弱以上、その他区判断等）。'
                     '通常の雨だけで免除とはしません。災害条件：' + SHINA_PAGE)
              for ident, _, _ in SHINA_ROOMS]
    result += [policy(ident, BUNKYO_GUIDE,
                      '納付済使用料は原則還付なし。3日前までに承認書を添えて取消申請し相当の理由が認められた場合は5割還付。窓口還付は印鑑持参。'
                      'ネット予約はネット取消可能で、3日前までなら取消翌月末に半額引落。クレジット決済時は取消後1時間以内にキャンセル料の決済手続き。'
                      '変更は3日前まで・1回限り。天候免除の具体的条件は当該案内では未確認。') for ident, _, _, _ in BUNKYO_ROOMS]
    result.append(policy(KUDAN, KUDAN_USE,
                         '仮予約の変更・取消は窓口または電話。支払済は利用日前日までに承認書・レシートを持参して来館し窓口返金。'
                         '利用料金は前日までに支払（当日不可）。当日の還付条件・割合・通常天候による免除は当該案内では未確認。'))
    result.append(policy(TANSU, TANSU_USE,
                         '申請書作成・システム予約完了時から、未入金でも取消変更の所定手数料が発生。取消は14日前まで利用予定ホールで申請・承認後、7割を口座返還。'
                         '14日前を過ぎると還付なし。変更は同月同ホールで1回、14日前まで。変更後は取消時の還付なし。'
                         '差額が減る場合は差額の7割返還・3割手数料。通常の天候免除は当該案内では未確認。'))
    result.append(policy(HALL, HALL_RULES,
                         '大ホール専用規約。申込から1か月以内に全額または半額予納、残額は使用1か月前まで。やむを得ない取消は全額納入済かつ1か月前までなら施設使用料の半額返金。'
                         '予納金は返金不可、使用者側過失による取消は納付済使用料の返金不可。附帯設備は使用当日の使用開始前までなら全額返金。'
                         '日時変更は1か月前まで。通常の天候免除・1か月前を過ぎた自己都合還付率は当該規約では未確認。'))
    result.append(policy(PICKLE, PICKLE_BOOKING,
                         '前日50%、当日100%のキャンセル料。2日前まではWebまたは店舗、当日は利用時間までに店舗へ連絡。前日の手続方法・2日前の料率は明記なし。'
                         '15分以上連絡なしは自動取消、無断取消も請求対象。降水量1mm以上の雨予報、雨天直後、熱中症アラート・暴風警報時は施設中止として取消料なし。'
                         '雨天判断は前日17時時点の江東区有明予報により施設から連絡。本人都合の雨天取消を自動無料とは扱いません。'))
    return result


def main():
    fees, policies = reviewed_fees(), reviewed_policies()
    validate(fees)
    assert len(set(REVIEWED_IDS)) == len(REVIEWED_IDS) == 30
    assert len(fees) == len(policies) == 17 and len(HOLDS) == 13
    assert set(REVIEWED_IDS) == {r['id'] for r in fees} | set(HOLDS)
    rows = {r['id']: r for r in get_catalog()['courts']}
    assert all(ident in rows for ident in REVIEWED_IDS)
    for row in fees:
        if rows[row['id']].get('fee_checked_at') != CHECKED and has_price(rows[row['id']]):
            raise ValueError('Refusing to replace priced venue: ' + row['id'])
    for name, additions in [('fee_plans.json', fees), ('cancellation_policies.json', policies)]:
        existing = {r['id']: r for r in json.loads((CATALOGS / name).read_text(encoding='utf-8'))}
        for row in additions:
            if row['id'] in existing and existing[row['id']] != row:
                raise ValueError('Refusing to replace prior review: ' + row['id'])
    append_reviews(CATALOGS / 'fee_plans.json', fees)
    append_reviews(CATALOGS / 'cancellation_policies.json', policies)
    print(json.dumps(dict(reviewed=30, prices_added=17, policies_added=17, holds=13)))


if __name__ == '__main__':
    main()
