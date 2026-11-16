"""Append the November 16 official-source tariff review without replacing data."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'outputs'))
from venues.fees import validate
from venues.sports_catalog import get_catalog, has_price
from record_venue_fee_review_20261018 import append_reviews, entry as previous_entry
from record_venue_fee_review_20261110 import SCHOOL_FEE, SCHOOL_UNIT

CHECKED = '2026-11-16'
BASE = '044da3f36b569681fc64be073f87ac8269fa026d'
CATALOGS = ROOT / 'outputs/venues/catalogs'
NANBU = 'https://nanbu-tc.sunnyday.jp/rentalcourt-rate.html'
NANBU_USE = 'https://nanbu-tc.sunnyday.jp/rentalcourt-use.html'
KUGAYAMA = 'https://kugayama-tennis.com/ryoukin.html'
HOLDS = ['tokyo-venue-205d87234dd3', 'private-chitose', 'private-santopia']
RECHECKS = ['tokyo-venue-be48cc26a9d5']
SCHOOLS = {
    'e890c2a951ca': '駒場', 'c2a0489bad1b': '南葛飾', 'cd6826b64715': '農産',
    '6897a4f835bf': '千早', '9a74de07afc3': '豊島', 'd6e171e13edd': '三鷹中等教育学校',
    '467b52342ac2': '八王子北', '835a6dd28f13': '八王子拓真', '446dc98645ef': '八王子桑志',
    '6a9c7a03ed11': '富士森', '783ac2187f25': '松が谷', '4491d27d006a': '国立',
    '7060fcc801cc': '第五商業', '798aa619b31e': '永山', 'cd8d6e22f9eb': '小平南',
    'deb360af22ba': '小平西', '58256cb22d64': '多摩科学技術', '91e516d865f0': '小金井北',
    '7df520ab2d90': '府中工科', 'ebc64ad4158d': '府中東',
}
HARD_ONLY = {'c2a0489bad1b', '9a74de07afc3', 'd6e171e13edd', '446dc98645ef',
             '6a9c7a03ed11', '783ac2187f25', '798aa619b31e', 'deb360af22ba',
             '91e516d865f0', '7df520ab2d90', 'ebc64ad4158d'}


def entry(ident, source, note, rows):
    return dict(previous_entry(ident, source, note, rows), checked_at=CHECKED)


def reviewed_fees():
    rows = [entry('private-nanbu', NANBU,
        '硬式テニス専用、コート料は税込の1時間単位。日中と日没後のナイターを分離。'
        '別途1人300円の施設料、新規・期限切れは代表者1名の登録料600円（1年間有効）が必要。'
        '1面8名まで、9名以上は超過人数×時間×550円が追加。半面は日中・2名までの相席制度で、'
        'カード所持者が利用90分前から予約可。通常予約はカード所持者1か月前、新規等は2週間前。'
        '曜日別の終了時刻には料金表と利用方法ページで記載差があるため公式へ確認。',
        [('平日・日中', 3700, 'コート1面・1時間（税込・施設料別）'),
         ('平日・ナイター', 6200, 'コート1面・1時間（税込・施設料別）'),
         ('土日祝・日中', 6200, 'コート1面・1時間（税込・施設料別）'),
         ('土日祝・ナイター', 7300, 'コート1面・1時間（税込・施設料別）'),
         ('平日・日中半面', 2000, 'コート半面・1時間（税込・2名まで・施設料別）'),
         ('土日祝・日中半面', 3500, 'コート半面・1時間（税込・2名まで・施設料別）')]),
        entry('private-kugayama', KUGAYAMA,
        '貸コート1面1時間、最小利用単位1時間・前払い。電話予約を案内。'
        '曜日と午前中・午後・17時以降を分離。オートテニスの料金や会場全体の貸切とは別。'
        '照明等の追加料金の有無は当該案内で明記されていません。',
        [(f'{day}・{period}', amount, '貸コート1面・1時間')
         for day, amounts in [('平日', (2200, 2750, 3850)), ('土日祝', (5500, 5500, 6600))]
         for period, amount in zip(('午前中', '午後', '17時以降'), amounts)])]
    for suffix in SCHOOLS:
        sport = '硬式のみ' if suffix in HARD_ONLY else '硬式・軟式'
        rows.append(entry('school-' + suffix, SCHOOL_FEE,
            f'令和8年度の都立学校開放に掲載された屋外庭球場（{sport}）。無料は昼間の施設使用料のみ。'
            '都内在住・在勤・在学者が主な10人以上の非営利・定期活動の登録団体が対象で、責任者は満20歳以上。'
            '学校ごとの毎年度登録と保険加入が必要。登録名簿に載る者の練習・練習試合が原則で、'
            '不特定多数の活動は不可。照明等の光熱費・保険料は含みません。'
            '開放日時と学校別条件は公式一覧で確認し、教育活動で中止・変更される場合があります。',
            [('昼間・施設使用料', 0, SCHOOL_UNIT)]))
    return rows


def reviewed_policies():
    return [dict(id='private-nanbu', checked_at=CHECKED, status='conditional', source_url=NANBU_USE,
        summary='1面1時間を1コマとする。1～3コマは火曜定休を除く3日前まで無料、2日前30%、前日50%、'
        '当日2時間前までは70%（料金表では11時以降の予約に限定）、以降全額。4～5コマ全取消は1週間前まで無料、'
        '以降全額。6コマ以上の全取消は全額。部分取消の上限・期限は料金表と利用方法に記載差があり、予約前に確認。'
        '天候不順は開始1時間前に施設が判断し電話確認が必要。使用可能時の自己都合取消は有料。'
        '雨天途中精算は2時間単位で1時間以上経過なら成立、1時間未満なら1時間分を返金。1時間利用のみでは返金なし。'
        '大口や通常より早い受付の特例は部分取消も制限されるため個別確認。'),
        dict(id='private-kugayama', checked_at=CHECKED, status='conditional', source_url=KUGAYAMA,
        summary='3日前まで取消料なし、2日前・前日はプレー料金の50%、当日は100%。'
        '雨天による中止の場合は取消料なし。貸コートの条件であり、オートテニスとは別。')]


REVIEWED_IDS = HOLDS + RECHECKS + [row['id'] for row in reviewed_fees()]


def main():
    fees, policies = reviewed_fees(), reviewed_policies()
    validate(fees)
    assert len(REVIEWED_IDS) == len(set(REVIEWED_IDS)) == 26
    assert len(fees) == 22 and len(policies) == 2
    rows = {r['id']: r for r in get_catalog()['courts']}
    assert set(REVIEWED_IDS) <= rows.keys()
    for suffix, name in SCHOOLS.items():
        school = name if name.endswith('学校') else name + '高等学校'
        assert '都立' + school + ' テニスコート' in rows['school-' + suffix]['name']
    for fee in fees:
        if has_price(rows[fee['id']]) and rows[fee['id']].get('fee_checked_at') != CHECKED:
            raise ValueError('Refusing to replace priced venue: ' + fee['id'])
    for name, additions in [('fee_plans.json', fees), ('cancellation_policies.json', policies)]:
        old = {r['id']: r for r in json.loads((CATALOGS / name).read_bytes())}
        for row in additions:
            if row['id'] in old and old[row['id']] != row:
                raise ValueError('Refusing to replace prior review: ' + row['id'])
        append_reviews(CATALOGS / name, additions)
    print(json.dumps(dict(reviewed=len(REVIEWED_IDS), prices_added=len(fees), policies_added=len(policies))))


if __name__ == '__main__':
    main()
