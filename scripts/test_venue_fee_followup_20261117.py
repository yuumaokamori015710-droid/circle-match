"""Verify November 17 fee scopes, registration limits and append-only updates."""
import json
import subprocess
import sys
import unittest
from urllib.parse import urlencode

import record_venue_fee_review_20261117 as review
from test_venues import IsolatedAppHttpCase


class November17VenueReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {r['id']: r for r in review.get_catalog()['courts']}

    def ranges(self, ident):
        return {r['unit']: (r['minimum'], r['maximum']) for r in self.rows[ident]['fee_ranges']}

    def test_saved_review_and_unchanged_inventory(self):
        self.assertEqual(len(set(review.REVIEWED_IDS)), 26)
        self.assertEqual(len(review.reviewed_fees()), 24)
        self.assertEqual(len(review.reviewed_policies()), 2)
        self.assertEqual(len(self.rows), 1206)
        later = [r for r in self.rows.values() if r.get('fee_checked_at', '') > review.CHECKED]
        unpriced = [r for r in self.rows.values() if not review.has_price(r)]
        self.assertEqual(len(unpriced) + len(later), 112)
        self.assertEqual(sum(r['availability_status'] != 'SUSPENDED' for r in unpriced + later), 101)
        for fee in review.reviewed_fees():
            row = self.rows[fee['id']]
            self.assertEqual(row['fee_checked_at'], review.CHECKED)
            self.assertEqual(row['fee_options'], fee['fee_options'])
            self.assertEqual(row['fee_note'], fee['fee_note'])
        for policy in review.reviewed_policies():
            self.assertEqual(self.rows[policy['id']]['cancellation'], policy)
        for ident in review.HOLDS:
            self.assertFalse(review.has_price(self.rows[ident]))

    def test_rooms_durations_and_residency_not_combined(self):
        units = self.ranges('tokyo-venue-d524a6778a50')
        self.assertEqual(units['音楽室1室・2時間30分（通常）'], (750, 750))
        self.assertEqual(units['体育館・3時間（通常）'], (1750, 1750))
        self.assertEqual(units['多目的広場・1時間（通常）'], (160, 160))
        self.assertEqual(units['多目的広場・2時間（通常）'], (330, 330))
        self.assertEqual(units['多目的広場・3時間（通常）'], (500, 500))
        note = self.rows['tokyo-venue-d524a6778a50']['fee_note']
        for phrase in ('第5会議室・学習室', '2028年7月', '夜間貸出はなし', '成人サッカー', '登録スポーツ団体'):
            self.assertIn(phrase, note)
        self.assertEqual(self.ranges('tokyo-venue-fd87d6430730')['ホール・3時間30分（通常）'], (6400, 6400))
        self.assertEqual(self.ranges('tokyo-venue-fd87d6430730')['ホール・4時間（通常）'], (7300, 7300))
        self.assertEqual(self.ranges('tokyo-venue-41e834c7fc62')['多目的ホール・2時間30分（通常）'], (4900, 4900))
        self.assertEqual(self.ranges('tokyo-venue-41e834c7fc62')['多目的ホール・全日13時間（通常）'], (22600, 22600))
        sunny = self.ranges('tokyo-venue-81ea80a5de3d')
        self.assertEqual(sunny['第2会議室・2時間（区内通常）'], (700, 700))
        self.assertEqual(sunny['第2会議室・2時間（区外通常）'], (750, 750))
        self.assertEqual(sunny['第2会議室・3時間（区内通常）'], (1100, 1100))
        self.assertTrue(all('会議室' in unit for unit in sunny))
        self.assertIn('5,001円', self.rows['tokyo-venue-81ea80a5de3d']['fee_note'])
        policy = self.rows['tokyo-venue-fd87d6430730']['cancellation']['summary']
        for phrase in ('15日前', '5日前', '返還割合', '無料取消とは扱いません', '1回限り'):
            self.assertIn(phrase, policy)

    def test_school_free_scope_and_unknown_cancellation(self):
        self.assertEqual(len(review.SCHOOLS), 20)
        self.assertEqual(len(review.HARD_ONLY), 9)
        for suffix in review.SCHOOLS:
            row = self.rows['school-' + suffix]
            self.assertEqual(self.ranges(row['id']), {review.SCHOOL_UNIT: (0, 0)})
            self.assertIsNone(row['price_per_hour'])
            self.assertIsNone(row['cancellation'])
            for phrase in ('光熱費・保険料は含みません', '不特定多数の活動は不可', '名簿掲載者', '令和6年度'):
                self.assertIn(phrase, row['fee_note'])
            self.assertIn('硬式のみ' if suffix in review.HARD_ONLY else '硬式・軟式', row['fee_note'])

    def test_original_catalogs_prior_reviews_and_contact_seed_preserved(self):
        names = ['tokyo_tennis.json', 'tokyo_sports.json', 'tokyo_expansion.json',
                 'fee_plans.json', 'cancellation_policies.json']
        before = [(review.CATALOGS / name).read_bytes() for name in names]
        for name, raw in zip(names, before):
            base = subprocess.check_output(['git', 'show', review.BASE + ':outputs/venues/catalogs/' + name], cwd=review.ROOT)
            if name.startswith('tokyo_'):
                self.assertEqual(raw.replace(b'\r\n', b'\n'), base.replace(b'\r\n', b'\n'))
            else:
                old, new = json.loads(base), json.loads(raw)
                additions = review.reviewed_fees() if name == 'fee_plans.json' else review.reviewed_policies()
                self.assertEqual(new[:len(old) + len(additions)], old + additions)
                self.assertTrue(all(r['checked_at'] > review.CHECKED for r in new[len(old) + len(additions):]))
        contact_path = 'outputs/circle_public_contacts.json'
        self.assertEqual(json.loads((review.ROOT / contact_path).read_bytes()), json.loads(subprocess.check_output(
            ['git', 'show', review.BASE + ':' + contact_path], cwd=review.ROOT)))
        subprocess.run([sys.executable, '-B', str(review.ROOT / 'scripts/record_venue_fee_review_20261117.py')],
                       check=True, capture_output=True)
        self.assertEqual(before, [(review.CATALOGS / name).read_bytes() for name in names])


class November17VenuePublicTests(IsolatedAppHttpCase):
    def test_scoped_fees_conditions_and_existing_booking_links_render(self):
        for name, phrases in [
            ('生涯学習センター', ('1,750円', '160円', '2時間30分', '第5会議室・学習室', '熱中症特別警戒')),
            ('アクト21', ('6,400円', '20,100円', '15日前', '返還割合', '営利活動')),
            ('町屋文化センター', ('4,900円', '22,600円', '2時間30分', 'Web予約不可')),
            ('日暮里サニーホール', ('700円', '750円', '区外通常', '5,001円', '会議室')),
            ('東久留米総合高等学校', ('無料', review.SCHOOL_UNIT, '硬式のみ', '名簿掲載者')),
        ]:
            with self.subTest(venue=name):
                status, body, _ = self.request('/venues?' + urlencode({'v_q': name}))
                self.assertEqual(status, 200)
                for phrase in phrases:
                    self.assertIn(phrase, body.decode())
