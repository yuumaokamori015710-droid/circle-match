const {chromium} = require('playwright');
const {spawn} = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

const root = path.resolve(__dirname, '..');
const base = process.env.VENUE_TEST_URL || 'http://127.0.0.1:8918';
const out = path.join(root, 'work/venue-fee-review-20261018', process.env.VENUE_TEST_URL ? 'production' : 'local');
const reviews = JSON.parse(fs.readFileSync(path.join(root, 'outputs/venues/catalogs/fee_plans.json'), 'utf8'))
  .filter(row => row.checked_at === '2026-10-18');
const policies = JSON.parse(fs.readFileSync(path.join(root, 'outputs/venues/catalogs/cancellation_policies.json'), 'utf8'))
  .filter(row => row.checked_at === '2026-10-18');
const ready = page => page.locator('#venue-loading-state[hidden]').waitFor({state: 'attached'});
const amount = range => range.minimum.toLocaleString('ja-JP') + '円' +
  (range.minimum === range.maximum ? '' : '〜' + range.maximum.toLocaleString('ja-JP') + '円');
let server, browser;
fs.mkdirSync(out, {recursive: true});

(async () => {
  if (!process.env.VENUE_TEST_URL) {
    server = spawn(process.env.VENUE_PYTHON || 'python', ['-X', 'utf8', '-c',
      "import os,sys;sys.path.insert(0,'outputs');os.environ['CIRCLEMATCH_DB_PATH']='work/venue-fee-review-20261018/unused.sqlite';from http.server import ThreadingHTTPServer;import circlematch_db_app as a;ThreadingHTTPServer(('127.0.0.1',8918),a.Handler).serve_forever()"
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
  const rows = new Map(catalog.courts.map(row => [row.id, row]));
  for (const policy of policies) assert.deepEqual(rows.get(policy.id).cancellation, policy);
  assert.equal(rows.get('tokyo-venue-ecb55dd79d92').availability_status, 'SUSPENDED');
  assert.equal(rows.get('shinjuku-ochiai-chuo').availability_status, 'UNKNOWN');
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
      const initial = await response.text();
      assert(initial.includes(row.name) && initial.includes(row.cancellation.summary), 'Missing server-rendered evidence');
      await ready(page);
      const card = page.locator('.venue-court-card').filter({has: page.getByRole('heading', {name: row.name, exact: true})});
      assert.equal(await card.count(), 1);
      assert.deepEqual(await card.locator('.venue-price-amount').allTextContents(), row.fee_ranges.slice(0, 2).map(amount));
      assert.deepEqual(await card.locator('.venue-price-unit').allTextContents(), row.fee_ranges.slice(0, 2).map(range => range.unit));
      assert.equal(await card.locator('.venue-fee-link').getAttribute('href'), review.fee_options[0].source_url);
      assert.equal(await card.locator('.venue-primary-link').getAttribute('href'), row.booking_url);
      const detail = card.locator('xpath=following-sibling::tr[1]');
      await detail.locator('summary').click();
      assert.equal(await detail.locator('.venue-tariff-amount').count(), review.fee_options.length);
      assert((await detail.locator('.venue-cancellation').innerText()).includes(row.cancellation.summary));
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'Horizontal overflow');
      assert(await card.locator('.venue-price-amount').evaluateAll(spans => spans.every(span => {
        const box = span.getBoundingClientRect(), cell = span.closest('td').getBoundingClientRect();
        return box.left >= cell.left - 1 && box.right <= cell.right + 1;
      })), 'Clipped price');
      if (['shinjuku-okubo', 'tokyo-gym-8107c9095a7c'].includes(row.id) && [390, 1440].includes(width)) {
        await card.scrollIntoViewIfNeeded();
        await page.screenshot({path: path.join(out, row.id + '-' + width + '.png')});
      }
    }
    await page.goto(base + '/venues?' + new URLSearchParams({v_q: '落合中央公園野球場'}));
    await ready(page);
    assert.equal(await page.locator('.venue-court-card').count(), 0);
    results.push({width, pricedCases: reviews.length, cancellationApiCases: policies.length, closedFieldHidden: true});
    await page.close();
  }
  const nojs = await browser.newContext({javaScriptEnabled: false, viewport: {width: 390, height: 1000}});
  const page = await nojs.newPage();
  for (const id of ['shinjuku-okubo', 'tokyo-gym-8107c9095a7c']) {
    const row = rows.get(id);
    await page.goto(base + '/venues?' + new URLSearchParams({v_q: row.name}));
    const card = page.locator('.venue-court-card').filter({has: page.getByRole('heading', {name: row.name, exact: true})});
    assert.deepEqual(await card.locator('.venue-price-amount').allTextContents(), row.fee_ranges.slice(0, 2).map(amount));
    const detail = card.locator('xpath=following-sibling::tr[1]');
    await detail.locator('summary').click();
    assert((await detail.locator('.venue-cancellation').innerText()).includes(row.cancellation.summary));
  }
  await nojs.close();
  assert.deepEqual(errors, []);
  const report = {base, results, noJavaScriptCases: 2, errors};
  fs.writeFileSync(path.join(out, 'results.json'), JSON.stringify(report, null, 2));
  console.log(JSON.stringify(report));
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(async () => {
  if (browser) await browser.close();
  if (server) server.kill();
});
