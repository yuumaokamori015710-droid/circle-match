"""Append official tariffs; retain identities, booking URLs and earlier reviews."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'outputs'))
from venues.fees import validate
from venues.sports_catalog import get_catalog, has_price
from record_venue_fee_review_20261018 import append_reviews, entry as old_entry

CHECKED = '2026-10-20'
CATALOGS = ROOT / 'outputs/venues/catalogs'
TACHIKAWA = 'https://www.city.tachikawa.lg.jp/_res/projects/default_project/_page_/001/008/085/tebiki_20260801.pdf'
NISHITOKYO = 'https://www.city.nishitokyo.lg.jp/enjoy/sports/sports_shisetu/50981020151125.files/homepage.pdf'
OI_FEE = 'https://tokyo-south-seaside-parks.com/oi-hockey-price/'
OI_GUIDE = 'https://tokyo-south-seaside-parks.com/oi-hockey-guide/'
SHIBA_SOURCE = 'https://minatoku-sports.com/facilities/aqua/'
EDOGAWA = 'https://www.city.edogawa.tokyo.jp/documents/1845/edonet-riyoguide_ver31_2.pdf'
YOYOGI_SOURCE = 'https://www.kensetsu.metro.tokyo.lg.jp/documents/d/kensetsu/080601suporekuriyouannai'
MINAMIOSAWA_SOURCE = 'https://yoyaku.labola.jp/r/shop/3263/'
FIELDS = ['tokyo-venue-3613cfebc9e0', 'tokyo-venue-420d40a1f5dd',
          'tokyo-venue-e393a820dfa2', 'tokyo-venue-d743d59116d7']
GYMS = ['tokyo-gym-80d67f6abfca', 'tokyo-gym-10bc0dd8ba3f']
NISHITOKYO_GYMS = ['tokyo-gym-4d7e676a9c85', 'tokyo-gym-f69296c59450', 'tokyo-gym-348957c5e382']
OI = ['tokyo-venue-e5f26bb9d6f1', 'tokyo-venue-3de282b7fae3']
HIGASHI = 'tokyo-venue-3d53586773a6'
TSUKIJI = 'tokyo-gym-62eea3b0216c'
SHIBA = 'tokyo-venue-6ff79262c31f'
ARIAKE = 'tokyo-gym-b7451bddb3f3'
YASHIO = 'tokyo-venue-27db04888b6c'
YOYOGI = 'tokyo-venue-ca8b4111eb08'
SPORTSLAND = 'tokyo-sports-038'
MINAMIOSAWA = 'tokyo-sports-015'
CLOSURES = {
    'tokyo-gym-c9fd2d3160d0': {
        'url': 'https://www.city.arakawa.tokyo.jp/a017/sport/shisetsuriyou/s-houseriyou.html',
        'note': '荒川遊園スポーツハウスは大規模改修のため2025年3月31日～2027年3月下旬（予定）休館。公式ページの料金表は改修前の金額と明記されているため現行料金として採用せず、再開確認まで通常検索から除外します。',
    },
    'tokyo-sports-013': {
        'url': 'https://www.futsal-tokyo.co.jp/',
        'note': '南豊ヶ丘フィールドは施設老朽化により2026年8月6日で営業終了。運営者の2026年8月7日告知による（契約期間満了は2026年9月）。再開確認まで通常検索から除外します。',
    },
}
HELD = ['tokyo-venue-71237581c393', 'tokyo-venue-2e14b39dc02c']
REVIEWED_IDS = FIELDS + GYMS + NISHITOKYO_GYMS + OI + [HIGASHI, TSUKIJI, SHIBA, ARIAKE, YASHIO, YOYOGI, SPORTSLAND, MINAMIOSAWA] + list(CLOSURES) + HELD


def entry(ident, source, note, rows):
    return dict(old_entry(ident, source, note, rows), checked_at=CHECKED)


def reviewed_fees():
    result = []
    for ident, amount in zip(FIELDS, [200, 400, 200, 400]):
        note = '多目的運動広場の通常団体貸切。10人以上かつ構成員全員が立川市内在住・在勤・在学の登録団体のみ。市外団体の利用対象ではありません。当日現地払い。4～10月9～17時、11～3月10～16時。'
        if ident == FIELDS[2]:
            note += '砂川中央地区多目的運動広場のサッカーは練習のみで、試合の許可を示すものではありません。'
        result.append(entry(ident, TACHIKAWA, note, [('市内登録団体・通常利用', amount, '多目的運動広場1面・2時間')]))

    for ident, rooms in [
        (GYMS[0], [('第1体育室全面', (8000, 8900, 8900, 7600), (16000, 17800, 17800, 15200)),
                   ('第1体育室半面', (4000, 4500, 4500, 3800), (8000, 8900, 8900, 7600))]),
        (GYMS[1], [('第1体育室全面', (12000, 13400, 13400, 16000), (24000, 26800, 26800, 32000)),
                   ('第1体育室3分の1面', (4000, 4500, 4500, 5400), (8000, 9000, 9000, 10700)),
                   ('第2体育室全面', (4500, 5000, 5000, 5700), (9000, 10000, 10000, 11400))]),
    ]:
        shibasaki = ident == GYMS[0]
        rows = []
        for room, city, outside in rooms:
            for group, prices in [('市内団体', city), ('市外団体', outside)]:
                for index, (slot, price) in enumerate(zip(['9～12時30分', '12時30分～16時', '16～19時30分',
                                                          '19時30分～22時' if shibasaki else '19時30分～23時'], prices)):
                    duration = '2時間30分' if shibasaki and index == 3 else '3時間30分'
                    rows.append((room + ' / ' + group + ' / ' + slot, price, room + '・' + duration))
        note = '2026年8月版の立川市公式手引きの通常団体料金。全面・分割面、時間長、市内外の区分を分離し、公表端数を保持。個人入場料・備品は別。市内団体は10人以上かつ構成員全員が市内在住・在勤・在学。市外団体も体育館は利用対象ですが抽選は市内団体のみ。'
        if shibasaki:
            note += '夜間のみ2時間30分。第2体育室は卓球等用でバスケット・バレーの料金に混ぜていません。'
        else:
            note += '第1・第2体育室ともバスケット・バレーに対応。'
        result.append(entry(ident, TACHIKAWA, note, rows))

    for ident in NISHITOKYO_GYMS:
        kiratto = ident == NISHITOKYO_GYMS[1]
        source = ('https://www.shisetsu-tds.jp/tokyo-nishitokyo-kiratto/fee/' if kiratto else
                  'https://www.city.nishitokyo.lg.jp/sisetu/sports/' + ('sports.html' if ident == NISHITOKYO_GYMS[0] else 'sogo.html'))
        rows = [('第1体育室全面 / 市内', 5400 if kiratto else 7600, '第1体育室全面・3時間'),
                ('第1体育室全面 / 市外', 10800 if kiratto else 15200, '第1体育室全面・3時間')]
        if not kiratto:
            rows += [('第1体育室半面 / 市内', 3800, '第1体育室半面・3時間'),
                     ('第1体育室半面 / 市外', 7600, '第1体育室半面・3時間')]
        note = '第1体育室の通常団体貸切、9～12・12～15・15～18・18～21時の各3時間枠。市内外は所定の団体登録区分によります。第2体育室や個人入場料をバスケット・バレーの貸切料金に混ぜません。備品・減免・特別利用の割増は別。'
        if ident == NISHITOKYO_GYMS[0]:
            note += '長期休館は2027年7月～2029年3月予定で、現在の休館ではありません（市の2026年10月1日案内）。'
        result.append(entry(ident, source, note, rows))

    for ident, main in zip(OI, [True, False]):
        room = 'メインピッチ' if main else 'サブピッチ'
        rows = []
        for water, three, four in [('散水なし', 33000 if main else 24000, 44000 if main else 32000),
                                   ('散水あり', 42000 if main else 33000, 56000 if main else 44000)]:
            rows += [('スポーツ・入場料徴収なし / ' + water + ' / 午前・夜間', three, room + '・3時間'),
                     ('スポーツ・入場料徴収なし / ' + water + ' / 午後', four, room + '・4時間')]
        note = room + 'のスポーツ利用・入場料徴収なしの通常料。午前9～12時・夜間18～21時は3時間、午後13～17時は4時間。散水あり／なしを明記し、入場料徴収時・スポーツ以外の料金や早朝30分単位は含めません。照明は別。スパイク禁止、他競技のライン設置等は事前相談が必要で、サッカー大会の開催許可をこの料金だけで保証しません。Webは空き照会、正式申込は電話・窓口予約後の申込書提出によります。'
        result.append(entry(ident, OI_FEE, note, rows))

    result.append(entry(HIGASHI, 'https://shisetsu.mizuno.jp/m-7610-1/guide',
                        '2025年7月以降のアリーナ通常貸切。渋谷区在住・在勤・在学等の団体登録要件があります。個人入場300円・多目的ルームの料金とは別。9～11時から19～21時までの各2時間枠。',
                        [('アリーナ全面・通常団体', 8500, 'アリーナ全面・2時間'),
                         ('アリーナ半面・通常団体', 4200, 'アリーナ半面・2時間')]))
    rows = []
    for room, prices in [('全面', [6500, 12900, 12900, 29100]), ('半面', [3250, 6450, 6450, 14550])]:
        rows += [('体育場' + room + ' / ' + slot, price, '体育場' + room + '・' + duration)
                 for slot, duration, price in zip(['9～12時', '13～17時', '18～21時', '9～21時'],
                                                  ['3時間', '4時間', '3時間', '全日12時間'], prices)]
    result.append(entry(TSUKIJI, 'https://chuo-shakyo.jp/facility/tsukiji',
                        '体育場の通常貸切。午前・夜間3時間、午後4時間、全日12時間を分離。団体登録要件に従います。バスケット・バレー用具は各200円、バドミントンは1組100円を別途加算。単独予約できない夜間延長料や会議室の割引は採用していません。', rows))
    result.append(entry(SHIBA, SHIBA_SOURCE,
                        '夏季プール期間以外のフットサルコート1面（25m×15m）・2時間の通常貸切。港区の登録団体が対象で、10人以上・全員区内在住在勤在学等の登録要件に従います。照明200円/時間は別。プール入場料やフル規格サッカー場の料金ではありません。営利・名義貸し不可。',
                        [('フットサル・通常団体貸切（照明別）', 2600, 'フットサルコート1面・2時間')]))

    rows = []
    for room, prices in [('サブアリーナ全面', [30800, 39600, 34650, 44550, 77000, 99000]),
                          ('サブアリーナ半面', [18480, 23760, 20790, 26730])]:
        slots = [('平日9～13時・13～17時', '4時間'), ('土日祝9～13時・13～17時', '4時間'),
                 ('平日17～21時', '4時間'), ('土日祝17～21時', '4時間'),
                 ('平日9～21時', '全日12時間'), ('土日祝9～21時', '全日12時間')]
        rows += [(room + ' / 入場料徴収なし / ' + slot, price, room + '・' + duration)
                 for (slot, duration), price in zip(slots, prices)]
    result.append(entry(ARIAKE, 'https://reserve.ariake-arena.tokyo/有明アリーナ利用料金表.pdf',
                        'サブアリーナのスポーツ利用・入場料徴収なし。全面と半面、平日と土日祝、4時間枠と全日を区別。メインアリーナ料金、障害者減額、備品、入場料徴収時の割増は別。事前の団体登録・審査と使用料納付等が必要。2027年7月からの将来料金は現行料に混ぜません。', rows))
    result.append(entry(YASHIO, 'https://www.city.shinagawa.tokyo.jp/ct/pdf/20260105094637_1.pdf',
                        '八潮5-10-27の八潮区民集会所スポーツ室。区が公開する2026年版ファイルの会館案内で確認。別住所の「こみゅにてぃぷらざ八潮」とは別施設。一般団体は木・金・土の18時15分～21時30分のみ利用可、昼間は児童専用。会議室・レクホールの料金は混ぜません。団体登録等の利用要件に従います。',
                        [('スポーツ室・区民', 4700, 'スポーツ室・3時間15分'),
                         ('スポーツ室・区民以外', 5600, 'スポーツ室・3時間15分')]))
    result.append(entry(YOYOGI, YOYOGI_SOURCE,
                        '都立公園の2026年6月版公式案内。代々木公園サッカー場の全面貸切1時間当たりの基本使用料。通常は2時間枠で予約するため2時間利用は7,200円。小競技場の料金や公園の無料入園料と混同しません。事前登録と施設の利用条件に従い、営利大会をこの基本料だけで許可するものではありません。',
                        [('サッカー場全面・通常利用', 3600, 'サッカー場全面・1時間')]))
    result.append(entry(SPORTSLAND, EDOGAWA,
                        '2026年6月改訂の区公式ガイド第31版p27と施設公式ページが一致する現行料。フットサル1面・1時間670円（ゴールネット料込み）。旧630円は採用しません。照明320円/時間は別途必須時間帯あり。利用者登録が必要、区内外の受付開始条件は異なります。当日現地で利用券購入。',
                        [('フットサル・通常利用（照明別）', 670, 'フットサルコート1面・1時間')]))
    rows = []
    for room, member, visitor in [('Aコート', [6000, 10000], [8000, 12000]),
                                   ('B多目的コート', [7150, 10450], [8250, 12100])]:
        for group, prices in [('有料メンバー', member), ('ビジター', visitor)]:
            rows += [(room + ' / ' + group + ' / ' + slot, price, room + '1面・1時間')
                     for slot, price in zip(['平日日中～18時', '平日18時以降・土日祝'], prices)]
    result.append(entry(MINAMIOSAWA, MINAMIOSAWA_SOURCE,
                        '運営者が案内する公式LaBOLAプロフィールの税込通常レンタル料。有料メンバーは別途登録・更新費が必要（今回の金額に含めず、無料利用とは案内しません）。学割は除外。Aはフットサル、Bはゴールのない多目的コートで別単位。A料金表の平日9時表記に対し営業時間は平日10時からのため、日中は営業時間内に限ります。無許可の営利利用・コート代を超える徴収等は禁止。', rows))
    return result


def policy(ident, source, summary):
    return {'id': ident, 'status': 'conditional', 'summary': summary,
            'source_url': source, 'checked_at': CHECKED}


def reviewed_policies():
    result = [policy(ident, TACHIKAWA,
                     '運動広場は前日までに取消手続き。当日取消・無断不使用は利用制限の対象。支払済み料金は原則返金なし。天候で使えるかは施設判断で、自己判断の無断不使用は避けてください。この広場に適用される雨天還付の具体条件は未確認です。') for ident in FIELDS]
    result += [policy(ident, TACHIKAWA,
                      '体育館は利用7日前までWeb取消可能。支払済みの使用料は原則返金なし。通常は申込・当選確定後7日以内に納付、利用6日前以降の申込は窓口で即時支払い。直前取消・無断不使用は利用制限の対象で、屋外の雨天免除を適用しません。') for ident in GYMS]
    result += [policy(ident, NISHITOKYO,
                      '7日前（前週の同曜日）までの取消で全額還付。利用1週間以内に取った予約に限り4日前までの取消で半額還付という例外があります。一般の6～4日前取消が全て半額になるわけではありません。領収書等を持参して窓口で還付し、オンライン決済も現金で返金。屋内施設に雨天免除は案内しません。') for ident in NISHITOKYO_GYMS]
    result += [policy(ident, OI_GUIDE,
                      '正式予約後の自己都合取消はキャンセル料が発生すると現行の利用案内に明記。具体的な料率・期限や雨天免除は同案内だけでは未確認のため、無料・全額のいずれとも断定しません。正式予約は申込書の受付完了後です。') for ident in OI]
    result.append(policy(SHIBA, SHIBA_SOURCE,
                         '雨天等でも利用者の自己判断で中止するとペナルティ対象になる場合があります。施設が利用困難と判断した場合や災害・施設工事等の所定事由は対象外。通常の自己都合取消の期限・返金率はこの施設ページだけでは未確認です。'))
    result.append(policy(YOYOGI, YOYOGI_SOURCE,
                         'サッカー場は8日前までの取消ならペナルティ対象外、7日前以降の取消1点・無断不使用2点。雨天等の利用可否は施設へ確認し、自己判断の無断不使用は避けてください。ペナルティ免除と支払済み料金の還付は別で、還付手続きを省略できるとは案内しません。'))
    result.append(policy(SPORTSLAND, EDOGAWA,
                         '7日前までの取消は直前取消ポイント対象外。6日前～開始前の取消1点、開始後の取消・無断不使用3点。雨天の利用可否は施設判断で、利用可能なのに不使用なら無断取消扱い。事前購入済み利用券は有効期限内に次回利用でき、払戻しは区の担当へ手続きが必要です。'))
    result.append(policy(MINAMIOSAWA, MINAMIOSAWA_SOURCE + 'terms/',
                         'レンタル合計4時間未満は14日前まで無料、13～7日前50%、6日前～当日100%。4時間以上（2時間×2面を含む）は予約確定時から全額が発生し、取消・時間短縮・日程変更でも免除されません。雨天を理由とした取消にも料金が発生。取消連絡はメールで行います。大会参加・個人フットサルの別規定を混ぜていません。'))
    return result


def mark_closed():
    for name in ['tokyo_expansion.json', 'tokyo_sports.json']:
        path = CATALOGS / name
        original = path.read_text(encoding='utf-8')
        data = json.loads(original)
        rendered = original
        for row in data:
            if row['id'] not in CLOSURES:
                continue
            before = json.loads(json.dumps(row))
            closure = CLOSURES[row['id']]
            row.update(availability_status='SUSPENDED', availability_note=closure['note'], checked_at=CHECKED)
            source = {'title': '公式運営者・自治体の休館／営業終了案内', 'url': closure['url']}
            if source not in row['sources']:
                row['sources'].append(source)
            if before != row:
                old = '\n'.join('  ' + line for line in json.dumps(before, ensure_ascii=False, indent=2).splitlines())
                new = '\n'.join('  ' + line for line in json.dumps(row, ensure_ascii=False, indent=2).splitlines())
                if rendered.count(old) != 1:
                    raise ValueError('Unexpected base catalog formatting')
                rendered = rendered.replace(old, new, 1)
        assert json.loads(rendered) == data
        if rendered != original:
            path.write_text(rendered, encoding='utf-8')


def main():
    fees, policies = reviewed_fees(), reviewed_policies()
    validate(fees)
    catalog = {row['id']: row for row in get_catalog()['courts']}
    assert len(REVIEWED_IDS) == len(set(REVIEWED_IDS)) == 23
    assert len(fees) == 19 and len(policies) == 15
    assert all(ident in catalog for ident in REVIEWED_IDS)
    for review in fees:
        row = catalog[review['id']]
        if row.get('fee_checked_at') != CHECKED and has_price(row):
            raise ValueError('Refusing to replace already priced venue: ' + review['id'])
    for filename, additions in [('fee_plans.json', fees), ('cancellation_policies.json', policies)]:
        existing = {row['id']: row for row in json.loads((CATALOGS / filename).read_text(encoding='utf-8'))}
        for row in additions:
            if row['id'] in existing and existing[row['id']] != row:
                raise ValueError('Refusing to replace existing review: ' + row['id'])
    mark_closed()
    append_reviews(CATALOGS / 'fee_plans.json', fees)
    append_reviews(CATALOGS / 'cancellation_policies.json', policies)
    print(json.dumps({'reviewed_records': 23, 'new_fee_reviews': 19,
                      'new_cancellation_reviews': 15, 'closed_records': 2, 'held_records': 2}))


if __name__ == '__main__':
    main()
