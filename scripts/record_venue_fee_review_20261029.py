"""Append scoped official tariffs without replacing identities or past reviews."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'outputs'))
from venues.fees import validate
from venues.sports_catalog import get_catalog, has_price
from record_venue_fee_review_20261018 import append_reviews, entry as old_entry

CHECKED = '2026-10-29'
BASE = '37bf2b3bab5eb6b225f843cdc69b7add65ab0d1f'
CATALOGS = ROOT / 'outputs/venues/catalogs'
TAITO = 'https://www.city.taito.lg.jp/kusei/shisetsu/hall/kuminkan/kuminkanriyouannai1'
TAITO_GUIDE = TAITO + '.files/kuminkanriyoannai202601.pdf'
TAITO_IN = TAITO + '.files/kunai0712.pdf'
TAITO_OUT = TAITO + '.files/kugai0712.pdf'
# One explicitly named room per community venue, not a whole-building minimum.
TAITO_ROOMS = [
    ('tokyo-venue-23fcab1795a5', '101集会室', [2200, 2700, 3100, 4100, 8000, 8600], [3300, 4050, 4650, 6150, 12000, 12900]),
    ('tokyo-venue-a86a7eeb46ef', '多目的ホール', [3300, 4000, 4600, 6100, 11900, 12800], [4950, 6000, 6900, 9150, 17850, 19200]),
    ('tokyo-venue-3d417eb9ddb1', '多目的ホール', [6600, 8100, 9200, 12200, 23900, 25700], [9900, 12150, 13800, 18300, 35850, 38550]),
    ('tokyo-venue-5ec0f9351274', '多目的ホール', [3300, 4000, 4600, 6100, 11900, 12800], [4950, 6000, 6900, 9150, 17850, 19200]),
    ('tokyo-venue-cbb9e4c8e623', '201集会室', [1800, 2400, 2500, 3300, 6700, 7500], [2700, 3600, 3750, 4950, 10050, 11250]),
    ('tokyo-venue-cf98941c1c06', '多目的ホール', [3300, 4000, 4600, 6100, 11900, 12800], [4950, 6000, 6900, 9150, 17850, 19200]),
    ('tokyo-venue-170c5d6244ec', '第1集会室', [1800, 2400, 2500, 3300, 6700, 7500], [2700, 3600, 3750, 4950, 10050, 11250]),
    ('tokyo-venue-4d06f7493e0d', '多目的ホール', [3300, 4000, 4600, 6100, 11900, 12800], [4950, 6000, 6900, 9150, 17850, 19200]),
    ('tokyo-venue-64365e822422', '第1集会室', [2200, 2700, 3100, 4100, 8000, 8600], [3300, 4050, 4650, 6150, 12000, 12900]),
    ('tokyo-venue-63761c552a29', '多目的ホール', [3300, 4000, 4600, 6100, 11900, 12800], [4950, 6000, 6900, 9150, 17850, 19200]),
    ('tokyo-venue-6c212c96a582', '第1集会室', [1800, 2400, 2500, 3300, 6700, 7500], [2700, 3600, 3750, 4950, 10050, 11250]),
    ('tokyo-venue-a6105bfc30dc', '第1集会室', [1800, 2400, 2500, 3300, 6700, 7500], [2700, 3600, 3750, 4950, 10050, 11250]),
]
TAITO_PERIODS = [('午前9～12時', '3時間'), ('午後13～17時', '4時間'), ('夜間1・18～21時', '3時間'),
                 ('夜間2・18～22時', '4時間'), ('全日1・9～21時', '12時間'), ('全日2・9～22時', '13時間')]
CHIYODA_GUIDE = 'https://www.city.chiyoda.lg.jp/shisetsu/kuyakusho/riyoannai.html'
CHIYODA_FEES = 'https://www.city.chiyoda.lg.jp/documents/6859/ryokinichiran.pdf'
CHIYODA_ROOMS = [
    ('tokyo-venue-94d304f25f14', '洋室A', [2200, 3200, 4500]),
    ('tokyo-venue-324fe306c335', '洋室A', [2300, 3300, 4100]),
    ('tokyo-venue-8fcfaf7a6e48', '洋室A', [2500, 3400, 5100]),
    ('tokyo-venue-a0077c4ae3c9', '洋室A', [2100, 2800, 4200]),
    ('tokyo-venue-95936f605ea9', '洋室A', [2500, 3400, 5100]),
    ('tokyo-venue-7229daa1f48e', '洋室A', [2400, 3300, 4900]),
]
PARA = 'tokyo-gym-d56f81f38406'
PARA_GUIDE = 'https://tokyo-ptc.jp/guide/'
PARA_FEES = 'https://tokyo-ptc.jp/wp-content/themes/tokyo-ptc/files/%E6%96%99%E9%87%91%E8%A1%A8.pdf'
HOLDS = ['tokyo-gym-a231878afdcf', 'tokyo-gym-aa77f48e78d0', 'tokyo-venue-2b0bbd7157ff',
         'tokyo-venue-8e6c0f81a52c', 'tokyo-venue-205d87234dd3', 'tokyo-venue-c282bded258a']
REVIEWED_IDS = HOLDS + [PARA] + [r[0] for r in TAITO_ROOMS + CHIYODA_ROOMS]


def entry(ident, source, note, rows):
    return dict(old_entry(ident, source, note, rows), checked_at=CHECKED)


def reviewed_fees():
    result = []
    for ident, room, inside, outside in TAITO_ROOMS:
        note = (room + 'のみの貸切料金。施設全室の最低・最高料金ではありません。入場料等の徴収なしに限定し、徴収あり・付帯設備料金は範囲外。'
                '区内は個人が在住在勤在学、団体は代表者が該当かつ構成員5割以上が該当する2人以上、その他は区外。事前窓口登録必要、原則登録構成員以外の使用不可。'
                '午前・夜間1の3時間、午後・夜間2の4時間、全日12・13時間を別単位で表示。営利、飲食主体、配信目的、不特定多数募集等の制限あり。'
                '2026年1月利用案内と区公式から現行リンクされた区内・区外料金表を照合。利用条件：' + TAITO_GUIDE)
        plans = []
        for group, amounts, source in [('区内・入場料徴収なし', inside, TAITO_IN), ('区外・入場料徴収なし', outside, TAITO_OUT)]:
            plans += [dict(label=room + ' / ' + group + ' / ' + period, amount=amount,
                           unit=room + '・' + duration + '（' + group + '）', conditions=note, source_url=source)
                      for (period, duration), amount in zip(TAITO_PERIODS, amounts)]
        result.append(dict(id=ident, checked_at=CHECKED, fee_note=note, fee_options=plans))
    for ident, room, amounts in CHIYODA_ROOMS:
        note = (room + '単室の通常料金のみ。全室最安値や併用額ではありません。一般団体は構成員半数以上が区内在住在勤在学、利用者登録・名簿審査が必要。'
                '名簿外の方は利用不可。NPO・企業等の別要件、個別減免はこの料金範囲の対象外。営利利用不可、準備撤収込み。'
                '午前3時間と午後・夜間4時間を区別し、時間単価へ換算しません。条件根拠：' + CHIYODA_GUIDE)
        result.append(entry(ident, CHIYODA_FEES, note,
                            [(room + ' / ' + period, amount, room + '・' + duration + '（一般団体）')
                             for (period, duration), amount in zip([('午前9～12時', '3時間'), ('午後13～17時', '4時間'), ('夜間18～22時', '4時間')], amounts)]))
    result.append(entry(PARA, PARA_FEES,
                        '体育室の団体利用のみ。平日と土日祝、各4時間枠を区別。トレーニング室の個人500円や他室の料金は含みません。'
                        '半数以上が障害者の団体によるスポーツ等の使用は当面料金免除、該当確認・事前団体登録が必要。個別減免は通常料金範囲へ混ぜず条件として記録。'
                        '承認通知の到着で予約確定、抽選結果確認が必要。現地券売機で支払い、クレジットカード不可。利用条件：' + PARA_GUIDE,
                        [('平日・午前9～13時／午後13～17時', 7000, '体育室・4時間（平日・通常団体）'),
                         ('平日・夜間17～21時', 8800, '体育室・4時間（平日・通常団体）'),
                         ('土日祝・午前9～13時／午後13～17時', 8800, '体育室・4時間（土日祝・通常団体）'),
                         ('土日祝・夜間17～21時', 11000, '体育室・4時間（土日祝・通常団体）')]))
    return result


def reviewed_policies():
    result = [dict(id=ident, status='conditional', source_url=TAITO_GUIDE, checked_at=CHECKED,
                   summary='支払後の取消は2か月前まで全額、15日前まで80%、7日前まで50%還付。窓口払いは承認書原本と印鑑を持参、期限が閉庁日なら直前開庁日まで。オンライン決済はシステムで取消・還付申請。変更は7日前まで1回のみで窓口手続き、付帯設備は全額還付。自然災害・施設都合閉館等は先に施設へ連絡し、通常のオンライン取消では全額還付できなくなる場合あり。通常の雨天だけで免除とは案内していません。7日前より後の還付割合は当該表に記載なし。')
              for ident, _, _, _ in TAITO_ROOMS]
    result += [dict(id=ident, status='conditional', source_url=CHIYODA_GUIDE, checked_at=CHECKED,
                    summary='前日までシステム取消または区民館へ連絡。支払後はシステム取消不可で、前日まで連絡した場合のみ窓口で返金手続き、代表者口座へ振込。当日予約は取消不可。返金の具体的割合・当日既存予約の手数料・天候免除は当該案内では未確認。')
               for ident, _, _ in CHIYODA_ROOMS]
    result.append(dict(id=PARA, status='conditional', source_url=PARA_GUIDE, checked_at=CHECKED,
                       summary='取消希望は必ず事前連絡。無断取消はキャンセル料支払いの対象。無料取消の期限・具体的料率・天候時の免除条件は公式利用案内と公開規約では未確認。通常の支払方法に関する「キャッシュレス決済後の取消不可」を予約取消そのものの禁止とは扱いません。'))
    return result


def main():
    fees, policies = reviewed_fees(), reviewed_policies()
    validate(fees)
    assert len(set(REVIEWED_IDS)) == len(REVIEWED_IDS) == 25
    assert len(fees) == len(policies) == 19 and len(HOLDS) == 6
    assert set(REVIEWED_IDS) == {r['id'] for r in fees} | set(HOLDS)
    rows = {r['id']: r for r in get_catalog()['courts']}
    assert all(ident in rows for ident in REVIEWED_IDS)
    for row in fees:
        if rows[row['id']].get('fee_checked_at') != CHECKED and has_price(rows[row['id']]):
            raise ValueError('Refusing to replace priced venue: ' + row['id'])
    for name, additions in [('fee_plans.json', fees), ('cancellation_policies.json', policies)]:
        existing = {r['id']: r for r in json.loads((CATALOGS / name).read_text(encoding='utf-8'))}
        for row in additions:
            if row['id'] in existing and existing[row['id']] != row:
                raise ValueError('Refusing to replace prior review: ' + row['id'])
    append_reviews(CATALOGS / 'fee_plans.json', fees)
    append_reviews(CATALOGS / 'cancellation_policies.json', policies)
    print(json.dumps(dict(reviewed=25, prices_added=19, policies_added=19, holds=6)))


if __name__ == '__main__':
    main()
