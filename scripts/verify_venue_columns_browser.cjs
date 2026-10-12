const {chromium}=require('playwright');
const {spawn}=require('node:child_process');
const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'), out=path.join(root,'work/venue-columns-verification');
const base=process.env.VENUE_TEST_URL||'http://127.0.0.1:8904';
const results=[];
fs.mkdirSync(out,{recursive:true});
let server;
const ready=page=>page.locator('#venue-loading-state[hidden]').waitFor({state:'attached'});
const names=page=>page.locator('.venue-court-card h3').allTextContents();
async function open(page,column,positioned=true){
  const menu=page.locator(`[data-venue-column="${column}"] .venue-column-menu`);
  if(!await menu.isVisible()) await page.locator('#venue-column-toggle').click();
  await menu.locator('summary').click();
  await menu.locator('.venue-column-options').waitFor();
  // Native details queues its toggle event after becoming visible.
  if(positioned) await page.waitForFunction(key=>document.querySelector(`[data-venue-column="${key}"] .venue-column-options`).style.position==='fixed',column);
  return menu;
}
async function select(page,column,key,value){const menu=await open(page,column);await menu.locator(`[data-venue-control="${key}"][data-value="${value}"]`).click();}
(async()=>{
  if(!process.env.VENUE_TEST_URL){
    server=spawn(process.env.VENUE_PYTHON||'python',['-c',"import os,sys;sys.path.insert(0,'outputs');os.environ['CIRCLEMATCH_DB_PATH']='work/venue-columns-verification/unused.sqlite';from http.server import ThreadingHTTPServer;import circlematch_db_app as a;ThreadingHTTPServer(('127.0.0.1',8904),a.Handler).serve_forever()"],{cwd:root,stdio:['ignore','ignore','pipe']});
    server.stderr.on('data',data=>process.stderr.write(data));
    let connected=false;
    for(let i=0;i<100;i++){try{if((await fetch(base+'/api/venues')).ok){connected=true;break;}}catch{}await new Promise(r=>setTimeout(r,150));}
    assert(connected,'Preview server failed to start');
  }
  const browser=await chromium.launch({channel:'chrome',headless:true});
  try{
    const catalog=await(await fetch(base+'/api/venues')).json();
    const known=row=>row.price_from!==null||row.fee_options?.length>0;
    const byName=new Map(catalog.courts.map(row=>[row.name,row]));
    const errors=[];
    for(const width of [320,390,768,1440,1920]){
      const page=await browser.newPage({viewport:{width,height:1000}});
      page.on('pageerror',e=>errors.push(e.message));
      await page.goto(base+'/venues');await ready(page);
      assert.equal(await page.locator('#venue-sort').inputValue(),'available');
      assert((await names(page)).every(name=>known(byName.get(name))));
      assert.equal(await page.locator('.venue-column-menu').count(),6);
      for(const column of ['name','location','price','booking','registration','checked_asc']){
        const menu=await open(page,column);
        const rect=await menu.locator('.venue-column-options').boundingBox();
        assert(rect.x>=0&&rect.x+rect.width<=width+1);
        assert(rect.y>=0&&rect.y+rect.height<=1001);
        await page.keyboard.press('Escape');
        assert.equal(await menu.getAttribute('open'),null);
      }
      await page.locator('.venue-court-card').first().scrollIntoViewIfNeeded();
      const heights=await page.locator('.venue-court-card').evaluateAll(rows=>rows.slice(0,10).map(row=>row.getBoundingClientRect().height+row.nextElementSibling.getBoundingClientRect().height));
      const median=[...heights].sort((a,b)=>a-b)[5];
      assert(median<(width>900?155:width<=640?225:330),`Rows too large: ${width}: ${median}`);
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
      await page.screenshot({path:path.join(out,`list-${width}.png`)});
      const feeMenu=await open(page,'price');
      await feeMenu.locator('[data-venue-control="price_status"][data-value="missing"]').click();
      assert((await names(page)).every(name=>!known(byName.get(name))));
      assert(page.url().includes('v_price_status=missing'));
      await page.reload();await ready(page);
      assert.equal(await page.locator('[name=price_status]').inputValue(),'missing');
      await select(page,'price','price_status','available');
      await select(page,'booking','booking_channel','web');
      assert.equal(await page.locator('[name=booking_channel]').inputValue(),'web');
      assert((await names(page)).every(name=>byName.get(name).booking_channels.includes('web')&&known(byName.get(name))));
      await select(page,'registration','registration','required');
      assert((await names(page)).every(name=>byName.get(name).registration_required===true));
      await select(page,'location','sort','location_desc');
      assert.equal(await page.locator('#venue-sort').inputValue(),'location_desc');
      await page.goBack();
      await page.waitForFunction(()=>document.querySelector('#venue-sort').value==='available');
      await page.locator('#venue-reset-filters').click();
      const nameMenu=await open(page,'name');
      await nameMenu.locator('[name=name]').fill('駒沢');
      await page.waitForFunction(()=>[...document.querySelectorAll('.venue-court-card h3')].every(el=>el.textContent.includes('駒沢')));
      await page.keyboard.press('Escape');
      assert((await names(page)).some(name=>name.endsWith('第二球技場')));
      assert(!(await names(page)).some(name=>name.endsWith('第一球技場')));
      await select(page,'checked_asc','show_suspended','1');
      const first=page.locator('.venue-court-card').filter({hasText:'駒沢オリンピック公園総合運動場 第一球技場'});
      assert.equal(await first.count(),1,JSON.stringify({url:page.url(),names:await names(page),filters:await page.locator('#venue-court-filters').evaluate(form=>Object.fromEntries(new FormData(form)))}));
      assert((await first.locator('.venue-availability-note').innerText()).includes('2027年3月31日'));
      assert.equal(await first.locator('a[href^="/events/new"]').count(),0);
      await select(page,'name','name','');
      await select(page,'location','places','');
      const mapMenu=await open(page,'location');
      await mapMenu.locator('[data-venue-open-region]').click();
      assert(await page.locator('#venue-region-dialog').isVisible());
      await page.locator('#venue-region-close').click();
      results.push({width,medianRowHeight:median});
      await page.close();
    }
    const page=await browser.newPage({viewport:{width:1440,height:1000}});
    await page.goto(base+'/venues');await ready(page);
    const orders=await page.locator('#venue-sort option').evaluateAll(options=>options.map(o=>o.value));
    for(const order of orders){
      await page.locator('#venue-sort').selectOption(order);
      const html=await(await fetch(base+'/venues?'+new URLSearchParams({v_sort:order}))).text();
      const serverNames=await page.evaluate(html=>[...new DOMParser().parseFromString(html,'text/html').querySelectorAll('.venue-court-card h3')].map(h=>h.textContent),html);
      assert.deepEqual(await names(page),serverNames,`Hydration order differs: ${order}`);
    }
    const context=await browser.newContext({javaScriptEnabled:false,viewport:{width:1440,height:1000}});
    const plain=await context.newPage();
    await plain.goto(base+'/venues?'+new URLSearchParams({sport:'サッカー・フットサル',v_name:'駒沢'}));
    assert((await names(plain)).some(name=>name.endsWith('第二球技場')));
    const priceMenu=await open(plain,'price',false);
    await priceMenu.locator('[data-venue-control="sort"][data-value="price_desc"]').click();
    assert(plain.url().includes('v_name=')&&plain.url().includes('v_sort=price_desc'));
    assert((await names(plain)).some(name=>name.endsWith('第二球技場')));
    assert.equal(errors.length,0,errors.join('\n'));
    fs.writeFileSync(path.join(out,'results.json'),JSON.stringify({base,results,sorts:orders,errors},null,2));
    console.log('PASS: 5 widths, 6 column menus, filters, reload/back, all sort SSR parity, Komazawa, no-JS');
  }finally{await browser.close();if(server)server.kill();}
})().catch(error=>{if(server)server.kill();console.error(error);process.exitCode=1;});
