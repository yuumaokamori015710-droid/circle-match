"""Verify the November 10 source scopes, preservation and public rendering."""
import json
import subprocess
import sys
import unittest
from urllib.parse import urlencode

import record_venue_fee_review_20261110 as review
from test_venues import IsolatedAppHttpCase


class November10VenueReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {r['id']: r for r in review.get_catalog()['courts']}

    def ranges(self, ident):
        return {r['unit']: (r['minimum'], r['maximum']) for r in self.rows[ident]['fee_ranges']}

    def test_saved_price_and_policy_scope(self):
        self.assertEqual(len(set(review.REVIEWED_IDS)), 23)
        self.assertEqual(len(review.reviewed_fees()), 22)
        self.assertEqual(len(review.reviewed_policies()), 6)
        self.assertEqual(len(self.rows), 1206)
        later = [r for r in self.rows.values() if r.get('fee_checked_at', '') > review.CHECKED]
        unpriced = [r for r in self.rows.values() if not review.has_price(r)]
        self.assertEqual(len(unpriced) + len(later), 206)
        self.assertEqual(sum(r['availability_status'] != 'SUSPENDED' for r in unpriced + later), 195)
        for fee in review.reviewed_fees():
            row = self.rows[fee['id']]
            self.assertEqual(row['fee_checked_at'], review.CHECKED)
            self.assertEqual(row['fee_options'], fee['fee_options'])
            self.assertEqual(row['fee_note'], fee['fee_note'])
        for policy in review.reviewed_policies():
            self.assertEqual(self.rows[policy['id']]['cancellation'], policy)
        from venue_review_test_helpers import assert_historical_hold
        for ident in review.HOLDS:
            assert_historical_hold(self, self.rows[ident])

    def test_units_and_eligibility_remain_separate(self):
        ranges = self.ranges(review.AKIRUDAI)
        self.assertEqual(len(ranges), 6)
        self.assertEqual(ranges['競技場貸切・午前9～12時（一般団体）'], (15800, 15800))
        self.assertEqual(ranges['競技場貸切・午後13～17時（都内小中学校）'], (6000, 6000))
        self.assertEqual(self.ranges(review.venue('f88290b749c0')), {
            '庭球場1面・1時間（照明別）': (1300, 1300),
            '野球場1面・1時間（照明別）': (1200, 1500),
        })
        self.assertEqual(self.ranges(review.venue('836ab2108e32')), {
            '兼用競技場全面・2時間（市内団体）': (1500, 1500),
            '兼用競技場全面・2時間（市外団体）': (3000, 3000),
        })
        for suffix in review.SCHOOLS:
            ident = 'school-' + suffix
            self.assertEqual(self.ranges(ident), {review.SCHOOL_UNIT: (0, 0)})
            self.assertTrue(review.has_price(self.rows[ident]))
            self.assertIsNone(self.rows[ident]['price_per_hour'])
            self.assertIn('照明等の光熱費・保険料は含みません', self.rows[ident]['fee_note'])

    def test_append_only_and_idempotent(self):
        names = ['tokyo_tennis.json', 'tokyo_sports.json', 'tokyo_expansion.json',
                 'fee_plans.json', 'cancellation_policies.json']
        before = [(review.CATALOGS / name).read_bytes() for name in names]
        for name, raw in zip(names, before):
            rel = 'outputs/venues/catalogs/' + name
            base = subprocess.check_output(['git', 'show', review.BASE + ':' + rel], cwd=review.ROOT)
            if name.startswith('tokyo_'):
                self.assertEqual(raw.replace(b'\r\n', b'\n'), base.replace(b'\r\n', b'\n'))
                continue
            old, new = json.loads(base), json.loads(raw)
            additions = review.reviewed_fees() if name == 'fee_plans.json' else review.reviewed_policies()
            self.assertEqual(new[:len(old) + len(additions)], old + additions)
            self.assertTrue(all(r['checked_at'] > review.CHECKED for r in new[len(old) + len(additions):]))
        subprocess.run([sys.executable, '-B', str(review.ROOT / 'scripts/record_venue_fee_review_20261110.py')],
                       check=True, capture_output=True)
        self.assertEqual(before, [(review.CATALOGS / name).read_bytes() for name in names])


class November10VenuePublicTests(IsolatedAppHttpCase):
    def test_tariffs_and_eligibility_in_directory(self):
        for name, expected in [
            ('秋留台公園', ('15,800円', '21,600円', review.PARK_RULE)),
            ('五反野野球場', ('1,100円', '利用前日・当日の自己都合は還付なし', review.ADACHI_CANCEL)),
            ('王子総合', ('無料', review.SCHOOL_UNIT, '照明等の光熱費・保険料は含みません')),
        ]:
            with self.subTest(venue=name):
                status, body, _ = self.request('/venues?' + urlencode({'v_q': name}))
                self.assertEqual(status, 200)
                for phrase in (name, *expected):
                    self.assertIn(phrase, body.decode())
