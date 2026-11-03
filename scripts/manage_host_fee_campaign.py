"""Render Shell-only campaign management. Never initializes or migrates the DB."""
import argparse
from contextlib import contextmanager
from dataclasses import replace
import json
import os
from pathlib import Path
import sqlite3
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'outputs'))
import circlematch_fee_campaign as campaign
from circlematch_host_billing import Billing
from circlematch_payments import Config, Payments, PaymentError


def existing_database(path, *, readonly):
    path = Path(path)
    if not path.is_absolute() or not path.is_file():
        raise ValueError('An existing absolute CIRCLEMATCH_DB_PATH is required')

    @contextmanager
    def connect():
        conn = sqlite3.connect(path.as_uri() + ('?mode=ro' if readonly else '?mode=rw'), uri=True, timeout=15)
        conn.row_factory = sqlite3.Row
        conn.execute('pragma foreign_keys=on')
        try:
            with conn:
                yield conn
        finally:
            conn.close()
    return connect


def run(command, connect, *, revision=None, confirm=False, actor='render-shell', config=None, gateway=None, app=None):
    if command not in {'status', 'on', 'off'}:
        raise ValueError('Unknown command')
    if command == 'status':
        with connect() as conn:
            return campaign.status(conn)
    if type(revision) is not int or revision < 0 or (command == 'on' and confirm is not True):
        raise PaymentError('Current revision and explicit ON confirmation are required')
    if not actor or len(actor) > 80 or any(ord(char) < 32 for char in actor):
        raise ValueError('Invalid operator label')
    if app is None:
        import circlematch_db_app as app
    # This is organizer billing only; participant/Connect flags are not changed.
    config = replace(config or Config.env(), enabled=command == 'on', live_approved=True)
    payments = Payments(connect, app.add_event_notification, config, gateway)
    if command == 'on':
        config.validate_new_payments()
        payments.platform_check(accepting_payments=True)
    with connect() as conn:
        conn.execute('begin immediate')
        before = campaign.status(conn)
        current = campaign.change(conn, dict(enabled=command == 'on', revision=revision, accepted=confirm))
        if current['revision'] != before['revision']:
            app.audit(conn, 'host_fee_campaign_change', 'app_state', campaign.KEY,
                dict(enabled=current['enabled'], revision=current['revision'], actor=actor, source='render_shell'))
    if command == 'off':
        Billing(connect, payments, app.add_event_notification).stop_open_checkouts()
    with connect() as conn:
        return campaign.status(conn)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['status', 'on', 'off'])
    parser.add_argument('--expected-revision', type=int)
    parser.add_argument('--confirm-new-events-only', action='store_true')
    parser.add_argument('--actor', default='render-shell', help='Operator label for the existing audit log')
    args = parser.parse_args(argv)
    try:
        if args.command != 'status' and os.getenv('CIRCLEMATCH_HOST_FEES_ENABLED') != 'true':
            raise PaymentError('Organizer billing is not enabled on this service')
        connect = existing_database(os.getenv('CIRCLEMATCH_DB_PATH', ''), readonly=args.command == 'status')
        result = run(args.command, connect, revision=args.expected_revision,
            confirm=args.confirm_new_events_only, actor=args.actor)
        ok = result['valid'] and not result['stopping']
        print(json.dumps(dict(ok=ok, command=args.command, campaign=result), ensure_ascii=False, indent=2))
        return 0 if ok else 3
    except Exception as error:
        # Provider errors can contain credential fragments; never print their text.
        print(json.dumps(dict(ok=False, error_type=type(error).__name__,
            error='Operation not completed. Check revision, explicit ON confirmation, configuration and pending payments.')))
        return 2


if __name__ == '__main__':
    raise SystemExit(main())
