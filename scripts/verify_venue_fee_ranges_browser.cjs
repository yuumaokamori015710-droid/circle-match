const {chromium}=require('playwright');
const {spawn}=require('node:child_process');
const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),out=path.join(root,'work/venue-fee-ranges-verification');
const base=process.env.VENUE_TEST_URL||'http://127.0.0.1:8905';
const results=[];
let server;
fs.mkdirSync(out,{recursive:true});
const ready=page=>page.locator('#venue-loading-state[hidden]').waitFor({state:'attached'});
const label=range=>range.minimum.toLocaleString('ja-JP')+'円'+(range.minimum===range.maximum?'':'〜'+range.maximum.toLocaleString('ja-JP')+'円');
const query=name=>'/venues?'+new URLSearchParams({v_q:name});
(async()=>{
  if(!process.env.VENUE_TEST_URL){
    server=spawn(process.env.VENUE_PYTHON||'python',['-c',"import os,sys;sys.path.insert(0,'outputs');os.environ['CIRCLEMATCH_DB_PATH']='work/venue-fee-ranges-verification/unused.sqlite';from http.server import ThreadingHTTPServer;import circlematch_db_app as a;ThreadingHTTPServer(('127.0.0.1',8905),a.Handler).serve_forever()"],{cwd:root,stdio:['ignore','ignore','pipe']});
    server.stderr.on('data',data=>process.stderr.write(data));
    let connected=false;
    for(let i=0;i<100;i++){try{if((await fetch(base+'/api/venues')).ok){connected=true;break;}}catch{}await new Promise(r=>setTimeout(r,150));}
    assert(connected,'Preview did not start');
  }
  const browser=await chromium.launch({channel:'chrome',headless:true});
  try{
    const catalog=await(await fetch(base+'/api/venues')).json();
    const errors=[];
    const ids=['tokyo-sports-017','tokyo-sports-018','tokyo-venue-e34356792fd2','tokyo-venue-3ba2d17ed46e','okutama-kawai','inagi-kitamidori'];
    for(const width of [320,390,768,1440,1920]){
      const page=await browser.newPage({viewport:{width,height:1000}});
      page.on('pageerror',error=>errors.push(error.message));
      await page.goto(base+'/venues');await ready(page);
      const metrics=await page.locator('.venue-price-amount').evaluateAll(spans=>spans.map(span=>({
        right:span.getBoundingClientRect().right,
        font:getComputedStyle(span).fontVariantNumeric,
        fits:span.getBoundingClientRect().left>=span.closest('td').getBoundingClientRect().left-1
      })));
      assert(metrics.length>10);
      assert(Math.max(...metrics.map(m=>m.right))-Math.min(...metrics.map(m=>m.right))<=1,'Amounts are not vertically aligned');
      assert(metrics.every(m=>m.font.includes('tabular-nums')&&m.fits));
      for(const id of ids){
        const row=catalog.courts.find(r=>r.id===id);
        assert(row);
        await page.goto(base+query(row.name));await ready(page);
        const card=page.locator('.venue-court-card').filter({has:page.getByRole('heading',{name:row.name,exact:true})});
        assert.equal(await card.count(),1);
        assert.deepEqual(await card.locator('.venue-price-amount').allTextContents(),row.fee_ranges.slice(0,2).map(label));
        assert.deepEqual(await card.locator('.venue-price-unit').allTextContents(),row.fee_ranges.slice(0,2).map(r=>r.unit));
        if(!row.fee_ranges.length) assert.equal(await card.locator('.venue-unconfirmed').textContent(),'金額未取得');
        if(row.fee_options?.length){
          await card.locator('.venue-tariff-more').click();
          const amounts=card.locator('xpath=following-sibling::tr[1]').locator('.venue-tariff-amount');
          assert.equal(await amounts.count(),row.fee_options.length);
          const edges=await amounts.evaluateAll(cells=>cells.map(c=>c.getBoundingClientRect().right));
          assert(Math.max(...edges)-Math.min(...edges)<=1);
          const caption=await card.locator('xpath=following-sibling::tr[1]').locator('.venue-tariff caption').boundingBox();
          assert(caption.width>100&&caption.height<40,'Tariff caption wrapped vertically');
        }
        assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),`Overflow: ${width},${id}`);
        if(id==='tokyo-venue-3ba2d17ed46e'&&[390,1440].includes(width)){
          await card.scrollIntoViewIfNeeded();
          await page.evaluate(()=>scrollBy(0,-85));
          await page.screenshot({path:path.join(out,`ranges-${width}.png`)});
        }
      }
      results.push({width,alignedAmounts:metrics.length,feeCases:ids.length});
      await page.close();
    }
    const context=await browser.newContext({javaScriptEnabled:false,viewport:{width:1440,height:1000}});
    const page=await context.newPage();
    for(const id of ids.slice(0,4)){
      const row=catalog.courts.find(r=>r.id===id);
      await page.goto(base+query(row.name));
      const card=page.locator('.venue-court-card').filter({has:page.getByRole('heading',{name:row.name,exact:true})});
      assert.deepEqual(await card.locator('.venue-price-amount').allTextContents(),row.fee_ranges.slice(0,2).map(label));
    }
    await context.close();
    assert.deepEqual(errors,[]);
    fs.writeFileSync(path.join(out,'results.json'),JSON.stringify({base,results,noJavaScriptCases:4,errors},null,2));
    console.log(JSON.stringify({results,noJavaScriptCases:4,errors}));
  }finally{await browser.close();}
})().catch(error=>{console.error(error);process.exitCode=1;}).finally(()=>{if(server)server.kill();});
