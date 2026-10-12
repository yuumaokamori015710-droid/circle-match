(()=>{
  let picker=document.getElementById('circle-region-picker');
  if(!picker)return;
  let state=JSON.parse(picker.dataset.state),request=0,controller;
  const current=()=>new URL(location.href);
  function toggle(place){
    const parents=item=>{const result=[];while(state.parents[item]){item=state.parents[item];result.push(item)}return result};
    return state.selected.includes(place)?state.selected.filter(p=>p!==place):state.selected.filter(p=>!parents(place).includes(p)&&!parents(p).includes(place)).concat(place);
  }
  function syncFields(){
    const url=current();
    for(const form of document.querySelectorAll('#dbFilters,#directoryContext')){
      for(const key of ['places','c_map']){
        let input=form.elements.namedItem(key);
        if(!input){input=document.createElement('input');input.type='hidden';input.name=key;form.append(input)}
        input.value=url.searchParams.get(key)||'';
      }
      for(const key of ['region','prefecture']){const input=form.elements.namedItem(key);if(input)input.value=url.searchParams.get(key)||''}
      if(url.searchParams.has('places')&&form.elements.namedItem('area'))form.elements.namedItem('area').value='';
    }
    for(const [id,key] of [['regionFilter','region'],['prefFilter','prefecture']]){const input=document.getElementById(id);if(input)input.value=url.searchParams.has('places')?'':url.searchParams.get(key)||''}
    document.querySelectorAll('a[href]').forEach(link=>{
      const raw=link.getAttribute('href');if(!raw.startsWith('/')||link.closest('#circle-region-picker'))return;
      const target=new URL(raw,location.origin);
      if(!['/circles','/social/circles'].includes(target.pathname)&&!(target.pathname==='/'&&target.searchParams.get('tab')==='db'))return;
      for(const key of ['places','c_map']){if(url.searchParams.has(key))target.searchParams.set(key,url.searchParams.get(key));else target.searchParams.delete(key)}
      if(url.searchParams.has('places')){target.searchParams.delete('region');target.searchParams.delete('prefecture')}
      link.href=target.pathname+target.search+target.hash;
    });
  }
  async function refresh(){
    const latest=++request;
    controller?.abort();controller=new AbortController();
    picker.setAttribute('aria-busy','true');
    const url=current();url.pathname='/api/circle-map';url.searchParams.set('path',location.pathname);
    try{
      const response=await fetch(url.pathname+url.search,{signal:controller.signal});
      const data=await response.json();if(!response.ok)throw Error(data.error||'地域データを取得できませんでした');
      if(latest!==request)return;
      const template=document.createElement('template');template.innerHTML=data.html;
      const next=template.content.querySelector('#circle-region-picker');
      if(!next)throw Error('地域データを取得できませんでした');
      const scroll=picker.querySelector('.circle-map-choices').scrollTop;
      const same=state.stage===JSON.parse(next.dataset.state).stage;
      const focused=document.activeElement.closest('[data-place],.circle-map-zoom,.circle-map-breadcrumbs a,.circle-region-clear');
      const focusPlace=focused?.dataset.place;
      picker.replaceWith(next);picker=next;state=JSON.parse(picker.dataset.state);
      if(same)picker.querySelector('.circle-map-choices').scrollTop=scroll;
      if(focusPlace){const candidates=[...picker.querySelectorAll('.circle-map-choice')];candidates.find(el=>el.dataset.place===focusPlace)?.focus({preventScroll:true})}
      else if(focused)picker.querySelector('[aria-current=page]')?.focus({preventScroll:true});
      syncFields();
    }catch(error){
      if(error.name==='AbortError'||latest!==request)return;
      let box=document.getElementById('circle-region-error');
      if(!box){box=document.createElement('div');box.id='circle-region-error';box.className='circle-region-error';box.setAttribute('role','status');picker.prepend(box)}
      box.textContent='地域データを取得できませんでした。';
      const button=document.createElement('button');button.type='button';button.textContent='再試行';button.onclick=refresh;box.append(button);
    }finally{if(latest===request)picker.removeAttribute('aria-busy')}
  }
  document.addEventListener('click',event=>{
    const link=event.target.closest('#circle-region-picker a[href]');
    if(!link||event.ctrlKey||event.metaKey||event.shiftKey||event.altKey||link.target==='_blank')return;
    event.preventDefault();
    const url=current(),target=new URL(link.href);
    url.searchParams.set('c_map',target.searchParams.get('c_map')||state.stage);
    if(link.dataset.place||link.classList.contains('circle-region-clear')){
      state.selected=link.dataset.place?toggle(link.dataset.place):[];
      url.searchParams.set('places',state.selected.join(','));
      url.searchParams.delete('region');url.searchParams.delete('prefecture');url.searchParams.delete('page');url.hash='';
    }
    if(url.href!==location.href)history.pushState(null,'',url.pathname+url.search+url.hash);
    syncFields();refresh();
    if(link.dataset.place||link.classList.contains('circle-region-clear'))document.dispatchEvent(new Event('circle-region-change'));
  });
  document.addEventListener('keydown',event=>{if(event.key===' '&&event.target.matches('#circle-region-picker [role=checkbox]')){event.preventDefault();event.target.click()}});
  document.addEventListener('circle-filters-updated',()=>{syncFields();refresh()});
  window.addEventListener('popstate',()=>{syncFields();refresh()});
  syncFields();
})();
