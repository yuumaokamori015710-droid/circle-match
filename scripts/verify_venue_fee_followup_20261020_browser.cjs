const {chromium} = require('playwright');
const {spawn} = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

const root = path.resolve(__dirname, '..');
const base = process.env.VENUE_TEST_URL || 'http://127.0.0.1:8920';
const out = path.join(root, 'work/venue-fee-review-20261020', process.env.VENUE_TEST_URL ? 'production' : 'local');
const read = name => JSON.parse(fs.readFileSync(path.join(root, 'outputs/venues/catalogs', name), 'utf8'));
const reviews = read('fee_plans.json').filter(r => r.checked_at === '2026-10-20');
const policies = read('cancellation_policies.json').filter(r => r.checked_at === '2026-10-20');
const closed = ['tokyo-gym-c9fd2d3160d0', 'tokyo-sports-013'];
const pictured = ['tokyo-gym-80d67f6abfca', 'tokyo-venue-e5f26bb9d6f1', 'tokyo-gym-b7451bddb3f3', 'tokyo-sports-038'];
const ready = page => page.locator('#venue-loading-state[hidden]').waitFor({state: 'attached'});
const amount = r => r.minimum.toLocaleString('ja-JP') + '円' + (r.minimum === r.maximum ? '' : '〜' + r.maximum.toLocaleString('ja-JP') + '円');
// Oi main and sub share their heading but retain distinct official booking URLs.
const cardFor = (page, row) => page.locator('.venue-court-card').filter({
  has: page.locator('.venue-primary-link[href=' + JSON.stringify(row.booking_url) + ']'),
}).filter({has: page.getByRole('heading', {name: row.name, exact: true})});
let server, browser;
fs.mkdirSync(out, {recursive: true});

(async () => {
  if (!process.env.VENUE_TEST_URL) {
    server = spawn(process.env.VENUE_PYTHON || 'python', ['-X', 'utf8', '-c',
      "import os,sys;sys.path.insert(0,'outputs');os.environ['CIRCLEMATCH_DB_PATH']='work/venue-fee-review-20261020/unused.sqlite';from http.server import ThreadingHTTPServer;import circlematch_db_app as a;ThreadingHTTPServer(('127.0.0.1',8920),a.Handler).serve_forever()"
    ], {cwd: root, stdio: ['ignore', 'ignore', 'pipe']});
    server.stderr.on('data', data => process.stderr.write(data));
    let connected = false;
    for (let i = 0; i < 100; i++) {
      try { if ((await fetch(base + '/api/venues')).ok) { connected = true; break; } } catch {}
      await new Promise(resolve => setTimeout(resolve, 150));
    }
    assert(connected, 'Preview failed to start');
  }
  const response = await fetch(base + '/api/venues');
  assert.equal(response.status, 200);
  const catalog = await response.json();
  const rows = new Map(catalog.courts.map(r => [r.id, r]));
  assert.equal(rows.size, 1206);
  assert.equal(reviews.length, 19);
  assert.equal(policies.length, 15);
  for (const p of policies) assert.deepEqual(rows.get(p.id).cancellation, p);
  for (const id of closed) assert.equal(rows.get(id).availability_status, 'SUSPENDED');
  browser = await chromium.launch({channel: 'chrome', headless: true});
  const errors = [], results = [];
  for (const width of [390, 768, 1440, 1920]) {
    const page = await browser.newPage({viewport: {width, height: 1000}});
    page.on('pageerror', error => errors.push(error.message));
    for (const review of reviews) {
      const row = rows.get(review.id);
      assert.deepEqual(row.fee_options, review.fee_options);
      const response = await page.goto(base + '/venues?' + new URLSearchParams({v_q: row.name}), {waitUntil: 'domcontentloaded'});
      assert.equal(response.status(), 200);
      const html = await response.text();
      assert(html.includes(row.name) && html.includes(review.fee_note), 'Missing SSR tariff');
      await ready(page);
      const card = cardFor(page, row);
      assert.equal(await card.count(), 1, row.id);
      assert.deepEqual(await card.locator('.venue-price-amount').allTextContents(), row.fee_ranges.slice(0, 2).map(amount));
      assert.deepEqual(await card.locator('.venue-price-unit').allTextContents(), row.fee_ranges.slice(0, 2).map(r => r.unit));
      assert.equal(new URL(await card.locator('.venue-fee-link').getAttribute('href')).href, new URL(review.fee_options[0].source_url).href);
      assert.equal(new URL(await card.locator('.venue-primary-link').getAttribute('href')).href, new URL(row.booking_url).href);
      const detail = card.locator('xpath=following-sibling::tr[1]');
      await detail.locator('summary').click();
      assert.equal(await detail.locator('.venue-tariff-amount').count(), review.fee_options.length);
      if (row.cancellation) assert((await detail.locator('.venue-cancellation').innerText()).includes(row.cancellation.summary));
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'Horizontal overflow: ' + row.id);
      assert(await card.locator('.venue-price-amount').evaluateAll(spans => spans.every(span => {
        const box = span.getBoundingClientRect(), cell = span.closest('td').getBoundingClientRect();
        return box.left >= cell.left - 1 && box.right <= cell.right + 1;
      })), 'Clipped price: ' + row.id);
      if (pictured.includes(row.id) && [390, 1440].includes(width)) {
        await detail.locator('summary').click();
        await card.scrollIntoViewIfNeeded();
        await page.screenshot({path: path.join(out, row.id + '-' + width + '.png')});
      }
    }
    for (const id of closed) {
      await page.goto(base + '/venues?' + new URLSearchParams({v_q: rows.get(id).name}));
      await ready(page);
      assert.equal(await page.locator('.venue-court-card').count(), 0);
    }
    results.push({width, pricedCases: reviews.length, cancellationApiCases: policies.length, closedCases: closed.length});
    await page.close();
  }
  const nojs = await browser.newContext({javaScriptEnabled: false, viewport: {width: 390, height: 1000}});
  const page = await nojs.newPage();
  for (const id of pictured) {
    const row = rows.get(id);
    await page.goto(base + '/venues?' + new URLSearchParams({v_q: row.name}));
    const card = cardFor(page, row);
    assert.equal(await card.count(), 1);
    assert.deepEqual(await card.locator('.venue-price-amount').allTextContents(), row.fee_ranges.slice(0, 2).map(amount));
    const detail = card.locator('xpath=following-sibling::tr[1]');
    await detail.locator('summary').click();
    assert.equal(await detail.locator('.venue-tariff-amount').count(), row.fee_options.length);
    if (row.cancellation) assert((await detail.locator('.venue-cancellation').innerText()).includes(row.cancellation.summary));
  }
  await nojs.close();
  assert.deepEqual(errors, []);
  const report = {base, results, noJavaScriptCases: pictured.length, errors};
  fs.writeFileSync(path.join(out, 'results.json'), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report));
})().catch(error => {console.error(error); process.exitCode = 1;}).finally(async () => {
  if (browser) await browser.close();
  if (server) server.kill();
});
