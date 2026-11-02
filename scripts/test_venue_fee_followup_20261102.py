"""Exact source transcription, unit separation, and preservation for November 2."""
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
import record_venue_fee_review_20261102 as review


class November2VenueReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {r['id']: r for r in get_catalog()['courts']}

    def ranges(self, ident):
        return {r['unit']: (r['minimum'], r['maximum']) for r in self.rows[ident]['fee_ranges']}

    def test_review_counts_exact_entries_and_inventory(self):
        self.assertEqual(len(set(review.REVIEWED_IDS)), 30)
        self.assertEqual(len(review.reviewed_fees()), 17)
        self.assertEqual(len(review.reviewed_policies()), 17)
        self.assertEqual(len(self.rows), 1206)
        self.assertEqual(sum(has_price(r) for r in self.rows.values()), 878)
        self.assertEqual(sum(not has_price(r) for r in self.rows.values()), 328)
        self.assertEqual(sum(not has_price(r) and r['availability_status'] != 'SUSPENDED' for r in self.rows.values()), 319)
        for fee in review.reviewed_fees():
            row = self.rows[fee['id']]
            self.assertEqual(row['fee_options'], fee['fee_options'])
            self.assertEqual(row['fee_note'], fee['fee_note'])
            self.assertEqual(row['fee_checked_at'], review.CHECKED)
            self.assertTrue(all(p['amount'] > 0 and p['source_url'].startswith('https://') for p in row['fee_options']))
        for policy in review.reviewed_policies():
            self.assertEqual(self.rows[policy['id']]['cancellation'], policy)

    def test_shinagawa_exact_single_room_and_six_distinct_units(self):
        for ident, inside, outside in review.SHINA_ROOMS:
            expected = {'第1集会室・' + duration + '（' + group + '）': (amount, amount)
                        for group, values in [('区内・通常', inside), ('区外・通常', outside)]
                        for (_, duration), amount in zip(review.PERIODS, values)}
            self.assertEqual(self.ranges(ident), expected)
            for phrase in ['第1集会室単室', '全室の最安値ではありません', '半数以上', '2名以上', '5割減額', '不特定多数', '日曜祝日']:
                self.assertIn(phrase, self.rows[ident]['fee_note'])

    def test_bunkyo_duration_and_co_located_facilities_not_merged(self):
        for ident, room, values, source in review.BUNKYO_ROOMS:
            self.assertEqual(self.ranges(ident), {room + '・3時間30分（区内利用資格・通常）': (values[0], values[0]),
                                                room + '・4時間（区内利用資格・通常）': (min(values[1:]), max(values[1:]))})
            self.assertIn('併設アカデミー', self.rows[ident]['fee_note'])
            self.assertIn('営利目的不可', self.rows[ident]['fee_note'])
            self.assertTrue(all(p['source_url'] == source for p in self.rows[ident]['fee_options']))

    def test_kudan_member_eligibility_and_no_extension_in_base_price(self):
        self.assertEqual(self.ranges(review.KUDAN), {'6階レクリエーションホール・3時間（登録団体・通常）': (2400, 3900),
                                                    '6階レクリエーションホール・4時間（登録団体・通常）': (3100, 3100)})
        for phrase in ['5名以上', '半数以上', '登録会員以外', '30分延長は別料金']:
            self.assertIn(phrase, self.rows[review.KUDAN]['fee_note'])

    def test_tansu_admission_day_type_and_non_round_duration(self):
        actual = self.ranges(review.TANSU)
        self.assertEqual(len(actual), 12)
        self.assertEqual(actual['ホール全体・4時間（土日祝・入場料なし）'], (32600, 40400))
        self.assertEqual(actual['ホール全体・4時間（土日祝・入場料あり）'], (65200, 81200))
        self.assertEqual(actual['ホール全体・12時間45分（平日・入場料あり）'], (134600, 134600))
        self.assertIn('物品販売・募金', self.rows[review.TANSU]['fee_note'])
        self.assertIn('在勤のみは区外', self.rows[review.TANSU]['fee_note'])

    def test_ebara_hall_not_stage_or_general_room_terms(self):
        actual = self.ranges(review.HALL)
        self.assertEqual(len(actual), 12)
        self.assertEqual(actual['大ホール全体・3時間（区民・平日）'], (12600, 12600))
        self.assertEqual(actual['大ホール全体・3時間30分（区民以外・土日祝）'], (25100, 25100))
        self.assertEqual(actual['大ホール全体・4時間（区民以外・土日祝）'], (33200, 33200))
        self.assertIn('日曜祝日の夜間は休館', self.rows[review.HALL]['fee_note'])
        text = self.rows[review.HALL]['cancellation']['summary']
        for phrase in ['専用規約', '1か月前', '半額返金', '予納金は返金不可', '附帯設備']:
            self.assertIn(phrase, text)

    def test_pickle_late_revision_not_old_homepage_or_personal_participation(self):
        self.assertEqual(self.ranges(review.PICKLE), {'コート1面・1時間（平日・通常）': (6500, 9000),
                                                      'コート1面・1時間（土日祝・通常）': (10000, 11000)})
        self.assertIn('未発表の会員割引', self.rows[review.PICKLE]['fee_note'])
        text = self.rows[review.PICKLE]['cancellation']['summary']
        for phrase in ['前日50%', '当日100%', '1mm以上', '前日17時', '本人都合', '料率は明記なし']:
            self.assertIn(phrase, text)

    def test_refund_procedure_and_disaster_conditions_not_unconditional_free(self):
        for ident, _, _ in review.SHINA_ROOMS:
            text = self.rows[ident]['cancellation']['summary']
            for phrase in ['7日前', '全額現金', '翌営業日', '警戒レベル3以上', '震度5弱以上', '通常の雨']:
                self.assertIn(phrase, text)
        for ident, _, _, _ in review.BUNKYO_ROOMS:
            text = self.rows[ident]['cancellation']['summary']
            for phrase in ['3日前', '相当の理由', '5割', '1時間以内', '未確認']:
                self.assertIn(phrase, text)
        text = self.rows[review.TANSU]['cancellation']['summary']
        for phrase in ['未入金でも', '14日前', '7割', '変更後', '還付なし']:
            self.assertIn(phrase, text)

    def test_all_thirteen_holds_stay_unknown_with_original_status(self):
        self.assertEqual(len(review.HOLDS), 13)
        for ident in review.HOLDS:
            self.assertFalse(has_price(self.rows[ident]))
            self.assertEqual(self.rows[ident]['fee_ranges'], [])
        self.assertEqual(sum(self.rows[i]['availability_status'] == 'SUSPENDED' for i in review.HOLDS), 7)

    def test_mobile_detail_track_cannot_expand_to_long_tariff_min_content(self):
        css = (ROOT / 'outputs/venues/static/tennis.css').read_text(encoding='utf-8')
        self.assertIn('.venue-detail-content{grid-template-columns:minmax(0,1fr);gap:16px}', css)
        self.assertNotIn('.venue-detail-content{grid-template-columns:1fr;gap:16px}', css)
        self.assertIn('.venue-cancellation{overflow-wrap:anywhere}', css)

    def test_original_catalogs_and_prior_reviews_unchanged(self):
        for name in ['tokyo_tennis.json', 'tokyo_sports.json', 'tokyo_expansion.json', 'fee_plans.json', 'cancellation_policies.json']:
            rel = 'outputs/venues/catalogs/' + name
            old = json.loads(subprocess.check_output(['git', 'show', review.BASE + ':' + rel], cwd=ROOT))
            new = json.loads((ROOT / rel).read_text(encoding='utf-8'))
            if name.startswith('tokyo_'):
                self.assertEqual(old, new)
            else:
                self.assertEqual(old, new[:len(old)])
                self.assertEqual(len(new) - len(old), 17)

    def test_idempotence_and_conflict_refusal_before_any_write(self):
        paths = [review.CATALOGS / p for p in ['fee_plans.json', 'cancellation_policies.json']]
        before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
        subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/record_venue_fee_review_20261102.py')], check=True, capture_output=True)
        self.assertEqual(before, [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths])
        fake = dict(self.rows[review.PICKLE], fee_checked_at='2000-01-01')
        rows = [fake if r['id'] == fake['id'] else r for r in self.rows.values()]
        with patch.object(review, 'get_catalog', return_value={'courts': rows}), patch.object(review, 'append_reviews') as append:
            with self.assertRaises(ValueError):
                review.main()
            append.assert_not_called()


if __name__ == '__main__':
    unittest.main()
