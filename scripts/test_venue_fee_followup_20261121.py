"""Verify November 21 room/time/eligibility scopes and append-only provenance."""
import json
import subprocess
import sys
import unittest
from urllib.parse import urlencode

import record_venue_fee_review_20261121 as review
from test_venues import IsolatedAppHttpCase


class November21VenueReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {r['id']: r for r in review.get_catalog()['courts']}

    def ranges(self, ident):
        return {r['unit']: (r['minimum'], r['maximum']) for r in self.rows[ident]['fee_ranges']}

    def test_saved_reviews_counts_and_unknowns(self):
        self.assertEqual(len(set(review.REVIEWED_IDS)), 26)
        self.assertEqual(len(review.reviewed_fees()), 23)
        self.assertEqual(len(review.reviewed_policies()), 7)
        self.assertEqual(len(self.rows), 1206)
        later = [r for r in self.rows.values() if r.get('fee_checked_at', '') > review.CHECKED]
        unpriced = [r for r in self.rows.values() if not review.has_price(r)]
        self.assertEqual(len(unpriced) + len(later), 89)
        self.assertEqual(sum(r['availability_status'] != 'SUSPENDED' for r in unpriced + later), 78)
        for fee in review.reviewed_fees():
            self.assertEqual(self.rows[fee['id']]['fee_options'], fee['fee_options'])
            self.assertEqual(self.rows[fee['id']]['fee_checked_at'], review.CHECKED)
        for ident in review.HOLDS:
            self.assertFalse(review.has_price(self.rows[ident]))
            self.assertIsNone(self.rows[ident]['price_per_hour'])
        for policy in review.reviewed_policies():
            self.assertEqual(self.rows[policy['id']]['cancellation'], policy)

    def test_room_duration_resident_and_day_types_stay_separate(self):
        units = self.ranges('tokyo-sports-033')
        self.assertEqual(units['会議室1室・3時間（市内一般団体）'], (600, 600))
        self.assertEqual(units['会議室1室・3時間（市外一般団体）'], (1200, 1200))
        self.assertEqual(units['会議室1室・3時間30分（市内一般団体）'], (1200, 1400))
        self.assertEqual(units['会議室1室・全日12時間（市外一般団体）'], (5800, 5800))
        sakura = self.ranges('tokyo-venue-370b51dc9413')
        self.assertEqual(sakura['集会室兼体育室・2時間（通常）'], (2980, 2980))
        self.assertEqual(sakura['集会室兼体育室・4時間（通常）'], (5960, 5960))
        ota = self.ranges('tokyo-venue-2c73f8af103d')
        self.assertEqual(ota['第二多目的室・2時間30分（通常）'], (2000, 2000))
        self.assertEqual(ota['第二多目的室・3時間（通常）'], (2400, 2400))
        self.assertTrue(all(o['source_url'] == review.OTA for o in self.rows['tokyo-venue-2c73f8af103d']['fee_options']))
        sun = self.ranges('tokyo-venue-68173b2f2e9f')
        self.assertEqual(sun['大ホール・3時間30分（月～金）'], (45500, 84500))
        self.assertEqual(sun['大ホール・全日13時間（土日祝）'], (260000, 260000))
        self.assertEqual(self.ranges('tokyo-venue-ca8003362ef9')['多目的ホール2・4時間（通常）'], (2200, 2200))
        sat = self.ranges('tokyo-venue-6bae42680d24')
        self.assertEqual(sat['体育室・3時間（区民団体）'], (900, 900))
        self.assertEqual(sat['体育室・3時間（一般団体）'], (1800, 1800))
        self.assertIn('固いボールは使用不可', self.rows['tokyo-venue-6bae42680d24']['fee_note'])
        for ident in review.ADACHI_ROOMS:
            ranges = self.ranges(ident)
            self.assertIn('レクリエーションホール・2時間30分（通常）', ranges)
            self.assertTrue(all('レクリエーションホール・4時間' not in u for u in ranges))

    def test_cancellation_is_refund_not_automatic_free_cancellation(self):
        policies = {p['id']: p['summary'] for p in review.reviewed_policies()}
        for ident in review.ADACHI_ROOMS:
            for phrase in ['2日前', '翌日から3日以内', '50％', '前日・当日', '年末年始']:
                self.assertIn(phrase, policies[ident])
        for phrase in ['10日前', '5日前', '75％', '100円未満切捨て', '暴風', '通常の雨']:
            self.assertIn(phrase, policies['tokyo-venue-e08430091e38'])
        self.assertIn('1か月前まで75％', policies['tokyo-venue-375db5fa8c9a'])
        self.assertIn('メール・郵送不可', policies['tokyo-venue-375db5fa8c9a'])
        self.assertIn('割合は当該ページに明記がなく', policies['tokyo-venue-6bae42680d24'])
        self.assertIsNone(self.rows['tokyo-venue-2c73f8af103d']['cancellation'])

    def test_all_twelve_schools_have_only_explicit_eligible_daytime_zero(self):
        self.assertEqual(len(review.SCHOOLS), 12)
        self.assertEqual(len(review.HARD_ONLY), 3)
        for suffix in review.SCHOOLS:
            row = self.rows['school-' + suffix]
            self.assertEqual(self.ranges(row['id']), {review.SCHOOL_UNIT: (0, 0)})
            self.assertIsNone(row['price_per_hour'])
            self.assertIsNone(row['cancellation'])
            for phrase in ['光熱費・保険料は含みません', '不特定多数の活動は不可', '名簿掲載者', '令和6年度']:
                self.assertIn(phrase, row['fee_note'])
            self.assertIn('硬式のみ' if suffix in review.HARD_ONLY else '硬式・軟式', row['fee_note'])

    def test_original_catalogs_all_previous_reviews_contacts_and_idempotence(self):
        names = ['tokyo_tennis.json', 'tokyo_sports.json', 'tokyo_expansion.json',
                 'fee_plans.json', 'cancellation_policies.json']
        before = [(review.CATALOGS / name).read_bytes() for name in names]
        for name, raw in zip(names, before):
            old = subprocess.check_output(['git', 'show', review.BASE + ':outputs/venues/catalogs/' + name], cwd=review.ROOT)
            if name.startswith('tokyo_'):
                self.assertEqual(raw.replace(b'\r\n', b'\n'), old.replace(b'\r\n', b'\n'))
            else:
                prior, current = json.loads(old), json.loads(raw)
                additions = review.reviewed_fees() if name == 'fee_plans.json' else review.reviewed_policies()
                self.assertEqual(current[:len(prior) + len(additions)], prior + additions)
                self.assertTrue(all(r['checked_at'] > review.CHECKED for r in current[len(prior) + len(additions):]))
        contact_path = 'outputs/circle_public_contacts.json'
        prior = json.loads(subprocess.check_output(['git', 'show', review.BASE + ':' + contact_path], cwd=review.ROOT))
        self.assertEqual(json.loads((review.ROOT / contact_path).read_bytes())[:len(prior)], prior)
        subprocess.run([sys.executable, '-B', str(review.ROOT / 'scripts/record_venue_fee_review_20261121.py')],
                       check=True, capture_output=True)
        self.assertEqual(before, [(review.CATALOGS / name).read_bytes() for name in names])


class November21VenuePublicTests(IsolatedAppHttpCase):
    def test_scoped_rates_provenance_policies_and_booking_links_render(self):
        for name, phrases in [
            ('蒲田西集会室', ('1,500円', '2,000円', '2時間30分', '2026年11月1日', '2割5分')),
            ('ふらっとにっぽり', ('3,400円', '10,700円', '10日前', '転貸', '運動等')),
            ('サンパール荒川', ('45,500円', '260,000円', '30％加算', '75％', '翌営業日')),
            ('竹の塚地域学習センター', ('1,100円', '19,700円', '2時間30分', '全額返金', '3日以内')),
            ('神津高等学校', ('無料', review.SCHOOL_UNIT, '硬式のみ', '名簿掲載者')),
        ]:
            with self.subTest(venue=name):
                status, body, _ = self.request('/venues?' + urlencode({'v_q': name}))
                self.assertEqual(status, 200)
                for phrase in phrases:
                    self.assertIn(phrase, body.decode())
