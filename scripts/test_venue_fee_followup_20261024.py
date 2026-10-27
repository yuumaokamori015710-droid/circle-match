"""Check the Oct24 tariff boundaries and preserve all previous source records."""
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
import record_venue_fee_review_20261024 as review


class October24VenueReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {r['id']: r for r in get_catalog()['courts']}

    def ranges(self, ident):
        return {r['unit']: (r['minimum'], r['maximum']) for r in self.rows[ident]['fee_ranges']}

    def test_twenty_reviews_eighteen_tariffs_seventeen_policies(self):
        self.assertEqual(len(set(review.REVIEWED_IDS)), 20)
        self.assertEqual(len(review.reviewed_fees()), 18)
        self.assertEqual(len(review.reviewed_policies()), 17)
        for entry in review.reviewed_fees():
            row = self.rows[entry['id']]
            self.assertEqual(row['fee_options'], entry['fee_options'])
            self.assertEqual(row['fee_note'], entry['fee_note'])
            self.assertEqual(row['fee_checked_at'], review.CHECKED)
            self.assertIsNone(row['price_from'])
        for entry in review.reviewed_policies():
            self.assertEqual(self.rows[entry['id']]['cancellation'], entry)
        self.assertEqual(len(self.rows), 1206)
        later_priced = sum(has_price(r) and r.get('fee_checked_at', '') > review.CHECKED
                           for r in self.rows.values())
        self.assertEqual(sum(has_price(r) for r in self.rows.values()) - later_priced, 785)
        self.assertEqual(sum(not has_price(r) for r in self.rows.values()) + later_priced, 421)
        later_closures = sum(not has_price(r) and r['availability_status'] == 'SUSPENDED'
                             and r['checked_at'] > review.CHECKED for r in self.rows.values())
        self.assertEqual(sum(not has_price(r) and r['availability_status'] != 'SUSPENDED'
                             for r in self.rows.values()) + later_priced + later_closures, 413)

    def test_unknown_not_zero_and_public_opening_not_private_hire(self):
        for ident in review.HOLDS:
            self.assertFalse(has_price(self.rows[ident]))
            self.assertEqual(self.rows[ident]['fee_ranges'], [])
        self.assertTrue(all(p['amount'] > 0 for row in review.reviewed_fees() for p in row['fee_options']))
        self.assertEqual(self.ranges(review.MACHIDA[1]), {
            'グラウンド全面・2時間30分': (2090, 2090), 'グラウンド全面・1時間30分': (1250, 1250)})
        self.assertIn('一般開放の無料料金と混ぜません', self.rows[review.MACHIDA[1]]['fee_note'])

    def test_machida_distinct_areas_and_permissions(self):
        self.assertEqual(self.ranges(review.MACHIDA[0]), {
            'グラウンド全面・2時間': (6280, 6280), 'グラウンド半面・2時間': (3140, 3140)})
        self.assertEqual(self.ranges(review.MACHIDA[2])['メインアリーナ3分の1面・3時間'], (3030, 3030))
        self.assertEqual(self.ranges(review.MACHIDA[2])['メインアリーナ全面・3時間'], (9110, 9110))
        for ident in [review.MACHIDA[1], review.MACHIDA[3], review.MACHIDA[4], review.MACHIDA[6]]:
            self.assertTrue(any(k in self.rows[ident]['fee_note'] for k in ['他用途', 'サッカー']))
        self.assertEqual(self.ranges(review.MACHIDA[7]), {'グラウンド全面・2時間': (1050, 1050)})

    def test_akiruno_new_april_rates_not_old_or_personal_use(self):
        self.assertEqual(self.ranges(review.AKIRUNO[0]), {'野球場1面・2時間': (800, 2400)})
        self.assertEqual(self.ranges(review.AKIRUNO[2]), {'体育室全面・2時間': (2400, 7200)})
        self.assertEqual(self.ranges(review.AKIRUNO[3])['大体育室8分の1面・2時間'], (300, 900))
        self.assertEqual(self.ranges(review.AKIRUNO[3])['小体育室全面・2時間'], (1200, 3600))
        self.assertIn('無条件で全額返金', self.rows[review.AKIRUNO[2]]['cancellation']['summary'])

    def test_murayama_current_city_tariff_units_and_exact_rounding(self):
        self.assertEqual(self.ranges(review.MURAYAMA[0])['第一体育室全面・全日12時間30分'], (47310, 94620))
        self.assertEqual(self.ranges(review.MURAYAMA[0])['第一体育室3分の1面・2時間30分'], (3080, 6160))
        self.assertEqual(self.ranges(review.MURAYAMA[1]), {
            '第2運動場全面・1時間（単価）': (1080, 2160), '第2運動場全面・2時間': (2160, 4320)})
        self.assertEqual(self.ranges(review.MURAYAMA[2]), {
            '野山北公園運動場全面・1時間（単価）': (750, 1500), '野山北公園運動場全面・2時間': (1500, 3000)})
        self.assertTrue(all(p['source_url'].endswith('r80609siyouryou.pdf')
                            for p in self.rows[review.MURAYAMA[0]]['fee_options']))

    def test_hamura_only_reopened_second_hall_and_exact_truncation(self):
        row = self.rows[review.HAMURA[1]]
        self.assertNotEqual(row['availability_status'], 'SUSPENDED')
        self.assertIn('第1ホールは利用停止中', row['fee_note'])
        self.assertIn('2026年5月26日', row['fee_note'])
        self.assertTrue(all('第2ホール' in p['unit'] for p in row['fee_options']))
        self.assertEqual(self.ranges(review.HAMURA[1])['第2ホール全面・3時間'], (3960, 6430))
        self.assertEqual(self.ranges(review.HAMURA[1])['第2ホール全面・4時間'], (6930, 10390))
        self.assertEqual(self.ranges(review.HAMURA[0]), {'サッカー場1面・2時間': (1220, 1220)})
        self.assertIsNone(self.rows[review.HAMURA[0]]['cancellation'])

    def test_kodaira_public_events_only_main_hall_and_mizuho_town(self):
        self.assertEqual(self.ranges(review.KODAIRA), {'第2体育室全面・2時間30分': (5000, 7500)})
        self.assertIn('公的行事のみ', self.rows[review.KODAIRA]['fee_note'])
        self.assertIn('14日前', self.rows[review.KODAIRA]['cancellation']['summary'])
        self.assertEqual(self.ranges(review.MIZUHO), {'第1体育室・2時間30分': (1000, 3000),
                                                     '第2体育室・2時間30分': (1000, 3000)})
        self.assertIn('フットサルは原則禁止', self.rows[review.MIZUHO]['fee_note'])
        self.assertIn('自己都合キャンセルによる返金なし', self.rows[review.MIZUHO]['cancellation']['summary'])

    def test_cancellation_penalties_are_not_refund_fees(self):
        for ident in review.MACHIDA:
            summary = self.rows[ident]['cancellation']['summary']
            self.assertIn('3週間前', summary)
            self.assertIn('60分未満', summary)
            self.assertIn('金銭の取消手数料・還付率とは別', summary)
        for ident in review.MURAYAMA[1:]:
            summary = self.rows[ident]['cancellation']['summary']
            self.assertIn('開始1時間以内', summary)
            self.assertIn('熱中症予防', summary)
        self.assertNotIn('熱中症予防', self.rows[review.MURAYAMA[0]]['cancellation']['summary'])

    def test_all_original_fields_and_prior_reviews_unchanged(self):
        base = 'ce2de38860b46a7555af1e8b62089091a906bb32'
        for name in ['tokyo_tennis.json', 'tokyo_sports.json', 'tokyo_expansion.json',
                     'fee_plans.json', 'cancellation_policies.json']:
            rel = 'outputs/venues/catalogs/' + name
            previous = json.loads(subprocess.check_output(['git', 'show', base + ':' + rel], cwd=ROOT))
            current = json.loads((ROOT / rel).read_bytes())
            if name.startswith('tokyo_'):
                for before, after in zip(previous, current):
                    if before['id'] == 'tokyo-venue-3df7eec0d53c':
                        for key in ['availability_status', 'availability_note', 'checked_at', 'sources']:
                            after[key] = before[key]
                self.assertEqual(previous, current)
            else:
                self.assertEqual(previous, current[:len(previous)])

    def test_import_idempotent_and_conflicting_review_rejected(self):
        paths = [review.CATALOGS / n for n in ['fee_plans.json', 'cancellation_policies.json']]
        before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
        subprocess.run([sys.executable, '-B', '-X', 'utf8', str(ROOT / 'scripts/record_venue_fee_review_20261024.py')],
                       check=True, capture_output=True)
        self.assertEqual(before, [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths])
        fake = dict(self.rows[review.MACHIDA[0]], fee_checked_at='2000-01-01')
        rows = [fake if r['id'] == fake['id'] else r for r in self.rows.values()]
        with patch.object(review, 'get_catalog', return_value={'courts': rows}), patch.object(review, 'append_reviews') as append:
            with self.assertRaises(ValueError):
                review.main()
            append.assert_not_called()


if __name__ == '__main__':
    unittest.main()
