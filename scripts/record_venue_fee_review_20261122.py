"""Append scoped official tariffs and cancellation evidence without changing prior data."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'outputs'))
from venues.fees import validate
from venues.sports_catalog import get_catalog, has_price
from record_venue_fee_review_20261018 import append_reviews, entry as earlier_entry

CHECKED = '2026-11-22'
BASE = '6381c6851b5d77895b16f134849cd43021dc8786'
CATALOGS = ROOT / 'outputs/venues/catalogs'
HALL_FEE = 'https://www.persimmon.or.jp/use/fee.html'
HALL_CANCEL = 'https://www.persimmon.or.jp/use/usage_hall.html'
MUSASHINO = 'https://city.tennis-musashino.co.jp/wp-content/uploads/2026/10/025d53f871e5acd791cc8c2cae2519c4.pdf'
NISHI = 'https://www.sports-create.com/nishikoku/fee/'
NISHI_BOOK = 'https://reserve.tennisbear.net/nishikoku'
WAKASU = 'https://wakasu.golftk.com/fee.html'
WAKASU_TERMS = 'https://wakasu.golftk.com/images/reservation/terms_202608.pdf'
GYMS = ['tokyo-sports-001', 'tokyo-sports-002', 'tokyo-sports-003', 'tokyo-sports-004']
RECHECKS = GYMS + ['tokyo-sports-018', 'tokyo-sports-019']
HOLDS = ['private-chitose', 'private-santopia', 'private-tanashi-yunan', 'private-sakurada', 'private-ivy-hachioji',
    'island-niijima-sports', 'island-kozushima-center',
    'tokyo-venue-224e0edf8fc0', 'tokyo-venue-9f52d51c61cb', 'tokyo-venue-78cfa1010903',
    'tokyo-venue-c8cf7bf99ca9', 'tokyo-venue-19d02dcce634', 'tokyo-venue-dda23102caba',
    'tokyo-venue-c9686e23e983', 'tokyo-venue-4dd228f1be29']


def entry(ident, source, note, options):
    return dict(earlier_entry(ident, source, note, options), checked_at=CHECKED)


def hall_options(room, day, general, arts):
    return [(f'{room}・{day}・{category}・{slot}', amount, f'{room}・{duration}（{category}・{day}）')
        for category, amounts in [('一般団体', general), ('登録芸術文化活動団体', arts)]
        for (slot, duration), amount in zip([
            ('午前9～12時', '3時間'), ('午後13～17時', '4時間'),
            ('夜間18～22時', '4時間'), ('全日9～22時', '全日13時間')], amounts)]


def reviewed_fees():
    note = ('部屋・曜日・時間帯・登録区分別の施設利用料。午前3時間、午後/夜間4時間、全日13時間を分離。'
        '芸術文化活動団体は区の登録と適格な芸術文化活動に限る減額料金で、一般団体の最安料金には混ぜません。'
        '特殊器具は別料金、各ホールの楽屋は含む。一般団体の入場料等3,000円以上又は商品直売は通常額の150％。'
        '芸術文化登録団体でも大ホールで1,000～3,000円未満の入場料なら一般料金、3,000円以上等は一般料金の150％。'
        '大ホールの早朝・舞台面のみ・延長料金は対象外。準備・片付けを含み、連続区分の中間1時間は継続利用可。'
        '利用者登録・事前打合せ等が必要。工事・点検による将来の休館や抽選日程、利用可能用途は最新の施設案内で確認。')
    main = []
    for room, day, general, arts in [
        ('大ホール', '平日', (93400, 160000, 191200, 444600), (46700, 80000, 95600, 222300)),
        ('大ホール', '土日休', (112000, 192000, 229400, 533400), (56000, 96000, 114700, 266700)),
        ('小ホール', '平日', (19300, 33200, 39600, 92100), (9700, 16600, 19800, 46100)),
        ('小ホール', '土日休', (23200, 39800, 47500, 110500), (11600, 19900, 23800, 55300)),
        ('リハーサル室', '共通', (2200, 3800, 4500, 10500), (1100, 1900, 2300, 5300)),
        ('第1練習室', '共通', (1600, 2800, 3300, 7700), (800, 1400, 1700, 3900)),
        ('第2練習室', '共通', (1300, 2200, 2600, 6100), (700, 1100, 1300, 3100)),
        ('第3練習室', '共通', (1400, 2400, 2900, 6700), (700, 1200, 1500, 3400)),
        ('会議室', '共通', (1000, 1800, 2100, 4900), (500, 900, 1100, 2500)),
        ('保育室', '共通', (1200, 2000, 2400, 5600), (600, 1000, 1200, 2800)),
    ]:
        main.extend(hall_options(room, day, general, arts))
    rows = [entry('tokyo-venue-e8c8e3801fe4', HALL_FEE, note, main)]
    gt = hall_options('ホール', '平日', (10100, 17300, 20600, 48000), (5000, 8600, 10300, 23900))
    gt += hall_options('ホール', '土日休', (12100, 20700, 24700, 57500), (6000, 10400, 12400, 28800))
    rows.append(entry('tokyo-venue-0094fb226d0e', HALL_FEE, note, gt))
    rows.append(entry('tokyo-wakasu-golf-links', WAKASU,
        '1組4名の場合の1名1ラウンドの税込合計。プレーフィ・ゴルフ場利用税600円・緑化協力金50円を含む。'
        'キャディ付きと通常セルフ（食事別）、セルフデー（食事込）を別単位とし、9ホールの早朝・薄暮とは混ぜません。'
        '3バッグ・2バッグ加算、レンタル品・食事別区分の食事代は含みません。年齢・障害等の税免除や割引は通常額へ適用しません。'
        '1月2・3日、12月29・30日は休日扱い。原則都内在住・在勤者、補充申込は区分が異なるため公式約款を確認。'
        '通常セルフ・セルフデーの実施日や抽選・登録条件は公式スケジュールに従います。', [
            (f'{category}・{day}', amount, f'1名1ラウンド（税込・4名1組・{category}）')
            for category, values in [('キャディ付き・食事別', (15540, 24540)),
                                     ('通常セルフ・食事別', (12450, 21450)),
                                     ('セルフデー・食事込', (13600, 22600))]
            for day, amount in zip(('平日', '土日祝（セルフデーは祝日）'), values)]))
    rows.append(entry('private-musashino-tennis-city', MUSASHINO,
        '2026年12月期限定の公式レンタル要項。通常通年料金や現在の空き枠を保証するものではありません。'
        '1コート6名まで、7名以上は事前相談。30分と60分を別単位で保存。抽選・随時申込や当月期のみの予約、受付時間帯の条件あり。'
        'ビジターも対象ですが通常レッスンとの重複やプライベートレッスン等の使用は禁止。'
        '終了5分前には退出準備が必要。要項内にボール貸出の可否・申込月の記載差があるため備品代・受付可否は施設に確認。'
        '料金に備品貸出やイベント参加費は含めません。', [
            ('12月期・30分', 2000, '1面30分（税込・2026年12月期限定）'),
            ('12月期・60分', 4000, '1面60分（税込・2026年12月期限定）')]))
    rows.append(entry('private-nishikoku', NISHI,
        '公式のレンタル料金表と公式埋込予約先の1面1時間・12名上限を照合した通常税込料金。'
        '平日10～16時1,100円、16～18時2,200円、18～21時2,750円、土日祝10～18時3,300円・18～21時3,850円。'
        'スクール受講料とは別。照明内訳は明記なし、備品貸出は別料金。2026年7月14日以降ソフトテニス不可。'
        'スクール契約外のレッスン・営利活動は禁止。受付・抽選・公開予約枠の情報は最新の公式予約先で確認。'
        '7日前取消の扱いが本体サイトと予約先で異なるため事前に確認が必要。', [
            (slot, amount, '1面1時間（税込・12名まで）') for slot, amount in [
                ('平日10～16時', 1100), ('平日16～18時', 2200), ('平日18～21時', 2750),
                ('土日祝10～18時', 3300), ('土日祝18～21時', 3850)]]))
    return rows


def policy(ident, source, summary):
    return dict(id=ident, checked_at=CHECKED, status='conditional', source_url=source, summary=summary)


def reviewed_policies():
    rows = [policy(ident, 'https://www.city.suginami.tokyo.jp/s032/652.html',
        '自己都合取消は利用7日前までにさざんかねっとで手続き。6日前～当日利用時間までの取消は翌日から30日間、'
        '当日利用時間までに取消しない場合は90日間、抽選・空き枠申込と当選確定が制限されます。'
        '予定施設へ出向き利用料金と同額を支払う制限解除の選択肢あり。これは無条件の取消料徴収ではありません。'
        '確定済みの他の枠は利用可、利用枠の譲渡は禁止。屋内体育館に雨天自動免除を適用せず、納付済み料金の還付条件は未確認。')
        for ident in GYMS]
    rows.append(policy('tokyo-sports-018', 'https://shinjukuchuo-park.jp/futsal/',
        '予約直後から利用5日前までWeb又は管理棟窓口で取消可能。4日前以降は翌月25日～翌々月24日の1か月間、'
        '抽選・空き予約を制限。無断未使用は前12か月の回数で1～3か月。本人確認後の現地当日払い。'
        '荒天・コート状態の使用可否は管理者判断。雨天取消は電話又は窓口へ申請し、Webで取消すとペナルティ対象になるため自己取消しない。'
        '営利利用・フットサル以外の利用は禁止。'))
    rows.append(policy('tokyo-sports-019', 'https://bonfim.co.jp/ochiai/caution/',
        '15日前まで無料。メンバーは14～3日前50％、2日前・前日・当日100％、ビジターは14日前以降100％。'
        '取消フォーム送信だけでは完了せず施設の完了メールで確認、取消日から1週間以内の支払い案内あり。'
        '屋外雨天は開始2時間前（土日祝8時開始は1時間前）に施設で降雨確認した場合のみ申出可能。'
        '当日同時間数の次回予約が必要で、その新予約を実際に利用した時点で雨天取消料がなくなる条件です。'
        '既に次回予約がある場合の案内も確認。屋内に雨天免除を広げず、天気予報だけで無条件免除とは扱いません。'
        '大会・個サル開催は事前申請が必要。'))
    rows.append(policy('tokyo-wakasu-golf-links', WAKASU_TERMS,
        '台風・降雪等でプレー不能と施設が判断した場合にクローズ。開始後の急変等でクローズし、前半9ホール以内で終了なら'
        '利用料金・キャディフィは半額、クローズの代替日への振替不可。通常の自己都合取消期限・手数料は本約款では未確認。'
        '予約取消を繰り返す等の利用阻害は利用拒否の対象。雨予報だけで無条件無料とは扱いません。'))
    for ident, detail in [
        ('tokyo-venue-e8c8e3801fe4', '大ホールは6か月前全額・3か月前50％、小ホールは2か月前全額・1か月前75％・5日前50％。'
         'リハーサル・練習室・会議室・保育室は20日前全額・10日前75％・5日前50％。'),
        ('tokyo-venue-0094fb226d0e', 'ホールは2か月前全額・1か月前75％・5日前50％。')]:
        rows.append(policy(ident, HALL_CANCEL, '利用承認後の取消は原則受付なし。やむを得ない場合は事前連絡のうえ窓口で取消・還付申請。'
            + detail + '利用日を含まず前日から数える独自計算で、7月15日利用の5日前期限は7月9日、1か月前は6月14日。'
            '予約取消後は同一施設・同一日の同一コマを再予約不可。利用権の譲渡・転貸不可、通常の雨天自動免除は未確認。'))
    rows.append(policy('private-musashino-tennis-city', MUSASHINO,
        '2026年12月期限定要項では6日前から50％、当日100％。取消料未納の間は次回予約不可。'
        'プライベート及びレッスン等の使用は禁止。7日前以前の料率や屋内雨天免除は今回未確認。'
        '申込月やボール貸出可否の記載差があり、受付条件は最新の施設案内を確認。'))
    rows.append(policy('private-nishikoku', NISHI,
        '本体サイトは7日前～前日50％・当日100％。公式予約先は7日前まで0％・6日前～前日50％・当日100％と案内し、'
        '7日前の扱いが一致しないため、無料取消を確約せず予約経路・適用条件を施設へ確認。'
        '天候可否は開始1時間前に電話確認、開始後中止は時間の3分の2を経過すると成立との予約先案内あり。'
        '経過前の返金額は推測しない。契約外レッスン・営利活動で中止の場合は返金なし。'))
    rows.append(policy('private-tanashi-yunan', 'https://reserve.tennisbear.net/yunan',
        '平日は取消料なし。土日祝は5日前までなし、4日前～前日50％、当日100％。12月29日～1月3日は休日規定。'
        '利用開始時に現地で雨なら取消料不要、予報・遠距離移動だけの取消は不可。現地へ電話確認。'
        '雨天中断で30分超プレーは1時間分、30分以内は30分料金。電話予約とテニスベア予約で金額が異なる案内あり。'
        '予約後の完了連絡が必要で、予約送信だけを確定扱いしません。'))
    rows.append(policy('private-sakurada', 'https://www.tennisbear.net/place/430/info',
        '公式サイトから直接リンクされた予約先で、天候・コート不良の中止判断は1時間前、電話確認必須。'
        '一般の取消期限・手数料や雨天免除額は今回未確認。営利目的のスクール・レッスン・イベント等は禁止。'))
    return rows


REVIEWED_IDS = RECHECKS + HOLDS + [r['id'] for r in reviewed_fees()]


def main():
    fees, policies = reviewed_fees(), reviewed_policies()
    validate(fees)
    assert len(REVIEWED_IDS) == len(set(REVIEWED_IDS)) == 26
    assert len(fees) == 5 and len(policies) == 13
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
