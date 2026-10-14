"""Operator tooling; test mode and an explicitly named DB by default.

Never starts the site's maintenance/seed importer or email sender.
"""
import argparse
import importlib.util
import json
import os
from pathlib import Path


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument("--database",type=Path,required=True)
    parser.add_argument("--actor",required=True,help="Operator audit identifier, not a credential")
    parser.add_argument("--allow-live",action="store_true",help="Only after explicit production approval")
    parser.add_argument("command",choices=["status","migrate","tick","reconcile","replay","recover-order","recover-account"])
    parser.add_argument("identifier",nargs="?")
    parser.add_argument("stripe_id",nargs="?")
    args=parser.parse_args()
    if not args.database.is_file():
        parser.error("Specify an existing isolated SQLite database")
    if os.getenv("CIRCLEMATCH_STRIPE_MODE","test") != "test" and not args.allow_live:
        parser.error("Live operations require a separate approval and --allow-live")
    os.environ["CIRCLEMATCH_DB_PATH"]=str(args.database.resolve())
    os.environ["CIRCLEMATCH_EMAIL_NOTIFICATIONS_ENABLED"]="false"
    spec=importlib.util.spec_from_file_location("circlematch_ops",Path(__file__).resolve().parents[1]/"outputs"/"circlematch_db_app.py")
    app=importlib.util.module_from_spec(spec);spec.loader.exec_module(app)
    service=app.payment_service()
    if service.config.mode=="live" and not service.config.live_approved:
        parser.error("Production approval switch is not enabled")
    if args.command=="migrate":
        with app.connect() as conn:app.online_payments.migrate(conn,args.database)
    elif args.command=="status":
        with app.connect() as conn:
            result={table:[dict(r) for r in conn.execute("select state,count(*) as count from "+table+" group by state")]
                    for table in ("payment_orders","payment_refunds","payment_webhooks")}
        print(json.dumps(result,ensure_ascii=False,indent=2))
    elif args.command=="tick":
        service.tick()
    else:
        if not args.identifier:parser.error("identifier is required")
        if args.command=="reconcile":service.reconcile(args.identifier)
        elif args.command=="replay":service.replay_webhook(args.identifier,args.actor)
        elif args.command=="recover-order":
            if not args.stripe_id:parser.error("Existing Checkout Session ID is required")
            service.recover_order(args.identifier,args.stripe_id,args.actor)
        elif args.command=="recover-account":
            if not args.stripe_id:parser.error("Existing connected account ID is required")
            service.recover_account(args.identifier,args.stripe_id,args.actor)
    print("Completed. No email sender was started.")


if __name__=="__main__":
    main()
