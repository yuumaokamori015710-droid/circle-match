const {chromium}=require('playwright');
const {spawn}=require('node:child_process');
const fs=require('node:fs');
const path=require('node:path');
const assert=require('node:assert/strict');
const root=path.resolve(__dirname,'..'),out=path.join(root,'work/venue-mobile-verification');
const base=process.env.VENUE_TEST_URL||'http://127.0.0.1:8906';
const results=[],errors=[];
let server;
fs.mkdirSync(out,{recursive:true});
const ready=page=>page.locator('#venue-loading-state[hidden]').waitFor({state:'attached'});
async function measure(page,mobile){
  assert.equal(await page.locator('.venue-intro .venue-coverage-note').first().isVisible(),!mobile);
  assert.equal(await page.locator('#venue-column-toggle').isVisible(),mobile);
  assert.equal(await page.locator('#venue-column-controls').isVisible(),!mobile);
  assert.equal(await page.locator('[name=price_max]').locator('xpath=ancestor::label').locator('small').count(),0);
  const metrics=await page.locator('.venue-court-card').evaluateAll((rows,mobile)=>rows.map(row=>{
    const rect=el=>el.getBoundingClientRect(),price=rect(row.querySelector('.venue-court-price'));
    const location=rect(row.querySelector('.venue-location-cell'));
    const links=[...row.querySelectorAll('.venue-court-links>a')].map(rect);
    const detail=rect(row.nextElementSibling.querySelector('summary'));
    const amounts=[...row.querySelectorAll('.venue-price-amount')].map(rect);
    return {height:rect(row).height+rect(row.nextElementSibling).height,
      sideBySide:!mobile||price.left>=location.right-1,
      amountsFit:amounts.every(r=>r.left>=price.left-1&&r.right<=price.right+1),
      touchTargets:!mobile||links.every(r=>r.height>=44&&r.width>=44),
      actionsFit:links.every(r=>r.left>=rect(row).left&&r.right<=rect(row).right+1),
      detailFits:!mobile||(detail.height>=44&&detail.width>=44&&links.every(r=>r.right<=detail.left-4)&&Math.abs(detail.bottom-links[0].bottom)<=1)};
  }),mobile);
  assert(metrics.every(m=>m.sideBySide&&m.amountsFit&&m.touchTargets&&m.actionsFit&&m.detailFits),JSON.stringify(metrics.filter(m=>!m.sideBySide||!m.amountsFit||!m.touchTargets||!m.actionsFit||!m.detailFits)));
  const median=metrics.map(m=>m.height).sort((a,b)=>a-b)[Math.floor(metrics.length/2)];
  assert(median<(mobile?215:330),`Large rows: ${median}`);
  assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'Horizontal overflow');
  return {medianRowHeight:median,rows:metrics.length};
}
(async()=>{
  if(!process.env.VENUE_TEST_URL){
    server=spawn(process.env.VENUE_PYTHON||'python',['-c',"import os,sys;sys.path.insert(0,'outputs');os.environ['CIRCLEMATCH_DB_PATH']='work/venue-mobile-verification/unused.sqlite';from http.server import ThreadingHTTPServer;import circlematch_db_app as a;ThreadingHTTPServer(('127.0.0.1',8906),a.Handler).serve_forever()"],{cwd:root,stdio:['ignore','ignore','pipe']});
    server.stderr.on('data',data=>process.stderr.write(data));
    let connected=false;
    for(let i=0;i<100;i++){try{if((await fetch(base+'/api/venues')).ok){connected=true;break;}}catch{}await new Promise(r=>setTimeout(r,150));}
    assert(connected,'Preview did not start');
  }
  const browser=await chromium.launch({channel:'chrome',headless:true});
  try{
    for(const width of [320,360,390,430,768,1440,1920]){
      const page=await browser.newPage({viewport:{width,height:900}});
      page.on('pageerror',e=>errors.push(e.message));
      await page.goto(base+'/venues');await ready(page);
      await page.locator('.venue-court-card').first().scrollIntoViewIfNeeded();
      await page.screenshot({path:path.join(out,`initial-list-${width}.png`)});
      const metrics=await measure(page,width<=640);
      if(width<=640){
        const toggle=page.locator('#venue-column-toggle');
        await toggle.focus();await page.keyboard.press('Enter');
        assert.equal(await toggle.getAttribute('aria-expanded'),'true');
        assert(await page.locator('#venue-column-controls').isVisible());
        const menu=page.locator('[data-venue-column=price]');
        await menu.locator('summary').click();
        await menu.locator('[data-venue-control=price_status][data-value=missing]').click();
        assert(await toggle.evaluate(el=>el.classList.contains('is-filtered')));
        assert(await page.locator('.venue-unconfirmed').count()>0);
        await toggle.click();
        assert.equal(await page.locator('#venue-column-controls').isVisible(),false);
        await page.locator('#venue-reset-filters').click();
        const coverage=page.locator('.venue-mobile-coverage');
        await coverage.locator('summary').click();
        assert(await coverage.locator('p').first().isVisible());
        await coverage.locator('summary').click();
      }
      if([390,1440].includes(width)){
        await page.screenshot({path:path.join(out,`overview-${width}.png`)});
        await page.locator('#venue-court-results').scrollIntoViewIfNeeded();
        await page.evaluate(()=>scrollBy(0,-85));
        await page.screenshot({path:path.join(out,`list-${width}.png`)});
      }
      results.push({width,...metrics});await page.close();
    }
    const forced=await browser.newPage({viewport:{width:1440,height:1000}});
    await forced.addInitScript(()=>localStorage.setItem('circlematch.preferences.v1',JSON.stringify({view:'mobile'})));
    await forced.goto(base+'/venues');await ready(forced);
    assert.equal(await forced.evaluate(()=>Math.round(document.body.getBoundingClientRect().width)),390);
    results.push({forcedMobile:true,...await measure(forced,true)});
    await forced.locator('#venue-court-results').scrollIntoViewIfNeeded();
    await forced.screenshot({path:path.join(out,'forced-mobile.png')});await forced.close();
    for(const width of [390,1440]){
      const context=await browser.newContext({javaScriptEnabled:false,viewport:{width,height:900}});
      const page=await context.newPage();await page.goto(base+'/venues');
      assert.equal(await page.locator('.venue-court-card').count(),50);
      assert(await page.locator('#venue-column-controls').isVisible());
      assert.equal(await page.locator('#venue-column-toggle').isVisible(),false);
      await page.locator('[data-venue-column=price] summary').click();
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1),'No-JS filter overflow');
      await page.locator('[data-venue-control=price_status][data-value=missing]').click();
      assert(page.url().includes('v_price_status=missing'));
      assert(await page.locator('.venue-unconfirmed').count()>0);
      assert(await page.evaluate(()=>document.documentElement.scrollWidth<=innerWidth+1));
      await context.close();
    }
    assert.deepEqual(errors,[]);
    fs.writeFileSync(path.join(out,'results.json'),JSON.stringify({base,results,noJavaScriptCases:2,errors},null,2));
    console.log(JSON.stringify({results,noJavaScriptCases:2,errors}));
  }finally{await browser.close();if(server)server.kill();}
})().catch(error=>{if(server)server.kill();console.error(error);process.exitCode=1;});
