"""Append verified daytime school-court fees without replacing prior reviews."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'outputs'))
from venues.fees import validate
from venues.sports_catalog import get_catalog, has_price
from record_venue_fee_review_20261018 import append_reviews, entry as previous_entry
from record_venue_fee_review_20261110 import SCHOOL_FEE, SCHOOL_UNIT

CHECKED = '2026-11-14'
BASE = '97468b6ef263dc12713444154b2fdd2801505b11'
CATALOGS = ROOT / 'outputs/venues/catalogs'
SCHOOL_LIST = ('https://www.syougai.metro.tokyo.lg.jp/sesaku/kaihou/files/taiiku/'
               'kensakuyou_20260625.xlsx')
SCHOOL_RULES = 'https://www.syougai.metro.tokyo.lg.jp/sesaku/kaihou/youken.html'
HOLDS = ['tokyo-venue-205d87234dd3']
RECHECKS = ['tokyo-venue-80dd6145978b']
SCHOOLS = {
    '259c06b6fa31': '世田谷泉', 'c64f582ad283': '世田谷総合', '7a794c5b322d': '千歳丘',
    '466d77ca642c': '桜町', 'c53efbc8b8c2': '深沢', 'cd0aef40728b': '芦花',
    'a4c1a9575d7e': '日本橋', '93018cb6557c': '本所',
    '9db05d4da333': 'つばさ総合', 'f1b1a4a64e5d': '大森', '28ea9ad4b487': '田園調布',
    'af025ea5a8e3': '美原', '69e67c4e20cd': '蒲田', '362ff8a03c9d': '雪谷',
    '84797d71e2f2': '小岩', 'c6e597e40d23': '小松川', '054db3fe8228': '篠崎',
    '703a8f9a6922': '紅葉川', 'a3f9ce1edde3': '葛西南', '75a9b4e237e6': '葛西工科',
    '35eae98f2594': '青山', '4be01ccc32ce': '三田', 'a5bbd14df784': '国際',
    '82caa2098b3b': '桜修館中等教育学校',
}
HARD_ONLY = {'7a794c5b322d', 'a4c1a9575d7e', '84797d71e2f2', '054db3fe8228',
             'a3f9ce1edde3', '35eae98f2594', '4be01ccc32ce', 'a5bbd14df784'}
SOFT_ONLY = {'28ea9ad4b487'}


def reviewed_fees():
    rows = []
    for suffix in SCHOOLS:
        sport = '軟式のみ' if suffix in SOFT_ONLY else '硬式のみ' if suffix in HARD_ONLY else '硬式・軟式'
        note = (
            f'令和8年度の都立学校開放に掲載された屋外庭球場（{sport}）。無料は昼間の施設使用料のみ。'
            '都内在住・在勤・在学者が主な10人以上の非営利・定期活動の登録団体が対象で、'
            '責任者は満20歳以上。登録名簿に載る者の練習・練習試合が原則で、不特定多数の活動は不可。'
            '保険加入が必要。照明等の光熱費・保険料は含みません。学校ごとに毎年度の登録が必要。'
            '開放日時・追加条件は学校別に確認し、教育活動で開放が中止・変更される場合があります。'
        )
        rows.append(dict(previous_entry('school-' + suffix, SCHOOL_FEE, note,
            [('昼間・施設使用料', 0, SCHOOL_UNIT)]), checked_at=CHECKED))
    return rows


REVIEWED_IDS = HOLDS + RECHECKS + [row['id'] for row in reviewed_fees()]


def main():
    fees = reviewed_fees()
    validate(fees)
    assert len(REVIEWED_IDS) == len(set(REVIEWED_IDS)) == 26
    assert len(fees) == 24 and not (HARD_ONLY & SOFT_ONLY)
    rows = {r['id']: r for r in get_catalog()['courts']}
    assert set(REVIEWED_IDS) <= rows.keys()
    for suffix, name in SCHOOLS.items():
        school = name if name.endswith('学校') else name + '高等学校'
        assert '都立' + school + ' テニスコート' in rows['school-' + suffix]['name']
    old = {r['id']: r for r in json.loads((CATALOGS / 'fee_plans.json').read_bytes())}
    for fee in fees:
        if has_price(rows[fee['id']]) and rows[fee['id']].get('fee_checked_at') != CHECKED:
            raise ValueError('Refusing to replace priced venue: ' + fee['id'])
        if fee['id'] in old and old[fee['id']] != fee:
            raise ValueError('Refusing to replace prior review: ' + fee['id'])
    append_reviews(CATALOGS / 'fee_plans.json', fees)
    print(json.dumps(dict(reviewed=len(REVIEWED_IDS), prices_added=len(fees), policies_added=0)))


if __name__ == '__main__':
    main()
