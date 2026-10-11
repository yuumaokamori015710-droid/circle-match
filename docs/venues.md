# 会場予約タブ

`/venues` is a native public Circle Match page alongside the events and circle
directory tabs. It currently lists Tokyo tennis courts. Searching, filtering,
sorting and pagination run locally after one read-only catalog request.
Reservation links lead to the facility's official reservation instructions or
booking site; this page does not submit reservations or process payments.

## Files and data

- `outputs/circlematch_venues.py`: native body, asset declarations and public
  catalog interface; no acquisition admin or database dependency.
- `outputs/venues/`: scoped CSS, JavaScript and the curated public catalog.
- `outputs/circlematch_db_app.py`: shared tabs and explicit public GET routes.
- `scripts/test_venues.py`: isolated HTTP and navigation integration checks.

The initial catalog and directory UI were copied from the existing
`circlematch-acquisition` project at commit
`f6b3b14f21a3c729e2e70f7f3f14f8ce51e94b3a`. The catalog contains 404 facilities
across 58 Tokyo municipalities, with source checks dated 2026-10-10. Each record
retains its official source URLs, original price unit, conditions, check date
and unknown values. Known suspended facilities are hidden by default.
Coverage is described in the catalog; the list is not a claim of completeness
or live availability.

Update the checked-in catalog from verified official information and run the
catalog validation and `scripts/test_venues.py` before publishing. The catalog
is intentionally independent of either application's private user database.
Do not copy private acquisition settings, credentials or management routes
into this public page.
