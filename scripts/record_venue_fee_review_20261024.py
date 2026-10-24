"""Append same-unit official tariffs; preserve source catalogs and prior reviews."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'outputs'))
from venues.fees import validate
from venues.sports_catalog import get_catalog, has_price
from record_venue_fee_review_20261018 import append_reviews, entry as old_entry

CHECKED = '2026-10-24'
CATALOGS = ROOT / 'outputs/venues/catalogs'
MACHIDA = ['tokyo-venue-eae5b1bb5ae8', 'tokyo-venue-1942d37f9398',
           'tokyo-venue-48447d8b7193', 'tokyo-venue-3c78bf0097ef',
           'tokyo-venue-18bb0f19de19', 'tokyo-venue-3108b074cea4',
           'tokyo-venue-84e92450decc', 'tokyo-venue-725e2cb0cf1f']
AKIRUNO = ['tokyo-venue-d75459afac94', 'tokyo-venue-2b0bbd7157ff',
           'tokyo-gym-3b5b5e39f0fa', 'tokyo-gym-21b7d81d6f9f']
MURAYAMA = ['tokyo-venue-055c51c0ec00', 'tokyo-venue-3b28f5cc8116', 'tokyo-venue-29421e4cf38d']
HAMURA = ['tokyo-venue-4bf7c3cb0c15', 'tokyo-gym-2ecb7ba4e163']
KODAIRA = 'tokyo-venue-783dec2ff5f5'
KOGANEI = 'tokyo-gym-a231878afdcf'
MIZUHO = 'tokyo-venue-3ad9e1c48a3f'
REVIEWED_IDS = MACHIDA + AKIRUNO + MURAYAMA + HAMURA + [KODAIRA, KOGANEI, MIZUHO]
HOLDS = [AKIRUNO[1], KOGANEI]
MACHIDA_BASE = 'https://www.city.machida.tokyo.jp/bunka/sport/sport/yakyujo/'
MACHIDA_GUIDE = 'https://www.city.machida.tokyo.jp/bunka/riyou/snet/snet01.files/guidobook20251009.pdf'
AKIRUNO_LAW = 'https://www.city.akiruno.tokyo.jp/reiki/reiki_int/reiki_honbun/g151RG00000222.html'
AKIRUNO_NEW = 'https://www.city.akiruno.tokyo.jp/cmsfiles/contents/0000019/19291/11.pdf'
MURA_PRICES = 'https://www.city.musashimurayama.lg.jp/_res/projects/default_project/_page_/001/001/847/r80609siyouryou.pdf'
MURA_GROUND = 'https://musashimurayama-gym.jp/sports-facilities/playground'
MURA_REFUND = 'https://musashimurayama-gym.jp/wp/wp-content/uploads/利用中止・返金手続き手順R1.9.1-1.pdf'
HAMURA_PRICES = 'https://www.city.hamura.tokyo.jp/prsite/0000002167.html'
HAMURA_GUIDE = 'https://www.city.hamura.tokyo.jp/prsite/0000002165.html'
HAMURA_CLOSURE = 'https://www.city.hamura.tokyo.jp/0000019660.html'
KODAIRA_GUIDE = 'https://sports-kodaira.jp/group'
MIZUHO_PAGE = 'https://www.town.mizuho.tokyo.jp/kyoikuiinkai/about/007/002/p010900.html'


def entry(ident, source, note, rows):
    return dict(old_entry(ident, source, note, rows), checked_at=CHECKED)


def pair(room, amount, duration, multiplier=2, labels=('市内通常', '市外通常')):
    return [(room + ' / ' + label, int(amount * factor), room + '・' + duration)
            for label, factor in zip(labels, [1, multiplier])]


def reviewed_fees():
    result = [entry(MACHIDA[0], 'https://www.onojikouen.com/riyouhouhou/',
                    '小野路GIONグラウンドの通常スポーツ貸切。全面・半面を分離し、併設野球場5,230円とは混ぜません。団体登録が必要。照明は全面1,460円・半面730円/30分が別途。入場料徴収・スポーツ以外の料金は範囲外で、通常料金の絶対的な最高額という意味ではありません。',
                    [('通常スポーツ・全面（照明別）', 6280, 'グラウンド全面・2時間'),
                     ('通常スポーツ・半面（照明別）', 3140, 'グラウンド半面・2時間')]),
              entry(MACHIDA[1], MACHIDA_BASE + 'sannnouduka.html',
                    '山王塚の有料団体貸切は2時間30分2,090円、9～3月の15時30分～17時のみ1時間30分1,250円。一般開放の無料料金と混ぜません。現行施設案内の用途は少年軟式野球・ソフトボールで、サッカー等の他用途は事前相談が必要です。団体登録・現金現地払い。',
                    [('通常貸切', 2090, 'グラウンド全面・2時間30分'),
                     ('9～3月の最終短縮枠', 1250, 'グラウンド全面・1時間30分')])]
    rows = []
    for room, amount in [('メインアリーナ全面', 9110), ('メインアリーナ3分の2面', 6070),
                         ('メインアリーナ3分の1面', 3030), ('サブアリーナ全面', 4190), ('サブアリーナ半面', 2090)]:
        rows.append((room + ' / 通常スポーツ専用利用', amount, room + '・3時間'))
    result.append(entry(MACHIDA[2], 'https://gion-machida.com/gymnasium/guide/',
                        '指定管理者が掲示する通常スポーツ専用利用の基本料、各3時間。個人310円・会議室・附属照明等と別。サブ半面はバスケットゴール1台のみ。営利目的は禁止と明記され、料金は商業大会開催の許可ではありません。市内団体は10人以上が在住在勤在学、うち5人以上が在住等の登録条件あり。2028年1月中旬～2030年5月末の休館予定は将来計画であり、現在の全館休止ではありません。', rows))
    for ident, page, room, amount, note in [
        (MACHIDA[3], 'tadao_sft', 'ソフトボール場全面', 2090, '公式の利用種目はソフトボール。サッカーの利用許可を意味しません。'),
        (MACHIDA[4], 'kiso_g', 'グラウンド全面', 2090, '現行案内の一般・少年軟式野球等の用途条件に従い、他用途の可否は施設確認が必要。'),
        (MACHIDA[5], 'aiharachuo_g', 'グラウンド全面', 2090, '夜間照明は30分1,460円が別途。'),
        (MACHIDA[6], 'midorigaoka', 'グラウンド全面', 2090, '現行案内の一般・少年軟式野球等の用途条件に従い、他用途の可否は施設確認が必要。'),
        (MACHIDA[7], 'serigaya', 'グラウンド全面', 1050, '現行施設案内にサッカー・フットサル等を明記。'),
    ]:
        result.append(entry(ident, MACHIDA_BASE + page + '.html',
                            '現行市公式施設案内と予約ガイドの通常団体貸切、各2時間。事前登録が必要。駐車料金やスポーツ以外の特殊料金は含めません。' + note,
                            [('通常団体貸切', amount, room + '・2時間')]))
    result.append(entry(AKIRUNO[0], 'https://www.city.akiruno.tokyo.jp/0000007671.html',
                        '2026年4月改定後の市民運動広場の野球場A面・B面、各1面2時間。市内800円・市外2,400円。総合グラウンドにある無料の運動広場とは別施設です。現行市案内は野球場として料金を掲載しており、サッカー等の使用許可は保証しません。市内在住在勤在学・団体登録等の条件を確認してください。',
                        pair('野球場1面', 800, '2時間', 3)))
    result.append(entry(AKIRUNO[2], AKIRUNO_NEW,
                        '横川観光ファインプラザ（五日市）の体育室団体貸切、2026年4月改定後の市公表額。体育室全面2時間の市内2,400円・市外7,200円。プール・武道場・個人120円は混ぜません。市内在住在勤在学等の条件あり。申請済み旧料金の遡及改定ではなく、現在の新規利用申請向けです。',
                        pair('体育室全面', 2400, '2時間', 3)))
    rows = []
    for room, amount in [('大体育室全面', 2400), ('大体育室半面', 1200),
                         ('大体育室4分の1面', 600), ('大体育室8分の1面', 300), ('小体育室全面', 1200)]:
        rows += pair(room, amount, '2時間', 3)
    result.append(entry(AKIRUNO[3], 'https://akigawa-gymnasium.com/gym/',
                        '2026年4月1日以降の新料金のみ。団体貸切2時間、全面・半面・分割面を分離。市の新料金と照合し、旧1,800円/全面は採用しません。市内在住在勤在学などの登録要件、使用人数の半数以上という団体区分条件は窓口確認が必要です。個人・幼児の無料利用を貸切料金と混ぜません。', rows))
    rows = []
    for room, amount in [('第一体育室全面', 9460), ('第一体育室半面', 4730), ('第一体育室3分の1面', 3080),
                         ('第二体育室', 1020), ('第三体育室', 1020)]:
        rows += pair(room, amount, '2時間30分')
    rows += pair('第一体育室全面', 47310, '全日12時間30分')
    result.append(entry(MURAYAMA[0], MURA_PRICES,
                        '市が現在リンクする令和8年6月版料金表と指定管理者の団体案内を照合。各2時間30分、市外は2倍。3分の1面3,080円と全日47,310円は掲載額を採用し、単純割算・5倍計算をしません。全日は9時～21時30分。団体登録が必要。', rows))
    for ident, room, amount, note in [
        (MURAYAMA[1], '第2運動場全面', 1080, '陸上競技・サッカー等向けの第2運動場で、第1・第3運動場と混ぜません。'),
        (MURAYAMA[2], '野山北公園運動場全面', 750, '指定管理者の用途案内はグラウンドゴルフなど。サッカー利用可の根拠とはしません。'),
    ]:
        result.append(entry(ident, MURA_PRICES,
                            '現在リンクされている市料金表の明記単価は1時間、市内・市外を分離。通常予約は2時間単位で、4・5・9・10月17～18時には1時間枠あり。指定管理者の2時間料金とも照合。団体登録が必要で、市民等が半数未満なら市外区分。1時間単価の表示は常時1時間だけ予約できる意味ではありません。' + note,
                            pair(room, amount, '1時間（単価）') + pair(room, amount * 2, '2時間')))
    result.append(entry(HAMURA[0], 'https://www.city.hamura.tokyo.jp/0000000768.html',
                        '宮の下運動公園のサッカー場全面、通常貸切2時間1,220円。市の公園有料施設案内の掲載額のみを確認し、隣接野球・ソフトボール610円や夜間3時間の料金を混ぜません。登録・予約が必要。市外加算を推測して付け加えていません。',
                        [('サッカー場・全面通常貸切', 1220, 'サッカー場1面・2時間')]))
    rows = []
    for room, values in [('第2ホール全面', [(3960, 5940), (4290, 6430), (6930, 10390)]),
                         ('第2ホール半面', [(1980, 2970), (2200, 3300), (3410, 5110)])]:
        for (slot, duration), amounts in zip([('午前9～12時', '3時間'), ('午後12～15時・15～18時', '3時間'), ('夜間18～22時', '4時間')], values):
            rows += [(room + ' / ' + label + ' / ' + slot, amount, room + '・' + duration)
                     for label, amount in zip(['市民等', '市民等以外'], amounts)]
    result.append(entry(HAMURA[1], HAMURA_PRICES,
                        '第1ホールは利用停止中のため旧料金を追加しません。第2ホールは2026年5月26日に利用再開と同施設の最新告知で確認。第2ホールの全面・半面、3時間・夜間4時間を分離。市外の10円未満切捨て後6,430円・10,390円等は掲載額を採用。市民等の団体構成条件があり、入場料等を徴収する場合は原則3倍で別扱いです。', rows))
    result.append(entry(KODAIRA, KODAIRA_GUIDE,
                        '第1体育室は公的行事のみ貸出可なので、一般サークル向け価格には収録しません。通常の第2体育室は各2時間30分5,000円、市外1.5倍7,500円。10人以上の団体登録が必要で、在住在勤在学が5割以上なら市内。個人・プール・会議室料金は混ぜません。',
                        pair('第2体育室全面', 5000, '2時間30分', 1.5)))
    rows = pair('第1体育室', 1000, '2時間30分', 3, ('町内在住在勤在学', 'その他'))
    rows += pair('第2体育室', 1000, '2時間30分', 3, ('町内在住在勤在学', 'その他'))
    result.append(entry(MIZUHO, MIZUHO_PAGE,
                        '瑞穂町（東京都）の中央体育館で、瑞穂市の体育館ではありません。体育室1コマ2時間30分、町内在住在勤在学1,000円・その他3,000円。第1・第2体育室を分離。事前登録と使用者全員の町内要件等の確認が必要。フットサルは原則禁止。入場料等徴収時の特殊料金・会議室は範囲外。', rows))
    return result


def policy(ident, source, summary):
    return {'id': ident, 'status': 'conditional', 'summary': summary,
            'source_url': source, 'checked_at': CHECKED}


def reviewed_policies():
    common = '本人が前日までに取消手続き。当日やむを得ない場合も利用開始前まで。利用日の3週間前の日以降の取消は1pt、無断取消は2ptで翌々月の申込に制限（予約後60分未満の取消は例外）。金銭の取消手数料・還付率とは別の予約ペナルティです。'
    result = [policy(i, MACHIDA_GUIDE, common + (
        '悪天候等の使用不可は開始30分前に施設が判断し、この場合は利用者による取消手続き不要・ペナルティ対象外。自己判断で中止としないでください。'
        if i != MACHIDA[2] else '屋外施設の雨天による取消免除を屋内体育館へ自動適用しません。')) for i in MACHIDA]
    result += [policy(i, AKIRUNO_LAW,
                      '条例第12条・指定管理施設への準用規定では納付後の還付は原則不可。本人に責任のない使用不可、施設側の取消・中止、又は4日前までの取消で相当な理由が認められる場合は全部又は一部を還付可能。4日前なら無条件で全額返金という規定ではなく、具体的料率や申請手続きは施設確認が必要。')
               for i in [AKIRUNO[0], AKIRUNO[2], AKIRUNO[3]]]
    for ident in MURAYAMA:
        summary = '納付後の自己都合中止は利用開始前までに窓口へ届け出（電話不可・FAXは送信後電話連絡が必要）。未納予約は3日以上前なら予約システムで取消、それ以降は窓口。返還申請書と利用許可書兼領収書が必要。開始後の自己都合取消、領収書未提出、返還申出から1か月経過は返還対象外。'
        if ident != MURAYAMA[0]:
            summary += '天候・施設不良は前日又は当日開始1時間以内に中止連絡（電話・FAX可）。2026年7月22日告知では熱中症予防の取消も同期間内の電話連絡で全額返金、無断中止は対象外。'
        result.append(policy(ident, MURA_REFUND, summary))
    result.append(policy(HAMURA[1], HAMURA_GUIDE,
                         '使用20日前まで全額、10日前まで75%、5日前まで50%を還付し、4日前以降は返還なし。使用承認書・領収書が必要で、口座振込での還付は申請者の口座情報も必要。別日への振替か還付の手続きで、自動返金ではありません。'))
    result.append(policy(KODAIRA, KODAIRA_GUIDE,
                         '申請・支払後の取消は利用日の14日前までなら還付。代表者の印鑑が必要。未申請のまま放置するとペナルティ対象となり、以後の予約ができない場合があります。具体的な14日前以降の還付率や屋内の雨天免除は推測しません。'))
    result.append(policy(MIZUHO, MIZUHO_PAGE,
                         '利用者都合の日時・場所変更は不可、自己都合キャンセルによる返金なし。降雨等で使用不可となった場合は役場開庁日5日以内に教育委員会へ申し出て同施設の振替対応、原則返金なし。屋内体育室が雨だけで使用不可になるという意味ではありません。'))
    return result


def main():
    fees, policies = reviewed_fees(), reviewed_policies()
    validate(fees)
    assert len(REVIEWED_IDS) == len(set(REVIEWED_IDS)) == 20
    assert len(fees) == 18 and len(policies) == 17
    rows = {r['id']: r for r in get_catalog()['courts']}
    assert all(i in rows for i in REVIEWED_IDS)
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
    print(json.dumps({'reviewed': 20, 'prices_added': 18, 'policies_added': 17, 'holds': 2}))


if __name__ == '__main__':
    main()
