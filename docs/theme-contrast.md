# Text Visibility Audit: 2026-11-05

## Scope

This change fixes foreground/background collisions without changing layouts,
the original logo, venue/circle records, fees, admission rules, notification
logic, authentication, environment variables, database schemas or Render plans.
It is isolated from the existing unpublished responsive-layout worktree.

`outputs/club_static/contrast.css` loads after component styles. It supplies
paired semantic colors for the Club Edit dark theme and small token corrections
for legacy light pages. Assets retain SHA-256 cache-versioned URLs. No content
is hidden to make an audit pass. Disabled controls retain native disabled state
and cursor but no longer become needlessly faint.

## Findings and Corrections

| Surface | Observed failure before fix | Correction |
| --- | --- | --- |
| Settings display choices | White text on white/near-white background, about 1.02–1.10:1 | Dark surface and explicit readable text for default/checked/hover states |
| Settings helper copy | Dark blue copy on dark background, about 3.89:1 | Shared muted text; readable saved-state feedback |
| Settings save button | White on orange, about 3.70:1 | Existing Club Edit lime action with dark text |
| Invitation creation, list, recipient and conversation | Local white panels inherited dark-theme white headings, links and body copy | Theme-paired panels, labels, notes, errors and primary/withdrawal actions |
| Organizer campaign exemption | Pale green panel with inherited white heading and pale copy, about 1.02–1.78:1 | Dark green information panel and explicit readable foreground |
| Payments / admin totals | Dark definition-list labels on dark background, about 2.51:1 | Muted text tokens and distinct separators |
| Directory labels and venue loading/skip states | Old label ID rule and pale loading backgrounds overrode the shared theme | Explicit directory label and message-panel pairs |
| Legacy representative, circle search and regions | White/orange actions about 3.66:1; small muted copy about 4.21–4.49:1 | Darker action/muted tokens, without changing the white layouts |

## Verification

- Entire existing unittest discovery: **696 tests, OK, 31 optional crawler
  tests skipped because lxml is unavailable**. Final focused theme run: 7/7.
- Added `scripts/test_theme_contrast.py`: paired-color ratios, control edges,
  cache-versioned stylesheet order, legacy light-page integration, read-only
  public asset behavior, and scope guards.
- `scripts/preview_contrast.py` provides 41 real page/role combinations using
  disposable SQLite, loopback HTTP only, blocked outbound requests, and disabled
  HTTP mutations. It never starts the production mail/payment workers.
- `scripts/audit_text_contrast.js` is a read-only computed-style audit, including
  alpha backgrounds, inherited colors, placeholders, control text and font size.
  Threshold comparisons use unrounded values.
- Desktop 1440x1000: **41 pages, 5,207 text samples, zero failing samples**.
- Mobile 390x844: **41 pages, 5,137 text samples, zero failing samples**.
- Neither matrix had horizontal page overflow. Covered public home/events,
  settings, sign-in, venues, circle search, guides/legal/operator pages,
  representative forms, member application, organizer editing/announcement,
  notifications/security, attendance/bank instructions, messaging, payments,
  host-fee exemption, invitations and local admin views.
- Additional interactions: checked settings choices and saved feedback,
  event-editor conditions and publication preview, individual/team/payment
  choices, application confirmation and forced local server-error message.
  No production application, invitation, charge or email was created.
- Narrow 320x844 checks additionally covered settings, invitation creation,
  event editing, participant application and venue search: zero text failures.

Logotypes are intentionally preserved and excluded from body-text failures,
as permitted by [WCAG 2.2 SC 1.4.3](https://www.w3.org/WAI/WCAG22/Understanding/contrast-minimum.html).
Ordinary text targets 4.5:1; large text targets 3:1. Focus/control color pairs
are also checked against [SC 1.4.11](https://www.w3.org/WAI/WCAG22/Understanding/non-text-contrast.html).
Native disabled states and image/gradient text require separate manual review.
This is a contrast-focused audit of the documented screens/states, not a claim
of complete WCAG conformance or exhaustive future/dynamic-content coverage.

Private measurements and screenshots are stored under
`work/contrast-audit-20261105/` and are not part of the public release.
