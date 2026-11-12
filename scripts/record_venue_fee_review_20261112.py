"""Append the November 12 official-source venue review without replacing records."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'outputs'))
from venues.fees import validate
from venues.sports_catalog import get_catalog, has_price
from record_venue_fee_review_20261018 import append_reviews, entry as previous_entry
from record_venue_fee_review_20261110 import SCHOOL_FEE, SCHOOL_UNIT

CHECKED = '2026-11-12'
BASE = 'ec5e9a827dbd59c268fd294dc4558c8378003bbe'
CATALOGS = ROOT / 'outputs/venues/catalogs'
TAITO = 'https://www.city.taito.lg.jp/kusei/online/yoyaku/riyosyaguide.files/'
HIGASHIMURAYAMA = 'https://www1.g-reiki.net/city.higashimurayama/reiki_honbun/'
MITSUGI = ('https://musashimurayama-gym.jp/wp/wp-content/uploads/'
           '%E5%B1%8B%E5%A4%96%E4%BD%93%E8%82%B2%E6%96%BD%E8%A8%AD%E6%96%99%E9%87%91%E8%A1%A8.pdf')
CHOFU = 'https://www.city.chofu.lg.jp/040070/p026085.html'
HOLDS = ['tokyo-venue-205d87234dd3']
RECHECKS = ['tokyo-gym-48e959a72b2e']
PUBLIC = ['taito-riverside', 'higashimurayama-maekawa', 'higashimurayama-undo',
          'musashimurayama-mitsugi', 'chofu-jindaiji']
SCHOOLS = {
    'eea59ce6923d': '戸山', '57414ccf6c4d': '新宿山吹', 'e74da0836c03': '新宿',
    '187be921c4be': '総合芸術', 'a281995e4f1e': '杉並工科', '882c590673c9': '杉並総合',
    '43c6aa524ded': '杉並', '031924c4f707': '荻窪', 'ce652014a3a2': '西',
    '31a6248da498': '向丘', '4e6511f4c1f6': '小石川中等教育学校', '01503f65b42c': '忍岡',
    '0582de262d45': '晴海総合', '1cd77d86e2e2': '稔ヶ丘', '832d67b2d40a': '鷺宮',
    'd6ed96b95fae': '江東商業', '1b2892a311a5': '科学技術', 'f72fc267d907': '第三商業',
    'a87258f3db56': '第一商業',
}
HARD_ONLY = {'57414ccf6c4d', '187be921c4be', '882c590673c9', '43c6aa524ded',
             '4e6511f4c1f6', '832d67b2d40a'}


def entry(ident, source, note, rows):
    return dict(previous_entry(ident, source, note, rows), checked_at=CHECKED)


def reviewed_fees():
    rows = [entry(PUBLIC[0], TAITO + '3.pdf',
        '庭球場1面2時間。入場料を徴収しない通常利用の料金で、区外利用者は区内料金の5割増。'
        '照明は30分400円が別途必要。入場料徴収時の割増・適用条件は別途確認。'
        '利用者登録が必要。体育館の料金や時間枠とは異なります。',
        [(f'{area}・{day}', amount, f'庭球場1面・2時間（{area}・照明別）')
         for area, amounts in [('区内', (1200, 1600)), ('区外', (1800, 2400))]
         for day, amount in zip(('平日', '土日祝'), amounts)])]
    for ident in PUBLIC[1:3]:
        rows.append(entry(ident, HIGASHIMURAYAMA + 'f200RG00000618.html',
            '東村山市スポーツ施設条例別表第2。庭球場1面1時間の使用料。'
            '一般と中学生以下、昼間と夜間を分離。予約は原則2時間単位で、表示額は1時間の法定料金。'
            '使用許可が必要。営利目的等の利用制限と利用権の譲渡・転貸禁止があります。',
            [(f'{category}・{period}', amount, f'庭球場1面・1時間（{category}・{period}）')
             for category, amounts in [('一般', (450, 1450)), ('中学生以下', (150, 1150))]
             for period, amount in zip(('昼間', '夜間'), amounts)]))
    rows.append(entry(PUBLIC[3], MITSUGI,
        '令和8年7月1日施行。市外料金は市内の倍額。通常は1面2時間、'
        '4・5・9・10月の17～18時のみ1時間枠。6～8月の最終枠は17～19時、11～3月は17時まで。'
        '市内区分は構成員の過半数が市内在住・在勤・在学の登録団体。庭球場は4名以上、代表者18歳以上。'
        '三ツ木には夜間照明なし。既存の雨天・取消条件は別欄で確認。',
        [(f'{area}・{slot}', amount, f'庭球場1面・{duration}（{area}）')
         for area, amounts in [('市内', (1020, 510)), ('市外', (2040, 1020))]
         for slot, duration, amount in zip(('通常枠', '4・5・9・10月17～18時'),
                                           ('2時間', '1時間・春秋17～18時枠'), amounts)]))
    rows.append(entry(PUBLIC[4], CHOFU,
        '事前に個人登録が必要。1単位は1面2時間。人工芝A・C面とクレイB面、市内と市外を分離。'
        '当日に利用カードを提示して支払い。休日・1～3月は8～10時、10～3月は16～18時の枠なし。'
        '準備・片付けを使用時間に含みます。',
        [(f'{surface}・{area}', amount, f'{surface}1面・2時間（{area}）')
         for surface, amounts in [('砂入り人工芝A・C面', (700, 1400)), ('クレイB面', (400, 800))]
         for area, amount in zip(('市内', '市外'), amounts)]))
    for suffix in SCHOOLS:
        sport = '硬式のみ' if suffix in HARD_ONLY else '硬式・軟式'
        rows.append(entry('school-' + suffix, SCHOOL_FEE,
            f'令和8年度の都立学校開放に掲載された屋外庭球場（{sport}）。無料は昼間の施設使用料のみ。'
            '都内在住・在勤・在学者が主な10人以上の非営利の登録団体が対象で、責任者は満20歳以上。'
            '登録名簿に載る者の練習・練習試合が原則で、不特定多数の活動は不可。保険加入が必要。'
            '照明等の光熱費・保険料は含みません。開放日時と学校別条件は公式一覧で確認。',
            [('昼間・施設使用料', 0, SCHOOL_UNIT)]))
    return rows


def reviewed_policies():
    def policy(ident, source, summary):
        return dict(id=ident, checked_at=CHECKED, status='conditional', source_url=source, summary=summary)

    rows = [policy(PUBLIC[0], TAITO + '4.pdf',
        '支払後の庭球場取消は利用15日前まで8割、7日前まで5割、6日前～当日は還付なし。'
        '窓口決済は窓口で取消、オンライン決済のみならシステムで取消・還付申請。併用時は先にオンライン分を処理。'
        '決済から185日経過後や雨天等で利用不可の場合は窓口手続き。使用承認書等の必要書類を要確認。'
        '照明料は別規定。雨天の還付率と照明料の還付率はこの案内では未確認。')]
    for ident in PUBLIC[1:3]:
        rows.append(policy(ident, HIGASHIMURAYAMA + 'f200RG00001117.html',
            '取消は使用予定日の前日までに手続き。期限までに取り下げなかった場合、翌月1日から末日まで'
            '当該施設の抽選申込が不可。全施設の予約停止ではありません。'
            '支払済み使用料は原則不還付ですが、利用者の責任によらず使用不可、または期限内の取消等を市長が認める場合は還付対象。'
            '還付請求書の提出が必要。雨天判断の具体的な連絡期限・返金割合は未確認。'))
    rows.append(policy(PUBLIC[4], CHOFU,
        '前日までシステムで取消可。当日は現地に連絡し、開始前なら新規予約1か月停止、開始後の連絡・無断は3か月停止。'
        '天候による使用可否確認・取消連絡も開始前に現地へ。利用時間の半分に達する前に現地で雨が降り使用不可ならペナルティなし。'
        '雨天でも連絡は必要。クレイは前日までの天候・霜等で晴天でも使用不可の場合あり。金銭の取消料・返金率は未確認。'))
    return rows


REVIEWED_IDS = HOLDS + RECHECKS + [row['id'] for row in reviewed_fees()]


def main():
    fees, policies = reviewed_fees(), reviewed_policies()
    validate(fees)
    assert len(REVIEWED_IDS) == len(set(REVIEWED_IDS)) == 26
    assert len(fees) == 24 and len(policies) == 4
    rows = {r['id']: r for r in get_catalog()['courts']}
    assert set(REVIEWED_IDS) <= rows.keys()
    assert {r['id'] for r in policies} <= set(REVIEWED_IDS)
    for suffix, name in SCHOOLS.items():
        school = name if name.endswith('学校') else name + '高等学校'
        assert '都立' + school + ' テニスコート' in rows['school-' + suffix]['name']
    for fee in fees:
        if has_price(rows[fee['id']]) and rows[fee['id']].get('fee_checked_at') != CHECKED:
            raise ValueError('Refusing to replace priced venue: ' + fee['id'])
    for name, additions in [('fee_plans.json', fees), ('cancellation_policies.json', policies)]:
        old = {r['id']: r for r in json.loads((CATALOGS / name).read_bytes())}
        for row in additions:
            if row['id'] in old and old[row['id']] != row:
                raise ValueError('Refusing to replace prior review: ' + row['id'])
    append_reviews(CATALOGS / 'fee_plans.json', fees)
    append_reviews(CATALOGS / 'cancellation_policies.json', policies)
    print(json.dumps(dict(reviewed=len(REVIEWED_IDS), prices_added=len(fees), policies_added=len(policies))))


if __name__ == '__main__':
    main()
