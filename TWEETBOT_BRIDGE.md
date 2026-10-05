# Optional Tweet-Bot Generation Bridge

The owner approved sharing this existing Starter host and disk on 2026-10-04.
The normal application, database, email worker, port, and start command remain
unchanged. No new Render service or paid OpenAI API fallback is added.

The isolated `/_tweet-bot/` routes are POST-only and require a 256-bit random
`TWEETBOT_BRIDGE_KEY`. `TWEETBOT_BRIDGE_ENABLED=true` opts in. All other requests
continue to use the existing handler. These routes do not use Circle Match
cookies, administrator credentials, user data, or database tables.

OAuth registration, rotating tokens, and a bounded generation ledger live under
`/var/data/tweet-bot/auth` (directory 0700; files 0600). Never commit, expose, or
log that directory. `/bootstrap` accepts a selected, already-validated local
session exactly once over authenticated TLS. The host keeps its own opaque ID.
The local owner retires the transferred session so refreshes only happen here.
`/status` returns readiness/model only, never tokens. `/generate` serializes
inference, reserves an attempt before calling OpenAI, caps attempts at eight per
Japan calendar day, and caches identical completed requests for that day.
Partial, failed, or interrupted attempts do not become publishable text.

X credentials, the three-post/day cap, budget accounting, duplicate checks,
source freshness, and metrics remain in the private tweet-bot repository and
GitHub Actions. This server returns draft text and can opt into the clock below.

`outputs/chatgpt_plan.py` and `outputs/chatgpt_bridge.py` are deployment copies
of the same named modules maintained and tested in tweet-bot. Keep them in sync
when updating the bridge. A Linux file lock releases automatically on process
exit so deployments cannot strand a token refresh lock.

Emergency stop: set `TWEETBOT_BRIDGE_ENABLED=false` and redeploy. Stop publication
independently with GitHub's `SPORTS_GROWTH_ENABLED=false`. Disabling this bridge
does not change Circle Match's normal routes. Restoring only the previous
application revision also removes the routes without removing either database.

## Approved Render Clock (2026-10-06)

GitHub cron deliveries were hours late and missed the posting grace period.
The owner approved using this existing always-on Starter service to dispatch
the existing `tweet-bot/growth.yml` workflow, without new contracts or top-ups.

- `TWEETBOT_SCHEDULER_ENABLED=true` enables a small thread started beside the
  existing email worker. It checks the JST clock every 15 seconds.
- `TWEETBOT_GITHUB_DISPATCH_TOKEN` must be a dedicated fine-grained token, selected
  repository `tweet-bot` only, Actions read/write plus mandatory Metadata read.
  No Contents, Secrets, account-wide or other-repository permissions. GitHub
  does not offer a narrower workflow-dispatch-only permission.
- Calls only the hardcoded GitHub workflow URL on `main`, `mode=run`,
  `source=render`. It cannot choose another URL or publish directly to X.
- Targets are 07:30/08:30, 12:10/13:10, 21:15/22:15 JST. The second in each pair
  is recovery/metrics collection, not an extra post. A restart catches up only
  within ten minutes. GitHub runner startup can still delay actual publication.
- A separate SQLite ledger in `/var/data/tweet-bot/scheduler` commits each claim
  before dispatch. Duplicate processes/restarts cannot dispatch a slot twice.
  Timeouts and ambiguous responses are retained, not automatically retried.
- Authenticated `/scheduler_status` returns worker status and bounded receipts,
  never credentials. `/scheduler_probe` dispatches one `preview` per JST day,
  without any X or AI API calls. It shares existing bridge authentication.
- `SPORTS_GROWTH_ENABLED=false` on GitHub blocks Render-triggered jobs too.
  Set `SPORTS_GROWTH_SCHEDULER=render` only after live verification to disable
  the old GitHub cron path. Manual diagnostics remain available.

No user data or Circle Match database is accessed. Keep `tweetbot_scheduler.py`
and `chatgpt_bridge.py` synchronized with the canonical copies in tweet-bot.
To stop the clock itself, disable `TWEETBOT_SCHEDULER_ENABLED` and redeploy.
Never log the token or store a broad existing Git login on this server.
