"""Append scoped official tariffs; preserve prior reviews and one sourced closure."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'outputs'))
from venues.fees import validate
from venues.sports_catalog import get_catalog, has_price
from record_venue_fee_review_20261018 import append_reviews, entry as old_entry

CHECKED = '2026-11-04'
BASE = '0aea1414be40f63eafad046d62d2461e4d5b1f77'
CATALOGS = ROOT / 'outputs/venues/catalogs'
OTA = 'https://www.city.ota.tokyo.jp/shisetsu/'
OTA_GUIDE = OTA + 'uguisunet_annai/ugu.html'
OTA_CULTURE = OTA + 'uguisunet_annai/bunka-c_yoyaku-henkou.html'
MEGURO = 'https://www.city.meguro.tokyo.jp/'
MEGURO_REGISTER = MEGURO + 'toubu/kusei/onlineservice/touroku.html'
MEGURO_BOOKING = MEGURO + 'toubu/kusei/onlineservice/communityroom.html'
MEGURO_CANCEL = MEGURO + 'toubu/kusei/onlineservice/shiyouryou.html'
MEETINGS = [
    ('tokyo-venue-d40445daf945', 'hall/community/life_kaigi0930.html', '会議室', [860, 1700, 2500], [980, 2100, 3100], False),
    ('tokyo-venue-9f1e6da622bb', 'hall/rokugosyuukaishitsu/daiichishukaishitsu.html', '第一集会室', [1700, 2900, 4700], [1700, 3500, 5600], True),
    ('tokyo-venue-a01a8272f849', 'hall/sannou_k/sannokaikan_shukaishitsu.html', '集会室', [1500, 2900, 4300], [1800, 3500, 5100], False),
    ('tokyo-venue-acafbf43b734', 'hall/tamagawasyuukai/tamagawa1.html', '第一集会室', [740, 1500, 2200], [860, 1700, 2600], False),
    ('tokyo-venue-f756c371fa95', 'hall/araijuku_k/araijukukaikan_shukaishitsu.html', '集会室', [3000, 4500, 7500], [3000, 5400, 9000], True),
]
CULTURE = [
    ('tokyo-venue-3dad1de4b1e7', 'minemachi', '体育室', [1700, 1400, 1400, 1700]),
    ('tokyo-venue-52d36d518953', 'haneda', '第一集会室', [1300, 1800, 1800]),
    ('tokyo-venue-8d8fb7de1c48', 'haginaka', '体育室', [1500, 1200, 1200, 1500]),
]
KAM = 'tokyo-venue-7f86d45f6b38'
KAM_FEES = OTA + 'hall/shisetu_kamkamshinkamata.files/sisetusiyouryou3.pdf'
KAM_GUIDE = 'https://shinkamata.jp/guide/'
KAM_CANCEL = ('https://shinkamata.jp/wp/wp-content/themes/actio/img/pdf/'
              '%E5%88%A9%E7%94%A8%E5%8F%96%E6%B6%88%E7%94%B3%E8%AB%8B%E6%9B%B8%E3%80%90%E8%A8%98%E5%85%A5%E4%BE%8B%E3%80%91.pdf')
MEGURO_ROOMS = [
    ('tokyo-venue-17c00cfd90cb', 'chuocho', 'B102', [2800, 2900, 2900, 2900]),
    ('tokyo-venue-51e711229a72', 'kyoiku_kumin_center', '701', [3600, 3700, 3700, 3700]),
    ('tokyo-venue-d8e3b629e732', 'higashiyama', '201', [3400, 3500, 3500, 3500]),
    ('tokyo-venue-cf9e1adb9414', 'kyoiku_megurohonmachi', '303', [2800, 2900, 2900, 2900]),
    ('tokyo-venue-13e7f69454a5', 'kyoiku_midorigaoka', '本館201', [4800, 5000, 5000, 5000]),
]
SHINKAWA = 'tokyo-venue-8e6c0f81a52c'
SHINKAWA_PAGE = 'https://www.city.mitaka.lg.jp/c_service/079/079233.html'
SHINKAWA_RULES = 'https://www.city.mitaka.lg.jp/c_service/079/079234.html'
HOLDS = ['tokyo-venue-2b0bbd7157ff', 'tokyo-venue-c282bded258a',
         'tokyo-venue-205d87234dd3', 'tokyo-gym-a231878afdcf', 'tokyo-gym-aa77f48e78d0']
CLOSED = 'tokyo-gym-aa77f48e78d0'
CLOSURE_SOURCE = 'https://www.city.fuchu.tokyo.jp/shisetu/supotu/taikukan/honshuku.html'
CLOSURE_NOTE = ('本宿体育館はトイレ改修工事で2026年11月～2027年2月末まで全館休館予定（期間変更の場合あり）。'
                '2026年10月と2027年3月も貸切予約不可・一般公開のみ。旧貸切料金を現在予約可能な額として追加せず、通常検索から除外します。')
CLOSURE_EVIDENCE = {'title': '府中市公式：本宿体育館の全館休館・貸切予約不可期間', 'url': CLOSURE_SOURCE}
REVIEWED_IDS = HOLDS + [SHINKAWA, KAM] + [r[0] for r in MEETINGS + CULTURE + MEGURO_ROOMS]


def entry(ident, source, note, rows):
    return dict(old_entry(ident, source, note, rows), checked_at=CHECKED)


def reviewed_fees():
    result = []
    for ident, path, room, weekday, holiday, short in MEETINGS:
        periods = ([('午前9～12時', '3時間'), ('午後13～16時30分', '3時間30分'), ('夜間17時30分～21時30分', '4時間')]
                   if short else [('午前9～12時', '3時間'), ('午後13～17時', '4時間'), ('夜間18～22時', '4時間')])
        note = (room + '単室・区内通常料金のみ。全室の最安値ではありません。平日と土日祝を明示し、異なる時間数は分離。'
                '区外の約2割増は正確な適用額を確認できないため算出せず、備品・営利目的の割増・減免・全日・他室料金を含みません。'
                'うぐいすネットは本人確認を伴う窓口登録が必要（個人16歳以上、区内在勤在学も区内扱い）。'
                '登録・予約・取消方法：' + OTA_GUIDE)
        if ident == 'tokyo-venue-acafbf43b734':
            note += 'この室の申込は施設へ直接行う案内です。一般のWeb予約可とはしません。'
        result.append(entry(ident, OTA + path, note,
                            [(room + ' / ' + day + ' / ' + label, amount, room + '・' + duration + '（区内通常・' + day + '）')
                             for day, values in [('平日', weekday), ('土日祝', holiday)]
                             for (label, duration), amount in zip(periods, values)]))
    for ident, slug, room, values in CULTURE:
        gym = room == '体育室'
        periods = ([('午前9～12時', '3時間'), ('午後A13～15時30分', '2時間30分'), ('午後B16～18時30分', '2時間30分'), ('夜間19～22時', '3時間')]
                   if gym else [('午前9～12時', '3時間'), ('午後13～17時', '4時間'), ('夜間18～22時', '4時間')])
        note = (room + '単室の公表通常料金。全館の最安値ではなく、個人入場・他室・備品・減免を含みません。'
                '午前・午後・夜間の実時間数を分離し、1時間単価に換算しません。うぐいすネットの窓口利用者登録が必要。'
                '区外利用可否や割増適用額を推測しません。抽選対象団体と一般の先着予約は別条件。予約方法：' + OTA_CULTURE)
        if slug == 'haneda':
            note += '掲載住所の羽田1-18-13にある第一集会室のみ。羽田4-11-1の体育室料金は別棟のため採用しません。'
        elif slug == 'haginaka':
            note += '体育室はバレー1面・バドミントン2面等。正式なバスケットコートはとれません。'
        else:
            note += '体育室はバレー1面・バドミントン2面等。天井が低く種目制限あり、利用可否を事前確認。'
        result.append(entry(ident, OTA + 'bunkacenter/' + slug + 'bunkacenter.html', note,
                            [(room + ' / ' + label, amount, room + '・' + duration + '（通常）')
                             for (label, duration), amount in zip(periods, values)]))
    note = ('第一集会室（2階・定員30名）単室の通常料金のみ。全館・多目的室・音楽スタジオ料金ではありません。'
            '午前3時間、午後夜間4時間を分離。全日・備品・減免を含みません。'
            '市の現行ページが案内する料金PDFと指定管理者案内を確認。区内の団体・個人のうぐいすネット登録・予約が必要。'
            '区外向け料金を推測しません。準備・原状回復を含む。利用資格：' + KAM_GUIDE)
    result.append(entry(KAM, KAM_FEES, note,
                        [('第一集会室 / ' + label, amount, '第一集会室・' + duration + '（区内通常）')
                         for (label, duration), amount in zip([('午前9～12時', '3時間'), ('午後13～17時', '4時間'), ('夜間18～22時', '4時間')], [1600, 2100, 2100])]))
    for ident, slug, room, values in MEGURO_ROOMS:
        note = (room + '単室・その他団体（利用者登録のみ）の料金。全室の最安値ではありません。区外のみの団体・個人も利用者登録可。'
                '区民の一般団体・登録団体の割引料金、備品、他室を混ぜません。午前3時間と他の2時間30分枠を分離。'
                'その他団体の空き予約は利用月の1か月前の月初から。利用内容・音振動等の室別制限に従い、球技場利用料へ流用しません。'
                '準備片付け込み。登録：' + MEGURO_REGISTER + ' 申込：' + MEGURO_BOOKING)
        result.append(entry(ident, MEGURO + 'shougaigakushuu/shisetsu/bunkakouryuu/' + slug + '.html', note,
                            [(room + ' / ' + label, amount, room + '・' + duration + '（その他団体）')
                             for (label, duration), amount in zip([('午前9～12時', '3時間'), ('午後1・12時30分～15時', '2時間30分'),
                                                                  ('午後2・15時30分～18時', '2時間30分'), ('夜間18時30分～21時', '2時間30分')], values)]))
    note = ('公式施設案内が無料開放と明示する球技場1面。無料の登録料を施設料に流用したものではありません。'
            '貸切予約には団体登録・承認が必要で、フットサル等6人以上、サッカー等9人以上、競技メンバーの半数以上が市内在住在勤在学。'
            '2026年10月以降の団体要件を使用。営利行為不可。2時間枠と冬季15～16時30分の1時間30分枠を分離。'
            '第2土曜・第4日曜は自由開放で団体予約不可、当日予約不可。予約枠は抽選当選を含め月5区分まで。'
            '現行利用方法：' + SHINKAWA_RULES)
    result.append(entry(SHINKAWA, SHINKAWA_PAGE, note,
                        [('球技場 / 通常予約枠', 0, '球技場1面・2時間（登録承認団体・無料）'),
                         ('球技場 / 冬季最終15～16時30分', 0, '球技場1面・1時間30分（登録承認団体・無料）')]))
    return result


def reviewed_policies():
    def policy(ident, source, summary):
        return dict(id=ident, checked_at=CHECKED, status='conditional', source_url=source, summary=summary)
    summary = ('支払前は予約システム、支払後は利用施設窓口で取消手続き。自己都合は原則還付なしだが申請日・理由による例外あり。'
               '施設別の還付期限・割合は共通案内だけでは確定できないため推測せず施設確認。還付には承認書兼領収書・印鑑等が必要。'
               '公園施設だけの雨天全額還付や直前取消ペナルティをこの屋内施設へ流用しません。屋内の通常雨天免除は未確認。')
    result = [policy(ident, OTA_GUIDE, summary) for ident, *_ in MEETINGS + CULTURE]
    result.append(policy(KAM, KAM_CANCEL,
                         '現行指定管理者案内がリンクする取消申請書記入例では30日以上前は100%返金、前日・当日は返金なし。'
                         '2～6日前・7～29日前は部分還付の欄がありますが、抽出表の対応が不明瞭のため割合を推測しません。'
                         '器具は使用時間前までの取消申請書提出で全額返金。窓口へ承認書（領収書付）・登録カード・印鑑等が必要。'
                         '変更予約の取消対象日は変更前の最初の利用日。通常雨天免除は未確認。案内：' + KAM_GUIDE))
    summary = ('自己都合の還付は申請日と利用日の間に20日あれば全額、10日なら75%、5日なら50%、それ未満はなし。'
               '両端の日を含めないため単純な「5日前まで」とは異なり、休館日は直前開館日が期限。'
               '現金払は承認書・領収書を持参し利用施設窓口で取消・還付申請。カード払はシステムで取消後に還付操作（窓口不可）。'
               'コミュニティルームは区内の警戒レベル3相当以上の警報、警報級予報かつ鉄道計画運休、避難所設置等で原則利用開始前の申出により全額還付。'
               'カード払の災害還付は自己取消せず施設へ連絡。通常の雨だけで全額免除とはしません。')
    result += [policy(ident, MEGURO_CANCEL, summary) for ident, *_ in MEGURO_ROOMS]
    return result


def update_closure():
    path = CATALOGS / 'tokyo_expansion.json'
    original = path.read_text(encoding='utf-8')
    rows = json.loads(original)
    row, = [r for r in rows if r['id'] == CLOSED]
    before = json.loads(json.dumps(row))
    row.update(availability_status='SUSPENDED', availability_note=CLOSURE_NOTE, checked_at=CHECKED)
    if CLOSURE_EVIDENCE not in row['sources']:
        row['sources'].append(CLOSURE_EVIDENCE)
    if row == before:
        return
    def block(value):
        return '\n'.join('  ' + line for line in json.dumps(value, ensure_ascii=False, indent=2).splitlines())
    assert original.count(block(before)) == 1
    rendered = original.replace(block(before), block(row), 1)
    assert json.loads(rendered) == rows
    path.write_text(rendered, encoding='utf-8')


def main():
    fees, policies = reviewed_fees(), reviewed_policies()
    validate(fees)
    assert len(REVIEWED_IDS) == len(set(REVIEWED_IDS)) == 20
    assert len(fees) == 15 and len(policies) == 14 and len(HOLDS) == 5
    catalog = {r['id']: r for r in get_catalog()['courts']}
    assert set(REVIEWED_IDS) <= catalog.keys()
    for fee in fees:
        if catalog[fee['id']].get('fee_checked_at') != CHECKED and has_price(catalog[fee['id']]):
            raise ValueError('Refusing to replace priced venue: ' + fee['id'])
    for name, additions in [('fee_plans.json', fees), ('cancellation_policies.json', policies)]:
        existing = {r['id']: r for r in json.loads((CATALOGS / name).read_text(encoding='utf-8'))}
        for row in additions:
            if row['id'] in existing and existing[row['id']] != row:
                raise ValueError('Refusing to replace prior review: ' + row['id'])
    update_closure()
    append_reviews(CATALOGS / 'fee_plans.json', fees)
    append_reviews(CATALOGS / 'cancellation_policies.json', policies)
    print(json.dumps(dict(reviewed=20, prices_added=15, policies_added=14, holds=5)))


if __name__ == '__main__':
    main()
