"""Append October 22 official prices without changing venue identities or URLs."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'outputs'))
from venues.fees import validate
from venues.sports_catalog import get_catalog, has_price
from record_venue_fee_review_20261018 import append_reviews, entry as old_entry

CHECKED = '2026-10-22'
CATALOGS = ROOT / 'outputs/venues/catalogs'
NISHI = ['tokyo-venue-be1fb7d41bbb', 'tokyo-venue-0811b80ad770',
         'tokyo-venue-41aa12f2a8c7', 'tokyo-venue-353ed3db391e']
CHOFU = ['tokyo-venue-f135b6f82c5e', 'tokyo-venue-a26a50d5b465',
         'tokyo-venue-6684ff4142bf', 'tokyo-gym-b4feff7afe32', 'tokyo-venue-be48cc26a9d5']
HINO = ['tokyo-venue-543347cda5ea', 'tokyo-venue-47fed525a9bf',
        'tokyo-venue-e2e5c66bee23', 'tokyo-venue-80dd6145978b',
        'tokyo-venue-a0cdc2805448', 'tokyo-venue-7ebb38dd6059']
KUNI = ['tokyo-gym-2c73268dcb25', 'tokyo-venue-8639e4fc7765']
AKISHIMA = ['tokyo-gym-aa6770a96ad9', 'tokyo-venue-4fa20e780efe', 'tokyo-gym-884b76d9b9af']
REVIEWED_IDS = NISHI + CHOFU + HINO + KUNI + AKISHIMA
NISHI_GUIDE = 'https://www.city.nishitokyo.lg.jp/enjoy/sports/sports_shisetu/50981020151125.files/homepage.pdf'
CHOFU_BASE = 'https://www.city.chofu.lg.jp/040070/'
CHOFU_GUIDE = 'https://www.city.chofu.lg.jp/documents/2504/guidebook.pdf'
HINO_GROUNDS = 'https://hino-playground.com/facility/ballfield'
HINO_ARENA = 'https://hino-minamidaira-gym.com/'
HINO_HALL = 'https://www.city.hino.lg.jp/_res/projects/default_project/_page_/001/005/895/siseturyoukin.pdf'
HINO_TRACK = 'https://www.city.hino.lg.jp/shisetsu/sports/1001014.html'
KUNI_FEE = 'https://kuzaidan.or.jp/gym/rule/charge/'
KUNI_FIELD = 'https://kuzaidan.or.jp/gym/park/shisetsu-k2/'
KUNI_BASEBALL = 'https://kuzaidan.or.jp/gym/park/shisetsu-k3/'
AKISHIMA_GYM = 'https://www.city.akishima.lg.jp/bunka/sports/1004531/1007540/1004541.html'
AKISHIMA_FIELD = 'https://www.city.akishima.lg.jp/bunka/sports/1004531/1004533.html'
MIHORI = 'https://www.city.akishima.lg.jp/reiki/reiki_honbun/g131RG00000332.html'


def entry(ident, source, note, rows):
    return dict(old_entry(ident, source, note, rows), checked_at=CHECKED)


def reviewed_fees():
    result = []
    for ident, page, room, amount, note in [
        (NISHI[0], 'kenko', '広場1面', 1200,
         'サッカーは練習ができる程度の広さ。一般開放の市民限定条件と団体貸切は別。照明・駐車場なし。'),
        (NISHI[1], 'mukodai', 'B面', 2400,
         'サッカー等はB面の料金。A面は野球用で混ぜません。照明B面3,200円/時間は別。6～9時・18～21時は4～10月のみ。'),
        (NISHI[2], 'siminkoen', 'グラウンド1面', 1800,
         'この施設は市内・市外同額。ほかの西東京市施設の市外2倍を適用しません。照明1,400円/時間は別。'),
    ]:
        note = '団体登録による通常貸切、3時間枠。' + note
        rows = [('市内・市外共通' if ident == NISHI[2] else '市内団体', amount, room + '・3時間')]
        if ident != NISHI[2]:
            rows.append(('市外団体', amount * 2, room + '・3時間'))
        result.append(entry(ident, f'https://www.city.nishitokyo.lg.jp/sisetu/sports/{page}.html', note, rows))
    result.append(entry(NISHI[3], 'https://www.city.nishitokyo.lg.jp/sisetu/sports/sibakubo.html',
                        '団体登録による通常貸切。少年サッカー等向け。9～11時40分・11時40分～14時20分・14時20分～17時の各2時間40分と全日8時間を分離。市外団体は2倍、照明・駐車場なし。',
                        [('市内・通常枠', 1000, 'グラウンド1面・2時間40分'),
                         ('市外・通常枠', 2000, 'グラウンド1面・2時間40分'),
                         ('市内・全日9～17時', 3000, 'グラウンド1面・全日8時間'),
                         ('市外・全日9～17時', 6000, 'グラウンド1面・全日8時間')]))

    result.append(entry(CHOFU[0], CHOFU_BASE + 'p026091.html',
                        '人工芝サッカー場1面の通常2時間枠。夜間照明は別途30分1,000円。9～21時の各2時間、7～9時は11月16日～3月14日使用不可。事前団体登録・当日現地受付と支払いが必要。',
                        [('サッカー場・通常貸切（照明別）', 3000, 'サッカー場1面・2時間')]))
    result.append(entry(CHOFU[1], CHOFU_BASE + 'p026080.html',
                        '公式ページが「無料（暫定使用中のみ）」と明記する予約制運動広場。無料の根拠は自由利用のいこいの広場とは別。団体登録・現地で利用カード提示と承認書受取が必要。日中9～17時のサッカー場2時間枠を収録し、6～9時の3時間枠は混ぜません。',
                        [('サッカー場・日中・暫定使用中のみ無料', 0, 'サッカー場1面・2時間')]))
    result.append(entry(CHOFU[2], CHOFU_BASE + 'p026086.html',
                        'サッカーA面の使用料金は公式に無料。団体登録・現地カード提示・承認書受取が必要。通常9～11・11～13・13～15・15～17時、6～9月の最終枠のみ15～18時。工事中の7面ソフトボール場をサッカーA面の休止と混同しません。',
                        [('サッカーA面・通常枠', 0, 'サッカー場1面・2時間'),
                         ('サッカーA面・6～9月15～18時', 0, 'サッカー場1面・3時間')]))
    result.append(entry(CHOFU[3], CHOFU_GUIDE,
                        '2026年4月一部改正の市公式ガイドp9「C体育館」の貸切料金。9～12・12～15・15～18・18～21時の各3時間。市内2,400円・市外4,800円。テニス用小運動場や会議室の料金ではありません。事前団体登録・利用カード提示・現地払い。',
                        [('体育館・市内団体', 2400, '体育館全面・3時間'),
                         ('体育館・市外団体', 4800, '体育館全面・3時間')]))
    result.append(entry(CHOFU[4], 'https://www.chofucity-sports.or.jp/tabid/772/Default.aspx',
                        '大体育室の団体貸切。9～11時45分・12～14時45分・15～17時45分・18～20時45分の各2時間45分。登録10人以上・利用当日7人以上。個人400円やバスケット用でない小体育室の料金を混ぜません。',
                        [('大体育室半面', 3500, '大体育室半面・2時間45分'),
                         ('大体育室3分の1面', 2300, '大体育室3分の1面・2時間45分')]))

    rows = []
    for room, weekday, weekend in [('アリーナ全面', [12000, 8000, 10400], [15000, 10000, 13000]),
                                   ('アリーナ半面', [6000, 4000, 5200], [7500, 5000, 6500])]:
        for day, prices in [('平日', weekday), ('土日祝', weekend)]:
            for group, multiplier in [('市内', 1), ('市外', 2)]:
                for (slot, duration), amount in zip([('9～12時・12～15時', '3時間'),
                                                     ('15～17時・17～19時', '2時間'),
                                                     ('19～21時', '2時間')], prices):
                    rows.append((room + ' / ' + group + ' / ' + day + ' / ' + slot,
                                 amount * multiplier, room + '・' + duration))
    result.append(entry(HINO[0], HINO_ARENA + 'fee',
                        'アリーナ通常貸切。市内外・平日土日祝・全面半面・2時間3時間を分離。市外は2倍。備品・入場料徴収時の加算は別。団体登録と当日受付・現地払いが必要。市外団体の空き予約は利用1週間前から。個人入場料金は含めません。', rows))
    result.append(entry(HINO[1], HINO_GROUNDS,
                        '無料ですが貸切は日野市サッカー連盟所属の少年サッカー団体のみ。成人一般・市外団体が自由に無料予約できる施設ではありません。土日祝のみ貸切、平日は一般開放。少年サッカー場40m×60m、駐車場100円/時間は別。予約1区分の時間長は料金表にないため推測しません。',
                        [('所定の連盟所属少年団体のみ・貸切', 0, '少年サッカー場1面・予約1区分')]))
    result.append(entry(HINO[2], HINO_GROUNDS,
                        '公式運営者が無料と明記。少年サッカー・大人のサッカー等の練習向け。団体登録・事前予約に加え、利用許可書と当日受付が必要。駐車場100円/時間は別。料金表にない予約枠の時間長や成人大会の許可は推測しません。',
                        [('グラウンド・所定の利用許可を受けた団体', 0, 'グラウンド1面・予約1区分')]))
    rows = []
    for room, weekday, weekend in [('コミュニティホール全面', [13800, 9000, 10200, 13400], [17200, 9800, 11700, 14400]),
                                   ('コミュニティホール半面', [6900, 4500, 5100, 6700], [8600, 4900, 5900, 7200]),
                                   ('コミュニティホール3分の1面', [4600, 3000, 3400], [5700, 3300, 3900])]:
        for day, prices in [('平日', weekday), ('土日祝', weekend)]:
            for group, multiplier in [('市内', 1), ('市外', 2)]:
                for (slot, duration), amount in zip([('9～12時30分・13～16時30分', '3時間30分'),
                                                     ('17～19時', '2時間'), ('19～21時', '2時間'),
                                                     ('21～23時（金・土のみ）', '2時間')], prices):
                    rows.append((room + ' / ' + group + ' / ' + day + ' / ' + slot,
                                 amount * multiplier, room + '・' + duration))
    result.append(entry(HINO[3], HINO_HALL,
                        '市公式ページから現在も案内される2024年4月改定後のコミュニティホール貸切料。旧料金欄は採用せず、市外2倍と公表端数を保持。午前午後3時間30分と夜間2時間を区別。深夜21～23時は金・土のみ、3分の1面には深夜料の掲載なし。個人入場料・集会室・12分の1面・延長単価は除外。', rows))
    result.append(entry(HINO[4], HINO_TRACK,
                        '競技場の通常団体貸切。9～11・11～13・13～15・15～17時の2時間枠。全面・3分の1面・全日8時間を分離。入場料等を徴収する場合の10割増を別表示。市登録団体が対象。個人走路100円、器具・放送・駐車料は含めません。加算料だけで営利大会の許可を保証しません。',
                        [('全面・入場料徴収なし', 4000, '競技場全面・2時間'),
                         ('全面・入場料等徴収あり', 8000, '競技場全面・2時間'),
                         ('3分の1面・入場料徴収なし', 2000, '競技場3分の1面・2時間'),
                         ('3分の1面・入場料等徴収あり', 4000, '競技場3分の1面・2時間'),
                         ('全面全日・入場料徴収なし', 14000, '競技場全面・全日8時間'),
                         ('全面全日・入場料等徴収あり', 28000, '競技場全面・全日8時間')]))
    result.append(entry(HINO[5], HINO_GROUNDS,
                        '人工芝多目的広場68m×105mの通常貸切。一般・少年サッカー等。入場料その他これに類する料金を徴収する場合は2倍。事前団体登録・予約に加え、許可書と当日受付・現地払いが必要。加算料の掲載は個別の営利大会許可を保証しません。',
                        [('入場料等徴収なし', 4000, '多目的広場1面・2時間'),
                         ('入場料等徴収あり', 8000, '多目的広場1面・2時間')]))

    result.append(entry(KUNI[0], KUNI_FEE,
                        '第一体育室半面の通常貸切料金。日中9～12・12～15・15～18時、夜間18～21時は各3時間、21～22時のみ1時間。市内外を明記。個人300円や第二・第三体育室の料金は除外。当日申込半額は通常料金に混ぜません。',
                        [('第一体育室半面・市内・日中', 2800, '第一体育室半面・3時間'),
                         ('第一体育室半面・市外・日中', 4200, '第一体育室半面・3時間'),
                         ('第一体育室半面・市内・18～21時', 3800, '第一体育室半面・3時間'),
                         ('第一体育室半面・市外・18～21時', 5700, '第一体育室半面・3時間'),
                         ('第一体育室半面・市内・21～22時', 1200, '第一体育室半面・1時間'),
                         ('第一体育室半面・市外・21～22時', 1800, '第一体育室半面・1時間')]))
    field = entry(KUNI[1], KUNI_FIELD,
                  '既存の河川敷公園レコードは野球場A・Bとサッカー場の出典を併載。各競技1面1時間の通常貸切料を個別に収録。市内650円・市外975円。サッカー市内団体は15人以上かつ市内在住在勤在学11人以上。所定の登録・利用承認書・支払いが必要。',
                  [('サッカー場・市内', 650, 'サッカー場1面・1時間'),
                   ('サッカー場・市外', 975, 'サッカー場1面・1時間')])
    field['fee_options'] += entry(KUNI[1], KUNI_BASEBALL, field['fee_note'],
                                  [('河川敷公園野球場・市内', 650, '野球場1面・1時間'),
                                   ('河川敷公園野球場・市外', 975, '野球場1面・1時間')])['fee_options']
    result.append(field)

    result.append(entry(AKISHIMA[0], MIHORI,
                        '市条例別表による体育室の通常貸切料。9～12・12～15・15～18・18～21時の各3時間、半面は全面の2分の1。研修室800円・個人200円と区別。予約・利用承認の条件に従います。',
                        [('体育室全面・通常貸切', 2000, '体育室全面・3時間'),
                         ('体育室半面・通常貸切', 1000, '体育室半面・3時間')]))
    result.append(entry(AKISHIMA[1], AKISHIMA_FIELD,
                        '大神公園の一般用サッカー場1面・2時間は公式に無料。ただし無料施設の貸出は市内団体または市内在住在勤在学者に限定。予約なし利用不可。少年用くじら運動公園や有料昭和公園の料金とは別で、誰でも予約できるとは案内しません。',
                        [('一般用サッカー場・市の利用要件を満たす利用者', 0, 'サッカー場1面・2時間')]))
    rows = []
    for room, prices in [('第一体育室全面', [6000, 6500, 7700, 9700, 25000]),
                          ('第一体育室半面', [3000, 3250, 3850, 4850, 12500])]:
        rows += [(room + ' / ' + slot, amount, room + '・' + duration)
                 for (slot, duration), amount in zip([('9～12時', '3時間'), ('12～15時', '3時間'),
                                                       ('15～18時', '3時間'), ('18～22時', '4時間'),
                                                       ('9～22時', '全日13時間')], prices)]
    result.append(entry(AKISHIMA[2], AKISHIMA_GYM,
                        '第一体育室の通常団体貸切。夜間4時間・日中3時間・全日13時間を分離。バスケット用でない第二体育室や個人入場料金は混ぜません。市外団体も所定の登録で利用対象ですがWeb予約システムは市内団体専用。営利目的不可。備品・駐車料別。', rows))
    return result


def policy(ident, source, summary):
    return {'id': ident, 'status': 'conditional', 'summary': summary,
            'source_url': source, 'checked_at': CHECKED}


def reviewed_policies():
    result = [policy(ident, NISHI_GUIDE,
                     '利用7日前までの取消は全額還付。1週間前を切って予約したものに限り、4日前の取消は半額還付の例外。一般の直前取消が全て半額になるわけではありません。領収書等を持参して窓口で還付（オンライン決済も現金）。屋外の天候・グラウンド不良による使用可否は利用60分前に施設判断し、不使用時は所定の還付手続きが必要です。') for ident in NISHI]
    for ident, page in [(CHOFU[0], 'p026091.html'), (CHOFU[1], 'p026080.html'), (CHOFU[2], 'p026086.html')]:
        result.append(policy(ident, CHOFU_BASE + page,
                             '前日までシステム取消可能。当日開始前に現地へ連絡して取消すると1か月間、開始後・無連絡は3か月間の新規予約停止。天候の使用可否も開始前までに現地へ確認。使用時間の半分に達する前に降雨で使用不能となる場合はペナルティ対象外ですが連絡は必要。ペナルティ免除を支払済み料金の自動返金とは扱いません。'))
    result.append(policy(CHOFU[3], CHOFU_BASE + 'p026077.html',
                         '前日までシステム取消可能。当日開始前連絡の取消は1か月間、開始後・無連絡は3か月間の新規予約停止。現地へ事前連絡が必要。複合施設ページの屋外降雨免除を屋内体育館へ自動適用せず、料金還付の個別条件は未確認です。'))
    result.append(policy(HINO[0], HINO_ARENA + 'guide',
                         '3日前まで予約システムで取消（付帯設備を先に取消）。2日前以降は体育館へ直接連絡。無断取消は利用停止等の対象。運営者案内では、前払いした利用料金は当日の利用の有無にかかわらず返還不可。屋内体育館に雨天免除は案内しません。'))
    result += [policy(ident, HINO_GROUNDS,
                      '運営者の共通案内では、事前納付した利用料金は当日の使用の有無にかかわらず返還不可。取消の具体的期限・ペナルティや悪天候時の例外条件までは同ページで確認できていないため、無料取消・自動返金とは案内しません。無料グラウンドには存在しない利用料金を請求しません。') for ident in [HINO[1], HINO[2], HINO[5]]]
    result.append(policy(KUNI[1], KUNI_FIELD,
                         '自己都合は利用5日前まで全額還付。雨天不使用は利用日を含め14日以内の申請で全額還付。利用者カードと利用承認書兼領収書を持参し、総合体育館で9～20時に手続き。野球場の公式案内も同条件。予約の取消操作だけで返金手続きが完了するとは案内しません。'))
    result.append(policy(AKISHIMA[0], MIHORI,
                         '条例第9条では既納の使用料は原則還付しないと規定。教育委員会が特別の理由と認める場合に全部または一部の還付が可能ですが、通常の自己都合取消の無料期限や料率は同条例に明記されていません。屋内施設への雨天免除は推測しません。'))
    result.append(policy(AKISHIMA[1], AKISHIMA_FIELD,
                         '雨等でグラウンドコンディション不良の場合は使用不可。予約なし利用は不可。通常の自己都合取消期限・ペナルティはこの公式ページでは未確認で、無料施設だから無断不使用でよいとは案内しません。'))
    result.append(policy(AKISHIMA[2], AKISHIMA_GYM,
                         '公式案内は、予約を確定（確認）した後のキャンセルを一切受け付けないと明記。取消無料の施設として案内しません。支払済み料金の災害等による例外・還付手続きは同ページでは未確認で、自己都合の返金を保証しません。'))
    return result


def main():
    fees, policies = reviewed_fees(), reviewed_policies()
    validate(fees)
    assert len(REVIEWED_IDS) == len(set(REVIEWED_IDS)) == len(fees) == 20
    assert len(policies) == 16
    catalog = {r['id']: r for r in get_catalog()['courts']}
    for row in fees:
        current = catalog[row['id']]
        if current.get('fee_checked_at') != CHECKED and has_price(current):
            raise ValueError('Refusing to replace priced venue: ' + row['id'])
    for name, additions in [('fee_plans.json', fees), ('cancellation_policies.json', policies)]:
        existing = {r['id']: r for r in json.loads((CATALOGS / name).read_text(encoding='utf-8'))}
        for row in additions:
            if row['id'] in existing and existing[row['id']] != row:
                raise ValueError('Refusing to replace existing review: ' + row['id'])
    for name, additions in [('fee_plans.json', fees), ('cancellation_policies.json', policies)]:
        append_reviews(CATALOGS / name, additions)
    print(json.dumps({'reviewed': 20, 'prices_added': len(fees), 'policies_added': len(policies)}))


if __name__ == '__main__':
    main()
