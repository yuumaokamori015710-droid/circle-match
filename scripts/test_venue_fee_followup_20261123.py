"""Keep cancellation penalties, refunds, weather exceptions and hire scopes distinct."""
import json
import subprocess
import sys
import unittest
from urllib.parse import urlencode

import record_venue_fee_review_20261123 as review
from test_venues import IsolatedAppHttpCase


class November23VenueReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {r['id']: r for r in review.get_catalog()['courts']}
        cls.policies = {r['id']: r['summary'] for r in review.reviewed_policies()}

    def test_counts_new_tariff_and_unpriced_holds(self):
        self.assertEqual(len(set(review.REVIEWED_IDS)), 26)
        self.assertEqual(len(review.reviewed_fees()), 1)
        self.assertEqual(len(self.policies), 22)
        self.assertEqual(len(self.rows), 1206)
        later = [r for r in self.rows.values() if r.get('fee_checked_at', '') > review.CHECKED]
        unpriced = [r for r in self.rows.values() if not review.has_price(r)]
        self.assertEqual(len(unpriced) + len(later), 83)
        self.assertEqual(sum(r['availability_status'] != 'SUSPENDED' for r in unpriced + later), 72)
        for ident in review.HOLDS:
            self.assertFalse(review.has_price(self.rows[ident]))
            self.assertIsNone(self.rows[ident]['price_per_hour'])
        self.assertNotIn('tokyo-sports-025', self.policies)

    def test_asahi_tariff_is_softball_daytime_not_basketball_or_night(self):
        row = self.rows['tokyo-venue-1c5373a218d7']
        self.assertEqual(row['fee_options'], review.reviewed_fees()[0]['fee_options'])
        self.assertEqual(row['fee_checked_at'], review.CHECKED)
        self.assertEqual([(r['unit'], r['minimum'], r['maximum']) for r in row['fee_ranges']],
            [('ソフトボール場1面2時間（昼間）', 610, 610)])
        self.assertIsNone(row['price_per_hour'])
        for phrase in ['バスケットコート貸切料金ではありません', '夜間', '未確認', '利用登録']:
            self.assertIn(phrase, row['fee_note'])

    def test_municipal_application_restrictions_are_not_automatic_fines(self):
        for ident in review.SUGINAMI_IDS:
            for phrase in ['7日前', '30日間', '90日間', '任意', '自動徴収', '譲渡は禁止']:
                self.assertIn(phrase, self.policies[ident])
        for ident in review.NERIMA_IDS:
            for phrase in ['2026年7月以降', '30日間', '90日間', '月1枠', '窓口', '雨天だけ']:
                self.assertIn(phrase, self.policies[ident])

    def test_paid_unpaid_and_calendar_refund_boundaries(self):
        for ident in review.KITA_IDS:
            for phrase in ['14日前', '13～7日前', '6日前', '未払い', '全額納付後', '登録メンバー', '電話不可']:
                self.assertIn(phrase, self.policies[ident])
        for phrase in ['1か月前', '10日前', '9日前', '30日前換算', '50円単位', '予約誤り']:
            self.assertIn(phrase, self.policies['tokyo-sports-028'])
        self.assertIn('使用承認後の取消は原則不可', self.policies['tokyo-sports-027'])

    def test_operator_fee_deadlines_and_weather_not_generalized(self):
        for phrase in ['8日前', '3日前', '24時間前', '1時間30分前', '施設が判断']:
            self.assertIn(phrase, self.policies['tokyo-sports-020'])
        for phrase in ['11日前', '10～3日前', '2日前', '1時間前', '自己判断']:
            self.assertIn(phrase, self.policies['tokyo-sports-021'])
        for phrase in ['1週間前', '2週間前', '学割', '通常料金', '振替', '返金保証ではありません', 'ソサイチ']:
            self.assertIn(phrase, self.policies['tokyo-sports-022'])
        for phrase in ['10日前', '9～3日前', '2日前', '9時59分', '10日以内', '未確認']:
            self.assertIn(phrase, self.policies['tokyo-sports-023'])

    def test_edogawa_rain_exclusions_and_partial_method_only_evidence(self):
        self.assertIn('後日免除', self.policies['tokyo-sports-039'])
        for ident in ['tokyo-sports-040', 'tokyo-sports-041']:
            for phrase in ['免除から除外', '当日取消', '原則還付なし', '営利目的利用は禁止']:
                self.assertIn(phrase, self.policies[ident])
        partial = self.policies['tokyo-venue-b350e0713b8e']
        for phrase in ['3日前', '2日前', '2022年', '電話', '未確認', '無料とは扱いません']:
            self.assertIn(phrase, partial)

    def test_prior_data_contact_privacy_identities_and_idempotence(self):
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
        subprocess.run([sys.executable, '-B', str(review.ROOT / 'scripts/record_venue_fee_review_20261123.py')],
                       check=True, capture_output=True)
        self.assertEqual(before, [(review.CATALOGS / name).read_bytes() for name in names])


class November23VenuePublicTests(IsolatedAppHttpCase):
    def test_tariff_and_cancellation_disclosures_render_without_login(self):
        for name, phrases in [
            ('あさひ公園', ('610円', 'ソフトボール場1面2時間', 'バスケットコート貸切料金ではありません')),
            ('荻窪体育館', ('30日間', '90日間', '自動徴収')),
            ('フットサルコート品川', ('学割', '返金保証ではありません', 'ソサイチ')),
            ('臨海球技場', ('免除から除外', '原則還付なし')),
        ]:
            with self.subTest(venue=name):
                status, body, _ = self.request('/venues?' + urlencode({'v_q': name}))
                self.assertEqual(status, 200)
                for phrase in phrases:
                    self.assertIn(phrase, body.decode())


if __name__ == '__main__':
    unittest.main()
