"""Scope, cancellation boundaries, source linkage and preservation for this batch."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'outputs'))
from venues.sports_catalog import get_catalog, filter_catalog
from record_venue_fee_review_20261018 import (reviewed_fees, reviewed_policies,
                                            append_reviews, REVIEWED_IDS, CLOSED)


class OfficialVenueReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {row['id']: row for row in get_catalog()['courts']}

    def ranges(self, ident):
        return {r['unit']: (r['minimum'], r['maximum']) for r in self.rows[ident]['fee_ranges']}

    def test_exact_existing_ids_and_ten_new_tariffs(self):
        self.assertEqual(len(set(REVIEWED_IDS)), 25)
        self.assertTrue(set(REVIEWED_IDS) <= self.rows.keys())
        self.assertEqual(len(reviewed_fees()), 10)
        for entry in reviewed_fees():
            row = self.rows[entry['id']]
            self.assertEqual(row['fee_checked_at'], '2026-10-18')
            self.assertEqual(row['fee_options'], entry['fee_options'])
            self.assertIsNone(row['price_from'])
            self.assertTrue(all(p['amount'] > 0 and p['conditions'] and p['source_url'].startswith('https://')
                                for p in row['fee_options']))

    def test_okubo_unequal_slots_and_lighting_are_separate(self):
        self.assertEqual(self.ranges('shinjuku-okubo'), {
            '庭球場1面・2時間': (1500, 1500), '庭球場1面・2時間30分': (1800, 1800)})
        self.assertIn('30分500円', self.rows['shinjuku-okubo']['fee_note'])

    def test_nishiochiai_does_not_advertise_free_adult_tennis(self):
        row = self.rows['tokyo-venue-144440cef349']
        self.assertEqual(self.ranges(row['id']), {'庭球場1面・2時間': (1500, 1500)})
        self.assertIn('少年野球場の無料料金とは別', row['fee_note'])
        self.assertIn('照明なし', row['fee_note'])

    def test_soccer_pitch_and_skateboard_rates_are_not_substituted(self):
        self.assertEqual(self.ranges('tokyo-venue-8a1449acfd44'), {'野球場1面・2時間': (5100, 5100)})
        self.assertIn('一般用サッカーゴールはなく', self.rows['tokyo-venue-8a1449acfd44']['fee_note'])
        self.assertEqual(self.ranges('tokyo-venue-be0319cd8fbd'), {'フットサル場1面・2時間以内': (2600, 2600)})
        self.assertIn('2時間1,100円', self.rows['tokyo-venue-be0319cd8fbd']['fee_note'])

    def test_river_fields_match_exact_sport_and_unit(self):
        for ident in ['tokyo-venue-6e8063869f46', 'tokyo-venue-f22c36060e5d']:
            self.assertEqual(self.ranges(ident), {'球技場1面・2時間以内': (1200, 1200)})
        for ident in ['tokyo-venue-6b66e7410823', 'tokyo-venue-e6f34cc5ab8e']:
            self.assertEqual(self.ranges(ident), {'野球場1面・2時間以内': (1200, 1200)})

    def test_indoor_full_half_sub_and_day_units_remain_separate(self):
        self.assertEqual(self.ranges('tokyo-gym-8661317f0c40'), {
            'エイトホール全面・2時間30分': (6300, 9700), 'エイトホール全面・全日12時間': (29200, 29200)})
        ranges = self.ranges('tokyo-gym-8107c9095a7c')
        self.assertEqual(ranges['メインアリーナ全面・2時間'], (10200, 15500))
        self.assertEqual(ranges['メインアリーナ半面・2時間'], (5100, 7750))
        self.assertEqual(ranges['サブアリーナ全面・2時間'], (5000, 7200))
        self.assertEqual(len(ranges), 6)

    def test_24_policies_boundary_and_indoor_weather(self):
        self.assertEqual(len(reviewed_policies()), 24)
        for entry in reviewed_policies():
            self.assertEqual(self.rows[entry['id']]['cancellation'], entry)
        shin = self.rows['shinjuku-okubo']['cancellation']['summary']
        for term in ['5日前まで', '4日前～当日', '翌月25日', '最長3か月', 'Webで自己取消しない']:
            self.assertIn(term, shin)
        indoor = self.rows['tokyo-gym-8107c9095a7c']['cancellation']['summary']
        for term in ['7日前まで', '6日前～前日', '50%', '100%', 'オンライン取消不可', '雨天免除を適用しません']:
            self.assertIn(term, indoor)
        self.assertIn('口座引落しせず', self.rows['katsushika-shibue']['cancellation']['summary'])

    def test_closed_baseball_field_does_not_close_adjacent_tennis(self):
        row = self.rows[CLOSED]
        self.assertEqual(row['availability_status'], 'SUSPENDED')
        self.assertIn('2027年3月末', row['availability_note'])
        self.assertIsNone(row['price_from'])
        self.assertFalse(row['fee_ranges'])
        self.assertFalse(filter_catalog([row], {}))
        self.assertEqual(len(filter_catalog([row], {'show_suspended': '1'})), 1)
        self.assertEqual(self.rows['shinjuku-ochiai-chuo']['availability_status'], 'UNKNOWN')
        self.assertEqual(self.rows['shinjuku-ochiai-chuo']['price_from'], 1500)

    def test_legacy_tariffs_previous_reviews_and_booking_urls_survive(self):
        self.assertEqual(len(self.rows), 1206)
        self.assertEqual(self.rows['katsushika-niijuku']['price_from'], 1200)
        self.assertEqual(self.rows['tokyo-venue-48461c620190']['fee_checked_at'], '2026-10-15')
        self.assertEqual(self.rows['tokyo-gym-ee0b47a21429']['fee_checked_at'], '2026-10-17')
        for ident in REVIEWED_IDS:
            self.assertTrue(self.rows[ident]['booking_url'].startswith('https://'))

    def test_importer_is_idempotent_and_refuses_replacing_prior_review(self):
        scratch = ROOT / 'work'
        scratch.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=scratch) as temporary:
            path = Path(temporary) / 'cancellation_policies.json'
            previous = {'id': 'preserved', 'summary': 'previous'}
            path.write_text(json.dumps([previous]), encoding='utf-8')
            append_reviews(path, reviewed_policies())
            first = path.read_bytes()
            append_reviews(path, reviewed_policies())
            self.assertEqual(first, path.read_bytes())
            self.assertEqual(json.loads(first)[0], previous)
            with self.assertRaises(ValueError):
                append_reviews(path, [{'id': 'preserved', 'summary': 'changed'}])
            self.assertEqual(first, path.read_bytes())


if __name__ == '__main__':
    unittest.main()
