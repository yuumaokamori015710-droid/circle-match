const {chromium} = require('playwright');
const {spawn} = require('node:child_process');
const fs = require('node:fs');
const path = require('node:path');
const assert = require('node:assert/strict');
const python = process.env.VENUE_PYTHON || 'python';
const root = path.resolve(__dirname, '..');
const out = path.join(root, 'work/venue-verification');
fs.mkdirSync(out, {recursive:true});
const port = 8903;
const base = process.env.VENUE_TEST_URL || `http://127.0.0.1:${port}`;
let server;
const results = [];
(async () => {
  if (!process.env.VENUE_TEST_URL) {
    server = spawn(python, ['-c', `import os,sys;sys.path.insert(0,'outputs');os.environ['CIRCLEMATCH_DB_PATH']='work/venue-verification/unused.sqlite';from http.server import ThreadingHTTPServer;import circlematch_db_app as a;ThreadingHTTPServer(('127.0.0.1',${port}),a.Handler).serve_forever()`], {cwd:root,stdio:['ignore','ignore','pipe']});
    server.stderr.on('data',data=>process.stderr.write(data));
    for (let i=0; i<80; i++) {
      try { if((await fetch(base+'/api/venues')).ok) break; } catch {}
      await new Promise(resolve=>setTimeout(resolve,100));
    }
  }
  const browser = await chromium.launch({channel:'chrome',headless:true});
  try {
    const catalog = await (await fetch(base+'/api/venues')).json();
    for (const width of [390,768,1440,1920]) {
      const page = await browser.newPage({viewport:{width,height:1000}});
      for (const sport of Object.keys(catalog.meta.sports)) {
        const url = base+'/venues?'+new URLSearchParams({sport,prefecture:'東京都'});
        const response = await page.goto(url,{waitUntil:'domcontentloaded'});
        assert.equal(response.status(),200);
        assert((await response.text()).includes('class="venue-court-card"'));
        await page.locator('#venue-filter-fields:not([disabled])').waitFor();
        assert(await page.locator('.venue-court-card').count() > 0);
        const metrics = await page.evaluate(()=>({width:innerWidth,document:document.documentElement.scrollWidth,brokenImages:[...document.images].filter(i=>i.complete&&!i.naturalWidth).length}));
        assert(metrics.document<=width+1);
        assert.equal(metrics.brokenImages,0);
        const booking = page.locator('.venue-court-card .venue-primary-link').first();
        assert(/^https?:/.test(await booking.getAttribute('href')));
        assert.equal(await booking.getAttribute('target'),'_blank');
        results.push({sport,...metrics});
        if (sport==='サッカー・フットサル' && [390,1440].includes(width)) {
          await page.screenshot({path:path.join(out,`football-${width}.png`)});
          await page.locator('.venue-court-card').first().scrollIntoViewIfNeeded();
          await page.screenshot({path:path.join(out,`football-results-${width}.png`)});
        }
      }
      for (const name of ['高円寺みんなの体育館','高円寺地域区民センター（セシオン杉並）','上高田運動施設庭球場','カラオケまねきねこ 経堂農大通り店']) {
        const row = catalog.courts.find(row=>row.name===name);
        assert(row && row.price_to !== undefined);
        await page.goto(base+'/venues?'+new URLSearchParams({v_q:name}));
        await page.locator('#venue-filter-fields:not([disabled])').waitFor();
        const card = page.locator('.venue-court-card').filter({has:page.getByRole('heading',{name,exact:true})});
        const expected = row.price_from.toLocaleString('ja-JP')+'円'+(row.price_to===row.price_from?'':'〜'+row.price_to.toLocaleString('ja-JP')+'円');
        assert.equal(await card.locator('.venue-original-price').innerText(),expected);
        assert.equal(await card.locator('.venue-price-unit').innerText(),row.price_unit);
        const source = row.sources.find(s=>s.title.includes('公式料金表'));
        assert.equal(await card.locator('.venue-fee-link').getAttribute('href'),source.url);
        const overflow = await card.locator('.venue-court-price').evaluate(el=>{
          const parent=el.getBoundingClientRect();
          return [...el.querySelectorAll('.venue-price-amount')].some(span=>{
            const rect=span.getBoundingClientRect();
            return rect.right>parent.right+1 || rect.left<parent.left-1;
          });
        });
        assert.equal(overflow,false);
        if(name==='高円寺みんなの体育館' && [390,1440].includes(width)) {
          await card.scrollIntoViewIfNeeded();
          await page.screenshot({path:path.join(out,`fee-range-${width}.png`)});
        }
      }
      await page.goto(base+'/venues?'+new URLSearchParams({sport:'サッカー・フットサル'}));
      await page.locator('#venue-filter-fields:not([disabled])').waitFor();
      await page.locator('input[name=q]').fill('no-matching-venue-xyz');
      await page.locator('#venue-empty-state:not([hidden])').waitFor();
      assert((await page.url()).includes('v_q='));
      await page.locator('#venue-empty-reset').click();
      await page.locator('.venue-court-card').first().waitFor();
      await page.locator('#directoryContext select[name=sport]').selectOption('ピックルボール');
      await page.waitForURL(/sport=/);
      await page.locator('#venue-page-title').filter({hasText:'ピックルボール'}).waitFor();
      await page.close();
    }
    const nojs = await browser.newContext({javaScriptEnabled:false,viewport:{width:390,height:844}});
    const plain = await nojs.newPage();
    await plain.goto(base+'/venues?'+new URLSearchParams({sport:'サッカー・フットサル'}));
    assert(await plain.locator('.venue-court-card').count()>=15);
    await plain.locator('input[name=q]').fill('no-matching-venue-xyz');
    await plain.getByRole('button',{name:'条件を適用',exact:true}).click();
    await plain.waitForURL(/q=/);
    assert.equal(await plain.locator('.venue-court-card').count(),0);
    await plain.goto(base+'/venues?'+new URLSearchParams({v_q:'高円寺みんなの体育館'}));
    assert.equal(await plain.locator('.venue-original-price').innerText(),'1,500円〜6,000円');
    assert.equal(await plain.locator('.venue-fee-link').count(),1);
    await nojs.close();
    const failed = await browser.newPage();
    await failed.route('**/api/venues*',route=>route.abort());
    await failed.goto(base+'/venues?'+new URLSearchParams({sport:'サッカー・フットサル'}));
    await failed.locator('#venue-error-state:not([hidden])').waitFor();
    assert(await failed.locator('.venue-court-card').count()>=15);
    await failed.close();
    fs.writeFileSync(path.join(out,'results.json'),JSON.stringify(results,null,2));
    console.log(`PASS: ${results.length} sport/viewport combinations, 16 fee/unit/source/overflow checks, filters, sport switch, no-JS, offline fallback`);
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;}).finally(()=>{if(server)server.kill();});
