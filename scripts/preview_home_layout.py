"""Loopback-only layout fixture: disposable DB, fake login, no external sends."""
import threading

from test_home_latest_events import HomeLatestEventTests


def main():
    HomeLatestEventTests.setUpClass()
    HomeLatestEventTests.app.init_db()
    case = HomeLatestEventTests()
    try:
        case.setUp()
        for index, sport in enumerate(('テニス', 'サッカー・フットサル', 'バスケットボール')):
            case.make_event('【表示テスト】' + sport + ' 初心者歓迎の交流会', sport=sport,
                            published_at=f'2028-12-{index + 1:02}T10:00:00+09:00',
                            participation_type='both', fee_amount=2500, individual_fee_amount=2500,
                            team_fee_amount=15000, capacity=None, payment_method='bank_transfer', allow_on_site_payment=1)
        done = threading.Event()
        with case.app.connect() as conn:
            session = case.app.create_user_session(conn, case.host['user_id'])
            participant = case.app.create_user_session(conn, case.guest['user_id'])

        class PreviewHandler(case.app.Handler):
            def do_GET(self):
                if self.path in {'/preview/signin', '/preview/participant'}:
                    self.send_response(302)
                    self.send_header('Location', '/')
                    chosen = participant if self.path == '/preview/participant' else session
                    self.send_header('Set-Cookie', 'cm_session=' + chosen + '; Path=/; HttpOnly; SameSite=Lax')
                    self.send_header('Content-Length', '0')
                    self.end_headers()
                    return
                if self.path == '/preview/stop':
                    self.send_html(b'Preview stopped')
                    done.set()
                    return
                super().do_GET()

        case.server.RequestHandlerClass = PreviewHandler
        print('PREVIEW_URL=' + case.base, flush=True)
        done.wait()
    except KeyboardInterrupt:
        pass
    finally:
        case.doCleanups()
        HomeLatestEventTests.doClassCleanups()


if __name__ == '__main__':
    main()
