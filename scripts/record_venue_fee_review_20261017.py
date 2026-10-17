"""Append source-matched tariffs; never replace a previous research batch."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'outputs'))
from venues.fees import validate
from venues.sports_catalog import get_catalog

CHECKED = '2026-10-17'
CATALOGS = ROOT / 'outputs/venues/catalogs'
FUCHU_GYMS = {
    'tokyo-gym-ee0b47a21429': 'yotuya',
    'tokyo-gym-2a259e8bdd71': 'oshidate',
    'tokyo-gym-426f334c2d57': 'sakaecho',
    'tokyo-gym-464c406a297c': 'shiraitodai',
}
KOMAE_GYM = 'tokyo-gym-6ad91a421d85'
KOMAE_WEST_GYM = 'tokyo-gym-7420040d51ac'
KOMAE_GROUND = 'tokyo-venue-87508e9a2968'
KOMAE_WEST_GROUND = 'tokyo-venue-e998aceac026'
TAITO_SOURCE = 'https://www.city.taito.lg.jp/kusei/online/yoyaku/riyosyaguide.files/3.pdf'


def entry(ident, source, conditions, rows):
    return {'id': ident, 'checked_at': CHECKED, 'fee_note': conditions,
            'fee_options': [{'label': label, 'amount': amount, 'unit': unit,
                             'conditions': conditions, 'source_url': source}
                            for label, amount, unit in rows]}


def reviewed_fees():
    result = []
    for ident, slug in FUCHU_GYMS.items():
        result.append(entry(ident, 'https://www.city.fuchu.tokyo.jp/shisetu/supotu/taikukan/' + slug + '.html',
                            '体育室全面の団体貸切。府中市内団体のみ。10名以上、過半数が市民で残りも市内在勤在学などの登録要件があり、営利利用不可。個人公開・会議室・付帯設備は含みません。', [
                                ('午前9:00～12:00', 2500, '体育室全面・3時間'),
                                ('夜間18:00～21:00', 3500, '体育室全面・3時間'),
                                ('午後1 12:45～15:00', 2000, '体育室全面・2時間15分'),
                                ('午後2 15:15～17:30', 2000, '体育室全面・2時間15分'),
                                ('全日9:00～21:00', 9000, '体育室全面・全日12時間'),
                            ]))
    result.append(entry('tokyo-venue-72dbbba725a1', 'https://www.city.fuchu.tokyo.jp/shisetu/supotu/sakka/shimin.html',
                        '郷土の森サッカー場の天然芝・人工芝1面の通常使用料。施設利用団体登録と公共施設予約システム登録が必要。天然芝は養生休止・雨天中止あり。付帯設備や減免は含みません。', [
                            ('市内団体', 800, 'サッカー場1面・1時間'),
                            ('市外団体', 1600, 'サッカー場1面・1時間'),
                        ]))

    conditions = '5名以上の非営利登録団体向け通常料金。市内は半数以上が狛江市在住在勤在学。市外は市内通常料金の2倍。高校生以下団体の割引・備品・個人利用を除きます。準備清掃を利用時間に含みます。'
    rows = [(room + ' / ' + group, amount * multiplier, room + '・2時間15分')
            for room, amount in [('第1体育室A面', 2600), ('第1体育室B面', 2600), ('第2体育室', 1600), ('第3体育室', 1000)]
            for group, multiplier in [('市内一般団体', 1), ('市外一般団体', 2)]]
    result.append(entry(KOMAE_GYM, 'https://www.komae-sponavi.net/gym/group/', conditions, rows))
    result.append(entry(KOMAE_WEST_GYM, 'https://www.komae-sponavi.net/nishiizumi/group/', conditions, [
        ('市内一般団体', 1400, '体育館全面・2時間15分'),
        ('市外一般団体', 2800, '体育館全面・2時間15分'),
    ]))
    for ident, url, short_slot in [
        (KOMAE_GROUND, 'https://www.komae-sponavi.net/other/ground/', '2・3・9・10月16:00～17:00'),
        (KOMAE_WEST_GROUND, 'https://www.komae-sponavi.net/nishiizumi/group/', '4～8月17:00～18:00、11～1月15:00～16:00'),
    ]:
        rows = [(group + ' / 通常枠', amount, 'グランド全面・2時間')
                for group, amount in [('市内一般団体', 2400), ('市外一般団体', 4800)]]
        rows += [(group + ' / ' + short_slot, amount, 'グランド全面・1時間（季節末尾枠）')
                 for group, amount in [('市内一般団体', 1200), ('市外一般団体', 2400)]]
        result.append(entry(ident, url, conditions + '日没により利用終了時刻が変わり、季節末尾の1時間枠は通常2時間枠と別に表示。', rows))

    result.append(entry('tokyo-gym-4f1d102ace47', 'https://www.city.fussa.tokyo.jp/map/sports/1001674.html',
                        '中央体育館の主競技場貸切1時間。市内は在住在勤在学者、市外はそれ以外。入場料等を徴収する利用は別料金（主競技場9,600円/時）で通常表示幅には含めません。個人利用・会議室・武道場・付帯設備は別。', [
                            ('市内在住在勤在学者', 1600, '主競技場全面・1時間'),
                            ('市外利用者', 4800, '主競技場全面・1時間'),
                        ]))

    rows = [(period + ' / ' + day, amount, '主競技場全面・' + duration)
            for period, duration, amounts in [
                ('昼間1 8:00～11:00', '3時間', (14100, 16900)),
                ('昼間2 11:30～14:30', '3時間', (18700, 22400)),
                ('昼間3 15:00～18:00', '3時間', (23400, 28100)),
                ('夜間18:30～21:30', '3時間', (28100, 33700)),
                ('全日8:00～21:30', '全日13時間30分', (75900, 91000)),
            ] for day, amount in zip(('平日', '土日祝'), amounts)]
    result.append(entry('tokyo-venue-c3c8b7f2193f', 'https://www.chuo-sports.jp/guide/',
                        '主競技場全面の通常団体貸切料金。団体登録・利用目的等の条件を確認。半面は公式案内が「半額程度」のため推計せず、個別料金表を確認してください。他の室場・備品・減免は表示幅に含みません。', rows))

    for ident, slug, full, half in [
        ('tokyo-gym-592c31402120', 'sougou', ((14800, 16300), (16300, 18000), (16300, 18000), (25000, 27500)),
         ((7400, 8200), (8200, 9000), (8200, 9000), (12500, 13800))),
        ('tokyo-gym-6b1a56ec4185', 'togoshi', ((7800, 8600), (8600, 9500), (8600, 9500), (13200, 14500)),
         ((3900, 4300), (4300, 4800), (4300, 4800), (6600, 7300))),
    ]:
        rows = [(period + ' / 区内一般団体 / ' + day + ' / ' + area, amount, '競技場' + area + '・' + duration)
                for area, slots in [('全面', full), ('半面', half)]
                for (period, duration), amounts in zip([
                    ('午前9:00～11:30', '2時間30分'), ('午後1 12:00～14:30', '2時間30分'),
                    ('午後2 15:00～17:30', '2時間30分'), ('夜間18:00～21:30', '3時間30分')], slots)
                for day, amount in zip(('平日', '土日祝'), amounts)]
        result.append(entry(ident, 'https://www.ssa.or.jp/' + slug + '/guide/dantai/index.html',
                            '品川区内一般登録団体の競技場料金のみ。区外団体は別料金のためこの表示幅には未収録。社会教育団体25%減額・連続利用割引・個人利用は対象外。バスケ・バレーボールのゴール/ネット等は1組1枠580円が別途必要。営利利用は別申請・区の審査承認が必要。', rows))

    rows = [(period + ' / ' + group + ' / ' + day + ' / ' + area, amount, 'アリーナ' + area + '・' + duration)
            for group, day, area, amounts in [
                ('区民', '平日', '全面', (5500, 6000, 6000, 9300)),
                ('区民', '土日祝', '全面', (6100, 6600, 6600, 10200)),
                ('区民以外', '平日', '全面', (8300, 9000, 9000, 14000)),
                ('区民以外', '土日祝', '全面', (9200, 9900, 9900, 15300)),
                ('区民', '平日', '半面', (2800, 3000, 3000, 4700)),
                ('区民', '土日祝', '半面', (3100, 3300, 3300, 5100)),
                ('区民以外', '平日', '半面', (4200, 4500, 4500, 7000)),
                ('区民以外', '土日祝', '半面', (4600, 5000, 5000, 7700)),
            ] for (period, duration), amount in zip([
                ('午前9:00～11:30', '2時間30分'), ('午後1 12:00～14:30', '2時間30分'),
                ('午後2 15:00～17:30', '2時間30分'), ('夜間18:00～21:30', '3時間30分')], amounts)]
    result.append(entry('tokyo-gym-4f634496a3db', 'https://www.shinagawa-culture.or.jp/square/facility/sports/price-list/facility.html',
                        'アリーナの1枠料金。体育館利用団体等の登録が必要。区民/区民以外、全面/半面、時間区分を区別。連続利用割引は別表で、この表示幅には含みません。ゴール・ネット等の付帯設備は別料金。', rows))

    for ident, room, slots in [
        ('tokyo-venue-353fa74611f1', '体育館アリーナ全面', [
            ('午前9:00～12:00', '3時間', (2700, 3240)),
            ('夜間1 18:00～21:00', '3時間', (5500, 6600)),
            ('午後13:00～17:00', '4時間', (3600, 4320)),
            ('夜間2 19:00～21:00', '2時間', (3700, 4440)),
            ('全日9:00～21:00', '全日12時間', (10200, 12240)),
        ]),
        ('tokyo-gym-48e959a72b2e', '第1競技場全面', [
            ('午前9:00～12:00', '3時間', (17000, 20400)),
            ('夜間18:00～21:00', '3時間', (35000, 42000)),
            ('午後13:00～17:00', '4時間', (23000, 27600)),
            ('全日9:00～21:00', '全日12時間', (65000, 78000)),
        ]),
    ]:
        rows = [(period + ' / ' + group + ' / ' + day, amount * numerator // 2, room + '・' + duration)
                for period, duration, amounts in slots
                for day, amount in zip(('平日', '土日祝'), amounts)
                for group, numerator in [('区内利用者', 2), ('区外利用者（5割加算）', 3)]]
        result.append(entry(ident, TAITO_SOURCE,
                            '台東区公共施設予約システムのスポーツ施設登録が必要。通常貸切の区内/区外、平日/土日祝を収録。区外は規定使用料に5割加算。入場料徴収時の5割加算・付帯設備・減免は含みません。小体育室等は表示幅の対象外。', rows))
    return result


def reviewed_policies():
    groups = [
        (list(FUCHU_GYMS) + ['tokyo-venue-72dbbba725a1'],
         'https://www.city.fuchu.tokyo.jp/shisetu/supotu/yoyaku/torikesi.html',
         '本人または団体代表者が窓口で取消申請（委任状で代理可）。利用1か月前まで100%、10日前まで50%、9日前以降0%還付。予約誤りも同条件。雨天時のサッカー場は別の振替・還付手順を確認。'),
        ([KOMAE_GYM, KOMAE_WEST_GYM], 'https://www.komae-sponavi.net/gym/group/',
         '自己都合取消は3日前までにシステムで手続き。それ以降は体育館へ連絡。自己都合は還付・振替不可。施設都合・天災等は還付対象。屋外グランドの雨天特例は屋内体育館へ適用しません。'),
        ([KOMAE_GROUND, KOMAE_WEST_GROUND], 'https://www.komae-sponavi.net/nishiizumi/group/',
         '自己都合取消は3日前までにシステムで手続き、それ以降は施設へ連絡。自己都合は還付・振替不可。天候・グランド不良や暑さ指数28以上で不使用は還付対象。天候等で利用不能なら全額還付、使用許可書と本人確認書類を体育館窓口へ。'),
        (['tokyo-gym-592c31402120', 'tokyo-gym-6b1a56ec4185'],
         'https://www.ssa.or.jp/vc-files/sougou/r080105riyougaidobukku.pdf',
         '当選確定・空き予約の取消料は利用1か月前まで50%（設備料除く）、1か月以内100%（設備料含む）。利用当日までに窓口で支払い。支払い済みとの差額は窓口で現金返還（オンライン決済も同様）。'),
        (['tokyo-gym-4f634496a3db'], 'https://www.shinagawa-culture.or.jp/square/facility/sports/usage.html',
         '当選確定・空き予約の取消料は利用1か月前まで50%（設備料除く）、1か月以内100%（設備料含む）。利用日時前までに窓口で支払い。支払い済みとの差額は窓口で現金返還（キャッシュレス決済も同様）。'),
        (['tokyo-gym-48e959a72b2e'], 'https://www.city.taito.lg.jp/kusei/online/yoyaku/riyosyaguide.files/4.pdf',
         '体育館は2か月前まで全額、15日前まで80%、7日前まで50%、6日前以降は還付なし。部屋・備品ともオンライン決済のみならシステム取消/還付申請（支払い後185日超は窓口）。混在決済・屋外の雨天取消は窓口手順を確認。'),
        (['tokyo-venue-353fa74611f1'], 'https://www.city.taito.lg.jp/kusei/online/yoyaku/riyosyaguide.files/4.pdf',
         'スポーツ施設は15日前まで80%、7日前まで50%、6日前以降は還付なし。会議室とは別区分。オンライン決済のみの場合の取消/還付申請はシステム、支払い後185日超等は窓口。グラウンド雨天不可は窓口へ（体育館に雨天免除は適用しません）。'),
    ]
    sources = {KOMAE_WEST_GYM: 'https://www.komae-sponavi.net/nishiizumi/group/',
               KOMAE_GROUND: 'https://www.komae-sponavi.net/other/ground/'}
    return [{'id': ident, 'status': 'conditional', 'summary': summary,
             'source_url': sources.get(ident, source), 'checked_at': CHECKED}
            for ids, source, summary in groups for ident in ids]


def main():
    fees = reviewed_fees()
    validate(fees)
    catalog = {row['id']: row for row in get_catalog()['courts']}
    assert len(fees) == 16 and all(row['id'] in catalog for row in fees)
    for filename, additions in [('fee_plans.json', fees), ('cancellation_policies.json', reviewed_policies())]:
        path = CATALOGS / filename
        original = path.read_text(encoding='utf-8')
        existing = json.loads(original)
        indexed = {row['id']: row for row in existing}
        for row in additions:
            if row['id'] in indexed and indexed[row['id']] != row:
                raise ValueError('Refusing to overwrite a different review: ' + row['id'])
        pending = [row for row in additions if row['id'] not in indexed]
        if not pending:
            continue
        existing.extend(pending)
        if filename == 'fee_plans.json':
            validate(existing)
        serialized = (json.dumps(pending, ensure_ascii=False, indent=2)[2:-2]
                      if filename == 'fee_plans.json' else
                      ',\n'.join('  ' + json.dumps(row, ensure_ascii=False, separators=(',', ':')) for row in pending))
        rendered = original.rstrip()[:-1].rstrip() + (',\n' if indexed else '\n') + serialized + '\n]'
        assert json.loads(rendered) == existing
        temporary = path.with_suffix('.json.tmp')
        temporary.write_text(rendered + '\n', encoding='utf-8')
        temporary.replace(path)
    print(json.dumps({'fee_reviews': len(fees), 'cancellation_reviews': len(reviewed_policies())}))


if __name__ == '__main__':
    main()
