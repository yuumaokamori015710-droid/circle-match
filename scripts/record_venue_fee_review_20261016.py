"""Apply the official tariff snapshot reviewed in the dated research note."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'outputs'))
from venues.fees import validate
from venues.sports_catalog import get_catalog

CHECKED = '2026-10-16'
CATALOGS = ROOT / 'outputs/venues/catalogs'


def entry(ident, source, conditions, rows, note=''):
    return {'id': ident, 'checked_at': CHECKED, 'fee_note': note or conditions,
            'fee_options': [{'label': label, 'amount': amount, 'unit': unit,
                             'conditions': conditions, 'source_url': source}
                            for label, amount, unit in rows]}


def reviewed_fees():
    result = []
    periods = [('午前9:00～12:00', '3時間'), ('午後1 12:30～15:00', '2時間30分'),
               ('午後2 15:30～18:00', '2時間30分'), ('夜間18:30～21:00', '2時間30分')]
    # The morning slot is longer than the other slots; whole/half areas stay separate.
    for ident, slug, amounts in [
        ('tokyo-venue-9b93d81ca10e', 'iko', (2700, 3500, 3500, 4100)),
        ('tokyo-venue-8a96774363e5', 'touwa', (2700, 3500, 3500, 4100)),
        ('tokyo-venue-84dbc0345777', 'shisetsu/kouhoku', (2700, 3500, 3500, 4100)),
        ('tokyo-gym-bc16a86706e5', 'chuouhonchou', (2700, 3500, 3500, 4100)),
        ('tokyo-gym-dc5097408efb', 'sano', (2200, 2700, 2700, 3300)),
        ('tokyo-gym-6a6bb1ea794a', 'umeda2', (2700, 3500, 3500, 4100)),
        ('tokyo-gym-145a2b1e2fa3', 'okimoto', (2200, 2700, 2700, 3300)),
        ('tokyo-gym-9df21a804b72', 'shikahama', (2700, 3500, 3500, 4100)),
    ]:
        rows = [(label + ' / ' + area, amount // divisor, '体育館' + area + '・' + duration)
                for area, divisor in [('全面', 1), ('半面', 2)]
                for (label, duration), amount in zip(periods, amounts)]
        result.append(entry(ident, 'https://www.city.adachi.tokyo.jp/sg-shien/' + slug + '.html',
                            '体育館の通常団体貸切料金。学習室・レクホール・個人公開の料金ではありません。Web予約は事前登録が必要。減免・付帯設備は別途。', rows))

    rows = [(label + ' / ' + area, amount, '体育館' + area + '・' + duration)
            for area, amounts in [('全面', (2700, 3500, 3500, 4100, 13800)),
                                  ('半面', (1350, 1750, 1750, 2050, 6900))]
            for (label, duration), amount in zip(periods + [('全日9:00～21:00', '全日12時間')], amounts)]
    result.append(entry('tokyo-gym-573105da20a9', 'https://www.city.adachi.tokyo.jp/sports/shisetsu/swim.html',
                        '体育館の通常団体貸切。小体育室・プール・個人公開料金は含みません。Web予約は事前登録が必要。減免・付帯設備は別途。', rows))

    rows = [(room + area + ' / ' + label, amount, room + area + '・' + duration)
            for room, area, amounts in [
                ('大体育室', '全面', (6600, 7700, 7700, 9200, 31200)),
                ('大体育室', '半面', (3300, 3850, 3850, 4600, 15600)),
                ('大体育室', '4分の1面', (1650, 1920, 1920, 2300, 7790)),
                ('小体育室', '全面', (2200, 2700, 2700, 3300, 10900)),
            ]
            for (label, duration), amount in zip(periods + [('全日9:00～21:00', '全日12時間')], amounts)]
    result.append(entry('tokyo-gym-46bb4a7e287c', 'https://www.city.adachi.tokyo.jp/sports/shisetsu/sousupo-in.html',
                        '大・小体育室の通常団体貸切。面積区分と利用時間ごとに表示。Web予約は事前登録が必要。減免・付帯設備・個人公開料金は別途。', rows))

    conditions = '通常の体育館団体貸切。原則けやきネット登録団体（5名以上・半数以上が区内在住在勤在学などの要件）が対象。個人利用・付帯設備・減免を除きます。'
    for ident, slug, periods_and_amounts in [
        ('tokyo-gym-0cb647825898', 'okura-gym', [
            ('9:00～12:00', '3時間', (7830, 15660, 9300, 18600)),
            ('12:00～15:00', '3時間', (7830, 15660, 9300, 18600)),
            ('15:00～17:00', '2時間', (5220, 10440, 6200, 12400)),
            ('17:00～19:00', '2時間', (5220, 10440, 6200, 12400)),
            ('19:00～22:00', '3時間', (7830, 15660, 9300, 18600)),
            ('全日9:00～22:00', '全日13時間', (29740, 59480, 35620, 71250)),
        ]),
        ('tokyo-gym-4eb031276843', 'sougou-gym', [
            ('9:00～12:00', '3時間', (8580, 17160, 10260, 20550)),
            ('12:00～15:00', '3時間', (8580, 17160, 10260, 20550)),
            ('15:00～18:00', '3時間', (8580, 17160, 10260, 20550)),
            ('18:00～21:00', '3時間', (8580, 17160, 10260, 20550)),
            ('全日9:00～21:00', '全日12時間', (29490, 58990, 35380, 70760)),
        ]),
    ]:
        rows = [(period + ' / ' + day + ' / ' + area, amount, '体育館' + area + '・' + duration)
                for period, duration, amounts in periods_and_amounts
                for (day, area), amount in zip([('平日', '半面'), ('平日', '全面'), ('土日祝', '半面'), ('土日祝', '全面')], amounts)]
        result.append(entry(ident, 'https://www.se-sports.or.jp/facilityinfo/' + slug + '/', conditions, rows))

    rows = [(label + ' / ' + day, amount, '3階体育館全面・' + duration)
            for label, duration, amounts in [
                ('9:00～12:00', '3時間', (7640, 9170)),
                ('12:00～15:00', '3時間', (8550, 10260)),
                ('16:00～18:30', '2時間30分', (8550, 10260)),
                ('18:30～21:00', '2時間30分', (9900, 11880)),
                ('全日9:00～21:00', '全日枠', (30200, 36240)),
            ] for day, amount in zip(('平日・土曜', '日祝'), amounts)]
    result.append(entry('tokyo-gym-e9661f9d4b0f', 'https://www.se-sports.or.jp/facilityinfo/kibougaoka-gym-3rd-floor/',
                        conditions + '対象は3階体育館。15:00～16:00は個人利用時間で団体利用不可。', rows))

    rows = [(label, amount, '体育館全面・' + duration) for label, amount, duration in [
        ('第1・3・5日曜・祝日9:00～13:00', 9140, '4時間'),
        ('第1・3・5日曜・祝日13:00～17:00', 9960, '4時間'),
        ('第1・3・5日曜・祝日17:00～21:00', 13890, '4時間'),
        ('第1・3・5日曜・祝日 全日9:00～21:00', 25490, '全日12時間'),
        ('第1・2・3・5水曜16:00～18:30', 6200, '2時間30分'),
        ('第1・2・3・5水曜18:30～21:00', 7180, '2時間30分'),
    ]]
    result.append(entry('tokyo-gym-815e7ebed1c0', 'https://www.se-sports.or.jp/facilityinfo/oyamadai-gym/',
                        conditions + '2026年12月～2027年2月中旬は改修休館予定（https://www.se-sports.or.jp/news/22467/）。予約可能日は公式案内で確認。', rows))

    rows = [(label, amount, '屋内球技場全面・' + duration + '（税込）')
            for label, amount, duration in [
                ('午前9:00～13:00', 37800, '4時間'), ('午後13:00～17:00', 45100, '4時間'),
                ('夜間17:00～21:00', 65000, '4時間'), ('午前・午後9:00～17:00', 77500, '8時間'),
                ('午後・夜間13:00～21:00', 102800, '8時間'), ('全日9:00～21:00', 129900, '全日12時間'),
            ]]
    result.append(entry('tokyo-gym-f4ecc307371e', 'https://www.tef.or.jp/kopgp/ballgame-indoor/',
                        '屋内球技場のアマチュアスポーツ・入場料等なし・スタンド未使用の通常貸切料金。団体登録が必要。スタンド使用・入場料等あり・その他スポーツ等・付属設備は別料金で、表示幅には含みません。', rows))

    source = 'https://yotsuya-sports-square.jp/yotsuyawp/wp-content/themes/twentytwentyone-child/pdf/price.pdf'
    rows = [(label + ' / ' + group, amount // divisor, '多目的ホール全面・' + duration)
            for group, divisor in [('区外団体', 1), ('区民団体', 2)]
            for label, amount, duration in [
                ('9:00～12:00', 6300, '3時間'), ('12:20～15:20', 8400, '3時間'),
                ('15:40～18:40', 8400, '3時間'), ('19:00～22:00', 10500, '3時間'),
                ('全日9:00～22:00', 33600, '全日13時間'),
            ]]
    result.append(entry('tokyo-gym-125683b2ea6c', source,
                        '事前の団体登録が必要。区民団体は10名以上・過半数が新宿区在住・代表者も区内在住などの登録条件があり半額。会議室・音楽室・個人利用・付帯設備は含みません。', rows))

    rows = [(label + ' / ' + day + ' / ' + area, amount, '大体育室' + area + '・' + duration)
            for label, duration, amounts in [
                ('9:00～12:00', '3時間', (35200, 17600, 42000, 21000)),
                ('12:20～15:20', '3時間', (42000, 21000, 44000, 22000)),
                ('15:40～18:40', '3時間', (42000, 21000, 44000, 22000)),
                ('19:00～22:00', '3時間', (44000, 22000, 44000, 22000)),
                ('全日9:00～22:00', '全日13時間', (163200, 81600, 174000, 87000)),
            ] for (day, area), amount in zip([('平日', '全面'), ('平日', '半面'), ('土日祝', '全面'), ('土日祝', '半面')], amounts)]
    result.append(entry('tokyo-gym-5074f6b079ec', 'https://www.regasu-shinjuku.or.jp/regasu/wp-content/uploads/2018/07/shisetsu-price.pdf',
                        '現行運営者の貸切案内（https://www.regasu-shinjuku.or.jp/?p=668）からリンクされる料金表。大体育室の通常団体貸切。区民・区外で料金の違いなし。子ども団体減額・個人公開・付帯設備を除きます。', rows))

    source = 'https://www.di-ksp.jp/wp/wp-content/uploads/R6%E5%88%A9%E7%94%A8%E6%96%99%E9%87%91%E6%94%B9%E8%A8%82%EF%BC%88%E6%96%B0%E7%A0%82%E9%81%8B%E5%8B%95%E5%A0%B4%EF%BC%89_202402HP%E5%91%A8%E7%9F%A5.pdf'
    rows = [(room + ' / ' + day, amount, room + '・2時間')
            for room, amounts in [('サッカー場全面', (7350, 10050)), ('第1・第2運動場全面', (5450, 7400)),
                                  ('第1・第2運動場半面', (2700, 3700)), ('多目的運動広場全面', (1800, 2400))]
            for day, amount in zip(('平日', '土日祝'), amounts)]
    result.append(entry('tokyo-venue-555e53ea3e30', source,
                        '2025年4月1日利用承認分からの通常団体料金。サッカー場・第1/第2運動場・多目的広場の区画ごとに表示。サッカー場の照明は別途1時間5,150円で、2時間枠料金には加算していません。テニス・撮影利用は対象外。', rows))

    rows = [(label + ' / ' + day, amount, '大体育室全面・' + duration)
            for label, duration, amounts in [
                ('午前9:00～12:00', '3時間', (16250, 19250)),
                ('午後13:00～17:00', '4時間', (25900, 31050)),
                ('夜間18:00～21:30', '3時間30分', (32250, 38900)),
                ('午前・午後9:00～17:00', '8時間', (38850, 46500)),
                ('午後・夜間13:00～21:30', '8時間30分', (51800, 61900)),
                ('全日9:00～21:30', '全日12時間30分', (64800, 77550)),
            ] for day, amount in zip(('平日', '土日祝'), amounts)]
    result.append(entry('tokyo-gym-01345ff23a1e', 'https://www.koto-hsc.or.jp/centerlist/sports_center3/',
                        '大体育室の通常団体全面貸切。団体登録・利用条件を確認。興行など入場料等を徴収する利用は150%。小体育室・個人公開・付帯設備を除く。半面は種目制限があるためこの表示幅には含めません。', rows))

    rows = [(label + ' / ' + day + ' / ' + area, amount, 'サブアリーナ' + area + '・' + duration + '（税込）')
            for label, duration, amounts in [
                ('午前9:00～13:00', '4時間', (9500, 19000, 11850, 23700)),
                ('午後13:00～17:00', '4時間', (9500, 19000, 11850, 23700)),
                ('夜間17:00～21:00', '4時間', (13250, 26500, 16550, 33100)),
                ('午前・午後9:00～17:00', '8時間', (17200, 34400, 21500, 43000)),
                ('午後・夜間13:00～21:00', '8時間', (20650, 41300, 25800, 51600)),
                ('全日9:00～21:00', '全日12時間', (25800, 51600, 32250, 64500)),
            ] for (day, area), amount in zip([('平日', '半面'), ('平日', '全面'), ('平日以外', '半面'), ('平日以外', '全面')], amounts)]
    result.append(entry('tokyo-gym-598414cefd93', 'https://www.tef.or.jp/tmg/subarena/subarena_fee02.pdf',
                        'サブアリーナのアマチュアスポーツ・入場料等なし。団体登録が必要。半面は原則練習のみ、利用月の2か月前から受付。平日以外は土日祝・年末年始。観客の入場料等あり・その他スポーツ等・付属設備・メインアリーナ同時利用の別区分は含みません。', rows))

    result.append(entry('tokyo-gym-ece12bfc054b', 'https://sunlifenerima.sakura.ne.jp/riyoujikan.html',
                        '練馬区公式案内からリンクされた指定管理者の2026年7月改定料金。体育室の団体貸切枠。施設予約システムで利用者・団体登録が必要。個人利用・減額免除・備品は対象外。', [
                            ('午前9:00～12:00', 5400, '体育室全面・3時間'),
                            ('午後13:00～17:00', 7200, '体育室全面・4時間'),
                            ('夜間18:00～22:00', 7200, '体育室全面・4時間'),
                        ]))
    result.append(entry('tokyo-gym-24073ef2f004', 'https://www.city.nerima.tokyo.jp/shisetsu/community/chikukuminkan/asahityouminami.html',
                        '体育室の団体利用。地域集会施設登録団体は半額。特別施設体育団体は10名以上かつ半数以上が対象地域在住在勤在学などの条件。木金日祝等に団体利用できない時間帯があります。プール・個人利用は含みません。', [
                            ('通常料金・全面', 1600, '体育室全面・1時間'),
                            ('地域集会施設登録団体・全面', 800, '体育室全面・1時間'),
                            ('通常料金・半面', 800, '体育室半面・1時間'),
                            ('地域集会施設登録団体・半面', 400, '体育室半面・1時間'),
                        ]))
    return result


def reviewed_policies():
    result = []
    groups = [
        (['tokyo-venue-9b93d81ca10e', 'tokyo-venue-8a96774363e5', 'tokyo-venue-84dbc0345777',
          'tokyo-gym-bc16a86706e5', 'tokyo-gym-dc5097408efb', 'tokyo-gym-6a6bb1ea794a',
          'tokyo-gym-145a2b1e2fa3', 'tokyo-gym-9df21a804b72'],
         'https://www.city.adachi.tokyo.jp/sg-shien/chiikibunka/shogaigakushu/riyohouhou02.html',
         '受付窓口で使用取消。利用2日前までなら50%還付。納入翌日から3日以内かつ利用2日前までなら全額還付。前日・当日は還付なし。利用者の責任でない事由で利用不能なら全額還付または条件付き振替。年末年始の還付期限は直前開館日。'),
        (['tokyo-gym-0cb647825898', 'tokyo-gym-4eb031276843', 'tokyo-gym-e9661f9d4b0f', 'tokyo-gym-815e7ebed1c0'],
         'https://www.se-sports.or.jp/keyaki/',
         '自己都合の取消料は7～6日前20%、5～3日前50%、2～1日前80%、当日以降100%。事前連絡なしは全額。屋外施設の天候不良無料取消は屋内体育館には適用されません。'),
        (['tokyo-gym-125683b2ea6c'], 'https://yotsuya-sports-square.jp/userguide1/',
         '窓口で取消・返還申請。利用1か月前の同日まで全額、翌日から14日前まで半額、それ以降は返金なし。承認後の変更は1か月前の同日まで、予約1件につき1回。'),
        (['tokyo-gym-5074f6b079ec'], 'https://www.regasu-shinjuku.or.jp/?p=668',
         '未払い予約は予約システムまたはコズミックセンター・大久保スポーツプラザ窓口で取消可能。支払い済みは窓口で返金申請が必要。返金割合は手続き日で変わり、現行案内の表を要確認（本調査では金額条件を確定していません）。'),
        (['tokyo-gym-01345ff23a1e'], 'https://www.koto-hsc.or.jp/centerlist/sports_center3/',
         '災害等で区が緊急臨時休館を決定した場合は、スポーツネットの運用手順に従って全額還付。自己都合の取消期限・還付割合は本調査では未確認です。'),
    ]
    for ids, source, summary in groups:
        result.extend({'id': ident, 'status': 'conditional', 'summary': summary,
                       'source_url': source, 'checked_at': CHECKED} for ident in ids)
    return result


def main():
    fees = reviewed_fees()
    validate(fees)
    catalog = {row['id']: row for row in get_catalog()['courts']}
    assert len(fees) == 22 and all(row['id'] in catalog for row in fees)
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
        temporary = path.with_suffix('.json.tmp')
        # Append serialized records without reformatting previous research batches.
        serialized = (json.dumps(pending, ensure_ascii=False, indent=2)[2:-2]
                      if filename == 'fee_plans.json' else
                      ',\n'.join('  ' + json.dumps(row, ensure_ascii=False, separators=(',', ':')) for row in pending))
        rendered = original.rstrip()[:-1].rstrip() + (',\n' if indexed else '\n') + serialized + '\n]'
        assert json.loads(rendered) == existing
        temporary.write_text(rendered + '\n', encoding='utf-8')
        temporary.replace(path)
    print(json.dumps({'fee_reviews': len(fees), 'cancellation_reviews': len(reviewed_policies())}))


if __name__ == '__main__':
    main()
