const assert = require('node:assert/strict');
const vm = require('node:vm');
const source = require('node:fs').readFileSync(0, 'utf8');
function setup({auto=true,native=false,copyFailure=false,abort=false}={}) {
  const nodes = new Map();
  const element = id => {
    if (!nodes.has(id)) nodes.set(id, {textContent:'',value:'',events:{},dataset:{},
      addEventListener(type,fn){this.events[type]=fn},focus(){this.focused=true},select(){this.selected=true},
      showModal(){this.open=true},close(){this.open=false;this.events.close?.()}});
    return nodes.get(id);
  };
  const instagram=element('instagram'),tiktok=element('tiktok'),button=element('trigger');
  instagram.dataset.copyShare='Instagram';tiktok.dataset.copyShare='TikTok';
  const calls=[];
  const navigator={clipboard:{async writeText(value){if(copyFailure)throw Error('denied');calls.push(['copy',value])}}};
  if(native)navigator.share=async data=>{calls.push(['share',data]);if(abort)throw {name:'AbortError'}};
  const context=vm.createContext({navigator,URL,URLSearchParams,
    location:{origin:'https://circle-match.example',href:'https://circle-match.example/events/abc?published=1&secret=do-not-share'},
    history:{state:null,replaceState(...args){calls.push(['history',...args])}},
    document:{getElementById:element,querySelector:()=>button,
      querySelectorAll:selector=>selector==='[data-share-event]'?[button]:[instagram,tiktok]}});
  vm.runInContext(source.replace(/<\/?script>/g,'').replace('__SHARE_EVENT__',JSON.stringify({path:'/events/abc',title:'募集 & test',text:'開催日時: 2030/06/01\n会場: 東京\n定員: 20人\n締切: 5/31\n内容: 交流\n参加条件: 初心者可',xText:'募集の要約',auto})),context);
  return {element,calls,instagram,tiktok,button};
}
(async()=>{
  const basic=setup();
  assert.equal(basic.element('eventShareDialog').open,true);
  assert.match(basic.element('shareHeading').textContent,/掲載しました/);
  assert.equal(basic.element('shareUrl').value,'https://circle-match.example/events/abc');
  for(const id of ['shareLine','shareX']){
    const url=new URL(basic.element(id).href);assert.equal(url.searchParams.get('url'),'https://circle-match.example/events/abc');
    assert(id==='shareLine'?url.searchParams.get('text').includes('参加条件: 初心者可'):url.searchParams.get('text')==='募集の要約');assert(!url.href.includes('secret'));
  }
  await basic.instagram.events.click();assert.match(basic.element('shareStatus').textContent,/コピーしました。Instagram/);
  assert.equal(basic.calls.filter(x=>x[0]==='copy').length,1);assert(basic.calls[1][1].includes('参加条件: 初心者可'));assert(!basic.calls.some(x=>x[0]==='share'));
  basic.element('closeShare').onclick();assert.equal(basic.element('eventShareDialog').open,false);assert(basic.button.focused);
  const native=setup({auto:false,native:true});assert(!native.element('eventShareDialog').open);
  await native.tiktok.events.click();assert(!native.calls.some(x=>x[0]==='share'));await native.element('shareMore').onclick();assert.equal(native.calls.find(x=>x[0]==='share')[1].url,'https://circle-match.example/events/abc');
  const cancelled=setup({native:true,abort:true});await cancelled.element('shareMore').onclick();assert(!cancelled.calls.some(x=>x[0]==='copy'));
  const failure=setup({copyFailure:true});await failure.element('copyShareLink').onclick();assert(failure.element('shareText').selected);assert.match(failure.element('shareStatus').textContent,/コピーできませんでした/);
  const fallback=setup({auto:false});await fallback.element('shareMore').onclick();assert(fallback.calls.some(x=>x[0]==='copy'));assert.match(fallback.element('shareStatus').textContent,/対応していません/);
  console.log('sharing: ok');
})().catch(error=>{console.error(error);process.exitCode=1});
