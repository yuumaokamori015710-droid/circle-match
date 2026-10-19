"""Append verified tariffs to existing IDs; retain every earlier review."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'outputs'))
from venues.fees import validate
from venues.sports_catalog import get_catalog, has_price
from record_venue_fee_review_20261018 import append_reviews

CHECKED = '2026-10-19'
CATALOGS = ROOT / 'outputs/venues/catalogs'
TAMA_GUIDE = 'https://tama-sports.com/wp/images/スポーツ施設の利用手引き20260525.pdf'
KODAIRA = 'https://www.city.kodaira.tokyo.jp/kurashi/001/001348.html'
SUMIDA_FEE = 'https://sumidacity-ground.com/fee'
MYOSHOJI = 'https://www.tetsugakudo.jp/wp-content/uploads/2024/07/2024_07232.pdf'
SAGINOMIYA = 'https://www.nakano-sports-comm.net/?mode=n&s=1&type=021'
HEIWA = 'https://information.konamisportsclub.jp/file.jsp?id=34282'
TAMA_IDS = ['tokyo-venue-121d6c8174f3', 'tokyo-venue-2eee55f51c74',
            'tokyo-venue-0e8ff3149e98', 'tokyo-venue-5b984fb3a2d9',
            'tokyo-venue-e394b1e32142', 'tokyo-venue-58dddea55c17']
KODAIRA_IDS = ['tokyo-venue-ddccb6a7186f', 'tokyo-venue-47487bc65669',
               'tokyo-venue-4b48ca660485', 'tokyo-venue-d6ae544d3049']
SUMIDA_FIELDS = ['tokyo-venue-147fe0995885', 'tokyo-venue-c4a96df3f8b8']
SUMIDA_GYM = 'tokyo-gym-de4248a7e59c'
UMEWAKA = 'tokyo-gym-e29afd238620'
NAKANO_IDS = ['tokyo-venue-7f5f8dbd18bb', 'tokyo-venue-8d267086196e', 'tokyo-gym-07d760f3b816']
SHINAGAWA_IDS = ['tokyo-venue-bde3fe735327', 'tokyo-gym-4cc7151e3584', 'tokyo-gym-62c8903535b7']
CLOSED = 'tokyo-venue-d7b168f67c73'
REVIEWED_IDS = TAMA_IDS + KODAIRA_IDS + SUMIDA_FIELDS + [SUMIDA_GYM, UMEWAKA] + NAKANO_IDS + SHINAGAWA_IDS + [CLOSED]
PREVIOUS_HEIWA_POLICY = {
    'id': NAKANO_IDS[1], 'status': 'conditional',
    'summary': '利用3日前までは無料取消。当日・前日・前々日は取消不可で利用料金が発生します。荒天による途中中止で残り1時間以上の場合は後半1時間分の還付対象。照明料の扱いは公式案内を確認してください。',
    'source_url': 'https://information.konamisportsclub.jp/file.jsp?id=33348',
    'checked_at': '2026-10-14',
}


def entry(ident, source, note, rows):
    return {'id': ident, 'checked_at': CHECKED, 'fee_note': note,
            'fee_options': [{'label': label, 'amount': amount, 'unit': unit,
                             'conditions': note, 'source_url': source}
                            for label, amount, unit in rows]}


def reviewed_fees():
    result = []
    for ident in TAMA_IDS:
        baseball = ident == 'tokyo-venue-58dddea55c17'
        unit = ('野球場' if baseball else '球技場') + '1面・2時間'
        city = 730 if ident == TAMA_IDS[0] else 2080
        note = '大人の通常団体貸切。10人以上の登録団体が対象。市内区分は構成員の半数以上が市内在住・在勤・在学等の登録要件によります。子ども・障害者減額、備品等は別。'
        rows = [('市内団体・大人', city, unit)]
        if baseball:
            note += '貝取南公園野球場は市外団体使用不可。球技場と別の施設区分です。'
        else:
            rows.append(('市外団体・大人', city * 2, unit))
        if ident in TAMA_IDS[3:5]:
            note += '諏訪南は野球場兼球技場の同じ用地。球技場として使う間は野球場として同時使用できません。'
        result.append(entry(ident, TAMA_GUIDE, note, rows))

    for ident in KODAIRA_IDS:
        city = 1700 if ident == 'tokyo-venue-4b48ca660485' else 1500
        note = '大人の通常グラウンド使用料。市外団体は5割増し。利用できる種目・団体登録の要件は公式施設案内に従い、この料金確認でサッカー等の許可範囲を広げるものではありません。入場料徴収時は通常料の3倍、照明は別。'
        rows = [('市内団体・大人', city, 'グラウンド1面・2時間'),
                ('市外団体・大人', city * 3 // 2, 'グラウンド1面・2時間')]
        if ident == 'tokyo-venue-4b48ca660485':
            note += '小川西の夜間照明は1時間4,200円（市外6,300円）を別途加算。'
        else:
            note += '1月5～31日・11月16日～12月27日の最終1時間枠は通常2時間料の半額。'
            rows += [('市内団体・冬季最終枠', city // 2, 'グラウンド1面・冬季最終1時間'),
                     ('市外団体・冬季最終枠', city * 3 // 4, 'グラウンド1面・冬季最終1時間')]
        result.append(entry(ident, KODAIRA, note, rows))

    for ident in SUMIDA_FIELDS:
        rows = []
        for room, amounts in [('フットサルコート1面', (10000, 12000, 15000, 18000)),
                              ('少年サッカー場', (9000, 10800, 13500, 16200)),
                              ('陸上トラック・インフィールド全面', (10000, 12000, 15000, 18000))]:
            rows += [(room + ' / ' + label, price, room + '・2時間')
                     for label, price in zip(('区内・一般・平日', '区内・一般・土日祝',
                                              '区外・一般・平日', '区外・一般・土日祝'), amounts)]
        result.append(entry(ident, SUMIDA_FEE,
                            '一般団体の通常貸切。フットサル用コートの他種目料金や児童割引は採用していません。少年サッカー場はピッチ規格名で、料金は一般区分。照明は別途1時間フットサル1面700円、少年サッカー場・陸上全面2,100円。営利・入場料徴収等の割増対象は2倍、事前の利用条件確認が必要。', rows))

    rows = []
    for room, city, outside in [
        ('メインアリーナ3分の1面', (6600, 8430, 11730, 7330), (9900, 12650, 17600, 11000)),
        ('サブアリーナ全面', (9900, 12650, 17600, 11000), (14850, 18970, 26400, 16500)),
        ('サブアリーナ半面', (4950, 6320, 8800, 5500), (7420, 9480, 13200, 8250)),
    ]:
        for group, prices in [('区民団体', city), ('区外団体', outside)]:
            for label, price in zip(('平日9～12時・12～15時', '平日15～18時',
                                      '平日18～21時・土日祝9～21時各枠'), prices[:3]):
                rows.append((room + ' / ' + group + ' / ' + label, price, room + '・3時間'))
            rows.append((room + ' / ' + group + ' / 21～22時30分', prices[3], room + '・1時間30分'))
    result.append(entry(SUMIDA_GYM, 'https://www.sumidacity-gym.com/facility/3f.php',
                        '通常団体貸切の指定面数のみ。メイン3分の1面はバスケット・バレー各1面。現在の予約システムはサブアリーナのバスケット利用不可を案内しており、サブ料金をバスケット料金とは扱いません。3時間と最終1時間30分は別単位。区民・区外の公表端数を保持し、個人入場料・備品・減免は含めません。', rows))

    rows = []
    for label, city, outside in [
        ('平日', (4840, 5830, 8800, 17270), (7260, 8740, 13200, 25900)),
        ('土日祝', (5830, 6930, 10450, 23100), (8740, 10390, 15670, 34650)),
    ]:
        for group, prices in [('区内団体', city), ('区外団体', outside)]:
            rows += [(group + ' / ' + label + ' / ' + slot, price, '体育館全面・' + duration)
                     for slot, duration, price in zip(('9～12時', '12時30分～16時30分', '17～21時', '9～21時'),
                                                     ('3時間', '4時間', '4時間', '全日12時間'), prices)]
    result.append(entry(UMEWAKA, 'https://information.konamisportsclub.jp/trust/umewaka/pricing/',
                        '体育館の通常団体貸切。個人開放170円や会議室料金とは別。午前3時間・午後夜間4時間・全日を分離。用具別途（バレー・バスケット各300円、バドミントン1面100円等）。区外の公表料金をそのまま記録し、倍率から推測していません。', rows))

    result.append(entry(NAKANO_IDS[0], MYOSHOJI,
                        '利用料が公式に無料と明記された運動広場。10人以上、全員または半数以上が中野区在住・在勤・在学という団体登録要件があります。中野区の利用日は毎月1～15日。サッカーはフル規格不可。営利使用禁止。無料は未確認額の代入ではありません。',
                        [('登録要件を満たす団体・通常利用', 0, '運動広場1面・2時間')]))
    result.append(entry(NAKANO_IDS[1], HEIWA,
                        '多目的運動広場1面・通常団体利用。少年・高齢者減額を除く2時間枠。照明は別途30分700円で、指定時間帯は利用必須。営利団体登録不可。練習試合の相手団体利用は事前報告が必要です。',
                        [('通常団体利用・減額なし（照明別）', 2900, '多目的運動広場1面・2時間')]))
    rows = []
    for room, prices in [('全面', (18400, 22200, 25600, 30900, 19700, 23700, 35500, 8400, 10000)),
                          ('半面', (9200, 11100, 12800, 15450, 9850, 11850, 17750, 4200, 5000))]:
        slots = [('平日9～12時', '3時間'), ('土日9～12時', '3時間'),
                 ('平日13～17時', '4時間'), ('土日13～17時', '4時間'),
                 ('平日17時45分～20時15分', '2時間30分'), ('土曜17時45分～20時15分', '2時間30分'),
                 ('日曜17時45分～21時30分', '3時間45分'),
                 ('平日20時30分～22時', '1時間30分'), ('土曜20時30分～22時', '1時間30分')]
        rows += [('全開放・' + room + ' / ' + label, price, '体育館' + room + '・' + duration)
                 for (label, duration), price in zip(slots, prices)]
    result.append(entry(NAKANO_IDS[2], SAGINOMIYA,
                        '現行ページがリンクする2024年7月以降の体育館「全開放」料金。無料の全開放登録区分を対象とし、登録・更新に各1,000円かかる一般団体の割引は混ぜません。全面・半面と時間長を分離。名簿未登録者は利用不可。半面はバスケットゴール1基のみで全面試合用ではありません。', rows))

    for ident, pdf, city, outside in [
        (SHINAGAWA_IDS[0], '17', (3500, 4600, 5800), (4200, 5500, 7000)),
        (SHINAGAWA_IDS[1], '18', (4600, 6000, 7600), (5500, 7200, 9100)),
        (SHINAGAWA_IDS[2], '16', (5300, 6900, 8800), (6400, 8300, 10600)),
    ]:
        rows = []
        for group, prices in [('区内団体', city), ('区外団体', outside)]:
            rows += [(group + ' / ' + slot, price, 'スポーツ室・' + duration)
                     for slot, duration, price in zip(('9～12時', '13～16時30分', '17時30分～21時30分'),
                                                     ('3時間', '3時間30分', '4時間'), prices)]
        result.append(entry(ident, 'https://www.city.shinagawa.tokyo.jp/ct/pdf/hpg000000314_' + pdf + '.pdf',
                            '文化センターのスポーツ室貸切。軽スポーツ室・会議室・個人入場料ではありません。午前3時間・午後3時間30分・夜間4時間を別単位で記録。日曜祝日は17時閉館で夜間利用不可。社会教育団体等の減額は除く通常料金。営利使用不可。', rows))
    return result


def policy(ident, source, summary):
    return {'id': ident, 'status': 'conditional', 'summary': summary,
            'source_url': source, 'checked_at': CHECKED}


def reviewed_policies():
    result = [policy(ident, TAMA_GUIDE,
                     '支払済みの自己都合取消は利用月の前月1～15日なら80%、以後利用3日前まで50%還付、2日前以降は返金なし。天候等で利用不能なら100%（30分以上使用後は不可）。手続きは紙の承認書兼明細書を持参し体育館・武道館・温水プール窓口で行い、オンライン決済分も現金還付。大会開催等の施設利用料はこの一般還付の対象外。') for ident in TAMA_IDS]
    result += [policy(ident, 'https://www.city.kodaira.tokyo.jp/kurashi/002/002684.html',
                      '申請・納付後は利用14日前までの取消で使用料を還付。申請をしないまま放置すると予約制限の対象になる場合があります。天候時の具体的な還付条件・直前取消料はこの公式案内だけでは未確認のため、無料とは案内しません。') for ident in KODAIRA_IDS]
    result += [policy(ident, 'https://sumidacity-ground.com/guide',
                      '支払済みは14日前まで全額、13～7日前50%、6日前以降は還付なし。台風・豪雨等で管理者が閉鎖した場合は全額還付ですが、通常の雨は閉鎖扱いではありません。還付は承認書等を持参し窓口手続き。未払の13～7日前取消1点、6日前以降2点、累積6点で6か月の予約制限。') for ident in SUMIDA_FIELDS]
    result.append(policy(SUMIDA_GYM, 'https://www.sumidacity-gym.com/sp/guide/dantai/introduction.php',
                         '支払済みは14日前まで100%、13～7日前50%、6日前以降0%還付（利用日を除く）。代表者が登録カード・本人確認書類・口座情報を持参し受付で取消、返金は後日振込。未払はWeb取消可能ですが13～7日前1点、6日前以降2点、過去2年で累積6点に達すると6か月予約停止。屋外の雨天免除は適用しません。'))
    result.append(policy(NAKANO_IDS[0], MYOSHOJI,
                         '3日前まで予約システムで取消可能。2日前～当日は管理事務所へ電話し、翌月末まで予約等の制限対象。無断不使用は翌々月末まで制限。荒天等の利用不能は管理者が判断し、開始前までの連絡が必要です。利用料は無料でも無断取消が自由になるわけではありません。'))
    result.append(policy(NAKANO_IDS[1], HEIWA,
                         '公開公式資料間で取消条件が相違。旧案内（id=33348）は3日前まで無料・2日前以降利用料発生、2026年1月30日案内は7日前まで50%還付・6日前以降なし。Web取消期限にも資料差があるため申込前に管理者へ確認してください。無条件の無料取消とは案内しません。未使用照明料は30分単位で還付。'))
    result += [policy(ident, 'https://www.city.shinagawa.tokyo.jp/reiki/H421902100022/print.html',
                      'スポーツ室は7日前まで（閉館日なら翌開館日）に取消申出し、相当の理由が認められれば全額還付。自己都合の6日前以降は通常還付対象外。本人の責任でない不使用は全額、公用等による取消は開始前または3分の2経過前なら全額、それ以後は半額。還付申請が必要。ホール・プールの別期限は流用しません。') for ident in SHINAGAWA_IDS]
    return result


def mark_closed():
    path = CATALOGS / 'tokyo_expansion.json'
    original = path.read_text(encoding='utf-8')
    data = json.loads(original)
    rows = data
    row = next(row for row in rows if row['id'] == CLOSED)
    before = json.loads(json.dumps(row))
    row.update(availability_status='SUSPENDED', checked_at=CHECKED,
               availability_note='中央公園グラウンド・陸上競技場は改修工事のため2026年4月1日～2027年3月末（予定）休場。工期は変更の場合あり。小平市公式案内で再開を確認するまで通常検索から除外します。')
    source = {'title': '小平市公式：中央公園グラウンド改修休場・料金案内', 'url': KODAIRA}
    if source not in row['sources']:
        row['sources'].append(source)
    if before != row:
        old = json.dumps(before, ensure_ascii=False, indent=2)
        new = json.dumps(row, ensure_ascii=False, indent=2)
        # Replace only this existing object's serialization, not the rest of the catalog.
        old = '\n'.join('  ' + line for line in old.splitlines())
        new = '\n'.join('  ' + line for line in new.splitlines())
        if original.count(old) != 1:
            raise ValueError('Unexpected base catalog formatting')
        rendered = original.replace(old, new, 1)
        assert json.loads(rendered) == data
        path.write_text(rendered, encoding='utf-8')


def main():
    fees, policies = reviewed_fees(), reviewed_policies()
    validate(fees)
    catalog = {row['id']: row for row in get_catalog()['courts']}
    assert len(REVIEWED_IDS) == len(set(REVIEWED_IDS)) == 21
    assert len(fees) == 20 and len(policies) == 18
    assert all(ident in catalog for ident in REVIEWED_IDS)
    for review in fees:
        row = catalog[review['id']]
        if row.get('fee_checked_at') != CHECKED and has_price(row):
            raise ValueError('Refusing to replace an already priced venue: ' + review['id'])
    # Check both overlay conflicts before making any changes.
    for filename, additions in [('fee_plans.json', fees), ('cancellation_policies.json', policies)]:
        existing = {row['id']: row for row in json.loads((CATALOGS / filename).read_text(encoding='utf-8'))}
        for row in additions:
            if row['id'] in existing and existing[row['id']] != row and not (
                    filename == 'cancellation_policies.json' and row['id'] == NAKANO_IDS[1]
                    and existing[row['id']] == PREVIOUS_HEIWA_POLICY):
                raise ValueError('Refusing to replace existing review: ' + row['id'])
    mark_closed()
    append_reviews(CATALOGS / 'fee_plans.json', fees)
    # Preserve the superseded statement in the dated report; never silently keep
    # advertising free cancellation when current official documents disagree.
    path = CATALOGS / 'cancellation_policies.json'
    original = path.read_text(encoding='utf-8')
    old = json.dumps(PREVIOUS_HEIWA_POLICY, ensure_ascii=False, separators=(',', ':'))
    corrected = next(row for row in policies if row['id'] == NAKANO_IDS[1])
    if old in original:
        assert original.count(old) == 1
        path.write_text(original.replace(old, json.dumps(corrected, ensure_ascii=False, separators=(',', ':')), 1), encoding='utf-8')
    append_reviews(CATALOGS / 'cancellation_policies.json', policies)
    print(json.dumps({'reviewed_records': 21, 'new_fee_reviews': 20, 'new_cancellation_reviews': 17,
                      'corrected_cancellation_reviews': 1, 'closed_records': 1}))


if __name__ == '__main__':
    main()
