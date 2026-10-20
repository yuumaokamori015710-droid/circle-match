"""Exact prices, unlike units, restricted free use and guarded policy correction."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'outputs'))
from venues.sports_catalog import get_catalog, filter_catalog, has_price
from record_venue_fee_review_20261019 import (
    reviewed_fees, reviewed_policies, append_reviews, REVIEWED_IDS, CLOSED,
    TAMA_IDS, KODAIRA_IDS, SUMIDA_FIELDS, SUMIDA_GYM, UMEWAKA, NAKANO_IDS,
    SHINAGAWA_IDS, PREVIOUS_HEIWA_POLICY,
)


class OfficialVenueReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {row['id']: row for row in get_catalog()['courts']}

    def ranges(self, ident):
        return {r['unit']: (r['minimum'], r['maximum']) for r in self.rows[ident]['fee_ranges']}

    def test_existing_21_records_20_new_tariffs_and_counts(self):
        self.assertEqual(len(set(REVIEWED_IDS)), 21)
        self.assertEqual(len(reviewed_fees()), 20)
        for review in reviewed_fees():
            row = self.rows[review['id']]
            self.assertEqual(row['fee_checked_at'], '2026-10-19')
            self.assertEqual(row['fee_options'], review['fee_options'])
            self.assertIsNone(row['price_from'])
            self.assertTrue(all(p['amount'] >= 0 and p['conditions'] and p['source_url'].startswith('https://')
                                for p in row['fee_options']))
        self.assertEqual(len(self.rows), 1206)
        later_priced = sum(has_price(r) and r.get('fee_checked_at', '') > '2026-10-19'
                           for r in self.rows.values())
        later_closures = sum(not has_price(r) and r['availability_status'] == 'SUSPENDED'
                             and r['checked_at'] > '2026-10-19' for r in self.rows.values())
        self.assertEqual(sum(has_price(r) for r in self.rows.values()) - later_priced, 710)
        self.assertEqual(sum(not has_price(r) for r in self.rows.values()) + later_priced, 496)
        self.assertEqual(sum(not has_price(r) and r['availability_status'] != 'SUSPENDED'
                             for r in self.rows.values()) + later_priced + later_closures, 491)

    def test_tama_city_only_baseball_and_duplicate_field_identity(self):
        self.assertEqual(self.ranges(TAMA_IDS[0]), {'球技場1面・2時間': (730, 1460)})
        for ident in TAMA_IDS[1:5]:
            self.assertEqual(self.ranges(ident), {'球技場1面・2時間': (2080, 4160)})
        self.assertEqual(self.ranges(TAMA_IDS[-1]), {'野球場1面・2時間': (2080, 2080)})
        self.assertIn('市外団体使用不可', self.rows[TAMA_IDS[-1]]['fee_note'])
        self.assertIn('同時使用できません', self.rows[TAMA_IDS[3]]['fee_note'])

    def test_kodaira_two_hour_and_short_winter_slots_separate(self):
        self.assertEqual(self.ranges(KODAIRA_IDS[2]), {'グラウンド1面・2時間': (1700, 2550)})
        for ident in [KODAIRA_IDS[0], KODAIRA_IDS[1], KODAIRA_IDS[3]]:
            self.assertEqual(self.ranges(ident), {'グラウンド1面・2時間': (1500, 2250),
                                                'グラウンド1面・冬季最終1時間': (750, 1125)})
            self.assertIn('許可範囲を広げるものではありません', self.rows[ident]['fee_note'])

    def test_sumida_correct_sport_and_room_and_published_rounding(self):
        for ident in SUMIDA_FIELDS:
            self.assertEqual(self.ranges(ident)['フットサルコート1面・2時間'], (10000, 18000))
            self.assertEqual(self.ranges(ident)['少年サッカー場・2時間'], (9000, 16200))
        gym = self.rows[SUMIDA_GYM]
        ranges = self.ranges(SUMIDA_GYM)
        self.assertEqual(ranges['メインアリーナ3分の1面・3時間'], (6600, 17600))
        self.assertEqual(ranges['サブアリーナ全面・3時間'], (9900, 26400))
        self.assertEqual(ranges['サブアリーナ全面・1時間30分'], (11000, 16500))
        self.assertTrue(any(p['amount'] == 18970 for p in gym['fee_options']))
        self.assertTrue(any(p['amount'] == 7420 for p in gym['fee_options']))
        self.assertIn('サブアリーナのバスケット利用不可', gym['fee_note'])
        self.assertEqual(self.ranges(UMEWAKA), {'体育館全面・3時間': (4840, 8740),
                                             '体育館全面・4時間': (5830, 15670),
                                             '体育館全面・全日12時間': (17270, 34650)})

    def test_nakano_free_is_confirmed_and_eligibility_is_not_unrestricted(self):
        self.assertEqual(self.ranges(NAKANO_IDS[0]), {'運動広場1面・2時間': (0, 0)})
        note = self.rows[NAKANO_IDS[0]]['fee_note']
        for term in ['10人以上', '半数以上', '中野区', '1～15日', '営利使用禁止']:
            self.assertIn(term, note)
        self.assertEqual(self.ranges(NAKANO_IDS[1]), {'多目的運動広場1面・2時間': (2900, 2900)})
        self.assertIn('30分700円', self.rows[NAKANO_IDS[1]]['fee_note'])
        ranges = self.ranges(NAKANO_IDS[2])
        self.assertEqual(ranges['体育館全面・3時間'], (18400, 22200))
        self.assertEqual(ranges['体育館全面・3時間45分'], (35500, 35500))
        self.assertEqual(ranges['体育館半面・1時間30分'], (4200, 5000))
        self.assertIn('各1,000円', self.rows[NAKANO_IDS[2]]['fee_note'])
        self.assertIn('無料の全開放', self.rows[NAKANO_IDS[2]]['fee_note'])

    def test_shinagawa_sports_not_light_sports_or_pool_and_unequal_durations(self):
        for ident, expected in zip(SHINAGAWA_IDS, [((3500, 4200), (4600, 5500), (5800, 7000)),
                                                                ((4600, 5500), (6000, 7200), (7600, 9100)),
                                                                ((5300, 6400), (6900, 8300), (8800, 10600))]):
            self.assertEqual(self.ranges(ident), dict(zip(['スポーツ室・3時間', 'スポーツ室・3時間30分', 'スポーツ室・4時間'], expected)))
            self.assertIn('日曜祝日は17時閉館', self.rows[ident]['fee_note'])
            self.assertIn('営利使用不可', self.rows[ident]['fee_note'])

    def test_17_added_policies_and_one_explicit_source_conflict(self):
        self.assertEqual(len(reviewed_policies()), 18)
        for review in reviewed_policies():
            self.assertEqual(self.rows[review['id']]['cancellation'], review)
        self.assertIsNone(self.rows[UMEWAKA]['cancellation'])
        self.assertEqual(self.rows[NAKANO_IDS[2]]['cancellation']['checked_at'], '2026-10-15')
        self.assertIn('通常の雨は閉鎖扱いではありません', self.rows[SUMIDA_FIELDS[0]]['cancellation']['summary'])
        for term in ['資料間', '3日前まで無料', '7日前まで50%', '申込前に管理者へ確認']:
            self.assertIn(term, self.rows[NAKANO_IDS[1]]['cancellation']['summary'])
        self.assertIn('オンライン決済分も現金還付', self.rows[TAMA_IDS[0]]['cancellation']['summary'])
        self.assertIn('大会開催等の施設利用料はこの一般還付の対象外', self.rows[TAMA_IDS[0]]['cancellation']['summary'])
        self.assertIn('7日前まで（閉館日なら翌開館日）', self.rows[SHINAGAWA_IDS[0]]['cancellation']['summary'])

    def test_closure_is_hidden_not_deleted_and_not_confused_with_other_central_parks(self):
        row = self.rows[CLOSED]
        self.assertEqual(row['availability_status'], 'SUSPENDED')
        self.assertIn('2026年4月1日～2027年3月末', row['availability_note'])
        self.assertFalse(has_price(row))
        self.assertEqual(filter_catalog([row], {}), [])
        self.assertEqual(len(filter_catalog([row], {'show_suspended': '1'})), 1)

    def test_append_helper_idempotent_and_refuses_replacing_prior_review(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'work') as temporary:
            path = Path(temporary) / 'fee_plans.json'
            previous = reviewed_fees()[0]
            path.write_text(json.dumps([previous]), encoding='utf-8')
            append_reviews(path, reviewed_fees())
            first = path.read_bytes()
            append_reviews(path, reviewed_fees())
            self.assertEqual(first, path.read_bytes())
            with self.assertRaises(ValueError):
                append_reviews(path, [dict(previous, checked_at='2000-01-01')])
            self.assertEqual(first, path.read_bytes())

    def test_whole_importer_is_idempotent(self):
        paths = [ROOT / 'outputs/venues/catalogs' / name for name in
                 ['tokyo_tennis.json', 'tokyo_sports.json', 'tokyo_expansion.json', 'fee_plans.json', 'cancellation_policies.json']]
        before = [hashlib.sha256(path.read_bytes()).hexdigest() for path in paths]
        subprocess.run([sys.executable, '-X', 'utf8', str(ROOT / 'scripts/record_venue_fee_review_20261019.py')],
                       check=True, capture_output=True)
        self.assertEqual(before, [hashlib.sha256(path.read_bytes()).hexdigest() for path in paths])


if __name__ == '__main__':
    unittest.main()
