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
const places=page=>page.locator('#venue-places-filter').evaluate(el=>[...el.selectedOptions].map(o=>o.value));
const pick=(page,name,checked=true)=>page.locator(`.venue-map-choice input[data-place="${name}"]`).setChecked(checked);
async function zoom(page,name,stage) {
  await page.getByRole('link',{name:name+'を詳しく選ぶ',exact:true}).click();
  await page.locator(`.venue-region-panel[data-stage=${stage}]`).waitFor();
}
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
        assert.equal(await page.locator('#venue-region-dialog').isVisible(),false);
        const filterRows=await page.locator('.venue-filter-grid').evaluate(el=>new Set([...el.children].map(child=>Math.round(child.getBoundingClientRect().top))).size);
        assert.equal(filterRows,width<=640?2:1);
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
      await page.goto(base+'/venues?'+new URLSearchParams({sport:'テニス'}));
      const guides=page.locator('.venue-registration-guides');
      await guides.locator('summary').click();
      assert.equal(await guides.locator('a.venue-registration-guide-link').count(),24);
      assert.equal(await guides.locator('ul').evaluate(el=>getComputedStyle(el).gridTemplateColumns.split(' ').length),width<=640?1:width<=900?2:4);
      assert((await guides.locator('a').first().getAttribute('href')).startsWith('https://'));
      assert((await page.evaluate(()=>document.documentElement.scrollWidth))<=width+1);
      if ([390,1440].includes(width)) await guides.screenshot({path:path.join(out,`registration-guides-${width}.png`)});
      for (const name of ['高円寺みんなの体育館','高円寺地域区民センター（セシオン杉並）','上高田運動施設庭球場','カラオケまねきねこ 経堂農大通り店']) {
        const row = catalog.courts.find(row=>row.name===name);
        assert(row && row.price_to !== undefined);
        await page.goto(base+'/venues?'+new URLSearchParams({v_q:name}));
        await page.locator('#venue-filter-fields:not([disabled])').waitFor();
        const card = page.locator('.venue-court-card').filter({has:page.getByRole('heading',{name,exact:true})});
        if (row.fee_options?.length) {
          assert.equal(await card.locator('.venue-rate-preview').count(),Math.min(2,row.fee_ranges.length));
          const detail=card.locator('xpath=following-sibling::tr[1]');
          await detail.locator('summary').click();
          assert.equal(await detail.locator('.venue-tariff tbody tr').count(),row.fee_options.length);
          assert.equal(await detail.locator('details').getAttribute('open'),'');
          assert.equal(await card.locator('.venue-price-unit').first().innerText(),row.fee_options[0].unit);
          assert.equal(await card.locator('.venue-fee-link').getAttribute('href'),row.fee_options[0].source_url);
        } else {
          const expected = row.price_from.toLocaleString('ja-JP')+'円'+(row.price_to===row.price_from?'':'〜'+row.price_to.toLocaleString('ja-JP')+'円');
          assert.equal(await card.locator('.venue-price-amount').innerText(),expected);
          assert.equal(await card.locator('.venue-price-unit').innerText(),row.price_unit);
        }
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
    await facetPage.evaluate(()=>window.venueDocumentMarker='same-document');
    await facetPage.locator('#venue-open-region').click();
    await facetPage.locator('#venue-region-dialog[open]').waitFor();
    const initialUrl=facetPage.url();
    await zoom(facetPage,'23区','wards');
    assert.deepEqual(await places(facetPage),[]);
    await pick(facetPage,'新宿区');
    await pick(facetPage,'渋谷区');
    const expectedBoth=catalog.courts.filter(r=>['新宿区','渋谷区'].includes(r.municipality)&&r.availability_status!=='SUSPENDED').length;
    assert.equal(await facetPage.locator('#venue-result-count').innerText(),expectedBoth+' 件');
    assert.equal(await facetPage.locator('.venue-map-shape.is-active').count(),2);
    assert.equal(facetPage.url(),initialUrl);
    await facetPage.getByRole('button',{name:'反映する',exact:true}).click();
    assert.deepEqual(await places(facetPage),['新宿区','渋谷区']);
    assert.equal(await facetPage.evaluate(()=>window.venueDocumentMarker),'same-document');
    const expectedShinjuku=catalog.courts.filter(r=>r.municipality==='新宿区'&&r.availability_status!=='SUSPENDED').length;
    await facetPage.locator('#venue-open-region').click();
    await pick(facetPage,'渋谷区',false);
    await facetPage.keyboard.press('Escape');
    assert.deepEqual(await places(facetPage),['新宿区','渋谷区']);
    assert.equal(await facetPage.locator('#venue-result-count').innerText(),expectedBoth+' 件');
    await facetPage.locator('#venue-open-region').click();
    await pick(facetPage,'渋谷区',false);
    await facetPage.locator('#venue-region-done').click();
    const shinjukuUrl=facetPage.url();
    await facetPage.goBack();
    assert.deepEqual(await places(facetPage),['新宿区','渋谷区']);
    await facetPage.goForward();
    assert.equal(facetPage.url(),shinjukuUrl);
    assert.deepEqual(await places(facetPage),['新宿区']);
    assert.equal(await facetPage.locator('#venue-result-count').innerText(),expectedShinjuku+' 件');
    await facetPage.locator('#venue-open-region').click();
    await facetPage.locator('.venue-map-breadcrumbs').getByRole('link',{name:'関東',exact:true}).click();
    await facetPage.locator('.venue-region-panel[data-stage=kanto]').waitFor();
    await pick(facetPage,'埼玉県');
    await pick(facetPage,'東京都');
    await facetPage.locator('#venue-region-done').click();
    assert.deepEqual(await places(facetPage),['埼玉県','東京都']);
    assert.equal(await facetPage.locator('#venue-region-dialog').isVisible(),false);
    assert.equal(await facetPage.evaluate(()=>document.activeElement.id),'venue-open-region');
    await facetPage.locator('#venue-open-region').click();
    await pick(facetPage,'東京都',false);
    assert.equal(await facetPage.locator('#venue-result-count').innerText(),'0 件');
    await facetPage.locator('#venue-region-done').click();
    await facetPage.locator('#venue-empty-state:not([hidden])').waitFor();
    await facetPage.locator('#venue-open-region').click();
    await zoom(facetPage,'東京都','tokyo');
    await zoom(facetPage,'23区','wards');
    await pick(facetPage,'新宿区');
    await facetPage.locator('#venue-region-done').click();
    assert.deepEqual(await places(facetPage),['埼玉県','新宿区']);
    await facetPage.reload();
    await facetPage.locator('#venue-filter-fields:not([disabled])').waitFor();
    assert.deepEqual(await places(facetPage),['埼玉県','新宿区']);
    assert.equal(await facetPage.locator('#venue-result-count').innerText(),expectedShinjuku+' 件');
    await facetPage.locator('#venue-reset-filters').click();
    await facetPage.locator('input[name=q]').fill('ＦＣ');
    const expectedPartial=catalog.courts.filter(row=>row.availability_status!=='SUSPENDED' && ['name','operator','municipality','area','address','surface','booking_method','booking_note','price_note'].map(k=>row[k]||'').join(' ').normalize('NFKC').toLowerCase().includes('fc')).length;
    await facetPage.waitForFunction(expected=>document.getElementById('venue-result-count').textContent===expected+' 件',expectedPartial);
    assert(expectedPartial>0);
    await facetPage.locator('#venue-reset-filters').click();
    for(const [field,value,predicate] of [
      ['booking_channel','phone',row=>row.booking_channels.includes('phone')],
      ['booking_channel','web',row=>row.booking_channels.includes('web')],
      ['registration','required',row=>row.registration_required===true],
      ['registration','unknown',row=>row.registration_required===null]
    ]) {
      await facetPage.locator('#venue-reset-filters').click();
      if(field==='registration') await facetPage.locator('.venue-extra-filters').evaluate(el=>el.open=true);
      await facetPage.locator(`[name=${field}]`).selectOption(value);
      const expected=catalog.courts.filter(row=>row.availability_status!=='SUSPENDED' && predicate(row)).length;
      assert.equal(await facetPage.locator('#venue-result-count').innerText(),expected.toLocaleString('ja-JP')+' 件');
      await facetPage.reload();
      await facetPage.locator('#venue-filter-fields:not([disabled])').waitFor();
      assert.equal(await facetPage.locator(`[name=${field}]`).inputValue(),value);
      assert.equal(await facetPage.locator('#venue-result-count').innerText(),expected.toLocaleString('ja-JP')+' 件');
    }
    await facetPage.locator('#venue-reset-filters').click();
    await facetPage.goto(base+'/venues?v_open_from=20%3A00&v_open_until=21%3A00');
    await facetPage.locator('#venue-filter-fields:not([disabled])').waitFor();
    assert.equal(await facetPage.locator('.venue-court-card').count(),12);
    await facetPage.locator('#venue-reset-filters').click();
    await facetPage.locator('[name=price_max]').fill('1,300');
    assert((await facetPage.locator('.venue-court-card').count())>0);
    await facetPage.locator('[name=price_max]').fill('not-a-price');
    assert.equal(await facetPage.locator('#venue-filter-error').isVisible(),true);
    await facetPage.locator('#venue-open-region').click();
    assert.equal(await facetPage.locator('#venue-region-dialog').isVisible(),false);
    assert.equal(await facetPage.evaluate(()=>document.activeElement.name),'price_max');
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
    assert.equal(await facetPage.locator('.venue-court-card').first().evaluate(el=>getComputedStyle(el).display),'grid');
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
    assert.deepEqual(await places(facetPage),['多摩']);
    assert.equal(await facetPage.locator('#venue-sort').inputValue(),'price');
    assert.equal(await facetPage.locator('.venue-court-card').first().evaluate(el=>getComputedStyle(el).display),'table-row');
    await facetPage.locator('.venue-region-panel[data-stage=tama]').waitFor({state:'attached'});
    await facetPage.goto(base+'/venues?v_area='+encodeURIComponent('23区'));
    await facetPage.locator('#venue-filter-fields:not([disabled])').waitFor();
    assert.deepEqual(await places(facetPage),['23区']);
    await facetPage.getByRole('link',{name:'設定',exact:true}).click();
    await facetPage.getByRole('button',{name:'初期設定に戻す',exact:true}).click();
    assert.equal(await facetPage.evaluate(()=>document.documentElement.dataset.cmView),'auto');
    await facetPage.locator('[name=rememberVenueSearch]').check();
    await facetPage.getByRole('button',{name:'設定を保存',exact:true}).click();
    await facetPage.goto(base+'/venues');
    await facetPage.locator('#venue-filter-fields:not([disabled])').waitFor();
    await facetPage.locator('#venue-open-region').click();
    await pick(facetPage,'多摩');
    await facetPage.locator('#venue-region-done').click();
    await facetPage.locator('#venue-filter-fields:not([disabled])').waitFor();
    await facetPage.goto(base+'/venues');
    await facetPage.locator('#venue-filter-fields:not([disabled])').waitFor();
    assert.deepEqual(await places(facetPage),['多摩']);
    assert.deepEqual(errors,[]);
    await facetPage.close();
    for(const width of [320,390,768,1440,1920]) {
      const page=await browser.newPage({viewport:{width,height:844}});
      await page.goto(base+'/venues?v_booking_channel=web');
      await page.locator('#venue-filter-fields:not([disabled])').waitFor();
      assert.equal(await page.locator('.venue-region-panel').isVisible(),false);
      await page.screenshot({path:path.join(out,`conditions-${width}.png`)});
      await page.locator('#venue-open-region').click();
      const dialog=page.locator('#venue-region-dialog');
      const bounds=await dialog.boundingBox();
      assert(bounds.x>=0 && bounds.x+bounds.width<=width+1 && bounds.y>=0 && bounds.y+bounds.height<=845);
      assert(await dialog.evaluate(el=>el.scrollWidth<=el.clientWidth+1));
      const countBefore=await page.locator('#venue-result-count').innerText();
      await pick(page,'23区');
      assert.equal(await dialog.evaluate(el=>el.open),true);
      assert.notEqual(await page.locator('#venue-result-count').innerText(),countBefore);
      await zoom(page,'23区','wards');
      await pick(page,'新宿区');
      await pick(page,'渋谷区');
      await page.screenshot({path:path.join(out,`region-dialog-${width}.png`)});
      const expected=catalog.courts.filter(row=>['新宿区','渋谷区'].includes(row.municipality) && row.booking_channels.includes('web') && row.availability_status!=='SUSPENDED').length;
      assert.equal(await page.locator('#venue-result-count').innerText(),expected+' 件');
      assert((await page.locator('#venue-region-result').innerText()).includes(expected+' 件'));
      await page.locator('#venue-region-done').click();
      assert((await page.locator('#venue-region-label').innerText()).includes('新宿区'));
      assert.equal(await page.evaluate(()=>document.activeElement.id),'venue-open-region');
      assert.equal(await page.locator('[name=booking_channel]').inputValue(),'web');
      assert(page.url().includes('v_places=') && page.url().includes('v_booking_channel=web'));
      const committedUrl=page.url();
      await page.locator('#venue-open-region').click();
      await page.locator('.venue-map-breadcrumbs').getByRole('link',{name:'関東',exact:true}).click();
      await page.locator('.venue-region-panel[data-stage=kanto]').waitFor();
      await pick(page,'東京都');
      await pick(page,'埼玉県');
      assert.equal(await page.locator('.venue-map-shape.is-active').count(),2);
      await page.screenshot({path:path.join(out,`region-prefectures-${width}.png`)});
      await page.locator('#venue-region-close').click();
      assert.equal(page.url(),committedUrl);
      assert.deepEqual(await places(page),['新宿区','渋谷区']);
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
      await page.close();
    }
    const mapFailure=await browser.newPage();
    await mapFailure.goto(base+'/venues');
    await mapFailure.locator('#venue-filter-fields:not([disabled])').waitFor();
    await mapFailure.locator('#venue-open-region').click();
    await mapFailure.route('**/venues?*',route=>route.abort());
    await pick(mapFailure,'23区');
    await mapFailure.getByRole('link',{name:'23区を詳しく選ぶ',exact:true}).click();
    await mapFailure.locator('#venue-map-error:not([hidden])').waitFor();
    assert.equal(await mapFailure.locator('#venue-region-selection').innerText(),'東京都 / 23区');
    assert.equal(await mapFailure.locator('#venue-result-count').innerText(),catalog.courts.filter(r=>r.area==='23区'&&r.availability_status!=='SUSPENDED').length.toLocaleString('ja-JP')+' 件');
    await mapFailure.unroute('**/venues?*');
    await mapFailure.locator('#venue-map-retry').click();
    await mapFailure.locator('.venue-region-panel[data-stage=wards]').waitFor();
    assert.equal(await mapFailure.locator('#venue-map-error').isVisible(),false);
    await mapFailure.close();
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
    await plain.getByRole('link',{name:'23区を詳しく選ぶ',exact:true}).click();
    await plain.waitForURL(/v_map=wards/);
    await plain.getByRole('link',{name:'新宿区',exact:true}).click();
    await plain.waitForURL(/v_places=/);
    assert.deepEqual(await places(plain),['新宿区']);
    assert(plain.url().includes('sport='));
    await plain.locator('#venue-places-filter').selectOption(['新宿区','渋谷区']);
    await plain.getByRole('button',{name:'条件を適用',exact:true}).click();
    assert.deepEqual(await places(plain),['新宿区','渋谷区']);
    assert.equal(new URL(plain.url()).searchParams.getAll('places').length,2);
    await plain.locator('#directoryContext [name=sport]').selectOption('テニス');
    await plain.getByRole('button',{name:'条件を変更する',exact:true}).click();
    assert.deepEqual(await places(plain),['新宿区','渋谷区']);
    await plain.locator('input[name=q]').fill('no-matching-venue-xyz');
    await plain.getByRole('button',{name:'条件を適用',exact:true}).click();
    await plain.waitForURL(/q=/);
    assert.equal(await plain.locator('.venue-court-card').count(),0);
    await plain.goto(base+'/venues?'+new URLSearchParams({v_q:'高円寺みんなの体育館'}));
    assert((await plain.locator('.venue-original-price').innerText()).includes('6,000円'));
    await plain.locator('.venue-court-details summary').click();
    assert((await plain.locator('.venue-tariff').innerText()).includes('1,500円'));
    assert.equal(await plain.locator('.venue-fee-link').count(),1);
    await plain.goto(base+'/venues?area='+encodeURIComponent('多摩'));
    assert.deepEqual(await places(plain),['多摩']);
    await plain.locator('[name=booking_channel]').selectOption('phone');
    await plain.locator('#venue-sort').selectOption('price');
    await plain.getByRole('button',{name:'条件を適用',exact:true}).click();
    assert.deepEqual(await places(plain),['多摩']);
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
    assert.equal(await device.locator('.venue-court-card').first().evaluate(el=>getComputedStyle(el).display),'table-row');
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
    await failed.locator('#venue-open-region').click();
    await zoom(failed,'23区','wards');
    await pick(failed,'新宿区');
    await failed.locator('#venue-region-done').click();
    await failed.waitForURL(/v_places=/);
    await failed.locator('#venue-error-state:not([hidden])').waitFor();
    assert(await failed.locator('.venue-court-card').count()>0);
    await failed.close();
    fs.writeFileSync(path.join(out,'results.json'),JSON.stringify(results,null,2));
    console.log(`PASS: ${results.length} sport/viewport combinations, 16 fee checks, multi-prefecture/municipality selection, apply/cancel/live preview, URL back/forward, 5 modal widths, map error/retry, normalized partial search, booking/registration/legacy-hours/price filters, reload, sorting, saved settings, forced mobile/desktop, 5 settings widths, no-JS multi-select, offline fallback`);
  } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;}).finally(()=>{if(server)server.kill();});
