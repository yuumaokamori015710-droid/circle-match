"""Official-price scope, units, holds and link-preservation regression checks."""
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'outputs'))
from venues.sports_catalog import filter_catalog, get_catalog
from record_venue_fee_review_20261017 import reviewed_fees, reviewed_policies


class OfficialTariffReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {row['id']: row for row in get_catalog()['courts']}

    def ranges(self, ident):
        return {r['unit']: (r['minimum'], r['maximum']) for r in self.rows[ident]['fee_ranges']}

    def test_16_reviews_attach_to_existing_ids(self):
        entries = reviewed_fees()
        self.assertEqual(len(entries), 16)
        self.assertEqual(len({entry['id'] for entry in entries}), 16)
        for entry in entries:
            with self.subTest(venue=entry['id']):
                row = self.rows[entry['id']]
                self.assertEqual(row['fee_checked_at'], '2026-10-17')
                self.assertEqual(row['fee_options'], entry['fee_options'])
                self.assertIsNone(row['price_from'])
                self.assertTrue(all(p['amount'] > 0 and p['conditions']
                                    and p['source_url'].startswith('https://') for p in row['fee_options']))

    def test_fuchu_gym_slots_remain_separate(self):
        self.assertEqual(self.ranges('tokyo-gym-ee0b47a21429'), {
            '体育室全面・3時間': (2500, 3500),
            '体育室全面・2時間15分': (2000, 2000),
            '体育室全面・全日12時間': (9000, 9000),
        })
        self.assertTrue(all('市内団体のみ' in p['conditions']
                            for p in self.rows['tokyo-gym-ee0b47a21429']['fee_options']))

    def test_komae_short_seasonal_slots_are_not_hourly_normalizations(self):
        self.assertEqual(self.ranges('tokyo-venue-87508e9a2968'), {
            'グランド全面・2時間': (2400, 4800),
            'グランド全面・1時間（季節末尾枠）': (1200, 2400),
        })
        self.assertEqual(self.ranges('tokyo-gym-7420040d51ac')['体育館全面・2時間15分'], (1400, 2800))
        self.assertTrue(all('高校生以下団体の割引' in p['conditions']
                            for p in self.rows['tokyo-gym-7420040d51ac']['fee_options']))

    def test_soccer_and_admission_surcharge_scope(self):
        self.assertEqual(self.ranges('tokyo-venue-72dbbba725a1')['サッカー場1面・1時間'], (800, 1600))
        self.assertEqual(self.ranges('tokyo-gym-4f1d102ace47')['主競技場全面・1時間'], (1600, 4800))
        self.assertNotIn(9600, [p['amount'] for p in self.rows['tokyo-gym-4f1d102ace47']['fee_options']])

    def test_chuo_approximate_half_area_is_not_guessed(self):
        self.assertEqual(self.ranges('tokyo-venue-c3c8b7f2193f')['主競技場全面・3時間'], (14100, 33700))
        self.assertTrue(all('全面' in p['unit'] for p in self.rows['tokyo-venue-c3c8b7f2193f']['fee_options']))

    def test_shinagawa_exact_half_prices_and_ward_limits(self):
        self.assertEqual(self.ranges('tokyo-gym-6b1a56ec4185')['競技場半面・2時間30分'], (3900, 4800))
        self.assertEqual(self.ranges('tokyo-gym-592c31402120')['競技場全面・3時間30分'], (25000, 27500))
        self.assertTrue(all('区外団体は別料金' in p['conditions']
                            for p in self.rows['tokyo-gym-592c31402120']['fee_options']))
        self.assertEqual(self.ranges('tokyo-gym-4f634496a3db')['アリーナ全面・2時間30分'], (5500, 9900))

    def test_taito_nonresident_surcharge_and_unequal_slots(self):
        self.assertEqual(self.ranges('tokyo-venue-353fa74611f1')['体育館アリーナ全面・3時間'], (2700, 9900))
        self.assertEqual(self.ranges('tokyo-venue-353fa74611f1')['体育館アリーナ全面・4時間'], (3600, 6480))
        self.assertEqual(self.ranges('tokyo-gym-48e959a72b2e')['第1競技場全面・3時間'], (17000, 63000))

    def test_14_cancellation_policies_and_weather_exclusion(self):
        policies = reviewed_policies()
        self.assertEqual(len(policies), 14)
        for entry in policies:
            self.assertEqual(self.rows[entry['id']]['cancellation'], entry)
        self.assertIn('10日前', self.rows['tokyo-gym-ee0b47a21429']['cancellation']['summary'])
        self.assertIn('屋内体育館', self.rows['tokyo-gym-7420040d51ac']['cancellation']['summary'])
        self.assertIn('28以上', self.rows['tokyo-venue-e998aceac026']['cancellation']['summary'])
        self.assertIn('185日超', self.rows['tokyo-gym-48e959a72b2e']['cancellation']['summary'])

    def test_closed_and_restricted_facilities_are_not_given_guessed_prices(self):
        for ident in ['tokyo-venue-6b06aed3958d', 'tokyo-gym-aa77f48e78d0',
                      'tokyo-gym-efd5e350238b', 'tokyo-gym-e6782f27b40b', 'tokyo-venue-205d87234dd3']:
            self.assertFalse(self.rows[ident]['fee_ranges'])
            self.assertIsNone(self.rows[ident]['price_from'])
        row = self.rows['tokyo-venue-6b06aed3958d']
        self.assertEqual(row['availability_status'], 'SUSPENDED')
        self.assertIn('2027年5月', row['availability_note'])
        self.assertFalse(filter_catalog([row], {}))
        self.assertEqual(len(filter_catalog([row], {'show_suspended': '1'})), 1)
        self.assertIn('一般公開のみ', self.rows['tokyo-gym-aa77f48e78d0']['availability_note'])

    def test_original_public_links_and_earlier_review_remain(self):
        for entry in reviewed_fees():
            self.assertTrue(self.rows[entry['id']]['booking_url'].startswith('https://'))
        for ident in ['tokyo-venue-6b06aed3958d', 'tokyo-gym-aa77f48e78d0']:
            row = self.rows[ident]
            self.assertTrue(row['booking_url'].startswith('https://spopita.jp/'))
            self.assertTrue(any('2026-10-17' in source['title'] for source in row['sources']))
        self.assertEqual(self.rows['tokyo-gym-bc16a86706e5']['fee_checked_at'], '2026-10-16')


if __name__ == '__main__':
    unittest.main()
