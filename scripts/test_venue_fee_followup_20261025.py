"""Verify current availability boundaries, exact tariff units and source preservation."""
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
import record_venue_fee_review_20261025 as review


class October25VenueReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {r['id']: r for r in get_catalog()['courts']}

    def ranges(self, ident):
        return {r['unit']: (r['minimum'], r['maximum']) for r in self.rows[ident]['fee_ranges']}

    def test_batch_counts_and_exact_published_records(self):
        self.assertEqual(len(set(review.REVIEWED_IDS)), 22)
        self.assertEqual(len(review.reviewed_fees()), 16)
        self.assertEqual(len(review.reviewed_policies()), 13)
        for entry in review.reviewed_fees():
            row = self.rows[entry['id']]
            self.assertEqual(row['fee_options'], entry['fee_options'])
            self.assertEqual(row['fee_note'], entry['fee_note'])
            self.assertEqual(row['fee_checked_at'], review.CHECKED)
        for entry in review.reviewed_policies():
            self.assertEqual(self.rows[entry['id']]['cancellation'], entry)
        later_priced = sum(has_price(r) and r.get('fee_checked_at', '') > review.CHECKED
                           for r in self.rows.values())
        self.assertEqual(len(self.rows), 1206)
        self.assertEqual(sum(has_price(r) for r in self.rows.values()) - later_priced, 801)
        self.assertEqual(sum(not has_price(r) for r in self.rows.values()) + later_priced, 405)
        self.assertEqual(sum(not has_price(r) and r['availability_status'] != 'SUSPENDED'
                             for r in self.rows.values()) + later_priced, 397)

    def test_holds_unknown_not_zero_or_restricted_hire(self):
        for ident in review.HOLDS:
            if ident in ['tokyo-venue-f403faf4f42f', 'tokyo-venue-5b81852866ce']:
                self.assertEqual(self.rows[ident]['fee_checked_at'], '2026-10-26')
                self.assertTrue(has_price(self.rows[ident]))
                continue
            self.assertFalse(has_price(self.rows[ident]))
            self.assertEqual(self.rows[ident]['fee_ranges'], [])
        self.assertTrue(all(p['amount'] > 0 for r in review.reviewed_fees() for p in r['fee_options']))

    def test_hachioji_current_rates_and_short_daytime(self):
        self.assertEqual(self.ranges(review.HACHIOJI[2])['主競技場半面・3時間'], (5200, 5200))
        self.assertEqual(self.ranges(review.HACHIOJI[2])['主競技場全面・2時間50分'], (9000, 9000))
        self.assertEqual(self.ranges(review.HACHIOJI[3])['第1体育室全面・2時間50分'], (3600, 3600))
        self.assertEqual(self.ranges(review.HACHIOJI[3])['第1体育室全面・3時間'], (4200, 4200))
        self.assertIn('2027年4月', self.rows[review.HACHIOJI[2]]['fee_note'])
        self.assertIn('2026年12月14日', self.rows[review.HACHIOJI[2]]['fee_note'])

    def test_hikari_only_available_second_room(self):
        row = self.rows[review.HIKARI]
        self.assertEqual(self.ranges(review.HIKARI), {'第二体育室・2時間30分': (1000, 2000)})
        self.assertTrue(all(p['unit'].startswith('第二体育室') for p in row['fee_options']))
        self.assertIn('第一体育室は天井の耐震性不足で停止中', row['fee_note'])
        self.assertIn('球技コート', self.rows[review.TOSHIMA[0]]['fee_note'])

    def test_fuchu_rounding_area_and_duration(self):
        ranges = self.ranges(review.FUCHU[2])
        self.assertEqual(ranges['体育室全面・2時間30分'], (2500, 3700))
        self.assertEqual(ranges['体育室半面・3時間'], (1500, 3000))
        self.assertEqual(ranges['体育室全面・3時間'], (3000, 6000))

    def test_hinode_conditions_and_published_admission_tariff(self):
        self.assertEqual(self.ranges(review.HINODE[0]), {'谷戸沢グランド全面・1時間': (500, 2000)})
        self.assertEqual(self.ranges(review.HINODE[1]), {'谷戸沢サッカー場全面・1時間': (3000, 12000)})
        for ident in review.HINODE:
            self.assertIn('練習・練習試合は不可', self.rows[ident]['fee_note'])
            self.assertIn('雨天等は可', self.rows[ident]['cancellation']['summary'])

    def test_higashi_alias_preserved_and_three_hour_slot_separate(self):
        first, alias = [self.rows[i] for i in review.HIGASHI[:2]]
        self.assertEqual(first['fee_options'], alias['fee_options'])
        self.assertEqual(self.ranges(review.HIGASHI[0])['桜が丘広場全面・2時間'], (450, 1800))
        self.assertEqual(self.ranges(review.HIGASHI[0])['桜が丘広場全面・3時間'], (450, 1800))
        self.assertEqual(self.ranges(review.HIGASHI[2]), {
            '清原運動広場全面・2時間': (3900, 7800), '清原運動広場全面・3時間': (3900, 7800)})
        self.assertEqual(self.ranges(review.HIGASHI[3])['第1体育室半面・2時間30分'], (4800, 4800))
        for ident in review.HIGASHI:
            self.assertIn('IDへ還付', self.rows[ident]['cancellation']['summary'])
        self.assertNotIn('開始30分前', self.rows[review.HIGASHI[3]]['cancellation']['summary'])

    def test_ome_lighting_and_individual_not_mixed(self):
        self.assertEqual(self.ranges(review.OME[0]), {'球技場全面・2時間': (2400, 2400), '球技場半面・2時間': (1200, 1200)})
        self.assertEqual(self.ranges(review.OME[1])['第1スポーツホール全面・3時間'], (9000, 9000))
        self.assertEqual(self.ranges(review.OME[1])['第1スポーツホール全面・4時間'], (12000, 12000))
        self.assertEqual(self.ranges(review.FUSSA[0]), {'第1体育室・1人90分': (70, 150)})
        self.assertIn('通常貸切なし', self.rows[review.FUSSA[0]]['fee_note'])
        self.assertEqual(self.ranges(review.FUSSA[1]), {'第2体育室・1時間': (400, 2400)})
        self.assertIn('利用者全員', self.rows[review.FUSSA[1]]['fee_note'])

    def test_original_fields_and_prior_review_prefix_unchanged(self):
        base = '3cac8975957073fb4d7bee6730e17398fa295e01'
        for name in ['tokyo_tennis.json', 'tokyo_sports.json', 'tokyo_expansion.json',
                     'fee_plans.json', 'cancellation_policies.json']:
            rel = 'outputs/venues/catalogs/' + name
            previous = json.loads(subprocess.check_output(['git', 'show', base + ':' + rel], cwd=ROOT))
            current = json.loads((ROOT / rel).read_bytes())
            self.assertEqual(previous, current if name.startswith('tokyo_') else current[:len(previous)])

    def test_import_idempotent_and_no_partial_writes_on_conflict(self):
        paths = [review.CATALOGS / n for n in ['fee_plans.json', 'cancellation_policies.json']]
        before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
        subprocess.run([sys.executable, '-B', '-X', 'utf8', str(ROOT / 'scripts/record_venue_fee_review_20261025.py')],
                       check=True, capture_output=True)
        self.assertEqual(before, [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths])
        fake = dict(self.rows[review.HIKARI], fee_checked_at='2000-01-01')
        rows = [fake if r['id'] == fake['id'] else r for r in self.rows.values()]
        with patch.object(review, 'get_catalog', return_value={'courts': rows}), patch.object(review, 'append_reviews') as append:
            with self.assertRaises(ValueError):
                review.main()
            append.assert_not_called()


if __name__ == '__main__':
    unittest.main()
