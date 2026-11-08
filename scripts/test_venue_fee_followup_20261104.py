"""Official tariff scope, real zero, closure and append-only regression checks."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'outputs'))
from venues.sports_catalog import get_catalog, has_price, filter_catalog
import record_venue_fee_review_20261104 as review
from venue_review_test_helpers import before_november4_closure, assert_historical_hold


class November4VenueReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {r['id']: r for r in get_catalog()['courts']}

    def ranges(self, ident):
        return {r['unit']: (r['minimum'], r['maximum']) for r in self.rows[ident]['fee_ranges']}

    def test_exact_review_inventory_and_new_records(self):
        self.assertEqual(len(set(review.REVIEWED_IDS)), 20)
        self.assertEqual(len(review.reviewed_fees()), 15)
        self.assertEqual(len(review.reviewed_policies()), 14)
        self.assertEqual(len(self.rows), 1206)
        later = sum(has_price(r) and r.get('fee_checked_at', '') > review.CHECKED for r in self.rows.values())
        later_closures = sum(not has_price(r) and r['availability_status'] == 'SUSPENDED' and r['checked_at'] > review.CHECKED for r in self.rows.values())
        self.assertEqual(sum(has_price(r) for r in self.rows.values()) - later, 906)
        self.assertEqual(sum(not has_price(r) for r in self.rows.values()) + later, 300)
        self.assertEqual(sum(not has_price(r) and r['availability_status'] != 'SUSPENDED' for r in self.rows.values()) + later + later_closures, 289)
        for fee in review.reviewed_fees():
            row = self.rows[fee['id']]
            self.assertEqual(row['fee_checked_at'], review.CHECKED)
            self.assertEqual(row['fee_options'], fee['fee_options'])
            self.assertEqual(row['fee_note'], fee['fee_note'])
            self.assertTrue(all(p['amount'] >= 0 if fee['id'] == review.SHINKAWA else p['amount'] > 0 for p in row['fee_options']))
        for policy in review.reviewed_policies():
            self.assertEqual(self.rows[policy['id']]['cancellation'], policy)

    def test_ota_exact_room_and_duration_ranges_not_approximate_nonresident(self):
        for ident, _, room, weekday, holiday, short in review.MEETINGS:
            expected = {}
            for day, values in [('平日', weekday), ('土日祝', holiday)]:
                suffix = '（区内通常・' + day + '）'
                expected[room + '・3時間' + suffix] = (values[0], values[0])
                if short:
                    expected[room + '・3時間30分' + suffix] = (values[1], values[1])
                    expected[room + '・4時間' + suffix] = (values[2], values[2])
                else:
                    expected[room + '・4時間' + suffix] = (min(values[1:]), max(values[1:]))
            self.assertEqual(self.ranges(ident), expected)
            for phrase in ['単室', '約2割増', '算出せず', '全室の最安値ではありません']:
                self.assertIn(phrase, self.rows[ident]['fee_note'])
        self.assertIn('施設へ直接', self.rows['tokyo-venue-acafbf43b734']['fee_note'])

    def test_gyms_are_whole_room_and_haneda_does_not_use_other_building_tariff(self):
        self.assertEqual(self.ranges('tokyo-venue-3dad1de4b1e7'), {'体育室・3時間（通常）': (1700, 1700), '体育室・2時間30分（通常）': (1400, 1400)})
        self.assertEqual(self.ranges('tokyo-venue-8d8fb7de1c48'), {'体育室・3時間（通常）': (1500, 1500), '体育室・2時間30分（通常）': (1200, 1200)})
        haneda = self.rows['tokyo-venue-52d36d518953']
        self.assertEqual(self.ranges(haneda['id']), {'第一集会室・3時間（通常）': (1300, 1300), '第一集会室・4時間（通常）': (1800, 1800)})
        self.assertIn('別棟', haneda['fee_note'])
        self.assertTrue(all('体育室' not in p['unit'] for p in haneda['fee_options']))
        self.assertIn('正式なバスケットコートはとれません', self.rows['tokyo-venue-8d8fb7de1c48']['fee_note'])

    def test_kam_room_and_local_only_not_studio_or_hall(self):
        self.assertEqual(self.ranges(review.KAM), {'第一集会室・3時間（区内通常）': (1600, 1600), '第一集会室・4時間（区内通常）': (2100, 2100)})
        self.assertIn('区内の団体・個人', self.rows[review.KAM]['fee_note'])
        self.assertIn('30日以上前', self.rows[review.KAM]['cancellation']['summary'])
        self.assertIn('割合を推測しません', self.rows[review.KAM]['cancellation']['summary'])

    def test_meguro_other_groups_only_and_actual_periods(self):
        for ident, _, room, values in review.MEGURO_ROOMS:
            self.assertEqual(self.ranges(ident), {room + '・3時間（その他団体）': (values[0], values[0]),
                                                room + '・2時間30分（その他団体）': (min(values[1:]), max(values[1:]))})
            for phrase in ['区外のみ', '割引料金', '1か月前', '球技場利用料へ流用しません']:
                self.assertIn(phrase, self.rows[ident]['fee_note'])
            text = self.rows[ident]['cancellation']['summary']
            for phrase in ['間に20日', '75%', '50%', '両端の日を含めない', '警戒レベル3', '利用開始前', '自己取消せず']:
                self.assertIn(phrase, text)

    def test_only_proven_free_group_hire_is_zero_not_unknown(self):
        row = self.rows[review.SHINKAWA]
        self.assertEqual(self.ranges(review.SHINKAWA), {'球技場1面・2時間（登録承認団体・無料）': (0, 0),
                                                      '球技場1面・1時間30分（登録承認団体・無料）': (0, 0)})
        for phrase in ['団体登録・承認', '6人以上', '9人以上', '半数以上', '2026年10月以降', '営利行為不可', '当日予約不可']:
            self.assertIn(phrase, row['fee_note'])
        self.assertTrue(all(p['source_url'] == review.SHINKAWA_PAGE for p in row['fee_options']))
        self.assertEqual(row['cancellation']['checked_at'], '2026-10-25')
        self.assertIn('7日前', row['cancellation']['summary'])
        assert_historical_hold(self, row)
        bad = dict(row, fee_options=[])
        with self.assertRaises(AssertionError):
            assert_historical_hold(self, bad)

    def test_hold_and_closure_are_not_erased_or_old_prices_reused(self):
        for ident in review.HOLDS:
            assert_historical_hold(self, self.rows[ident])
        row = self.rows[review.CLOSED]
        self.assertEqual(row['availability_status'], 'SUSPENDED')
        self.assertEqual(row['availability_note'], review.CLOSURE_NOTE)
        self.assertEqual(row['checked_at'], review.CHECKED)
        self.assertEqual(filter_catalog([row], {}), [])
        self.assertEqual(filter_catalog([row], {'show_suspended': '1'}), [row])

    def test_ota_general_rules_do_not_promise_park_weather_refund(self):
        for ident, *_ in review.MEETINGS + review.CULTURE:
            summary = self.rows[ident]['cancellation']['summary']
            for phrase in ['原則還付なし', '例外あり', '推測せず', '雨天全額還付', '流用しません']:
                self.assertIn(phrase, summary)

    def test_all_original_data_and_prior_reviews_preserved(self):
        for name in ['tokyo_tennis.json', 'tokyo_sports.json', 'tokyo_expansion.json', 'fee_plans.json', 'cancellation_policies.json']:
            rel = 'outputs/venues/catalogs/' + name
            old = json.loads(subprocess.check_output(['git', 'show', review.BASE + ':' + rel], cwd=ROOT))
            new = json.loads((ROOT / rel).read_bytes())
            if name.startswith('tokyo_'):
                self.assertEqual(old, before_november4_closure(new, old))
                self.assertEqual([r['id'] for r in old], [r['id'] for r in new])
                self.assertEqual([r['booking_url'] for r in old], [r['booking_url'] for r in new])
            else:
                self.assertEqual(old, new[:len(old)])
                additions = review.reviewed_fees() if name == 'fee_plans.json' else review.reviewed_policies()
                self.assertEqual(new[len(old):len(old) + len(additions)], additions)
                self.assertTrue(all(r['checked_at'] > review.CHECKED for r in new[len(old) + len(additions):]))

    def test_closure_exception_rejects_any_other_source_change(self):
        rel = 'outputs/venues/catalogs/tokyo_expansion.json'
        old = json.loads(subprocess.check_output(['git', 'show', review.BASE + ':' + rel], cwd=ROOT))
        new = json.loads((ROOT / rel).read_bytes())
        closed, = [r for r in new if r['id'] == review.CLOSED]
        closed['sources'].append({'title': 'unapproved', 'url': 'https://example.com/'})
        with self.assertRaises(AssertionError):
            before_november4_closure(new, old)

    def test_idempotence_and_preflight_refuses_conflicting_price(self):
        paths = [review.CATALOGS / p for p in ['fee_plans.json', 'cancellation_policies.json', 'tokyo_expansion.json']]
        before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
        subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/record_venue_fee_review_20261104.py')], check=True, capture_output=True)
        self.assertEqual(before, [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths])
        fake = dict(self.rows[review.SHINKAWA], fee_checked_at='2000-01-01')
        rows = [fake if r['id'] == fake['id'] else r for r in self.rows.values()]
        with patch.object(review, 'get_catalog', return_value={'courts': rows}), patch.object(review, 'update_closure') as closure, patch.object(review, 'append_reviews') as append:
            with self.assertRaises(ValueError):
                review.main()
            closure.assert_not_called()
            append.assert_not_called()


if __name__ == '__main__':
    unittest.main()
