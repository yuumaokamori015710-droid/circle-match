"""Tariff identity, eligibility, closure, and append-only audit checks."""
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
import record_venue_fee_review_20261103 as review


class November3VenueReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.rows = {r['id']: r for r in get_catalog()['courts']}

    def ranges(self, ident):
        return {r['unit']: (r['minimum'], r['maximum']) for r in self.rows[ident]['fee_ranges']}

    def test_inventory_and_exact_reviewed_rows(self):
        self.assertEqual(len(set(review.REVIEWED_IDS)), 29)
        self.assertEqual(len(review.reviewed_fees()), 13)
        self.assertEqual(len(review.reviewed_policies()), 14)
        self.assertEqual(len(review.HOLDS), 16)
        self.assertEqual(len(self.rows), 1206)
        later = sum(has_price(r) and r.get('fee_checked_at', '') > review.CHECKED for r in self.rows.values())
        later_closures = sum(not has_price(r) and r['availability_status'] == 'SUSPENDED' and r['checked_at'] > review.CHECKED for r in self.rows.values())
        self.assertEqual(sum(has_price(r) for r in self.rows.values()) - later, 891)
        self.assertEqual(sum(not has_price(r) for r in self.rows.values()) + later, 315)
        self.assertEqual(sum(not has_price(r) and r['availability_status'] != 'SUSPENDED' for r in self.rows.values()) + later + later_closures, 305)
        for fee in review.reviewed_fees():
            row = self.rows[fee['id']]
            self.assertEqual(row['fee_options'], fee['fee_options'])
            self.assertEqual(row['fee_note'], fee['fee_note'])
            self.assertEqual(row['fee_checked_at'], review.CHECKED)
            self.assertTrue(all(p['amount'] > 0 for p in row['fee_options']))
        for policy in review.reviewed_policies():
            self.assertEqual(self.rows[policy['id']]['cancellation'], policy)

    def test_koto_single_room_durations_and_registered_not_personal(self):
        for ident, slug, section, room, values in review.KOTO:
            self.assertEqual(self.ranges(ident), {room + '・3時間（通常・割増なし）': (values[0], values[0]),
                                                room + '・4時間（通常・割増なし）': (min(values[1:]), max(values[1:]))})
            self.assertTrue(all(p['source_url'] == review.koto_url(slug, section, 'fee') for p in self.rows[ident]['fee_options']))
            for phrase in ['全室の最安値ではありません', '区内外', '2名以上', '1500円', '5割増', '不特定多数', '営利目的不可']:
                self.assertIn(phrase, self.rows[ident]['fee_note'])
            text = self.rows[ident]['cancellation']['summary']
            for phrase in ['14日前21時', '7日前21時', '半額', '直前の開館日', '振込手数料', '一般室へ適用しません', '通常の雨天免除は未確認']:
                self.assertIn(phrase, text)

    def test_sumida_no_child_gym_or_extension_in_room_tariffs(self):
        ume, yoko = [r[0] for r in review.SUMIDA]
        self.assertEqual(self.ranges(ume), {'多目的室・3時間（通常）': (2200, 2200), '多目的室・4時間（通常）': (2900, 2900)})
        self.assertEqual(self.ranges(yoko), {'和室25畳・3時間（通常）': (2600, 2600), '和室25畳・4時間（通常）': (3400, 3400), '和室25畳・2時間（通常）': (1700, 1700)})
        self.assertIn('土曜日も平日', self.rows[yoko]['fee_note'])
        self.assertIn('学校休業日は夜間Bのみ', self.rows[yoko]['fee_note'])
        for ident in [ume, yoko]:
            self.assertIn('児童向け体育室', self.rows[ident]['fee_note'])
            self.assertIn('利用5日前', self.rows[ident]['cancellation']['summary'])
            self.assertIn('全額返還', self.rows[ident]['cancellation']['summary'])

    def test_tama_track_durations_and_admission_not_parking_or_personal_fee(self):
        self.assertEqual(self.ranges(review.TRACK), {'競技場貸切・3時間（入場料加算・設備別）': (8370, 8370),
                                                    '競技場貸切・4時間（入場料加算・設備別）': (12560, 12560),
                                                    '競技場貸切・8時間（入場料加算・設備別）': (20930, 20930)})
        text = self.rows[review.TRACK]['fee_note']
        for phrase in ['最高入場料×100', '貸切利用条件', '夜間照明なし', '個人開放では芝生内立入不可']:
            self.assertIn(phrase, text)
        self.assertIn('自動適用しません', self.rows[review.TRACK]['cancellation']['summary'])

    def test_tama_baseball_residency_separate_and_old_lighting_excluded(self):
        for ident, name, amounts in review.BASEBALL:
            self.assertEqual(self.ranges(ident), {'野球場1面・2時間（' + group + '・大人一般・照明別）': (v, v)
                                                for group, v in zip(['市内登録団体', '市外登録団体'], amounts)})
            for phrase in ['10名以上', '半数以上', '名簿外利用不可', '1時間枠', '前月16日']:
                self.assertIn(phrase, self.rows[ident]['fee_note'])
            text = self.rows[ident]['cancellation']['summary']
            for phrase in ['前月1～15日', '80%', '3日前', '50%', '30分以上', '5年以内', '大会開催', '対象外']:
                self.assertIn(phrase, text)
        self.assertIn('夜間照明の稼働終了', self.rows[review.BASEBALL[0][0]]['fee_note'])

    def test_holds_unknown_and_new_closure_hidden_not_deleted(self):
        for ident in review.HOLDS:
            from venue_review_test_helpers import assert_historical_hold
            assert_historical_hold(self, self.rows[ident])
        row = self.rows[review.CLOSED]
        self.assertEqual(row['availability_status'], 'SUSPENDED')
        self.assertEqual(row['availability_note'], review.CLOSURE_NOTE)
        self.assertEqual(row['checked_at'], review.CHECKED)
        self.assertEqual(filter_catalog([row], {}), [])
        self.assertEqual(len(filter_catalog([row], {'show_suspended': '1'})), 1)

    def test_dark_theme_tariff_header_has_explicit_readable_colors(self):
        css = (ROOT / 'outputs/club_static/styles.css').read_text(encoding='utf-8')
        self.assertIn('.cm-club .venue-directory .venue-tariff thead{background:#29332b;color:#f2f5f2}', css)
        def luminance(color):
            channels = [int(color[i:i + 2], 16) / 255 for i in (0, 2, 4)]
            linear = [v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4 for v in channels]
            return sum(v * w for v, w in zip(linear, [.2126, .7152, .0722]))
        self.assertGreater((luminance('f2f5f2') + .05) / (luminance('29332b') + .05), 4.5)

    def test_prior_records_ids_booking_urls_and_all_nonclosure_fields_preserved(self):
        for name in ['tokyo_tennis.json', 'tokyo_sports.json', 'tokyo_expansion.json', 'fee_plans.json', 'cancellation_policies.json']:
            rel = 'outputs/venues/catalogs/' + name
            before = json.loads(subprocess.check_output(['git', 'show', review.BASE + ':' + rel], cwd=ROOT))
            after = json.loads((ROOT / rel).read_bytes())
            from venue_review_test_helpers import before_november4_closure
            after = before_november4_closure(after, before)
            if name.startswith('tokyo_'):
                self.assertEqual([r['id'] for r in before], [r['id'] for r in after])
                for old, new in zip(before, after):
                    allowed = {'checked_at', 'availability_status', 'availability_note', 'sources'} if old['id'] == review.CLOSED else set()
                    self.assertEqual(set(old), set(new))
                    for field in set(old) - allowed:
                        self.assertEqual(old[field], new[field], (old['id'], field))
                    if allowed:
                        self.assertEqual(new['sources'], old['sources'] + [review.CLOSURE_EVIDENCE])
            else:
                self.assertEqual(before, after[:len(before)])
                self.assertEqual(sum(r['checked_at'] == review.CHECKED for r in after[len(before):]), 13 if name == 'fee_plans.json' else 14)

    def test_idempotence_conflicts_before_any_mutation(self):
        paths = [review.CATALOGS / p for p in ['fee_plans.json', 'cancellation_policies.json', 'tokyo_expansion.json']]
        before = [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths]
        subprocess.run([sys.executable, '-B', str(ROOT / 'scripts/record_venue_fee_review_20261103.py')], check=True, capture_output=True)
        self.assertEqual(before, [hashlib.sha256(p.read_bytes()).hexdigest() for p in paths])
        fake = dict(self.rows[review.TRACK], fee_checked_at='2000-01-01')
        rows = [fake if r['id'] == fake['id'] else r for r in self.rows.values()]
        with patch.object(review, 'get_catalog', return_value={'courts': rows}), patch.object(review, 'update_closure') as closure, patch.object(review, 'append_reviews') as append:
            with self.assertRaises(ValueError):
                review.main()
            closure.assert_not_called()
            append.assert_not_called()


if __name__ == '__main__':
    unittest.main()
