# Inline Circle DB Geography

- The DB tab, `/circles` and `/social/circles` display the geographic picker inline, not in a dialog.
- Existing venue boundary assets supply the national, regional and Tokyo municipality maps. No map-service key is required.
- Regional and prefectural choices are available nationally. Tokyo supports 23 wards, Tama and islands, then municipalities.
- A checkbox-style choice toggles a location; the adjacent arrow changes the map level without changing the selection.
- `places` stores comma-separated locations (repeated query parameters also work); `c_map` stores the visible map level.
- Multiple locations are OR conditions; audience, sport, text and verification filters remain AND conditions.
- Selecting a child refines a selected parent. Siblings and selections in other prefectures remain selected.
- Tokyo municipality matching uses recorded `universities.city` and `circles.activity_area`, restricted to Tokyo. Broad or missing location information is not invented.
- Counts are grouped SQL aggregates scoped to the audience and non-geographic filters. The browser receives map HTML and paginated circle records, not the entire circle DB.
- The native links work without JavaScript. The enhanced picker updates the existing list and URL without full navigation, restores history, and exposes fetch failures with retry.
- Both circle directories now render the requested conditions into their initial HTML. Errors are distinct from real empty results.
- No schema, seed, authentication, billing, venue tariff or booking URL changes.

## Verification

- `test_circle_regions`: OR semantics, audience isolation, bound parameters, region/legacy conditions, SSR, counts, native links, pagination and errors.
- `verify_circle_regions_browser.cjs`: four circle views at 320, 390, 768, 1440 and 1920 px; multiple locations, orange selection, sport/audience switches, reload/back, no-JS and error/retry.
- Existing venue, sport navigation, SEO, event, account, notification and invitation regression suites remain in use.
