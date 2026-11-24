"""Append one scoped tariff and official sports cancellation conditions."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'outputs'))
from venues.fees import validate
from venues.sports_catalog import get_catalog, has_price
from record_venue_fee_review_20261018 import append_reviews, entry as earlier_entry
import record_venue_fee_review_20261123 as previous

CHECKED = '2026-11-24'
BASE = 'aa868f432255227a51e43691bd3d06ed184bd03f'
CATALOGS = ROOT / 'outputs/venues/catalogs'
PASELA = 'https://www.pasela.co.jp/shop/shinjuku/price.html'
KOMAZAWA = 'https://www.tef.or.jp/kopgp/general/'
NAKANO = 'https://information.konamisportsclub.jp/file.jsp?id=38043'
CHUO = 'https://www.city.chuo.lg.jp/documents/4235/riyouannai.pdf'
SHINAGAWA = 'https://www.city.shinagawa.tokyo.jp/_res/projects/default_project/_page_/001/008/256/hpg000006487_2.pdf'
SUGINAMI_IDS = ['tokyo-sports-043', 'tokyo-sports-044']
KOMAZAWA_IDS = ['tokyo-komazawa-ballgame2', 'tokyo-komazawa-substadium', 'tokyo-komazawa-stadium']
KITA_IDS = ['tokyo-venue-0ed440fdd641', 'tokyo-venue-e4038f2459a4', 'tokyo-venue-a231a98caa19']
HACHIOJI_IDS = ['tokyo-venue-fb1731b080c2', 'tokyo-venue-340b25d181f0']
SHINAGAWA_IDS = ['tokyo-venue-7d1c070c2f5e', 'tokyo-venue-74e266c5a64d']
RECHECKS = SUGINAMI_IDS + KOMAZAWA_IDS + [
    'tokyo-venue-c3c8b7f2193f', 'tokyo-venue-76009f87c8f4', 'tokyo-venue-712511e56aa8',
    'tokyo-venue-c00e2b6906bf'] + HACHIOJI_IDS + KITA_IDS + [
    'tokyo-venue-7688aee9e7f7', 'tokyo-venue-7d1c070c2f5e', 'tokyo-venue-27db04888b6c',
    'tokyo-venue-74e266c5a64d', 'tokyo-venue-a2d6191898f8', 'tokyo-venue-c8eeb7f64931',
    'tokyo-venue-a6e3e9da0d77', 'tokyo-venue-cd769beb35fc']
HOLDS = ['tokyo-venue-3ffcbdafb4b2', 'private-tanashi-yunan', 'island-niijima-sports']


def reviewed_fees():
    note = ('新宿本店の大人1名30分の税込基本料金。昼8～17時は無料1ドリンク付き、夜17時～翌8時は室料のみとして分離。'
        '昼の平日380円・土日祝580円、夜の月～木580円・金～日祝前祝680円。飲み放題・料理・パック・追加オプションは含めません。'
        '2026年12月1日～2027年1月3日は全日週末料金のため別の期間限定単位で保存。1室全体の貸切価格や1時間料金ではありません。'
        '小学生以下等の割引・無償料金は今回採用せず、大人の通常額と混ぜません。取消期限・手数料は基本料金だけでは未確認。')
    options = [
        ('通常・昼・月～金', 380, '大人1名30分（昼・1ドリンク込・通常期間）'),
        ('通常・昼・土日祝', 580, '大人1名30分（昼・1ドリンク込・通常期間）'),
        ('通常・夜・月～木', 580, '大人1名30分（夜・室料のみ・通常期間）'),
        ('通常・夜・金～日祝前祝', 680, '大人1名30分（夜・室料のみ・通常期間）'),
        ('2026/12/1～2027/1/3・昼・全日週末料金', 580, '大人1名30分（昼・1ドリンク込・2026/12/1～2027/1/3）'),
        ('2026/12/1～2027/1/3・夜・全日週末料金', 680, '大人1名30分（夜・室料のみ・2026/12/1～2027/1/3）'),
    ]
    return [dict(earlier_entry('tokyo-pasela-shinjuku', PASELA, note, options), checked_at=CHECKED)]


def policy(ident, source, summary):
    return dict(id=ident, checked_at=CHECKED, status='conditional', source_url=source, summary=summary)


def reviewed_policies():
    old = {r['id']: r for r in previous.reviewed_policies()}
    rows = [policy(ident, previous.SUGINAMI, old['tokyo-sports-005']['summary']) for ident in SUGINAMI_IDS]
    rows += [policy(ident, previous.KITA, old['tokyo-sports-029']['summary']) for ident in KITA_IDS]
    rows += [policy(ident, KOMAZAWA,
        '通常の先着受付に関する案内：予納金は利用料金の10％、残額は利用申込日から1か月以内に納入。'
        '納付済み料金は原則返還不可。ただしやむを得ない事情で残額納入期限までに取消を申し出た場合、予納金を除く額を返還。'
        '利用日1か月前以降の申込は1週間以内に全額納付し、取消しても返還不可。施設による取扱い差は窓口確認が必要。'
        '軟式野球場・テニスコートだけの3日前無料取消をこの球技場・競技場へ適用しません。雨天時の個別還付率は未確認。')
        for ident in KOMAZAWA_IDS]
    rows.append(policy('tokyo-venue-c3c8b7f2193f', 'https://www.chuo-sports.jp/guide/',
        '指定管理者の現行団体利用案内は来館申込時に使用料納付・承認書交付。申込後の変更・キャンセルは不可と明記。'
        '備品は別料金の場合があり、準備・片付け・更衣も利用時間内。学校施設や屋外運動場の還付表は流用しません。'
        'この案内から例外時の返金率や屋内施設の雨天免除は確認できず、無料取消とは扱いません。'))
    rows.append(policy('tokyo-venue-76009f87c8f4', CHUO,
        '浜町運動場の取消は10日前までシステムから、9～5日前は1ポイント、4日前～当日の連絡あり取消は2ポイント、無断は3ポイント。'
        '当日取消は開始時刻までに直接施設へ連絡。学校体育館・河川敷の支払済み還付率と別の扱いです。'
        '雨天・高温・強風等の利用可否は施設へ確認し、自己判断で利用しないとペナルティ対象の場合あり。'
        '施設判断で中止又は利用時間の半分以下で途中中止の場合は使用料返却。取消ポイントと金銭の取消料を混同しません。'))
    rows.append(policy('tokyo-venue-712511e56aa8', NAKANO,
        '現行案内は利用日の1か月前から取消料発生と記載し、支払済み予約の還付表は15日前まで80％、7日前まで50％、6日前から0％。'
        '1か月境界の適用は窓口確認とし、15日前なら無条件80％・それ以前も一律80％とは一般化しません。'
        '取消料発生時は来館手続きが必要。取消は申込時点から1ポイント、不来場（未払いかつ不使用）も1ポイント。'
        '過去5か月で5ポイントの月の翌月から1か月申込制限。金銭の取消料・還付とポイントは別制度。屋内の雨天免除は未確認。'))
    rows.append(policy('tokyo-venue-c00e2b6906bf', 'https://www.hachioji.esforta.jp/how-to-use/',
        '屋内貸切はフロントで取消。1か月前の同日まで0％、翌日～2週間前50％、13日前以降100％。'
        '屋外運動場は別で8日前まで無料、7～3日前50％、2日前～当日100％。天候不良時は2時間前から電話申出で無料取消可、'
        '施設が荒天中止とする場合あり。屋外の雨天条件を屋内アリーナに適用しません。屋外で無断・連絡不能の場合の予約制限は取消料支払後に解除。'))
    rows += [policy(ident, 'https://www.city.hachioji.tokyo.jp/shisetsu/104/p005417.html',
        '八王子市の屋外運動施設：前日までは予約システム、当日は各施設へ直接電話で取消。'
        '当日取消・無断不使用は抽選申込と空き施設予約を3か月制限。開始は該当月の翌々月1日で、取消の翌日からではありません。'
        '例：5月5日当日取消なら7月1日～9月30日。制限開始前に確保済みの予約は有効。'
        'この案内から当該施設の金銭の取消料や雨天免除額は未確認で、無料とは扱いません。') for ident in HACHIOJI_IDS]
    rows += [policy(ident, SHINAGAWA,
        '品川区公園運動施設は1週間前まで取消、6日前～前日は使用料100％（照明料除く）、当日は100％（照明料含む）。'
        '口座払いは該当額を引落し。現金等の返還手続きは期限内に窓口で行い、電話申出後の後日返還手続きは不可。'
        '休館日・他の開館窓口・年末年始の例外は公式ガイドに従います。'
        '天候不良で施設が中止と判断した分は使用料なし。必ず当日現地へ確認（目安開始2時間前、最初の枠は窓口受付開始時）。'
        '口座払いは不徴収、支払済みは窓口で口座振込返還手続き。譲渡前提・取消前提の枠確保は認められません。') for ident in SHINAGAWA_IDS]
    rows.append(policy('tokyo-venue-a6e3e9da0d77', 'https://www.city.meguro.tokyo.jp/sports/kusei/onlineservice/chuui.html',
        '目黒区サッカー場は5日前から直前取消の対象。直前取消3回又は無断不使用で、その時点から3か月間抽選・空き予約不可。'
        '屋外は利用当日支払。天候・コート不良で施設が利用不可の場合は自分でシステム取消せずそのままにし、ペナルティ対象外。'
        '利用可否は施設のお知らせ又は施設へ確認。納付後の還付は別手続きが必要で、この注意事項では具体的還付率は未確認。'))
    rows.append(policy('tokyo-venue-cd769beb35fc', 'https://www.city.ota.tokyo.jp/shisetsu/uguisunet_annai/ugu.html',
        'うぐいすネット公園施設の未払い予約は3日前までWeb取消、2日前～当日は施設窓口に相談。'
        '2日前・前日の取消は取消日から1か月、当日取消・無断不使用は3か月の利用制限。'
        '支払後は窓口で手続きし、自己都合の還付は原則なし（施設・理由・申請日による例外は窓口確認）。'
        '天候・グラウンド不良で施設が使用中止の場合は全額還付又は同じ施設・種目の利用変更が可能。'
        '必ず使用可否を確認し、確認せず無断不使用ならペナルティ対象。'))
    rows.append(policy('tokyo-venue-a2d6191898f8',
        'https://www.city.kokubunji.tokyo.jp/culture-sports-tourism/sports/1011397/1002609.html',
        '国分寺市の共通還付案内：利用者の責めによらない使用不可は原則全額、自己都合は1か月前まで全額、10日前まで半額。'
        '還付は窓口申請で許可書兼領収書又はスポーツセンター承認書と印鑑が必要。屋外の天候による全額又は半額を屋内に流用しません。'
        '2027年3月1日以降利用分の新システムのキャッシュレス還付方法は調整中との記載あり。'
        'ひかりの第一体育室は停止中、第二体育室とは区別。工事は2027年1月末頃予定で、再開日は確定していません。'))
    return rows


REVIEWED_IDS = RECHECKS + HOLDS + [r['id'] for r in reviewed_fees()]


def main():
    fees, policies = reviewed_fees(), reviewed_policies()
    validate(fees)
    assert len(REVIEWED_IDS) == len(set(REVIEWED_IDS)) == 26
    assert len(RECHECKS) == 22 and len(policies) == 19
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
