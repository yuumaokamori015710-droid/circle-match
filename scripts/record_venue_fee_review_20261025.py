"""Append verified tariffs without changing venue identities or earlier reviews."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'outputs'))
from venues.fees import validate
from venues.sports_catalog import get_catalog, has_price
from record_venue_fee_review_20261018 import append_reviews, entry as old_entry

CHECKED = '2026-10-25'
CATALOGS = ROOT / 'outputs/venues/catalogs'
MITAKA = ['tokyo-venue-f403faf4f42f', 'tokyo-venue-8e6c0f81a52c']
HACHIOJI = ['tokyo-venue-5b81852866ce', 'tokyo-venue-c282bded258a',
            'tokyo-gym-bc35a0a1e3c2', 'tokyo-gym-132a18a63ed5']
HIKARI = 'tokyo-venue-a2d6191898f8'
FUCHU = ['tokyo-venue-205d87234dd3', 'tokyo-gym-aa77f48e78d0', 'tokyo-gym-bd292e78d64f']
HINODE = ['tokyo-venue-d0be017dbb50', 'tokyo-venue-455b065cd3a8']
HIGASHI = ['tokyo-venue-9b83c8d54781', 'tokyo-venue-f03ca8d7146e',
           'tokyo-venue-f8ec50340ea7', 'tokyo-gym-9387fcd334e9']
OME = ['tokyo-venue-1a933984b689', 'tokyo-gym-3fc84a0cf785']
FUSSA = ['tokyo-gym-efd5e350238b', 'tokyo-gym-e6782f27b40b']
TOSHIMA = ['tokyo-venue-71237581c393', 'tokyo-venue-2e14b39dc02c']
REVIEWED_IDS = MITAKA + HACHIOJI + [HIKARI] + FUCHU + HINODE + HIGASHI + OME + FUSSA + TOSHIMA
HOLDS = MITAKA + HACHIOJI[:2] + FUCHU[:2]
HACHI_GUIDE = 'https://www.city.hachioji.tokyo.jp/shisetsu/104/p005417.html'
HIGASHI_BASE = 'https://www.higashiyamato-taiikukan.com/_files/ugd/'
SAKURA = HIGASHI_BASE + 'b5659a_5d9395de9937446eb7d46894b621a412.pdf'
KIYOHARA = HIGASHI_BASE + 'b5659a_8777533f47564dc59e0f9aff5c6b1d62.pdf'
HIGASHI_GYM = HIGASHI_BASE + '21c974_2146814578aa4dd183435800952630c8.pdf'


def entry(ident, source, note, rows):
    return dict(old_entry(ident, source, note, rows), checked_at=CHECKED)


def reviewed_fees():
    result = []
    for ident, source, rooms, note in [
        (HACHIOJI[2], 'https://www.city.hachioji.tokyo.jp/shisetsu/104/p025060.html',
         [('主競技場全面', 9000, 10500), ('主競技場半面', 4500, 5200),
          ('分館競技場全面', 4200, 4800), ('分館競技場半面', 2100, 2400)],
         '主競技場B面の床の浮き上がりに注意。主競技場は2026年12月14日～2027年1月15日、第三競技場は2026年12月14～28日休止予定。'),
        (HACHIOJI[3], 'https://information.konamisportsclub.jp/trust/kounohara/pricing/',
         [('第1体育室全面', 3600, 4200), ('第1体育室半面', 1800, 2100),
          ('第2体育室全面', 1600, 1700), ('第3体育室全面', 1000, 1200)], ''),
    ]:
        rows = []
        for room, daytime, night in rooms:
            rows += [(room + ' / 午前・午後A・午後B', daytime, room + '・2時間50分'),
                     (room + ' / 夜間18～21時', night, room + '・3時間')]
        result.append(entry(ident, source,
                            '通常スポーツ貸切の現行料金。午前9～11時50分・午後12～14時50分・15～17時50分と夜間18～21時は別単位。2027年4月改定予定の将来料金は採用しません。個人・プール・附属設備・延長・入場料徴収の特殊料金は範囲外。事前登録と各室の対応種目確認が必要。' + note, rows))
    result.append(entry(HIKARI, 'https://www.city.kokubunji.tokyo.jp/shisetsu/sport/hikari/1004200.html',
                        '利用可能な第二体育室（軽体操・軽スポーツ）の貸切のみ。第一体育室は天井の耐震性不足で停止中のため、バスケ・バレーのコート料金や第一体育室の個人開放料金は追加しません。第二体育室2時間30分は市民1,000円、市外団体2倍2,000円。原則10人以上の事前団体登録。料金確認はバスケ等が第二体育室で可能という意味ではありません。',
                        [('第二体育室 / 市民', 1000, '第二体育室・2時間30分'),
                         ('第二体育室 / 市外団体', 2000, '第二体育室・2時間30分')]))
    rows = []
    for room, inside, outside in [('体育室全面', [3000, 2500, 4000], [4500, 3700, 6000]),
                                  ('体育室半面', [1500, 1200, 2000], [2200, 1800, 3000])]:
        for index, (slot, duration) in enumerate([('午前9～12時', '3時間'),
                                                 ('午後13～15時30分・15時45分～18時15分', '2時間30分'),
                                                 ('夜間18時30分～21時30分', '3時間')]):
            rows += [(room + ' / ' + label + ' / ' + slot, amounts[index], room + '・' + duration)
                     for label, amounts in [('市内', inside), ('市外', outside)]]
    result.append(entry(FUCHU[2], 'https://www.city.fuchu.tokyo.jp/shisetu/supotu/taikukan/syougaigakusyuu.html',
                        '市公式料金表を指定管理者の現行案内とも照合した体育室の通常団体貸切。過半数が市内在住在勤在学等かつ5名以上など登録条件あり。面積・2時間30分・3時間を分離。市外料金は掲載額3,700円・2,200円等を使い単純な1.5倍にしません。個人入場・プール・会議室は別です。', rows))
    for ident, page, room, values in [
        (HINODE[0], '0154', '谷戸沢グランド全面', [500, 1000, 2000]),
        (HINODE[1], '0155', '谷戸沢サッカー場全面', [3000, 6000, 12000]),
    ]:
        result.append(entry(ident, 'https://www.town.hinode.tokyo.jp/000000' + page + '.html',
                            '東京都内団体限定、大会・試合のみで練習・練習試合は不可。掲載単価は1時間。中学生以下・一般・入場料徴収の区分を明記します。7～17時、準備片付け込み、文化スポーツ課窓口への事前申請が必要。' +
                            ('天然芝サッカー場の貸出は5月～10月末のみ。' if ident == HINODE[1] else 'ナイター使用不可。'),
                            [(label, amount, room + '・1時間') for label, amount in
                             zip(['都内団体・中学生以下', '都内団体・一般', '入場料徴収'], values)]))
    for ident in HIGASHI[:2]:
        rows = []
        for room, adult, child in [('桜が丘広場全面', 1800, 450), ('桜が丘広場A面', 1000, 250), ('桜が丘広場B面', 800, 200)]:
            for duration, slot in [('2時間', '6～16時の各2時間枠'), ('3時間', '3～10月の16～19時')]:
                rows += [(room + ' / ' + label + ' / ' + slot, amount, room + '・' + duration)
                         for label, amount in [('一般', adult), ('中学生以下団体', child)]]
        result.append(entry(ident, SAKURA,
                            'S&Dフィールド桜が丘（桜が丘市民広場）の指定管理者現行案内。既存の別名2登録を保全し、施設数を2倍には数えません。全面・A・B面及び通常2時間と3～10月16～19時の3時間枠を分離、各1単位の掲載額を採用。10名以上で団体登録、曜日種目制限あり。市外団体の別倍率は案内にないため推測しません。', rows))
    rows = []
    for duration, slot in [('2時間', '8～16時の各2時間枠'), ('3時間', '3～10月の16～19時')]:
        rows += [(label + ' / ' + slot, amount, '清原運動広場全面・' + duration)
                 for label, amount in [('一般', 7800), ('中学生以下', 3900)]]
    result.append(entry(HIGASHI[2], KIYOHARA,
                        '人工芝グラウンド全面の団体貸切。指定管理者の1単位7,800円、中学生以下3,900円を採用。通常2時間と3～10月16～19時の3時間枠を分離。10人以上の団体登録が必要、市外倍率は推測しません。営利・個人利用不可、条件付き種目あり。', rows))
    result.append(entry(HIGASHI[3], HIGASHI_GYM,
                        '東大和S&D体育館の指定管理者が現在リンクする団体案内。各室2時間30分の通常貸切で、部屋・全面半面を分離。第1体育室がバスケ・バレー等、第2は武道・体操、第3は卓球・ダンス等。10人以上の団体登録が必要。市外倍率を推測せず、入場料徴収3倍・個人利用料とは混ぜません。',
                        [(room + ' / 通常貸切', amount, room + '・2時間30分') for room, amount in
                         [('第1体育室全面', 9600), ('第1体育室半面', 4800), ('第2体育室全面', 4600),
                          ('第2体育室半面', 2300), ('第3体育室全面', 2600), ('第3体育室半面', 1300)]]))
    result.append(entry(OME[0], 'https://www.omesports.net/facility/higashihara',
                        '指定管理者の球技場2時間基本料。全面2,400円、半面は規定額の半額1,200円。照明は別途全面1時間3,000円、半面は半額で、2時間基本料と混ぜません。ソフトボール・サッカー等（野球は除く）。利用者登録が必要。',
                        [('球技場全面 / 照明別', 2400, '球技場全面・2時間'),
                         ('球技場半面 / 照明別', 1200, '球技場半面・2時間')]))
    rows = []
    for room, morning, later in [('第1スポーツホール全面', 9000, 12000),
                                  ('第1スポーツホール半面', 4500, 6000),
                                  ('第1スポーツホール4分の1面', 2250, 3000),
                                  ('第2スポーツホール全面', 1500, 2000),
                                  ('第2スポーツホール半面', 750, 1000)]:
        rows += [(room + ' / 午前9～12時', morning, room + '・3時間'),
                 (room + ' / 午後13～17時・夜間18～22時', later, room + '・4時間')]
    result.append(entry(OME[1], 'https://www.omesports.net/facility/gymnasium',
                        '指定管理者の団体貸切料金。第1スポーツホールと武道用の第2ホールを分離、午前3時間と午後・夜間4時間を分離。個人の夜間21時30分終了と団体22時終了を混同しません。入場料徴収3倍・個人料金・駐車料は範囲外。団体登録・使用種目確認が必要。', rows))
    result.append(entry(FUSSA[0], 'https://fussa-kumagawa.com/gym-1/',
                        '第1体育室の個人利用のみ、1人1回90分。大人150円・3歳以上中学生以下70円。通常貸切なし（大会・教室利用等を除く）なので会場貸切価格ではありません。バスケ・バレーは19時まで、バレーは支柱ネットなし・トスのみ。用具料等は別途。',
                        [('個人・大人', 150, '第1体育室・1人90分'), ('個人・3歳以上中学生以下', 70, '第1体育室・1人90分')]))
    result.append(entry(FUSSA[1], 'https://fussa-fussa.com/facility/?facility=facility_arena-2',
                        '指定管理者の第2体育室の貸切1時間、市内大人800円・市内小人400円・市外2,400円。市内は利用者全員が在住在勤在学、小人は3歳～中学生。第1体育室は通常貸切なし。第2体育室は卓球・ダンス等向けでバスケの貸切を保証しません。入場料徴収は市内6倍、営利はその5倍で範囲外。個人利用90分70～150円とは混ぜません。',
                        [('第2体育室貸切・市内大人', 800, '第2体育室・1時間'),
                         ('第2体育室貸切・市内小人', 400, '第2体育室・1時間'),
                         ('第2体育室貸切・市外', 2400, '第2体育室・1時間')]))
    result.append(entry(TOSHIMA[0], 'https://www.city.toshima.lg.jp/501/bunka/sports/sports/003418/003496.html',
                        '団体登録が必要な武道場（白木床・畳）の団体貸切、各1コマ3時間3,600円。プール・トレーニング400円/人や教室参加料とは別。市の現行施設案内にバスケ・バレーのコート貸切はなく、この金額は球技コートの料金ではありません。',
                        [('武道場（白木床）団体貸切', 3600, '武道場（白木床）・3時間'),
                         ('武道場（畳）団体貸切', 3600, '武道場（畳）・3時間')]))
    result.append(entry(TOSHIMA[1], 'https://www.city.toshima.lg.jp/501/bunka/sports/sports/003418/003476.html',
                        '市公式の庭球場1面の貸切単価1時間1,000円。実際の使用時間は2時間又は3時間単位で、常時1時間だけ予約できる意味ではありません。団体・個人登録条件あり。無料多目的広場はゲートボール・子どもの遊び場でありフットサル貸切の無料料金ではありません。',
                        [('庭球場1面・貸切単価', 1000, '庭球場1面・1時間（単価）')]))
    return result


def policy(ident, source, summary):
    return {'id': ident, 'status': 'conditional', 'summary': summary,
            'source_url': source, 'checked_at': CHECKED}


def reviewed_policies():
    result = [policy(MITAKA[1], 'https://www.city.mitaka.lg.jp/c_service/079/079234.html',
                     '2026年10月1日以降利用分は利用日の7日前まで予約システムから取消可能。それ以降はごみ対策課へ連絡。具体的な料金・取消手数料・還付率は同案内で確認できないため推測しません。')]
    for ident in HACHIOJI:
        result.append(policy(ident, HACHI_GUIDE,
                             '利用しないと分かった時点で取消。前日までは予約システム、当日は施設へ直接電話。' +
                             ('屋外施設は当日・無断取消で翌々月1日から3か月間抽選・空き予約不可。金銭手数料ではなく申込制限です。天候による免除条件・還付率はこの案内だけでは確認できません。' if ident in HACHIOJI[:2] else
                              '富士森・甲の原体育館は支払い後の払い戻し不可。屋外施設の当日取消ペナルティを屋内へ適用するとは記載されていません。')))
    result.append(policy(FUCHU[0], 'https://www1.g-reiki.net/city.fuchu.tokyo/reiki_honbun/g130RG00000266.html',
                         '体育施設条例第10条では納入済み使用料は原則不還付。本人に責任のない使用不可、市又は管理上の承認取消、その他市長が相当と認めるときは全部又は一部返還可能。一般サークルによるグラウンド使用は不可の施設です。具体的期限・返還率はこの条例から推測しません。'))
    result.append(policy(FUCHU[1], 'https://www.city.fuchu.tokyo.jp/shisetu/supotu/yoyaku/torikesi.html',
                         '予約取消しは所定の窓口手続き。利用日の1か月前まで100%、10日前まで50%、9日前以降0%還付。施設利用券控・取消申込書が必要で代理人は委任状も必要。100円未満の端数は50円単位に切捨て。現在の体育室貸切受付停止・改修休館予定は別途施設案内に従ってください。'))
    for ident, page in zip(HINODE, ['0154', '0155']):
        result.append(policy(ident, 'https://www.town.hinode.tokyo.jp/000000' + page + '.html',
                             '施設予約後の自己都合によるキャンセルは受け付けない（雨天等は可）。自己判断で無断中止せず文化スポーツ課へ確認してください。具体的返還率・連絡期限・雨天判断基準は現行施設ページでは確認できません。'))
    for ident, source in zip(HIGASHI, [SAKURA, SAKURA, KIYOHARA, HIGASHI_GYM]):
        text = '未払い予約はマイページから削除。納付済みは利用7日前まで（休館日なら前日）窓口申請により利用者IDへ還付し、次回以降窓口で料金に充当可能。期限後も取消は可能だが原則還付・充当不可、不可抗力と判断される場合は例外。IDの充当額はマイページには表示されません。自動的な現金返金とは表現しません。'
        if ident in HIGASHI[:2]:
            text += '桜が丘の雨・暑さ等の状態不良は当日開始30分前以降に広場へ連絡、管理人不在時は体育館へ連絡。'
        result.append(policy(ident, source, text))
    return result


def main():
    fees, policies = reviewed_fees(), reviewed_policies()
    validate(fees)
    assert len(REVIEWED_IDS) == len(set(REVIEWED_IDS)) == 22
    assert len(fees) == 16 and len(policies) == 13 and len(HOLDS) == 6
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
    print(json.dumps({'facilities_reviewed': 21, 'records_reviewed': 22, 'prices_added': 16,
                      'policies_added': 13, 'holds': 6}))


if __name__ == '__main__':
    main()
