"""Append November 21 official fees without merging different units or eligibility."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'outputs'))
from venues.fees import validate
from venues.sports_catalog import get_catalog, has_price
from record_venue_fee_review_20261018 import append_reviews, entry as previous_entry
from record_venue_fee_review_20261110 import SCHOOL_FEE, SCHOOL_UNIT

CHECKED = '2026-11-21'
BASE = '81f283c0bdc8c400ac8119c045122f73db6e0f7f'
CATALOGS = ROOT / 'outputs/venues/catalogs'
ARAKAWA = 'https://www.city.arakawa.tokyo.jp'
FURATTO = ARAKAWA + '/a020/sangyou/furattonippori/tamokutekispace.html'
SUNPEARL = ARAKAWA + '/a015/bunkageijutsu/geijutu/sunpearlriyou.html'
MOVE = ARAKAWA + '/a015/bunkageijutsu/geijutu/mubumachiyariyou.html'
ACROSS = ARAKAWA + '/a030/shisetsuannai/fukushikanren/shougaishamuke001.html'
SATSUKI = ARAKAWA + '/a001/seikatsu/jinkendanjo/satukiriyuouannnai.html'
FUCHU = 'https://www.city.fuchu.tokyo.jp/shisetu/komyunite/senta/about/yoyaku.html'
SAKURA = 'https://www.city.setagaya.lg.jp/02072/8540.html'
OTA = 'https://www.city.ota.tokyo.jp/shisetsu/hall/syuukaishitu_complexfacirity.files/annnai.pdf'
ADACHI = 'https://www.city.adachi.tokyo.jp/sg-shien/'
ADACHI_CANCEL = ADACHI + 'chiikibunka/shogaigakushu/riyohouhou02.html'
HOLDS = ['tokyo-venue-205d87234dd3', 'tokyo-venue-3ffcbdafb4b2']
RECHECKS = ['tokyo-venue-be48cc26a9d5']
SCHOOLS = {
    '2e1b7d61bb56': '砂川', '38ef11579546': '羽村', '7ba3aa112099': '保谷',
    '0934088ebb18': '田無工科', 'a854cce6f244': '青梅総合', '72ba3226b2f0': '三宅',
    '5e8dfe108e10': '八丈', '6a785b095fe2': '大島海洋国際', '7fef1e6f99f9': '大島',
    '2be5bc5fff6a': '小笠原', 'fab7b9d3e061': '新島', 'd2a73704f207': '神津',
}
HARD_ONLY = {'38ef11579546', 'fab7b9d3e061', 'd2a73704f207'}
ADACHI_ROOMS = {
    'tokyo-venue-ed023319a334': ('hotsuka.html', [
        ('第1学習室', (1600, 2000, 2500)), ('第2学習室', (1100, 1400, 1700)),
        ('第3学習室', (1100, 1400, 1700)), ('教養室', (1100, 1400, 1700))], (2100, 2700, 3100)),
    'tokyo-venue-6178e8b63baa': ('sinden.html', [
        ('第1学習室', (2100, 2700, 3300)), ('第2学習室', (2100, 2700, 3300)),
        ('第3学習室', (1600, 2000, 2500)), ('教養室', (1600, 2000, 2500)),
        ('料理室', (2500, 3000, 3700))], (2400, 3000, 3600)),
    'tokyo-venue-19395ebfe432': ('takenotsuka.html', [
        ('第1学習室', (1100, 1400, 1700)), ('第2学習室', (1100, 1400, 1700)),
        ('教養室', (1100, 1400, 1700))], (2400, 3000, 3600)),
}


def entry(ident, source, note, rows):
    return dict(previous_entry(ident, source, note, rows), checked_at=CHECKED)


def arakawa_slots(room, amounts, condition='通常'):
    return [(f'{room}・{condition}・{slot}', amount, f'{room}・{unit}（{condition}）')
            for (slot, unit), amount in zip([
                ('午前9～12時30分', '3時間30分'), ('午後13時30分～17時', '3時間30分'),
                ('夜間18～22時', '4時間'), ('全日9～22時', '全日13時間')], amounts)]


def reviewed_fees():
    rows = []
    fuchu = []
    for room, amounts in [('講堂1室', (1400, 2400, 3000, 6100)),
                          ('会議室1室', (600, 1200, 1400, 2900)),
                          ('小会議室', (300, 400, 500, 1100)),
                          ('和室23畳', (600, 1000, 1200, 2500)),
                          ('料理講習室', (400, 600, 800, 1600))]:
        for area, multiplier in [('市内一般団体', 1), ('市外一般団体', 2)]:
            fuchu.extend((f'{room}・{area}・{slot}', amount * multiplier, f'{room}・{unit}（{area}）')
                for (slot, unit), amount in zip([
                    ('午前9～12時', '3時間'), ('午後13～16時30分', '3時間30分'),
                    ('夜間17時30分～21時', '3時間30分'), ('全日9～21時', '全日12時間')], amounts))
    rows.append(entry('tokyo-sports-033', FUCHU,
        '中央文化センターの公民館部分（講堂・会議室・小会議室・23畳和室・料理講習室）の一般団体料金。'
        '10人以上は7割以上、10人未満は5割以上が市内在住・在勤・在学の団体が市内区分、市外は2倍。'
        '市登録団体の料金や高齢者福祉館・児童館とは別。ひばりホール・付属器具・夜間延長は対象外。'
        '準備・片付けを含み、窓口予約は予約システム登録不要、Web予約は登録と利用実績等の条件あり。'
        '営業・不特定多数対象の事業等は不可。自己都合取消の返還割合・期限は今回の案内では未確認。', fuchu))

    sakura = []
    for room, amount in [('第1会議室', 390), ('第2会議室', 390), ('第3会議室', 390),
                         ('第1第2会議室併合', 780), ('音楽室', 1050), ('料理講習室', 1050)]:
        sakura.extend([(f'{room}・午前9～12時', amount, f'{room}・3時間（通常）'),
            (f'{room}・午後A/午後B/夕方/夜間', amount * 2 // 3, f'{room}・2時間（通常）')])
    sakura.append(('大広間・夕方/夜間', 260, '大広間・2時間（団体貸切）'))
    sakura.extend([(f'集会室兼体育室・{slot}', amount, f'集会室兼体育室・{unit}（通常）')
        for slot, amount, unit in [('午前9～12時', 4470, '3時間'),
            ('午後13～15時/15時30分～17時30分', 2980, '2時間'), ('夜間18～22時', 5960, '4時間')]])
    rows.append(entry('tokyo-venue-370b51dc9413', SAKURA,
        '令和7年10月1日改定の本館料金。別住所の別館桜丘ホール・別館会議室は含めません。'
        'けやきネット登録が必要。会議室等の午後Aは12時30分～14時30分、午後Bは15～17時、'
        '夕方17時30分～19時30分、夜間20～22時。体育室の時間区分とは異なります。'
        '大広間の日中個人利用を無料の団体貸切とは扱わず、夕方・夜間だけ掲載。'
        '準備・片付けや利用可能用途は施設規則に従い、取消・還付の期限は今回未確認。', sakura))

    ota = []
    for room, amounts in [('第一集会室', (1800, 1500)), ('第二集会室', (2400, 2000)),
                          ('第一多目的室', (1800, 1500)), ('第二多目的室', (2400, 2000))]:
        ota.extend([(f'{room}・午前/午後B/夜間', amounts[0], f'{room}・3時間（通常）'),
                    (f'{room}・午後A', amounts[1], f'{room}・2時間30分（通常）')])
    rows.append(entry('tokyo-venue-2c73f8af103d', OTA,
        '2026年11月1日開設の現行公式案内と所在地を照合。午前9～12時、午後A12時30分～15時、'
        '午後B15時30分～18時30分、夜間19～22時。2区分以上の連続利用時だけ中間時間の使用料なし。'
        '公益目的の登録少年育成・少年団体/障害者団体は5割、登録社会教育一般団体は2割5分減免。'
        'ここでは通常料金だけ掲載し、備品は別。うぐいすネットの事前登録が必要、営利利用不可。'
        '3階集会室は振動が下階に響くダンス等不可、4階多目的室は音楽・ダンス等に対応。'
        '部屋併合には両室の予約が必要。一般の取消・返還条件は今回のPDFでは未確認。', ota))

    rows.append(entry('tokyo-venue-e08430091e38', FURATTO,
        '3階多目的スペースA/B/Cの通常貸室料金。準備・片付けを含む。'
        '公共的団体・荒川区産業団体は減免対象ですが、割合は推測せず通常利用へ適用しません。'
        '附帯設備・控室は別料金。区内企業等の展示即売や区外企業等の展示・展示即売には別途加算あり。'
        'Web申請はA又はCの1室を会議・集会目的に使う場合のみ、登録が必要。'
        '会議・研修が主用途で、楽器演奏・運動等の大きな音や振動の出る活動は不可。'
        '利用権の譲渡・転貸は禁止。学校や競技場の貸切料金とは別です。',
        [item for room, amounts in [('多目的スペースA', (3400, 3400, 3900, 10700)),
                                   ('多目的スペースB', (2500, 2500, 2900, 7900)),
                                   ('多目的スペースC', (2500, 2500, 2900, 7900))]
         for item in arakawa_slots(room, amounts)]))
    sunpearl = [item for room, amounts, condition in [
        ('大ホール', (45500, 84500, 110500, 214500), '月～金'),
        ('大ホール', (52000, 104000, 130000, 260000), '土日祝'),
        ('小ホール', (15600, 18200, 18200, 52000), '月～金'),
        ('小ホール', (19500, 22800, 22800, 65100), '土日祝'),
        ('第1集会室', (2000, 2900, 2900, 7800), '通常'),
        ('第2集会室', (2000, 2900, 2900, 7800), '通常'),
        ('第3集会室', (2000, 2900, 2900, 7800), '通常'),
        ('第4集会室', (2400, 3700, 3700, 9800), '通常'),
        ('第5集会室', (3700, 5300, 5300, 14300), '通常'),
        ('第6集会室', (3700, 5300, 5300, 14300), '通常'),
        ('第7集会室', (7500, 10600, 10600, 28700), '通常')]
        for item in arakawa_slots(room, amounts, condition)]
    rows.append(entry('tokyo-venue-68173b2f2e9f', SUNPEARL,
        '大・小ホールと第1～7集会室の通常料金。曜日・部屋・時間区分を分離。附帯設備は別。'
        '5,001円以上の入場料等を徴収する場合は30％加算、利用目的で料金が変わる場合あり。'
        '無料ギャラリーを有料ホール料金に混在させません。Web予約は第1～3集会室のみ、事前登録が必要。'
        '11月17日の点検休館は過去の日付で、恒久休止と扱いません。', sunpearl))
    rows.append(entry('tokyo-venue-375db5fa8c9a', MOVE,
        'ムーブホール・会議室・スタジオの通常料金。附帯設備・有料楽屋・技術スタッフ等は別。'
        '5,001円以上の入場料等は50％加算、商品展示・即売は区内外と内容により別途加算。'
        '本公演のための準備練習の半額区分を通常利用へ適用しません。Web予約はスタジオのみ、登録が必要。'
        '料金は午前/午後3時間30分・夜間4時間・全日13時間を分離。',
        [item for room, amounts, condition in [
            ('ムーブホール', (12000, 24000, 31000, 61000), '平日'),
            ('ムーブホール', (15000, 30000, 38000, 75000), '土日祝'),
            ('会議室', (3000, 3000, 3400, 9400), '通常'),
            ('スタジオ', (2200, 2200, 2500, 6900), '通常')]
         for item in arakawa_slots(room, amounts, condition)]))
    rows.append(entry('tokyo-venue-ca8003362ef9', ACROSS,
        'アクロスあらかわの通常施設使用料。準備・片付けを含み、午前/午後は各3時間30分、夜間4時間、全日13時間。'
        '障害者福祉推進団体は使用料免除ですが、通常利用や誰でも無料には適用しません。'
        'Web予約は事前登録が必要。多目的ホール全面・分割と会議室は別単位。'
        '支払期限超過の自動取消を、納付済み料金の無料取消・返還とは扱いません。一般取消の期限・割合は未確認。',
        [item for room, amounts in [
            ('多目的ホール全面', (5200, 5200, 6100, 16500)),
            ('多目的ホール1', (3400, 3400, 3900, 10700)),
            ('多目的ホール2', (1800, 1800, 2200, 5800)),
            ('第1会議室', (1300, 1300, 1500, 4100)),
            ('第2会議室', (1300, 1300, 1500, 4100)),
            ('第3会議室', (1000, 1000, 1100, 3100))]
         for item in arakawa_slots(room, amounts)]))
    rows.append(entry('tokyo-venue-6bae42680d24', SATSUKI,
        '荒川さつき会館の登録団体貸室。各区分3時間（9～12時/12時20分～15時20分/'
        '15時40分～18時40分/19～22時）で準備・片付けを含む。5名以上で使用。'
        '区民団体は構成員の過半数が区内在住・在勤・在学、一般団体でも代表者は区内要件が必要。'
        '登録人数超過・営利・不特定多数の催し等不可。体育室はバスケ・サッカー・バレー・ピックルボール等の'
        '固いボールは使用不可（ビーチボールバレー・卓球・バドミントン等の使用例）。'
        '個人向けロビー等の無料利用とは別です。',
        [(f'{room}・{category}・各時間帯', amount, f'{room}・3時間（{category}）')
         for room, amounts in [('和室', (900, 1800)), ('体育室', (900, 1800)),
                              ('洋室1', (400, 900)), ('洋室2', (400, 900)), ('洋室3', (300, 600))]
         for category, amount in zip(('区民団体', '一般団体'), amounts)]))

    for ident, (path, rooms, recreation) in ADACHI_ROOMS.items():
        options = [(f'{room}・{slot}', amount, f'{room}・{unit}（通常）')
            for room, amounts in rooms
            for (slot, unit), amount in zip([
                ('午前9～12時30分', '3時間30分'), ('午後13～17時', '4時間'),
                ('夜間17時30分～21時30分', '4時間')], amounts)]
        options.extend((f'レクリエーションホール・{slot}', amount, f'レクリエーションホール・{unit}（通常）')
            for (slot, unit), amount in zip([
                ('午前9～12時', '3時間'), ('午後1/午後2', '2時間30分'),
                ('夜間18時30分～21時30分', '3時間')], recreation))
        if path == 'takenotsuka.html':
            options.extend((f'ホール・{day}・{slot}', amount, f'ホール・{unit}（{day}）')
                for day, amounts in [('平日', (5100, 10100, 15200)), ('土日休日', (6900, 13000, 19700))]
                for (slot, unit), amount in zip([
                    ('午前9～12時30分', '3時間30分'), ('午後13～17時', '4時間'),
                    ('夜間17時30分～21時30分', '4時間')], amounts))
        rows.append(entry(ident, ADACHI + path,
            '部屋別・時間区分別の通常貸室料金。学習室等の午前は3時間30分、午後/夜間は4時間。'
            'レクリエーションホールは午前/夜間3時間、午後1（12時30分～15時）/'
            '午後2（15時30分～18時）は2時間30分で、別単位。準備・片付け・原状復帰を含む。'
            '有料備品は別。Web予約は事前登録が必要、支払い前は仮予約。'
            '営利・宗教活動、不特定多数の使用は不可。会議室やレクリエーション室を一般の競技コートと扱いません。'
            '竹の塚のホールは一般貸室と申込・取消窓口が異なります。', options))

    for suffix in SCHOOLS:
        sport = '硬式のみ' if suffix in HARD_ONLY else '硬式・軟式'
        rows.append(entry('school-' + suffix, SCHOOL_FEE,
            f'令和8年度の開放予定一覧で学校・庭球場・種目を個別照合（{sport}）。無料は昼間の施設使用料のみ。'
            '主に都内在住・在勤・在学の10人以上の非営利・定期活動団体、20歳以上の責任者、'
            '学校ごとの毎年度登録と傷害保険加入が必要。名簿掲載者の練習・練習試合が原則で、'
            '不特定多数の活動は不可。照明等の光熱費・保険料は含みません。'
            '制度説明資料の手続き例は令和6年度であり、現行一覧・登録要件を併せて確認。'
            '時間単価・開放日・各校の取消期限は推測せず、学校教育により中止・変更される場合があります。',
            [('昼間・施設使用料', 0, SCHOOL_UNIT)]))
    return rows


def reviewed_policies():
    rows = [dict(id='tokyo-venue-e08430091e38', checked_at=CHECKED, status='conditional', source_url=FURATTO,
        summary='納付後の自己都合取消は原則不返還。使用10日前までの取消は75％、5日前までは50％返金'
        '（100円未満切捨て）、承認書を持参して窓口手続き。使用者の責によらない使用不可は全額。'
        '23区東部の暴風特別警報/警報、積雪で使用困難、震度5強以上の地震で使用困難等を規定。'
        '通常の雨だけで無料取消とは扱いません。利用権の譲渡・転貸は禁止。'),
        dict(id='tokyo-venue-68173b2f2e9f', checked_at=CHECKED, status='conditional',
        source_url='https://www.sunpearl-arakawa.com/guide/subscribe/',
        summary='納付済み料金は原則不返還。大・小ホールは1か月前まで75％、15日前まで50％返金。'
        '集会室・ホワイエは10日前まで75％、5日前まで50％返金。承認書・領収書等を持参して手続き。'
        '期限が休館日なら翌営業日。大ホール半額納入の場合は返金額から未納額を差し引く。'
        '未使用附帯設備は全額返金。屋内の雨天無料取消は確認できていません。'),
        dict(id='tokyo-venue-375db5fa8c9a', checked_at=CHECKED, status='conditional',
        source_url='https://www.sunny-move.jp/move/use/index.html',
        summary='納付済み料金は原則不返還。ムーブホールは1か月前まで75％、15日前まで50％返金。'
        '会議室・スタジオは10日前まで75％、5日前まで50％返金。承認書を持参して来館手続きが必要で、'
        '変更・取消はメール・郵送不可。雨天を理由とした屋内無料取消は未確認。'),
        dict(id='tokyo-venue-6bae42680d24', checked_at=CHECKED, status='conditional', source_url=SATSUKI,
        summary='納付済み使用料は原則不還付。特別な理由が認められる場合、使用5日前までに還付申請書と'
        '承認書等を持参して窓口手続きすることで還付可能。割合は当該ページに明記がなく、無料取消と推測しません。'
        '窓口の受付時間・休業日に注意。屋内の雨天免除は未確認。')]
    for ident in ADACHI_ROOMS:
        rows.append(dict(id=ident, checked_at=CHECKED, status='conditional', source_url=ADACHI_CANCEL,
            summary='使用2日前までの取消手続きは50％返金。使用承認（納付）翌日から3日以内かつ'
            '使用2日前までの取消、又は使用者責任でない使用不可は全額返金。前日・当日の取消は返金不可。'
            '承認書原本又は画像で窓口手続きが必要。竹の塚ホールは当該館のみ受付。'
            '年末年始に期限が重なる場合は直前の開館日が期限。通常の雨天を無条件の免除とは扱いません。'))
    return rows


REVIEWED_IDS = HOLDS + RECHECKS + [r['id'] for r in reviewed_fees()]


def main():
    fees, policies = reviewed_fees(), reviewed_policies()
    validate(fees)
    assert len(REVIEWED_IDS) == len(set(REVIEWED_IDS)) == 26
    assert len(fees) == 23 and len(policies) == 7
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
