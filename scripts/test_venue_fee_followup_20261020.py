"""Verified facility identity, same-unit tariffs, closures and no guessed prices."""
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
from venues.sports_catalog import get_catalog, filter_catalog, has_price
import record_venue_fee_review_20261020 as review


class OfficialVenueReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {r['id']: r for r in get_catalog()['courts']}

    def ranges(self, ident):
        return {r['unit']: (r['minimum'], r['maximum']) for r in self.rows[ident]['fee_ranges']}

    def test_23_existing_records_19_new_prices_15_policies(self):
        self.assertEqual(len(set(review.REVIEWED_IDS)), 23)
        self.assertEqual(len(review.reviewed_fees()), 19)
        self.assertEqual(len(review.reviewed_policies()), 15)
        for item in review.reviewed_fees():
            row = self.rows[item['id']]
            self.assertEqual(row['fee_checked_at'], review.CHECKED)
            self.assertEqual(row['fee_options'], item['fee_options'])
            self.assertEqual(row['fee_note'], item['fee_note'])
            self.assertTrue(has_price(row))
            self.assertIsNone(row['price_from'])
            self.assertTrue(all(p['amount'] > 0 and p['conditions'] and p['source_url'].startswith('https://')
                                for p in row['fee_options']))
        for item in review.reviewed_policies():
            self.assertEqual(self.rows[item['id']]['cancellation'], item)
        self.assertEqual(len(self.rows), 1206)
        later = sum(has_price(r) and r.get('fee_checked_at', '') > review.CHECKED for r in self.rows.values())
        self.assertEqual(sum(has_price(r) for r in self.rows.values()) - later, 729)
        self.assertEqual(sum(not has_price(r) for r in self.rows.values()) + later, 477)

    def test_city_only_grounds_and_practice_only_not_free_for_everyone(self):
        for ident, price in zip(review.FIELDS, [200, 400, 200, 400]):
            self.assertEqual(self.ranges(ident), {'多目的運動広場1面・2時間': (price, price)})
            for text in ['10人以上', '構成員全員', '市外団体の利用対象ではありません']:
                self.assertIn(text, self.rows[ident]['fee_note'])
        self.assertIn('練習のみ', self.rows[review.FIELDS[2]]['fee_note'])

    def test_tachikawa_durations_partition_and_published_rounding(self):
        self.assertEqual(self.ranges(review.GYMS[0]), {
            '第1体育室全面・3時間30分': (8000, 17800), '第1体育室全面・2時間30分': (7600, 15200),
            '第1体育室半面・3時間30分': (4000, 8900), '第1体育室半面・2時間30分': (3800, 7600)})
        izumi = self.ranges(review.GYMS[1])
        self.assertEqual(izumi['第1体育室全面・3時間30分'], (12000, 32000))
        self.assertEqual(izumi['第1体育室3分の1面・3時間30分'], (4000, 10700))
        self.assertEqual(izumi['第2体育室全面・3時間30分'], (4500, 11400))
        self.assertIn('第2体育室は卓球等用', self.rows[review.GYMS[0]]['fee_note'])

    def test_nishitokyo_current_prices_not_future_closure(self):
        for ident in [review.NISHITOKYO_GYMS[0], review.NISHITOKYO_GYMS[2]]:
            self.assertEqual(self.ranges(ident), {'第1体育室全面・3時間': (7600, 15200),
                                                '第1体育室半面・3時間': (3800, 7600)})
        self.assertEqual(self.ranges(review.NISHITOKYO_GYMS[1]), {'第1体育室全面・3時間': (5400, 10800)})
        row = self.rows[review.NISHITOKYO_GYMS[0]]
        self.assertNotEqual(row['availability_status'], 'SUSPENDED')
        self.assertIn('2027年7月', row['fee_note'])
        self.assertIn('一般の6～4日前取消が全て半額になるわけではありません', row['cancellation']['summary'])

    def test_oi_same_name_main_sub_have_separate_tariffs(self):
        main, sub = [self.rows[i] for i in review.OI]
        self.assertEqual(main['name'], sub['name'])
        self.assertNotEqual(main['booking_url'], sub['booking_url'])
        self.assertEqual(self.ranges(review.OI[0]), {'メインピッチ・3時間': (33000, 42000),
                                                  'メインピッチ・4時間': (44000, 56000)})
        self.assertEqual(self.ranges(review.OI[1]), {'サブピッチ・3時間': (24000, 33000),
                                                  'サブピッチ・4時間': (32000, 44000)})
        self.assertIn('Webは空き照会', main['fee_note'])
        self.assertIn('具体的な料率・期限', main['cancellation']['summary'])

    def test_other_gyms_correct_room_and_unequal_slots(self):
        self.assertEqual(self.ranges(review.HIGASHI), {'アリーナ全面・2時間': (8500, 8500),
                                                     'アリーナ半面・2時間': (4200, 4200)})
        self.assertEqual(self.ranges(review.TSUKIJI)['体育場全面・3時間'], (6500, 12900))
        self.assertEqual(self.ranges(review.TSUKIJI)['体育場半面・4時間'], (6450, 6450))
        self.assertEqual(self.ranges(review.ARIAKE), {'サブアリーナ全面・4時間': (30800, 44550),
                                                    'サブアリーナ全面・全日12時間': (77000, 99000),
                                                    'サブアリーナ半面・4時間': (18480, 26730)})
        self.assertEqual(self.ranges(review.YASHIO), {'スポーツ室・3時間15分': (4700, 5600)})
        self.assertIn('八潮5-10-27', self.rows[review.YASHIO]['fee_note'])
        self.assertIn('木・金・土', self.rows[review.YASHIO]['fee_note'])
        for ident in [review.HIGASHI, review.TSUKIJI, review.ARIAKE, review.YASHIO]:
            self.assertIsNone(self.rows[ident]['cancellation'])

    def test_shiba_yoyogi_edogawa_right_sport_and_source_revision(self):
        self.assertEqual(self.ranges(review.SHIBA), {'フットサルコート1面・2時間': (2600, 2600)})
        self.assertEqual(self.ranges(review.YOYOGI), {'サッカー場全面・1時間': (3600, 3600)})
        row = self.rows[review.SPORTSLAND]
        self.assertEqual(self.ranges(review.SPORTSLAND), {'フットサルコート1面・1時間': (670, 670)})
        self.assertIn('旧630円は採用しません', row['fee_note'])
        self.assertIn('320円', row['fee_note'])
        self.assertIn('8日前まで', self.rows[review.YOYOGI]['cancellation']['summary'])
        self.assertIn('6日前～開始前', row['cancellation']['summary'])

    def test_minamiosawa_member_visitor_distinct_and_four_hour_exception(self):
        row = self.rows[review.MINAMIOSAWA]
        self.assertEqual(self.ranges(review.MINAMIOSAWA), {'Aコート1面・1時間': (6000, 12000),
                                                        'B多目的コート1面・1時間': (7150, 12100)})
        self.assertIn('別途登録・更新費', row['fee_note'])
        self.assertIn('ゴールのない', row['fee_note'])
        for text in ['14日前まで無料', '13～7日前50%', '4時間以上', '雨天']:
            self.assertIn(text, row['cancellation']['summary'])

    def test_two_closed_records_hidden_not_deleted_and_two_holds_not_fabricated(self):
        for ident, info in review.CLOSURES.items():
            row = self.rows[ident]
            self.assertEqual(row['availability_status'], 'SUSPENDED')
            self.assertEqual(row['availability_note'], info['note'])
            self.assertFalse(has_price(row))
            self.assertEqual(filter_catalog([row], {}), [])
            self.assertEqual(len(filter_catalog([row], {'show_suspended': '1'})), 1)
        for ident in review.HELD:
            self.assertEqual(self.rows[ident]['fee_checked_at'], '2026-10-25')
            self.assertTrue(all(p['unit'].startswith('武道場') if ident == review.HELD[0]
                                else p['unit'] == '庭球場1面・1時間（単価）'
                                for p in self.rows[ident]['fee_options']))
            self.assertIn('球技コート' if ident == review.HELD[0] else 'フットサル',
                          self.rows[ident]['fee_note'])

    def test_preflight_refuses_overwrite_and_append_is_idempotent(self):
        with tempfile.TemporaryDirectory(dir=ROOT / 'work') as temporary:
            path = Path(temporary) / 'fee_plans.json'
            path.write_text('[]', encoding='utf-8')
            review.append_reviews(path, review.reviewed_fees())
            first = path.read_bytes()
            review.append_reviews(path, review.reviewed_fees())
            self.assertEqual(first, path.read_bytes())
            with self.assertRaises(ValueError):
                review.append_reviews(path, [dict(review.reviewed_fees()[0], checked_at='2000-01-01')])
            self.assertEqual(first, path.read_bytes())
        fake = dict(self.rows[review.FIELDS[0]], fee_checked_at='2000-01-01')
        rows = [fake if r['id'] == fake['id'] else r for r in self.rows.values()]
        with patch.object(review, 'get_catalog', return_value={'courts': rows}), patch.object(review, 'mark_closed') as closed:
            with self.assertRaises(ValueError):
                review.main()
            closed.assert_not_called()

    def test_importer_repeated_run_changes_no_file(self):
        paths = [review.CATALOGS / name for name in ['tokyo_tennis.json', 'tokyo_sports.json',
                                                   'tokyo_expansion.json', 'fee_plans.json', 'cancellation_policies.json']]
        before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
        subprocess.run([sys.executable, '-X', 'utf8', str(ROOT / 'scripts/record_venue_fee_review_20261020.py')],
                       check=True, capture_output=True)
        self.assertEqual(before, [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths])


if __name__ == '__main__':
    unittest.main()
