"""Read the reviewed operator PDFs with pdfplumber; reject ambiguous columns."""
from concurrent.futures import ThreadPoolExecutor
import hashlib
import io
import json
from pathlib import Path
import re
import unicodedata
from urllib.request import Request, urlopen

import pdfplumber

ROOT = Path(__file__).resolve().parents[1]
CACHE = ROOT / 'work/venue-verification/fee-review/karaoke'


def collect(row):
    source = row['source']
    path = CACHE / (hashlib.sha256(source.encode()).hexdigest()+'.pdf')
    try:
        if not path.exists():
            with urlopen(Request(source,headers={'User-Agent':'Mozilla/5.0'}),timeout=30) as response:
                path.write_bytes(response.read())
        with pdfplumber.open(io.BytesIO(path.read_bytes())) as pdf:
            text = unicodedata.normalize('NFKC',pdf.pages[0].extract_text() or '')
        lines = text.splitlines()
        plans = []
        evidence = row['evidence']
        if 'お部屋ごとの価格' in text:
            unit = '1室30分（税込・ルームチャージ）'
        elif 'お一人様あたりの価格' in text:
            unit = '1人30分（税込・通常室料）'
        else:
            return {'skipped':row['id'],'reason':'1人／1室の課金単位を確認できません'}
        for i, marker in enumerate(lines):
            if marker.strip() != '会員 一般':
                continue
            time_match = next((match for line in reversed(lines[max(0,i-3):i])
                               if (match := re.match(r'(\d{1,2}:\d{2}\s*[~〜]\s*翌?\d{1,2}:\d{2})',line.strip()))),None)
            time = time_match.group(1) if time_match else None
            if not time or i+4 >= len(lines):
                continue
            days = lines[i+1].split()
            if len(days)!=4 or days[:2]!=days[2:] or lines[i+2].strip()!='30分':
                continue
            amounts = lines[i+3].split()
            if len(amounts)!=4 or any(not re.fullmatch(r'[\d,]+',x) for x in amounts):
                continue
            amounts = [int(x.replace(',','')) for x in amounts]
            if not any(e.get('amounts') == amounts for e in evidence):
                continue
            for member,day,amount in zip(['会員','会員','一般','一般'],days,amounts):
                plans.append(dict(label=f'{time} / {member} / {day}',amount=amount,
                                  unit=unit,
                                  conditions='通常室料のみ。ドリンク等の注文・追加料金、最低利用時間は公式料金表の条件に従います。1人利用・特別期間・学割・パックは別料金。',source_url=source))
        if len(plans)==8:
            return dict(id=row['id'],checked_at='2026-10-12',fee_options=plans,fee_note=row['price_note'])
        return {'skipped':row['id'],'reason':'PDFの時間帯・会員列を一意に対応できません'}
    except Exception as error:
        return {'skipped':row['id'],'reason':str(error)}


def main():
    CACHE.mkdir(parents=True,exist_ok=True)
    review = json.loads((ROOT/'docs/venue-fee-review-2026-10-12.json').read_text(encoding='utf-8'))
    candidates = [r for r in review if 'karaokemanekineko.jp' in r['source']]
    with ThreadPoolExecutor(max_workers=3) as pool:
        result = list(pool.map(collect,candidates))
    target = ROOT/'outputs/venues/catalogs/fee_plans.json'
    entries = {r['id']:r for r in json.loads(target.read_text(encoding='utf-8'))}
    entries.update({r['id']:r for r in result if 'id' in r})
    target.write_text(json.dumps(list(entries.values()),ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    (CACHE/'review.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps({'accepted':sum('id' in r for r in result),'skipped':[r for r in result if 'skipped' in r]},ensure_ascii=False))


if __name__ == '__main__':
    main()
