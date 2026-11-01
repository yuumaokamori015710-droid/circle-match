"""Disposable owner-only fee proposal; no real charges, credentials or email."""
from http.server import ThreadingHTTPServer
import json
import os
from pathlib import Path
import tempfile
from urllib.parse import quote, urlsplit

ROOT = Path(__file__).resolve().parents[1]
WORK = ROOT / 'work/organizer-fee-preview'
os.environ.update(CIRCLEMATCH_HOST_FEES_ENABLED='true', CIRCLEMATCH_ONLINE_PAYMENTS_ENABLED='false',
                  CIRCLEMATCH_EMAIL_NOTIFICATIONS_ENABLED='false', CIRCLEMATCH_EMAIL_AUTH_ENABLED='false',
                  CIRCLEMATCH_SUPABASE_URL='', CIRCLEMATCH_SUPABASE_ANON_KEY='', CIRCLEMATCH_RESEND_API_KEY='',
                  CIRCLEMATCH_GOOGLE_CLIENT_ID='', CIRCLEMATCH_GOOGLE_CLIENT_SECRET='',
                  CIRCLEMATCH_SITE_BASE_URL='http://127.0.0.1:8930', CIRCLEMATCH_SESSION_SECRET='local-owner-fee-preview')
from test_event_flow import load_app, user, create_account, event_payload


def main():
    WORK.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='preview-', dir=WORK) as folder:
        app = load_app(Path(folder) / 'preview.sqlite')
        app.init_db()
        app.HOST_FEES_ENABLED = True
        app.ADSENSE_HEAD = ''
        app.LOG_PATH = WORK / 'preview.log'
        app.EMAIL_NOTIFICATIONS_ENABLED = False
        host = user('fee-preview-host', 'host@example.test', 'プレビュー主催者')
        guest = user('fee-preview-guest', 'guest@example.test', 'プレビュー参加者')
        team = user('fee-preview-team', 'team@example.test', 'プレビューチーム')
        for account in [host, guest, team]:
            create_account(app, account)
        events = {}
        for stage in ['pending', 'announced', 'cancelled', 'free']:
            payload = event_payload('駒沢イレブンカップ / 利用料確認用 ' + stage, capacity='')
            payload.update(sport_category='サッカー・フットサル', participation_type='both', individual_fee_amount=0 if stage == 'free' else 2500,
                           team_fee_amount=0 if stage == 'free' else 15000, minimum_participants=2,
                           payment_method='on_site', starts_at='2026-12-25T17:00', ends_at='2026-12-25T19:00',
                           application_deadline='2026-12-23T17:00', location='駒沢公園補助競技場',
                           description='ローカル検証用の募集です。実際の大会への申込・支払いは発生しません。')
            payload.update(host_fee_accepted=True, host_fee_policy_version=app.host_fees.POLICY_VERSION)
            with app.connect() as conn:
                eid = app.save_event_post(conn, payload, host)
            for account, kind, number in [(guest, 'individual', 2), (team, 'team', 11)]:
                with app.connect() as conn:
                    app.submit_event_application(conn, eid, dict(participation_type=kind, participant_count=number,
                        applicant_name='プレビュー参加者', representative_name='プレビュー代表', team_name='テストFC'), account)
            if stage != 'pending':
                with app.connect() as conn:
                    app.announce_event(conn, eid, dict(version=0, starts_at='2026-12-25T17:00',
                        location='駒沢公園補助競技場', announcement_details='入口集合。ローカルの検証データです。',
                        attendance_deadline='2026-12-24T17:00'), host)
                with app.connect() as conn:
                    conn.execute("update event_applications set payment_status='paid' where event_id=?", (eid,))
            if stage == 'cancelled':
                with app.connect() as conn:
                    app.set_event_status(conn, eid, 'cancelled', host)
            events[stage] = eid
        with app.connect() as conn:
            sessions = {name: app.create_user_session(conn, account['user_id']) for name, account in [('host', host), ('guest', guest)]}
        (WORK / 'preview.json').write_text(json.dumps(dict(base='http://127.0.0.1:8930', events=events,
            host_url='http://127.0.0.1:8930/__preview__/host', local_only=True, actual_billing=False), ensure_ascii=False, indent=2), encoding='utf-8')

        class Handler(app.Handler):
            def cookie_value(self, name):
                return super().cookie_value('cm_fee_preview_session' if name == 'cm_session' else name)

            def redirect(self, location, cookies=None):
                super().redirect(location, [value.replace('cm_session=', 'cm_fee_preview_session=', 1)
                                            for value in cookies or []])

            def do_GET(self):
                path = urlsplit(self.path).path
                if path == '/__preview__/host':
                    self.redirect('/events/' + quote(events['announced'], safe='') + '/host-fee',
                                  [f'cm_session={sessions["host"]}; Path=/; HttpOnly; SameSite=Lax'])
                    return
                if path == '/__preview__/guest':
                    self.redirect('/events/' + quote(events['announced'], safe=''),
                                  [f'cm_session={sessions["guest"]}; Path=/; HttpOnly; SameSite=Lax'])
                    return
                super().do_GET()

        with ThreadingHTTPServer(('127.0.0.1', 8930), Handler) as server:
            print('Host-only proposal: http://127.0.0.1:8930/__preview__/host', flush=True)
            server.serve_forever()


if __name__ == '__main__':
    main()
