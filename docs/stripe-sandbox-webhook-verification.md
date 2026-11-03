# Isolated Stripe Webhook Verification

This opt-in receiver verifies provider delivery without writing to the Circle Match
application database or enabling live collection. It is not an alternative payment
processor or proof that an application order has been paid.

## Boundaries

- POST `/api/payments/sandbox-verification/webhook` is disabled by default (410).
- It requires a dedicated `whsec_` signature, a restricted test key, an exact
  `cs_test_` Checkout Session ID, and a future deadline no more than six hours away.
- Both live collection flags must remain false. Existing live webhook signatures
  cannot be reused for this receiver.
- Only own-account, test-mode `checkout.session.completed` snapshots for that exact
  session, with `metadata.purpose=circlematch_qa_only`, are accepted.
- Raw bytes are verified with the Stripe SDK, its 300-second signature tolerance,
  and a 64 KiB request limit. No payload, customer details, key, or signature is stored.
- Routing IDs, timestamps and counters go only to a session-specific SQLite file
  in the system temporary directory. The application DB and its schema are untouched.
- Event IDs and the event-type/session pair are deduplicated. Receiving a notification
  queues verification and returns promptly; it makes no Stripe write API calls.
- A private, explicit reconciliation reads the Session and expanded intent/charge
  through the existing restricted sandbox key. It requires complete/paid, captured
  JPY 500, no refund, and an authenticated 3DS challenge. It does not post a real order.

## Temporary Configuration

Set only on the existing Render `circle-match` service:

| Variable | Meaning |
| --- | --- |
| `CIRCLEMATCH_STRIPE_QA_WEBHOOK_SECRET` | New sandbox destination's signing secret |
| `CIRCLEMATCH_STRIPE_QA_WEBHOOK_UNTIL` | UTC Unix-seconds deadline, at most six hours away |
| `CIRCLEMATCH_STRIPE_QA_CHECKOUT_SESSION` | Exact previously verified test Session ID |
| `CIRCLEMATCH_STRIPE_QA_SECRET_KEY` | Existing dedicated restricted test key; do not broaden permissions |

Never place secret values in Git, a local fixture, a command argument, or a public
status page. Keep live platform/Connect webhook secrets and all unrelated variables
unchanged. A configuration save is not active until its Render deployment is Live.

## Verification And Shutdown

1. Deploy the disabled route and confirm its HTTP 410 response.
2. Register one snapshot destination in the existing sandbox account, own-account
   scope, subscribing only to `checkout.session.completed`. Use the pinned API
   version from `circlematch_payments.API_VERSION`.
3. Save the three temporary variables on the existing Render service and wait for
   that settings deployment to become Live.
4. Use Stripe Workbench to send/resend the actual successful test Checkout event.
   Preserve the issued Checkout URL verbatim, including its fragment, if needed.
5. Confirm a successful provider delivery and run the private reconciliation once:

   ```sh
   python -c 'import sys,json; sys.path.insert(0,"outputs"); import circlematch_stripe_qa as q; print(json.dumps({"checks":q.reconcile(),"report":q.report()}))'
   ```

6. Resend the same event, rerun reconciliation, and confirm deliveries increased
   while the verified receipt and processing count remain one. Capture the provider
   delivery result and private counters without customer payloads or secret values.
7. Disable the sandbox destination. Set the temporary deadline to `0` (and clear
   the temporary signing-secret value), wait for the settings deploy, and confirm
   HTTP 410. Leave live collection flags false until separately approved for launch.

Unit/HTTP tests use isolated temporary DBs and fake keys, but the actual Stripe SDK
for signature verification. They cover invalid signatures, stale signatures, wrong
mode/session/account/purpose, expiry, duplicate IDs and duplicate object events,
read-only reconciliation, private payload handling and application-DB isolation.

Primary references: [Stripe webhooks](https://docs.stripe.com/webhooks),
[Render environment variables](https://render.com/docs/configure-environment-variables).
