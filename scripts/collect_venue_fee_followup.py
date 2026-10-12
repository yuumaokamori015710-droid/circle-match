"""Read-only official tariff follow-up; merging preserves all other catalog data."""
import argparse
import json
from pathlib import Path
import re
import subprocess
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[1]
CHECKED = '2026-10-12'
SHINJUKU_SOURCE = 'https://www.city.shinjuku.lg.jp/content/000423351.pdf'


def fetch(url):
    with urlopen(Request(url, headers={'User-Agent': 'CircleMatch-TariffReview/1.0'}), timeout=30) as response:
        return response.read()


def plan(label, amount, unit, conditions, source):
    return dict(label=label, amount=amount, unit=unit, conditions=conditions, source_url=source)


def entry(ident, plans, note):
    if not plans:
        raise ValueError('No reviewed tariffs: ' + ident)
    return dict(id=ident, checked_at=CHECKED, fee_options=plans, fee_note=note)


def reviewed_sports():
    result = []
    source = 'https://www.totai-futsal.jp/guide/'
    plans = []
    for period, amounts, minutes in [
        ('平日9:00～12:00', (7700, 9900), 60),
        ('平日12:00～19:00', (11000, 13200), 60),
        ('平日19:00～21:00', (17600, 19800), 60),
        ('平日21:00～22:30', (24200, 26400), 90),
        ('土曜9:00～20:00', (17600, 19800), 60),
        ('土曜20:00～21:30', (24200, 26400), 90),
        ('日祝9:00～21:00', (17600, 19800), 60),
    ]:
        for group, amount in zip(('メンバー', 'ビジター'), amounts):
            plans.append(plan(period + ' / ' + group, amount, f'1面{minutes}分（税込）',
                              'フットサルコートレンタル。メンバーは年額5,500円のチーム登録が別途必要。ボール2個・ビブス5枚を含む。', source))
    result.append(entry('tokyo-sports-017', plans, '60分枠と90分枠を区別しています。個人フットサル参加費とは別です。'))

    source = 'https://shinjukuchuo-park.jp/futsal/'
    plans = [plan(period, amount, '1面1時間', '団体登録が必要。子ども団体減額・障害者免除を除く通常料金。公式ページの「フットサル料金」画像を確認。', source)
             for period, amount in [('午前9:00～12:00', 3000), ('午後12:00～17:00', 4000), ('夜間17:00～22:00', 5000)]]
    result.append(entry('tokyo-sports-018', plans, '公園の現行公式案内に掲載されている料金画像を確認。区分をまたぐ利用は各時間帯の料金です。'))

    source = 'https://www.jexer.jp/futsal/oi/program.html'
    plans = []
    for period, amounts in [('平日10:00～18:00', (13200, 18700)), ('平日18:00～23:00', (18700, 24200)), ('土日祝10:00～22:00', (18700, 24200))]:
        for group, amount in zip(('登録チーム', 'ビジター'), amounts):
            plans.append(plan(period + ' / ' + group, amount, '1面1時間', '通常コート使用料。学割は含みません。登録チームは初年度11,000円、更新8,800円の登録料が別途必要。', source))
    result.append(entry('tokyo-sports-021', plans, '公式プログラム紹介のコート使用料を確認。平日昼の学割5,500円・8,800円は学生証提示条件があるため通常料金の範囲には含めていません。'))

    source = 'https://www.sports-alpha.com/shinagawa/use.html'
    plans = []
    for period, amounts in [('平日11:00～18:00', (4400, 5500)), ('平日18:00～21:00', (6050, 7700)), ('土日祝終日', (6050, 7700))]:
        for group, amount in zip(('登録チーム', '未登録チーム'), amounts):
            plans.append(plan(period + ' / ' + group, amount, '1面30分（税込）', '最低1時間から30分単位。土日朝は当日予約を除き2時間単位。学割・ジュニア割引は含みません。', source))
    for period, amount in [('日祝17:00まで', 72600), ('日祝17:00以降', 52800)]:
        plans.append(plan('ソサイチ / ' + period, amount, '3面連結・2時間（税込）', '土曜の祝日を除く日祝限定。最低2時間から。事前振込。通常のフットサル1面料金とは別です。', source))
    result.append(entry('tokyo-sports-022', plans, '30分単価は30分のみの予約ができる意味ではありません。ソサイチ料金と分けて表示します。'))

    base = 'https://www.city.meguro.tokyo.jp/sports/shisetsu/sports/'
    for ident, page, values in [
        ('tokyo-venue-e34356792fd2', 'komaba_kashikiritaiikushitsu', (8700, 17500, 10800, 21600)),
        ('tokyo-venue-19bdbd66ba0c', 'center_kashikiritaiikushitsu', (6600, 13300, 8200, 16500)),
        ('tokyo-venue-14082e508e16', 'himonya_taiikusitu_kasikiriri', (9400, 18800, 11600, 23300)),
        ('tokyo-gym-e4e044521f5b', 'chuo_kashikirikyogijo', (13100, 26200, 16200, 32400)),
        ('tokyo-venue-ec8de0668a02', 'yakumo_kashikiritaiikushitsu', (8000, 16000, 9900, 19800)),
    ]:
        source = base + page + '.html'
        plans = []
        for period, amounts in [('午前9:00～12:00', values[:2]), ('午後1 12:20～15:20', values[2:]), ('午後2 15:40～18:40', values[2:]), ('夜間19:00～22:00', values[2:])]:
            for group, amount in zip(('区民団体', '区外団体'), amounts):
                plans.append(plan(period + ' / ' + group, amount, '体育室・競技場貸切1枠（3時間）', '事前の団体登録が必要。個人公開料金とは別。器具使用料は含みません。', source))
        result.append(entry(ident, plans, '2025年4月改定後の各施設の現行公式料金表を確認。八雲体育館は試算資料の9,300円ではなく現行案内の8,000円を採用。'))

    source = 'https://www.city.ota.tokyo.jp/shisetsu/sports/oomori_s/oomorisportsc_arena.html'
    plans = [plan(period, amount, unit, 'アマチュアスポーツ・区内使用者の「その他」区分。区外使用者は5割加算、土日祝は5割加算。小中高生の別料金・付帯設備は含みません。', source)
             for period, amount, unit in [('午前9:00～12:00', 24100, '競技場全面・区内平日3時間'), ('午後13:00～17:00', 28300, '競技場全面・区内平日4時間'), ('夜間18:00～22:00', 40700, '競技場全面・区内平日4時間'), ('全日9:00～22:00', 93100, '競技場全面・区内平日全日')]]
    result.append(entry('tokyo-sports-027', plans, '表示額は一般の区内平日基本料。区外・土日祝・利用目的で割増があり、施設全体の絶対的な最高料金ではありません。'))

    for ident, slug in [('tokyo-jelly-shibuya', 'shibuya'), ('tokyo-jelly-ikebukuro', 'ikebukuro')]:
        source = 'https://jellyjellycafe.com/' + slug
        plans = []
        for label, amount, hours in [('平日デイ13:00～18:00', 1800, 5), ('平日ナイト18:00～23:00', 1800, 5), ('土日祝・ハイシーズン デイ13:00～18:00', 2800, 5), ('土日祝・ハイシーズン ナイト18:00～23:00', 2200, 5), ('平日オールデイ13:00～23:00', 2800, 10), ('土日祝・ハイシーズン オールデイ13:00～23:00', 4000, 10)]:
            plans.append(plan(label, amount, f'1人・最大{hours}時間（税込）', '1ドリンク付き通常パック。学生・未就学児の割引、延長料金、店舗貸切料金を含みません。', source))
        if slug == 'ikebukuro':
            plans.append(plan('土日モーニング10:00～13:00', 1500, '1人・最大3時間（税込）', '1ドリンク付き。モーニングからの延長は通常料金。', source))
        result.append(entry(ident, plans, '通常の個人利用パック料金。店舗貸切料金とは別です。課金時間ごとに範囲を分けています。'))
    return result


def collect_academies(rows):
    result = []
    for row in rows:
        if row['municipality'] != '文京区' or not row['name'].startswith('アカデミー'):
            continue
        source = row['official_url']
        soup = BeautifulSoup(fetch(source), 'html.parser')
        table = next(t for t in soup.select('table') if '施設名' in t.get_text() and '料金' in t.get_text())
        cells = [[c.get_text('', strip=True) for c in tr.find_all(['th', 'td'], recursive=False)] for tr in table.select('tr')]
        periods = next(c for c in cells if c and c[0] == '午前')
        times = cells[cells.index(periods) + 1]
        if len(times) != len(periods):
            raise ValueError('Academy times changed: ' + source)
        plans = []
        for values in cells[cells.index(periods) + 2:]:
            amount_cells = values[-len(periods):]
            if not all(re.fullmatch(r'[\d,]+', v) for v in amount_cells):
                raise ValueError('Academy amount changed: ' + source)
            names = values[:-len(periods)-2]
            room = next((v for v in names if not re.fullmatch(r'\d+階|\d+', v)), '')
            room = re.sub(r'（(?:JPG|PDF)：[^）]+）', '', room)
            if not room:
                raise ValueError('Academy room missing: ' + source)
            for period, time, amount in zip(periods, times, amount_cells):
                plans.append(plan(room + ' / ' + period + time, int(amount.replace(',', '')), '1室・1利用区分', '利用登録が必要。附帯設備・減免・割増は別途。区分ごとに利用時間が異なります。', source))
        result.append(entry(row['id'], plans, '文京区の現行施設料金表の全室・午前/午後/夜間を確認。1時間料金への推定換算はしていません。'))
    return result


def parse_community_tables(pages, rows):
    names = ['四谷', '牛込箪笥', '榎町', '若松', '大久保', '戸塚', '落合第一', '落合第二', '柏木', '角筈']
    result = []
    for index, tables in enumerate(pages):
        row = next((r for r in rows if r['name'] == names[index] + '地域センター'), None)
        if row is None:
            continue
        table = next(t for t in tables if any('施設使用料' in (c or '') for c in t[0]))
        headers = next(c for c in table if '午前' in c and '全日' in c)
        start = headers.index('午前')
        plans = []
        parent_room = ''
        for number in range(table.index(headers) + 1, len(table)-1):
            upper, lower = table[number], table[number+1]
            if upper[0]:
                parent_room = upper[0].replace('\n', '')
            # Only unambiguous registered/general pairs; merged purpose-use rows are excluded.
            if not any(upper[:start]) or any(lower[:start]):
                continue
            amounts = [upper[start:start+6], lower[start:start+6]]
            if not all(len(v) == 6 for v in amounts):
                raise ValueError('Community fee pair changed: ' + names[index])
            room_parts = [parent_room, *upper[1:start-1]]
            room = ' '.join((v or '').replace('\n', '') for v in room_parts).strip()
            for pair in zip(*amounts):
                if all(c in ('‐', '-', '－', '—') for c in pair):
                    continue
                if not all(re.fullmatch(r'[\d,]+', c or '') for c in pair):
                    raise ValueError('Community fee pair changed: ' + names[index])
            for group, values in zip(('登録団体', 'その他一般団体'), amounts):
                for period, amount in zip(('午前', '午後1', '午後2', '夜間1', '夜間2', '全日'), values):
                    if amount in ('‐', '-', '－', '—'):
                        continue
                    plans.append(plan(room + ' / ' + group + ' / ' + period, int(amount.replace(',', '')),
                                      '1室・全日' if period == '全日' else '1室・1利用区分',
                                      f'新宿区公式料金表{index+1}ページ。団体区分・部屋の利用目的制限に従います。調理設備は別途。葬儀使用料を除く。', SHINJUKU_SOURCE))
        result.append(entry(row['id'], plans, '新宿区の現行総合案内がリンクする料金表を確認。明確に対応づけできた部屋の登録団体・その他一般団体の料金幅。目的利用等の特殊な結合行は含みません。'))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--pdf-python', required=True)
    args = parser.parse_args()
    rows = sum([json.loads((ROOT/'outputs/venues/catalogs'/name).read_text(encoding='utf-8-sig'))
                for name in ('tokyo_tennis.json', 'tokyo_sports.json', 'tokyo_expansion.json')], [])
    pdf = fetch(SHINJUKU_SOURCE)
    program = 'import sys,json,io,pdfplumber;p=pdfplumber.open(io.BytesIO(sys.stdin.buffer.read()));print(json.dumps([x.extract_tables() for x in p.pages],ensure_ascii=True))'
    parsed = subprocess.run([args.pdf_python, '-c', program], input=pdf, capture_output=True, check=True)
    entries = reviewed_sports() + collect_academies(rows) + parse_community_tables(json.loads(parsed.stdout), rows)
    sys_path = str(ROOT/'outputs')
    import sys
    sys.path.insert(0, sys_path)
    from venues.fees import validate, price_ranges
    checked = validate(entries)
    path = ROOT/'outputs/venues/catalogs/fee_plans.json'
    previous = json.loads(path.read_text(encoding='utf-8'))
    existing = {e['id']: e for e in previous}
    existing.update(checked)
    path.write_text(json.dumps(list(existing.values()), ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    report = [dict(id=e['id'], name=next(r['name'] for r in rows if r['id']==e['id']),
                   checked_at=CHECKED, ranges=price_ranges(e), source_urls=sorted({p['source_url'] for p in e['fee_options']})) for e in entries]
    (ROOT/'docs/venue-fee-followup-2026-10-12.json').write_text(json.dumps(report, ensure_ascii=False, indent=2)+'\n', encoding='utf-8')
    print(json.dumps({'venues_updated': len(entries), 'tariffs_added': sum(len(e['fee_options']) for e in entries)}, ensure_ascii=True))


if __name__ == '__main__':
    main()
