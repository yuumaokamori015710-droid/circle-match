"""Preserve identities, exact time units, eligibility and current closures."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'outputs'))
from venues.sports_catalog import get_catalog, has_price
import record_venue_fee_review_20261023 as review


class October23VenueReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {r['id']: r for r in get_catalog()['courts']}

    def ranges(self, ident):
        return {r['unit']: (r['minimum'], r['maximum']) for r in self.rows[ident]['fee_ranges']}

    def test_twenty_reviews_eighteen_prices_thirteen_policies(self):
        self.assertEqual(len(set(review.REVIEWED_IDS)), 20)
        self.assertEqual(len(review.reviewed_fees()), 18)
        for entry in review.reviewed_fees():
            row = self.rows[entry['id']]
            self.assertEqual(row['fee_options'], entry['fee_options'])
            self.assertEqual(row['fee_note'], entry['fee_note'])
            self.assertEqual(row['fee_checked_at'], review.CHECKED)
            self.assertIsNone(row['price_from'])
        self.assertEqual(len(review.reviewed_policies()), 13)
        for entry in review.reviewed_policies():
            self.assertEqual(self.rows[entry['id']]['cancellation'], entry)
        self.assertEqual(len(self.rows), 1206)
        later_priced = sum(has_price(r) and r.get('fee_checked_at', '') > review.CHECKED
                           for r in self.rows.values())
        self.assertEqual(sum(has_price(r) for r in self.rows.values()) - later_priced, 767)
        self.assertEqual(sum(not has_price(r) for r in self.rows.values()) + later_priced, 439)
        self.assertEqual(sum(not has_price(r) and r['availability_status'] != 'SUSPENDED'
                             for r in self.rows.values()) + later_priced, 431)

    def test_higashi_ground_rental_not_lighting_or_closed_west(self):
        self.assertEqual(self.ranges(review.HIGASHI[0]), {'グラウンド全面・1時間': (1200, 1200)})
        for ident in review.HIGASHI[1:3]:
            self.assertEqual(self.ranges(ident), {'運動広場全面・1時間': (300, 300)})
        self.assertIn('1時間1,900円', self.rows[review.HIGASHI[0]]['fee_note'])
        closed = self.rows[review.HIGASHI[3]]
        self.assertFalse(has_price(closed))
        self.assertEqual(closed['availability_status'], 'SUSPENDED')
        self.assertIn('2026年3月31日', closed['availability_note'])
        self.assertIsNone(closed['cancellation'])

    def test_higashi_gym_exact_rounding_and_different_slot_durations(self):
        ranges = self.ranges(review.HIGASHI[5])
        self.assertEqual(ranges['第1体育室半面・2時間10分'], (6800, 6800))
        self.assertEqual(ranges['第1体育室半面・2時間20分'], (7300, 7300))
        self.assertEqual(ranges['第1体育室4分の1面・2時間20分'], (3700, 3700))
        self.assertEqual(len(ranges), 6)
        self.assertEqual(self.ranges(review.HIGASHI[4]), {'体育室全面・2時間': (2400, 3600),
                                                       '体育室半面・2時間': (1200, 1800)})
        self.assertTrue(all(type(p['amount']) is int for r in review.reviewed_fees() for p in r['fee_options']))

    def test_kiyose_indoor_and_outdoor_cancellation_deadlines_differ(self):
        self.assertEqual(self.ranges(review.KIYOSE[0]), {'下宿運動公園広場全面・2時間': (1200, 6900)})
        self.assertEqual(self.ranges(review.KIYOSE[1]), {'競技場全面・3時間': (2900, 4350),
                                                      '競技場全面・4時間': (4000, 7800),
                                                      '競技場半面・3時間': (1450, 2175),
                                                      '競技場半面・4時間': (2000, 3900)})
        self.assertIn('前日まで30%', self.rows[review.KIYOSE[0]]['cancellation']['summary'])
        for ident in review.KIYOSE[1:]:
            self.assertIn('10日前まで30%', self.rows[ident]['cancellation']['summary'])
            self.assertIn('それ以降は還付なし', self.rows[ident]['cancellation']['summary'])

    def test_hirao_actual_free_overrides_nominal_fee_but_not_outside_fee(self):
        self.assertEqual(self.ranges(review.INAGI[0]), {'体育館全面・1時間': (0, 1020),
                                                      'グラウンド全面・1時間': (0, 680)})
        self.assertIn('市外未登録は窓口', self.rows[review.INAGI[0]]['fee_note'])
        self.assertIn('体育館はフットサル不可', self.rows[review.INAGI[0]]['fee_note'])
        self.assertEqual(self.ranges(review.INAGI[1]), {'多目的広場全面・3時間': (0, 0)})
        self.assertIn('団体登録・予約', self.rows[review.INAGI[1]]['fee_note'])
        self.assertEqual({r['id'] for r in review.reviewed_fees() if any(p['amount'] == 0 for p in r['fee_options'])},
                         {review.INAGI[0], review.INAGI[1]})

    def test_nagamine_commercial_prohibition_not_surcharge_permission(self):
        self.assertEqual(self.ranges(review.INAGI[2]), {'サッカー場1面・2時間': (4940, 19760),
                                                      'フットサル場1面・2時間': (3690, 14780)})
        note = self.rows[review.INAGI[2]]['fee_note']
        self.assertIn('不特定多数', note)
        self.assertIn('禁止', note)
        summary = self.rows[review.INAGI[2]]['cancellation']['summary']
        self.assertIn('30分以内', summary)
        self.assertIn('窓口・電話', summary)
        self.assertIn('一時中断', summary)
        for ident in review.INAGI[3:5]:
            summary = self.rows[ident]['cancellation']['summary']
            self.assertIn('翌日23時59分', summary)
            self.assertIn('電話申告は受付不可', summary)

    def test_inagi_gym_rounding_and_youth_soccer_limit(self):
        ranges = self.ranges(review.INAGI[5])
        self.assertEqual(ranges['メインアリーナ3分の1面・2時間50分'], (3580, 7160))
        self.assertEqual(ranges['ウエルネスアリーナ半面・2時間50分'], (2680, 5360))
        self.assertEqual(self.ranges(review.INAGI[3]), {'競技場全面・1時間': (2950, 5900)})
        self.assertIn('少年のみ', self.rows[review.INAGI[4]]['fee_note'])
        self.assertIn('許可を意味しません', self.rows[review.INAGI[4]]['fee_note'])

    def test_musashino_nonstandard_units_and_upcoming_closure(self):
        self.assertEqual(self.ranges(review.MUSASHINO[0]), {'緑町スポーツ広場全面・2時間': (6000, 12000),
                                                          '緑町スポーツ広場半面・2時間': (3000, 6000)})
        self.assertIn('2026年11月～2027年3月', self.rows[review.MUSASHINO[0]]['fee_note'])
        self.assertNotEqual(self.rows[review.MUSASHINO[0]]['availability_status'], 'SUSPENDED')
        self.assertEqual(self.ranges(review.MUSASHINO[1])['メインアリーナ半面・2時間45分'], (5310, 10620))
        self.assertEqual(self.ranges(review.MUSASHINO[2])['陸上競技場全面・全日8時間'], (36000, 72000))
        for ident in review.MUSASHINO:
            summary = self.rows[ident]['cancellation']['summary']
            self.assertIn('3日前まで取消料50%', summary)
            self.assertIn('予約当日', summary)

    def test_kokubunji_partial_closure_not_entire_site_or_old_gym_rate(self):
        hikari = self.rows[review.KOKUBUNJI[0]]
        self.assertEqual(hikari['fee_checked_at'], '2026-10-25')
        self.assertEqual(self.ranges(review.KOKUBUNJI[0]), {'第二体育室・2時間30分': (1000, 2000)})
        self.assertTrue(all(p['unit'].startswith('第二体育室') for p in hikari['fee_options']))
        self.assertNotEqual(hikari['availability_status'], 'SUSPENDED')
        self.assertIn('第一体育室', hikari['booking_note'])
        self.assertIn('第二体育室・フィットネスルームは利用可能', hikari['booking_note'])
        self.assertEqual(self.ranges(review.KOKUBUNJI[1]), {'第一体育室全面・2時間30分': (6000, 12000),
                                                         '第一体育室半面・2時間30分': (3000, 6000)})

    def test_all_original_fields_and_prior_reviews_preserved_except_documented_metadata(self):
        base = '9bea74907fed9d66b553b76ce803cfbfe312ef8f'
        permitted = {review.HIGASHI[3]: {'availability_status', 'availability_note', 'checked_at', 'sources'},
                     review.KOKUBUNJI[0]: {'booking_note', 'checked_at', 'sources'}}
        for name in ['tokyo_tennis.json', 'tokyo_sports.json', 'tokyo_expansion.json',
                     'fee_plans.json', 'cancellation_policies.json']:
            rel = 'outputs/venues/catalogs/' + name
            previous = json.loads(subprocess.check_output(['git', 'show', base + ':' + rel], cwd=ROOT))
            current = {r['id']: r for r in json.loads((ROOT / rel).read_bytes())}
            for before in previous:
                after = current[before['id']]
                allowed = permitted.get(before['id'], set()) if name == 'tokyo_expansion.json' else set()
                self.assertEqual(set(before), set(after))
                for key in set(before) - allowed:
                    self.assertEqual(before[key], after[key], (before['id'], key))
                if allowed:
                    self.assertEqual(after['sources'][:len(before['sources'])], before['sources'])
                    self.assertEqual(after['checked_at'], review.CHECKED)
                    if before['id'] == review.KOKUBUNJI[0]:
                        self.assertTrue(after['booking_note'].startswith(before['booking_note']))

    def test_import_idempotent_and_preflight_blocks_overwrite(self):
        paths = [review.CATALOGS / n for n in ['tokyo_expansion.json', 'fee_plans.json', 'cancellation_policies.json']]
        before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
        subprocess.run([sys.executable, '-X', 'utf8', str(ROOT / 'scripts/record_venue_fee_review_20261023.py')],
                       check=True, capture_output=True)
        self.assertEqual(before, [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths])
        fake = dict(self.rows[review.HIGASHI[0]], fee_checked_at='2000-01-01')
        rows = [fake if r['id'] == fake['id'] else r for r in self.rows.values()]
        with patch.object(review, 'get_catalog', return_value={'courts': rows}), patch.object(review, 'update_availability') as update:
            with self.assertRaises(ValueError):
                review.main()
            update.assert_not_called()
        with tempfile.TemporaryDirectory(dir=ROOT / 'work') as temporary:
            path = Path(temporary) / 'fees.json'
            path.write_text('[]', encoding='utf-8')
            review.append_reviews(path, review.reviewed_fees())
            before = path.read_bytes()
            with self.assertRaises(ValueError):
                review.append_reviews(path, [dict(review.reviewed_fees()[0], checked_at='2000-01-01')])
            self.assertEqual(path.read_bytes(), before)


if __name__ == '__main__':
    unittest.main()
