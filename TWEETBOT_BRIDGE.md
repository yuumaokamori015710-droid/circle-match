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

X credentials, schedules, the three-post/day cap, budget accounting, duplicate
checks, source freshness, and metrics remain in the private tweet-bot repository
and GitHub Actions. This server returns draft text only.

`outputs/chatgpt_plan.py` and `outputs/chatgpt_bridge.py` are deployment copies
of the same named modules maintained and tested in tweet-bot. Keep them in sync
when updating the bridge. A Linux file lock releases automatically on process
exit so deployments cannot strand a token refresh lock.

Emergency stop: set `TWEETBOT_BRIDGE_ENABLED=false` and redeploy. Stop publication
independently with GitHub's `SPORTS_GROWTH_ENABLED=false`. Disabling this bridge
does not change Circle Match's normal routes. Restoring only the previous
application revision also removes the routes without removing either database.
