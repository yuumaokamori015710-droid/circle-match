"""Preservation, exact tariff units, eligibility and public rendering checks."""
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
from venues.sports_catalog import get_catalog, has_price
import record_venue_fee_review_20261107 as review
from test_venues import IsolatedAppHttpCase


class November7VenueReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {r['id']: r for r in get_catalog()['courts']}

    def ranges(self, ident):
        return {r['unit']: (r['minimum'], r['maximum']) for r in self.rows[ident]['fee_ranges']}

    def test_exact_inventory_sources_and_saved_data(self):
        self.assertEqual(len(set(review.REVIEWED_IDS)), 24)
        self.assertEqual(len(self.rows), 1206)
        self.assertEqual(sum(has_price(r) for r in self.rows.values()), 958)
        self.assertEqual(sum(not has_price(r) for r in self.rows.values()), 248)
        self.assertEqual(sum(not has_price(r) and r['availability_status'] != 'SUSPENDED' for r in self.rows.values()), 237)
        self.assertEqual(len(review.reviewed_fees()), 17)
        self.assertEqual(len(review.reviewed_policies()), 6)
        for fee in review.reviewed_fees():
            row = self.rows[fee['id']]
            self.assertEqual(row['fee_checked_at'], review.CHECKED)
            self.assertEqual(row['fee_options'], fee['fee_options'])
            self.assertEqual(row['fee_note'], fee['fee_note'])
            self.assertTrue(all(p['amount'] > 0 and p['source_url'].startswith('https://') for p in row['fee_options']))
        for policy in review.reviewed_policies():
            self.assertEqual(self.rows[policy['id']]['cancellation'], policy)
        for ident in review.HOLDS:
            self.assertFalse(has_price(self.rows[ident]))
            self.assertEqual(self.rows[ident]['fee_ranges'], [])

    def test_actual_hire_not_filming_individual_or_lighting(self):
        self.assertEqual(self.ranges('koto-shinsuna'), {'テニスコート1面・1時間（団体通常）': (1100, 1800)})
        self.assertIn('写真撮影', self.rows['koto-shinsuna']['fee_note'])
        for ident in ['shibuya-sportscenter', 'shibuya-nishihara']:
            self.assertEqual(list(self.ranges(ident).values()), [(1400, 1400)])
            self.assertIn('30分250円', self.rows[ident]['fee_note'])
        self.assertIn('C/D面', self.rows['shibuya-sportscenter']['fee_note'])
        self.assertIn('A/B面は利用可能', self.rows['shibuya-sportscenter']['fee_note'])
        self.assertIn('平日9～15時のみ', self.rows['shibuya-honmachi']['fee_note'])
        self.assertEqual(self.ranges('hamura-fujimi'), {
            'テニスコート1面・2時間（通常・照明別）': (600, 600),
            'テニスコート1面・3時間（夜間・照明別）': (900, 900)})

    def test_residency_age_and_seasonal_units_remain_separate(self):
        self.assertEqual(self.ranges('machida-tsuruma'), {
            'テニスコート1面・2時間（市内・照明別）': (1800, 2500),
            'テニスコート1面・2時間（市外・照明別）': (3700, 5000)})
        self.assertEqual(self.rows['machida-tsuruma']['cancellation']['checked_at'], '2026-11-05')
        self.assertEqual(self.ranges('musashino-tennis'), {
            '庭球場1面・2時間（市民通常）': (1000, 1000),
            '庭球場1面・2時間（市外通常）': (2000, 2000)})
        self.assertEqual(len(self.ranges('meguro-kumin')), 8)
        self.assertEqual(self.ranges('meguro-kumin')['庭球場1面・2時間（区外団体・大人）'], (4800, 4800))
        self.assertEqual(self.ranges('meguro-kumin')['庭球場1面・1時間（区外団体・大人・季節限定）'], (2400, 2400))
        self.assertEqual(len(self.ranges('komae-motoizumi')), 4)
        self.assertEqual(len(self.ranges('komae-higashinogawa')), 2)
        self.assertIn('高校生以下のみ', self.rows['komae-motoizumi']['fee_note'])
        self.assertIn('中学生以下のみの利用不可', self.rows['higashiyamato-kaminakahara']['fee_note'])

    def test_akiruno_night_fee_not_surcharge_and_winter_closure_scoped(self):
        self.assertEqual(self.ranges('akiruno-yamada')['テニスコート1面・2時間（市外夜間・照明使用）'], (4300, 4300))
        self.assertIn('追加照明料ではなく', self.rows['akiruno-yamada']['fee_note'])
        for ident in ['akiruno-sogo', 'akiruno-tamamikazaki']:
            self.assertIn('12月20日～3月20日', self.rows[ident]['fee_note'])
            self.assertNotEqual(self.rows[ident]['availability_status'], 'SUSPENDED')
        self.assertIn('営利目的利用不可', self.rows['chofu-midori']['fee_note'])
        self.assertIn('転貸不可', self.rows['higashiyamato-kaminakahara']['fee_note'])

    def test_cancel_penalties_and_weather_are_not_invented_refund_rates(self):
        for ident in ['komae-motoizumi', 'komae-higashinogawa']:
            text = self.rows[ident]['cancellation']['summary']
            for phrase in ['3日前', '6回', '30分未満', '1時間30分未満', '半額', '未確認']:
                self.assertIn(phrase, text)
        text = self.rows['meguro-kumin']['cancellation']['summary']
        for phrase in ['4日前', '3日前', '3か月', '屋内施設の還付率を庭球場へ適用せず']:
            self.assertIn(phrase, text)
        self.assertIn('次回利用分へ充当', self.rows['fuchu-koyanagi']['cancellation']['summary'])
        self.assertIn('開始60分以内', self.rows['musashino-tennis']['cancellation']['summary'])

    def test_original_catalogs_and_all_previous_entries_unchanged(self):
        for name in ['tokyo_tennis.json', 'tokyo_sports.json', 'tokyo_expansion.json', 'fee_plans.json', 'cancellation_policies.json']:
            rel = 'outputs/venues/catalogs/' + name
            old_bytes = subprocess.check_output(['git', 'show', review.BASE + ':' + rel], cwd=ROOT)
            new_bytes = (ROOT / rel).read_bytes()
            if name.startswith('tokyo_'):
                self.assertEqual(old_bytes.replace(b'\r\n', b'\n'), new_bytes.replace(b'\r\n', b'\n'))
            else:
                old, new = json.loads(old_bytes), json.loads(new_bytes)
                self.assertEqual(new[:len(old)], old)
                self.assertEqual(new[len(old):], review.reviewed_fees() if name == 'fee_plans.json' else review.reviewed_policies())

    def test_idempotent_and_conflicting_price_rejected_before_writing(self):
        paths = [review.CATALOGS / n for n in ['fee_plans.json', 'cancellation_policies.json']]
        before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
        subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/record_venue_fee_review_20261107.py')], check=True, capture_output=True)
        self.assertEqual(before, [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths])
        fake = dict(self.rows['koto-shinsuna'], fee_checked_at='2000-01-01')
        rows = [fake if r['id'] == fake['id'] else r for r in self.rows.values()]
        with patch.object(review, 'get_catalog', return_value={'courts': rows}), patch.object(review, 'append_reviews') as append:
            with self.assertRaises(ValueError):
                review.main()
            append.assert_not_called()


class November7VenuePublicTests(IsolatedAppHttpCase):
    def test_paged_api_and_server_rendered_prices(self):
        query = urlencode({'view': 'page', 'q': '鶴間公園', 'limit': 5})
        status, body, headers = self.request('/api/venues?' + query)
        self.assertEqual(status, 200)
        row, = [r for r in json.loads(body)['courts'] if r['id'] == 'machida-tsuruma']
        self.assertEqual(row['fee_checked_at'], review.CHECKED)
        self.assertEqual([(r['minimum'], r['maximum']) for r in row['fee_ranges']], [(1800, 2500), (3700, 5000)])
        self.assertIsNone(row['price_per_hour'])
        self.assertIn('ETag', headers)
        status, body, _ = self.request('/venues?' + urlencode({'v_q': '鶴間公園'}))
        self.assertEqual(status, 200)
        text = body.decode()
        for phrase in ['1,800円〜2,500円', '3,700円〜5,000円', review.MACHIDA]:
            self.assertIn(phrase, text)


if __name__ == '__main__':
    unittest.main()
