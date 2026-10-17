"""Separate individual/team tariffs, isolated from production data."""
from pathlib import Path
import json
import sqlite3
import tempfile
import unittest
from bs4 import BeautifulSoup
from test_event_flow import load_app, user, create_account, event_payload


class DualPricingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.path = Path(cls.temp.name) / 'dual.sqlite'
        cls.app = load_app(cls.path)
        cls.app.init_db()
        cls.app.EMAIL_NOTIFICATIONS_ENABLED = False
        cls.host = user('dual-host', 'host@example.test', 'Host')
        cls.person = user('dual-person', 'person@example.test', 'Person')
        cls.team = user('dual-team', 'team@example.test', 'Team')
        for account in (cls.host, cls.person, cls.team):
            create_account(cls.app, account)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def save(self, **changes):
        data = event_payload(self._testMethodName, participation_type='both', capacity='30')
        data.update(individual_fee_amount='2500', team_fee_amount='15000', minimum_participants=1)
        data.update(changes)
        with self.app.connect() as conn:
            return self.app.save_event_post(conn, data, self.host)

    def apply(self, eid, mode='individual', count=2):
        with self.app.connect() as conn:
            result = self.app.submit_event_application(conn, eid, dict(participation_type=mode,
                applicant_name='Person', representative_name='Captain', team_name='Test FC',
                participant_count=count), self.person if mode == 'individual' else self.team)
            return dict(conn.execute('select * from event_applications where application_id=?', (result['application_id'],)).fetchone())

    def test_distinct_rates_persist_and_public_html_sharing_agree(self):
        eid = self.save()
        event = self.app.get_event(eid)
        self.assertEqual((event['individual_fee_amount'], event['team_fee_amount']), (2500, 15000))
        for text in (self.app.render_event_detail_html(eid), self.app.event_fee_text(event),
                     self.app.event_share_dialog(event)[1]):
            self.assertIn('2,500円', text)
            self.assertIn('15,000円', text)

    def test_individual_group_and_team_have_different_totals(self):
        eid = self.save()
        person, team = self.apply(eid), self.apply(eid, 'team', 11)
        event = self.app.get_event(eid)
        self.assertEqual(self.app.event_application_total(event, person), '5,000円')
        self.assertEqual(self.app.event_application_total(event, team), '15,000円')
        self.assertEqual(event['confirmed_count'], 13)
        self.assertIn('15,000円', self.app.render_event_apply_html(eid, self.team))
        listing = BeautifulSoup(self.app.render_event_application_operations(eid, self.host), 'html.parser')
        rows = [row.get_text() for row in listing.select('.app-row')]
        self.assertTrue(any('チーム参加' in row and '15,000円' in row for row in rows))
        self.assertTrue(any('個人参加' in row and '5,000円' in row for row in rows))

    def test_notifications_use_the_applications_rate(self):
        eid = self.save()
        person, team = self.apply(eid), self.apply(eid, 'team', 11)
        event = self.app.get_event(eid)
        self.assertIn('参加費合計：5,000円', self.app.confirmed_application_notification_body(event, person))
        self.assertIn('参加費合計：15,000円', self.app.confirmed_application_notification_body(event, team))

    def test_missing_negative_fractional_or_oversized_dual_price_rejected(self):
        for key in ('individual_fee_amount', 'team_fee_amount'):
            for value in ('', None, '-1', '1.5', '10000001'):
                with self.subTest(key=key, value=value), self.assertRaises(ValueError):
                    self.save(**{key: value})
        eid = self.save(participation_type='individual')
        data = event_payload('Switch to both', participation_type='both')
        data['event_id'] = eid
        with self.assertRaisesRegex(ValueError, '個人参加費'), self.app.connect() as conn:
            self.app.save_event_post(conn, data, self.host)

    def test_both_free_versus_one_free(self):
        eid = self.save(individual_fee_amount='0')
        event = self.app.get_event(eid)
        self.assertEqual(event['payment_method'], 'on_site')
        person, team = self.apply(eid), self.apply(eid, 'team', 11)
        self.assertEqual(self.app.application_payment_label(event, person), '無料')
        self.assertEqual(self.app.application_payment_label(event, team), '現地払い予定')
        free = self.app.get_event(self.save(title='All free', individual_fee_amount='0', team_fee_amount='0'))
        self.assertEqual(free['payment_method'], 'free')
        self.assertNotIn('支払方法', self.app.render_event_detail_html(free['event_id']))

    def test_untrusted_amount_cannot_change_team_quote(self):
        eid = self.save()
        with self.app.connect() as conn:
            admission = self.app.submit_event_application(conn, eid, dict(participation_type='team',
                team_name='Test FC', representative_name='Captain', participant_count=11,
                fee_amount=1, team_fee_amount=1), self.team)
            admission = dict(conn.execute('select * from event_applications where application_id=?', (admission['application_id'],)).fetchone())
        self.assertEqual(self.app.event_application_total(self.app.get_event(eid), admission), '15,000円')

    def test_rate_change_after_applications_rejected(self):
        eid = self.save()
        self.apply(eid)
        with self.assertRaisesRegex(ValueError, '申込受付後'):
            self.save(event_id=eid, individual_fee_amount='2600')

    def test_draft_edit_and_copy_keep_rates(self):
        eid = self.save(status='draft')
        self.save(event_id=eid)
        page = self.app.render_event_form_html({'copy': [eid]}, self.host)
        self.assertIn('15000', page)
        soup = BeautifulSoup(page, 'html.parser')
        self.assertEqual(soup.select_one('#individual_fee_amount')['type'], 'text')
        self.assertEqual(soup.select_one('#team_fee_amount')['type'], 'text')

    def test_legacy_both_price_not_reinterpreted_by_migration(self):
        eid = self.save()
        with self.app.connect() as conn:
            conn.execute('update event_posts set individual_fee_amount=null,team_fee_amount=null,fee_amount=1000,fee_unit=? where event_id=?', ('1人', eid))
        self.app.init_db()
        event = self.app.get_event(eid)
        self.assertIsNone(event['team_fee_amount'])
        team = self.apply(eid, 'team', 11)
        self.assertEqual(self.app.event_application_total(event, team), '11,000円')
        data = event_payload('Legacy title edit', participation_type='both', capacity='30')
        data.update(event_id=eid, minimum_participants=1)
        with self.app.connect() as conn:
            self.app.save_event_post(conn, data, self.host)
        self.assertIsNone(self.app.get_event(eid)['team_fee_amount'])
        self.assertIn('id="upgradeDualPricing"', self.app.render_event_form_html({'event_id': [eid]}, self.host))

    def test_migration_is_idempotent_and_preserves_relations(self):
        eid = self.save()
        admission = self.apply(eid)
        with self.app.connect() as conn:
            conn.execute('alter table event_posts drop column individual_fee_amount')
        self.app.init_db()
        self.app.init_db()
        with self.app.connect() as conn:
            self.assertEqual(conn.execute('select event_id from event_applications where application_id=?', (admission['application_id'],)).fetchone()[0], eid)
            self.assertIsNone(conn.execute('pragma foreign_key_check(event_applications)').fetchone())
        self.assertTrue(list(self.path.parent.glob('*.pre-dual-pricing-*.sqlite')))

    def test_capacity_is_total_people_and_approval_rechecks_it(self):
        eid = self.save(capacity='12', acceptance_mode='approval')
        person, team = self.apply(eid), self.apply(eid, 'team', 11)
        with self.app.connect() as conn:
            self.app.set_event_application_status(conn, eid, team['application_id'], 'confirm', self.host)
        with self.assertRaisesRegex(ValueError, '定員'), self.app.connect() as conn:
            self.app.set_event_application_status(conn, eid, person['application_id'], 'confirm', self.host)
        self.assertEqual(self.app.get_event(eid)['confirmed_count'], 11)

    def test_team_headcount_change_does_not_multiply_team_price(self):
        eid = self.save()
        team = self.apply(eid, 'team', 11)
        with self.app.connect() as conn:
            self.app.change_application_count(conn, eid, team['application_id'],
                {'revision': team['operation_revision'], 'participant_count': 12}, self.team)
            updated = dict(conn.execute('select * from event_applications where application_id=?', (team['application_id'],)).fetchone())
        self.assertEqual(self.app.event_application_total(self.app.get_event(eid), updated), '15,000円')
        self.assertEqual(self.app.get_event(eid)['confirmed_count'], 12)

    def test_bank_guidance_uses_team_total_only_after_final_confirmation(self):
        eid = self.save(payment_method='bank_transfer')
        self.apply(eid, 'team', 11)
        with self.app.connect() as conn:
            self.app.announce_event(conn, eid, dict(version=0, starts_at='2030-06-01T10:00', location='会場',
                announcement_details='開催します', attendance_deadline='2030-05-30T18:00',
                payment_deadline='2030-05-31T18:00', bank_transfer_details='TEST BANK ONLY'), self.host)
        self.assertNotIn('TEST BANK ONLY', self.app.render_event_attendance_html(eid, self.team))
        with self.app.connect() as conn:
            self.app.confirm_event_attendance(conn, eid, {'version': 1}, self.team)
        page = self.app.render_event_attendance_html(eid, self.team)
        self.assertIn('お支払額：15,000円', page)
        self.assertIn('TEST BANK ONLY', page)
        self.assertNotIn('165,000円', page)

    def test_host_financial_forecast_uses_each_rate_not_capacity_times_maximum(self):
        eid = self.save(target_total_amount='10000')
        self.apply(eid)
        self.apply(eid, 'team', 11)
        data = next(e for e in self.app.event_my_page(self.host)['hosted'] if e['event_id'] == eid)
        self.assertEqual(data['confirmed_fee_total'], 20000)
        self.assertIn('20,000円', self.app.owner_financial_summary(data))
        self.assertNotIn('450,000円', self.app.owner_financial_summary(data))

    def test_second_mode_is_not_a_duplicate_application_bypass(self):
        eid = self.save()
        self.apply(eid)
        with self.assertRaises(ValueError), self.app.connect() as conn:
            self.app.submit_event_application(conn, eid, dict(participation_type='team', team_name='FC',
                representative_name='Captain', participant_count=11), self.person)

    def test_x_share_keeps_both_tariffs_inside_its_budget(self):
        event = self.app.get_event(self.save(title='大会' * 60, individual_fee_amount=10000000, team_fee_amount=10000000))
        script = self.app.event_share_dialog(event)[1]
        data, _ = json.JSONDecoder().raw_decode(script.split('const data=', 1)[1])
        self.assertIn('個人10,000,000円/チーム10,000,000円', data['xText'])
        self.assertLessEqual(sum(1 if ord(c) < 128 else 2 for c in data['xText']) + 24, 280)


if __name__ == '__main__':
    unittest.main()
