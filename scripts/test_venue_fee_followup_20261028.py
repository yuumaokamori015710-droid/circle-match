"""Exact units, eligibility, policy qualifications and prior-catalog preservation."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'outputs'))
from venues.sports_catalog import get_catalog, has_price
import record_venue_fee_review_20261028 as review


class October28VenueReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {r['id']: r for r in get_catalog()['courts']}

    def ranges(self, ident):
        return {r['unit']: (r['minimum'], r['maximum']) for r in self.rows[ident]['fee_ranges']}

    def test_exact_entries_and_counts(self):
        self.assertEqual(len(set(review.REVIEWED_IDS)), 21)
        self.assertEqual(len(review.reviewed_fees()), 12)
        self.assertEqual(len(review.reviewed_policies()), 12)
        for entry in review.reviewed_fees():
            row = self.rows[entry['id']]
            self.assertEqual(row['fee_options'], entry['fee_options'])
            self.assertEqual(row['fee_note'], entry['fee_note'])
            self.assertEqual(row['fee_checked_at'], review.CHECKED)
        for entry in review.reviewed_policies():
            self.assertEqual(self.rows[entry['id']]['cancellation'], entry)
        self.assertEqual(len(self.rows), 1206)
        self.assertEqual(sum(has_price(r) for r in self.rows.values()), 842)
        self.assertEqual(sum(not has_price(r) for r in self.rows.values()), 364)
        self.assertEqual(sum(not has_price(r) and r['availability_status'] != 'SUSPENDED' for r in self.rows.values()), 355)

    def test_holds_never_zero_or_unbookable_old_tariffs(self):
        for ident in review.HOLDS:
            self.assertFalse(has_price(self.rows[ident]))
            self.assertEqual(self.rows[ident]['fee_ranges'], [])
        self.assertIn('貸切受付停止', self.rows['tokyo-gym-aa77f48e78d0']['cancellation']['summary'])
        self.assertFalse(any(p['amount'] == 0 for e in review.reviewed_fees() for p in e['fee_options']))

    def test_district_rooms_and_discount_eligibility_are_separate(self):
        for ident, slug, rooms in review.DISTRICTS:
            ranges = self.ranges(ident)
            self.assertEqual(len(ranges), 2 * len(rooms))
            for room, amount in rooms:
                self.assertEqual(ranges[room + '・1時間（一般）'], (amount, amount))
                self.assertEqual(ranges[room + '・1時間（地域集会施設登録団体）'], (amount // 2, amount // 2))
            for phrase in ['半数以上', '新システム', '不特定多数', '開放中は貸切不可']:
                self.assertIn(phrase, self.rows[ident]['fee_note'])

    def test_hall_periods_are_not_hourly_conversions(self):
        hikari = self.ranges(review.HIKARI)
        self.assertEqual(hikari['多目的ホール・3時間'], (5400, 5400))
        self.assertEqual(hikari['多目的ホール・4時間'], (7200, 7200))
        self.assertEqual(hikari['会議室1・3時間'], (2100, 2100))
        self.assertEqual(hikari['集会室1・2併用・4時間'], (4400, 4400))
        self.assertEqual(self.ranges(review.SEKI), {'多目的ホール・3時間': (5400, 5400),
                                                  '多目的ホール・4時間': (7200, 7200), 'リハーサル室・1時間': (400, 400)})

    def test_field_units_not_lighting_or_personal_prices(self):
        self.assertEqual(self.ranges(review.TRACK), {'新河岸陸上競技場・1時間': (3600, 3600)})
        self.assertEqual(self.ranges(review.MUSASHINO), {'軟式野球場1面・2時間（市内・参加料なし）': (2000, 2000),
                                                       '軟式野球場1面・2時間（市外・参加料なし）': (4000, 4000)})
        self.assertIn('併用額は未確認', self.rows[review.MUSASHINO]['fee_note'])
        self.assertEqual(self.ranges(review.CHOFU[0]), {'野球場1面・2時間': (3000, 3000)})
        self.assertEqual(self.ranges(review.CHOFU[1]), {'野球場1面・2時間（市内）': (1200, 1200),
            '野球場1面・2時間（市外）': (2400, 2400), '野球場1面・3時間（市内・照明別）': (1800, 1800),
            '野球場1面・3時間（市外・照明別）': (3600, 3600)})

    def test_cancellation_penalties_are_not_money_or_weather_guesses(self):
        for ident in review.CHOFU:
            text = self.rows[ident]['cancellation']['summary']
            for phrase in ['1か月', '3か月', '金銭の取消料ではありません', '推測しません']:
                self.assertIn(phrase, text)
        seki = self.rows[review.SEKI]['cancellation']['summary']
        for phrase in ['30日', '90日', 'Web', '金銭の取消料・還付率', '未確認']:
            self.assertIn(phrase, seki)
        self.assertIn('60分以内', self.rows[review.MUSASHINO]['cancellation']['summary'])
        self.assertIn('1時間）を超過', self.rows[review.MUSASHINO]['cancellation']['summary'])
        self.assertIn('無断100%', self.rows['private-chitose']['cancellation']['summary'])

    def test_original_catalogs_and_prior_fee_policy_prefix_unchanged(self):
        for name in ['tokyo_tennis.json', 'tokyo_sports.json', 'tokyo_expansion.json', 'fee_plans.json', 'cancellation_policies.json']:
            rel = 'outputs/venues/catalogs/' + name
            previous = subprocess.check_output(['git', 'show', review.BASE + ':' + rel], cwd=ROOT)
            current = (ROOT / rel).read_bytes()
            if name.startswith('tokyo_'):
                self.assertEqual(json.loads(previous), json.loads(current))
            else:
                old, new = json.loads(previous), json.loads(current)
                self.assertEqual(old, new[:len(old)])

    def test_idempotence_and_preflight_conflicts(self):
        paths = [review.CATALOGS / name for name in ['fee_plans.json', 'cancellation_policies.json']]
        before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
        subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/record_venue_fee_review_20261028.py')], check=True, capture_output=True)
        self.assertEqual(before, [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths])
        fake = dict(self.rows[review.TRACK], fee_checked_at='2000-01-01')
        rows = [fake if r['id'] == fake['id'] else r for r in self.rows.values()]
        with patch.object(review, 'get_catalog', return_value={'courts': rows}), patch.object(review, 'append_reviews') as append:
            with self.assertRaises(ValueError):
                review.main()
            append.assert_not_called()


if __name__ == '__main__':
    unittest.main()
