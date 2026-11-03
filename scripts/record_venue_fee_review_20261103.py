"""Append scoped official tariffs and one explicitly sourced closure correction."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'outputs'))
from venues.fees import validate
from venues.sports_catalog import get_catalog, has_price
from record_venue_fee_review_20261018 import append_reviews, entry as old_entry
from record_venue_fee_review_20261102 import HOLDS as PREVIOUS_HOLDS

CHECKED = '2026-11-03'
BASE = '8ecf2edb4f75c62026079d52b1621b863390120b'
CATALOGS = ROOT / 'outputs/venues/catalogs'
KOTO = [
    ('tokyo-venue-13c10707fc3b', 'kameido', 'shisetsu-bunka', '第1会議室', [2000, 4100, 5150]),
    ('tokyo-venue-92c99e38e33e', 'furuishiba', 'shisetsu', '第1会議室', [1800, 3700, 4550]),
    ('tokyo-venue-22803d6ec704', 'higashiojima', 'shisetsu', '第1会議室', [1800, 3700, 4550]),
    ('tokyo-venue-1cb442e20203', 'morishita', 'shisetsu', '第1会議室', [1800, 3700, 4550]),
    ('tokyo-venue-0d428ad0eed9', 'koto', 'shisetsu', '第1会議室', [1800, 3700, 4550]),
    ('tokyo-venue-8cc9f3611320', 'sunamachi', 'shisetsu', '第1会議室', [1800, 3700, 4550]),
    ('tokyo-venue-f4279ddf1eb4', 'toyosu', 'shisetsu', '第1研修室', [1300, 2700, 3700]),
]
PERIODS = [('午前9～12時', '3時間'), ('午後13～17時', '4時間'), ('夜間18～22時', '4時間')]
KOTO_APPLY = 'https://www.kcf.or.jp/koto/shisetsu/apply/'
SUMIDA_ROOT = 'https://www.city.sumida.lg.jp/sisetu_info/tamokuteki/communitykaikan/'
SUMIDA_GUIDE = 'https://www.city.sumida.lg.jp/sisetu_info/tamokuteki/tiikisyuukaizyo.html'
SUMIDA_RULES = 'https://www.city.sumida.lg.jp/wkg/reiki_int/reiki_honbun/g108RG00000288.html'
SUMIDA = [
    ('tokyo-venue-39dcf27aa5d1', 'umewakabashi', '多目的室', [2200, 2900, 2900]),
    ('tokyo-venue-5cc27fca9da0', 'yokokawa', '和室25畳', [2600, 3400, 3400, 1700]),
]
CLOSED = 'tokyo-venue-5fe09db3d869'
CLOSURE_SOURCE = SUMIDA_ROOT + 'index.html'
CLOSURE_NOTE = ('東駒形コミュニティ会館は修繕工事で2026年10月10日～12月20日全館休館。'
                '集会室・図書室は2027年2月16日まで、体育室は2月28日まで休室予定。'
                '工事状況により変更あり。旧集会室料金を現在予約可能な料金として追加せず、通常検索から除外します。')
CLOSURE_EVIDENCE = {'title': '墨田区公式：東駒形コミュニティ会館の大規模修繕休館', 'url': CLOSURE_SOURCE}
TRACK = 'tokyo-venue-689b7f628626'
TRACK_FEES = 'https://tama-sports.com/wp/images/%E9%99%B8%E4%B8%8A%E7%AB%B6%E6%8A%80%E5%A0%B4.docx-1.pdf'
TRACK_PAGE = 'https://tama-sports.com/facility/tamahigashi'
TAMA_GUIDE = 'https://tama-sports.com/wp/images/%E3%82%B9%E3%83%9D%E3%83%BC%E3%83%84%E6%96%BD%E8%A8%AD%E3%81%AE%E5%88%A9%E7%94%A8%E6%89%8B%E5%BC%95%E3%81%8D20260525.pdf'
BASEBALL_PAGE = 'https://tama-sports.com/facility/baseball'
LIGHTING_NOTICE = 'https://www.city.tama.lg.jp/kenkofukushi/1008238/sports/riyou/index.html'
BASEBALL = [
    ('tokyo-venue-5623e0c1f690', '一本杉公園野球場', [8370, 16740]),
    ('tokyo-venue-1dcd0e1458df', '諏訪北公園野球場', [2080, 4160]),
    ('tokyo-venue-f36637b84638', '関戸公園野球場', [2080, 4160]),
]
HACHIOJI_HOLDS = ['tokyo-venue-456ad6cd0311', 'tokyo-venue-40fd2672b512']
HOLDS = PREVIOUS_HOLDS + HACHIOJI_HOLDS + [CLOSED]
REVIEWED_IDS = HOLDS + [r[0] for r in KOTO + SUMIDA + BASEBALL] + [TRACK]


def entry(ident, source, note, rows):
    return dict(old_entry(ident, source, note, rows), checked_at=CHECKED)


def koto_url(slug, section, page):
    return 'https://www.kcf.or.jp/' + slug + '/' + section + '/' + page + '/'


def reviewed_fees():
    result = []
    for ident, slug, section, room, values in KOTO:
        use = koto_url(slug, section, 'use')
        note = (room + '単室の通常料金のみで、全室の最安値ではありません。午前3時間と午後・夜間4時間を分離。'
                '区内外利用可・営利目的不可。会議室等は団体利用で、一般団体登録は2名以上・代表者18歳以上（高校生不可）。'
                '抽選・ネット予約は事前窓口登録が必要で、区内登録は抽選優先。準備片付け込み、設備・他室・延長は別。'
                '入場料・受講料等が1回1500円を超えると本番時間帯に5割増となる場合があり、適用は施設確認。'
                '不特定多数対象の集会・販売目的は不可。ダンス・軽体操等の禁止事項は室別に要確認。'
                '利用条件：' + use + ' 登録：' + KOTO_APPLY)
        result.append(entry(ident, koto_url(slug, section, 'fee'), note,
                            [(room + ' / ' + period, amount, room + '・' + duration + '（通常・割増なし）')
                             for (period, duration), amount in zip(PERIODS, values)]))
    for ident, slug, room, values in SUMIDA:
        periods = [('午前9～12時', '3時間'), ('午後13～17時', '4時間'), ('夜間17～21時', '4時間')]
        if slug == 'yokokawa':
            periods.append(('夜間B19～21時', '2時間'))
        note = (room + '単室の通常料金。児童向け体育室の料金ではなく、体育館・球技利用料へ流用しません。'
                '3時間・4時間・2時間は分離し、他室・設備・前後1時間の延長料金を含みません。営利目的不可。'
                '区民は3か月前、区民以外は2か月前の月の1日から、利用5日前まで申込。減免は申請・承認が必要で通常料金に混ぜません。'
                '利用条件：' + SUMIDA_GUIDE)
        if slug == 'yokokawa':
            note += '学童利用のため平日は午前・夜間Bのみ、学校休業日は夜間Bのみ。土曜日も平日扱い。'
        else:
            note += '窓口・電話で仮予約可。Web仮予約は利用実績のある登録者に限定。運営者案内：https://sumida-umecomi.net/meeting_room/'
        result.append(entry(ident, SUMIDA_ROOT + slug + '/syuukaijyo.html', note,
                            [(room + ' / ' + period, amount, room + '・' + duration + '（通常）')
                             for (period, duration), amount in zip(periods, values)]))
    note = ('競技場貸切の公表基本料金のみ。午前9～12時3時間8370円、午後13～17時4時間12560円、全日9～17時8時間20930円を分離。'
            '附帯設備・会議室・個人開放料金を含みません。入場料等を徴収する場合は最高入場料×100が別途加算。'
            '貸切利用条件は施設への確認が必要で、掲載は利用資格・空き・芝生利用の保証ではありません。夜間照明なし。'
            '現行案内がリンクする2020年4月改定PDFを確認。個人開放では芝生内立入不可。利用条件：' + TRACK_PAGE)
    result.append(entry(TRACK, TRACK_FEES, note,
                        [('競技場貸切 / ' + period, amount, '競技場貸切・' + duration + '（入場料加算・設備別）')
                         for (period, duration), amount in zip([('午前9～12時', '3時間'), ('午後13～17時', '4時間'), ('全日9～17時', '8時間')], [8370, 12560, 20930])]))
    for ident, name, values in BASEBALL:
        note = (name + '1面・通常2時間枠の大人一般団体の料金のみ。市内・市外を分離。10名以上の団体登録が必要。'
                '市内は半数以上が市内在住在勤在学、代表者も原則市内在住在勤。名簿外利用不可。'
                '子ども・障害者団体の減額、照明・放送・スコアボードは含みません。日没による1時間枠は別条件で料金半額。'
                '市外団体の随時申込は前月16日から。料金は空き・大会利用の承認を保証しません。'
                '施設別の大人料金を運営者表と照合：' + BASEBALL_PAGE)
        if name == '一本杉公園野球場':
            note += '市は夜間照明の稼働終了を別途告知。終了詳細本文の取得ができず、旧ナイター併用額は掲載しません。告知：' + LIGHTING_NOTICE
        result.append(entry(ident, TAMA_GUIDE, note,
                            [(name + ' / ' + group, amount, '野球場1面・2時間（' + group + '・大人一般・照明別）')
                             for group, amount in zip(['市内登録団体', '市外登録団体'], values)]))
    return result


def reviewed_policies():
    def policy(ident, source, summary):
        return dict(id=ident, checked_at=CHECKED, status='conditional', source_url=source, summary=summary)
    result = [policy(ident, koto_url(slug, section, 'use'),
                     room + '等の一般室は支払済取消を14日前21時までに手続きすると全額、7日前21時まで半額、それ以降返金なし。'
                     '利用承認書・代表者印を持参して利用館窓口で手続き。期限が休館日なら直前の開館日まで。'
                     '返金2万円超は口座振込で振込手数料は利用者負担。12か月前予約のホール用6か月・4か月期限は一般室へ適用しません。'
                     '通常の雨天免除は未確認。災害避難所・選挙利用で承認内容変更となる場合がありますが、還付率を推測しません。')
              for ident, slug, section, room, _ in KOTO]
    result += [policy(ident, SUMIDA_RULES,
                      '地域集会室は利用5日前までの承認取消申出で全額返還。取消兼返還申請を指定管理者へ提出、対応システムの申込・オンライン決済分はシステム申請・オンライン返還。'
                      '災害事故・利用者の責任によらない使用不可も全部または該当部分を返還。利用途中の場合は管理者が定める額。'
                      '期限後の自己都合返還は当該条件に含まれず、通常の雨だけで無料とはしません。実際の受付方法は施設で確認。')
               for ident, _, _, _ in SUMIDA]
    result.append(policy(CLOSED, CLOSURE_SOURCE,
                         CLOSURE_NOTE + ' 再開後の変更条件・料金は再確認が必要。既存の予約・申請を代行しません。'))
    for ident, _, _ in BASEBALL:
        result.append(policy(ident, TAMA_GUIDE,
                             '支払後の自己都合取消は利用月の前月1～15日まで80%返金、利用3日前まで50%、3日未満は返金なし。支払直後でも自己都合は80%から。'
                             '変更は7日前まで同利用者番号・同条件の仮予約分へ1回限り。同日の同時刻へ変更不可。紙の承認書兼明細書を持参し総合体育館・武道館・温水プール窓口で手続き。'
                             'カード払も窓口現金還付で、利用日までの明細書ダウンロード・印刷が必要。天候等で使用不能なら100%返金、30分以上利用した場合は還付不可、申請は利用日時以降5年以内。'
                             '本人判断の雨天取消を全額免除とはしません。当日券・事業参加費・大会開催に伴う施設利用料等はこの一般手続きの対象外。暑熱還付は別制度・開始前連絡が必要で、条件をこの規則から推測しません。'))
    result.append(policy(TRACK, TRACK_PAGE,
                         '貸切の使用条件・申込は施設確認が必要。料金PDFに個別の取消期限・手数料・天候還付率は未記載。'
                         '悪天候（雷・雪・光化学スモッグ等）では利用中止の場合あり。個人開放の走幅跳・走高跳・砲丸投げは雨天・強風時不可。'
                         '一般の野球場予約や個人当日券の返金条件を競技場貸切へ自動適用しません。'))
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
    assert len(REVIEWED_IDS) == len(set(REVIEWED_IDS)) == 29
    assert len(fees) == 13 and len(policies) == 14 and len(HOLDS) == 16
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
    print(json.dumps(dict(reviewed=29, prices_added=13, policies_added=14, holds=16)))


if __name__ == '__main__':
    main()
