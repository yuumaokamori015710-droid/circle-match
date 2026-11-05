"""Same-unit official tariffs, eligibility, weather and append-only checks."""
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
import record_venue_fee_review_20261105 as review
from test_venues import IsolatedAppHttpCase
from urllib.parse import urlencode


class November5VenueReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {r['id']: r for r in get_catalog()['courts']}

    def ranges(self, ident):
        return {r['unit']: (r['minimum'], r['maximum']) for r in self.rows[ident]['fee_ranges']}

    def test_reviewed_inventory_and_exact_saved_data(self):
        self.assertEqual(len(set(review.REVIEWED_IDS)), 21)
        self.assertEqual(len(review.reviewed_fees()), 16)
        self.assertEqual(len(review.reviewed_policies()), 16)
        self.assertEqual(len(self.rows), 1206)
        self.assertEqual(sum(has_price(r) for r in self.rows.values()), 922)
        self.assertEqual(sum(not has_price(r) for r in self.rows.values()), 284)
        self.assertEqual(sum(not has_price(r) and r['availability_status'] != 'SUSPENDED' for r in self.rows.values()), 273)
        for fee in review.reviewed_fees():
            row = self.rows[fee['id']]
            self.assertEqual(row['fee_checked_at'], review.CHECKED)
            self.assertEqual(row['fee_options'], fee['fee_options'])
            self.assertEqual(row['fee_note'], fee['fee_note'])
            self.assertTrue(all(p['amount'] >= 0 if fee['id'] == review.MINAMITAMA else p['amount'] > 0 for p in row['fee_options']))
        for policy in review.reviewed_policies():
            self.assertEqual(self.rows[policy['id']]['cancellation'], policy)

    def test_suginami_exact_room_duration_and_not_all_room_extrema(self):
        for ident, source, room, morning, other in review.SUGINAMI:
            expected = {room + '・3時間（通常）': (morning, morning), room + '・2時間（通常）': (other, other)}
            if ident == 'tokyo-venue-ea84b99ae578':
                expected.update({'体育室全面・1時間（通常）': (800, 800), '体育室半面・1時間（通常）': (400, 400)})
            elif ident == 'tokyo-venue-1f805e4e165d':
                expected['体育室・1時間（通常）'] = (500, 500)
            self.assertEqual(self.ranges(ident), expected)
            self.assertTrue(all(p['source_url'] == source for p in self.rows[ident]['fee_options']))
            for phrase in ['単室', '全室の最安値ではありません', '事前利用者登録', '転貸・権利譲渡不可', '商用利用の承認を意味しません']:
                self.assertIn(phrase, self.rows[ident]['fee_note'])
            summary = self.rows[ident]['cancellation']['summary']
            for phrase in ['7日前', '6日前以降', '現金支払後', 'カード支払後', '一律全額還付とはしません', '通常雨天免除は未確認']:
                self.assertIn(phrase, summary)

    def test_machida_base_court_not_lighting_or_nonresident_exception(self):
        for ident, slug, lit in review.MACHIDA:
            self.assertEqual(self.ranges(ident), {'テニスコート1面・2時間（登録個人・通常・照明別）': (1040, 1040)})
            self.assertEqual(self.rows[ident]['fee_options'][0]['source_url'], review.MACHIDA_BASE + slug)
            for phrase in ['15歳以上', '中学生除く', '市内在住・在勤・在学', '鶴間公園', '換算しません']:
                self.assertIn(phrase, self.rows[ident]['fee_note'])
            self.assertEqual('30分410円' in self.rows[ident]['fee_note'], lit)
        self.assertFalse(has_price(self.rows[review.TSURUMA]))
        self.assertIn('開始30分前', self.rows[review.TSURUMA]['cancellation']['summary'])

    def test_machida_cancel_penalty_is_not_money_and_weather_is_facility_decision(self):
        for ident in [r[0] for r in review.MACHIDA] + [review.TSURUMA]:
            text = self.rows[ident]['cancellation']['summary']
            for phrase in ['前日まで', '3週間前', '1点', '2点', '60分以内', '1点の制限は団体のみ', '翌々月',
                           '還付額は共通案内では未確認', '施設判断', 'ペナルティなし', '自己判断']:
                self.assertIn(phrase, text)

    def test_inagi_ordinary_court_fee_and_weather_refund_deadline(self):
        for ident, slug, lit in review.INAGI:
            self.assertEqual(self.ranges(ident), {'テニスコート1面・2時間（通常・照明別）': (1580, 1580)})
            self.assertEqual(self.rows[ident]['fee_options'][0]['source_url'], review.INAGI_BASE + slug)
            self.assertEqual('1時間780円' in self.rows[ident]['fee_note'], lit)
            for phrase in ['開始1時間前', '翌日23時59分', '電話不可', '未報告は還付不可', '自己都合', '手数料・還付率は未確認']:
                self.assertIn(phrase, self.rows[ident]['cancellation']['summary'])
            self.assertEqual(self.rows[ident]['cancellation']['source_url'], review.INAGI_WEATHER)
        self.assertIn('市外料金は2倍', self.rows['inagi-kitamidori']['fee_note'])

    def test_only_officially_free_hire_is_zero_and_registration_is_required(self):
        row = self.rows[review.MINAMITAMA]
        self.assertEqual(self.ranges(row['id']), {'テニスコート1面・2時間（登録個人・団体・無料）': (0, 0)})
        for phrase in ['無料利用', '未登録者は利用不可', '年2回', 'コート整備参加']:
            self.assertIn(phrase, row['fee_note'])
        self.assertIsNone(row['cancellation'])
        for ident in review.HOLDS:
            self.assertFalse(has_price(self.rows[ident]))
            self.assertEqual(self.rows[ident]['fee_ranges'], [])

    def test_catalog_bytes_and_prior_sidecar_entries_are_unchanged(self):
        for name in ['tokyo_tennis.json', 'tokyo_sports.json', 'tokyo_expansion.json', 'fee_plans.json', 'cancellation_policies.json']:
            rel = 'outputs/venues/catalogs/' + name
            before = subprocess.check_output(['git', 'show', review.BASE + ':' + rel], cwd=ROOT)
            current = (ROOT / rel).read_bytes()
            if name.startswith('tokyo_'):
                self.assertEqual(before.replace(b'\r\n', b'\n'), current.replace(b'\r\n', b'\n'))
            else:
                old, new = json.loads(before), json.loads(current)
                self.assertEqual(old, new[:len(old)])
                self.assertEqual(new[len(old):], review.reviewed_fees() if name == 'fee_plans.json' else review.reviewed_policies())

    def test_idempotence_and_conflicting_prior_price_preflight(self):
        paths = [review.CATALOGS / p for p in ['fee_plans.json', 'cancellation_policies.json']]
        before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
        subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/record_venue_fee_review_20261105.py')], check=True, capture_output=True)
        self.assertEqual(before, [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths])
        fake = dict(self.rows['machida-chuo'], fee_checked_at='2000-01-01')
        rows = [fake if r['id'] == fake['id'] else r for r in self.rows.values()]
        with patch.object(review, 'get_catalog', return_value={'courts': rows}), patch.object(review, 'append_reviews') as append:
            with self.assertRaises(ValueError):
                review.main()
            append.assert_not_called()


class November5VenuePublicTests(IsolatedAppHttpCase):
    def test_public_api_serves_new_prices_and_keeps_legacy_unit_unknown(self):
        status, body, _ = self.request('/api/venues?' + urlencode({'sport': 'テニス'}))
        self.assertEqual(status, 200)
        row, = [r for r in json.loads(body)['courts'] if r['id'] == 'inagi-kitamidori']
        self.assertEqual(row['id'], 'inagi-kitamidori')
        self.assertEqual(row['fee_ranges'][0]['minimum'], 1580)
        self.assertEqual(row['fee_checked_at'], review.CHECKED)
        self.assertIsNone(row['price_per_hour'])
        self.assertIn('翌日23時59分', row['cancellation']['summary'])

    def test_public_html_renders_hourly_gym_and_free_eligibility(self):
        for query, phrases in [('下高井戸区民集会所', ['800円', '400円', '体育室全面・1時間', '体育室半面・1時間']),
                               ('南多摩スポーツ広場', ['0円', '未登録者は利用不可', '年2回'])]:
            status, body, _ = self.request('/venues?' + urlencode({'v_q': query}))
            self.assertEqual(status, 200)
            html = body.decode('utf-8')
            for phrase in phrases:
                self.assertIn(phrase, html)


if __name__ == '__main__':
    unittest.main()
