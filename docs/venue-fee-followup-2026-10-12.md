# Venue fee follow-up: 2026-10-12

## Display

- Right-aligned amounts and tabular numerals in both the directory and the expanded tariff table.
- Conditional tariffs now show the minimum and maximum of **all reviewed tariffs with the same billing unit**, rather than the first two arbitrary prices.
- Different billing units remain separate. The compact list shows the first two unit groups; the full tariff table retains every reviewed amount and condition.
- Fixed prices, free prices (0 yen), and genuinely unconfirmed prices remain distinct. Unknown does not become free.
- API, initial HTML, and the interactive client use the same unit grouping and bounds.

## Official tariff additions

26 previously unpriced venues, 1,053 tariff rows:

- 4 futsal facilities (Tokyo Metropolitan Gymnasium, Shinjuku Central Park, Jexer Oimachi, Shinagawa).
- 5 Meguro gymnasiums.
- Omori Sports Center (Ota, explicitly scoped to the published intra-ward weekday base rates).
- 2 JELLY JELLY CAFE locations (individual admission packs, not whole-store hire).
- 5 Bunkyo academies.
- 9 Shinjuku community centers.

All 1,206 venue records and their existing URLs are preserved. Venues with published numerical fees increase from 569 to **595**; **611 remain unconfirmed**. This is not a claim that the remaining venues have been priced, or that every discount/surcharge is covered.

Exact reviewed units, bounds, official source URLs and dates are recorded in `venue-fee-followup-2026-10-12.json`. Full tariffs and conditions are in `outputs/venues/catalogs/fee_plans.json`.

## Collection safeguards

`scripts/collect_venue_fee_followup.py` merges reviewed entries without replacing unrelated catalog records. Bunkyo HTML tables are parsed structurally. Shinjuku PDF room names inherit merged parent cells; paired unavailable slots are skipped, never interpreted as zero. Unexpected tariff layouts abort before any catalog writes. Specialized merged purpose-use rows and ancillary fees are not guessed.

Futsal and gym tariffs were verified against the current official facility pages, including the Shinjuku Central Park tariff image. Meguro's current Yakumo fee is 8,000 yen for the intra-ward morning slot, not the 9,300 yen found in an older proposal. Different 30/60/90-minute, 3/4-hour and all-day units are not silently converted to hourly rates. Membership fees, eligibility conditions and minimum booking lengths remain in the tariff notes.

No new per-request network access or database work is introduced. The existing modification-time-keyed catalog cache and content-hashed assets remain in use.

## Verification

- 125 Python tests passed: venue/API/SSR/range parsing, geography, navigation, SEO, event flow/capacity, account navigation, latest events and circle invitations.
- `verify_venue_fee_ranges_browser.cjs`: 320/390/768/1440/1920 px; equal right edges for the visible amounts, tabular numerals, 30 fee scenarios, expanded tariff alignment, no horizontal overflow and 4 JavaScript-disabled pages passed.
- `verify_venue_columns_browser.cjs`: 5 widths, 6 column menus, combined filters, reload/back, all sort orders with SSR parity, Komazawa and JavaScript-disabled use passed.
- `verify_venues_browser.cjs`: 56 sport/viewport combinations, 16 tariff checks, geography/apply/cancel, URL history, search, filters, preferences, modal/settings widths and offline fallback passed.
- Desktop/mobile screenshots were visually inspected. The mobile tariff caption was corrected to stay horizontal.
