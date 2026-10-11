"""Home latest-event checks using disposable SQLite and loopback HTTP only."""
from html import unescape
import re
import unittest
from unittest.mock import patch
from urllib.parse import quote, unquote, urlencode

from test_event_flow import create_account, event_payload, user
from test_venues import IsolatedAppHttpCase


class HomeLatestEventTests(IsolatedAppHttpCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.host = user('latest-host', 'private-host@example.test', '公開主催者')
        cls.guest = user('latest-guest', 'private-guest@example.test', '参加者')
        create_account(cls.app, cls.host)
        create_account(cls.app, cls.guest)
        # Production's original schema treats published events as public. Also
        # exercise the stricter visibility column supported by newer schemas.
        with cls.app.connect() as conn:
            columns = {row['name'] for row in conn.execute('pragma table_info(event_posts)')}
            if 'visibility' not in columns:
                conn.execute("alter table event_posts add column visibility text not null default 'public'")

    def setUp(self):
        with self.app.connect() as conn:
            conn.execute('delete from event_applications')
            conn.execute('delete from event_posts')
        self.clock = patch.object(self.app, 'event_local_now', return_value='2029-01-01 12:00')
        self.clock.start()
        self.addCleanup(self.clock.stop)

    def make_event(self, title, *, sport='テニス', prefecture='東京都',
                   published_at='2028-12-01T10:00:00+09:00',
                   created_at='2028-11-01T10:00:00+09:00', **changes):
        payload = event_payload(title)
        payload.update(sport_category=sport, prefecture=prefecture)
        with self.app.connect() as conn:
            event_id = self.app.save_event_post(conn, payload, self.host)
            values = dict(changes, published_at=published_at, created_at=created_at)
            conn.execute('update event_posts set ' + ','.join(key + '=?' for key in values) + ' where event_id=?',
                         [*values.values(), event_id])
        return event_id

    def home(self, path='/'):
        status, body, _ = self.request(path)
        self.assertEqual(status, 200)
        return body.decode('utf-8')

    def test_newest_three_across_sports_and_regions_use_publication_or_creation(self):
        expected = []
        for index in range(8):
            stamp = f'2028-12-{index + 1:02}T10:00:00+09:00'
            event_id = self.make_event('最新募集' + str(index), sport='テニス' if index % 2 else 'サッカー・フットサル',
                                       prefecture='東京都' if index % 2 else '大阪府',
                                       published_at=stamp if index != 7 else None, created_at=stamp,
                                       starts_at=f'2030-06-{20 - index:02} 10:00',
                                       updated_at='2035-01-01T00:00:00+09:00' if index == 0 else stamp)
            expected.insert(0, event_id)
        result = self.app.latest_home_events()
        self.assertEqual([event['event_id'] for event in result], expected[:3])
        page = self.home('/?' + urlencode({'region':'kansai', 'prefecture':'大阪府'}))
        self.assertLess(page.index('id="home-journeys-heading"'), page.index('id="sports-list"'))
        self.assertLess(page.index('id="sports-list"'), page.index('id="homeLatestEvents"'))
        rows = re.search(r'<ul[^>]*id="homeLatestEvents"[^>]*>(.*?)</ul>', page, re.S)
        self.assertIsNotNone(rows)
        row_ids = [unquote(value) for value in re.findall(r'href="/events/([^"]+)"', rows.group(1))]
        self.assertEqual(row_ids, expected[:3])
        self.assertEqual(rows.group(1).count('class="home-latest-item"'), 3)
        self.assertEqual(rows.group(1).count('class="home-latest-link"'), 3)
        self.assertEqual(rows.group(1).count('class="home-latest-title"'), 3)
        self.assertNotIn('<article class="event-card">', page)

    def test_draft_private_closed_cancelled_expired_and_full_events_are_excluded(self):
        wanted = self.make_event('募集中の公開イベント', published_at='2028-01-01T10:00:00+09:00')
        cases = [dict(status='draft'), dict(status='closed'), dict(status='cancelled'),
                 dict(visibility='private'), dict(visibility='unlisted'),
                 dict(starts_at='2028-01-01 10:00'), dict(application_deadline='2028-12-31 18:00'),
                 dict(announcement_version=1, payment_deadline='2028-12-31 18:00'),
                 dict(announcement_version=1, attendance_deadline='2028-12-31 18:00')]
        excluded = [self.make_event('非表示募集' + str(index), **changes) for index, changes in enumerate(cases)]
        full = self.make_event('満員の募集', capacity=2)
        with self.app.connect() as conn:
            conn.execute("""insert into event_applications
                (application_id,event_id,applicant_user_id,participation_type,participant_count,status,created_at,updated_at)
                values(?,?,?,?,?,?,?,?)""",
                ('full-application', full, self.guest['user_id'], 'individual', 2, 'confirmed', self.app.now(), self.app.now()))
        self.assertEqual([event['event_id'] for event in self.app.latest_home_events()], [wanted])
        page = self.home()
        for event_id in [*excluded, full]:
            self.assertNotIn('/events/' + quote(event_id), page)
        self.assertIn('/events/' + quote(wanted), page)

    def test_publication_order_handles_timezone_offsets(self):
        older = self.make_event('絶対時刻が古い募集', published_at='2028-12-10T10:00:00+09:00')
        newer = self.make_event('絶対時刻が新しい募集', published_at='2028-12-10T02:00:00+00:00')
        self.assertEqual([event['event_id'] for event in self.app.latest_home_events()], [newer, older])

    def test_home_query_never_filters_latest_and_public_fields_remain_safe(self):
        tennis = self.make_event('東京のテニス募集')
        other = self.make_event('<img src=x onerror=alert(1)>', sport='サッカー・フットサル', prefecture='大阪府',
                                bank_transfer_details='private-bank-details', target_total_amount=999999)
        result = self.app.latest_home_events()
        for event in result:
            for private in ('organizer_user_id', 'organizer_contact_email', 'bank_transfer_details', 'target_total_amount'):
                self.assertNotIn(private, event)
        page = self.app.render_sports_home_html({'sport':['テニス'], 'prefecture':['東京都'], 'region':['kanto']}).decode()
        self.assertIn('/events/' + quote(tennis), page)
        self.assertIn('/events/' + quote(other), page)
        self.assertNotIn('<img src=x onerror=alert(1)>', page)
        self.assertIn('&lt;img src=x onerror=alert(1)&gt;', page)
        for private in ('private-host@example.test', 'private-guest@example.test', 'private-bank-details', '999999'):
            self.assertNotIn(private, page)

    def test_successful_empty_home_keeps_entries_and_explicit_actions(self):
        page = self.home()
        self.assertIn('現在、募集中の大会・イベントはありません', page)
        self.assertNotIn('取得できませんでした', page)
        self.assertIn('スポーツから探す', page)
        self.assertIn('目的から探す', page)
        self.assertIn('href="/events/new?custom=1">募集を作る', page)
        self.assertIn('href="/events">現在募集中のイベントを見る', page)
        latest_section = re.search(r'<section\b[^>]*aria-labelledby="home-latest-heading"[^>]*>(.*?)</section>', page, re.S)
        self.assertIsNotNone(latest_section)
        self.assertEqual(latest_section.group(1).count('募集を作る</a>'), 1)

    def test_failed_query_preserves_home_without_false_empty_or_private_error(self):
        with patch.object(self.app, 'connect', side_effect=RuntimeError('private-db-error')) as connection:
            page = self.home()
            self.assertTrue(connection.called)
        self.assertIn('最新の募集を取得できませんでした', page)
        self.assertNotIn('現在、募集中の大会・イベントはありません', page)
        self.assertNotIn('0件', unescape(page))
        self.assertNotIn('private-db-error', page)
        self.assertIn('スポーツから探す', page)
        self.assertIn('目的から探す', page)
        self.assertIn('募集を作る', page)


if __name__ == '__main__':
    unittest.main(verbosity=2)
