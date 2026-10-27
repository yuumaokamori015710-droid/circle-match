"""Append source-matched tariffs and one confirmed closure, retaining identities."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'outputs'))
from venues.fees import validate
from venues.sports_catalog import get_catalog, has_price
from record_venue_fee_review_20261018 import append_reviews, entry as old_entry

CHECKED = '2026-10-27'
BASE = '55a7ff321a43d845c15ebd9fc075aa745393745f'
CATALOGS = ROOT / 'outputs/venues/catalogs'
HACHIJOJI = 'https://www.city.hachioji.tokyo.jp/shisetsu/104/'
HACHIJOJI_GUIDE = HACHIJOJI + 'p005417.html'
HACHIOJI = [
    'tokyo-venue-048bb49572f3', 'tokyo-venue-16bb2c8850d1', 'tokyo-venue-4a8e4a8753a7',
    'tokyo-venue-3cfb27df8e7a', 'tokyo-venue-1c7e242fd790', 'tokyo-venue-5e7a80249c77',
    'tokyo-venue-606b9074a6ba', 'tokyo-venue-c282bded258a', 'tokyo-venue-456ad6cd0311',
    'tokyo-venue-649d27923ae4', 'tokyo-venue-e2bb272043d2', 'tokyo-venue-40fd2672b512',
]
KITA_BASE = 'https://www.city.kita.lg.jp/culture-tourism-sports/sports/1010385/'
KITA_FACILITY = KITA_BASE + '1010387/1010393/1010396/'
KITA_GUIDE = KITA_BASE + '1010387/1010441.html'
KITA = ['tokyo-sports-032', 'tokyo-venue-58eea0a2f035', 'tokyo-venue-49f6c14142ff']
KOTO = ['tokyo-venue-3df7eec0d53c', 'tokyo-venue-74f8af5c1bc3',
        'tokyo-venue-3766e52a081e', 'tokyo-venue-f8e9ad9cee63']
PRIORITY = ['tokyo-gym-a231878afdcf', 'tokyo-gym-c9fd2d3160d0',
            'tokyo-venue-ec7d0ac023ca', 'tokyo-venue-6b06aed3958d',
            'tokyo-venue-205d87234dd3', 'tokyo-venue-2b0bbd7157ff', 'tokyo-venue-8e6c0f81a52c']
REVIEWED_IDS = PRIORITY + HACHIOJI + KITA + KOTO
HOLDS = PRIORITY + [HACHIOJI[7], HACHIOJI[8], HACHIOJI[11], KOTO[0], KOTO[1]]
YUME = 'https://www.di-ksp.jp/facility/yumenoshima_u'
SHIOMI = 'https://www.di-ksp.jp/facility/shiomi'
CLOSURE_SOURCE = 'https://www.city.koto.lg.jp/104010/bunkasports/sports/torikumi/6384.html'
CLOSURE_NOTE = '亀戸野球場・庭球場は老朽化による解体・撤去工事のため2025年4月1日から休場、再開日は未定。2026年10月7日更新の江東区公式案内で確認。野球場・庭球場とも対象で、通常検索から除外します。'


def entry(ident, source, note, rows):
    return dict(old_entry(ident, source, note, rows), checked_at=CHECKED)


def reviewed_fees():
    result = []
    for index, page, amount, extra in [
        (0, 'p012122.html', 8000, '夜間照明は別途2時間18,000円。観戦者用駐車場なし。'),
        (1, 'p012126.html', 8000, 'ナイター料金を他の球場から転用しません。'),
        (2, 'p012128.html', 2000, 'ソフトボール専用。少年軟式野球は可能ですが、一般野球には使用できません。'),
        (4, 'p012123.html', 4000, '夜間照明は別途2時間6,000円。'),
        (5, 'p012125.html', 2000, '軟式野球・ソフトボール用。'),
        (10, 'p012127.html', 1000, '軟式野球場・ソフトボール場の各1面の料金。両面一括の料金ではありません。'),
    ]:
        unit = 'ソフトボール場1面・2時間' if index == 2 else '野球場1面・2時間'
        result.append(entry(HACHIOJI[index], HACHIJOJI + page,
                            '市公式の通常団体利用料金。事前利用者登録・予約・利用申請が必要。冬季休場・季節別時間区分あり。減免や器具代は別途。' + extra,
                            [('通常利用・照明別', amount, unit)]))
    result.append(entry(HACHIOJI[3], HACHIJOJI + 'p012069.html',
                        '上柚木公園陸上競技場の団体貸切4時間20,000円。夜間照明は別途4時間15,000円。50～200円の個人陸上利用、回数券や障害者の個人免除を貸切料金に混ぜません。事前申請が必要。',
                        [('団体貸切・照明別', 20000, '陸上競技場・4時間')]))
    result.append(entry(HACHIOJI[6], 'https://www.city.hachioji.tokyo.jp/life/010/002/003/004/p012068.html',
                        '既存の陸上競技場登録について、有料一般開放の個人1人1回料金のみ。大人200円、高校生100円、小中学生50円。貸切・イベント時は個人利用不可。別の無料地域開放時間は用器具・球技・団体占有不可であり、無料の団体貸切を意味しません。サッカー場としての団体貸切料金とは区別しています。',
                        [(label, value, '個人陸上利用・1人1回') for label, value in
                         [('大人', 200), ('高校生', 100), ('小・中学生', 50)]]))
    result.append(entry(HACHIOJI[9], HACHIJOJI + 'p012130.html',
                        '滝ガ原運動場の軟式野球場とソフトボール場を別単位で記録。いずれも1面2時間、硬式野球不可。登録・予約・申請が必要。季節別時間・早朝枠・冬季及び火曜休場は公式案内に従います。',
                        [('野球場・通常利用', 2000, '野球場1面・2時間'),
                         ('ソフトボール場・通常利用', 1000, 'ソフトボール場1面・2時間')]))
    result.append(entry(KITA[0], KITA_FACILITY + '1010397.html',
                        '中央公園野球場1面2時間、一般登録団体2,920円。夜間照明は別途2時間6,160円（合計9,080円）。少年登録団体は使用料免除ですが、照明まで無料とは推測しません。団体登録・承認が必要。少年登録は小中学生10名以上、10名中7名以上が北区在住在勤在学、代表副代表は18歳以上。区外少年登録不可、指定の少年利用時間帯に従います。',
                        [('一般登録団体・照明別', 2920, '野球場1面・2時間'),
                         ('区内少年登録団体・使用料免除', 0, '野球場1面・2時間')]))
    result.append(entry(KITA[1], KITA_FACILITY + '1010400.html',
                        '岩淵水門野球場は少年利用専用で使用料無料。一般成人の団体利用が無料という意味ではありません。北区の少年団体登録・承認が必要。小中学生10名以上、10名中7名以上が区内在住在勤在学、代表副代表18歳以上、区外少年登録不可。通常の時間区分は2時間。冬季日没による短縮枠は別途案内に従います。',
                        [('区内少年登録団体のみ', 0, '少年野球場1面・2時間')]))
    result.append(entry(KITA[2], KITA_FACILITY + '1010398.html',
                        '新荒川大橋野球場1面2時間、一般登録団体1,200円、区内少年登録団体は使用料免除。団体登録・承認必要。区外少年登録不可、少年は小中学生10名以上・10名中7名以上が北区在住在勤在学等の登録条件あり。一般用・少年用の指定面に従います。冬季日没による1時間枠を2時間料金から推測換算しません。',
                        [('一般登録団体', 1200, '野球場1面・2時間'),
                         ('区内少年登録団体・使用料免除', 0, '野球場1面・2時間')]))
    result.append(entry(KOTO[2], YUME,
                        '夢の島野球場の軟式野球場と少年野球場の各1面2時間。少年650～800円は区内小中学生登録団体のみ、それ以外は軟式野球場料金2,700～3,700円。少年用の区画と登録条件を区別しています。軟式野球の夜間照明は別途1時間4,600円、少年野球場に照明なし。準備整備込み、スポーツネット登録必要。会議室・撮影料・面積課金の運動広場・駐車料は範囲外。',
                        [('軟式野球場・平日', 2700, '軟式野球場1面・2時間'),
                         ('軟式野球場・土日祝', 3700, '軟式野球場1面・2時間'),
                         ('少年野球場・区内小中学生団体・平日', 650, '少年野球場1面・2時間'),
                         ('少年野球場・区内小中学生団体・土日祝', 800, '少年野球場1面・2時間')]))
    result.append(entry(KOTO[3], SHIOMI,
                        '潮見の軟式野球場・ソフトボール場は各1面2時間2,700～3,700円、庭球場は1面1時間1,100～1,800円。異なる種目・時間単位を分離。照明は野球・ソフトボール別途1時間4,600円、庭球場別途1時間1,800円。壁打ちの無料開放は庭球場の貸切とは別。準備整備込み、スポーツネット登録必要。会議室・駐車場別。',
                        [('軟式野球場・ソフトボール場・平日', 2700, '野球場・ソフトボール場1面・2時間'),
                         ('軟式野球場・ソフトボール場・土日祝', 3700, '野球場・ソフトボール場1面・2時間'),
                         ('庭球場・平日', 1100, '庭球場1面・1時間'),
                         ('庭球場・土日祝', 1800, '庭球場1面・1時間')]))
    return result


def policy(ident, source, summary):
    return dict(id=ident, status='conditional', source_url=source,
                checked_at=CHECKED, summary=summary)


def reviewed_policies():
    text = '利用しないと分かった時点で取消。前日までは予約システム、当日は各施設へ直接電話。屋外施設の当日・無断取消では、該当月の翌々月1日から3か月間、抽選申込・空き施設予約が不可。既存予約は有効。金銭の取消手数料ではなく予約制限です。雨天免除や還付割合はこの案内だけでは確認できません。'
    result = [policy(ident, HACHIJOJI_GUIDE, text +
                     ('高倉は1週間前までに富士森体育館で利用申請が必要。未申請もキャンセル・ペナルティ対象。' if ident == HACHIOJI[11] else ''))
              for ident in HACHIOJI if ident != HACHIOJI[7]]
    for ident in [KITA[0], KITA[2]]:
        result.append(policy(ident, KITA_GUIDE,
                             '14日前まで全額還付・振替、13～7日前は半額、6日前～当日は還付・振替なし。未払いでも13日前以降の取消は全額支払後に所定額を還付。支払前は予約システム、支払後は体育系窓口のみで取消、電話不可。登録メンバーによる手続きと証明書等が必要。無料少年使用に有料料金を課す意味ではありません。天候時の現地使用可否確認と、還付の条件・割合は区別し、未記載の雨天還付は推測しません。'))
    for ident, source in [(KOTO[2], YUME), (KOTO[3], SHIOMI)]:
        result.append(policy(ident, source,
                             '天候による利用可否は利用開始前に管理事務所へ確認。準備・片付け・整備も予約時間内。自己都合取消期限、金銭手数料、雨天中止時の還付割合は当該施設ページでは明記されていないため未確認。利用不可判断だけで自動返金とは扱いません。'))
    return result


def main():
    fees, policies = reviewed_fees(), reviewed_policies()
    validate(fees)
    assert len(set(REVIEWED_IDS)) == len(REVIEWED_IDS) == 26
    assert len(fees) == 14 and len(policies) == 15 and len(HOLDS) == 12
    assert set(REVIEWED_IDS) == {r['id'] for r in fees} | set(HOLDS)
    rows = {r['id']: r for r in get_catalog()['courts']}
    assert all(i in rows for i in REVIEWED_IDS)
    for row in fees:
        current = rows[row['id']]
        if current.get('fee_checked_at') != CHECKED and has_price(current):
            raise ValueError('Refusing to replace priced venue: ' + row['id'])
    for name, additions in [('fee_plans.json', fees), ('cancellation_policies.json', policies)]:
        existing = {r['id']: r for r in json.loads((CATALOGS / name).read_text(encoding='utf-8'))}
        for row in additions:
            if row['id'] in existing and existing[row['id']] != row:
                raise ValueError('Refusing to replace prior review: ' + row['id'])
    path = CATALOGS / 'tokyo_expansion.json'
    original = json.loads(path.read_text(encoding='utf-8'))
    closed = next(r for r in original if r['id'] == KOTO[0])
    if closed['availability_status'] not in ['UNKNOWN', 'SUSPENDED']:
        raise ValueError('Unexpected availability state')
    changed = closed['availability_status'] != 'SUSPENDED'
    if changed:
        closed.update(availability_status='SUSPENDED', availability_note=CLOSURE_NOTE, checked_at=CHECKED)
        closed['sources'].append({'title': '公式の休場・再開未定案内', 'url': CLOSURE_SOURCE})
    elif closed.get('availability_note') != CLOSURE_NOTE:
        raise ValueError('Refusing to replace another closure review')
    append_reviews(CATALOGS / 'fee_plans.json', fees)
    append_reviews(CATALOGS / 'cancellation_policies.json', policies)
    if changed:
        path.write_text(json.dumps(original, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(reviewed=26, prices_added=14, policies_added=15, new_closures=1)))


if __name__ == '__main__':
    main()
