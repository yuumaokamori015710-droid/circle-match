"""Record official same-unit tariffs and two bounded availability corrections."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'outputs'))
from venues.fees import validate
from venues.sports_catalog import get_catalog, has_price
from record_venue_fee_review_20261018 import append_reviews, entry as old_entry

CHECKED = '2026-10-23'
CATALOGS = ROOT / 'outputs/venues/catalogs'
HIGASHI = ['tokyo-venue-c5c68276fb25', 'tokyo-venue-865b431ef9b6',
           'tokyo-venue-6c680a5347e7', 'tokyo-venue-ec7d0ac023ca',
           'tokyo-gym-9b00ba3ee03d', 'tokyo-gym-51188a9f707c']
KIYOSE = ['tokyo-venue-eb34fa4336b1', 'tokyo-gym-f948f874fd53', 'tokyo-gym-69b886badd4e']
INAGI = ['tokyo-venue-8376df208306', 'tokyo-venue-5b8cfd045305',
         'tokyo-venue-106255f60722', 'tokyo-venue-6bc70316b229',
         'tokyo-venue-10ad05c36089', 'tokyo-gym-7178502efd55']
MUSASHINO = ['tokyo-venue-76cc5329900e', 'tokyo-venue-a28254e6f948', 'tokyo-venue-c39d95077093']
KOKUBUNJI = ['tokyo-venue-a2d6191898f8', 'tokyo-gym-6c42ed662bb9']
REVIEWED_IDS = HIGASHI + KIYOSE + INAGI + MUSASHINO + KOKUBUNJI
HIGASHI_LAW = 'https://www2.city.higashikurume.lg.jp/reiki_int/reiki_honbun/g146RG00000302.html'
WEST_CLOSED = 'https://www.city.higashikurume.lg.jp/_res/projects/default_project/_page_/001/028/861/080401n.pdf'
HIGASHI_GYM = 'https://www.city.higashikurume.lg.jp/shisetsu/siyouryou/1003417.html'
WAKUWAKU = 'https://www.city.higashikurume.lg.jp/shisetsu/fukushi/hoken/1002100.html'
KIYOSE_BASE = 'https://www.city.kiyose.lg.jp/shisetsu/riyouyoyaku/'
INAGI_PRICES = 'https://www.city.inagi.tokyo.jp/kanko/sports/1004109/1004114.html'
HIRAO = 'https://www.city.inagi.tokyo.jp/shisetsu/sports/1004857/1004858/1004863.html'
TAMAGAWA = 'https://www.city.inagi.tokyo.jp/shisetsu/sports/1004857/1004883/1004886.html'
NAGAMINE = 'https://www.inaginagamine-sportsfield.jp/facilities/'
NAGAMINE_RULES = 'https://www.inaginagamine-sportsfield.jp/guide/pdf/rule.pdf'
INAGI_WEATHER = 'https://inagisoutai.jp/request/'
MUSA_BASE = 'https://www.musashino.or.jp/_res/projects/default_project/_page_/001/001/578/'
MUSA_PRICES = MUSA_BASE + '1001578-03.pdf'
MUSA_GUIDE = MUSA_BASE + '202604kashikiri.pdf'
MIDORI = 'https://www.musashino.or.jp/sports/1001550/1001571.html'
HIKARI = 'https://www.city.kokubunji.tokyo.jp/shisetsu/sport/hikari/1004200.html'
SHIMIN = 'https://www.city.kokubunji.tokyo.jp/shisetsu/sport/shimin/1004197.html'
KOKU_GUIDE = 'https://www.city.kokubunji.tokyo.jp/culture-sports-tourism/sports/1011397/1002609.html'


def entry(ident, source, note, rows):
    return dict(old_entry(ident, source, note, rows), checked_at=CHECKED)


def local_outside(room, amount, duration, labels=('市内通常', '市外通常'), multiplier=2):
    return [(room + ' / ' + label, int(amount * factor), room + '・' + duration)
            for label, factor in zip(labels, [1, multiplier])]


def reviewed_fees():
    result = [entry(HIGASHI[0], 'https://www.city.higashikurume.lg.jp/shisetsu/sports/hiroba/1014634.html',
                    '上の原グラウンド全面の団体貸切、1時間1,200円。事前団体登録が必要。照明は別途1時間1,900円で、10～2月は16時30分から原則使用必須。照明を使わなかった場合も返金不可。団体の営利行事は条例で使用拒否対象。市外加算は推測して加えていません。',
                    [('全面・通常貸切（照明別）', 1200, 'グラウンド全面・1時間')])]
    for ident, page in [(HIGASHI[1], '1003067'), (HIGASHI[2], '1003065')]:
        result.append(entry(ident, 'https://www.city.higashikurume.lg.jp/shisetsu/sports/hiroba/' + page + '.html',
                            '現行施設案内と令和8年4月施行条例を照合した全面貸切1時間300円。団体登録が必要。少年野球・サッカー等の用途制限と営業時間に従います。廃止された西部運動広場へこの料金を流用しません。営利行事は条例で使用拒否対象。',
                            [('運動広場・通常貸切', 300, '運動広場全面・1時間')]))
    result.append(entry(HIGASHI[4], WAKUWAKU,
                        '体育室貸切は各2時間（8時30分からの6区分）。一般と市外、全面と半面を分離。個人50円/時間や集会室料金は含めません。空調のない体育室です。',
                        local_outside('体育室全面', 2400, '2時間', ('一般', '市外'), 1.5)
                        + local_outside('体育室半面', 1200, '2時間', ('一般', '市外'), 1.5)))
    rows = []
    for room, weekday, weekend in [('第1体育室全面', 13450, 14450),
                                   ('第1体育室半面', 6800, 7300), ('第1体育室4分の1面', 3400, 3700)]:
        rows += [(room + ' / 平日', weekday, room + '・2時間10分'),
                 (room + ' / 土日祝', weekend, room + '・2時間20分')]
    result.append(entry(HIGASHI[5], HIGASHI_GYM,
                        '第1体育室の通常貸切。市の改定後欄と指定管理者の現行料金を照合。平日2時間10分、土日祝2時間20分を別単位にし、半面6,800/7,300円・4分の1面3,400/3,700円は市の明記額を採用。個人利用・回数券の市外1.5倍を貸切に自動適用しません。事前登録、備品等は別。', rows))

    rows = []
    for label, amount in [('中学生以下', 1200), ('大人・平日', 3500), ('大人・土日祝', 4600)]:
        rows += [(label + ' / 市内', amount, '下宿運動公園広場全面・2時間'),
                 (label + ' / 市外', amount * 3 // 2, '下宿運動公園広場全面・2時間')]
    result.append(entry(KIYOSE[0], KIYOSE_BASE + '1005434.html',
                        '下宿運動公園広場の団体貸切。中学生以下は硬式野球以外の運動、大人はニュースポーツ等という用途条件を保全。成人サッカー大会の許可とは案内しません。市外5割増。隣接体育館や内山サッカー場とは別施設・別料金。', rows))
    for ident, source, room, amounts in [
        (KIYOSE[1], KIYOSE_BASE + '1005435.html', '競技場', [2900, 4000, 5200]),
        (KIYOSE[2], KIYOSE_BASE + '1005439.html', '多目的屋内ひろば', [2600, 3400, 4800]),
    ]:
        rows = []
        for slot, duration, amount in zip(['午前9～12時', '午後13～17時', '夜間18～22時'],
                                          ['3時間', '4時間', '4時間'], amounts):
            rows += [(room + '全面 / 市内 / ' + slot, amount, room + '全面・' + duration),
                     (room + '全面 / 市外 / ' + slot, amount * 3 // 2, room + '全面・' + duration)]
            if ident == KIYOSE[1]:
                rows += [(room + '半面 / 市内 / ' + slot, amount // 2, room + '半面・' + duration),
                         (room + '半面 / 市外 / ' + slot, amount * 3 // 4, room + '半面・' + duration)]
        result.append(entry(ident, source,
                            '屋内の通常貸切、午前3時間と午後・夜間4時間を分離。市外5割増。全日等の通し区分・会議室・屋外広場の料金は混ぜません。'
                            + ('競技場の半面は全面の半額と公式に明記。' if ident == KIYOSE[1] else '大きな音を発する機器類の使用は不可。'), rows))

    result.append(entry(INAGI[0], HIRAO,
                        '令和8年5月更新の施設別案内を優先。登録団体は体育館・グラウンド無料、市外未登録は体育館1,020円/時間・グラウンド680円/時間。旧一般料金表の510円/340円を現在の登録団体へ請求しません。市外未登録は窓口申込。グラウンドは少年サッカー等向けで成人大会可とは案内せず、体育館はフットサル不可。空調1,000円/2時間、照明870円（市外1,740円）/時間は別。',
                        [('体育館・登録団体のみ無料', 0, '体育館全面・1時間'),
                         ('体育館・市外未登録', 1020, '体育館全面・1時間'),
                         ('グラウンド・登録団体のみ無料', 0, 'グラウンド全面・1時間'),
                         ('グラウンド・市外未登録', 680, 'グラウンド全面・1時間')]))
    result.append(entry(INAGI[1], TAMAGAWA,
                        '多摩川緑地公園の多目的広場。市が団体1単位3時間無料と明記し、無料の根拠を確認。団体登録・予約等の利用条件は必要で、一般開放や予約不要とは案内しません。野球場の料金と混ぜません。',
                        [('多目的広場・団体利用（公式無料）', 0, '多目的広場全面・3時間')]))
    rows = []
    for room, adult, child in [('サッカー場', 9880, 4940), ('フットサル場', 7390, 3690)]:
        for group, multiplier in [('登録団体', 1), ('未登録・市外', 2)]:
            rows += [(room + ' / ' + group + ' / 大人', adult * multiplier, room + '1面・2時間'),
                     (room + ' / ' + group + ' / 小学生以下のみ', child * multiplier, room + '1面・2時間')]
    result.append(entry(INAGI[2], NAGAMINE,
                        '通常貸切のサッカー・フットサルを別単位で収録。子どもは選手全員小学生以下、未登録市外は2倍。照明はサッカー2,690円・フットサル670円/時間が別（市外は2倍）。入場料徴収時の5倍規定は通常料金の範囲外。2026年7月利用基準は営利目的と日時・会場を指定した不特定多数のネット/SNS募集を禁止しており、追加料金だけで一般募集大会が許可されるとは案内しません。', rows))
    result.append(entry(INAGI[3], INAGI_PRICES,
                        '総合グラウンド競技場の団体貸切1時間。市内登録2,950円、未登録・市外は2倍。個人ランニング120円や放送室料金を混ぜません。原則9～17時。',
                        local_outside('競技場全面', 2950, '1時間', ('市内登録', '未登録・市外'))))
    rows = []
    for label, amount in [('大人料金区分（少年サッカー用途制限あり）', 3270), ('小学生以下のみ', 1630)]:
        rows += [(label + ' / 市内登録', amount, 'サッカー場1面・2時間'),
                 (label + ' / 未登録・市外', amount * 2, 'サッカー場1面・2時間')]
    result.append(entry(INAGI[4], INAGI_PRICES,
                        '若葉台公園のサッカー場通常貸切、2時間。未登録・市外2倍。指定管理者はサッカー場を「少年のみ」と案内しており、料金表の大人区分は成人サッカー大会の許可を意味しません。サッカー照明1,460円/時間は別で、野球照明3,220円/時間を混ぜません。', rows))
    rows = []
    for room, amount in [('メインアリーナ全面', 10720), ('メインアリーナ半面', 5360),
                         ('メインアリーナ3分の1面', 3580), ('ウエルネスアリーナ全面', 5360),
                         ('ウエルネスアリーナ半面', 2680)]:
        rows += local_outside(room, amount, '2時間50分', ('市内登録', '未登録・市外'))
    result.append(entry(INAGI[5], 'https://inagisoutai.jp/facilities/177/',
                        '団体貸切のメイン・ウエルネスアリーナ。各2時間50分で全面・半面・3分の1面を分離。未登録・市外2倍。3分の1面3,580円は公式表の値で、10,720円の単純割算ではありません。個人260円やレクリエーション室の料金は除外。', rows))

    common = '通常の団体貸切。市民以外は2倍。入場料・参加料徴収時は別の3倍規定があり、通常料金には含めません。団体区分・事前登録・許可条件に従い、営利大会や無人予約を保証しません。'
    result.append(entry(MUSASHINO[0], MUSA_PRICES,
                        common + '各2時間、全面と半面を分離。2026年11月～2027年3月は人工芝張替えにより休場予定（公式2026年10月告知）。この料金は工事中の予約可能性を示しません。',
                        local_outside('緑町スポーツ広場全面', 6000, '2時間')
                        + local_outside('緑町スポーツ広場半面', 3000, '2時間')))
    rows = []
    for room, amount in [('メインアリーナ全面', 10620), ('メインアリーナ3分の2面', 7080),
                         ('メインアリーナ半面', 5310), ('メインアリーナ3分の1面', 3540),
                         ('サブアリーナ全面', 5200), ('サブアリーナ半面', 2600)]:
        rows += local_outside(room, amount, '2時間45分')
    result.append(entry(MUSASHINO[1], MUSA_PRICES,
                        common + '体育館の1区分は9～11時45分等の2時間45分。全日通し・会議室・ダンス室・個人利用の料金はこの範囲に混ぜません。', rows))
    result.append(entry(MUSASHINO[2], MUSA_PRICES,
                        common + '陸上競技場全面とフィールドのみ、2時間と9～17時の全日8時間を分離。5～8月17～19時はフィールドの枠であり、競技場全面の同時間帯は料金表で貸出対象外。備品・個人料金は別。',
                        local_outside('陸上競技場全面', 9000, '2時間')
                        + local_outside('陸上競技場フィールド', 4500, '2時間')
                        + local_outside('陸上競技場全面', 36000, '全日8時間')))
    result.append(entry(KOKUBUNJI[1], SHIMIN,
                        '市民スポーツセンター第一体育室の通常団体貸切。9～11時30分等の各2時間30分、全面と半面を分離。市民料金と市外2倍を収録し、小平市との相互利用条件は別途登録確認が必要。第二体育室・個人300円は混ぜません。原則10人以上の団体、施設内の有料設備等は別。',
                        local_outside('第一体育室全面', 6000, '2時間30分')
                        + local_outside('第一体育室半面', 3000, '2時間30分')))
    return result


def policy(ident, source, summary):
    return {'id': ident, 'status': 'conditional', 'summary': summary,
            'source_url': source, 'checked_at': CHECKED}


def reviewed_policies():
    result = [policy(i, HIGASHI_LAW,
                     '現行市民体育施設条例第8条では、納付済み使用料は原則還付しないと規定。教育委員会が特別の理由を認める場合のみ全部又は一部の還付が可能。通常の無料取消期限や雨天時の具体的料率は同条例から推測しません。') for i in HIGASHI[:3]]
    result.append(policy(KIYOSE[0], KIYOSE_BASE + '1005434.html',
                         '使用30日前まで80%、20日前まで60%、前日まで30%を還付。納付後の日付・時間・施設変更は不可。承認書と印鑑を持参し下宿地域市民センター窓口で取消。天候不順等で中止の際は同センターに確認して還付手続きが必要で、自動返金ではありません。'))
    for ident, page in [(KIYOSE[1], '1005435.html'), (KIYOSE[2], '1005439.html')]:
        result.append(policy(ident, KIYOSE_BASE + page,
                             '使用30日前まで80%、20日前まで60%、10日前まで30%を還付、それ以降は還付なし。屋外広場の「前日まで30%」を屋内へ適用しません。承認書・印鑑を用意して当該窓口で取消手続き。納付後の日付・時間・施設変更は不可。屋内の雨天免除は案内しません。'))
    result += [policy(i, INAGI_WEATHER,
                      '雨・雪・雷・大風による屋外施設の使用不可は、利用開始1時間前から翌日23時59分までに指定のWeb申告が必要。電話申告は受付不可、申告なしは返金対象外。総合グラウンド・若葉台多目的広場に適用。通常の自己都合取消の無料期限を示す規定ではありません。') for i in INAGI[3:5]]
    result.append(policy(INAGI[2], NAGAMINE_RULES,
                         '2026年7月1日利用基準では納付後の返金は原則不可。設備不備・天災や天候不良で施設使用不可となり窓口・電話で中止連絡した場合は返金。天候は開始1時間前の現地状況で判断し、開始後30分以内の中止も返金対象。単なる雷による一時中断は返金せず、同30分以内中止の例外を除きます。他の稲城施設のWeb申告方式を転用しません。'))
    for ident in MUSASHINO:
        summary = '確定後から利用3日前まで取消料50%、2日前以降100%。先着Web予約を予約当日に取り消す場合のみ取消料なし。未確定抽選の自動取消は無料。窓口手続きは印鑑持参。通常取消と未確定抽選を混同しません。'
        if ident == MUSASHINO[0]:
            summary += '緑町の天候中止は施設判断。利用者判断日も不使用なら各回開始60分以内に連絡が必要で、時間の半分を超過してからの中止は返金対象外（公式施設案内も参照）。'
        result.append(policy(ident, MUSA_GUIDE, summary))
    result.append(policy(KOKUBUNJI[1], KOKU_GUIDE,
                         '使用1か月前までの取消申出で全額、10日前までで半額還付。承認書兼領収書等と印鑑を持参し施設窓口で申請。使用者に責任のない使用不可は全額還付。屋外の天候による全額・半額規定を屋内体育室へ自動適用しません。'))
    return result


def update_availability():
    path = CATALOGS / 'tokyo_expansion.json'
    original = path.read_text(encoding='utf-8')
    rows = json.loads(original)
    rendered = original
    for row in rows:
        if row['id'] not in {HIGASHI[3], KOKUBUNJI[0]}:
            continue
        before = json.loads(json.dumps(row))
        if row['id'] == HIGASHI[3]:
            row.update(availability_status='SUSPENDED', checked_at=CHECKED,
                       availability_note='西部運動広場は2026年3月31日をもって廃止。市の2026年4月1日広報と現行条例の施設一覧から確認。旧300円/時間は現行料金として追加せず、通常検索から除外します。')
            source = {'title': '東久留米市公式：西部運動広場廃止のお知らせ', 'url': WEST_CLOSED}
        else:
            note = '第一体育室は天井の耐震性不足により2025年9月12日から当面利用停止。第二体育室・フィットネスルームは利用可能で、施設全体の休館ではありません。停止室の旧料金は現行予約料金に追加しません。'
            if note not in row['booking_note']:
                row['booking_note'] += ' ' + note
            row['checked_at'] = CHECKED
            source = {'title': '国分寺市公式：第一体育室のみ利用停止、他室は利用可', 'url': HIKARI}
        if source not in row['sources']:
            row['sources'].append(source)
        if row != before:
            old = '\n'.join('  ' + line for line in json.dumps(before, ensure_ascii=False, indent=2).splitlines())
            new = '\n'.join('  ' + line for line in json.dumps(row, ensure_ascii=False, indent=2).splitlines())
            if rendered.count(old) != 1:
                raise ValueError('Unexpected catalog formatting: ' + row['id'])
            rendered = rendered.replace(old, new, 1)
    assert json.loads(rendered) == rows
    if rendered != original:
        path.write_text(rendered, encoding='utf-8')


def main():
    fees, policies = reviewed_fees(), reviewed_policies()
    validate(fees)
    assert len(REVIEWED_IDS) == len(set(REVIEWED_IDS)) == 20
    assert len(fees) == 18 and len(policies) == 13
    catalog = {r['id']: r for r in get_catalog()['courts']}
    assert all(i in catalog for i in REVIEWED_IDS)
    for row in fees:
        current = catalog[row['id']]
        if current.get('fee_checked_at') != CHECKED and has_price(current):
            raise ValueError('Refusing to replace priced venue: ' + row['id'])
    for name, additions in [('fee_plans.json', fees), ('cancellation_policies.json', policies)]:
        existing = {r['id']: r for r in json.loads((CATALOGS / name).read_text(encoding='utf-8'))}
        for row in additions:
            if row['id'] in existing and existing[row['id']] != row:
                raise ValueError('Refusing to replace prior review: ' + row['id'])
    update_availability()
    append_reviews(CATALOGS / 'fee_plans.json', fees)
    append_reviews(CATALOGS / 'cancellation_policies.json', policies)
    print(json.dumps({'reviewed': 20, 'prices_added': 18, 'policies_added': 13, 'price_holds': 2}))


if __name__ == '__main__':
    main()
