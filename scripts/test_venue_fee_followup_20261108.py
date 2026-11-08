"""Check source-matched venue additions, historical data and public rendering."""
import json
from pathlib import Path
import subprocess
import sys
import unittest
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'outputs'))
from venues.sports_catalog import get_catalog, has_price
import record_venue_fee_review_20261108 as review
from test_venues import IsolatedAppHttpCase


class November8VenueReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {r['id']: r for r in get_catalog()['courts']}

    def ranges(self, suffix):
        row = self.rows[review.venue(suffix)]
        return {r['unit']: (r['minimum'], r['maximum']) for r in row['fee_ranges']}

    def test_scope_and_saved_data(self):
        self.assertEqual(len(set(review.REVIEWED_IDS)), 25)
        self.assertEqual(len(self.rows), 1206)
        later = sum(has_price(r) and r.get('fee_checked_at', '') > review.CHECKED for r in self.rows.values())
        self.assertEqual(sum(not has_price(r) for r in self.rows.values()) + later, 228)
        self.assertEqual(len(review.reviewed_fees()), 20)
        self.assertEqual(len(review.reviewed_policies()), 10)
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

    def test_verified_zero_and_youth_eligibility(self):
        free = [r for r in review.reviewed_fees() if any(f['amount'] == 0 for f in r['fee_options'])]
        self.assertEqual({r['id'] for r in free}, {
            review.venue(suffix) for suffix in
            ('c282bded258a', '456ad6cd0311', '40fd2672b512', 'd7f8d384bd4b')
        })
        for fee in free:
            self.assertTrue(has_price(self.rows[fee['id']]))
            self.assertIn('無料と明記', fee['fee_note'])
        self.assertIn('中学生以下', self.rows[review.venue('c282bded258a')]['fee_note'])

    def test_duration_area_lighting_and_age_are_distinct(self):
        gym = self.rows['tokyo-gym-a231878afdcf']
        ranges = {r['unit']: (r['minimum'], r['maximum']) for r in gym['fee_ranges']}
        self.assertEqual(len(ranges), 8)
        self.assertEqual(ranges['大体育室全面・3時間（団体貸切）'], (6600, 6600))
        self.assertEqual(ranges['大体育室1/3面・12時間（団体貸切）'], (8800, 8800))
        self.assertEqual(self.ranges('17f2a6ab5bfc'), {
            '野球場1面・2時間（昼間）': (2000, 2000),
            '野球場1面・2時間（夜間・照明込み）': (8000, 8000),
        })
        self.assertEqual(self.ranges('4f32c019760c')['野球場1面・2時間（市外・大人）'], (5250, 6900))
        self.assertEqual(self.ranges('aed3f0dc916c')['野球場1面・2時間（市外・19～21時・照明込み）'], (24000, 24000))
        self.assertIn('金銭取消料', self.rows[review.venue('336735e641ac')]['cancellation']['summary'])

    def test_append_only_and_idempotent(self):
        catalogs = ['tokyo_tennis.json', 'tokyo_sports.json', 'tokyo_expansion.json',
                    'fee_plans.json', 'cancellation_policies.json']
        before = [(review.CATALOGS / name).read_bytes() for name in catalogs]
        for name, raw in zip(catalogs, before):
            rel = 'outputs/venues/catalogs/' + name
            base = subprocess.check_output(['git', 'show', review.BASE + ':' + rel], cwd=ROOT)
            if name.startswith('tokyo_'):
                self.assertEqual(raw.replace(b'\r\n', b'\n'), base.replace(b'\r\n', b'\n'))
            else:
                old, new = json.loads(base), json.loads(raw)
                self.assertEqual(new[:len(old)], old)
                expected = review.reviewed_fees() if name == 'fee_plans.json' else review.reviewed_policies()
                self.assertEqual(new[len(old):len(old) + len(expected)], expected)
                self.assertTrue(all(r['checked_at'] > review.CHECKED for r in new[len(old) + len(expected):]))
        subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/record_venue_fee_review_20261108.py')],
                       check=True, capture_output=True)
        self.assertEqual(before, [(review.CATALOGS / name).read_bytes() for name in catalogs])


class November8VenuePublicTests(IsolatedAppHttpCase):
    def test_main_gym_tariff_and_cancellation_in_page_and_api(self):
        name = '小金井市総合体育館'
        query = urlencode({'view': 'page', 'q': name, 'limit': 5})
        status, body, headers = self.request('/api/venues?' + query)
        self.assertEqual(status, 200)
        row, = [r for r in json.loads(body)['courts'] if r['id'] == 'tokyo-gym-a231878afdcf']
        self.assertEqual(row['fee_checked_at'], review.CHECKED)
        self.assertEqual(row['cancellation']['source_url'], review.KOGANEI_CANCEL)
        self.assertIsNone(row['price_per_hour'])
        self.assertIn('ETag', headers)
        status, body, _ = self.request('/venues?' + urlencode({'v_q': name}))
        self.assertEqual(status, 200)
        text = body.decode()
        for phrase in [name, '6,600円', '26,400円', review.KOGANEI]:
            self.assertIn(phrase, text)
