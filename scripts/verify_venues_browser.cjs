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
    const facetPage=await browser.newPage({viewport:{width:1440,height:1000}});
    const errors=[];
    facetPage.on('pageerror',error=>errors.push(error.message));
    await facetPage.goto(base+'/venues');
    await facetPage.locator('#venue-filter-fields:not([disabled])').waitFor();
    await facetPage.locator('#venue-area-filter').selectOption('23区');
    await facetPage.locator('[name=municipality]').selectOption('新宿区');
    await facetPage.locator('#venue-area-filter').selectOption('多摩');
    assert.equal(await facetPage.locator('[name=municipality]').inputValue(),'');
    const options=await facetPage.locator('[name=municipality] option').allTextContents();
    assert(options.includes('八王子市') && !options.includes('新宿区'));
    await facetPage.locator('#venue-reset-filters').click();
    for(const [field,value,predicate] of [
      ['booking_channel','phone',row=>row.booking_channels.includes('phone')],
      ['booking_channel','web',row=>row.booking_channels.includes('web')],
      ['registration','required',row=>row.registration_required===true],
      ['registration','unknown',row=>row.registration_required===null],
      ['venue_type','gym',row=>row.venue_types.includes('gym')]
    ]) {
      await facetPage.locator('#venue-reset-filters').click();
      await facetPage.locator(`[name=${field}]`).selectOption(value);
      const expected=catalog.courts.filter(row=>row.availability_status!=='SUSPENDED' && predicate(row)).length;
      assert.equal(await facetPage.locator('#venue-result-count').innerText(),expected.toLocaleString('ja-JP')+' 件');
      await facetPage.reload();
      await facetPage.locator('#venue-filter-fields:not([disabled])').waitFor();
      assert.equal(await facetPage.locator(`[name=${field}]`).inputValue(),value);
      assert.equal(await facetPage.locator('#venue-result-count').innerText(),expected.toLocaleString('ja-JP')+' 件');
    }
    await facetPage.locator('#venue-reset-filters').click();
    await facetPage.locator('[name=open_from]').fill('20:00');
    await facetPage.locator('[name=open_until]').fill('21:00');
    assert.equal(await facetPage.locator('.venue-court-card').count(),12);
    await facetPage.locator('#venue-reset-filters').click();
    await facetPage.locator('[name=price_max]').fill('1,300');
    assert((await facetPage.locator('.venue-court-card').count())>0);
    await facetPage.locator('[name=price_max]').fill('not-a-price');
    assert.equal(await facetPage.locator('#venue-filter-error').isVisible(),true);
    await facetPage.locator('#venue-reset-filters').click();
    await facetPage.locator('#venue-sort').selectOption('price');
    assert(facetPage.url().includes('v_sort=price'));
    assert.equal(await facetPage.locator('#venue-sort').evaluate(el=>el.closest('.venue-filter-panel')),null);
    const returnUrl=new URL(facetPage.url()).pathname+new URL(facetPage.url()).search;
    await facetPage.getByRole('link',{name:'設定',exact:true}).click();
    await facetPage.getByRole('radio',{name:'スマホビュー',exact:true}).check();
    await facetPage.getByRole('button',{name:'設定を保存',exact:true}).click();
    await facetPage.getByText('設定を保存しました。',{exact:true}).waitFor();
    assert.equal(await facetPage.evaluate(()=>CircleMatchSettings.get().view),'mobile');
    assert.equal(await facetPage.evaluate(()=>document.documentElement.dataset.cmView),'auto');
    await facetPage.getByRole('link',{name:'元の画面へ戻る',exact:false}).click();
    await facetPage.locator('#venue-filter-fields:not([disabled])').waitFor();
    assert.equal(new URL(facetPage.url()).pathname+new URL(facetPage.url()).search,returnUrl);
    assert.equal(await facetPage.locator('.venue-court-card').first().evaluate(el=>getComputedStyle(el).display),'block');
    assert.equal(await facetPage.evaluate(()=>document.documentElement.dataset.cmView),'mobile');
    assert.equal(await facetPage.evaluate(()=>Math.round(document.body.getBoundingClientRect().width)),390);
    await facetPage.screenshot({path:path.join(out,'forced-mobile-on-desktop.png')});
    await facetPage.getByRole('link',{name:'設定',exact:true}).click();
    await facetPage.getByRole('radio',{name:'PCビュー',exact:true}).check();
    await facetPage.locator('[name=venueArea]').selectOption('多摩');
    await facetPage.locator('[name=venueSort]').selectOption('price');
    await facetPage.getByRole('button',{name:'設定を保存',exact:true}).click();
    await facetPage.goto(base+'/venues');
    await facetPage.locator('#venue-filter-fields:not([disabled])').waitFor();
    assert.equal(await facetPage.locator('#venue-area-filter').inputValue(),'多摩');
    assert.equal(await facetPage.locator('#venue-sort').inputValue(),'price');
    assert.equal(await facetPage.locator('.venue-court-card').first().evaluate(el=>getComputedStyle(el).display),'grid');
    await facetPage.goto(base+'/venues?v_area='+encodeURIComponent('23区'));
    await facetPage.locator('#venue-filter-fields:not([disabled])').waitFor();
    assert.equal(await facetPage.locator('#venue-area-filter').inputValue(),'23区');
    await facetPage.getByRole('link',{name:'設定',exact:true}).click();
    await facetPage.getByRole('button',{name:'初期設定に戻す',exact:true}).click();
    assert.equal(await facetPage.evaluate(()=>document.documentElement.dataset.cmView),'auto');
    await facetPage.locator('[name=rememberVenueSearch]').check();
    await facetPage.getByRole('button',{name:'設定を保存',exact:true}).click();
    await facetPage.goto(base+'/venues');
    await facetPage.locator('#venue-filter-fields:not([disabled])').waitFor();
    await facetPage.locator('#venue-area-filter').selectOption('多摩');
    await facetPage.goto(base+'/venues');
    await facetPage.locator('#venue-filter-fields:not([disabled])').waitFor();
    assert.equal(await facetPage.locator('#venue-area-filter').inputValue(),'多摩');
    assert.deepEqual(errors,[]);
    await facetPage.close();
    for(const width of [320,390,768,1440,1920]) {
      const settings=await browser.newPage({viewport:{width,height:1000}});
      await settings.goto(base+'/settings');
      assert.equal(await settings.getByRole('link',{name:'設定',exact:true}).count(),1);
      assert(await settings.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
      await settings.screenshot({path:path.join(out,`settings-${width}.png`)});
      // Layout-only signed-in navigation fixture; no login or logout request.
      if(width<=390) {
        await settings.evaluate(()=>{
          const account=document.getElementById('accountLink');account.textContent='マイページ';account.href='/mypage';
          account.insertAdjacentHTML('afterend','<form class="account-logout"><button type="button">ログアウト</button></form>');
        });
        assert(await settings.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
        const overlapping=await settings.locator('.main-nav').evaluate(nav=>{
          const rects=[...nav.children].map(el=>el.getBoundingClientRect());
          return rects.some((a,i)=>rects.slice(i+1).some(b=>a.left<b.right-1 && b.left<a.right-1 && a.top<b.bottom-1 && b.top<a.bottom-1));
        });
        assert.equal(overlapping,false);
      }
      await settings.close();
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
    await plain.goto(base+'/venues?area='+encodeURIComponent('多摩'));
    assert(!(await plain.locator('[name=municipality] option').allTextContents()).includes('新宿区'));
    await plain.locator('[name=booking_channel]').selectOption('phone');
    await plain.locator('#venue-sort').selectOption('price');
    await plain.getByRole('button',{name:'条件を適用',exact:true}).click();
    assert.equal(await plain.locator('#venue-area-filter').inputValue(),'多摩');
    assert.equal(await plain.locator('#venue-sort').inputValue(),'price');
    assert((await plain.locator('.venue-court-card').count())>0);
    await nojs.close();
    const phone=await browser.newContext({viewport:{width:390,height:844},isMobile:true,deviceScaleFactor:1});
    const device=await phone.newPage();
    await device.goto(base+'/settings');
    await device.getByRole('radio',{name:'PCビュー',exact:true}).check();
    await device.getByRole('button',{name:'設定を保存',exact:true}).click();
    await device.goto(base+'/venues');
    await device.locator('#venue-filter-fields:not([disabled])').waitFor();
    assert.equal(await device.locator('.venue-court-card').first().evaluate(el=>getComputedStyle(el).display),'grid');
    assert((await device.locator('meta[name=viewport]').getAttribute('content')).startsWith('width=1280, initial-scale='));
    assert(await device.evaluate(()=>visualViewport.width>=1200));
    await device.getByRole('link',{name:'設定',exact:true}).click();
    await device.getByRole('button',{name:'初期設定に戻す',exact:true}).click();
    assert((await device.locator('meta[name=viewport]').getAttribute('content')).includes('device-width'));
    assert(await device.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
    await phone.close();
    const failed = await browser.newPage();
    await failed.route('**/api/venues*',route=>route.abort());
    await failed.goto(base+'/venues?'+new URLSearchParams({sport:'サッカー・フットサル'}));
    await failed.locator('#venue-error-state:not([hidden])').waitFor();
    assert(await failed.locator('.venue-court-card').count()>=15);
    await failed.close();
    fs.writeFileSync(path.join(out,'results.json'),JSON.stringify(results,null,2));
    console.log(`PASS: ${results.length} sport/viewport combinations, 16 fee checks, cascading area/municipality, booking/registration/type/hours/price filters, URL reload, sorting, saved settings, forced mobile/desktop, 5 settings widths, no-JS, offline fallback`);
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;}).finally(()=>{if(server)server.kill();});
