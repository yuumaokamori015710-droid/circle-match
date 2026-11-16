"""Verify the November 14 free-base scope, eligibility and append-only changes."""
import json
import subprocess
import sys
import unittest
from urllib.parse import urlencode

import record_venue_fee_review_20261114 as review
from test_venues import IsolatedAppHttpCase


class November14VenueReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {r['id']: r for r in review.get_catalog()['courts']}

    def test_saved_scopes_and_inventory(self):
        self.assertEqual(len(set(review.REVIEWED_IDS)), 26)
        self.assertEqual(len(review.reviewed_fees()), 24)
        self.assertEqual(len(self.rows), 1206)
        later = [r for r in self.rows.values() if r.get('fee_checked_at', '') > review.CHECKED]
        unpriced = [r for r in self.rows.values() if not review.has_price(r)]
        self.assertEqual(len(unpriced) + len(later), 158)
        self.assertEqual(sum(r['availability_status'] != 'SUSPENDED' for r in unpriced + later), 147)
        for fee in review.reviewed_fees():
            row = self.rows[fee['id']]
            self.assertEqual(row['fee_checked_at'], review.CHECKED)
            self.assertEqual(row['fee_options'], fee['fee_options'])
            self.assertEqual(row['fee_note'], fee['fee_note'])
        self.assertFalse(review.has_price(self.rows[review.HOLDS[0]]))
        self.assertTrue(review.has_price(self.rows[review.RECHECKS[0]]))

    def test_daytime_base_is_not_an_all_in_hourly_price(self):
        self.assertEqual(len(review.HARD_ONLY), 8)
        self.assertEqual(review.SOFT_ONLY, {'28ea9ad4b487'})
        for suffix in review.SCHOOLS:
            row = self.rows['school-' + suffix]
            self.assertEqual([(r['unit'], r['minimum'], r['maximum']) for r in row['fee_ranges']],
                             [(review.SCHOOL_UNIT, 0, 0)])
            self.assertIsNone(row['price_per_hour'])
            self.assertIsNone(row['price_from'])
            self.assertIsNone(row['cancellation'])
            for phrase in ('照明等の光熱費・保険料は含みません', '不特定多数の活動は不可',
                           '10人以上', '満20歳以上', '毎年度の登録'):
                self.assertIn(phrase, row['fee_note'])
            sport = '軟式のみ' if suffix in review.SOFT_ONLY else '硬式のみ' if suffix in review.HARD_ONLY else '硬式・軟式'
            self.assertIn('屋外庭球場（' + sport + '）', row['fee_note'])

    def test_append_only_and_idempotent(self):
        names = ['tokyo_tennis.json', 'tokyo_sports.json', 'tokyo_expansion.json',
                 'fee_plans.json', 'cancellation_policies.json']
        before = [(review.CATALOGS / name).read_bytes() for name in names]
        for name, raw in zip(names, before):
            base = subprocess.check_output(['git', 'show', review.BASE + ':outputs/venues/catalogs/' + name],
                                           cwd=review.ROOT)
            if name.startswith('tokyo_'):
                self.assertEqual(raw.replace(b'\r\n', b'\n'), base.replace(b'\r\n', b'\n'))
                continue
            old, new = json.loads(base), json.loads(raw)
            additions = review.reviewed_fees() if name == 'fee_plans.json' else []
            self.assertEqual(new[:len(old) + len(additions)], old + additions)
            self.assertTrue(all(r['checked_at'] > review.CHECKED for r in new[len(old) + len(additions):]))
        subprocess.run([sys.executable, '-B', str(review.ROOT / 'scripts/record_venue_fee_review_20261114.py')],
                       check=True, capture_output=True)
        self.assertEqual(before, [(review.CATALOGS / name).read_bytes() for name in names])


class November14VenuePublicTests(IsolatedAppHttpCase):
    def test_new_base_fees_and_restrictions_render(self):
        for name, sport in [('世田谷泉高等学校', '硬式・軟式'), ('田園調布高等学校', '軟式のみ'),
                            ('三田高等学校', '硬式のみ')]:
            with self.subTest(venue=name):
                status, body, _ = self.request('/venues?' + urlencode({'v_q': name}))
                self.assertEqual(status, 200)
                for phrase in ('無料', review.SCHOOL_UNIT, review.SCHOOL_FEE, '屋外庭球場（' + sport + '）',
                               '照明等の光熱費・保険料は含みません', '不特定多数の活動は不可'):
                    self.assertTrue(phrase in body.decode(), phrase)
