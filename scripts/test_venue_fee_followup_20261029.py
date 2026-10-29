"""Room/period/eligibility boundaries and append-only venue research regression checks."""
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
import record_venue_fee_review_20261029 as review


class October29VenueReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {r['id']: r for r in get_catalog()['courts']}

    def ranges(self, ident):
        return {r['unit']: (r['minimum'], r['maximum']) for r in self.rows[ident]['fee_ranges']}

    def test_count_and_exact_published_entries(self):
        self.assertEqual(len(set(review.REVIEWED_IDS)), 25)
        self.assertEqual(len(review.reviewed_fees()), 19)
        self.assertEqual(len(review.reviewed_policies()), 19)
        for entry in review.reviewed_fees():
            actual = self.rows[entry['id']]
            self.assertEqual(actual['fee_options'], entry['fee_options'])
            self.assertEqual(actual['fee_note'], entry['fee_note'])
            self.assertEqual(actual['fee_checked_at'], review.CHECKED)
        for entry in review.reviewed_policies():
            self.assertEqual(self.rows[entry['id']]['cancellation'], entry)
        self.assertEqual(len(self.rows), 1206)
        self.assertEqual(sum(has_price(r) for r in self.rows.values()), 861)
        self.assertEqual(sum(not has_price(r) for r in self.rows.values()), 345)
        self.assertEqual(sum(not has_price(r) and r['availability_status'] != 'SUSPENDED' for r in self.rows.values()), 336)

    def test_taito_room_duration_and_eligibility_not_combined(self):
        for ident, room, inside, outside in review.TAITO_ROOMS:
            actual = self.ranges(ident)
            self.assertEqual(len(actual), 8)
            for group, values, source in [('区内・入場料徴収なし', inside, review.TAITO_IN), ('区外・入場料徴収なし', outside, review.TAITO_OUT)]:
                expected = {'3時間': (min(values[0], values[2]), max(values[0], values[2])),
                            '4時間': (min(values[1], values[3]), max(values[1], values[3])),
                            '12時間': (values[4], values[4]), '13時間': (values[5], values[5])}
                for duration, bounds in expected.items():
                    self.assertEqual(actual[room + '・' + duration + '（' + group + '）'], bounds)
                self.assertTrue(all(p['source_url'] == source for p in self.rows[ident]['fee_options'] if group in p['label']))
            for phrase in ['のみ', '施設全室', '5割以上', '原則登録構成員以外', '入場料等の徴収なし', '配信目的']:
                self.assertIn(phrase, self.rows[ident]['fee_note'])

    def test_chiyoda_no_hourly_or_other_room_minimum(self):
        for ident, room, values in review.CHIYODA_ROOMS:
            self.assertEqual(self.ranges(ident), {room + '・3時間（一般団体）': (values[0], values[0]),
                                                room + '・4時間（一般団体）': (min(values[1:]), max(values[1:]))})
            self.assertIn('名簿外', self.rows[ident]['fee_note'])
            self.assertIn('全室最安値', self.rows[ident]['fee_note'])

    def test_para_restored_source_not_personal_fee_or_unconditional_zero(self):
        self.assertEqual(self.ranges(review.PARA), {'体育室・4時間（平日・通常団体）': (7000, 8800),
                                                   '体育室・4時間（土日祝・通常団体）': (8800, 11000)})
        self.assertIn('半数以上が障害者', self.rows[review.PARA]['fee_note'])
        self.assertIn('当面料金免除', self.rows[review.PARA]['fee_note'])
        self.assertFalse(any(p['amount'] == 0 for e in review.reviewed_fees() for p in e['fee_options']))

    def test_six_holds_remain_unknown_not_old_closure_or_restricted_prices(self):
        for ident in review.HOLDS:
            self.assertFalse(has_price(self.rows[ident]))
            self.assertEqual(self.rows[ident]['fee_ranges'], [])
        self.assertIn('貸切受付停止', self.rows['tokyo-gym-aa77f48e78d0']['cancellation']['summary'])

    def test_policy_qualifications(self):
        for ident, _, _, _ in review.TAITO_ROOMS:
            text = self.rows[ident]['cancellation']['summary']
            for phrase in ['2か月前', '80%', '50%', '7日前', '自然災害', '通常の雨天']:
                self.assertIn(phrase, text)
        for ident, _, _ in review.CHIYODA_ROOMS:
            text = self.rows[ident]['cancellation']['summary']
            for phrase in ['前日', '当日予約は取消不可', '割合', '未確認']:
                self.assertIn(phrase, text)
        self.assertIn('無断取消', self.rows[review.PARA]['cancellation']['summary'])
        self.assertIn('料率', self.rows[review.PARA]['cancellation']['summary'])

    def test_catalog_id_booking_and_previous_review_prefix_preserved(self):
        for name in ['tokyo_tennis.json', 'tokyo_sports.json', 'tokyo_expansion.json', 'fee_plans.json', 'cancellation_policies.json']:
            rel = 'outputs/venues/catalogs/' + name
            old = json.loads(subprocess.check_output(['git', 'show', review.BASE + ':' + rel], cwd=ROOT))
            new = json.loads((ROOT / rel).read_text(encoding='utf-8'))
            if name.startswith('tokyo_'):
                self.assertEqual(old, new)
            else:
                self.assertEqual(old, new[:len(old)])
                self.assertEqual(len(new) - len(old), 19)

    def test_idempotence_and_conflict_no_write(self):
        paths = [review.CATALOGS / p for p in ['fee_plans.json', 'cancellation_policies.json']]
        before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
        subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/record_venue_fee_review_20261029.py')], check=True, capture_output=True)
        self.assertEqual(before, [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths])
        fake = dict(self.rows[review.PARA], fee_checked_at='2000-01-01')
        rows = [fake if r['id'] == fake['id'] else r for r in self.rows.values()]
        with patch.object(review, 'get_catalog', return_value={'courts': rows}), patch.object(review, 'append_reviews') as append:
            with self.assertRaises(ValueError):
                review.main()
            append.assert_not_called()


if __name__ == '__main__':
    unittest.main()
