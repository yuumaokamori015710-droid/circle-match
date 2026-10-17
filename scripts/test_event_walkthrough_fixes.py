"""Regression cases from the participant and organizer walkthrough."""
import json
from pathlib import Path
import tempfile
import unittest
from urllib.parse import parse_qs, urlparse, unquote
from bs4 import BeautifulSoup
from test_event_flow import load_app, user, create_account, event_payload


class WalkthroughFixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.app = load_app(Path(cls.temp.name) / 'walkthrough.sqlite')
        cls.app.init_db()
        cls.app.EMAIL_NOTIFICATIONS_ENABLED = False
        cls.host = user('fix-host', 'host@example.test', 'Host')
        cls.person = user('fix-person', 'person@example.test', 'Person')
        for account in (cls.host, cls.person):
            create_account(cls.app, account)

    @classmethod
    def tearDownClass(cls):
        cls.temp.cleanup()

    def event(self, **changes):
        payload = event_payload(self.id(), capacity='12')
        payload.update(minimum_participants=1, target_total_amount='5000')
        payload.update(changes)
        with self.app.connect() as conn:
            return self.app.save_event_post(conn, payload, self.host)

    def apply(self, eid, count=2, team=False):
        with self.app.connect() as conn:
            return self.app.submit_event_application(conn, eid, {
                'participation_type': 'team' if team else 'individual', 'applicant_name': 'Person',
                'team_name': '検証FC', 'representative_name': '代表者', 'participant_count': count,
            }, self.person)

    def test_list_cards_and_detail_preserve_all_filters(self):
        eid = self.event(title='東京の申込条件確認会')
        params = {'sport': ['サッカー・フットサル'], 'prefecture': ['東京都'],
                  'date_from': ['2030-01-01'], 'participation': ['individual'], 'event_type': ['大会']}
        markup = self.app.render_event_cards([self.app.get_event(eid)], params)
        link = BeautifulSoup(markup, 'html.parser').select_one('h3 a')['href']
        destination = parse_qs(urlparse(link).query)['return_to'][0]
        self.assertEqual(BeautifulSoup(markup, 'html.parser').select_one('.event-card')['id'],
                         unquote(urlparse(destination).fragment))
        values = parse_qs(urlparse(destination).query)
        for key, value in params.items():
            self.assertEqual(values[key], value)
        page = self.app.render_event_detail_html(eid, self.person, {'return_to': [destination]})
        back = BeautifulSoup(page, 'html.parser').find('a', string='大会・イベント一覧')
        self.assertEqual(back['href'], destination)

    def test_list_return_rejects_foreign_urls_and_non_list_paths(self):
        for unsafe in ['//evil.test', '/\\evil.test', '/%5cevil.test',
                       'https://evil.test', '/events/new', '/logout', '/?tab=db']:
            with self.subTest(unsafe=unsafe):
                self.assertEqual(self.app.event_list_return({'return_to': [unsafe]}), '/events')

    def test_application_success_shows_group_count_and_total(self):
        eid = self.event()
        self.apply(eid)
        soup = BeautifulSoup(self.app.render_event_apply_html(eid, self.person), 'html.parser')
        summary = soup.select_one('.application-result-summary')
        self.assertIsNotNone(summary)
        self.assertIn('2名', summary.get_text())
        self.assertIn('2,000円', summary.get_text())

    def test_input_is_brief_and_full_conditions_are_in_confirmation_step(self):
        eid = self.event(eligibility='確認すべき参加条件', cancellation_policy='確認すべき取消条件')
        soup = BeautifulSoup(self.app.render_event_apply_html(eid, self.person), 'html.parser')
        self.assertIsNotNone(soup.select_one('.application-brief'))
        review = soup.select_one('#applicationReview')
        self.assertIn('確認すべき参加条件', review.get_text())
        self.assertIn('確認すべき取消条件', review.get_text())
        self.assertTrue(review.select_one('#applicationConditions').has_attr('required'))

    def test_announced_event_below_minimum_warns_without_cancelling(self):
        eid = self.event(participation_type='team', capacity='2')
        admission = self.apply(eid, 10, team=True)
        with self.app.connect() as conn:
            conn.execute("update event_posts set announcement_version=1 where event_id=?", (eid,))
        with self.app.connect() as conn:
            self.app.cancel_event_application(conn, eid, admission['application_id'], self.person)
        self.assertIn('最低開催数未達', self.app.event_formation_label(self.app.get_event(eid)))
        page = self.app.render_mypage_html(self.host)
        self.assertIn('開催可否を再確認', page)
        self.assertEqual(self.app.get_event(eid)['status'], 'published')

    def test_owner_management_has_inline_approval_and_next_action(self):
        eid = self.event(acceptance_mode='approval')
        admission = self.apply(eid)
        listing = BeautifulSoup(self.app.render_event_application_operations(eid, self.host), 'html.parser')
        self.assertIn('承認待ち 1件', listing.get_text())
        self.assertIsNotNone(listing.select_one('button[name=action][value=confirm]'))
        self.assertNotIn('未入金1件', listing.get_text().replace(' ', ''))
        with self.app.connect() as conn:
            self.app.set_event_application_status(conn, eid, admission['application_id'], 'confirm', self.host)
        page = self.app.render_event_application_operations(eid, self.host, admission['application_id'])
        self.assertIn('開催を決定する', page)

    def test_payment_labels_distinguish_pending_on_site_and_late_transfer(self):
        eid = self.event(acceptance_mode='approval')
        admission = self.apply(eid)
        event = self.app.get_event(eid)
        self.assertEqual(self.app.application_payment_label(event, dict(admission, status='pending')), '受付未確定・支払対象外')
        self.assertEqual(self.app.application_payment_label(event, dict(admission, status='confirmed')), '現地払い予定')
        bank = dict(event, payment_method='bank_transfer', announcement_version=1, payment_deadline='2000-01-01 12:00')
        self.assertEqual(self.app.application_payment_label(bank, dict(admission, status='confirmed', attendance_version=1)), '振込期限超過')

    def test_cancel_button_identifies_event_team_and_whole_group(self):
        eid = self.event(participation_type='team', capacity='2')
        self.apply(eid, 10, team=True)
        soup = BeautifulSoup(self.app.render_mypage_html(self.person), 'html.parser')
        card = next(c for c in soup.select('#my-attending .my-card') if self.id() in c.get_text())
        button = card.select_one('[data-cancel-app]')
        self.assertIn(self.id(), button['data-cancel-message'])
        self.assertIn('検証FC', button['data-cancel-message'])
        self.assertIn('10名全員', button['data-cancel-message'])
        self.assertEqual(button['data-count-url'], '/events/' + eid + '/applications/' + button['data-cancel-app'])
        self.assertEqual(soup.select_one('#actionConfirm').get_text(), '実行する')

    def test_host_financial_and_secondary_actions_are_collapsed(self):
        eid = self.event()
        self.apply(eid)
        soup = BeautifulSoup(self.app.render_mypage_html(self.host), 'html.parser')
        card = next(c for c in soup.select('#my-hosted .my-card') if self.id() in c.get_text())
        self.assertIsNotNone(card.select_one('details.host-financial:not([open])'))
        self.assertIsNotNone(card.select_one('details.host-more:not([open])'))
        self.assertIn('収支の見込み', card.select_one('details.host-financial summary').get_text())

    def test_share_includes_fee_and_admission_mode(self):
        eid = self.event(acceptance_mode='approval')
        _, script = self.app.event_share_dialog(self.app.get_event(eid))
        self.assertIn('参加費: 1,000円', script)
        self.assertIn('受付方式: 主催者承認制', script)

    def test_x_share_keeps_long_japanese_metadata_within_post_budget(self):
        eid = self.event(title='大会' * 60, location='会場' * 100, description='内容' * 1000,
                         eligibility='参加条件' * 100, acceptance_mode='approval')
        _, script = self.app.event_share_dialog(self.app.get_event(eid))
        data, _ = json.JSONDecoder().raw_decode(script.split('const data=', 1)[1])
        weight = sum(1 if ord(char) < 128 else 2 for char in data['xText'])
        self.assertLessEqual(weight + 24, 280)
        self.assertIn('参加費:', data['xText'])
        self.assertIn('受付方式:', data['xText'])

    def test_on_site_announcement_does_not_describe_bank_transfer(self):
        eid = self.event()
        self.apply(eid)
        page = self.app.render_event_organize_html(eid, self.host)
        self.assertNotIn('振込先・期限を表示', page)
        self.assertIn('現地払い', page)

    def test_hosting_signin_explains_requirement(self):
        page = self.app.render_signin_html('/events/new').decode()
        self.assertIn('掲載にはログインが必要です', page)

    def test_publication_preview_requires_consistent_conditions_acknowledgement(self):
        soup = BeautifulSoup(self.app.render_event_form_html({}, self.host), 'html.parser')
        checkbox = soup.select_one('[data-step="2"] #publicationConsistency')
        self.assertIsNotNone(checkbox)
        self.assertTrue(checkbox.has_attr('required'))
        self.assertIn('説明と一致', checkbox.parent.get_text())

    def test_continuation_below_minimum_requires_ack_and_creates_new_notice_version(self):
        eid = self.event(title='人数不足での開催継続確認')
        admission = self.apply(eid)
        data = dict(version=0, starts_at='2030-06-01T10:00', location='会場',
                    announcement_details='継続して開催します。', attendance_deadline='2030-05-31T18:00')
        with self.app.connect() as conn:
            self.app.announce_event(conn, eid, data, self.host)
        with self.app.connect() as conn:
            self.app.cancel_event_application(conn, eid, admission['application_id'], self.person)
        data['version'] = 1
        with self.assertRaisesRegex(ValueError, '最低開催数未達'), self.app.connect() as conn:
            self.app.announce_event(conn, eid, data, self.host)
        data['continue_below_minimum'] = '1'
        with self.app.connect() as conn:
            self.assertEqual(self.app.announce_event(conn, eid, data, self.host), 2)

    def test_on_site_notification_has_payment_specific_copy(self):
        eid = self.event()
        self.apply(eid)
        with self.app.connect() as conn:
            self.app.announce_event(conn, eid, dict(version=0, starts_at='2030-06-01T10:00',
                location='会場', announcement_details='開催します', attendance_deadline='2030-05-31T18:00'), self.host)
        note = next(n for n in self.app.notifications_for_user(self.person)
                    if n['event_id'] == eid and n['notification_type'] == 'event_announced')
        self.assertIn('現地払い', note['body'])
        self.assertNotIn('振込先', note['body'])


if __name__ == '__main__':
    unittest.main()
