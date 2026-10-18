/* Start: python scripts/preview_home_layout.py
 * Check: node scripts/check_home_layout.cjs <PREVIEW_URL> [screenshot-directory]
 * Requires Playwright and Chrome. All login data belongs to the isolated fixture.
 */
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');

const base = process.argv[2] || 'http://127.0.0.1:8899';
const output = path.resolve(process.argv[3] || 'work/home-layout-check');

(async () => {
  fs.mkdirSync(output, { recursive: true });
  const browser = await chromium.launch({ channel: 'chrome', headless: true });
  const results = [];
  try {
    for (const [width, height] of [[320, 700], [375, 812], [390, 844], [430, 932], [699, 1000], [700, 1000], [768, 1024], [1440, 1000], [1920, 1080]]) {
      const page = await browser.newPage({ viewport: { width, height } });
      const errors = [];
      page.on('pageerror', error => errors.push(error.message));
      await page.goto(base + '/', { waitUntil: 'networkidle' });
      const metrics = await page.evaluate(() => {
        const rect = node => {
          const r = node.getBoundingClientRect();
          return { x: r.x, y: r.y, width: r.width, height: r.height, right: r.right, bottom: r.bottom };
        };
        const journeys = [...document.querySelectorAll('.home-journey')];
        const buttons = [...document.querySelectorAll('.home-journey-actions .button')];
        const firstImage = document.querySelector('.sport-card img');
        return {
          documentWidth: document.documentElement.scrollWidth,
          latest: rect(document.querySelector('.home-latest-events')),
          header: rect(document.querySelector('header')),
          wordmark: rect(document.querySelector('.brand-wordmark')),
          brand: rect(document.querySelector('a.brand')),
          nav: rect(document.querySelector('.main-nav')),
          purposes: rect(document.querySelector('.home-journeys')),
          sports: rect(document.querySelector('.sports-home')),
          journeys: journeys.map(rect),
          summariesVisible: [...document.querySelectorAll('.home-journey-summary')].filter(n => n.getClientRects().length).length,
          stepsVisible: [...document.querySelectorAll('.home-journey-steps')].filter(n => n.getClientRects().length).length,
          buttonBounds: buttons.map(rect),
          buttonOverflow: buttons.filter(n => n.scrollWidth > n.clientWidth + 1 || n.scrollHeight > n.clientHeight + 1).length,
          cardOverflow: journeys.filter(n => [...n.querySelectorAll('h2, .home-journey-actions .button')].some(child => {
            const a = child.getBoundingClientRect(), b = n.getBoundingClientRect();
            return a.left < b.left || a.right > b.right || a.bottom > b.bottom;
          })).length,
          actionGaps: journeys.map(n => n.querySelector('.home-journey-actions').getBoundingClientRect().top - n.querySelector('h2').getBoundingClientRect().bottom),
          links: buttons.map(n => n.getAttribute('href')),
          brokenImages: [...document.querySelectorAll('.sport-card img')].filter(n => !n.complete || !n.naturalWidth).length,
          imageVisible: Math.max(0, Math.min(rect(firstImage).bottom, innerHeight) - Math.max(0, rect(firstImage).y)),
          sportsColumns: getComputedStyle(document.querySelector('.sport-grid')).gridTemplateColumns.split(' ').length,
        };
      });
      assert(metrics.documentWidth <= width + 1, `${width}: horizontal overflow`);
      assert(metrics.latest.bottom <= metrics.purposes.y, `${width}: latest must be first`);
      assert(metrics.purposes.bottom <= metrics.sports.y, `${width}: sports must follow purposes`);
      assert.equal(metrics.buttonOverflow, 0, `${width}: button text overflow`);
      assert.equal(metrics.cardOverflow, 0, `${width}: content outside journey card`);
      assert.equal(metrics.brokenImages, 0, `${width}: missing sports image`);
      assert(metrics.wordmark.width > 30 && metrics.wordmark.height > 10, `${width}: brand name hidden`);
      assert(metrics.header.height <= 72, `${width}: guest header too tall`);
      assert(metrics.brand.right <= metrics.nav.x, `${width}: logo overlaps navigation`);
      assert(metrics.buttonBounds.every(r => r.height >= 44), `${width}: touch targets too short`);
      assert.equal(metrics.links.length, 4);
      assert(metrics.links[0].startsWith('/events/new?'));
      assert.equal(metrics.links[1], '/venues');
      assert.equal(metrics.links[2], '/events');
      assert.equal(metrics.links[3], '/?tab=db&audience=university');
      const [host, join] = metrics.journeys;
      assert(Math.abs(host.y - join.y) < 1 && host.right < join.x, `${width}: journeys not side by side`);
      assert(Math.abs(host.width - join.width) < 1, `${width}: unequal journey widths`);
      if (width <= 699) {
        assert.equal(metrics.summariesVisible, 0, `${width}: numbered summaries visible`);
        assert.equal(metrics.stepsVisible, 0, `${width}: detailed steps visible`);
        assert(host.height / host.width < 1.25, `${width}: journey card too tall`);
        assert(metrics.actionGaps.every(gap => gap >= 0 && gap <= 9), `${width}: blank space before journey buttons`);
        assert(metrics.latest.height <= 186, `${width}: latest events section too tall`);
        assert.equal(metrics.sportsColumns, 2);
        if (width <= 430) assert(metrics.imageVisible >= 100, `${width}: sports images hidden below first screen`);
      } else {
        assert.equal(metrics.stepsVisible, 2, `${width}: desktop explanations missing`);
        assert.equal(metrics.sportsColumns, width >= 1600 ? 5 : width >= 1024 ? 4 : 3);
        if (width >= 900) assert(metrics.latest.height <= 100, `${width}: desktop latest section too tall`);
      }
      assert.deepEqual(errors, [], `${width}: browser errors`);
      await page.screenshot({ path: path.join(output, `home-${width}.png`), fullPage: true });
      results.push({ width, height, ...metrics });
      await page.close();
    }
    const noJs = await browser.newPage({ viewport: { width: 390, height: 844 }, javaScriptEnabled: false });
    await noJs.goto(base + '/');
    assert.equal(await noJs.locator('.home-latest-item').count(), 3);
    assert.equal(await noJs.locator('.home-journey-actions .button').count(), 4);
    await noJs.close();
    for (const width of [320, 375, 390, 430, 620, 768]) {
      const page = await browser.newPage({ viewport: { width, height: 844 } });
      await page.goto(base + '/preview/signin', { waitUntil: 'networkidle' });
      assert.equal(await page.locator('header .account-logout').count(), 1);
      const header = await page.evaluate(() => {
        const rect = selector => {
          const r = document.querySelector(selector).getBoundingClientRect();
          return { x: r.x, y: r.y, right: r.right, bottom: r.bottom, height: r.height, width: r.width };
        };
        return { scroll: document.documentElement.scrollWidth, header: rect('header'), brand: rect('a.brand'), wordmark: rect('.brand-wordmark'), nav: rect('.main-nav') };
      });
      assert(header.scroll <= width + 1, `${width}: signed-in overflow`);
      assert(header.wordmark.width > 30 && header.wordmark.height > 10, `${width}: signed-in brand name hidden`);
      assert(header.brand.right <= header.nav.x || header.brand.bottom <= header.nav.y, `${width}: signed-in header overlap`);
      assert(header.header.height <= 116, `${width}: signed-in header too tall`);
      await page.screenshot({ path: path.join(output, `home-signed-in-${width}.png`), fullPage: true });
      await page.close();
    }
    for (const width of [320, 390]) {
      const page = await browser.newPage({ viewport: { width, height: 844 } });
      for (const route of ['/events', '/venues', '/?tab=db', '/signin?return_to=%2Fmypage', '/circles', '/social/circles']) {
        await page.goto(base + route, { waitUntil: 'networkidle' });
        const header = await page.evaluate(() => {
          const root = document.querySelector('header'), brand = root.querySelector('.brand-wordmark');
          return { scroll: root.scrollWidth, brandWidth: brand.getBoundingClientRect().width };
        });
        assert(header.scroll <= width + 1, `${width} ${route}: header overflow`);
        assert(header.brandWidth > 30, `${width} ${route}: brand name hidden`);
      }
      await page.close();
    }
    fs.writeFileSync(path.join(output, 'results.json'), JSON.stringify(results, null, 2));
    console.log(`PASS: ${results.length} responsive layouts, 6 signed-in headers, 12 other-page headers and no-JavaScript home`);
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
