"""Append verified public tariffs, preserving identities and earlier reviews."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'outputs'))
from venues.fees import validate
from venues.sports_catalog import get_catalog, has_price
from record_venue_fee_review_20261018 import append_reviews, entry as old_entry

CHECKED = '2026-10-26'
CATALOGS = ROOT / 'outputs/venues/catalogs'
KAWAI = 'tokyo-gym-77213713f20f'
NIPPARA = 'tokyo-gym-3d46bb173da3'
HACHIJO = ['tokyo-venue-15fb9fbe4c57', 'tokyo-venue-fbb6eed2f3b0',
           'tokyo-venue-9cf3b539f28b', 'tokyo-venue-d53efa57a050']
CHOFU = 'tokyo-venue-aac633c1f3fe'
TRACK = 'tokyo-venue-a047783f25fd'
MUSASHINO = 'tokyo-venue-4422731f5921'
SHONEN = 'tokyo-venue-3a4d82e5e208'
TAITO = 'tokyo-venue-299cd43c6cce'
TAC = 'tokyo-gym-3ca2e0f9828f'
KEIO = 'tokyo-gym-f3e1aaf426e5'
NAKAHARA = 'tokyo-venue-f403faf4f42f'
FUJI = 'tokyo-venue-5b81852866ce'
HOLDS = ['tokyo-venue-2b0bbd7157ff', 'tokyo-venue-8e6c0f81a52c',
         'tokyo-venue-c282bded258a', 'tokyo-venue-205d87234dd3',
         'tokyo-gym-aa77f48e78d0', 'tokyo-gym-a231878afdcf', 'tokyo-gym-d56f81f38406']
REVIEWED_IDS = [KAWAI, NIPPARA] + HACHIJO + [CHOFU, TRACK, MUSASHINO, SHONEN, TAITO,
                                               TAC, KEIO, NAKAHARA, FUJI] + HOLDS
OKUTAMA = 'https://www.town.okutama.tokyo.jp/1/kyoikuka/bunka_sports/1/1/'
HACHIJO_SOURCE = 'https://www.town.hachijo.tokyo.jp/kurashi/shisetsu/taiikukan/'
CHOFU_SOURCE = 'https://www.city.chofu.lg.jp/040070/p026079.html'
TRACK_SOURCE = 'https://www.shisetsu-tds.jp/tokyo-itabashi-arakawatodabashi-rikujou/fee/'
TAITO_SOURCE = 'https://www.city.taito.lg.jp/gakushu/sports/sportssisetsuichiran/arakawa/arakawakasenjiki.html'
SHONEN_SOURCE = 'https://www.city.arakawa.tokyo.jp/a017/sport/shisetsuriyou/shounenriyou.html'
TAC_SOURCE = 'https://www.higashimurayama-sportscenter.jp/?s=1&mode=h&type=group'
KEIO_SOURCE = 'https://keio-arena.tokyo/information/pdf/pricelist.pdf'
MITAKA_SOURCE = 'https://www.city.mitaka.lg.jp/c_service/103/attached/attach_103305_4.pdf'
FUJI_SOURCE = 'https://www.city.hachioji.tokyo.jp/life/010/002/003/004/p012068_d/fil/syuti.pdf'


def entry(ident, source, note, rows):
    return dict(old_entry(ident, source, note, rows), checked_at=CHECKED)


def reviewed_fees():
    result = []
    for ident, page, outside in [(KAWAI, '1048.html', 3000), (NIPPARA, '647.html', 2000)]:
        result.append(entry(ident, OKUTAMA + page,
                            '体育館の団体貸切2時間のみ。一般登録は町内在住・在勤5名以上等、特定登録は町外等5名以上かつ使用時に町内宿泊施設へ宿泊する団体。単に町外料金を払えば日帰り利用できる意味ではありません。一般は3か月前、特定は2か月前から各10日前まで申請。用具持参、登録・使用許可が必要。' +
                            ('川井の無料グラウンド・庭球場とは別料金。' if ident == KAWAI else '日原保勝会が管理運営、使用希望団体は同会へ事前確認。'),
                            [('一般登録団体', 500, '体育館・2時間'),
                             ('特定登録団体・町内宿泊条件あり', outside, '体育館・2時間')]))
    for ident, name in zip(HACHIJO[:3], ['中之郷', '樫立', '末吉']):
        result.append(entry(ident, HACHIJO_SOURCE,
                            '町公式の通常団体利用単価。既存の屋内外複合登録について運動場と屋内運動場を別単位で記録。団体登録・空き確認・利用申請・教育委員会の許可が必要で、原則個人利用不可。入場料類を徴収する場合の1時間10,000円は通常料金の範囲外。' +
                            ('屋外照明は別途1時間250円、運動場基本料250円と合計500円。屋内500円と混同しません。' if ident == HACHIJO[2] else ''),
                            [(name + '運動場・通常利用', 250, name + '運動場・1時間'),
                             (name + '屋内運動場・通常利用', 500, name + '屋内運動場・1時間')]))
    result.append(entry(HACHIJO[3], HACHIJO_SOURCE,
                        '南原スポーツ公園のサッカー場1面の通常団体利用単価。団体登録・利用申請・教育委員会の許可が必要、原則個人利用不可。入場料類を徴収する場合の1時間15,000円、他の運動場・野球場・公園利用料は範囲外。',
                        [('サッカー場1面・通常団体', 500, 'サッカー場1面・1時間')]))
    result.append(entry(CHOFU, CHOFU_SOURCE,
                        '体育室1室（260平方メートル）の団体利用、1単位3時間（9～12・12～15・15～18・18～21時、清掃入替込み）。市内1,200円・市外2,400円、事前団体登録が必要。天井が低くバスケ・バレー・バドミントンは使用不可。卓球・武道・ダンス等の料金であり、既存種目タグが利用可能性を保証するものではありません。',
                        [('市内団体', 1200, '体育室1室・3時間'), ('市外団体', 2400, '体育室1室・3時間')]))
    result.append(entry(TRACK, TRACK_SOURCE,
                        '陸上競技場・フィールドの団体貸切1時間3,600円。団体登録・予約と事前支払が必要、準備片付け込み。貸切のないトラックの無料個人開放はフィールド対象外で占有・団体利用不可のため、貸切料金へ無料を混ぜません。駐車場別。',
                        [('団体貸切', 3600, '陸上競技場・1時間')]))
    result.append(entry(MUSASHINO, 'https://www.musashino.or.jp/sports/1001550/1001573.html',
                        '財団公式が明記するスポーツ広場A面・B面の団体貸切は市内外とも無料。各面1団体、利用4週間前から当日まで窓口受付（インターネット不可）。サッカー等が可能、ラグビーポストなし。固定時間単価を推測せず1利用として記録。大会・工事による2026年10・11月の受付中止日は別途案内があり、無料は空きや無条件利用を意味しません。',
                        [('A面・団体貸切', 0, 'スポーツ広場A面・1利用'),
                         ('B面・団体貸切', 0, 'スポーツ広場B面・1利用')]))
    result.append(entry(SHONEN, SHONEN_SOURCE,
                        '所在地は足立区小台ですが荒川区管理施設。既存登録が指す多目的広場の2時間1,000円のみ。別区画の少年野球300円・サッカー750円と混ぜません。荒川区在住・在勤・在学の登録資格、申請・支払期限あり。利用可能種目・年齢区分は区画別の利用案内に従ってください。',
                        [('多目的広場・登録利用', 1000, '多目的広場・2時間')]))
    result.append(entry(TAITO, TAITO_SOURCE,
                        '所在地は足立区千住大川町ですが台東区管理の運動公園。サッカー場1面2時間、区内登録は台東区の条件であり足立区料金ではありません。個人の事前利用者登録・本申請・支払が必要。抽選は台東区在住在勤在学、区外は空き先着申込。野球場も同額ですがここではサッカー場のみ、駐車場1台500円は別。営利・撮影利用不可。',
                        [(label, amount, 'サッカー場1面・2時間') for label, amount in
                         [('平日・台東区内登録', 1100), ('平日・区外登録', 1650),
                          ('土日祝・台東区内登録', 1300), ('土日祝・区外登録', 1950)]]))
    rows = []
    for slot, duration, base in [('夏休み早朝7～8時50分', '1時間50分', 3100),
                                 ('午前・午後1・午後2・夜間1', '2時間30分', 4300),
                                 ('夜間2・19時40分～22時20分', '2時間40分', 4300)]:
        rows += [(label + ' / ' + slot, base * factor, '第2体育室・' + duration)
                 for label, factor in [('市内団体', 1), ('市外団体', 2)]]
    result.append(entry(TAC, TAC_SOURCE,
                        '既存登録が指す第2体育室のみ。7名以上で団体登録、構成員の過半数以上が東村山市在住在勤在学の市内団体が基本額、他は倍額。実際の時間区分を分離し、夜間2は2時間40分。夏休みのみ早朝枠あり。第1体育室・半面・営利3倍等・附帯設備は範囲外。2026年11月5日は体育館棟臨時休館。プールの別日程を体育館全体へ適用しません。', rows))
    rows = []
    for slot, amounts in [('午前9～13時・午後13～17時', [(7000, 14000, 8800, 17600), (14000, 28100, 17600, 35200)]),
                           ('夜間17～21時', [(8800, 17600, 11000, 22000), (17600, 35200, 22000, 44000)])]:
        for category, values in zip(['スポーツ区分A', 'スポーツ区分B'], amounts):
            rows += [(category + ' / ' + day + ' / ' + space + ' / ' + slot, value,
                      'サブアリーナ' + space + '・4時間')
                     for (day, space), value in zip([('平日', '半面'), ('平日', '全面'),
                                                     ('土日祝', '半面'), ('土日祝', '全面')], values)]
    result.append(entry(KEIO, KEIO_SOURCE,
                        '既存登録のサブアリーナ、入場料等なしのスポーツA・Bの午前・午後・夜間各4時間のみ（税込）。Aは主催者関係者に限定する団体内練習等、Bは複数チームの大会等で学割区分ではありません。半面・全面を分離。半面は利用月2か月前から受付、全面優先。8時間・全日12時間・入場料徴収・商業・設備料は範囲外。バスケットゴール等は別料金（1日1面24,000円）で本体料金だけの総額利用を保証しません。', rows))
    result.append(entry(NAKAHARA, MITAKA_SOURCE,
                        '市のスポーツインフォメーション2025の団体利用表（冊子3ページ）で練習エリア3面の無料を確認。2026年10月20日更新の施設案内とも用途・登録制を照合。1区分2時間、団体登録と初回説明が必要。フットサルは6人以上、他種目は登録人数等の要件あり。試合のできる広さではなく、個人の空き時間開放とは別。',
                        [('登録団体・練習エリア', 0, '練習エリア1面・2時間')]))
    result.append(entry(FUJI, FUJI_SOURCE,
                        '市が現行施設ページでリンクする東京フットボールセンター八王子富士森競技場の団体貸切、1回3時間以内。一般サークルへ無条件貸出ではなく、小中学生の陸上・サッカー等や市内団体の運動会等、原則50名以上で教育委員会が認めるその他催事など対象制限あり。個人申込みによる団体利用不可。全面・半面を分離。夜間照明3,000円/3時間以内、サッカー用器具2,000円/3時間以内、時間外超過・特別徴収額は別途。無料開放や50～200円の個人陸上利用と混ぜません。',
                        [('許可対象団体・全面', 15000, '競技場全面・3時間以内'),
                         ('許可対象団体・半面', 7500, '競技場半面・3時間以内')]))
    return result


def policy(ident, source, summary):
    return {'id': ident, 'status': 'conditional', 'summary': summary,
            'source_url': source, 'checked_at': CHECKED}


def reviewed_policies():
    return [
        policy(KAWAI, OKUTAMA + '1048.html', '取消時は教育委員会教育課へ必ず連絡（平日8時30分～17時15分）。使用料は原則不還付、教育委員会の事情等による許可取消などは還付。一般的な取消期限・返還割合や雨天の自動免除は明記がないため推測しません。'),
        policy(CHOFU, CHOFU_SOURCE, '当日キャンセルは使用開始時刻前までに現地管理事務所へ直接連絡。期限前後の金銭手数料・還付率や屋内施設の天候免除は、この施設案内では確認できません。'),
        policy(TRACK, TRACK_SOURCE, '天候やグラウンド状態で中止の場合は利用料を還付。当日に小豆沢体育館へ可否を確認し、施設側から中止連絡はありません。利用承認書を持参して体育館・温水プール窓口で手続き（口座振替団体は手続き不要）。自己都合取消の期限・返還率はこの案内では未確認。'),
        policy(SHONEN, SHONEN_SOURCE, '熱中症特別警戒アラート発表時は施設使用を中止。これは通常の暑さ一般による無条件取消ではありません。自己都合取消の期限・手数料・還付額や雨天の扱いはこの案内では確認できません。'),
        policy(TAITO, TAITO_SOURCE, '利用2か月前まで全額、15日前まで8割、7日前まで半額、6日前～当日は還付なし。管理人がグラウンド使用不能と判断した場合は、使用せず承認書兼領収書・申込者の印鑑を持ってスポーツ振興課で還付手続き。掲載ページの暑さによる還付は開始前申出が条件ですが旧称「高温注意情報」のため、現行警戒情報への適用範囲は推測しません。'),
        policy(KEIO, 'https://keio-arena.tokyo/information/', '団体利用キャンセル申込書をFAX・郵送・窓口で提出。納入済み料金は原則不還付。ただし、やむを得ない事情で残額納入期限までに申し出た場合は利用予納金を除き還付。予納金10%は申込から1週間以内、残額は申込から1か月以内（使用まで1か月以内の申込は一括払い）。「利用日の1か月前まで返金」ではありません。'),
    ]


def main():
    fees, policies = reviewed_fees(), reviewed_policies()
    validate(fees)
    assert len(REVIEWED_IDS) == len(set(REVIEWED_IDS)) == 22
    assert len(fees) == 15 and len(policies) == 6 and len(HOLDS) == 7
    assert set(REVIEWED_IDS) == {r['id'] for r in fees} | set(HOLDS)
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
    print(json.dumps({'facilities_reviewed': 22, 'prices_added': 15, 'policies_added': 6, 'holds': 7}))


if __name__ == '__main__':
    main()
