# Public Delivery Cost Controls

## Scope

Public venue catalogs, public assets and strictly cookie-free public listing
HTML are cacheable. Personal HTML,
login, guest verification, applications, bank details, payments and webhooks
retain their existing no-store/authentication/CSRF behavior. No billing plan,
environment variable, database schema or runtime service configuration changes.

The venue UI requests `/api/venues?view=page&limit=50&offset=0`. Existing
server-side filters and ordering run before pagination; later pages are fetched
only on demand. Search cancels obsolete requests so slow responses cannot replace
newer results. The legacy complete catalogs remain compatible with research
tools. Without JavaScript or when the API fails, server-rendered results remain.

Venue JSON uses `public, max-age=300, must-revalidate` and a content-derived ETag.
Public assets keep their one-day TTL and gain ETag revalidation. An unchanged
conditional GET returns 304 with no response body. New catalog content changes
the tag; the maximum browser freshness period is five minutes. This does not
enable Render's optional edge-cache setting or cache personalized pages.

Cookie-free public listing HTML has a 60-second cache TTL and conditional GETs,
with `Vary: Cookie, Authorization, Accept-Encoding`. Any Cookie or Authorization
header keeps the original no-store response and disables this HTML compression
path. Forms, account pages, guest links and event details are never included.
Anonymous listings use deterministic gzip where accepted, reducing origin
transfer as well as the existing edge compression. Private responses are not
compressed by this code.

The initial all-sports response measured with the same local gzip settings:

| Response | JSON bytes | gzip bytes |
|---|---:|---:|
| Complete catalog | 6,476,653 | 370,814 |
| First 50 results | 213,899 | 25,418 |

The compressed payload reduction is 93.1%, not a guarantee of the same reduction
in the whole Render bill. HTML, images and other requests also consume bandwidth.

## Bounded Catalog Requests

On Render only, in-memory token buckets permit 30 complete-catalog requests per
minute or 240 paginated-catalog requests per minute per observed client address.
The buckets allow an initial burst, refill continuously, and retain at most
4,096 entries. Excess requests receive a no-store 429 and Retry-After. Only the
two public catalog GET routes enter this limiter: login, applications, payment
callbacks, health checks and other APIs cannot be rejected by it.

The observed address is used only in bounded process memory, not logged. This
best-effort cost guard is not an authentication or bot identity mechanism.
Shared networks may share a bucket. No new CAPTCHA, login condition or global
service traffic cap is introduced. Cloudflare's overwritten CF-Connecting-IP is
preferred on Render; an unambiguous single X-Forwarded-For address is the
fallback. Ambiguous/missing proxy identity fails open instead of treating every
visitor as the same proxy client. Local test servers do not trust these headers.

After the first deployment, the first complete 60-second log window contained
87 self-declared crawler requests to `/` and other public pages, accounting for
8,696,580 uncompressed body bytes. Release-check traffic was separately labeled.
This is evidence of a large crawler contribution in that window, not proof of
every historical charge or a verified bot identity.

The follow-up limits self-declared non-search crawlers on cookie-free public
listing GETs to 20/minute per declared family across the single service instance.
The first follow-up logs identified the dominant family as self-declared Meta
crawlers; a family-wide budget also covers their distributed source addresses.
This attribution is user-agent based, not independent ownership verification.
Ordinary browsers,
authenticated/cookie-bearing requests, Google/AdSense, Bing and Apple crawlers,
event details, login submissions, authentication APIs, applications and payment
routes bypass that limiter.
Robots rules discourage duplicate free-text/filter/sort/offset URLs already
excluded from indexing; canonical listings, event details and sitemap stay open.
Crawler family labels are fixed categories and do not retain raw user agents.

## Diagnostics

`delivery_summary` JSON lines in existing Render application logs aggregate
request counts and application response-body bytes every 60 seconds, on traffic.
Only fixed route groups, numeric statuses and coarse client classes are emitted.
No query strings, event IDs, IP addresses, emails, cookies, credentials, request
bodies, referrers or raw user-agent strings are logged. Arbitrary paths and asset
extensions map to fixed `other` groups. A failed log write cannot fail a request.

`body_bytes` counts the application response body as sent (gzip bytes for
compressed anonymous HTML, otherwise uncompressed bytes), not Render's metered
byte total. The edge may compress or transform it further.
Client classes are hints from self-declared user agents, not verified identity.
Browser-driven Codex actions cannot reliably be distinguished from real browsers.
Use the aggregate to rank routes; compare trends against Render billing metrics.

## Codex Scheduled-Run Investigation (2026-11-05)

Read-only inspection found the following active Circle Match automations:

- Venue tariff research: once daily.
- Public contact research: once daily.
- University circle DB collection: once daily.

The older mail-setup continuation is paused. No matching Windows scheduled task
or currently running Circle Match/monitor/verification process was found at the
inspection time. This is a snapshot, not proof that no past process existed.

Existing venue/contact verification scripts default to loopback disposable
servers; production runs require an explicit target override. They have bounded
startup waits and terminate their own server. The GitHub admin check runs on
main pushes, polls the small health endpoint at most every 20 seconds for 15
minutes, then makes bounded access checks. It is not an endless monitor.

The contact research inventory downloads at most 200 records per page, stops at
the last page, and reuses a saved snapshot. It can contribute some production
traffic, as can visual release verification, but these findings alone do not
attribute the persistent approximately 3-5 GB/day to Codex. Historical path/client
logs were unavailable; do not infer attribution from daily schedules alone.
No automation is stopped, deleted or rescheduled by this change.

## Verification and Release

Run `python -m unittest discover -s scripts -p 'test_*.py' -q`, including
`test_delivery.py`. The added tests cover 304s, credential-independent public
content, pagination/filter equivalence, unchanged full catalogs, private no-store
responses, limiter isolation/refill/memory bounds, and log redaction/failure.

Verify desktop/mobile search, reset, incremental paging, guest entry, member
application and organizer bank instructions using disposable local data. After
the matching main commit is Live, make bounded read-only production checks of
catalog headers, 304s, the event page and anonymous login/application boundaries.
Do not submit a production application, send verification mail or create payment.

Persistent-disk Render deploys can briefly interrupt connections at rollout;
this change cannot promise zero downtime. Sessions and application data stay on
the existing disk. The first rollout enabled diagnostics; the follow-up responds
to newly observed crawler traffic without changing any service configuration.

## Additional Public Delivery Controls (2026-11-07)

A later 601-second live aggregate still showed 522 Meta-declared successful
responses in the coarse `/other` group, carrying 20,300,134 application body
bytes. This group was not sufficient to identify each actual path. The follow-up
therefore extends the explicit public-document allowlist to legal/information
pages and single-segment published circle profiles and guides, not arbitrary
paths or a generic catch-all. They share the existing non-search crawler-family
budget with listings, rather than each gaining a fresh budget. Fixed log groups
now separate policies, event listings and circle profiles without recording IDs
or query strings. Ordinary browsers, cookie/authorization-bearing requests,
search/ad crawlers and every event detail/application route remain exempt.

Cookie-free successful public information pages and guides gain the existing
60-second cache TTL, encoding-specific ETags and deterministic gzip. Circle
profiles use `max-age=0, must-revalidate` so each request rechecks publication and
contact consent. Failed/unpublished profiles never return a cached 304.
Cookie-bearing and authorization-bearing HTML retains
no-store and remains outside this compression path. No event, invitation,
account, notification, bank, payment or authentication response enters it.

Already-public venue JSON and textual static assets also negotiate gzip, with
`Vary: Accept-Encoding` on both compressed and identity responses. Their ETags
identify the bytes of the selected representation; a compressed validator does
not suppress a different identity response. PNG and other binary assets are not
recompressed. Existing full-catalog compatibility and pagination are unchanged.

Use `python -m unittest discover -s scripts -p 'test_delivery*.py' -q` for the
focused contracts and the full `test_*.py` suite for application regressions.
`scripts/check_public_delivery.py --base-url <origin> --expected-commit <sha>`
makes a fixed set of read-only requests, downloads only 50 venue rows, checks
304/body-zero behavior and private-route cache boundaries, and writes a
credential-free report. It never loops over catalogs, signs in, applies, sends
mail or creates a Checkout session. Use disposable local data for authenticated
and guest-flow tests; do not submit test applications to production.

Application byte savings are not a bill estimate: Render's edge may already
compress responses. Compare subsequent Render bandwidth metrics over complete,
comparable time windows before extrapolating any further monthly savings.

The first follow-up's expanded fixed log groups resolved the former `/other`
traffic to non-search crawlers repeatedly fetching `/signin` and `/settings`.
These two **GET screen routes only** now share the same crawler-family budget.
They are not added to the cache/compression allowlist: even anonymous entry
screens keep no-store. Ordinary browser agents, all Cookie/Authorization-bearing
requests, Google/AdSense/Bing/Apple and every authentication API, OAuth callback,
POST, event/application/payment route bypass this crawler guard. Robots rules
also discourage indexing these two non-content screens. This is neither a human
login throttle nor a change to login eligibility, sessions or form submission.
