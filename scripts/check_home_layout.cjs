/* Read-only browser checks. Run against an isolated preview with three events. */
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
        assert.equal(metrics.sportsColumns, 2);
        if (width <= 430) assert(metrics.imageVisible >= 100, `${width}: sports images hidden below first screen`);
      } else {
        assert.equal(metrics.stepsVisible, 2, `${width}: desktop explanations missing`);
        assert.equal(metrics.sportsColumns, width >= 1600 ? 5 : width >= 1024 ? 4 : 3);
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
    fs.writeFileSync(path.join(output, 'results.json'), JSON.stringify(results, null, 2));
    console.log(`PASS: ${results.length} responsive layouts and no-JavaScript home`);
  } finally {
    await browser.close();
  }
})().catch(error => { console.error(error); process.exitCode = 1; });
