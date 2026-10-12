const {chromium}=require('playwright');
const {spawn}=require('node:child_process');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const path=require('node:path');
const root=path.resolve(__dirname,'..'),out=path.join(root,'work/circle-map-verification');
fs.mkdirSync(out,{recursive:true});
let server,base=process.env.CIRCLE_TEST_URL;
const results=[];
const selected=page=>page.locator('#circle-region-picker').evaluate(el=>JSON.parse(el.dataset.state).selected);
const ready=page=>page.locator('#circle-region-picker:not([aria-busy])').waitFor();
async function pick(page,place){await page.locator('.circle-map-choice').filter({hasText:place}).first().click();await ready(page)}
(async()=>{
  if(!base){
    server=spawn(process.env.VENUE_PYTHON||'python',['-u','-c',"import sys;sys.path.insert(0,'scripts');from test_circle_regions import CircleRegionTests as T;T.setUpClass();print(T.base,flush=True);sys.stdin.read();T.doClassCleanups()"],{cwd:root,stdio:['pipe','pipe','pipe']});
    base=await new Promise((resolve,reject)=>{let text='';server.stdout.on('data',data=>{text+=data;const match=text.match(/http:\/\/127\.0\.0\.1:\d+/);if(match)resolve(match[0])});server.stderr.on('data',data=>process.stderr.write(data));server.on('exit',code=>reject(Error('test server exit '+code)));setTimeout(()=>reject(Error('server startup timeout')),30000).unref()});
  }
  const browser=await chromium.launch({channel:'chrome',headless:true});
  try{
    for(const width of [320,390,768,1440,1920])for(const [pathname,audience,modern] of [['/','university',true],['/','social',true],['/circles','university',false],['/social/circles','social',false]]){
      const page=await browser.newPage({viewport:{width,height:1000}}),errors=[];
      page.on('pageerror',e=>errors.push(e.message));
      const query=new URLSearchParams({tab:'db',audience,c_map:'wards',sport:'サッカー・フットサル'});
      await page.goto(base+pathname+'?'+query,{waitUntil:'domcontentloaded'});
      await page.waitForFunction(()=>!!document.querySelector('#circle-region-picker')&&!document.querySelector('#circle-region-picker').hasAttribute('aria-busy'));
      if(!modern)await page.waitForTimeout(300);
      assert(await page.locator('#circle-region-picker').isVisible());
      assert.equal(await page.locator('dialog').count(),0);
      await pick(page,'新宿区');await pick(page,'渋谷区');
      assert.deepEqual(await selected(page),['新宿区','渋谷区']);
      const expected=await (await fetch(base+'/api/circle-stats?'+new URLSearchParams({audience,places:'新宿区,渋谷区',sport:'サッカー・フットサル'}))).json();
      const count=modern?'#dbCircles':'#circleCount';
      await page.waitForFunction(({selector,n})=>document.querySelector(selector).textContent===String(n),{selector:count,n:expected.circles});
      assert.equal(await page.locator('.circle-map-shape.is-active').count(),2);
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
      await page.locator('#circle-region-picker').scrollIntoViewIfNeeded();
      await page.screenshot({path:path.join(out,`${modern?'tab':'detail'}-${audience}-${width}.png`)});
      const committed=page.url();await page.reload();await ready(page);
      assert.deepEqual(await selected(page),['新宿区','渋谷区']);
      await pick(page,'渋谷区');await page.goBack();await ready(page);
      assert.deepEqual(await selected(page),['新宿区','渋谷区']);
      assert.equal(page.url(),committed);
      await page.locator('.circle-map-breadcrumbs').getByRole('link',{name:'関東',exact:true}).click();await ready(page);
      await pick(page,'東京都');await pick(page,'埼玉県');
      assert.deepEqual(await selected(page),['東京都','埼玉県']);
      if(modern){
        await page.locator('#directoryContext [name=sport]').selectOption('テニス');await page.waitForURL(url=>url.searchParams.get('sport')==='テニス');await ready(page);
        assert.deepEqual(await selected(page),['東京都','埼玉県']);
        await page.locator('.db-toggle a').filter({hasText:audience==='university'?'社会人':'大学'}).click();await ready(page);
        assert.deepEqual(await selected(page),['東京都','埼玉県']);
      }else{
        await page.locator('#q').fill('no-circle-map-result-xyz');
        await page.waitForFunction(()=>document.querySelector('#circleCount').textContent==='0');
        assert.deepEqual(await selected(page),['東京都','埼玉県']);
      }
      assert.deepEqual(errors,[]);
      results.push({width,pathname,audience,matched:expected.circles});await page.close();
    }
    const context=await browser.newContext({javaScriptEnabled:false,viewport:{width:390,height:844}});
    for(const pathname of ['/','/circles','/social/circles']){
      const page=await context.newPage();await page.goto(base+pathname+'?tab=db&c_map=wards');
      await pick(page,'新宿区');await pick(page,'渋谷区');
      assert.deepEqual(await selected(page),['新宿区','渋谷区']);
      assert(await page.locator(pathname==='/'?'.circle-row':'#rows tr').count()>0);
      if(pathname==='/'){
        await page.locator('#directoryContext [name=sport]').selectOption('テニス');
        await page.getByRole('button',{name:'条件を変更する',exact:true}).click();
        assert.deepEqual(await selected(page),['新宿区','渋谷区']);
      }
      await page.close();
    }
    await context.close();
    const failed=await browser.newPage();await failed.goto(base+'/?tab=db&c_map=wards');
    await failed.route('**/api/circle-map*',route=>route.abort());
    await failed.locator('.circle-map-choice').filter({hasText:'新宿区'}).click();
    await failed.locator('#circle-region-error').waitFor();
    await failed.unroute('**/api/circle-map*');
    await failed.getByRole('button',{name:'再試行',exact:true}).click();await ready(failed);
    assert.deepEqual(await selected(failed),['新宿区']);
    await failed.route('**/api/circles?*',route=>route.abort());
    await pick(failed,'渋谷区');await failed.locator('#dbList .error-box').waitFor();
    assert.equal(await failed.locator('#dbCircles').innerText(),'取得失敗');await failed.close();
    fs.writeFileSync(path.join(out,'results.json'),JSON.stringify({base,results,noJS:'PASS',retry:'PASS'},null,2));
    console.log('PASS: '+results.length+' circle views/widths; multi-region filtering, SSR, audience/sport switching, reload/back, no-JS, failure/retry');
  }finally{await browser.close()}
})().catch(error=>{console.error(error);process.exitCode=1}).finally(()=>{
  if(server){server.stdin.end();setTimeout(()=>{if(server.exitCode===null)server.kill()},3000).unref()}
});
