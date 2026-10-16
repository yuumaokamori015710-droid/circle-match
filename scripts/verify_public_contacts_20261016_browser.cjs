const {chromium} = require('playwright');
const {spawn} = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');

const root = path.resolve(__dirname, '..');
const base = process.env.CONTACT_TEST_URL || 'http://127.0.0.1:8908';
const out = path.join(root, 'work/contact-review-20261016');
const reviews = JSON.parse(fs.readFileSync(path.join(root, 'outputs/circle_public_contacts.json'), 'utf8'))
  .filter(row => row.checked_at === '2026-10-16');
fs.mkdirSync(out, {recursive: true});
let server;

(async () => {
  if (!process.env.CONTACT_TEST_URL) {
    server = spawn(process.env.CONTACT_PYTHON || 'python', ['-c',
      "import sys;sys.path.insert(0,'outputs');from http.server import ThreadingHTTPServer;import circlematch_db_app as a;a.ADSENSE_HEAD='';a.init_db();ThreadingHTTPServer(('127.0.0.1',8908),a.Handler).serve_forever()"
    ], {cwd: root, stdio: ['ignore', 'ignore', 'pipe'], env: {...process.env,
      CIRCLEMATCH_DB_PATH: path.join(out, 'directory.sqlite'),
      CIRCLEMATCH_EMAIL_NOTIFICATIONS_ENABLED: 'false', CIRCLEMATCH_EMAIL_AUTH_ENABLED: 'false',
      CIRCLEMATCH_SUPABASE_URL: '', CIRCLEMATCH_SUPABASE_ANON_KEY: '', CIRCLEMATCH_RESEND_API_KEY: '',
      CIRCLEMATCH_GOOGLE_CLIENT_ID: '', CIRCLEMATCH_GOOGLE_CLIENT_SECRET: '',
      CIRCLEMATCH_SITE_BASE_URL: base, CIRCLEMATCH_SESSION_SECRET: 'isolated-contact-preview-only'}});
    server.stderr.on('data', data => process.stderr.write(data));
    let connected = false;
    for (let i = 0; i < 100; i++) {
      try {
        if ((await fetch(base + '/api/circles?audience=social&q=SIT')).ok) { connected = true; break; }
      } catch {}
      await new Promise(resolve => setTimeout(resolve, 150));
    }
    assert(connected, 'Local disposable directory failed to start');
  }
  const browser = await chromium.launch({channel: 'chrome', headless: true});
  const errors = [], results = [];
  try {
    for (const width of [390, 1440]) {
      const page = await browser.newPage({viewport: {width, height: 1000}});
      page.on('pageerror', error => errors.push(error.message));
      for (const review of reviews) {
        const query = new URLSearchParams({tab: 'db', audience: 'social', q: review.circle_name});
        const response = await page.goto(base + '/?' + query, {waitUntil: 'networkidle'});
        assert.equal(response.status(), 200);
        assert((await response.text()).includes(review.circle_name), 'Missing initial HTML row');
        const row = page.locator('#dbList .circle-row').filter({has: page.getByText(review.circle_name, {exact: true})});
        assert.equal(await row.count(), 1);
        if (review.contact_url) {
          assert.equal(await row.locator('a').filter({hasText: review.contact_method === 'line' ? '公式LINE' : '問い合わせフォーム'}).getAttribute('href'), review.contact_url);
        } else {
          assert((await row.innerText()).includes('公開メールあり'));
        }
        const api = await page.request.get(base + '/api/circles?' + query);
        const circle = (await api.json()).find(item => item.circle_id === review.circle_id);
        assert(circle, 'Exact seeded ID missing');
        assert.equal(circle.public_contact_email, review.email || '');
        assert.equal(circle.contact_source_url, review.source_url);
        assert.equal(circle.contact_checked_at, review.checked_at);
        assert.equal(circle.contact_purpose, review.purpose);
        assert(!('claimant_email' in circle) && !('user_id' in circle));
        assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1), 'Horizontal overflow');
        await row.scrollIntoViewIfNeeded();
        assert(await row.isVisible());
        if (['SITクラブ', 'FC.サルミナート', 'ラビサル神奈川'].includes(review.circle_name)) {
          await page.screenshot({path: path.join(out, review.circle_id.split('_').at(-1) + '-' + width + '.png')});
        }
      }
      results.push({width, directoryCases: reviews.length});
      await page.close();
    }
    const nojs = await browser.newContext({javaScriptEnabled: false, viewport: {width: 390, height: 1000}});
    const page = await nojs.newPage();
    for (const review of reviews) {
      await page.goto(base + '/?' + new URLSearchParams({tab: 'db', audience: 'social', q: review.circle_name}));
      assert.equal(await page.locator('#dbList .circle-row').filter({has: page.getByText(review.circle_name, {exact: true})}).count(), 1);
      if (review.contact_url) assert(await page.locator('#dbList a').evaluateAll((links, href) => links.some(link => link.getAttribute('href') === href), review.contact_url));
    }
    await nojs.close();
    assert.deepEqual(errors, []);
    const report = {base, results, noJavaScriptCases: reviews.length, errors};
    fs.writeFileSync(path.join(out, process.env.CONTACT_TEST_URL ? 'production-results.json' : 'results.json'), JSON.stringify(report, null, 2));
    console.log(JSON.stringify(report));
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; }).finally(() => { if (server) server.kill(); });
