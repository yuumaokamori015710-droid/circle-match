"""Append public-source tariffs and cancellation terms without replacing prior reviews."""
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'outputs'))
from venues.fees import validate
from venues.sports_catalog import get_catalog

CHECKED = '2026-10-18'
CATALOGS = ROOT / 'outputs/venues/catalogs'
SHINJUKU_GUIDE = 'https://www.regasu-shinjuku.or.jp/?p=139217'
KATSUSHIKA_GUIDE = 'https://spo.katsushika-web.net/group_guide/'
OUTDOOR = 'https://spo.katsushika-web.net/facility/others/'
SHINJUKU_IDS = ['shinjuku-okubo', 'shinjuku-kansenen', 'shinjuku-ochiai-chuo',
                'shinjuku-nishiochiai', 'tokyo-venue-144440cef349', 'tokyo-venue-8a1449acfd44']
KATSUSHIKA_TENNIS = ['katsushika-kamichiba', 'katsushika-okudo', 'katsushika-kosuge',
                     'katsushika-higashishinkoiwa', 'katsushika-higashikanamachi',
                     'katsushika-mizumoto', 'katsushika-shibue', 'katsushika-niijuku']
KATSUSHIKA_OUTDOOR = ['tokyo-venue-be0319cd8fbd', 'tokyo-venue-6e8063869f46',
                      'tokyo-venue-f22c36060e5d', 'tokyo-venue-acf6eedff95e',
                      'tokyo-venue-c4c0a999cf17', 'tokyo-venue-6b66e7410823',
                      'tokyo-venue-e6f34cc5ab8e']
KATSUSHIKA_INDOOR = ['tokyo-gym-8661317f0c40', 'tokyo-gym-8107c9095a7c',
                     'tokyo-venue-48461c620190']
CLOSED = 'tokyo-venue-ecb55dd79d92'
REVIEWED_IDS = SHINJUKU_IDS + KATSUSHIKA_TENNIS + KATSUSHIKA_OUTDOOR + KATSUSHIKA_INDOOR + [CLOSED]


def entry(ident, source, conditions, rows):
    return {'id': ident, 'checked_at': CHECKED, 'fee_note': conditions,
            'fee_options': [{'label': label, 'amount': amount, 'unit': unit,
                             'conditions': conditions, 'source_url': source}
                            for label, amount, unit in rows]}


def reviewed_fees():
    result = [
        entry('shinjuku-okubo', 'https://www.regasu-shinjuku.or.jp/regasu/wp-content/uploads/2013/05/ookubo-tennis-price.pdf',
              '大久保スポーツプラザ庭球場1面の通常料金。区内外で料金差なし。無料の利用登録後、利用当日に現地払い。準備・整備を含みます。夜間照明は別途30分500円。2時間枠と2時間30分枠を混ぜて表示しません。', [
                  ('11:30～13:30・13:30～15:30・15:30～17:30・17:30～19:30', 1500, '庭球場1面・2時間'),
                  ('9:00～11:30・19:30～22:00', 1800, '庭球場1面・2時間30分'),
              ]),
        entry('tokyo-venue-144440cef349', 'https://www.regasu-shinjuku.or.jp/?p=653',
              '西落合公園の庭球場1面のみ。少年野球場の無料料金とは別です。通常のテニスは2時間1,500円。区内外同額、登録必要・現地当日払い。現行施設ページは照明なしと案内（旧一覧PDFの照明記載は採用しません）。', [
                  ('庭球場・通常利用', 1500, '庭球場1面・2時間'),
              ]),
        entry('tokyo-venue-8a1449acfd44', 'https://www.regasu-shinjuku.or.jp/?p=652',
              '西戸山公園野球場1面の通常料金。無料登録後、利用当日に現地払い。夜間照明は別途30分3,150円。一般用サッカーゴールはなくフットサルゴール3組のみ。硬式野球不可。', [
                  ('野球場・通常利用', 5100, '野球場1面・2時間'),
              ]),
        entry('tokyo-venue-be0319cd8fbd', OUTDOOR + '#anc-kosugenishi',
              '小菅西フットサル場1面の貸切基本料金。隣接スケートボード場の個人料金ではありません。無料の体育施設登録・口座設定が必要。照明別途1面2時間1,100円、備品・駐車場別。', [
                  ('貸切基本料金（照明別）', 2600, 'フットサル場1面・2時間以内'),
              ]),
    ]
    for ident, anchor, room in [
        ('tokyo-venue-6e8063869f46', 'anc-edogawa-sibamata', '球技場'),
        ('tokyo-venue-f22c36060e5d', 'anc-arakawa-kosuge', '球技場'),
        ('tokyo-venue-6b66e7410823', 'anc-edogawa-sibamata', '野球場'),
        ('tokyo-venue-e6f34cc5ab8e', 'anc-arakawa-kosuge', '野球場'),
    ]:
        result.append(entry(ident, OUTDOOR + '#' + anchor,
                            '公式案内の河川敷' + room + '1面の通常貸切料金。少年ソフトボール場の無料開放・減免を除きます。無料登録・口座設定が必要。4～9月の早朝6～8時・夕方16～18時は10～3月閉鎖。備品・駐車場別、悪天候時は現場判断。', [
                                ('通常貸切（少年施設の無料区分を除く）', 1200, room + '1面・2時間以内'),
                            ]))
    result.append(entry('tokyo-gym-8661317f0c40', KATSUSHIKA_GUIDE,
                        '奥戸総合スポーツセンター温水プール館内エイトホールの通常貸切料金のみ。プール・会議室・個人入場料は含みません。無料登録・口座設定が必要。準備片付けを含み、備品や減免は別。', [
                            ('第1回9:00～11:30', 6300, 'エイトホール全面・2時間30分'),
                            ('第2回12:30～15:00・第3回15:30～18:00', 8200, 'エイトホール全面・2時間30分'),
                            ('第4回18:30～21:00', 9700, 'エイトホール全面・2時間30分'),
                            ('全日9:00～21:00', 29200, 'エイトホール全面・全日12時間'),
                        ]))
    rows = [(label, amount, room + '・2時間')
            for room, amounts in [('メインアリーナ全面', (10200, 12700, 15500)),
                                  ('メインアリーナ半面', (5100, 6350, 7750)),
                                  ('サブアリーナ全面', (5000, 6200, 7200))]
            for label, amount in zip(('第1回9:00～11:00', '第2～4回11:30～13:30・14:00～16:00・16:30～18:30', '第5回19:00～21:00'), amounts)]
    rows += [(room + ' / 全日9:00～21:00', amount, room + '・全日12時間')
             for room, amount in [('メインアリーナ全面', 57200), ('メインアリーナ半面', 28600), ('サブアリーナ全面', 27700)]]
    result.append(entry('tokyo-gym-8107c9095a7c', KATSUSHIKA_GUIDE,
                        '水元総合スポーツセンターの通常アリーナ貸切。メイン全面・半面・サブを別の課金単位として記録。無料の体育施設登録と口座設定が必要。準備片付けを含み、武道場・会議室・個人利用・備品・減免は含みません。全日利用は窓口申請。', rows))
    return result


def reviewed_policies():
    shin = '予約システムまたは窓口で取消可能。5日前までの取消なら利用制限なし。4日前～当日の取消は翌月25日～翌々月24日の1か月間、抽選・空き予約が停止。無断未使用は翌月25日から最長3か月。利用料は現地当日払い。雨天・施設コンディションによる中止は現地へ電話し、Webで自己取消しない。天候による利用不能は制限対象外。'
    cancel = '利用7日前まで取消料無料、6日前～前日は利用料50%、当日・無断未使用は100%。窓口で手続きした予約（減免申請等を含む）はオンライン取消不可。口座登録による後払いでも取消料は発生します。'
    weather = '屋外の悪天候中止は施設の現場判断。利用不能分は口座引落しせず、事前払い済みの場合は窓口還付手続きが必要。'
    indoor = '屋内ホールに屋外の雨天免除を適用しません。'
    result = [{'id': ident, 'status': 'conditional', 'summary': shin,
               'source_url': SHINJUKU_GUIDE, 'checked_at': CHECKED} for ident in SHINJUKU_IDS]
    for ident in KATSUSHIKA_TENNIS + KATSUSHIKA_OUTDOOR + KATSUSHIKA_INDOOR:
        source = ('https://www.city.katsushika.lg.jp/tourism/1002753/1030217/1003235.html'
                  if ident == 'katsushika-higashishinkoiwa' else KATSUSHIKA_GUIDE)
        result.append({'id': ident, 'status': 'conditional',
                       'summary': cancel + (indoor if ident in KATSUSHIKA_INDOOR else weather),
                       'source_url': source, 'checked_at': CHECKED})
    return result


def append_reviews(path, additions):
    original = path.read_text(encoding='utf-8')
    entries = json.loads(original)
    indexed = {row['id']: row for row in entries}
    for row in additions:
        if row['id'] in indexed and indexed[row['id']] != row:
            raise ValueError('Refusing to replace existing review: ' + row['id'])
    pending = [row for row in additions if row['id'] not in indexed]
    if not pending:
        return
    entries.extend(pending)
    if path.name == 'fee_plans.json':
        validate(entries)
    serialized = (json.dumps(pending, ensure_ascii=False, indent=2)[2:-2]
                  if path.name == 'fee_plans.json' else
                  ',\n'.join('  ' + json.dumps(row, ensure_ascii=False, separators=(',', ':')) for row in pending))
    rendered = original.rstrip()[:-1].rstrip() + (',\n' if indexed else '\n') + serialized + '\n]\n'
    assert json.loads(rendered) == entries
    temporary = path.with_suffix('.json.tmp')
    temporary.write_text(rendered, encoding='utf-8')
    temporary.replace(path)


def main():
    fees, policies = reviewed_fees(), reviewed_policies()
    validate(fees)
    catalog = {row['id']: row for row in get_catalog()['courts']}
    assert len(REVIEWED_IDS) == len(set(REVIEWED_IDS)) == 25
    assert len(fees) == 10 and len(policies) == 24
    assert all(ident in catalog for ident in REVIEWED_IDS)
    for review in fees:
        row = catalog[review['id']]
        if row.get('fee_checked_at') != CHECKED and (row.get('fee_ranges') or row['price_from'] is not None):
            raise ValueError('Refusing to replace an already priced venue: ' + review['id'])
    append_reviews(CATALOGS / 'fee_plans.json', fees)
    append_reviews(CATALOGS / 'cancellation_policies.json', policies)
    print(json.dumps({'reviewed_records': 25, 'new_fee_reviews': 10, 'cancellation_reviews': 24}))


if __name__ == '__main__':
    main()
