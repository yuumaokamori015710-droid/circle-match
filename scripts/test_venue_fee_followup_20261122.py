"""Guard distinct duration, discount, future-period and cancellation scopes."""
import json
import subprocess
import sys
import unittest
from urllib.parse import urlencode

import record_venue_fee_review_20261122 as review
from test_venues import IsolatedAppHttpCase


class November22VenueReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {r['id']: r for r in review.get_catalog()['courts']}

    def ranges(self, ident):
        return {r['unit']: (r['minimum'], r['maximum']) for r in self.rows[ident]['fee_ranges']}

    def test_counts_added_fees_and_remaining_holds(self):
        self.assertEqual(len(set(review.REVIEWED_IDS)), 26)
        self.assertEqual(len(review.reviewed_fees()), 5)
        self.assertEqual(len(review.reviewed_policies()), 13)
        self.assertEqual(len(self.rows), 1206)
        later = [r for r in self.rows.values() if r.get('fee_checked_at', '') > review.CHECKED]
        unpriced = [r for r in self.rows.values() if not review.has_price(r)]
        self.assertEqual(len(unpriced) + len(later), 84)
        self.assertEqual(sum(r['availability_status'] != 'SUSPENDED' for r in unpriced + later), 73)
        for fee in review.reviewed_fees():
            self.assertEqual(self.rows[fee['id']]['fee_options'], fee['fee_options'])
            self.assertEqual(self.rows[fee['id']]['fee_checked_at'], review.CHECKED)
        for ident in review.HOLDS:
            self.assertFalse(review.has_price(self.rows[ident]))
            self.assertIsNone(self.rows[ident]['price_per_hour'])

    def test_hall_rooms_durations_and_arts_discount_are_not_combined(self):
        main = self.ranges('tokyo-venue-e8c8e3801fe4')
        self.assertEqual(main['大ホール・4時間（一般団体・平日）'], (160000, 191200))
        self.assertEqual(main['大ホール・4時間（登録芸術文化活動団体・平日）'], (80000, 95600))
        self.assertEqual(main['大ホール・全日13時間（一般団体・土日休）'], (533400, 533400))
        self.assertEqual(main['会議室・3時間（一般団体・共通）'], (1000, 1000))
        gt = self.ranges('tokyo-venue-0094fb226d0e')
        self.assertEqual(gt['ホール・4時間（一般団体・平日）'], (17300, 20600))
        self.assertEqual(gt['ホール・3時間（登録芸術文化活動団体・平日）'], (5000, 5000))
        self.assertIn('150％', self.rows['tokyo-venue-0094fb226d0e']['fee_note'])

    def test_golf_is_per_person_round_and_meal_scopes_stay_distinct(self):
        ranges = self.ranges('tokyo-wakasu-golf-links')
        self.assertEqual(ranges['1名1ラウンド（税込・4名1組・キャディ付き・食事別）'], (15540, 24540))
        self.assertEqual(ranges['1名1ラウンド（税込・4名1組・通常セルフ・食事別）'], (12450, 21450))
        self.assertEqual(ranges['1名1ラウンド（税込・4名1組・セルフデー・食事込）'], (13600, 22600))
        self.assertIsNone(self.rows['tokyo-wakasu-golf-links']['price_per_hour'])
        for phrase in ['600円', '50円', '3バッグ', '都内在住・在勤', '9ホール']:
            self.assertIn(phrase, self.rows['tokyo-wakasu-golf-links']['fee_note'])

    def test_december_period_not_generalized_and_court_headcount_separate(self):
        musashino = self.rows['private-musashino-tennis-city']
        self.assertEqual(self.ranges(musashino['id']), {
            '1面30分（税込・2026年12月期限定）': (2000, 2000),
            '1面60分（税込・2026年12月期限定）': (4000, 4000)})
        self.assertIn('通常通年料金', musashino['fee_note'])
        self.assertIn('記載差', musashino['fee_note'])
        nishi = self.rows['private-nishikoku']
        self.assertEqual(self.ranges(nishi['id'])['1面1時間（税込・12名まで）'], (1100, 3850))
        for phrase in ['ソフトテニス不可', '7日前', '営利活動', '備品貸出は別料金']:
            self.assertIn(phrase, nishi['fee_note'])

    def test_cancellation_deadlines_weather_and_conflicts_not_simplified(self):
        policies = {p['id']: p['summary'] for p in review.reviewed_policies()}
        for ident in review.GYMS:
            for phrase in ['30日間', '90日間', '制限解除', '譲渡は禁止']:
                self.assertIn(phrase, policies[ident])
        for phrase in ['2時間前', '1時間前', '実際に利用した時点', '屋内', '事前申請']:
            self.assertIn(phrase, policies['tokyo-sports-019'])
        self.assertIn('7日前の扱いが一致しない', policies['private-nishikoku'])
        self.assertIn('7月9日', policies['tokyo-venue-0094fb226d0e'])
        self.assertIn('6月14日', policies['tokyo-venue-e8c8e3801fe4'])
        self.assertIn('現地で雨', policies['private-tanashi-yunan'])
        self.assertIn('前半9ホール以内', policies['tokyo-wakasu-golf-links'])
        self.assertNotIn('private-chitose', policies)
        self.assertNotIn('private-ivy-hachioji', policies)

    def test_original_catalogs_prior_reviews_contact_seed_and_idempotence(self):
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
        path = 'outputs/circle_public_contacts.json'
        prior = json.loads(subprocess.check_output(['git', 'show', review.BASE + ':' + path], cwd=review.ROOT))
        self.assertEqual(json.loads((review.ROOT / path).read_bytes())[:len(prior)], prior)
        subprocess.run([sys.executable, '-B', str(review.ROOT / 'scripts/record_venue_fee_review_20261122.py')],
                       check=True, capture_output=True)
        self.assertEqual(before, [(review.CATALOGS / name).read_bytes() for name in names])


class November22VenuePublicTests(IsolatedAppHttpCase):
    def test_scoped_tariffs_and_policy_disclosures_render(self):
        for name, phrases in [
            ('中目黒GTプラザホール', ('10,100円', '57,500円', '登録芸術文化活動団体', '7月9日')),
            ('若洲ゴルフリンクス', ('12,450円', '24,540円', '1名1ラウンド', '食事込')),
            ('スポーツクリエイト にしこくテニススクール', ('1,100円', '3,850円', '12名まで', '一致しない')),
            ('武蔵野テニスシティー', ('12月期限定', '30分', '60分', '記載差')),
        ]:
            with self.subTest(venue=name):
                status, body, _ = self.request('/venues?' + urlencode({'v_q': name}))
                self.assertEqual(status, 200)
                for phrase in phrases:
                    self.assertIn(phrase, body.decode())
