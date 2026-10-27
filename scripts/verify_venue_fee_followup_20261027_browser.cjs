const {chromium} = require('playwright');
const {spawn} = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

const root = path.resolve(__dirname, '..');
const port = Number(process.env.VENUE_TEST_PORT || 8937);
const base = process.env.VENUE_TEST_URL || `http://127.0.0.1:${port}`;
const out = path.join(root, 'work/venue-fee-review-20261027', process.env.VENUE_TEST_URL ? 'production' : 'local');
const read = name => JSON.parse(fs.readFileSync(path.join(root, 'outputs/venues/catalogs', name), 'utf8'));
const reviews = read('fee_plans.json').filter(r => r.checked_at === '2026-10-27');
const policies = read('cancellation_policies.json').filter(r => r.checked_at === '2026-10-27');
const holds = ['tokyo-gym-a231878afdcf', 'tokyo-gym-c9fd2d3160d0', 'tokyo-venue-ec7d0ac023ca',
  'tokyo-venue-6b06aed3958d', 'tokyo-venue-205d87234dd3', 'tokyo-venue-2b0bbd7157ff',
  'tokyo-venue-8e6c0f81a52c', 'tokyo-venue-c282bded258a', 'tokyo-venue-456ad6cd0311',
  'tokyo-venue-40fd2672b512', 'tokyo-venue-3df7eec0d53c', 'tokyo-venue-74f8af5c1bc3'];
const pictured = ['tokyo-venue-3766e52a081e', 'tokyo-venue-f8e9ad9cee63', 'tokyo-sports-032', 'tokyo-venue-3df7eec0d53c'];
const amount = r => r.minimum.toLocaleString('ja-JP') + '\u5186' + (r.minimum === r.maximum ? '' : '\u301c' + r.maximum.toLocaleString('ja-JP') + '\u5186');
const escape = s => s.replaceAll('&', '&amp;').replaceAll('<', '&lt;').replaceAll('>', '&gt;').replaceAll('"', '&quot;').replaceAll("'", '&#x27;');
const cardFor = (page, row) => page.locator('.venue-court-card').filter({
  has: page.locator('.venue-primary-link[href=' + JSON.stringify(row.availability_status === 'SUSPENDED' ? row.official_url : row.booking_url) + ']'),
}).filter({has: page.getByRole('heading', {name: row.name, exact: true})});
const query = row => new URLSearchParams({v_q: row.name, v_show_suspended: '1'});
let server, browser;
fs.mkdirSync(out, {recursive: true});

(async () => {
  if (!process.env.VENUE_TEST_URL) {
    server = spawn(process.env.VENUE_PYTHON || 'python', ['-B', '-X', 'utf8', '-c',
      `import os,sys;sys.path.insert(0,'outputs');os.environ['CIRCLEMATCH_DB_PATH']='work/venue-fee-review-20261027/unused.sqlite';from http.server import ThreadingHTTPServer;import circlematch_db_app as a;ThreadingHTTPServer(('127.0.0.1',${port}),a.Handler).serve_forever()`
    ], {cwd: root, stdio: ['ignore', 'ignore', 'pipe']});
    server.stderr.on('data', data => process.stderr.write(data));
    let connected = false;
    for (let i = 0; i < 100; i++) {
      assert(server.exitCode === null, 'Preview exited prematurely');
      try { if ((await fetch(base + '/api/venues')).ok) { connected = true; break; } } catch {}
      await new Promise(resolve => setTimeout(resolve, 150));
    }
    assert(connected, 'Preview failed to start');
  }
  const response = await fetch(base + '/api/venues');
  assert.equal(response.status, 200);
  const catalog = await response.json(), rows = new Map(catalog.courts.map(r => [r.id, r]));
  assert.equal(rows.size, 1206);
  assert.equal(catalog.meta.prices_available, 830);
  assert.equal(reviews.length, 14);
  assert.equal(policies.length, 15);
  for (const policy of policies) assert.deepEqual(rows.get(policy.id).cancellation, policy);
  for (const review of reviews) {
    const row = rows.get(review.id);
    assert.deepEqual(row.fee_options, review.fee_options);
    assert.equal(row.fee_note, review.fee_note);
    assert.equal(row.fee_checked_at, review.checked_at);
  }
  for (const id of holds) {
    assert.equal(rows.get(id).price_from, null);
    assert.deepEqual(rows.get(id).fee_ranges, []);
  }
  assert.equal(rows.get(pictured[3]).availability_status, 'SUSPENDED');
  browser = await chromium.launch({channel: 'chrome', headless: true});
  const errors = [], results = [];
  for (const width of [390, 768, 1440, 1920]) {
    const page = await browser.newPage({viewport: {width, height: 1000}});
    page.on('pageerror', error => errors.push(error.message));
    for (const id of [...reviews.map(r => r.id), ...holds]) {
      const row = rows.get(id), priced = !holds.includes(id);
      const response = await page.goto(base + '/venues?' + query(row), {waitUntil: 'domcontentloaded'});
      assert.equal(response.status(), 200);
      const html = await response.text();
      assert(html.includes(escape(row.name)), 'Missing SSR venue: ' + id);
      if (priced) assert(html.includes(escape(row.fee_note)), 'Missing SSR conditions: ' + id);
      await page.locator('#venue-loading-state[hidden]').waitFor({state: 'attached'});
      const card = cardFor(page, row);
      assert.equal(await card.count(), 1, id);
      if (priced) {
        assert.deepEqual(await card.locator('.venue-price-amount').allTextContents(), row.fee_ranges.slice(0, 2).map(amount));
        assert.deepEqual(await card.locator('.venue-price-unit').allTextContents(), row.fee_ranges.slice(0, 2).map(r => r.unit));
        assert.equal(new URL(await card.locator('.venue-fee-link').getAttribute('href')).href, new URL(row.fee_options[0].source_url).href);
      }
      assert.equal(new URL(await card.locator('.venue-primary-link').getAttribute('href')).href, new URL(row.availability_status === 'SUSPENDED' ? row.official_url : row.booking_url).href);
      const detail = card.locator('xpath=following-sibling::tr[1]');
      await detail.locator('summary').click();
      assert.equal(await detail.locator('.venue-tariff-amount').count(), (row.fee_options || []).length);
      if (row.cancellation) assert((await detail.locator('.venue-cancellation').innerText()).includes(row.cancellation.summary));
      if (row.availability_status === 'SUSPENDED') assert(html.includes(escape(row.availability_note)));
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'Overflow: ' + id);
      assert(await card.locator('.venue-price-amount').evaluateAll(spans => spans.every(span => {
        const box = span.getBoundingClientRect(), cell = span.closest('td').getBoundingClientRect();
        return box.left >= cell.left - 1 && box.right <= cell.right + 1;
      })), 'Clipped price: ' + id);
      if (pictured.includes(id) && [390, 1440].includes(width)) {
        await card.scrollIntoViewIfNeeded();
        await page.screenshot({path: path.join(out, id + '-' + width + '.png'), fullPage: true});
      }
      results.push({id, width, hold: !priced, ok: true});
    }
    const closed = rows.get(pictured[3]);
    await page.goto(base + '/venues?' + new URLSearchParams({v_q: closed.name}));
    await page.locator('#venue-loading-state[hidden]').waitFor({state: 'attached'});
    assert.equal(await cardFor(page, closed).count(), 0, 'Closed facility not hidden');
    results.push({width, defaultClosureHidden: true, ok: true});
    await page.close();
  }
  for (const width of [390, 1440]) {
    const page = await browser.newPage({viewport: {width, height: 1000}, javaScriptEnabled: false});
    for (const id of [pictured[0], pictured[3]]) {
      const row = rows.get(id), response = await page.goto(base + '/venues?' + query(row));
      assert.equal(response.status(), 200);
      assert.equal(await cardFor(page, row).count(), 1);
      assert((await response.text()).includes(row.fee_note || row.availability_note));
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
      results.push({id, width, noJavaScript: true, ok: true});
    }
    await page.close();
  }
  assert.deepEqual(errors, []);
  fs.writeFileSync(path.join(out, 'results.json'), JSON.stringify({base, checkedAt: new Date().toISOString(), results, errors}, null, 2));
  console.log(JSON.stringify({base, cases: results.length, errors}));
})().catch(error => {console.error(error); process.exitCode = 1;}).finally(async () => {
  if (browser) await browser.close();
  if (server && server.exitCode === null) await new Promise(resolve => {server.once('exit', resolve); server.kill();});
});
