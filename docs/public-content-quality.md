# Public Content Quality

Updated: 2026-11-04

## Release Scope

The AdSense site review reported low-value content. This release improves the
actual visitor experience; it does not resubmit the site or guarantee approval.
No account, advertising-dashboard, billing, authentication, DB schema, catalog
record, circle ID, source URL, contact-consent setting or event price is changed.

- A shared footer connects the public entry points, guides, operator, editorial
  policy, corrections/contact, terms and privacy policy. Legacy footers are
  replaced, not stacked. Admin pages and private workflows are excluded.
- The existing logo, sports rail and Club Edit presentation are retained. The
  home page links directly to practical reading alongside real event listings.
- Three existing guides now contain concrete planning steps, participant/team
  templates, clearly labeled fictional budget examples, source checks, weather
  decisions and cancellation considerations.
- The new `/guides/tokyo-venue-costs` explains how to compare unlike booking
  units. Five editorially chosen examples read the existing public catalog at
  request time, preserving each fee unit, eligibility condition, evidence URL,
  checked date and unknown value. They are not a cheapest-venue ranking. Closed
  venues are omitted; failed data loads remain explicit and ad-free.
- The comparison's original discussion was checked against the official Tokyo
  Parks sports fee list, TEF Komazawa tennis page and Bonfim Ochiai tariff page
  on 2026-11-04. Catalog dates remain their actual earlier review dates; this
  release does not claim to reverify every venue.
- Editorial pages have a table of contents, editorial attribution, revision
  metadata, unique descriptions, relevant links and sitemap inclusion.
- Empty event searches offer context-preserving venue/circle alternatives and
  preparation guidance, including after client-side filtering.
- Circle rows show source type and source-check date in server-rendered and
  client-rendered results. A source check is not proof of current activity,
  recruiting, official recognition or participant acceptance. Unverified meeting
  times and membership fees are not fabricated.

## Advertising Boundary

`circlematch_public_content.apply_ad_policy` runs on the final HTTP HTML after
SEO metadata. The existing helper's logo styling is retained; only the exact
configured advertising loader is removed from ineligible responses.

Eligibility is deny-by-default, restricted to successful, indexable home pages,
the four expanded editorial articles, and published public event details.
Visible server error states are excluded. Search screens are excluded even when
initially populated because client filtering can replace results with an empty
state without a new HTTP document. Auth, settings, applications, payments,
management, private invitations, directory searches, policy pages, short legacy
articles, errors and unknown routes do not load the advertising script.

This is independent of `noindex`; indexing controls are not ad-exclusion rules.
No Auto Ads setting, publisher ID or ads.txt entry is changed. No approval or
actual ad serving is inferred merely from the presence of the loader.

## Validation

```powershell
python -X utf8 -m unittest discover -s scripts -p test_public_content.py
python -X utf8 -m unittest discover -s scripts -p 'test_*.py'
```

Use disposable fixture databases. Verify desktop/mobile home, article TOC,
expanded source details, footer, empty event alternatives, circle provenance,
and the unchanged participant prices. Check horizontal overflow and the sticky
mobile navigation. After Render reports the intended commit Live, repeat public
HTTP and browser checks. Do not resubmit AdSense until the owner reviews the
deployed changes.

## Ongoing Editorial Work

Imported circle records still require evidence-based review of stale sources,
mistaken categories and inactive organizations. This release adds transparency,
not a blanket assertion that all imported records were reviewed. Continue the
existing venue/contact research without changing public-contact privacy rules.
Use actual usage data to prioritize useful comparisons; do not invent traffic
thresholds, reviews, events or a minimum article count for AdSense approval.

Google references:
- https://support.google.com/adsense/answer/10015918?hl=ja
- https://support.google.com/adsense/answer/7299563?hl=ja
- https://support.google.com/publisherpolicies/answer/11112688?hl=ja
