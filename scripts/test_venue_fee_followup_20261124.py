"""Guard person/room rates, dated peak tariffs and distinct cancellation regimes."""
import json
import subprocess
import sys
import unittest
from urllib.parse import urlencode

import record_venue_fee_review_20261124 as review
from test_venues import IsolatedAppHttpCase


class November24VenueReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {r['id']: r for r in review.get_catalog()['courts']}
        cls.policies = {p['id']: p['summary'] for p in review.reviewed_policies()}

    def test_counts_tariff_and_remaining_holds(self):
        self.assertEqual(len(set(review.REVIEWED_IDS)), 26)
        self.assertEqual(len(review.RECHECKS), 22)
        self.assertEqual(len(review.reviewed_fees()), 1)
        self.assertEqual(len(self.policies), 19)
        self.assertEqual(len(self.rows), 1206)
        later = [r for r in self.rows.values() if r.get('fee_checked_at', '') > review.CHECKED]
        unpriced = [r for r in self.rows.values() if not review.has_price(r)]
        self.assertEqual(len(unpriced) + len(later), 82)
        self.assertEqual(sum(r['availability_status'] != 'SUSPENDED' for r in unpriced + later), 71)
        for ident in review.HOLDS:
            self.assertFalse(review.has_price(self.rows[ident]))
            self.assertIsNone(self.rows[ident]['price_per_hour'])
        for item in review.reviewed_policies():
            self.assertEqual(self.rows[item['id']]['cancellation'], item)

    def test_pasela_day_night_peak_and_per_person_scopes(self):
        row = self.rows['tokyo-pasela-shinjuku']
        ranges = {r['unit']: (r['minimum'], r['maximum']) for r in row['fee_ranges']}
        self.assertEqual(ranges, {
            '大人1名30分（昼・1ドリンク込・通常期間）': (380, 580),
            '大人1名30分（夜・室料のみ・通常期間）': (580, 680),
            '大人1名30分（昼・1ドリンク込・2026/12/1～2027/1/3）': (580, 580),
            '大人1名30分（夜・室料のみ・2026/12/1～2027/1/3）': (680, 680)})
        self.assertEqual(row['fee_options'], review.reviewed_fees()[0]['fee_options'])
        self.assertEqual(row['fee_checked_at'], review.CHECKED)
        self.assertIsNone(row['price_per_hour'])
        for phrase in ['1室全体', '飲み放題', '小学生', '取消期限', '税込']:
            self.assertIn(phrase, row['fee_note'])

    def test_municipal_restrictions_not_money_or_wrong_start_dates(self):
        for ident in review.SUGINAMI_IDS:
            for phrase in ['30日間', '90日間', '任意', '自動徴収']:
                self.assertIn(phrase, self.policies[ident])
        for ident in review.KITA_IDS:
            for phrase in ['14日前', '13～7日前', '6日前', '未払い', '全額納付後']:
                self.assertIn(phrase, self.policies[ident])
        for ident in review.HACHIOJI_IDS:
            for phrase in ['翌々月1日', '7月1日～9月30日', '確保済み', '未確認']:
                self.assertIn(phrase, self.policies[ident])
        for phrase in ['9～5日前', '2ポイント', '無断は3ポイント', '半分以下', '学校体育館']:
            self.assertIn(phrase, self.policies['tokyo-venue-76009f87c8f4'])

    def test_deposit_exception_and_nakano_ambiguity_not_erased(self):
        for ident in review.KOMAZAWA_IDS:
            for phrase in ['10％', '予納金を除く', '1か月前以降', '3日前無料取消をこの']:
                self.assertIn(phrase, self.policies[ident])
        for phrase in ['1か月前から', '15日前まで80％', '7日前まで50％', '6日前から0％', '窓口確認', '5ポイント']:
            self.assertIn(phrase, self.policies['tokyo-venue-712511e56aa8'])
        self.assertIn('変更・キャンセルは不可', self.policies['tokyo-venue-c3c8b7f2193f'])

    def test_indoor_outdoor_lighting_weather_and_partial_closure(self):
        esforta = self.policies['tokyo-venue-c00e2b6906bf']
        for phrase in ['1か月前の同日', '13日前', '8日前', '7～3日前', '2時間前', '屋内アリーナに適用しません']:
            self.assertIn(phrase, esforta)
        for ident in review.SHINAGAWA_IDS:
            for phrase in ['照明料除く', '照明料含む', '電話申出後', '現地へ確認', '譲渡前提']:
                self.assertIn(phrase, self.policies[ident])
        hikari = self.policies['tokyo-venue-a2d6191898f8']
        for phrase in ['第一体育室は停止中', '第二体育室', '再開日は確定していません', '調整中']:
            self.assertIn(phrase, hikari)
        self.assertIn('自分でシステム取消せず', self.policies['tokyo-venue-a6e3e9da0d77'])
        self.assertIn('使用可否を確認', self.policies['tokyo-venue-cd769beb35fc'])

    def test_preservation_of_catalogs_reviews_contacts_and_idempotence(self):
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
        subprocess.run([sys.executable, '-B', str(review.ROOT / 'scripts/record_venue_fee_review_20261124.py')],
                       check=True, capture_output=True)
        self.assertEqual(before, [(review.CATALOGS / name).read_bytes() for name in names])


class November24VenuePublicTests(IsolatedAppHttpCase):
    def test_public_scoped_tariffs_and_cancellation_details(self):
        for name, phrases in [
            ('カラオケパセラ 新宿本店', ('380円', '680円', '大人1名30分', '2027/1/3', '1ドリンク')),
            ('浜町運動場', ('2ポイント', '半分以下', '学校体育館')),
            ('中野区立総合体育館', ('15日前まで80％', '窓口確認')),
            ('しながわ中央公園多目的広場', ('照明料除く', '照明料含む')),
        ]:
            with self.subTest(venue=name):
                status, body, _ = self.request('/venues?' + urlencode({'v_q': name}))
                self.assertEqual(status, 200)
                for phrase in phrases:
                    self.assertIn(phrase, body.decode())


if __name__ == '__main__':
    unittest.main()
