"""Append verified cancellation scopes and one newly documented ground tariff."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'outputs'))
from venues.fees import validate
from venues.sports_catalog import get_catalog, has_price
from record_venue_fee_review_20261018 import append_reviews, entry as earlier_entry

CHECKED = '2026-11-23'
BASE = '3bd1c2c7d387c859b5d4f3e9e38a29c4fd39dad1'
CATALOGS = ROOT / 'outputs/venues/catalogs'
SUGINAMI = 'https://www.city.suginami.tokyo.jp/s032/652.html'
NERIMA = 'https://www.call-center.jp/faq_nerima/faq.asp?faqno=NER03648'
FUCHU = 'https://www.city.fuchu.tokyo.jp/shisetu/supotu/yoyaku/torikesi.html'
KITA = 'https://www.city.kita.lg.jp/culture-tourism-sports/sports/1010385/1010387/1010441.html'
EDOGAWA = 'https://www.city.edogawa.tokyo.jp/e028/kuseijoho/denshi/shisetsuyoyaku/info_sports.html'
EDOGAWA_CANCEL = 'https://www.city.edogawa.tokyo.jp/e030/qa/kusejoho/onlineservice/shisetsu/cancel/002.html'
HAMURA = 'https://www.city.hamura.tokyo.jp/0000000768.html'
SUGINAMI_IDS = ['tokyo-sports-005', 'tokyo-sports-006', 'tokyo-sports-042']
NERIMA_IDS = ['tokyo-sports-007', 'tokyo-sports-008', 'tokyo-sports-009', 'tokyo-sports-010']
KITA_IDS = ['tokyo-sports-029', 'tokyo-sports-034', 'tokyo-sports-035', 'tokyo-sports-036', 'tokyo-sports-037']
RECHECKS = [f'tokyo-sports-{n:03}' for n in [5, 6, 7, 8, 9, 10, 20, 21, 22, 23, 27, 28, 29, 34, 35, 36, 37, 39, 40, 41, 42]]
HOLDS = ['tokyo-sports-025', 'tokyo-venue-205d87234dd3', 'tokyo-venue-b350e0713b8e', 'tokyo-venue-74f8af5c1bc3']


def reviewed_fees():
    note = ('あさひ公園の有料ソフトボール場1面について、市の公園有料施設一覧と使用料表を照合。'
        '6～18時の昼間2時間単位610円のみを採用。バスケットゴールの利用料やバスケットコート貸切料金ではありません。'
        '施設利用には公共予約システムの利用登録が必要。減免や夜間の利用可否・照明の当該施設への適用は今回未確認のため、'
        '夜間3時間料金・照明料・減免料金は採用しません。取消条件・雨天時の還付も未確認。')
    return [dict(earlier_entry('tokyo-venue-1c5373a218d7', HAMURA, note, [
        ('ソフトボール場・昼間6～18時', 610, 'ソフトボール場1面2時間（昼間）')]), checked_at=CHECKED)]


def policy(ident, source, summary):
    return dict(id=ident, checked_at=CHECKED, status='conditional', source_url=source, summary=summary)


def reviewed_policies():
    rows = [policy(ident, SUGINAMI,
        'さざんかねっとの貸切予約は利用7日前までの取消なら申込制限なし。'
        '6日前～開始時刻までの取消は利用予定日翌日から30日間、開始までに取消しない場合は90日間、'
        '抽選・空き枠申込と当選分の利用確定ができません。既に予約済みの枠は利用可。'
        '利用予定施設で利用料相当額を任意に支払うと制限解除可能ですが、自動徴収のキャンセル料とは区別します。'
        '利用枠の譲渡は禁止。一般の返金額や雨天免除はこの案内では未確認。') for ident in SUGINAMI_IDS]
    rows += [policy(ident, NERIMA,
        '2026年7月以降の利用分：予約取消自体に施設使用料はかかりません。'
        '7日前を過ぎての取消は利用予定日翌日から30日間、無連絡不使用は90日間、'
        '予約システムの随時予約・抽選申込・当選申請を制限。随時予約と当選申請のみ施設窓口で受付可能。'
        '2026年6月までの月1枠上限制度とは異なります。料金の無償取消と申込制限は別です。'
        '屋内体育館に雨天だけでの免除を適用しません。') for ident in NERIMA_IDS]
    rows.append(policy('tokyo-sports-020', 'https://www.fctokyoparkfuchu.jp/rental/',
        'レンタルコートは8日前まで0％、8日前経過～3日前50％、3日前経過～当日100％。'
        '24時間前までは予約サイト、それ以降は電話で取消。キャンセル料は受付から1週間以内に窓口又は振込で支払います。'
        '通常の雨は実施。荒天は利用1時間30分前に確認し、安全利用不可と施設が判断した場合に限り取消料なし。'
        '府中市への気象警報発令時は利用不可。無許可の営利利用は不可、大会運営は別途施設への相談が必要。'))
    rows.append(policy('tokyo-sports-021', 'https://www.jexer.jp/futsal/oi/program.html',
        'コートは11日前まで取消料なし、10～3日前50％、2日前～当日及び無連絡100％。'
        'Web取消期限後は電話又は窓口。取消料は申出後1週間以内に窓口又は振込（手数料利用者負担）で支払い。'
        '雨天でも利用可。荒天の利用可否は開始1時間前までに運営者が判断するため電話確認が必要。'
        '運営者が利用困難と判断した場合のみ時期に関わらず取消料なし。自己判断の取消は当日扱い。'))
    rows.append(policy('tokyo-sports-022', 'https://www.sports-alpha.com/shinagawa/use.html',
        '通常フットサルの取消・日時変更は平日1週間前、土日祝2週間前まで無料、以降は全額。'
        '長時間・複数面・複数日の予約には事前振込後変更不可や予約完了時から全額の別条件あり。'
        '学割の取消料は通常料金で算定。雨天取消と荒天時の無断不使用も全額。'
        '施設が開始2時間前以降に荒天と判断し電話確認を受けた場合は振替可、返金保証ではありません。'
        '振替日は1週間以内に2か月先までで決定、同料金以上、再取消・再変更不可。'
        'ソサイチは振込後取消・返金不可、トレサポ割は予約後全額のため通常枠の無料期限を適用しません。'
        '暑さ指数による取消条件変更なし。取消料の支払は申出から1週間以内。'))
    rows.append(policy('tokyo-sports-023',
        'https://www.jpnsport.go.jp/hpsc/facility/futsal/info/m7rhmn000000132t-att/kyanseruryouchoushuusaikai.pdf',
        '2023年5月8日利用分から通常の取消料徴収を再開。10日前まで無料でWeb取消、以降は電話又は受付。'
        '9～3日前は利用料50％、2日前～当日は100％。Web期限は日付だけでなく予約開始時刻にも注意'
        '（公式例：5月8日10時の予約は4月28日9時59分まで）。発生日から10日以内に受付で支払い。'
        '未払いは会員資格取消・利用拒否の対象。一般の雨天免除条件はこの通知では未確認。'))
    rows.append(policy('tokyo-sports-027', 'https://omori-sc.jp/information/',
        '貸切使用料は申込時納付。使用承認後の取消は原則不可。天災や工事等、施設側の理由で利用できない場合は例外。'
        'この案内では利用者都合の無料取消期限や具体的な返金率を確認できず、無料と扱いません。'
        '屋内施設のため通常の雨だけを取消免除理由としません。'))
    rows.append(policy('tokyo-sports-028', FUCHU,
        '予約取消はスポーツタウン推進課又は総合体育館窓口で、利用券控えと取消申込書を提出。'
        '団体は代表者本人、代理人は委任状が必要。使用料還付は1か月前まで100％、それを過ぎ10日前まで50％、'
        '9日前以降0％。月末・年末年始の期限補正は公式案内に従い、単純な30日前換算はしません。'
        '還付額の100円未満の端数は50円単位で切り捨て。場所・日時の予約誤りでも同条件。'))
    rows += [policy(ident, KITA,
        '北区スポーツ施設の取消：支払前は予約システム、支払後は体育系窓口のみ（電話不可）。'
        '登録証・申請者の公的証明・領収書（オンライン決済は領収書不要）を持参し、登録メンバーのみ申請可。'
        '14日前まで全額還付又は振替、13～7日前は半額還付又は振替、6日前～当日は還付・振替不可。'
        '未払いでも13日前以降は全額納付後に該当条件を適用します。委任状による登録外の代理申請は不可。'
        'この案内から雨天免除は確認できず、無料取消と推定しません。') for ident in KITA_IDS]
    rows.append(policy('tokyo-sports-039', EDOGAWA,
        '屋外施設の事前取消は利用6日前午前0時以降キャンセルポイントの対象。'
        '当日に雨天・災害等で施設利用不可となった場合は事前取消のポイントを後日免除する扱いがあります。'
        '雷・光化学スモッグの注意報又は警報の場合は当日取消のみポイント免除。'
        'ポイント免除と使用料還付は別で、未納予約の取消に金銭の取消料はなく、納付後は原則還付なし。'
        '利用者責任でない利用不可等の全額還付例外は区の取消FAQに従います。'
        '利用実態なしに利用券を渡すだけではポイント免除になりません。営利目的利用は禁止。'))
    rows += [policy(ident, EDOGAWA,
        '利用6日前午前0時以降の事前取消はキャンセルポイントの対象。'
        '臨海球技場フットサルコート・葛西ラグビースポーツパークは、当日雨天等で使えなくなった場合の'
        '事前取消ポイントの事後免除から除外されています。両施設とも単に雨なら免除とは扱いません。'
        '雷・光化学スモッグの注意報又は警報の当日取消については全屋外施設でポイント免除。'
        '金銭の取消料とポイントは別。未納予約の取消料はなく、納付後は原則還付なしで、'
        '利用者責任でない利用不可等の全額還付例外は区の取消FAQに従います。営利目的利用は禁止。')
        for ident in ['tokyo-sports-040', 'tokyo-sports-041']]
    rows.append(policy('tokyo-venue-b350e0713b8e',
        'https://www.city.musashimurayama.lg.jp/shisetus/reservation/1014615.html',
        '公共施設の予約取消は原則利用3日前まで予約システム、2日前～当日は予約施設窓口で取消申請。'
        '2022年更新案内に感染症対策として電話申請可との記載もありますが、現在の受付可否は施設確認が必要。'
        'この案内では少年野球場の使用料・取消手数料・返金率・雨天免除額は未確認で、無料とは扱いません。'))
    return rows


REVIEWED_IDS = RECHECKS + HOLDS + [r['id'] for r in reviewed_fees()]


def main():
    fees, policies = reviewed_fees(), reviewed_policies()
    validate(fees)
    assert len(REVIEWED_IDS) == len(set(REVIEWED_IDS)) == 26
    assert len(fees) == 1 and len(policies) == 22
    rows = {r['id']: r for r in get_catalog()['courts']}
    assert set(REVIEWED_IDS) <= rows.keys()
    for fee in fees:
        if has_price(rows[fee['id']]) and rows[fee['id']].get('fee_checked_at') != CHECKED:
            raise ValueError('Refusing to replace an already priced facility: ' + fee['id'])
    append_reviews(CATALOGS / 'fee_plans.json', fees)
    append_reviews(CATALOGS / 'cancellation_policies.json', policies)
    print(json.dumps(dict(reviewed=26, prices_added=len(fees), policies_added=len(policies))))


if __name__ == '__main__':
    main()
