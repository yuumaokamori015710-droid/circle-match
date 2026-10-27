"""Temporary loopback-only fixture. No production login or external notification."""
import tempfile
from http.server import ThreadingHTTPServer
from pathlib import Path

from test_event_flow import load_app, user, create_account, event_payload


def main():
    with tempfile.TemporaryDirectory() as directory:
        app = load_app(Path(directory) / "payment-preview.sqlite")
        app.EMAIL_NOTIFICATIONS_ENABLED = False
        app.init_db()
        roles = {role: user("qa-choice-" + role, role + "@example.test", "QA " + role)
                 for role in ("host", "individual-cash", "individual-bank", "team-cash", "team-bank")}
        sessions = {}
        for role, account in roles.items():
            create_account(app, account)
            with app.connect() as conn:
                sessions["/qa/" + role] = app.create_user_session(conn, account["user_id"])
        data = event_payload("QA payment choices", participation_type="both", capacity="")
        data.update(individual_fee_amount=2500, team_fee_amount=15000, minimum_participants=1,
                    payment_method="on_site_or_bank_transfer")
        with app.connect() as conn:
            event_id = app.save_event_post(conn, data, roles["host"])

        class PreviewHandler(app.Handler):
            def do_GET(self):
                if self.path in sessions:
                    target = "/events/new?event_id=" + event_id if self.path == "/qa/host" else "/events/" + event_id + "/apply"
                    self.redirect(target, [f"cm_session={sessions[self.path]}; Path=/; HttpOnly; SameSite=Lax"])
                    return
                super().do_GET()

        with ThreadingHTTPServer(("127.0.0.1", 0), PreviewHandler) as server:
            print(f"QA_ORIGIN=http://127.0.0.1:{server.server_port}", flush=True)
            print(f"QA_EVENT={event_id}", flush=True)
            try:
                server.serve_forever()
            except KeyboardInterrupt:
                pass


if __name__ == "__main__":
    main()
