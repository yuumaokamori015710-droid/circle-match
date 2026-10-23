"""Same-unit tariffs, restricted free grounds and preservation of prior reviews."""
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
import record_venue_fee_review_20261022 as review


class October22VenueReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {r['id']: r for r in get_catalog()['courts']}

    def ranges(self, ident):
        return {r['unit']: (r['minimum'], r['maximum']) for r in self.rows[ident]['fee_ranges']}

    def test_20_prices_16_policies_attached_to_original_ids(self):
        self.assertEqual(len(set(review.REVIEWED_IDS)), 20)
        for entry in review.reviewed_fees():
            row = self.rows[entry['id']]
            self.assertEqual(row['fee_options'], entry['fee_options'])
            self.assertEqual(row['fee_checked_at'], review.CHECKED)
            self.assertEqual(row['fee_note'], entry['fee_note'])
            self.assertIsNone(row['price_from'])
            self.assertTrue(has_price(row))
        self.assertEqual(len(review.reviewed_policies()), 16)
        for entry in review.reviewed_policies():
            self.assertEqual(self.rows[entry['id']]['cancellation'], entry)
        self.assertEqual(len(self.rows), 1206)
        later = sum(has_price(r) and r.get('fee_checked_at', '') > review.CHECKED for r in self.rows.values())
        self.assertEqual(sum(has_price(r) for r in self.rows.values()) - later, 749)
        self.assertEqual(sum(not has_price(r) for r in self.rows.values()) + later, 457)

    def test_nishitokyo_outside_exception_and_nonstandard_duration(self):
        self.assertEqual(self.ranges(review.NISHI[0]), {'広場1面・3時間': (1200, 2400)})
        self.assertEqual(self.ranges(review.NISHI[1]), {'B面・3時間': (2400, 4800)})
        self.assertEqual(self.ranges(review.NISHI[2]), {'グラウンド1面・3時間': (1800, 1800)})
        self.assertEqual(self.ranges(review.NISHI[3]), {'グラウンド1面・2時間40分': (1000, 2000),
                                                      'グラウンド1面・全日8時間': (3000, 6000)})
        self.assertIn('A面は野球用', self.rows[review.NISHI[1]]['fee_note'])
        for ident in review.NISHI:
            summary = self.rows[ident]['cancellation']['summary']
            self.assertIn('1週間前を切って予約', summary)
            self.assertIn('60分前', summary)

    def test_chofu_free_is_explicit_and_summer_duration_stays_separate(self):
        self.assertEqual(self.ranges(review.CHOFU[0]), {'サッカー場1面・2時間': (3000, 3000)})
        self.assertIn('30分1,000円', self.rows[review.CHOFU[0]]['fee_note'])
        self.assertEqual(self.ranges(review.CHOFU[1]), {'サッカー場1面・2時間': (0, 0)})
        self.assertIn('暫定使用中のみ', self.rows[review.CHOFU[1]]['fee_note'])
        self.assertEqual(self.ranges(review.CHOFU[2]), {'サッカー場1面・2時間': (0, 0),
                                                      'サッカー場1面・3時間': (0, 0)})
        self.assertIn('7面ソフトボール場', self.rows[review.CHOFU[2]]['fee_note'])
        for ident in review.CHOFU[:3]:
            text = self.rows[ident]['cancellation']['summary']
            self.assertIn('前日まで', text)
            self.assertIn('3か月間', text)
            self.assertIn('半分に達する前', text)

    def test_chofu_gym_not_individual_fee_or_rounded_three_hours(self):
        self.assertEqual(self.ranges(review.CHOFU[3]), {'体育館全面・3時間': (2400, 4800)})
        self.assertEqual(self.ranges(review.CHOFU[4]), {'大体育室半面・2時間45分': (3500, 3500),
                                                      '大体育室3分の1面・2時間45分': (2300, 2300)})
        self.assertIn('屋内体育館へ自動適用せず', self.rows[review.CHOFU[3]]['cancellation']['summary'])
        self.assertIsNone(self.rows[review.CHOFU[4]]['cancellation'])

    def test_minamidaira_areas_durations_and_outside_multiplier(self):
        self.assertEqual(self.ranges(review.HINO[0]), {
            'アリーナ全面・3時間': (12000, 30000), 'アリーナ全面・2時間': (8000, 26000),
            'アリーナ半面・3時間': (6000, 15000), 'アリーナ半面・2時間': (4000, 13000)})
        self.assertEqual(len(self.rows[review.HINO[0]]['fee_options']), 24)
        summary = self.rows[review.HINO[0]]['cancellation']['summary']
        self.assertIn('3日前まで', summary)
        self.assertIn('2日前以降', summary)
        self.assertIn('返還不可', summary)

    def test_hino_restricted_free_not_zero_for_unknown(self):
        self.assertIn('連盟所属', self.rows[review.HINO[1]]['fee_note'])
        self.assertIn('少年サッカー団体のみ', self.rows[review.HINO[1]]['fee_note'])
        self.assertIn('練習向け', self.rows[review.HINO[2]]['fee_note'])
        self.assertEqual(self.ranges(review.HINO[1]), {'少年サッカー場1面・予約1区分': (0, 0)})
        self.assertEqual(self.ranges(review.HINO[2]), {'グラウンド1面・予約1区分': (0, 0)})
        free_ids = {r['id'] for r in review.reviewed_fees() if any(p['amount'] == 0 for p in r['fee_options'])}
        self.assertEqual(free_ids, {review.CHOFU[1], review.CHOFU[2], review.HINO[1], review.HINO[2], review.AKISHIMA[1]})

    def test_fureai_after_revision_published_rounding_not_old_fee(self):
        self.assertEqual(self.ranges(review.HINO[3]), {
            'コミュニティホール全面・3時間30分': (13800, 34400),
            'コミュニティホール全面・2時間': (9000, 28800),
            'コミュニティホール半面・3時間30分': (6900, 17200),
            'コミュニティホール半面・2時間': (4500, 14400),
            'コミュニティホール3分の1面・3時間30分': (4600, 11400),
            'コミュニティホール3分の1面・2時間': (3000, 7800)})
        self.assertIn('金・土のみ', self.rows[review.HINO[3]]['fee_note'])
        self.assertIn(5900, [p['amount'] for p in self.rows[review.HINO[3]]['fee_options']])
        self.assertFalse(any('3分の1面' in p['label'] and '21～23時' in p['label']
                             for p in self.rows[review.HINO[3]]['fee_options']))
        self.assertIsNone(self.rows[review.HINO[3]]['cancellation'])

    def test_hino_track_and_field_admission_surcharge_separate(self):
        self.assertEqual(self.ranges(review.HINO[4]), {'競技場全面・2時間': (4000, 8000),
                                                     '競技場3分の1面・2時間': (2000, 4000),
                                                     '競技場全面・全日8時間': (14000, 28000)})
        self.assertEqual(self.ranges(review.HINO[5]), {'多目的広場1面・2時間': (4000, 8000)})
        self.assertIn('許可を保証しません', self.rows[review.HINO[5]]['fee_note'])

    def test_kunitachi_split_rooms_and_separate_baseball_soccer_sources(self):
        self.assertEqual(self.ranges(review.KUNI[0]), {'第一体育室半面・3時間': (2800, 5700),
                                                     '第一体育室半面・1時間': (1200, 1800)})
        self.assertEqual(self.ranges(review.KUNI[1]), {'サッカー場1面・1時間': (650, 975),
                                                     '野球場1面・1時間': (650, 975)})
        plans = self.rows[review.KUNI[1]]['fee_options']
        self.assertEqual({p['source_url'] for p in plans}, {review.KUNI_FIELD, review.KUNI_BASEBALL})
        self.assertIn('5日前まで', self.rows[review.KUNI[1]]['cancellation']['summary'])
        self.assertIn('14日以内', self.rows[review.KUNI[1]]['cancellation']['summary'])

    def test_akishima_nonresident_booking_restrictions_and_exact_hours(self):
        self.assertEqual(self.ranges(review.AKISHIMA[0]), {'体育室全面・3時間': (2000, 2000),
                                                         '体育室半面・3時間': (1000, 1000)})
        self.assertEqual(self.ranges(review.AKISHIMA[1]), {'サッカー場1面・2時間': (0, 0)})
        self.assertIn('市内団体または市内在住在勤在学者に限定', self.rows[review.AKISHIMA[1]]['fee_note'])
        self.assertEqual(self.ranges(review.AKISHIMA[2]), {
            '第一体育室全面・3時間': (6000, 7700), '第一体育室全面・4時間': (9700, 9700),
            '第一体育室全面・全日13時間': (25000, 25000),
            '第一体育室半面・3時間': (3000, 3850), '第一体育室半面・4時間': (4850, 4850),
            '第一体育室半面・全日13時間': (12500, 12500)})
        self.assertIn('Web予約システムは市内団体専用', self.rows[review.AKISHIMA[2]]['fee_note'])
        self.assertIn('一切受け付けない', self.rows[review.AKISHIMA[2]]['cancellation']['summary'])

    def test_original_catalogs_and_all_earlier_review_records_preserved(self):
        base = 'c8b28c6829aa497ab95e6d5e43d9c8038f5bb1d7'
        for name in ['tokyo_tennis.json', 'tokyo_sports.json', 'tokyo_expansion.json']:
            relative = 'outputs/venues/catalogs/' + name
            previous = subprocess.check_output(['git', 'show', base + ':' + relative], cwd=ROOT)
            current = {r['id']: r for r in json.loads((ROOT / relative).read_bytes())}
            corrections = {'tokyo-venue-ec7d0ac023ca': {'checked_at', 'availability_status', 'availability_note', 'sources'},
                           'tokyo-venue-a2d6191898f8': {'checked_at', 'booking_note', 'sources'}}
            for before in json.loads(previous):
                after = current[before['id']]
                allowed = corrections.get(before['id'], set()) if name == 'tokyo_expansion.json' else set()
                for field in set(before) - allowed:
                    self.assertEqual(before[field], after[field], (before['id'], field))
                if allowed:
                    self.assertEqual(after['checked_at'], '2026-10-23')
                    self.assertEqual(after['sources'][:len(before['sources'])], before['sources'])
                    if before['id'] == 'tokyo-venue-ec7d0ac023ca':
                        self.assertEqual(after['availability_status'], 'SUSPENDED')
                        self.assertIn('2026年3月31日', after['availability_note'])
                    else:
                        self.assertTrue(after['booking_note'].startswith(before['booking_note']))
                        self.assertIn('第一体育室', after['booking_note'])
        for name in ['fee_plans.json', 'cancellation_policies.json']:
            relative = 'outputs/venues/catalogs/' + name
            previous = json.loads(subprocess.check_output(['git', 'show', base + ':' + relative], cwd=ROOT))
            current = {r['id']: r for r in json.loads((ROOT / relative).read_bytes())}
            for row in previous:
                self.assertEqual(current[row['id']], row)

    def test_import_idempotence_and_refusal_to_overwrite(self):
        paths = [review.CATALOGS / n for n in ['fee_plans.json', 'cancellation_policies.json']]
        before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
        subprocess.run([sys.executable, '-X', 'utf8', str(ROOT / 'scripts/record_venue_fee_review_20261022.py')],
                       check=True, capture_output=True)
        self.assertEqual(before, [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths])
        with tempfile.TemporaryDirectory(dir=ROOT / 'work') as temporary:
            path = Path(temporary) / 'fee_plans.json'
            path.write_text('[]', encoding='utf-8')
            review.append_reviews(path, review.reviewed_fees())
            first = path.read_bytes()
            with self.assertRaises(ValueError):
                review.append_reviews(path, [dict(review.reviewed_fees()[0], checked_at='2000-01-01')])
            self.assertEqual(path.read_bytes(), first)
        fake = dict(self.rows[review.NISHI[0]], fee_checked_at='2000-01-01')
        with patch.object(review, 'get_catalog', return_value={'courts': [fake]}):
            with self.assertRaises(ValueError):
                review.main()


if __name__ == '__main__':
    unittest.main()
