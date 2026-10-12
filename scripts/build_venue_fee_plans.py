"""Convert reviewed official table cells to explicit tariffs. Offline by default.

Network collection is opt-in; only official pages already present in the catalog
and Kita's official fee PDF are read. No booking or contact request is submitted.
"""
import argparse
from collections import defaultdict
import json
from pathlib import Path
import re
import subprocess
import unicodedata
from urllib.request import urlopen, Request

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / 'outputs/venues/catalogs/fee_plans.json'
REVIEW = ROOT / 'docs/venue-fee-review-2026-10-12.json'
KITA_PDF = 'https://www.city.kita.lg.jp/_res/projects/default_project/_page_/001/002/372/20180423shimokaisetsugo.pdf'
CHECKED = '2026-10-12'


def normalize(text):
    return unicodedata.normalize('NFKC', str(text or '')).strip()


def money(text):
    match = re.fullmatch(r'([\d,]+)\s*円?', normalize(text))
    return int(match[1].replace(',', '')) if match else None


def reviewed_plans():
    result = []
    for row in json.loads(REVIEW.read_text(encoding='utf-8')):
        source, evidence = row['source'], row['evidence']
        plans = []
        def add(label, amount, unit='1室・1利用区分', conditions=''):
            if amount is not None:
                plans.append(dict(label=normalize(label), amount=amount, unit=unit,
                                  conditions=conditions or row['price_note'], source_url=source))
        def columns(room, values, periods, unit='1室・1利用区分', conditions=''):
            for cell, period in zip(values, periods):
                add(room + ' / ' + period, money(cell), unit, conditions)
        if isinstance(evidence, list):
            if 'suginami' in source:
                for cells in evidence:
                    if len(cells) == 2 and cells[0] == '体育館':
                        for label, amount in re.findall(r'[（(]([^）)]+)[）)]\s*([\d,]+)円', normalize(cells[1])):
                            label = label.replace('4分の14面', '4分の1面')
                            add(label, money(amount), '体育館貸切2時間')
                    elif len(cells) == 3:
                        for period, amount in re.findall(r'([^、。:：]+)[:：]([\d,]+)円', normalize(cells[2])):
                            if '延長' not in period:
                                add(cells[0]+' / '+period,money(amount))
            elif 'nerima' in source:
                for cells in evidence:
                    if len(cells) == 5:
                        columns(cells[0], cells[1:], ['午前9:00–12:00','午後1 12:30–15:30','午後2 16:00–18:00','夜間18:30–21:30'], '競技場貸切1枠')
            elif 'setagaya' in source:
                for cells in evidence:
                    if len(cells) == 6:
                        columns(cells[0], cells[1:], ['午前9:00–12:00','午後A 12:30–14:30','午後B 15:00–17:00','夕方17:30–19:30','夜間20:00–22:00'])
            elif 'tokyo-nakano' in source:
                for cells in evidence:
                    amounts = [c for c in cells[1:] if money(c) is not None and '円' in c]
                    periods = ['午前9:00–12:00','午後13:00–17:00','夜間18:00–22:00'] if len(amounts)==3 else ['午前9:00–12:00','午後1 13:00–16:00','午後2 16:00–19:00','夜間19:00–22:00']
                    if len(amounts) in (3,4):
                        columns(cells[0], amounts, periods)
            elif 'itabashi' in source:
                for cells in evidence:
                    if len(cells) == 7:
                        columns(cells[1], cells[-3:], ['午前','午後','夜間'])
            elif 'minato' in source:
                room = ''
                for cells in evidence:
                    if len(cells) == 3:
                        room = cells[0]
                    if len(cells) in (2,3):
                        add(room + ' / ' + cells[-2], money(cells[-1]))
            elif 'meguro' in source:
                seen = defaultdict(int)
                for cells in evidence:
                    room = cells[0]
                    # Review contains general-resident and other-group tables only.
                    group = '一般区民団体' if seen[room] == 0 else 'その他団体'
                    seen[room] += 1
                    columns(room + ' / ' + group, cells[2:6], ['午前9:00–12:00','午後1 12:30–15:00','午後2 15:30–18:00','夜間18:30–21:00'])
            elif 'katsushika' in source:
                room = ''
                for cells in evidence:
                    if len(cells) in (9,10):
                        room = cells[0]
                        weekday = cells[3] if len(cells)==10 else ''
                    elif len(cells) == 7:
                        weekday = cells[0]
                    else:
                        continue
                    columns(room + (' / '+weekday if weekday else ''), cells[-6:], ['午前9:00–12:00','午後1 13:00–15:00','午後2 15:30–17:30','午後全13:00–17:30','夜間18:00–21:00','全日9:00–21:00'])
            elif 'arakawa' in source:
                for cells in evidence:
                    if len(cells) == 5:
                        add(cells[0]+' / 区民料金', money(cells[-2]))
                        add(cells[0]+' / 一般料金', money(cells[-1]))
            elif 'toshima' in source:
                for cells in evidence:
                    if len(cells) in (5,6):
                        room = cells[-5] if len(cells)==5 else cells[1]
                        columns(room, cells[-3:-1], ['午前','午後・夜間'])
            elif 'edogawa' in source:
                for cell in evidence:
                    if isinstance(cell, dict) and 'new_yen' in cell:
                        add(cell['room'],cell['new_yen'],'1室'+cell['unit'])
            elif 'city.ota' in source:
                for cell in evidence:
                    if isinstance(cell,dict) and 'new_yen' in cell:
                        add(cell['room']+' / '+cell['period'],cell['new_yen'],f'1面{cell["hours"]:g}時間')
            elif 'koto-hsc' in source:
                for cells in evidence:
                    columns(cells[0], cells[1:3], ['平日','土日祝'], '主体育室貸切1枠')
            elif 'city.shibuya' in source:
                for cells in evidence:
                    add(cells[0], money(cells[1]), '大体育室貸切2時間')
            elif 'bonfim' in source:
                periods = ['平日10:00–19:00','平日19:00–23:00','土日祝8:00–10:00','土10:00–23:00','日祝10:00–19:00','日祝19:00–23:00']
                for cells, period in zip(evidence,periods):
                    columns(period,cells[-2:],['メンバー','ビジター'],'1面1時間（税込）')
        if row['id'] == 'tokyo-sports-011':
            for period, amounts in [('平日10:00–18:00',(8250,10450)),('平日18:00–23:00',(13750,15950)),('土日祝9:00–23:00',(13750,15950))]:
                for group, amount in zip(['有料会員','無料会員・ビジター'],amounts):
                    add(period+' / '+group,amount,'1面1時間（税込）')
        if 'tetsugakudo.jp' in source:
            add('平日',600,'1面2時間'); add('土日祝',1000,'1面2時間')
        if row['id'] == 'tokyo-venue-626edd16b268':
            add('アリーナ半面',2400,'3時間'); add('アリーナ全面',4810,'3時間')
        if row['id'] == 'tokyo-sports-042':
            add('運動場半面',3800,'2時間'); add('運動場全面',7500,'2時間')
        if row['price_from'] == row['price_to'] and not plans:
            add('基本使用料',row['price_from'],row['price_unit'])
        if plans:
            result.append(dict(id=row['id'],checked_at=CHECKED,fee_options=plans,fee_note=row['price_note']))
    return result


def fetch(url):
    req = Request(url,headers={'User-Agent':'Mozilla/5.0 (CircleMatch official tariff review)'})
    with urlopen(req,timeout=35) as response:
        return response.read()


def collect_kita(rows, pdf_python, cache):
    pdf = cache / 'kita-fees.pdf'
    pdf.write_bytes(fetch(KITA_PDF))
    command = 'import json,sys,pdfplumber;d=pdfplumber.open(sys.argv[1]);print(json.dumps([p.extract_tables()[0] for p in d.pages],ensure_ascii=False))'
    tables = json.loads(subprocess.check_output([pdf_python,'-X','utf8','-c',command,str(pdf)],text=True,encoding='utf-8'))
    grouped = defaultdict(list)
    for page, table in enumerate(tables):
        facility = room = ''
        group = '北区民' if page < 3 else '北区民以外'
        for cells in table[3:]:
            if cells[0] and 'ふれあい館' in cells[0]:
                facility = normalize(cells[0].split('\n')[0]).lstrip('★')
                room = ''
            if cells[1]:
                room = normalize(cells[1])
            suffix = normalize(cells[2])
            if not facility or not room:
                continue
            for cell, period in zip(cells[-3:], ['午前9:00–12:00','午後13:00–17:00','夜間18:00–22:00']):
                amount = money(cell)
                if amount is not None:
                    grouped[facility].append(dict(label=' / '.join(filter(None,[room+suffix,group,period])),amount=amount,unit='1室・1利用区分',conditions='団体貸室利用。高齢者福祉コーナーの無料個人利用とは別です。備品・減免は含みません。PDFの'+str(page+1)+'ページ。',source_url=KITA_PDF))
    result = []
    for row in rows:
        if row['municipality'] != '北区':
            continue
        options = next((plans for name,plans in grouped.items() if name in row['name']),None)
        if options:
            result.append(dict(id=row['id'],checked_at=CHECKED,fee_options=options,
                               fee_note='北区の現行施設案内がリンクする料金表。高齢者優先の曜日・時間、部屋ごとの利用資格を公式案内で確認してください。時間をまたぐ利用は別区分です。'))
    return result


def collect_meguro(rows, cache):
    from bs4 import BeautifulSoup
    result = []
    for row in rows:
        if row['municipality'] != '目黒区' or '住区センター' not in row['name']:
            continue
        source = row['official_url']
        html = fetch(source)
        (cache / (row['id']+'.html')).write_bytes(html)
        soup = BeautifulSoup(html,'html.parser')
        plans = []
        for table in soup.select('table'):
            caption = table.find('caption')
            heading = caption or table.find_previous_sibling()
            group = heading.get_text(' ',strip=True) if heading else ''
            if group not in ['登録団体（区民団体）','一般団体（区民団体）','その他団体']:
                continue
            for tr in table.select('tr'):
                cells = [c.get_text(' ',strip=True) for c in tr.find_all(['th','td'],recursive=False)]
                amounts = [money(c) if '円' in c else None for c in cells]
                first = next((i for i,v in enumerate(amounts) if v is not None), None)
                if first is None or first < 2 or len(cells[first:first+4]) != 4:
                    continue
                room = cells[first-2]
                for amount,period in zip(amounts[first:first+4],['午前9:00–12:00','午後1 12:30–15:00','午後2 15:30–18:00','夜間18:30–21:00']):
                    if amount is not None:
                        plans.append(dict(label=room+' / '+group+' / '+period,amount=amount,unit='1室・1利用区分',conditions='利用者区分は施設の団体登録条件に従います。付帯設備・減免・割増を除く基本使用料。',source_url=source))
        if plans:
            result.append(dict(id=row['id'],checked_at=CHECKED,fee_options=plans,fee_note='登録団体・一般区民団体・その他団体は料金が異なります。対象区分と利用資格を公式案内で確認してください。'))
    return result


def collect_kita_gyms(cache):
    from bs4 import BeautifulSoup
    result = []
    base = 'https://www.city.kita.lg.jp/culture-tourism-sports/sports/1010385/1010387/1010416/1010420/'
    periods = ['午前9:00–12:00','午後1 12:30–15:00','午後2 15:30–18:00','夜間18:30–21:30','全日9:00–21:30']
    for venue_id, page in [('tokyo-sports-029','1010421'),('tokyo-gym-a158d5ba41af','1010422'),('tokyo-venue-a231a98caa19','1010423')]:
        source = base + page + '.html'
        html = fetch(source)
        (cache / (venue_id+'.html')).write_bytes(html)
        soup = BeautifulSoup(html,'html.parser')
        table = next(t for t in soup.select('table') if 'アリーナ' in t.get_text())
        plans = []
        for tr in table.select('tr')[1:]:
            cells = [c.get_text(' ',strip=True) for c in tr.find_all(['th','td'],recursive=False)]
            if len(cells) != 6 or any(money(c) is None for c in cells[1:]):
                raise ValueError('Unexpected gym tariff table: '+source)
            for period, amount in zip(periods,map(money,cells[1:])):
                plans.append(dict(label=cells[0]+' / '+period,amount=amount,unit='団体貸切・1利用区分',
                                  conditions='団体登録・予約が必要です。貸切使用料であり個人公開料金ではありません。器具使用料・減免・割増は別途。',source_url=source))
        result.append(dict(id=venue_id,checked_at=CHECKED,fee_options=plans,fee_note='令和7年4月改定後の公式貸切使用料。利用区分をまたぐ場合は区分ごとの料金が必要です。'))
    return result


def football_plans():
    result = []
    source = 'https://www.fctokyoparkfuchu.jp/rental/'
    plans = []
    for period, amounts, unit in [('平日11:00–19:00',(6600,8800),'1面1時間（税込）'),
                                  ('平日19:00–21:00',(13200,15400),'1面1時間（税込）'),
                                  ('土日祝11:00–21:00',(13200,15400),'1面1時間（税込）'),
                                  ('全日21:00–21:45',(9900,11550),'1面45分（税込）')]:
        for group, amount in zip(['メンバー','ビジター'],amounts):
            plans.append(dict(label=period+' / '+group,amount=amount,unit=unit,
                              conditions='コートレンタル料金。メンバーは年額5,500円／チームの登録・更新料が別途必要です。21:00以降は1時間ではなく45分枠です。',source_url=source))
    result.append(dict(id='tokyo-sports-020',checked_at=CHECKED,fee_options=plans,fee_note='会員登録は任意。一般はビジター料金で利用できます。'))
    source = 'https://www.jpnsport.go.jp/hpsc/Default.aspx?TabId=1440'
    plans = [dict(label=period,amount=amount,unit='1面1時間',
                  conditions='通常のコートレンタル料金。大会参加費とは別です。施設案内には年間登録料5,250円が別途記載されています。',source_url=source)
             for period,amount in [('平日9:00–19:00',5040),('平日19:00–21:00',6720),('土日祝9:00–21:00',6720)]]
    result.append(dict(id='tokyo-sports-023',checked_at=CHECKED,fee_options=plans,fee_note='JSC公式施設案内の掲載額。休業日・登録条件は予約前に公式案内をご確認ください。'))
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--collect',action='store_true')
    parser.add_argument('--collect-sports',action='store_true')
    parser.add_argument('--pdf-python')
    args = parser.parse_args()
    entries = {e['id']:e for e in reviewed_plans()}
    if OUTPUT.exists():
        entries.update({e['id']:e for e in json.loads(OUTPUT.read_text(encoding='utf-8')) if e['id'] not in entries})
    cache = ROOT / 'work/venue-verification/fee-review'
    if args.collect:
        if not args.pdf_python:
            parser.error('--collect requires --pdf-python with pdfplumber installed')
        rows = sum([json.loads((ROOT/'outputs/venues/catalogs'/name).read_text(encoding='utf-8-sig')) for name in ('tokyo_tennis.json','tokyo_sports.json','tokyo_expansion.json')],[])
        cache.mkdir(parents=True,exist_ok=True)
        entries.update({e['id']:e for e in collect_kita(rows,args.pdf_python,cache)+collect_meguro(rows,cache)})
    if args.collect_sports:
        cache.mkdir(parents=True,exist_ok=True)
        entries.update({e['id']:e for e in collect_kita_gyms(cache)})
    entries.update({e['id']:e for e in football_plans()})
    OUTPUT.write_text(json.dumps(list(entries.values()),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print(json.dumps({'venues':len(entries),'tariffs':sum(len(e['fee_options']) for e in entries.values())}))


if __name__ == '__main__':
    main()
