"""Loopback-only visual audit: disposable data, no mail/payment/network writes."""
import base64
from html import escape
import json
from pathlib import Path
import threading
from urllib.parse import parse_qs, quote, urlencode, urlsplit

from test_event_flow import create_account, event_payload, user
from test_venues import IsolatedAppHttpCase

ROOT = Path(__file__).resolve().parents[1]


def main():
    fixture = IsolatedAppHttpCase
    fixture.setUpClass()
    done = threading.Event()
    try:
        app = fixture.app
        app.HOST_FEES_ENABLED = True
        app.ONLINE_PAYMENTS_ENABLED = False
        app.init_db()
        actors = {role: user('contrast-' + role, role + '@example.test', name)
                  for role, name in [('host', '確認用の主催者'), ('participant', '確認用の参加者'), ('visitor', '確認用の応募者')]}
        for actor in actors.values():
            create_account(app, actor)
        events = {}
        for stage in ['open', 'announced', 'cancelled']:
            data = event_payload('視認性確認 テニス交流会 / ' + stage, participation_type='both', capacity='')
            data.update(sport_category='テニス', minimum_participants=2, individual_fee_amount=2500,
                        team_fee_amount=15000, payment_method='on_site_or_bank_transfer')
            with app.connect() as conn:
                eid = app.save_event_post(conn, data, actors['host'])
            with app.connect() as conn:
                app.submit_event_application(conn, eid, dict(participation_type='individual', participant_count=2,
                    applicant_name='確認用参加者', payment_method='bank_transfer'), actors['participant'])
            if stage != 'open':
                with app.connect() as conn:
                    app.announce_event(conn, eid, dict(version=0, starts_at=data['starts_at'], location=data['location'],
                        announcement_details='入口に集合してください。テスト用の案内です。',
                        attendance_deadline='2030-05-28T18:00', payment_deadline='2030-05-30T18:00',
                        bank_transfer_details='テスト用口座・実在しません'), actors['host'])
                with app.connect() as conn:
                    app.confirm_event_attendance(conn, eid, dict(version=1, conditions_accepted=True), actors['participant'])
            if stage == 'cancelled':
                with app.connect() as conn:
                    app.set_event_status(conn, eid, 'cancelled', actors['host'])
            events[stage] = eid
        with app.connect() as conn:
            sessions = {role: app.create_user_session(conn, actor['user_id']) for role, actor in actors.items()}
        with app.connect() as conn:
            circle = conn.execute("select circle_id from circles where coalesce(public_status,'published')<>'demo' limit 1").fetchone()[0]
            invitation = app.invitations.create(conn, dict(target_circle_id=circle, kind='consultation',
                subject='合同練習のご相談', sender_label='確認用チーム', activity='合同練習',
                proposed_date='来月の週末', location='東京都内', body='交流のご相談です。'),
                actors['host'], app.public_circle_clause(), app.invitation_event)
        pages = {
            'home': ('anonymous', '/'), 'settings': ('anonymous', '/settings'),
            'signin': ('anonymous', '/signin'), 'events': ('anonymous', '/events'),
            'venues': ('anonymous', '/venues?v_q=' + urlencode({'q': '下高井戸区民集会所'})[2:]),
            'circles': ('anonymous', '/?tab=db&audience=social'),
            'guides': ('anonymous', '/guides'), 'guide': ('anonymous', '/guides/tokyo-venue-costs'),
            'terms': ('anonymous', '/terms'), 'privacy': ('anonymous', '/privacy'),
            'event': ('anonymous', '/events/' + events['open']),
            'cancelled': ('anonymous', '/events/' + events['cancelled']),
            'guest-entry': ('anonymous', '/events/' + events['open'] + '/guest'),
            'apply': ('visitor', '/events/' + events['open'] + '/apply'),
            'editor': ('host', '/events/new?event_id=' + events['open']),
            'mypage': ('host', '/mypage?tab=hosted'), 'notifications': ('host', '/notifications'),
            'security': ('host', '/settings/security'),
            'organize': ('host', '/events/' + events['announced'] + '/organize'),
            'applications': ('host', '/events/' + events['announced'] + '/applications'),
            'attendance': ('participant', '/events/' + events['announced'] + '/attendance'),
            'contact': ('participant', '/events/' + events['announced'] + '/contact'),
            'host-fee': ('host', '/events/' + events['announced'] + '/host-fee'),
            'payments': ('host', '/payments'), 'connect': ('host', '/payments/connect'),
            'invitation-compose': ('host', '/invitations/new?circle_id=' + circle),
            'invitation-list': ('host', '/invitations'),
            'invitation-detail': ('host', '/invitations/' + invitation),
            'invitation-public': ('anonymous', '/invitations/' + invitation),
            'admin-security': ('admin', '/admin/security'),
            'admin-payments': ('admin', '/admin/payments'),
            'admin-main': ('admin', '/admin'),
            'admin-research': ('admin', '/admin/contact-research'),
            'post-match': ('anonymous', '/post-match'),
            'representative': ('anonymous', '/representative'),
            'circle-search': ('anonymous', '/circles'),
            'social-search': ('anonymous', '/social/circles'),
            'regions': ('anonymous', '/regions'),
            'contact-page': ('anonymous', '/contact'),
            'operator': ('anonymous', '/operator'),
            'about-data': ('anonymous', '/about-data'),
        }

        class Handler(app.Handler):
            def do_GET(self):
                parsed = urlsplit(self.path)
                if parsed.path == '/__contrast__/stop':
                    self.send_html(b'Preview stopped')
                    done.set()
                    return
                if parsed.path.startswith('/__contrast__/page/'):
                    key = parsed.path.rsplit('/', 1)[-1]
                    if key not in pages:
                        self.send_json({'error': 'unknown preview'}, 404)
                        return
                    role, target = pages[key]
                    cookie = 'cm_session=' + sessions.get(role, '') + '; Path=/; HttpOnly; SameSite=Lax'
                    if role == 'admin':
                        target += ('&' if '?' in target else '?') + '__contrast_admin=1'
                    self.redirect(quote(target, safe='/?=&%'), [cookie])
                    return
                if (parsed.path == '/admin' or parsed.path.startswith('/admin/')) and parse_qs(parsed.query).get('__contrast_admin') == ['1']:
                    token = base64.b64encode((app.ADMIN_USERNAME + ':' + app.ADMIN_PASSWORD).encode()).decode()
                    self.headers['Authorization'] = 'Basic ' + token
                if parsed.path == '/__contrast__':
                    links = ''.join('<li><a href="/__contrast__/page/' + key + '">' + escape(key) + '</a></li>' for key in pages)
                    self.send_html(app.event_page('視認性チェック', '<h1>視認性チェック</h1><ul>' + links + '</ul>').encode())
                    return
                super().do_GET()

            def do_POST(self):
                self.send_json({'error': 'read-only visual preview'}, 405)

        fixture.server.RequestHandlerClass = Handler
        work = ROOT / 'work/contrast-audit-20261105'
        work.mkdir(parents=True, exist_ok=True)
        manifest = dict(base=fixture.base, pages={key: fixture.base + '/__contrast__/page/' + key for key in pages},
                        local_only=True, outgoing_network=False, writes_via_http=False)
        (work / 'preview.json').write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
        print('PREVIEW_URL=' + fixture.base + '/__contrast__', flush=True)
        done.wait()
    finally:
        fixture.doClassCleanups()


if __name__ == '__main__':
    main()
