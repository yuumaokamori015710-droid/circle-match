"""Append verified room/field tariffs; preserve previous reviews and venue identities."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'outputs'))
from venues.fees import validate
from venues.sports_catalog import get_catalog, has_price
from record_venue_fee_review_20261018 import append_reviews, entry as old_entry

CHECKED = '2026-10-28'
BASE = '83d63902d840ddfd5b866e7e5575357d2995c030'
CATALOGS = ROOT / 'outputs/venues/catalogs'
NERIMA = 'https://www.city.nerima.tokyo.jp/shisetsu/community/chikukuminkan/'
NERIMA_GUIDE = NERIMA + '1119.html'
NERIMA_PAYMENT = NERIMA + 'kaisuukenn.html'
DISTRICTS = [
    ('tokyo-venue-fb993a9bd6f1', 'kitamachi', [('会議室', 200), ('多目的室', 100), ('大広間', 300), ('和室', 200), ('音楽室', 300), ('レクルーム', 400)]),
    ('tokyo-venue-f9757579e50e', 'hayamiya', [('大広間', 400), ('和室', 100), ('会議室（1階）', 200), ('会議室（2階）', 200), ('レクルーム', 400), ('多目的室', 300)]),
    ('tokyo-venue-88a2836410aa', 'sakuradai', [('大広間', 300), ('和室', 100), ('会議室', 200), ('音楽室', 100), ('多目的室', 100), ('レクルーム', 300)]),
    ('tokyo-venue-18ca308ccdfb', 'hikawadai', [('大広間', 400), ('和室', 100), ('レクルーム', 600), ('会議室', 100), ('音楽室', 300), ('多目的室', 200)]),
    ('tokyo-venue-e50943c53e95', 'toyotama', [('大広間', 300), ('会議室2', 100), ('会議室1', 200), ('会議室3', 100), ('おやこ広場', 200), ('レクルーム', 300), ('図書室', 100)]),
    ('tokyo-venue-4d2338f59594', 'takamatsu', [('多目的室', 200), ('レクルーム', 300), ('集会室', 100), ('図書・会議室', 100)]),
]
HIKARI = 'tokyo-venue-caef0b487244'
HIKARI_SOURCE = 'https://www.city.nerima.tokyo.jp/shisetsu/bunka/kuminhall/hikarigaokakuminnhor.html'
SEKI = 'tokyo-venue-b87866a9fdd9'
SEKI_SOURCE = 'https://www.nerima-swf.jp/datas/seki_hol/pdf/020260815111033_SJE3r.pdf'
TRACK = 'tokyo-sports-031'
TRACK_SOURCE = 'https://www.shisetsu-tds.jp/tokyo-itabashi-shingashi-rikujou/fee/'
MUSASHINO = 'tokyo-venue-c698a2f4c1f9'
MUSASHINO_SOURCE = 'https://www.musashino.or.jp/_res/projects/default_project/_page_/001/001/568/1001568-02.pdf'
MUSASHINO_GUIDE = 'https://www.musashino.or.jp/sports/1001550/1001568.html'
CHOFU = ['tokyo-venue-294da8909003', 'tokyo-venue-6832b2db0714']
CHOFU_SOURCES = ['https://www.city.chofu.lg.jp/040070/p026093.html', 'https://www.city.chofu.lg.jp/040070/p026082.html']
PRIORITY_HOLDS = ['tokyo-gym-a231878afdcf', 'tokyo-gym-aa77f48e78d0', 'tokyo-gym-d56f81f38406',
                  'tokyo-venue-2b0bbd7157ff', 'tokyo-venue-8e6c0f81a52c', 'tokyo-venue-205d87234dd3']
PRIVATE_HOLDS = ['private-chitose', 'private-nanbu', 'private-santopia']
HOLDS = PRIORITY_HOLDS + PRIVATE_HOLDS
REVIEWED_IDS = PRIORITY_HOLDS + [r[0] for r in DISTRICTS] + [HIKARI, SEKI, TRACK, MUSASHINO] + CHOFU + PRIVATE_HOLDS


def entry(ident, source, note, rows):
    return dict(old_entry(ident, source, note, rows), checked_at=CHECKED)


def reviewed_fees():
    result = []
    for ident, slug, rooms in DISTRICTS:
        note = ('区公式の各室1時間料金。一般の施設利用登録と、5名以上・半数以上が区内在住在勤在学等を要件とする地域集会施設団体登録を区別。'
                '後者は通常料金の半額。適用条件ごとに単位を分離し、75歳以上団体等の個別免除は料金範囲に含めません。'
                '2026年7月以降の新システムで再登録が必要。営利利用・不特定多数募集不可。児童・敬老・子育て開放中は貸切不可、室別用途・定員・防音制限に従います。'
                '無料の個人開放や学童・ロビーを貸切の無料枠とは扱いません。減額根拠：' + NERIMA_GUIDE)
        rows = [(room + ' / ' + group, amount // divisor, room + '・1時間（' + group + '）')
                for room, amount in rooms for group, divisor in [('一般', 1), ('地域集会施設登録団体', 2)]]
        result.append(entry(ident, NERIMA + slug + '.html', note, rows))
    rows = []
    for room, morning, later in [('多目的ホール', 5400, 7200), ('集会室1', 1800, 2400),
                                 ('集会室2', 1800, 2400), ('集会室1・2併用', 3300, 4400),
                                 ('会議室1', 2100, 2800), ('会議室2', 1800, 2400)]:
        rows += [(room + ' / 午前9～12時', morning, room + '・3時間'),
                 (room + ' / 午後13～17時・夜間17時30分～21時30分', later, room + '・4時間')]
    result.append(entry(HIKARI, HIKARI_SOURCE,
                        '光が丘区民ホールの明示した6室のみの通常料金。3時間と4時間、単室と併用を区別。会議室1は2026年8月1日利用再開。事前利用登録と用途審査が必要。飲食目的不可、会議室2はダンス不可。保育専用室、音楽室、美術工芸室、和室、心身障害者福祉集会所と付帯設備は今回の料金範囲に含みません。区公式ページの予約日程と新システムの現行案内を併せて確認してください。', rows))
    result.append(entry(SEKI, SEKI_SOURCE,
                        '指定管理者の2026年8月7日発行案内10頁を確認。多目的ホールは午前3時間、午後・夜間4時間、リハーサル室は新システムで1時間単位。旧3区分のリハーサル料金へ転用しません。はつらつセンター目的外利用室・設備は範囲外。営利利用不可、不特定多数を集める利用不可、用途ごとの制限あり。多目的ホールは2週間前までの事前打合せが必要で2週間を切ると予約・延長不可。',
                        [('多目的ホール / 午前9～12時', 5400, '多目的ホール・3時間'),
                         ('多目的ホール / 午後13～17時・夜間17時30分～21時30分', 7200, '多目的ホール・4時間'),
                         ('リハーサル室 / 時間貸し', 400, 'リハーサル室・1時間')]))
    result.append(entry(TRACK, TRACK_SOURCE,
                        '新河岸陸上競技場の団体貸切のみ、1時間3,600円。団体登録必要。個人利用30～180円は団体占有不可なので別です。既存レコード名にある多目的運動場や、荒川戸田橋のフィールドの料金を含みません。器具・駐車場別。季節別開場時間あり。',
                        [('団体貸切', 3600, '新河岸陸上競技場・1時間')]))
    result.append(entry(MUSASHINO, MUSASHINO_SOURCE,
                        '武蔵野軟式野球場1面2時間、市内2,000円・市外団体倍額4,000円。参加料等を徴収しない通常貸切の範囲。参加料徴収時は別途3倍額の規定があり、市外割増との併用額は未確認のため採用しません。夏季最終枠も2時間。事前利用者登録・予約が必要。高反発複合バット不可。個人利用・他施設の料金は含みません。',
                        [('市内・参加料等の徴収なし', 2000, '軟式野球場1面・2時間（市内・参加料なし）'),
                         ('市外・参加料等の徴収なし', 4000, '軟式野球場1面・2時間（市外・参加料なし）')]))
    result.append(entry(CHOFU[0], CHOFU_SOURCES[0],
                        '市民西町野球場1面、9～11・11～13・13～15・15～17時の各2時間枠3,000円。市民西町少年野球場・都立公園一般野球場とは別施設。事前団体登録が必要。当日現地でカード提示・支払い、駐車場有料。1・2月等は休場。市外別単価は当該案内に明記がなく推測しません。',
                        [('通常貸切', 3000, '野球場1面・2時間')]))
    result.append(entry(CHOFU[1], CHOFU_SOURCES[1],
                        '市民野球場の団体貸切。通常2時間と18～21時の3時間を区別、市外は各倍額。照明は別途30分2,000円。事前団体登録必要。11・3月は16時以降使用不可、1・2月等休場。個人用シルバー割引等を団体料金に混ぜません。',
                        [('市内・通常枠', 1200, '野球場1面・2時間（市内）'), ('市外・通常枠', 2400, '野球場1面・2時間（市外）'),
                         ('市内・18～21時', 1800, '野球場1面・3時間（市内・照明別）'), ('市外・18～21時', 3600, '野球場1面・3時間（市外・照明別）')]))
    return result


def policy(ident, source, text):
    return dict(id=ident, status='conditional', source_url=source, checked_at=CHECKED, summary=text)


def reviewed_policies():
    result = [policy(ident, NERIMA_PAYMENT,
                     '支払済み使用料は特別な理由以外払い戻し不可と区公式が明記。通常取消の締切・予約制限の詳細や天候時の免除はこの支払い案内だけでは未確認。地区区民館の規則を区民ホールに転用しません。') for ident, _, _ in DISTRICTS]
    result.append(policy(SEKI, SEKI_SOURCE,
                         '利用日の1週間を切る取消はペナルティ。直前取消は翌日から30日、無断取消は翌日から90日間Web抽選・予約不可。開始後は原則無断扱い、終了前までの利用料支払い・利用報告で回避可能という施設特例あり。同日複数取消は1回扱い。短縮にも同様の扱い、多目的ホールは2週間前打合せ必要で以後予約・延長不可。金銭の取消料・還付率・天候時の免除は未確認。'))
    result.append(policy(TRACK, TRACK_SOURCE,
                         '当日の天候・グラウンド状況を利用開始前に確認。施設から中止連絡はしません。天候・グラウンド状況による中止は利用料還付、承認書を持ち体育館・温水プール窓口で手続き（口座振替団体は手続き不要）。自己都合取消の期限・還付率は当該案内では未確認。'))
    result.append(policy(MUSASHINO, MUSASHINO_GUIDE,
                         '初回枠は当日8時30分、以降は各回2時間前に利用可否決定。施設中止では取消連絡不要だが、中止決定時に利用時間の半分（1時間）を超過していると返金対象外。事業団が利用者判断と決定した悪天候・暑さ等で利用しない場合は連絡必須、開始から60分以内に連絡がないと返金対象外。自己都合の取消期限・還付率はこの施設案内では未確認。'))
    for ident, source in zip(CHOFU, CHOFU_SOURCES):
        result.append(policy(ident, source,
                             '前日までシステム取消可。当日は利用開始前までに現地へ連絡し、当日取消は1か月、開始後の連絡・無連絡は無断取消で3か月の新規予約停止。これは予約制限であり金銭の取消料ではありません。開始前に天候可否確認・取消連絡が必要。' +
                             ('利用時間の半分に達する前に現地降雨で使用不可ならペナルティなし、連絡は必要。' if ident == CHOFU[0] else '雨天等の使用可否は直接管理事務所に確認。') + '未記載の現金還付割合は推測しません。'))
    result.append(policy('private-chitose', 'https://tennis.chitose.jp/rentalcoat/',
                         '3日前30%、2日前・前日50%、当日70%、無断100%の取消料。振込手数料は利用者負担。天候不順の利用判断は当日1時間前、電話確認が必要。4日前以前の無料取消や悪天候時の返金・免除は当該案内に明記がなく推測しません。'))
    return result


def main():
    fees, policies = reviewed_fees(), reviewed_policies()
    validate(fees)
    assert len(set(REVIEWED_IDS)) == len(REVIEWED_IDS) == 21
    assert len(fees) == 12 and len(policies) == 12 and len(HOLDS) == 9
    assert set(REVIEWED_IDS) == {r['id'] for r in fees} | set(HOLDS)
    rows = {r['id']: r for r in get_catalog()['courts']}
    assert all(ident in rows for ident in REVIEWED_IDS)
    for row in fees:
        current = rows[row['id']]
        if current.get('fee_checked_at') != CHECKED and has_price(current):
            raise ValueError('Refusing to replace priced venue: ' + row['id'])
    for name, additions in [('fee_plans.json', fees), ('cancellation_policies.json', policies)]:
        existing = {r['id']: r for r in json.loads((CATALOGS / name).read_text(encoding='utf-8'))}
        for row in additions:
            if row['id'] in existing and existing[row['id']] != row:
                raise ValueError('Refusing to replace prior review: ' + row['id'])
    append_reviews(CATALOGS / 'fee_plans.json', fees)
    append_reviews(CATALOGS / 'cancellation_policies.json', policies)
    print(json.dumps(dict(reviewed=21, prices_added=12, policies_added=12, holds=9)))


if __name__ == '__main__':
    main()
