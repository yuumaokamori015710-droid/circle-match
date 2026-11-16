"""Verify November 16 tariff units, unknown holds and append-only preservation."""
import json
import subprocess
import sys
import unittest
from urllib.parse import urlencode

import record_venue_fee_review_20261116 as review
from test_venues import IsolatedAppHttpCase


class November16VenueReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {r['id']: r for r in review.get_catalog()['courts']}

    def ranges(self, ident):
        return {r['unit']: (r['minimum'], r['maximum']) for r in self.rows[ident]['fee_ranges']}

    def test_saved_scopes_and_inventory(self):
        self.assertEqual(len(set(review.REVIEWED_IDS)), 26)
        self.assertEqual(len(review.reviewed_fees()), 22)
        self.assertEqual(len(review.reviewed_policies()), 2)
        self.assertEqual(len(self.rows), 1206)
        later = [r for r in self.rows.values() if r.get('fee_checked_at', '') > review.CHECKED]
        unpriced = [r for r in self.rows.values() if not review.has_price(r)]
        self.assertEqual(len(unpriced) + len(later), 136)
        self.assertEqual(sum(r['availability_status'] != 'SUSPENDED' for r in unpriced + later), 125)
        for fee in review.reviewed_fees():
            row = self.rows[fee['id']]
            self.assertEqual(row['fee_checked_at'], review.CHECKED)
            self.assertEqual(row['fee_options'], fee['fee_options'])
            self.assertEqual(row['fee_note'], fee['fee_note'])
        for policy in review.reviewed_policies():
            self.assertEqual(self.rows[policy['id']]['cancellation'], policy)
        for ident in review.HOLDS:
            self.assertFalse(review.has_price(self.rows[ident]))
        self.assertEqual(self.rows['private-chitose']['cancellation']['checked_at'], '2026-10-28')

    def test_unlike_units_and_additional_costs_remain_explicit(self):
        self.assertEqual(self.ranges('private-nanbu'), {
            'コート1面・1時間（税込・施設料別）': (3700, 7300),
            'コート半面・1時間（税込・2名まで・施設料別）': (2000, 3500),
        })
        for phrase in ('1人300円', '登録料600円', '超過人数×時間×550円', '日没後', '記載差'):
            self.assertIn(phrase, self.rows['private-nanbu']['fee_note'])
        self.assertEqual(self.ranges('private-kugayama'), {'貸コート1面・1時間': (2200, 6600)})
        self.assertIn('11時以降', self.rows['private-nanbu']['cancellation']['summary'])
        self.assertIn('記載差', self.rows['private-nanbu']['cancellation']['summary'])
        self.assertIn('雨天による中止', self.rows['private-kugayama']['cancellation']['summary'])
        self.assertEqual(len(review.SCHOOLS), 20)
        self.assertEqual(len(review.HARD_ONLY), 11)
        for suffix in review.SCHOOLS:
            row = self.rows['school-' + suffix]
            self.assertEqual(self.ranges(row['id']), {review.SCHOOL_UNIT: (0, 0)})
            self.assertIsNone(row['price_per_hour'])
            self.assertIsNone(row['cancellation'])
            self.assertIn('照明等の光熱費・保険料は含みません', row['fee_note'])
            self.assertIn('不特定多数の活動は不可', row['fee_note'])
            self.assertIn('硬式のみ' if suffix in review.HARD_ONLY else '硬式・軟式', row['fee_note'])

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
            additions = review.reviewed_fees() if name == 'fee_plans.json' else review.reviewed_policies()
            self.assertEqual(new[:len(old) + len(additions)], old + additions)
            self.assertTrue(all(r['checked_at'] > review.CHECKED for r in new[len(old) + len(additions):]))
        subprocess.run([sys.executable, '-B', str(review.ROOT / 'scripts/record_venue_fee_review_20261116.py')],
                       check=True, capture_output=True)
        self.assertEqual(before, [(review.CATALOGS / name).read_bytes() for name in names])


class November16VenuePublicTests(IsolatedAppHttpCase):
    def test_new_tariffs_and_restrictions_render(self):
        for name, phrases in [
            ('南部テニスクラブ', ('3,700円', '7,300円', '2,000円', '1人300円', '登録料600円', '記載差')),
            ('久我山オートテニス', ('2,200円', '6,600円', '貸コート1面・1時間', '雨天による中止')),
            ('三鷹中等教育学校', ('無料', review.SCHOOL_UNIT, '屋外庭球場（硬式のみ）', '不特定多数の活動は不可')),
        ]:
            with self.subTest(venue=name):
                status, body, _ = self.request('/venues?' + urlencode({'v_q': name}))
                self.assertEqual(status, 200)
                for phrase in phrases:
                    self.assertTrue(phrase in body.decode(), phrase)
