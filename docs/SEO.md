# SEO baseline

Updated: 2026-10-10

The stdlib HTTP server already renders the event portal and DB tab records on the server. The release adds metadata to the final HTML response, not only after JavaScript execution. Existing body scripts, images, business logic, and database contents are retained.

- Unique Japanese page titles and descriptions for event searches, university/social DB tabs and informational pages. Area and sport come from the request, not hardcoded counts.
- Canonical URLs use the configured site origin, never the Host header. Tracking parameters are removed; DB audience and page numbers remain distinct. Sport-selected event links on the root canonicalize to /events.
- Open Graph and Twitter card metadata reuse existing images.
- Public event details emit Event JSON-LD using real name, date, venue, description and organizer. Naive dates are interpreted in Japan time. No invented end time, venue street address, event photo, prices, ratings or performer. Private email, banking and organizer revenue fields are excluded. Missing optional data may cause Google's validator to report recommendations; rich-result eligibility is not guaranteed.
- Authentication, applications, management, arbitrary text/date/participation filters, unknown categories, errors and empty filtered listings use noindex. Robots.txt allows the HTML crawler to read these directives; API/admin disallows remain.
- Legacy client-filtered sport/region screens are retained at their URLs but excluded from indexing and the sitemap. The SSR event portal and university/social DB tabs are the preferred search entry points.
- The sitemap uses an XML serializer, includes published upcoming events and published circle profiles, and excludes representative signup, private/management routes and drafts. If a visibility column exists, only public events are included. DB failures are logged explicitly. No database migration is needed.
- HTML retains no-store caching, so stale zero counts or metadata are not persisted by this release.

## Verification

Run `python -m unittest discover -s scripts -p test_seo.py -v` and `python scripts/test_event_flow.py`. Both use disposable databases. Read the public HTML (without JS), check canonical/meta tags and parse sitemap XML after deployment. Check desktop/mobile screenshots and sport navigation without posting production data.

## Remaining operational work

Search Console ownership and sitemap submission require the owner's authenticated Google session. No Search Console connector was available during this implementation. Do not claim the property is verified or the sitemap was submitted until confirmed. Use https://circle-match.jp/sitemap.xml as the sitemap URL.

This baseline does not improve the factual quality of imported circle rows. Spam/miscategorized/stale records require a separate reviewed cleanup. More unique, accurate event and organization content is needed for sustained search traffic. No search ranking or AdSense approval is guaranteed.

References:
- https://developers.google.com/search/docs/appearance/structured-data/event
- https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls
