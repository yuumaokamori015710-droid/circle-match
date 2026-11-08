"""Exact residency/duration ranges, closure isolation and append-only checks."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch
from urllib.parse import urlencode

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'outputs'))
from venues.sports_catalog import get_catalog, has_price, filter_catalog
import record_venue_fee_review_20261106 as review
from venue_review_test_helpers import before_november6_closure
from test_venues import IsolatedAppHttpCase


class November6VenueReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {r['id']: r for r in get_catalog()['courts']}

    def ranges(self, ident):
        return {r['unit']: (r['minimum'], r['maximum']) for r in self.rows[ident]['fee_ranges']}

    def test_exact_inventory_and_sources(self):
        self.assertEqual(len(set(review.REVIEWED_IDS)), 26)
        self.assertEqual(len(review.reviewed_fees()), 19)
        self.assertEqual(len(review.reviewed_policies()), 18)
        self.assertEqual(len(self.rows), 1206)
        later = sum(has_price(r) and r.get('fee_checked_at', '') > review.CHECKED for r in self.rows.values())
        self.assertEqual(sum(has_price(r) for r in self.rows.values()) - later, 941)
        self.assertEqual(sum(not has_price(r) for r in self.rows.values()) + later, 265)
        self.assertEqual(sum(not has_price(r) and r['availability_status'] != 'SUSPENDED' for r in self.rows.values()) + later, 254)
        for fee in review.reviewed_fees():
            row = self.rows[fee['id']]
            self.assertEqual(row['fee_checked_at'], review.CHECKED)
            self.assertEqual(row['fee_options'], fee['fee_options'])
            self.assertEqual(row['fee_note'], fee['fee_note'])
            self.assertTrue(all(p['amount'] > 0 for p in row['fee_options']))
        for policy in review.reviewed_policies():
            self.assertEqual(self.rows[policy['id']]['cancellation'], policy)
        from venue_review_test_helpers import assert_historical_hold
        for ident in review.HOLDS:
            assert_historical_hold(self, self.rows[ident])

    def test_residency_and_seasonal_duration_are_separate(self):
        for ident in review.MUSASHI[:2]:
            self.assertEqual(self.ranges(ident), {
                'テニスコート1面・2時間（市内登録団体）': (1020, 1020),
                'テニスコート1面・2時間（市外登録団体）': (2040, 2040),
                'テニスコート1面・1時間（市内登録団体・季節限定）': (510, 510),
                'テニスコート1面・1時間（市外登録団体・季節限定）': (1020, 1020)})
            self.assertIn('営利目的利用不可', self.rows[ident]['fee_note'])
        for ident, _, amount, _ in review.FUSSA:
            self.assertEqual(self.ranges(ident), {
                'テニスコート1面・1時間（市内・照明別）': (amount, amount),
                'テニスコート1面・1時間（市外・照明別）': (amount * 3, amount * 3)})
            self.assertIsNone(self.rows[ident]['cancellation'])
            self.assertIn('未確認', self.rows[ident]['fee_note'])
        self.assertIn('フットサルはテニス2面分', self.rows['fussa-musashinodai']['fee_note'])

    def test_tachikawa_eligibility_and_cancel_penalty_not_money(self):
        self.assertEqual(self.ranges('tachikawa-sunagawa'), {'テニスコート1面・2時間（市内登録個人）': (100, 100)})
        self.assertIn('5人以上', self.rows[review.JIJI]['fee_note'])
        self.assertIn('14日前', self.rows[review.JIJI]['cancellation']['summary'])
        for ident in review.TACHIKAWA:
            self.assertIn('取消料ではありません', self.rows[ident]['cancellation']['summary'])
            self.assertIn(review.TACHI_CANCEL, self.rows[ident]['fee_note'])
        self.assertIn('開始前', self.rows['tachikawa-izumi']['cancellation']['summary'])

    def test_future_hino_tariffs_do_not_enter_current_ranges(self):
        for ident in review.HINO[:2]:
            self.assertEqual(list(self.ranges(ident).values()), [(700, 700)])
            self.assertIn('2027年4月1日から980円', self.rows[ident]['fee_note'])
        self.assertEqual(self.ranges('hino-nanao'), {
            'テニスコート1面・2時間（通常基本）': (2100, 2100),
            'テニスコート1面・3時間（通常基本・指定枠）': (3150, 3150)})
        for ident in review.HINO:
            text = self.rows[ident]['cancellation']['summary']
            self.assertIn('取消料は取らない', text)
            self.assertIn('返還不可', text)
            self.assertIn('雨天', text)

    def test_refund_percentages_are_not_cancellation_charges(self):
        for ident in review.KIYOSE:
            if ident in ('kiyose-chuo', 'kiyose-shimokiyoto'):
                self.assertEqual(self.rows[ident]['price_from'], 600)
                self.assertFalse(self.rows[ident].get('fee_options'))
            else:
                self.assertEqual(self.ranges(ident), {
                    'テニスコート1面・2時間（市内通常）': (600, 600),
                    'テニスコート1面・2時間（市外通常）': (900, 900)})
            text = self.rows[ident]['cancellation']['summary']
            for phrase in ['30日前まで80%', '20日前まで60%', '前日まで30%', '取消料の割合ではありません']:
                self.assertIn(phrase, text)
        for ident in review.MUSASHI:
            for phrase in ['1時間以内', '1か月', '全額無料とは表示しません']:
                self.assertIn(phrase, self.rows[ident]['cancellation']['summary'])

    def test_closed_court_stays_hidden_and_not_confused_with_shared_personal_use(self):
        row = self.rows[review.CLOSED]
        self.assertEqual(row['availability_status'], 'SUSPENDED')
        self.assertEqual(row['availability_note'], review.CLOSURE_NOTE)
        self.assertEqual(filter_catalog([row], {}), [])
        self.assertEqual(filter_catalog([row], {'show_suspended': '1'}), [row])
        for ident, _, amount in review.MITAKA:
            self.assertEqual(list(self.ranges(ident).values()), [(amount, amount)])
            self.assertIn('1人あたり', self.rows[ident]['fee_note'])
            self.assertIn('全員登録', self.rows[ident]['fee_note'])
            self.assertIn('7日前', self.rows[ident]['cancellation']['summary'])

    def test_ids_booking_urls_and_all_other_data_preserved(self):
        for name in ['tokyo_tennis.json', 'tokyo_sports.json', 'tokyo_expansion.json', 'fee_plans.json', 'cancellation_policies.json']:
            rel = 'outputs/venues/catalogs/' + name
            old = json.loads(subprocess.check_output(['git', 'show', review.BASE + ':' + rel], cwd=ROOT))
            new = json.loads((ROOT / rel).read_bytes())
            if name.startswith('tokyo_'):
                self.assertEqual(old, before_november6_closure(new, old))
                self.assertEqual([r['booking_url'] for r in old], [r['booking_url'] for r in new])
            else:
                self.assertEqual(old, new[:len(old)])
                additions = review.reviewed_fees() if name == 'fee_plans.json' else review.reviewed_policies()
                self.assertEqual(new[len(old):len(old) + len(additions)], additions)
                self.assertTrue(all(r['checked_at'] > review.CHECKED for r in new[len(old) + len(additions):]))

    def test_closure_whitelist_does_not_mask_other_changes(self):
        rel = 'outputs/venues/catalogs/tokyo_tennis.json'
        old = json.loads(subprocess.check_output(['git', 'show', review.BASE + ':' + rel], cwd=ROOT))
        new = json.loads((ROOT / rel).read_bytes())
        row, = [r for r in new if r['id'] == review.CLOSED]
        row['sources'].append({'title': 'unexpected', 'url': 'https://example.com/'})
        with self.assertRaises(AssertionError):
            before_november6_closure(new, old)

    def test_idempotence_and_conflicts_fail_before_writes(self):
        paths = [review.CATALOGS / p for p in ['fee_plans.json', 'cancellation_policies.json', 'tokyo_tennis.json']]
        before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
        subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/record_venue_fee_review_20261106.py')], check=True, capture_output=True)
        self.assertEqual(before, [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths])
        fake = dict(self.rows['hino-nanao'], fee_checked_at='2000-01-01')
        rows = [fake if r['id'] == fake['id'] else r for r in self.rows.values()]
        with patch.object(review, 'get_catalog', return_value={'courts': rows}), patch.object(review, 'update_closure') as closure, patch.object(review, 'append_reviews') as append:
            with self.assertRaises(ValueError):
                review.main()
            closure.assert_not_called()
            append.assert_not_called()


class November6VenuePublicTests(IsolatedAppHttpCase):
    def test_paged_api_serves_residency_ranges_and_hides_closed_court(self):
        status, body, headers = self.request('/api/venues?' + urlencode({'view': 'page', 'q': '清瀬内山', 'limit': 5}))
        self.assertEqual(status, 200)
        row, = [r for r in json.loads(body)['courts'] if r['id'] == 'kiyose-uchiyama']
        self.assertEqual(row['fee_checked_at'], review.CHECKED)
        self.assertIsNone(row['price_per_hour'])
        self.assertEqual([r['minimum'] for r in row['fee_ranges']], [600, 900])
        self.assertIn('ETag', headers)
        status, body, _ = self.request('/api/venues?' + urlencode({'view': 'page', 'q': '大沢野川'}))
        self.assertEqual(status, 200)
        self.assertNotIn(review.CLOSED, [r['id'] for r in json.loads(body)['courts']])


if __name__ == '__main__':
    unittest.main()
