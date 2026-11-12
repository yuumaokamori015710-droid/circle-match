"""Verify the November 12 tariff scopes and append-only preservation."""
import json
import subprocess
import sys
import unittest
from urllib.parse import urlencode

import record_venue_fee_review_20261112 as review
from test_venues import IsolatedAppHttpCase


class November12VenueReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {r['id']: r for r in review.get_catalog()['courts']}

    def ranges(self, ident):
        return {r['unit']: (r['minimum'], r['maximum']) for r in self.rows[ident]['fee_ranges']}

    def test_saved_scopes_and_inventory(self):
        self.assertEqual(len(set(review.REVIEWED_IDS)), 26)
        self.assertEqual(len(review.reviewed_fees()), 24)
        self.assertEqual(len(review.reviewed_policies()), 4)
        self.assertEqual(len(self.rows), 1206)
        later = [r for r in self.rows.values() if r.get('fee_checked_at', '') > review.CHECKED]
        unpriced = [r for r in self.rows.values() if not review.has_price(r)]
        self.assertEqual(len(unpriced) + len(later), 182)
        self.assertEqual(sum(r['availability_status'] != 'SUSPENDED' for r in unpriced + later), 171)
        for fee in review.reviewed_fees():
            row = self.rows[fee['id']]
            self.assertEqual(row['fee_checked_at'], review.CHECKED)
            self.assertEqual(row['fee_options'], fee['fee_options'])
            self.assertEqual(row['fee_note'], fee['fee_note'])
        for policy in review.reviewed_policies():
            self.assertEqual(self.rows[policy['id']]['cancellation'], policy)
        self.assertFalse(review.has_price(self.rows[review.HOLDS[0]]))

    def test_units_and_conditions_do_not_mix(self):
        self.assertEqual(self.ranges(review.PUBLIC[0]), {
            '庭球場1面・2時間（区内・照明別）': (1200, 1600),
            '庭球場1面・2時間（区外・照明別）': (1800, 2400),
        })
        for ident in review.PUBLIC[1:3]:
            self.assertEqual(len(self.ranges(ident)), 4)
            self.assertEqual(self.ranges(ident)['庭球場1面・1時間（一般・夜間）'], (1450, 1450))
            self.assertEqual(self.ranges(ident)['庭球場1面・1時間（中学生以下・昼間）'], (150, 150))
            self.assertIn('原則2時間単位', self.rows[ident]['fee_note'])
        self.assertEqual(self.ranges(review.PUBLIC[3])['庭球場1面・2時間（市内）'], (1020, 1020))
        self.assertEqual(self.ranges(review.PUBLIC[3])['庭球場1面・1時間・春秋17～18時枠（市外）'], (1020, 1020))
        self.assertEqual(self.ranges(review.PUBLIC[4])['クレイB面1面・2時間（市内）'], (400, 400))
        self.assertEqual(self.ranges(review.PUBLIC[4])['砂入り人工芝A・C面1面・2時間（市外）'], (1400, 1400))
        for suffix in review.SCHOOLS:
            row = self.rows['school-' + suffix]
            self.assertEqual(self.ranges(row['id']), {review.SCHOOL_UNIT: (0, 0)})
            self.assertIsNone(row['price_per_hour'])
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
        subprocess.run([sys.executable, '-B', str(review.ROOT / 'scripts/record_venue_fee_review_20261112.py')],
                       check=True, capture_output=True)
        self.assertEqual(before, [(review.CATALOGS / name).read_bytes() for name in names])


class November12VenuePublicTests(IsolatedAppHttpCase):
    def test_new_tariffs_and_restrictions_render(self):
        for name, phrases in [
            ('市民深大寺', ('400円', '1,400円', 'クレイB面1面・2時間（市内）', review.CHOFU)),
            ('前川公園テニス', ('1,450円', '150円', '原則2時間単位', '全施設の予約停止ではありません')),
            ('三ツ木庭球場', ('1,020円', '2,040円', '510円', '春秋17～18時枠', '2026-11-06')),
            ('戸山高等学校', ('無料', review.SCHOOL_UNIT, '不特定多数の活動は不可')),
        ]:
            with self.subTest(venue=name):
                status, body, _ = self.request('/venues?' + urlencode({'v_q': name}))
                self.assertEqual(status, 200)
                for phrase in phrases:
                    self.assertIn(phrase, body.decode())
