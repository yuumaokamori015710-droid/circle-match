"""Append source-matched tariffs without changing catalog identities or prior reviews."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'outputs'))
from venues.fees import validate
from venues.sports_catalog import get_catalog, has_price
from record_venue_fee_review_20261018 import append_reviews, entry as previous_entry

CHECKED = '2026-11-07'
BASE = 'b2bd02898598d47b2e9476e120f1f834d40646c9'
CATALOGS = ROOT / 'outputs/venues/catalogs'
KOKUBUNJI = 'https://www.city.kokubunji.tokyo.jp/shisetsu/sport/tennis/1004190.html'
SHIBUYA = 'https://www.city.shibuya.tokyo.jp/shisetsu/sports-shisetsu/sports-center/'
SHIBUYA_CLOSURE = SHIBUYA + 'sportscenterkasetukousyakennsetunitomonauitibusisetunoriyoukyuusinituite.html'
KOTO = ('https://www.di-ksp.jp/wp/wp-content/uploads/'
        'R6%E5%88%A9%E7%94%A8%E6%96%99%E9%87%91%E6%94%B9%E8%A8%82%EF%BC%88%E6%96%B0%E7%A0%82%E9%81%8B%E5%8B%95%E5%A0%B4%EF%BC%89_202402HP%E5%91%A8%E7%9F%A5.pdf')
MEGURO = 'https://www.city.meguro.tokyo.jp/documents/5809/sportsguidebook.pdf'
AKIRUNO = 'https://www.city.akiruno.tokyo.jp/'
FUCHU = 'https://www.city.fuchu.tokyo.jp/shisetu/supotu/tekyujo/koyanagi.html'
HIGASHIYAMATO = 'https://www.higashiyamato-taiikukan.com/s-d%E4%B8%8A%E4%BB%B2%E5%8E%9F%E3%83%86%E3%83%8B%E3%82%B9%E3%82%B3%E3%83%BC%E3%83%88'
MUSASHINO = 'https://www.musashino.or.jp/_res/projects/default_project/_page_/001/001/569/1001569-02.pdf'
MUSASHINO_WEATHER = 'https://www.musashino.or.jp/sports/1001550/1001569.html'
KOMAE = 'https://www.komae-sponavi.net/other/'
CHOFU = 'https://www.city.chofu.lg.jp/040070/p026083.html'
HAMURA = 'https://www.city.hamura.tokyo.jp/0000000768.html'
MACHIDA = 'https://tsuruma-park.com/playfield/sports-ground/'
HOLDS = ['tokyo-venue-2b0bbd7157ff', 'tokyo-venue-c282bded258a',
         'tokyo-venue-205d87234dd3', 'tokyo-gym-a231878afdcf',
         'higashimurayama-maekawa', 'higashimurayama-undo', 'chofu-jindaiji']


def entry(ident, source, note, rows):
    return dict(previous_entry(ident, source, note, rows), checked_at=CHECKED)


def reviewed_fees():
    result = [entry('tokyo-venue-e2d803873b82', KOKUBUNJI,
        '戸倉第一の通常貸切1面1コマ2時間。市内在住・在勤・在学の個人又は市民スポーツサークル登録団体のみ。'
        '申請・支払いは市民スポーツセンター窓口。市外一般向け料金と取消・雨天還付条件は未確認。',
        [('通常貸切・登録対象者', 1600, 'テニスコート1面・2時間（市内個人・登録団体）')])]
    for ident, slug in [('shibuya-sportscenter', 'sp0_spcenter2.html'),
                        ('shibuya-nishihara', 'sp2_nishihara.html')]:
        note = ('登録利用の庭球場1面2時間、基本料金1400円。夜間照明は別途1面30分250円で、'
                '照明のみの額をコート最安値にしません。登録資格・受付時期を予約案内で確認。'
                '自己都合取消期限・取消料・雨天還付の具体的条件は今回未確認。')
        if ident == 'shibuya-sportscenter':
            note += '個人開放の1人400円とは別。仮設校舎工事によりC/D面は令和23年度まで休止、A/B面は利用可能とする現行告知あり。' + SHIBUYA_CLOSURE
        result.append(entry(ident, SHIBUYA + slug, note,
                            [('庭球場・通常貸切（照明別）', 1400, '庭球場1面・2時間（登録利用・照明別）')]))
    result.append(entry('shibuya-honmachi', SHIBUYA + 'honmachicc_sports.html',
        '本町CCの庭球場1面2時間。テニス利用は平日9～15時のみ。土日祝・平日15～17時のグラウンドや、'
        'アリーナ・スタジオの料金とは分離。事前団体登録が必要でゲスト利用不可。区外のその他団体も2人以上等の登録区分あり。'
        '取消期限・取消料・天候時還付条件は未確認。',
        [('平日9～15時の庭球場', 2000, '庭球場1面・2時間（登録団体・平日指定枠）')]))
    result.append(entry('koto-shinsuna', KOTO,
        '2025年4月1日利用承認分からの団体テニス場1面1時間料金。PDF表の団体利用欄を目視確認し、'
        '写真撮影の庭球場1400円やターゲットバードゴルフ個人料金を採用しません。平日と土日祝を表示。'
        '夜間照明の告知は運動場サッカー場の別表であり、庭球場に転用しません。登録方法と取消・雨天条件は別途確認。',
        [('平日・通常団体利用', 1100, 'テニスコート1面・1時間（団体通常）'),
         ('土日祝・通常団体利用', 1800, 'テニスコート1面・1時間（団体通常）')]))
    note = ('2026年4月の区公式スポーツ施設利用ガイド26頁。庭球場の登録団体通常貸切で、個人開放と区分を分けます。'
            '区民・区外、大人・小人、通常2時間と季節限定1時間を別単位で表示。小人は中学・高校生以下の区分。'
            '1時間枠は8月16～31日及び11月15～1月31日の最終回のみ。区外団体は抽選対象外で空き予約から。')
    rows = []
    for resident, adult, child in [('区民団体', 2400, 1200), ('区外団体', 4800, 2400)]:
        for group, amount in [('大人', adult), ('小人', child)]:
            scope = resident + '・' + group
            rows.extend([(scope + '・通常枠', amount, '庭球場1面・2時間（' + scope + '）'),
                         (scope + '・季節限定最終枠', amount // 2, '庭球場1面・1時間（' + scope + '・季節限定）')])
    result.append(entry('meguro-kumin', MEGURO, note, rows))
    for ident, source, amount in [('akiruno-yamada', '0000007644.html', 1300),
                                  ('akiruno-sogo', '0000007648.html', 1300),
                                  ('akiruno-tamamikazaki', '0000007648.html', 500)]:
        note = ('2026年10月更新の市施設案内に掲載された1面2時間のテニス通常基本料金。'
                '当日の構成員の半数以上が市内在住・在勤・在学の場合に市内料金。市外と別区分。'
                '無料の運動広場・テニス以外の施設料金は使用しません。取消・雨天還付条件は今回未確認。')
        rows = [('市内・昼間通常', amount, 'テニスコート1面・2時間（市内通常）'),
                ('市外・昼間通常', amount * 3, 'テニスコート1面・2時間（市外通常）')]
        if ident == 'akiruno-yamada':
            rows += [('市内・17時以降又は照明使用', 1500, 'テニスコート1面・2時間（市内夜間・照明使用）'),
                     ('市外・17時以降又は照明使用', 4300, 'テニスコート1面・2時間（市外夜間・照明使用）')]
            note += '夜間料金は追加照明料ではなく夜間使用料金。フットサルはテニス2面必要で、本欄はテニス1面のみ。'
        else:
            note += '総合グラウンドは12月20日～3月20日が季節休場（少年野球場・クラブハウスは別期間）。通年予約可能とは表示しません。'
        result.append(entry(ident, AKIRUNO + source, note, rows))
    result.append(entry('fuchu-koyanagi', FUCHU,
        '小柳庭球場1面1時間の基本使用料。市内・市外を分離。ナイターには照明料が別途市内650円・市外1300円加算され、'
        '基本料金だけで照明込みとは表示しません。A～D面は照明あり、E面は昼間のみ。個人・団体の事前登録が必要。',
        [('市内・基本使用料（照明別）', 400, '庭球場1面・1時間（市内・照明別）'),
         ('市外・基本使用料（照明別）', 800, '庭球場1面・1時間（市外・照明別）')]))
    result.append(entry('higashiyamato-kaminakahara', HIGASHIYAMATO,
        '指定管理者の1単位2時間の料金表。大人と中学生以下を区分。照明は別途1単位1000円でコート料金に混ぜません。'
        '中学生以下のみの利用不可で保護者同伴が必要。登録は15歳以上（中学生不可）の個人、市内外とも可能。'
        '営利目的・利用権譲渡・転貸不可。自己都合取消と雨天還付の現行詳細は今回未確認。',
        [('大人・基本使用料', 800, 'テニスコート1面・2時間（大人・照明別）'),
         ('中学生以下・保護者同伴', 400, 'テニスコート1面・2時間（中学生以下・照明別）')]))
    result.append(entry('musashino-tennis', MUSASHINO,
        '指定管理者料金表の庭球場1面2時間。市民1000円、市民以外は公式の倍額で2000円。'
        '通常利用の市内外を分離し、入場料・参加料徴収時の3倍額は通常範囲に含めません。'
        '課金して募集する場合は別の料金徴収利用規約と承認条件を確認。予約登録が必要。',
        [('市民・通常基本', 1000, '庭球場1面・2時間（市民通常）'),
         ('市民以外・通常基本', 2000, '庭球場1面・2時間（市外通常）')]))
    for ident, slug in [('komae-motoizumi', 'motoizumi_tennis/'), ('komae-higashinogawa', 'higashinogawa/')]:
        note = ('狛江市内在住・在勤・在学、12歳以上（小学生除く）の個人登録者が対象。通常1面2時間、'
                '一般1400円・高校生以下800円。高校生以下本人が申し込み高校生以下のみで使用する場合に限る。'
                '利用当日は予約者の本人確認あり。現地はキャッシュレス、現金は総合体育館の受付窓口。')
        rows = [('一般・通常枠', 1400, 'テニスコート1面・2時間（市内登録一般）'),
                ('高校生以下・対象者のみ', 800, 'テニスコート1面・2時間（高校生以下のみ）')]
        if ident == 'komae-motoizumi':
            note += '9月16～17時だけの1時間枠は一般700円・高校生以下400円で通常2時間と分離。'
            rows += [('一般・9月最終枠', 700, 'テニスコート1面・1時間（市内登録一般・9月限定）'),
                     ('高校生以下・9月最終枠', 400, 'テニスコート1面・1時間（高校生以下のみ・9月限定）')]
        result.append(entry(ident, KOMAE + slug, note, rows))
    result.append(entry('chofu-midori', CHOFU,
        '個人登録のコート1面1単位2時間。市内2400円・市外4800円で照明別。照明は30分300円。'
        '休日は10～18時のみ。営利目的利用不可。反復的に不特定多数へ参加費付き募集を行い、'
        '参加費合計がコート使用料を超える場合などの市の禁止条件を確認。',
        [('市内・通常使用', 2400, 'テニスコート1面・2時間（市内・照明別）'),
         ('市外・通常使用', 4800, 'テニスコート1面・2時間（市外・照明別）')]))
    result.append(entry('hamura-fujimi', HAMURA,
        '富士見公園を含む公園有料施設表のコート料金。6～18時は2時間600円、18～21時は3時間900円。'
        '照明は別途1時間510円。2時間と3時間を分離し、照明加算のみを施設の最安値にしません。'
        '利用登録が必要。市外割増、取消期限・取消料・雨天還付の詳細はこの案内では未確認。',
        [('昼間・2時間単位', 600, 'テニスコート1面・2時間（通常・照明別）'),
         ('18～21時・3時間のみ', 900, 'テニスコート1面・3時間（夜間・照明別）')]))
    result.append(entry('machida-tsuruma', MACHIDA,
        '鶴間公園指定管理者の硬式テニス1面2時間。市内平日1800円・土日祝2500円、市外平日3700円・土日祝5000円。'
        '他の町田市営庭球場の1040円やグラウンド料金を流用しません。照明は別途30分400円。利用登録が必要。'
        '既存の2026年11月5日確認済み取消・天候条件は変更しません。',
        [('市内・平日', 1800, 'テニスコート1面・2時間（市内・照明別）'),
         ('市内・土日祝', 2500, 'テニスコート1面・2時間（市内・照明別）'),
         ('市外・平日', 3700, 'テニスコート1面・2時間（市外・照明別）'),
         ('市外・土日祝', 5000, 'テニスコート1面・2時間（市外・照明別）')]))
    return result


def reviewed_policies():
    def policy(ident, source, text):
        return dict(id=ident, checked_at=CHECKED, status='conditional', source_url=source, summary=text)
    result = []
    for ident, slug in [('komae-motoizumi', 'motoizumi_tennis/'), ('komae-higashinogawa', 'higashinogawa/')]:
        result.append(policy(ident, KOMAE + slug,
            '利用3日前までシステム取消可。期限後は総合体育館へ連絡。取消せず未払い不使用が6回で1か月利用停止。'
            'これは予約制裁で金銭の取消料ではありません。天候・熱中症警戒等で施設が使えない場合は回数対象外。'
            '当日の可否は開始30分前に施設判断。利用者判断・使用不能による不使用等は、開始30分未満は支払不要、'
            '2時間枠の30分以上1時間30分未満は半額。1時間枠の30分以上の割合や自己都合の還付額は未確認。'))
    result.append(policy('musashino-tennis', MUSASHINO_WEATHER,
        '8時45分枠は当日8時30分、それ以降は開始2時間前に天候による可否を決定。施設中止なら取消連絡不要。'
        '中止決定時に利用時間の半分（1時間）を超過した場合は返金対象外。施設が利用者判断とした場合、'
        '不使用は各回開始60分以内までに総合体育館へ連絡しないと返金対象外。通常自己都合の取消期限・返金率は未確認。'))
    result.append(policy('meguro-kumin', MEGURO,
        '庭球場の未払い予約は利用4日前までペナルティなしで取消可能、3日前から直前取消。'
        '開始15分経過後の無連絡不使用は無断取消。無断1回又は直前取消3回で事象発生から3か月後まで予約・抽選不可。'
        '開始時刻以後の取消や天候等やむを得ない中止は、権利消滅前に施設へ連絡が必要。'
        'これは予約制裁で取消料ではありません。屋内施設の還付率を庭球場へ適用せず、庭球場の具体的還付率は未確認。'))
    result.append(policy('fuchu-koyanagi', FUCHU,
        '雨天でも一律閉場せず、天候やコート状態により使用しなかった場合は施設へ連絡（後日でも可）。'
        '雨天不使用分は公共施設予約システムの振替機能で次回利用分へ充当。自動現金返金とは表示しません。'
        '自己都合取消の期限・取消料・還付率はこの施設案内では未確認。'))
    result.append(policy('chofu-midori', CHOFU,
        '前日までシステム取消可能。当日は開始前までに現地連絡し、当日取消は1か月の新規予約停止、'
        '無連絡は3か月停止。これは予約制裁で取消料ではありません。天候可否・取消は開始前までに現地確認。'
        '利用時間の半分に達する前に現地降雨で使用できない場合は制裁なし。ただし雨でも取消連絡は必要。金銭の還付率は未確認。'))
    return result


REVIEWED_IDS = HOLDS + [row['id'] for row in reviewed_fees()]


def main():
    fees, policies = reviewed_fees(), reviewed_policies()
    validate(fees)
    assert len(REVIEWED_IDS) == len(set(REVIEWED_IDS)) == 24
    assert len(fees) == 17 and len(policies) == 6
    rows = {r['id']: r for r in get_catalog()['courts']}
    assert set(REVIEWED_IDS) <= rows.keys()
    for fee in fees:
        row = rows[fee['id']]
        if has_price(row) and row.get('fee_checked_at') != CHECKED:
            raise ValueError('Refusing to replace priced venue: ' + fee['id'])
    for name, additions in [('fee_plans.json', fees), ('cancellation_policies.json', policies)]:
        old = {r['id']: r for r in json.loads((CATALOGS / name).read_bytes())}
        for row in additions:
            if row['id'] in old and old[row['id']] != row:
                raise ValueError('Refusing to replace prior review: ' + row['id'])
    append_reviews(CATALOGS / 'fee_plans.json', fees)
    append_reviews(CATALOGS / 'cancellation_policies.json', policies)
    print(json.dumps(dict(reviewed=24, prices_added=17, policies_added=6, holds=7)))


if __name__ == '__main__':
    main()
