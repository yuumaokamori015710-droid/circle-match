"""Offline payment choices and the guarded operator correction, using temporary DBs."""
import itertools
import json
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from bs4 import BeautifulSoup
from test_event_flow import load_app, user, create_account, event_payload


class PaymentChoiceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.path = Path(cls.temp.name) / "choices.sqlite"
        cls.app = load_app(cls.path)
        cls.app.init_db()
        cls.app.EMAIL_NOTIFICATIONS_ENABLED = False
        cls.host = user("choices-host", "host@example.test", "Host")
        cls.people = [user(f"choices-person-{n}", f"p{n}@example.test", f"Person {n}") for n in range(5)]
        for person in [cls.host, *cls.people]:
            create_account(cls.app, person)
        cls.serial = itertools.count()

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def event(self, **changes):
        data = event_payload(f"{self.id()}-{next(self.serial)}", participation_type="both", capacity="")
        data.update(individual_fee_amount="2500", team_fee_amount="15000",
                    payment_method="on_site_or_bank_transfer", minimum_participants=1)
        data.update(changes)
        with self.app.connect() as conn:
            return self.app.save_event_post(conn, data, self.host)

    def apply(self, eid, person=0, kind="individual", method="on_site", count=1):
        data = dict(participation_type=kind, participant_count=count, applicant_name="Person",
                    team_name="Test FC", representative_name="Captain")
        if method is not None:
            data["payment_method"] = method
        with self.app.connect() as conn:
            result = self.app.submit_event_application(conn, eid, data, self.people[person])
            return dict(conn.execute("select * from event_applications where application_id=?", (result["application_id"],)).fetchone())

    def announce(self, eid):
        with self.app.connect() as conn:
            return self.app.announce_event(conn, eid, dict(version=0, starts_at="2030-06-01T10:00",
                location="Test field", announcement_details="Meet at entrance", attendance_deadline="2030-05-30T12:00",
                payment_deadline="2030-05-31T18:00", bank_transfer_details="PRIVATE-ACCOUNT"), self.host)

    def test_both_modes_and_both_methods_keep_correct_totals(self):
        eid = self.event()
        for index, (kind, method) in enumerate((('individual', 'on_site'), ('individual', 'bank_transfer'),
                                               ('team', 'on_site'), ('team', 'bank_transfer'))):
            admission = self.apply(eid, index, kind, method, 11 if kind == 'team' else 1)
            self.assertEqual(admission['selected_payment_method'], method)
            event = self.app.get_event(eid)
            self.assertEqual(self.app.event_application_total(event, admission), '15,000円' if kind == 'team' else '2,500円')
            self.assertIn(self.app.event_payment_label(method), self.app.event_application_recap(event, admission))
            self.assertIn(self.app.event_payment_label(method), self.app.confirmed_application_notification_body(event, admission))
        self.assertIsNone(self.app.get_event(eid)['capacity'])
        self.assertEqual(self.app.get_event(eid)['confirmed_count'], 24)

    def test_choice_required_and_unlisted_methods_rejected(self):
        eid = self.event()
        for method in (None, 'online', 'free', 'wire', 'on_site_or_bank_transfer'):
            with self.subTest(method=method), self.assertRaisesRegex(ValueError, '支払方法'):
                self.apply(eid, method=method)

    def test_legacy_single_method_does_not_require_new_client_fields(self):
        for method in ('on_site', 'bank_transfer'):
            eid = self.event(payment_method=method)
            admission = self.apply(eid, method=None)
            self.assertEqual(admission['selected_payment_method'], method)
            with self.assertRaisesRegex(ValueError, '支払方法'):
                self.apply(eid, person=1, method='online')

    def test_free_tariff_has_no_payment_requirement(self):
        eid = self.event(individual_fee_amount='0')
        admission = self.apply(eid, method=None)
        self.assertEqual(admission['selected_payment_method'], 'free')
        self.assertEqual(self.app.application_payment_label(self.app.get_event(eid), admission), '無料')
        self.assertNotIn('支払方法', self.app.event_application_recap(self.app.get_event(eid), admission))

    def test_bank_details_only_for_confirmed_bank_payer(self):
        eid = self.event()
        self.apply(eid, person=0, method='on_site')
        self.apply(eid, person=1, kind='team', method='bank_transfer', count=11)
        self.announce(eid)
        self.assertNotIn('PRIVATE-ACCOUNT', self.app.render_event_attendance_html(eid, self.people[1]))
        for person in self.people[:2]:
            with self.app.connect() as conn:
                self.app.confirm_event_attendance(conn, eid, {'version': 1}, person)
        cash = self.app.render_event_attendance_html(eid, self.people[0])
        bank = self.app.render_event_attendance_html(eid, self.people[1])
        self.assertNotIn('PRIVATE-ACCOUNT', cash)
        self.assertIn('現地でお支払い', cash)
        self.assertIn('PRIVATE-ACCOUNT', bank)
        self.assertIn('15,000円', bank)
        self.assertNotIn('PRIVATE-ACCOUNT', json.dumps(self.app.get_event(eid)))
        self.assertNotIn('PRIVATE-ACCOUNT', self.app.render_event_detail_html(eid))

    def test_expired_bank_deadline_does_not_block_cash(self):
        eid = self.event()
        self.apply(eid, method='bank_transfer')
        self.announce(eid)
        with self.app.connect() as conn:
            conn.execute("update event_posts set payment_deadline='2020-01-01 12:00' where event_id=?", (eid,))
        self.assertTrue(self.app.event_availability(self.app.get_event(eid))[1])
        self.assertEqual(self.apply(eid, person=1)['selected_payment_method'], 'on_site')
        with self.assertRaisesRegex(ValueError, '振込期限'):
            self.apply(eid, person=2, method='bank_transfer')
        with self.app.connect() as conn, self.assertRaisesRegex(ValueError, '振込期限'):
            self.app.confirm_event_attendance(conn, eid, {'version': 1}, self.people[0])

    def test_host_editor_and_application_choices(self):
        eid = self.event()
        event = self.app.get_event(eid)
        self.assertEqual(event['payment_method'], 'bank_transfer')
        self.assertEqual(event['allow_on_site_payment'], 1)
        self.assertIn('現地払い・口座振込', self.app.render_event_detail_html(eid))
        editor = self.app.render_event_form_html({'event_id': [eid]}, self.host)
        self.assertIn('"payment_method": "on_site_or_bank_transfer"', editor)
        self.assertIn('on_site_or_bank_transfer:', editor)
        page = BeautifulSoup(self.app.render_event_apply_html(eid, self.people[0]), 'html.parser')
        self.assertEqual({item['value'] for item in page.select('[name=payment_method]')}, {'on_site', 'bank_transfer'})
        self.assertTrue(all(item.has_attr('required') for item in page.select('[name=payment_method]')))

    def test_payment_selection_is_frozen_after_first_application(self):
        eid = self.event()
        self.apply(eid)
        with self.assertRaisesRegex(ValueError, '支払方法'):
            self.event(event_id=eid, payment_method='bank_transfer', allow_on_site_payment=False)

    def test_other_user_still_cannot_edit(self):
        eid = self.event()
        data = event_payload('Unauthorized edit', participation_type='both', capacity='')
        data.update(event_id=eid, individual_fee_amount=2500, team_fee_amount=15000, payment_method='on_site_or_bank_transfer')
        with self.app.connect() as conn, self.assertRaises(PermissionError):
            self.app.save_event_post(conn, data, self.people[0])

    def test_migration_idempotence_and_legacy_data(self):
        path = Path(self.temp.name) / 'legacy.sqlite'
        conn = sqlite3.connect(path)
        conn.row_factory = sqlite3.Row
        try:
            conn.executescript("create table event_posts(event_id text, payment_method text);"
                               "create table event_applications(application_id text, status text);"
                               "insert into event_posts values('legacy','on_site');"
                               "insert into event_applications values('application','confirmed');")
            with patch.object(self.app, 'DB_PATH', path):
                self.app.migrate_event_payment_choices(conn)
                self.app.migrate_event_payment_choices(conn)
            self.assertEqual(tuple(conn.execute('select payment_method,allow_on_site_payment from event_posts').fetchone()), ('on_site', 0))
            self.assertEqual(tuple(conn.execute('select status,selected_payment_method from event_applications').fetchone()), ('confirmed', None))
            self.assertEqual(len(list(path.parent.glob(path.name + '.pre-payment-choices-*'))), 1)
        finally:
            conn.close()

    def test_operator_correction_is_exact_once_and_preserves_owner(self):
        eid = self.event(participation_type='individual', payment_method='on_site', fee_amount=2500,
                         individual_fee_amount=None, team_fee_amount=None, minimum_participants=5)
        target = 'event_user_supabase_fe23d660_0d10_49cc_ae6_f42c6bd8fd'
        with self.app.connect() as conn:
            conn.execute('update event_posts set event_id=? where event_id=?', (target, eid))
        try:
            before = self.app.get_event(target)
            self.assertEqual(self.app.repair_requested_komazawa_admission(), 'applied')
            self.assertEqual(self.app.repair_requested_komazawa_admission(), 'already_applied')
            after = self.app.get_event(target)
            for key in ('title', 'description', 'starts_at', 'location', 'capacity', 'minimum_participants'):
                self.assertEqual(before[key], after[key])
            self.assertEqual((after['participation_type'], after['individual_fee_amount'], after['team_fee_amount'], after['allow_on_site_payment']), ('both', 2500, 15000, 1))
            with self.app.connect() as conn:
                self.assertEqual(conn.execute('select organizer_user_id from event_posts where event_id=?', (target,)).fetchone()[0], self.host['user_id'])
                self.assertEqual(conn.execute("select count(*) from audit_logs where action='komazawa_admission_20261028'").fetchone()[0], 1)
        finally:
            with self.app.connect() as conn:
                conn.execute("delete from audit_logs where action='komazawa_admission_20261028'")
                conn.execute('delete from event_posts where event_id=?', (target,))

    def test_operator_correction_does_not_change_existing_applications(self):
        eid = self.event(participation_type='individual', payment_method='on_site', fee_amount=2500,
                         individual_fee_amount=None, team_fee_amount=None, minimum_participants=5)
        target = 'event_user_supabase_fe23d660_0d10_49cc_ae6_f42c6bd8fd'
        with self.app.connect() as conn:
            conn.execute('update event_posts set event_id=? where event_id=?', (target, eid))
        try:
            self.apply(target)
            self.assertEqual(self.app.repair_requested_komazawa_admission(), 'not_eligible')
            self.assertEqual(self.app.get_event(target)['participation_type'], 'individual')
        finally:
            with self.app.connect() as conn:
                for table in ('event_notifications', 'event_applications'):
                    conn.execute(f'delete from {table} where event_id=?', (target,))
                conn.execute('delete from event_posts where event_id=?', (target,))

    def test_operator_correction_skips_changed_settings_and_protected_payments(self):
        eid = self.event(participation_type='individual', payment_method='on_site', fee_amount=2500,
                         individual_fee_amount=None, team_fee_amount=None, minimum_participants=5)
        target = 'event_user_supabase_fe23d660_0d10_49cc_ae6_f42c6bd8fd'
        with self.app.connect() as conn:
            conn.execute('update event_posts set event_id=?,fee_amount=2600 where event_id=?', (target, eid))
        try:
            self.assertEqual(self.app.repair_requested_komazawa_admission(), 'not_eligible')
            with self.app.connect() as conn:
                conn.execute('update event_posts set fee_amount=2500 where event_id=?', (target,))
            with patch.object(self.app.online_payments, 'guard_mutation', side_effect=self.app.online_payments.PaymentError('protected')):
                self.assertEqual(self.app.repair_requested_komazawa_admission(), 'protected_payment')
            self.assertEqual(self.app.get_event(target)['participation_type'], 'individual')
        finally:
            with self.app.connect() as conn:
                conn.execute('delete from event_posts where event_id=?', (target,))


if __name__ == '__main__':
    unittest.main()
