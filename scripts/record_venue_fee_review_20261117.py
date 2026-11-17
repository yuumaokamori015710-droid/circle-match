"""Append November 17 official venue fees, keeping unlike units separate."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'outputs'))
from venues.fees import validate
from venues.sports_catalog import get_catalog, has_price
from record_venue_fee_review_20261018 import append_reviews, entry as previous_entry
from record_venue_fee_review_20261110 import SCHOOL_FEE, SCHOOL_UNIT

CHECKED = '2026-11-17'
BASE = '673eb05bbc8b7f868f64edcfe1f7e8cc42286c53'
CATALOGS = ROOT / 'outputs/venues/catalogs'
ARAKAWA = 'https://www.city.arakawa.tokyo.jp'
LIFELONG = ARAKAWA + '/a016/shougaigakushuu/centerriyou.html'
ACT = ARAKAWA + '/a001/seikatsu/jinkendanjo/act21riyou.html'
MACHIYA = ARAKAWA + '/a016/shougaigakushuu/gakushuushisetsu/matiyariyouannnai.html'
SUNNY = ARAKAWA + '/a015/bunkageijutsu/geijutu/sunnyhallriyou.html'
HOLDS = ['tokyo-venue-205d87234dd3']
RECHECKS = ['tokyo-venue-be48cc26a9d5']
SCHOOLS = {
    '48f2b19f32aa': '五日市', '708dac459baf': '府中西', 'f3bb67d38872': '南平',
    '88ff28ae1369': '拝島', '72bb9afece5c': '東久留米総合', 'eaa14d75feb4': '東大和南',
    '2bc379c7eece': '東大和', '19dd49439a46': '東村山西', '752d3bd89b5a': '東村山',
    'b6a5ed38dc81': '上水', 'e93b40315f11': '武蔵村山', '538269edad9e': '武蔵野北',
    'ecb1cdce90bf': '武蔵', 'abcc9130e7fc': '狛江', 'b6af34b461b6': '瑞穂農芸',
    'ea447b1514c1': '小川', 'a15283a0d104': '成瀬', 'c02f5ffe3fa2': '町田総合',
    '95f7248bd388': '多摩工科', 'a7cfe17084a4': '若葉総合',
}
HARD_ONLY = {'48f2b19f32aa', '708dac459baf', '88ff28ae1369', '72bb9afece5c',
             '19dd49439a46', 'b6a5ed38dc81', 'e93b40315f11', 'ea447b1514c1', 'a7cfe17084a4'}


def entry(ident, source, note, rows):
    return dict(previous_entry(ident, source, note, rows), checked_at=CHECKED)


def reviewed_fees():
    rows = [entry('tokyo-venue-d524a6778a50', LIFELONG,
        '荒川区立生涯学習センターの通常施設使用料。事前の利用者登録が必要、準備・片付けを含む。'
        '社会教育関係団体は会議室等50％減額、体育館・多目的広場は免除（区の共通案内）。'
        '第5会議室・学習室は2028年7月まで利用休止予定のため料金対象に含めません。'
        '音楽室の夜間は19～21時30分で他室より30分短い。多目的広場の夜間貸出はなし。'
        '広場は少年活動向けで、中学生以上への拡大利用は登録スポーツ団体の平日午前・午後1のみ。'
        '拡大利用では危険を及ぼす野球・サッカー等や大きな声・音楽を使う活動は不可。'
        '体育館用具は持参。一般の成人サッカー貸切や空き確保を意味しません。',
        [('大会議室・午前/午後1/午後2/夜間', 1000, '大会議室1室・3時間（通常）'),
         ('小会議室・第1/第3/第4・各時間帯', 500, '小会議室1室・3時間（通常・休止室除外）'),
         ('音楽室・午前/午後1/午後2', 750, '音楽室1室・3時間（通常）'),
         ('音楽室・夜間19～21時30分', 750, '音楽室1室・2時間30分（通常）'),
         ('多目的室・午前/午後1/午後2/夜間', 750, '多目的室1室・3時間（通常）'),
         ('体育館・9～12/12～15/15～18/18～21時', 1750, '体育館・3時間（通常）'),
         ('広場・9～12/12～15時、4～9月の15～18時', 500, '多目的広場・3時間（通常）'),
         ('広場・3月/10月の15～17時', 330, '多目的広場・2時間（通常）'),
         ('広場・11～2月の15～16時', 160, '多目的広場・1時間（通常）')])]
    act_rows = [(f'{room}・{slot}', amount, f'{room}・{unit}（通常）')
                for room, amounts in [('ホール', (6400, 7300, 20100)),
                                      ('第1会議室', (2400, 2700, 7500)),
                                      ('第2会議室', (900, 1100, 2900)),
                                      ('第3会議室（和室）', (1300, 1500, 4100)),
                                      ('創作室', (1900, 2100, 5900))]
                for (slot, unit), amount in zip(
                    [('午前9～12時30分/午後13時30分～17時', '3時間30分'),
                     ('夜間18～22時', '4時間'), ('全日9～22時', '全日13時間')], amounts)]
    rows.append(entry('tokyo-venue-fd87d6430730', ACT,
        'アクト21の通常施設使用料。準備・片付けを含み、附帯設備・持込器具電源料は別。'
        '男女平等推進団体は50％減額、一般利用へ自動適用しません。'
        '政治・宗教・営利活動を目的とする団体は利用不可。Web予約には事前の窓口利用者登録が必要。'
        '午前/午後3時間30分、夜間4時間、全日13時間は別単位。無料交流コーナーとは別です。', act_rows))
    machiya_rows = [(f'{room}・{slot}', amount, f'{room}・{unit}（通常）')
                   for room, amounts in [('多目的ホール', (5900, 4900, 22600)),
                                         ('音楽練習室', (1800, 1500, 6900)),
                                         ('第1会議室', (1500, 1300, 5800)),
                                         ('第2会議室', (2000, 1700, 7700)),
                                         ('第3会議室', (2300, 1800, 8700)),
                                         ('第4会議室', (2300, 1800, 8700))]
                   for (slot, unit), amount in zip(
                       [('午前9～12時/午後2の15時30分～18時30分/夜間19～22時', '3時間'),
                        ('午後1の12時30分～15時', '2時間30分'), ('全日9～22時', '全日13時間')], amounts)]
    rows.append(entry('tokyo-venue-41e834c7fc62', MACHIYA,
        '町屋文化センターの通常施設使用料。社会教育関係団体は50％減額、一般へ自動適用しません。'
        '午後1は2時間30分、午前・午後2・夜間は3時間、全日は13時間で混在させません。'
        'Web予約には利用者登録が必要。多目的ホールは空き照会のみでWeb予約不可。'
        '附帯設備や特別利用の追加料金・取消料は基本使用料に含みません。', machiya_rows))
    sunny_rows = [(f'{room}・{area}・{slot}', amount, f'{room}・{unit}（{area}通常）')
                  for room, charges in [('第1会議室', ((1500, 2200, 8200), (1600, 2400, 8800))),
                                        ('第2会議室', ((700, 1100, 3900), (750, 1200, 4200))),
                                        ('第3会議室', ((800, 1100, 4300), (850, 1200, 4600)))]
                  for area, amounts in zip(('区内', '区外'), charges)
                  for (slot, unit), amount in zip(
                      [('9～11時/11時30分～13時30分/14～16時/16時30分～18時30分', '2時間'),
                       ('夜間19～22時', '3時間'), ('全日9～22時', '全日13時間')], amounts)]
    rows.append(entry('tokyo-venue-81ea80a5de3d', SUNNY,
        '日暮里サニーホール第1～第3会議室の通常料金のみ。区内・区外、昼間2時間・夜間3時間・全日13時間を分離。'
        'ホールやコンサートサロン、附帯設備は別料金で、この表に含めません。'
        '入場料等5,001円以上の徴収は規定料金50％加算、展示・即売は区分等による追加料金あり。'
        '会議室Web予約には利用者登録が必要、予約後1週間以内の窓口申請・支払を案内。'
        '一般取消の返還割合・期限は今回の料金ページでは確認できていません。', sunny_rows))
    for suffix in SCHOOLS:
        sport = '硬式のみ' if suffix in HARD_ONLY else '硬式・軟式'
        rows.append(entry('school-' + suffix, SCHOOL_FEE,
            f'令和8年度の開放予定一覧で照合した屋外庭球場（{sport}）。無料は昼間の施設使用料のみ。'
            '主に都内在住・在勤・在学の10人以上の非営利・定期活動団体、20歳以上の責任者、'
            '学校ごとの毎年度登録と保険加入が必要。登録名簿掲載者の練習・練習試合が原則で、'
            '不特定多数の活動は不可。照明等の光熱費・保険料は含みません。'
            '共通制度説明の手続き例は令和6年度で、現行一覧・使用条件を併せて確認。'
            '時間単価・開放日時・各校の取消期限は推測せず、学校教育で中止・変更される場合があります。',
            [('昼間・施設使用料', 0, SCHOOL_UNIT)]))
    return rows


def reviewed_policies():
    return [dict(id='tokyo-venue-fd87d6430730', checked_at=CHECKED, status='conditional', source_url=ACT,
        summary='納付済み利用料は原則返還なし。取消理由により一部返還できる場合があり、'
        'ホールは利用15日前まで、会議室・創作室は5日前までの取消申請が対象。'
        '返還割合とそれ以降の返還額は当該ページに明記されておらず、無料取消とは扱いません。'
        '利用日変更は1回限り。屋内施設への雨天免除は確認できていません。'),
        dict(id='tokyo-venue-d524a6778a50', checked_at=CHECKED, status='conditional', source_url=LIFELONG,
        summary='熱中症特別警戒アラート発表時は屋外の多目的広場を使用中止。'
        '施設管理上の臨時休館もあり。自己都合取消の期限・手数料、雨天中止時の還付額は今回の案内では未確認。'
        '屋内体育館や会議室に屋外広場の中止条件・天候免除を一律適用しません。')]


REVIEWED_IDS = HOLDS + RECHECKS + [row['id'] for row in reviewed_fees()]


def main():
    fees, policies = reviewed_fees(), reviewed_policies()
    validate(fees)
    assert len(REVIEWED_IDS) == len(set(REVIEWED_IDS)) == 26
    assert len(fees) == 24 and len(policies) == 2
    rows = {r['id']: r for r in get_catalog()['courts']}
    assert set(REVIEWED_IDS) <= rows.keys()
    for suffix, name in SCHOOLS.items():
        assert '都立' + name + '高等学校 テニスコート' in rows['school-' + suffix]['name']
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
