"""Offline checks of reviewed prices, charging scope, closure and preservation."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'outputs'))
from venues.sports_catalog import filter_catalog, get_catalog
from record_venue_fee_review_20261016 import reviewed_fees, reviewed_policies


class OfficialTariffReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {row['id']: row for row in get_catalog()['courts']}

    def test_all_22_reviews_attach_to_existing_ids_with_sources(self):
        entries = reviewed_fees()
        self.assertEqual(len(entries), 22)
        self.assertEqual(len({entry['id'] for entry in entries}), 22)
        for entry in entries:
            with self.subTest(venue=entry['id']):
                row = self.rows[entry['id']]
                self.assertEqual(row['fee_checked_at'], '2026-10-16')
                self.assertEqual(row['fee_options'], entry['fee_options'])
                self.assertIsNone(row['price_from'])
                self.assertTrue(all(option['amount'] > 0 and option['conditions']
                                    and option['source_url'].startswith('https://')
                                    for option in row['fee_options']))

    def test_morning_half_full_and_short_slots_are_not_combined(self):
        row = self.rows['tokyo-gym-bc16a86706e5']
        ranges = {item['unit']: (item['minimum'], item['maximum']) for item in row['fee_ranges']}
        self.assertEqual(ranges, {
            '体育館全面・3時間': (2700, 2700), '体育館全面・2時間30分': (3500, 4100),
            '体育館半面・3時間': (1350, 1350), '体育館半面・2時間30分': (1750, 2050),
        })
        okura = {item['unit']: (item['minimum'], item['maximum'])
                 for item in self.rows['tokyo-gym-0cb647825898']['fee_ranges']}
        self.assertEqual(okura['体育館全面・2時間'], (10440, 12400))
        self.assertEqual(okura['体育館全面・3時間'], (15660, 18600))

    def test_registered_group_discounts_are_explicit_not_guessed(self):
        yotsuya = self.rows['tokyo-gym-125683b2ea6c']
        short = next(item for item in yotsuya['fee_ranges'] if item['unit'] == '多目的ホール全面・3時間')
        self.assertEqual((short['minimum'], short['maximum']), (3150, 10500))
        nerima = self.rows['tokyo-gym-24073ef2f004']['fee_options']
        self.assertEqual({option['amount'] for option in nerima}, {400, 800, 1600})
        self.assertTrue(all('登録団体' in option['conditions'] for option in nerima))

    def test_soccer_lighting_and_different_surfaces_stay_separate(self):
        row = self.rows['tokyo-venue-555e53ea3e30']
        ranges = {item['unit']: (item['minimum'], item['maximum']) for item in row['fee_ranges']}
        self.assertEqual(ranges['サッカー場全面・2時間'], (7350, 10050))
        self.assertEqual(ranges['多目的運動広場全面・2時間'], (1800, 2400))
        self.assertTrue(all('5,150円' in option['conditions'] for option in row['fee_options']))
        self.assertFalse(any(option['amount'] == 5150 for option in row['fee_options']))

    def test_arena_prices_do_not_mix_paid_spectator_or_stand_charges(self):
        tokyo = self.rows['tokyo-gym-598414cefd93']
        four = next(item for item in tokyo['fee_ranges'] if item['unit'] == 'サブアリーナ全面・4時間（税込）')
        self.assertEqual((four['minimum'], four['maximum']), (19000, 33100))
        komazawa = self.rows['tokyo-gym-f4ecc307371e']
        self.assertTrue(all('スタンド未使用' in option['conditions'] for option in komazawa['fee_options']))
        self.assertEqual(komazawa['fee_ranges'][0]['minimum'], 37800)

    def test_cancel_terms_keep_unknowns_and_indoor_weather_exclusion(self):
        self.assertEqual(len(reviewed_policies()), 15)
        for review in reviewed_policies():
            self.assertEqual(self.rows[review['id']]['cancellation'], review)
        self.assertIn('適用されません', self.rows['tokyo-gym-e9661f9d4b0f']['cancellation']['summary'])
        self.assertIn('未確認', self.rows['tokyo-gym-01345ff23a1e']['cancellation']['summary'])

    def test_conflicting_edogawa_price_is_not_published_as_a_range(self):
        row = self.rows['tokyo-sports-038']
        self.assertIsNone(row['price_from'])
        self.assertFalse(row.get('fee_options'))

    def test_closed_hanahata_record_and_original_links_are_preserved(self):
        row = self.rows['tokyo-gym-e4c214671936']
        self.assertEqual(row['availability_status'], 'SUSPENDED')
        self.assertIn('2028年3月', row['availability_note'])
        self.assertTrue(row['booking_url'].startswith('https://spopita.jp/'))
        self.assertIsNone(row['price_from'])
        self.assertFalse(row.get('fee_options'))
        self.assertFalse(filter_catalog([row], {}))
        self.assertEqual(len(filter_catalog([row], {'show_suspended': '1'})), 1)


if __name__ == '__main__':
    unittest.main()
