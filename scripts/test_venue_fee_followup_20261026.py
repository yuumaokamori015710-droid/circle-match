"""Verify exact tariff scope, nonstandard units and append-only preservation."""
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
import record_venue_fee_review_20261026 as review


class October26VenueReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {r['id']: r for r in get_catalog()['courts']}

    def ranges(self, ident):
        return {r['unit']: (r['minimum'], r['maximum']) for r in self.rows[ident]['fee_ranges']}

    def test_batch_counts_and_exact_entries(self):
        self.assertEqual(len(set(review.REVIEWED_IDS)), 22)
        self.assertEqual(len(review.reviewed_fees()), 15)
        self.assertEqual(len(review.reviewed_policies()), 6)
        for entry in review.reviewed_fees():
            row = self.rows[entry['id']]
            self.assertEqual(row['fee_options'], entry['fee_options'])
            self.assertEqual(row['fee_note'], entry['fee_note'])
            self.assertEqual(row['fee_checked_at'], review.CHECKED)
        for entry in review.reviewed_policies():
            self.assertEqual(self.rows[entry['id']]['cancellation'], entry)
        later = sum(has_price(r) and r.get('fee_checked_at', '') > review.CHECKED for r in self.rows.values())
        self.assertEqual(len(self.rows), 1206)
        self.assertEqual(sum(has_price(r) for r in self.rows.values()) - later, 816)
        self.assertEqual(sum(not has_price(r) for r in self.rows.values()) + later, 390)
        self.assertEqual(sum(not has_price(r) and r['availability_status'] != 'SUSPENDED'
                             for r in self.rows.values()) + later, 382)

    def test_holds_not_fabricated(self):
        for ident in review.HOLDS:
            self.assertFalse(has_price(self.rows[ident]))
            self.assertEqual(self.rows[ident]['fee_ranges'], [])

    def test_okutama_town_lodging_and_gym_not_field(self):
        self.assertEqual(self.ranges(review.KAWAI), {'体育館・2時間': (500, 3000)})
        self.assertEqual(self.ranges(review.NIPPARA), {'体育館・2時間': (500, 2000)})
        for ident in [review.KAWAI, review.NIPPARA]:
            self.assertIn('町内宿泊施設', self.rows[ident]['fee_note'])
        self.assertIsNone(self.rows[review.NIPPARA]['cancellation'])

    def test_hachijo_indoor_outdoor_and_lighting(self):
        for ident, name in zip(review.HACHIJO[:3], ['中之郷', '樫立', '末吉']):
            self.assertEqual(self.ranges(ident), {name + '運動場・1時間': (250, 250),
                                                name + '屋内運動場・1時間': (500, 500)})
        self.assertIn('別途1時間250円', self.rows[review.HACHIJO[2]]['fee_note'])
        self.assertEqual(self.ranges(review.HACHIJO[3]), {'サッカー場1面・1時間': (500, 500)})

    def test_chofu_restricted_sports_and_track_not_free(self):
        self.assertEqual(self.ranges(review.CHOFU), {'体育室1室・3時間': (1200, 2400)})
        self.assertIn('バスケ・バレー・バドミントンは使用不可', self.rows[review.CHOFU]['fee_note'])
        self.assertEqual(self.ranges(review.TRACK), {'陸上競技場・1時間': (3600, 3600)})

    def test_explicit_free_only_not_unknown_or_personal(self):
        free = {r['id'] for r in review.reviewed_fees() if any(p['amount'] == 0 for p in r['fee_options'])}
        self.assertEqual(free, {review.MUSASHINO, review.NAKAHARA})
        self.assertEqual(self.ranges(review.NAKAHARA), {'練習エリア1面・2時間': (0, 0)})
        self.assertIn('試合のできる広さではなく', self.rows[review.NAKAHARA]['fee_note'])

    def test_geographical_address_not_municipal_operator(self):
        self.assertEqual(self.ranges(review.SHONEN), {'多目的広場・2時間': (1000, 1000)})
        self.assertIn('荒川区管理', self.rows[review.SHONEN]['fee_note'])
        self.assertEqual(self.ranges(review.TAITO), {'サッカー場1面・2時間': (1100, 1950)})
        self.assertIn('台東区管理', self.rows[review.TAITO]['fee_note'])
        self.assertIn('15日前まで8割', self.rows[review.TAITO]['cancellation']['summary'])

    def test_tac_second_room_only_and_short_slots(self):
        self.assertEqual(self.ranges(review.TAC), {'第2体育室・1時間50分': (3100, 6200),
                                                   '第2体育室・2時間30分': (4300, 8600),
                                                   '第2体育室・2時間40分': (4300, 8600)})
        self.assertTrue(all(p['unit'].startswith('第2体育室') for p in self.rows[review.TAC]['fee_options']))

    def test_keio_subarena_only_and_refund_date_basis(self):
        self.assertEqual(self.ranges(review.KEIO), {'サブアリーナ半面・4時間': (7000, 22000),
                                                    'サブアリーナ全面・4時間': (14000, 44000)})
        self.assertEqual(len(self.rows[review.KEIO]['fee_options']), 16)
        self.assertIn('学割区分ではありません', self.rows[review.KEIO]['fee_note'])
        self.assertIn('申込から1か月以内', self.rows[review.KEIO]['cancellation']['summary'])
        self.assertEqual(self.ranges(review.FUJI), {'競技場全面・3時間以内': (15000, 15000),
                                                   '競技場半面・3時間以内': (7500, 7500)})
        self.assertIn('個人申込みによる団体利用不可', self.rows[review.FUJI]['fee_note'])

    def test_original_fields_and_prior_review_prefix(self):
        base = '657654c373c803a1a8d46bf9ea0cb1c01e471f26'
        for name in ['tokyo_tennis.json', 'tokyo_sports.json', 'tokyo_expansion.json',
                     'fee_plans.json', 'cancellation_policies.json']:
            rel = 'outputs/venues/catalogs/' + name
            previous = json.loads(subprocess.check_output(['git', 'show', base + ':' + rel], cwd=ROOT))
            current = json.loads((ROOT / rel).read_bytes())
            self.assertEqual(previous, current if name.startswith('tokyo_') else current[:len(previous)])

    def test_idempotency_and_preflight_conflicts(self):
        paths = [review.CATALOGS / n for n in ['fee_plans.json', 'cancellation_policies.json']]
        before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
        subprocess.run([sys.executable, '-B', '-X', 'utf8', str(ROOT / 'scripts/record_venue_fee_review_20261026.py')],
                       check=True, capture_output=True)
        self.assertEqual(before, [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths])
        fake = dict(self.rows[review.KAWAI], fee_checked_at='2000-01-01')
        rows = [fake if r['id'] == fake['id'] else r for r in self.rows.values()]
        with patch.object(review, 'get_catalog', return_value={'courts': rows}), patch.object(review, 'append_reviews') as append:
            with self.assertRaises(ValueError):
                review.main()
            append.assert_not_called()


if __name__ == '__main__':
    unittest.main()
