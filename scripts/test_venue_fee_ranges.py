"""Unit-aware tariff bounds and reproducible official fee follow-up checks."""
import json
from pathlib import Path
from urllib.parse import urlencode

from bs4 import BeautifulSoup
from test_venues import IsolatedAppHttpCase


class VenueFeeRangeTests(IsolatedAppHttpCase):
    def test_bounds_use_every_tariff_and_keep_billing_units_separate(self):
        from venues.fees import price_ranges
        row = {'fee_options': [
            {'unit': '1面1時間', 'amount': 3000},
            {'unit': '1面全日', 'amount': 50000},
            {'unit': '1面1時間', 'amount': 9000},
            {'unit': '1面1時間', 'amount': 1000},
            {'unit': '1面全日', 'amount': 40000},
        ]}
        self.assertEqual(price_ranges(row), [
            {'unit': '1面1時間', 'minimum': 1000, 'maximum': 9000, 'tariff_count': 3},
            {'unit': '1面全日', 'minimum': 40000, 'maximum': 50000, 'tariff_count': 2},
        ])
        self.assertEqual(price_ranges({'price_from': None}), [])
        self.assertEqual(price_ranges({'price_from': 0, 'price_to': 0, 'price_unit': '1面1時間'})[0]['maximum'], 0)

    def test_api_and_initial_html_have_same_unit_aware_bounds(self):
        rows = json.loads(self.request('/api/venues')[1])['courts']
        expected = {
            'tokyo-sports-017': [(7700,19800), (24200,26400)],
            'tokyo-sports-018': [(3000,5000)],
            'tokyo-venue-e34356792fd2': [(8700,21600)],
            'tokyo-venue-3ba2d17ed46e': [(400,4700), (2200,18800)],
        }
        for row in rows:
            if row['id'] not in expected:
                continue
            with self.subTest(venue=row['id']):
                self.assertEqual([(r['minimum'],r['maximum']) for r in row['fee_ranges']], expected[row['id']])
                html = self.request('/venues?' + urlencode({'v_q': row['name']}))[1].decode()
                page = BeautifulSoup(html, 'html.parser')
                card = next(c for c in page.select('.venue-court-card') if c.h3.get_text() == row['name'])
                for preview, bounds in zip(card.select('.venue-rate-preview'), row['fee_ranges'][:2]):
                    self.assertEqual(preview.select_one('.venue-price-amount').get_text(), f"{bounds['minimum']:,}円〜{bounds['maximum']:,}円")
                    self.assertEqual(preview.select_one('.venue-price-unit').get_text(), bounds['unit'])
                self.assertNotIn('金額未取得', str(card))
                self.assertIsNone(card.select_one('.venue-tariff-more'))
                self.assertEqual(len(card.select('.venue-court-price a')), 1)
                link = card.select_one('.venue-fee-link')
                self.assertEqual(link['href'], row['fee_options'][0]['source_url'])
                self.assertEqual(link['target'], '_blank')
                self.assertNotRegex(card.get_text(), r'全\d+区分の料金')

    def test_followup_preserves_catalog_and_includes_source_for_every_amount(self):
        rows = {row['id']: row for row in json.loads(self.request('/api/venues')[1])['courts']}
        root = Path(__file__).resolve().parents[1]
        report = json.loads((root/'docs/venue-fee-followup-2026-10-12.json').read_text(encoding='utf-8'))
        self.assertEqual(len(rows), 1206)
        self.assertEqual(len(report), 26)
        self.assertEqual(sum(bool(r['fee_ranges']) for r in rows.values()), 595)
        for change in report:
            row = rows[change['id']]
            self.assertEqual(row['fee_ranges'], change['ranges'])
            self.assertEqual(row['fee_checked_at'], '2026-10-12')
            self.assertTrue(all(p['unit'] and p['conditions'] and p['source_url'].startswith('https://') for p in row['fee_options']))
        kakuhazu = rows['tokyo-venue-3ba2d17ed46e']['fee_options']
        self.assertTrue(any('会議室 Ｂ' in p['label'] and p['amount'] == 400 for p in kakuhazu))
        restricted = [p for p in kakuhazu if '和室Ⅱ' in p['label']]
        self.assertTrue(restricted)
        self.assertTrue(all('夜間' in p['label'] and p['amount'] in (600,1200) for p in restricted))

    def test_pdf_pairs_skip_unavailable_slots_and_inherit_room_names(self):
        from collect_venue_fee_followup import parse_community_tables
        header = ['施設使用料',None,None,None,None,None,None,None,None,None]
        periods = [None,None,None,'午前','午後1','午後2','夜間1','夜間2','全日',None]
        table = [header, periods,
                 ['会議室','Ａ','30名','600','600','600','700','700','2,900',None],
                 [None,None,None,'1,200','1,200','1,200','1,500','1,500','5,900',None],
                 [None,'Ｂ','24名','400','400','400','500','500','2,200',None],
                 [None,None,None,'900','900','900','1,100','1,100','4,400',None],
                 ['和室Ⅱ',None,'20名','‐','‐','‐','600','600','‐',None],
                 [None,None,None,'‐','‐','‐','1,200','1,200','‐',None]]
        result = parse_community_tables([[table]], [{'id': 'test', 'name':'四谷地域センター'}])
        plans = result[0]['fee_options']
        self.assertEqual(len(plans), 28)
        self.assertTrue(any('会議室 Ｂ' in p['label'] for p in plans))
        table[-1][3] = '100'
        with self.assertRaises(ValueError):
            parse_community_tables([[table]], [{'id':'test','name':'四谷地域センター'}])


if __name__ == '__main__':
    import unittest
    unittest.main()
