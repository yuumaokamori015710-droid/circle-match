"""Append the November 10 official-source venue review."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'outputs'))
from venues.fees import validate
from venues.sports_catalog import get_catalog, has_price
from record_venue_fee_review_20261018 import append_reviews, entry as previous_entry

CHECKED = '2026-11-10'
BASE = 'dbcf433ab9992a7917d542124d9847e0584f1324'
CATALOGS = ROOT / 'outputs/venues/catalogs'
PARK_RULE = 'https://www.reiki.metro.tokyo.lg.jp/reiki/reiki_honbun/g101RG00001485.html'
ADACHI = 'https://www.city.adachi.tokyo.jp'
ADACHI_CANCEL = ADACHI + '/sports/sports-facilities-outside.html'
EAST_PARK = 'https://tokyo-eastpark.com'
TACHIKAWA = 'https://www.city.tachikawa.lg.jp'
TACHIKAWA_GUIDE = TACHIKAWA + '/_res/projects/default_project/_page_/001/008/085/tebiki_20260801.pdf'
SCHOOL_FEE = ('https://club-tokyo-sports.jp/club_wp/wp-content/uploads/'
              '%E9%80%A3%E7%B5%A1%E5%8D%94%E8%AD%B0%E4%BC%9A%E2%91%A0.pdf')
SCHOOL_UNIT = '庭球場・昼間の施設使用料（登録団体・照明なし）'
AKIRUDAI = 'tokyo-venue-2b0bbd7157ff'
HOLDS = ['tokyo-venue-205d87234dd3']

SCHOOLS = {
    'e60c7e7035dd': '王子総合', '3e251f4715c2': '赤羽北桜', '9a3c9d3fbf47': '飛鳥',
    '0e79200066c6': '竹台', '2b966c096121': '荒川工科', '501ffaa0d70e': '北豊島工科',
    '7de409e5a91e': '板橋有徳', '8c1acc612b2e': '板橋', '69a8728e295f': '井草',
    'cda05260b36e': '光丘', '41ee58abf075': '大泉桜', '39e6b314d3d0': '練馬',
    'dbbb7a9721c1': '足立工科', '90607ae66368': '足立西', '969bf020ce14': '青井',
}
HARD_ONLY = {'7de409e5a91e', 'cda05260b36e', '969bf020ce14'}
ADACHI_FIELDS = {
    'c557a7408e05': (1100, '/sports/shisetsu/koen/029.html', ''),
    '6fe3fc68a882': (1400, '/documents/9417/17hokima.pdf', '照明なし。冬季の時間は施設案内を確認。'),
    'e1fc716b3101': (1400, '/documents/9419/yanaka-park.pdf',
                     '照明なし。12月第2日曜の翌日から2月末までは芝生養生のため利用不可。'),
}


def venue(suffix):
    return 'tokyo-venue-' + suffix


def entry(ident, source, note, rows):
    return dict(previous_entry(ident, source, note, rows), checked_at=CHECKED)


def reviewed_fees():
    rows = [entry(AKIRUDAI, PARK_RULE,
        '都立公園条例施行規則別表第五の団体貸切。サッカーは貸切時の芝生フィールドのみ。'
        '12月1日から3月31日までは芝生での競技不可。陸上トラックの無料個人利用とは別。'
        '都内小中学校の区分と、それ以外の学校およびこれに準ずる団体の区分を分離。',
        [(f'{category}・{slot}', amount, f'競技場貸切・{slot}（{category}）')
         for category, amounts in [('一般団体', (15800, 21600)), ('都内小中学校', (5000, 6000)),
                                   ('その他の学校等', (7200, 9400))]
         for slot, amount in zip(('午前9～12時', '午後13～17時'), amounts)])]
    for suffix, (amount, path, note) in ADACHI_FIELDS.items():
        rows.append(entry(venue(suffix), ADACHI + path,
            '足立区の野球場使用料。1面2時間、利用者登録が必要。駐車料は含みません。' + note,
            [('野球場・通常枠', amount, '野球場1面・2時間')]))
    rows.append(entry(venue('f88290b749c0'), EAST_PARK + '/parksearch/higashiayase',
        '都立東綾瀬公園の庭球場と野球場。テニスは曜日によらず同額。野球は平日と土日祝で異なります。'
        '照明は1面1時間につきテニス500円、野球1500円が別途必要。12～2月は16時まで。',
        [('庭球場・基本', 1300, '庭球場1面・1時間（照明別）'),
         ('野球場・平日', 1200, '野球場1面・1時間（照明別）'),
         ('野球場・土日祝', 1500, '野球場1面・1時間（照明別）')]))
    rows.append(entry(venue('b9706845abf5'), TACHIKAWA + '/shisetsu/1008063/1024068.html',
        '登録団体による立川公園陸上競技場の貸切。市内と市外、午前・午後・全日を分離。'
        '団体予約のない時間の無料個人開放には、この貸切料金は適用されません。',
        [(f'{area}・{slot}', amount, f'陸上競技場貸切・{slot}（{area}）')
         for area, amounts in [('市内団体', (8000, 10000, 18000)), ('市外団体', (16000, 20000, 36000))]
         for slot, amount in zip(('午前9～12時', '午後13～17時', '全日9～17時'), amounts)]))
    rows.append(entry(venue('836ab2108e32'), TACHIKAWA_GUIDE,
        '見影橋公園野球場兼陸上競技場の全面を登録団体で貸切。2時間枠で使用当日に支払い。'
        '野球の東面・西面の部分利用と、空き時間の無料個人開放とは別。',
        [('市内団体', 1500, '兼用競技場全面・2時間（市内団体）'),
         ('市外団体', 3000, '兼用競技場全面・2時間（市外団体）')]))
    for suffix in SCHOOLS:
        sport = '硬式のみ' if suffix in HARD_ONLY else '硬式・軟式'
        rows.append(entry('school-' + suffix, SCHOOL_FEE,
            f'令和8年度の都立学校開放に掲載された屋外庭球場（{sport}）。無料は昼間の施設使用料のみ。'
            '都内在住・在勤・在学者が主な10人以上の非営利の登録団体が対象で、'
            '責任者は満20歳以上。登録名簿に載る者が利用し、保険加入が必要。'
            '照明等の光熱費・保険料は含みません。開放日時と学校別条件は公式一覧で確認。',
            [('昼間・施設使用料', 0, SCHOOL_UNIT)]))
    return rows


def reviewed_policies():
    def policy(ident, source, summary):
        return dict(id=ident, checked_at=CHECKED, status='conditional', source_url=source, summary=summary)

    rows = [policy(venue(suffix), ADACHI_CANCEL,
        '支払方法入力前は予約システムか窓口で取消可。支払い後は利用2日前までに窓口で申請し、'
        '支払い翌日から3日以内なら全額、その後は半額。利用前日・当日の自己都合は還付なし。'
        '当日の雨・積雪や現地判断による強風・グラウンド不良で利用不可なら還付の対象。'
        '天気予報だけで雨天還付は不可。還付は施設使用承認書を提示。暑さによる還付は区の別条件。')
        for suffix in ADACHI_FIELDS]
    rows.append(policy(venue('f88290b749c0'), EAST_PARK + '/question',
        'テニスは利用4日前、野球は8日前までにスポレクで取消。期限後はペナルティ対象。'
        '荒天時は自己取消せず施設へ連絡。通常の取消は施設窓口では不可。'
        'この案内では金銭の取消料・荒天時の返金率は未確認。'))
    rows.append(policy(venue('b9706845abf5'), TACHIKAWA_GUIDE,
        '前払い施設。通常のシステム取消は使用7日前まで。支払期限内の連絡と無連絡の自動取消は別扱い。'
        '直前取消・同一枠の反復取消は新規予約1か月停止、無断は2か月停止。'
        '支払い後の自己都合還付なし。雨などによる中止は還付対象で、利用可否は現地管理人に確認。'))
    rows.append(policy(venue('836ab2108e32'), TACHIKAWA_GUIDE,
        '当日現地払いの施設。前日までシステムで取消可。当日は開始前に管理人へ連絡すると直前取消扱い。'
        '直前取消は新規予約1か月停止、開始後連絡・無断は2か月停止。支払い後の自己都合還付なし。'
        '雨天時の利用可否は現地管理人に確認。'))
    return rows


REVIEWED_IDS = HOLDS + [row['id'] for row in reviewed_fees()]


def main():
    fees, policies = reviewed_fees(), reviewed_policies()
    validate(fees)
    assert len(REVIEWED_IDS) == len(set(REVIEWED_IDS)) == 23
    assert len(fees) == 22 and len(policies) == 6
    rows = {r['id']: r for r in get_catalog()['courts']}
    assert set(REVIEWED_IDS) <= rows.keys()
    assert {r['id'] for r in policies} <= set(REVIEWED_IDS)
    for suffix, name in SCHOOLS.items():
        assert name + '高等学校 テニスコート' in rows['school-' + suffix]['name']
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
    print(json.dumps(dict(reviewed=len(REVIEWED_IDS), prices_added=len(fees), policies_added=len(policies))))


if __name__ == '__main__':
    main()
