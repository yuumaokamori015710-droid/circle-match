"""Exact tariffs, restricted free use, closure and prior-data preservation."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'outputs'))
from venues.sports_catalog import get_catalog, has_price, filter_catalog
import record_venue_fee_review_20261027 as review


class October27VenueReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {r['id']: r for r in get_catalog()['courts']}

    def ranges(self, ident):
        return {r['unit']: (r['minimum'], r['maximum']) for r in self.rows[ident]['fee_ranges']}

    def test_counts_and_exact_published_records(self):
        self.assertEqual(len(set(review.REVIEWED_IDS)), 26)
        self.assertEqual(len(review.reviewed_fees()), 14)
        self.assertEqual(len(review.reviewed_policies()), 15)
        for entry in review.reviewed_fees():
            row = self.rows[entry['id']]
            self.assertEqual(row['fee_options'], entry['fee_options'])
            self.assertEqual(row['fee_note'], entry['fee_note'])
            self.assertEqual(row['fee_checked_at'], review.CHECKED)
        for entry in review.reviewed_policies():
            self.assertEqual(self.rows[entry['id']]['cancellation'], entry)
        self.assertEqual(len(self.rows), 1206)
        self.assertEqual(sum(has_price(r) for r in self.rows.values()), 830)
        self.assertEqual(sum(not has_price(r) for r in self.rows.values()), 376)
        self.assertEqual(sum(not has_price(r) and r['availability_status'] != 'SUSPENDED'
                             for r in self.rows.values()), 367)

    def test_holds_not_free_or_legacy_tariffs(self):
        for ident in review.HOLDS:
            self.assertFalse(has_price(self.rows[ident]))
            self.assertEqual(self.rows[ident]['fee_ranges'], [])

    def test_hachioji_baseball_not_lighting_or_other_space(self):
        for index, amount in [(0, 8000), (1, 8000), (4, 4000), (5, 2000), (10, 1000)]:
            self.assertEqual(self.ranges(review.HACHIOJI[index]), {'野球場1面・2時間': (amount, amount)})
        self.assertEqual(self.ranges(review.HACHIOJI[2]), {'ソフトボール場1面・2時間': (2000, 2000)})
        self.assertIn('一般野球には使用できません', self.rows[review.HACHIOJI[2]]['fee_note'])
        self.assertIn('18,000円', self.rows[review.HACHIOJI[0]]['fee_note'])
        self.assertEqual(self.ranges(review.HACHIOJI[9]), {'野球場1面・2時間': (2000, 2000),
                                                        'ソフトボール場1面・2時間': (1000, 1000)})

    def test_track_personal_and_group_not_mixed(self):
        self.assertEqual(self.ranges(review.HACHIOJI[3]), {'陸上競技場・4時間': (20000, 20000)})
        self.assertEqual(self.ranges(review.HACHIOJI[6]), {'個人陸上利用・1人1回': (50, 200)})
        self.assertIn('団体占有不可', self.rows[review.HACHIOJI[6]]['fee_note'])
        self.assertIn('15,000円', self.rows[review.HACHIOJI[3]]['fee_note'])

    def test_kita_free_only_registered_juniors(self):
        for ident, maximum in [(review.KITA[0], 2920), (review.KITA[2], 1200)]:
            self.assertEqual(self.ranges(ident), {'野球場1面・2時間': (0, maximum)})
            self.assertIn('区外少年登録不可', self.rows[ident]['fee_note'])
        self.assertEqual(self.ranges(review.KITA[1]), {'少年野球場1面・2時間': (0, 0)})
        self.assertIn('一般成人', self.rows[review.KITA[1]]['fee_note'])
        self.assertIn('9,080円', self.rows[review.KITA[0]]['fee_note'])
        free = {r['id'] for r in review.reviewed_fees() if any(p['amount'] == 0 for p in r['fee_options'])}
        self.assertEqual(free, set(review.KITA))

    def test_koto_units_and_junior_conditions(self):
        self.assertEqual(self.ranges(review.KOTO[2]), {'軟式野球場1面・2時間': (2700, 3700),
                                                     '少年野球場1面・2時間': (650, 800)})
        self.assertEqual(self.ranges(review.KOTO[3]), {'野球場・ソフトボール場1面・2時間': (2700, 3700),
                                                     '庭球場1面・1時間': (1100, 1800)})
        self.assertIn('区内小中学生登録団体のみ', self.rows[review.KOTO[2]]['fee_note'])
        self.assertIn('壁打ちの無料', self.rows[review.KOTO[3]]['fee_note'])

    def test_cancellation_not_fabricated_weather_refunds(self):
        for ident in [review.KITA[0], review.KITA[2]]:
            text = self.rows[ident]['cancellation']['summary']
            for phrase in ['14日前', '13～7日前', '6日前', '未払い', '電話不可']:
                self.assertIn(phrase, text)
        for ident in review.HACHIOJI:
            if ident != review.HACHIOJI[7]:
                self.assertIn('翌々月1日', self.rows[ident]['cancellation']['summary'])
                self.assertIn('予約制限', self.rows[ident]['cancellation']['summary'])
        for ident in review.KOTO[2:]:
            self.assertIn('自動返金とは扱いません', self.rows[ident]['cancellation']['summary'])

    def test_kameido_closed_retained_but_hidden(self):
        row = self.rows[review.KOTO[0]]
        self.assertEqual(row['availability_status'], 'SUSPENDED')
        self.assertEqual(row['availability_note'], review.CLOSURE_NOTE)
        visible = filter_catalog(list(self.rows.values()), {'q': row['name']})
        self.assertNotIn(row['id'], [r['id'] for r in visible])
        shown = filter_catalog(list(self.rows.values()), {'q': row['name'], 'show_suspended': '1'})
        self.assertIn(row['id'], [r['id'] for r in shown])

    def test_original_fields_and_exact_prior_review_prefix(self):
        for name in ['tokyo_tennis.json', 'tokyo_sports.json', 'tokyo_expansion.json',
                     'fee_plans.json', 'cancellation_policies.json']:
            rel = 'outputs/venues/catalogs/' + name
            previous = json.loads(subprocess.check_output(['git', 'show', review.BASE + ':' + rel], cwd=ROOT))
            current = json.loads((ROOT / rel).read_bytes())
            if not name.startswith('tokyo_'):
                self.assertEqual(previous, current[:len(previous)])
                continue
            self.assertEqual([r['id'] for r in previous], [r['id'] for r in current])
            for before, after in zip(previous, current):
                allowed = {'availability_status', 'availability_note', 'checked_at', 'sources'} if before['id'] == review.KOTO[0] else set()
                self.assertEqual(set(before), set(after))
                for key in set(before) - allowed:
                    self.assertEqual(before[key], after[key], (before['id'], key))
                if allowed:
                    self.assertEqual(after['sources'], before['sources'] + [{'title': '公式の休場・再開未定案内', 'url': review.CLOSURE_SOURCE}])
                    self.assertEqual(after['checked_at'], review.CHECKED)

    def test_idempotence_and_conflict_preflight(self):
        paths = [review.CATALOGS / n for n in ['tokyo_expansion.json', 'fee_plans.json', 'cancellation_policies.json']]
        before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
        subprocess.run([sys.executable, '-B', '-X', 'utf8', str(ROOT / 'scripts/record_venue_fee_review_20261027.py')], check=True, capture_output=True)
        self.assertEqual(before, [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths])
        fake = dict(self.rows[review.KITA[0]], fee_checked_at='2000-01-01')
        rows = [fake if r['id'] == fake['id'] else r for r in self.rows.values()]
        with patch.object(review, 'get_catalog', return_value={'courts': rows}), patch.object(review, 'append_reviews') as append:
            with self.assertRaises(ValueError):
                review.main()
            append.assert_not_called()


if __name__ == '__main__':
    unittest.main()
