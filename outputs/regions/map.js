(()=>{
  let picker=document.getElementById('circle-region-picker');
  const dialog=document.getElementById('circle-region-dialog'),opener=document.getElementById('circle-open-region');
  if(!picker||!dialog||!opener)return;
  let state=JSON.parse(picker.dataset.state),request=0,controller,draft=null;
  let committed={selected:[...state.selected],stage:state.stage};
  const current=()=>new URL(location.href);
  function toggle(place){
    const parents=item=>{const result=[];while(state.parents[item]){item=state.parents[item];result.push(item)}return result};
    return draft.selected.includes(place)?draft.selected.filter(p=>p!==place):draft.selected.filter(p=>!parents(place).includes(p)&&!parents(p).includes(place)).concat(place);
  }
  function paint(){
    const places=draft?.selected||state.selected;
    for(const element of picker.querySelectorAll('[data-place]')){
      let place=element.dataset.place,checked=places.includes(place);
      while(!checked&&state.parents[place]){place=state.parents[place];checked=places.includes(place)}
      element.classList.toggle('is-active',checked);element.setAttribute('aria-checked',String(checked));
      const check=element.querySelector('.circle-map-check');if(check)check.textContent=checked?'\u2713':'';
    }
    picker.dataset.state=JSON.stringify({...state,...draft});
    picker.querySelector('.circle-region-selection strong').textContent=places.join('・')||'全国';
    document.getElementById('circle-region-result').textContent=places.join('・')||'全国';
    if(!draft)document.getElementById('circle-region-label').textContent=places.join('・')||'全国';
  }
  function syncFields(){
    const url=current();
    for(const form of document.querySelectorAll('#dbFilters,#directoryContext')){
      for(const key of ['places','c_map']){
        let input=form.elements.namedItem(key);
        if(!input){input=document.createElement('input');input.type='hidden';input.name=key;form.append(input)}
        input.value=(key==='places'?url.searchParams.getAll(key).join(','):url.searchParams.get(key))||'';
      }
      for(const key of ['region','prefecture']){const input=form.elements.namedItem(key);if(input)input.value=url.searchParams.get(key)||''}
      if(url.searchParams.has('places')&&form.elements.namedItem('area'))form.elements.namedItem('area').value='';
    }
    for(const [id,key] of [['regionFilter','region'],['prefFilter','prefecture']]){const input=document.getElementById(id);if(input)input.value=url.searchParams.has('places')?'':url.searchParams.get(key)||''}
    document.querySelectorAll('a[href]').forEach(link=>{
      const raw=link.getAttribute('href');if(!raw.startsWith('/')||link.closest('#circle-region-picker'))return;
      const target=new URL(raw,location.origin);
      if(!['/circles','/social/circles'].includes(target.pathname)&&!(target.pathname==='/'&&target.searchParams.get('tab')==='db'))return;
      for(const key of ['places','c_map']){if(url.searchParams.has(key))target.searchParams.set(key,key==='places'?url.searchParams.getAll(key).join(','):url.searchParams.get(key));else target.searchParams.delete(key)}
      if(url.searchParams.has('places')){target.searchParams.delete('region');target.searchParams.delete('prefecture')}
      link.href=target.pathname+target.search+target.hash;
    });
  }
  async function refresh(){
    const latest=++request;
    controller?.abort();controller=new AbortController();
    picker.setAttribute('aria-busy','true');
    const url=current();url.pathname='/api/circle-map';url.searchParams.set('path',location.pathname);
    if(draft){url.searchParams.set('places',draft.selected.join(','));url.searchParams.set('c_map',draft.stage);url.searchParams.delete('region');url.searchParams.delete('prefecture')}
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
      const hadFocus=picker.contains(document.activeElement);
      const focusPlace=focused?.dataset.place;
      picker.replaceWith(next);picker=next;state=JSON.parse(picker.dataset.state);
      if(draft)draft={selected:[...state.selected],stage:state.stage};
      else committed={selected:[...state.selected],stage:state.stage};
      if(same)picker.querySelector('.circle-map-choices').scrollTop=scroll;
      if(focusPlace){const candidates=[...picker.querySelectorAll('.circle-map-choice')];candidates.find(el=>el.dataset.place===focusPlace)?.focus({preventScroll:true})}
      else if(focused)picker.querySelector('[aria-current=page]')?.focus({preventScroll:true});
      else if(hadFocus&&dialog.open)document.getElementById('circle-region-dialog-title').focus({preventScroll:true});
      paint();syncFields();
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
    if(!draft)return;
    const target=new URL(link.href);
    draft.stage=target.searchParams.get('c_map')||state.stage;
    if(link.dataset.place||link.classList.contains('circle-region-clear')){
      draft.selected=link.dataset.place?toggle(link.dataset.place):[];
    }
    paint();refresh();
  });
  opener.addEventListener('click',()=>{
    draft={selected:[...committed.selected],stage:committed.stage};paint();
    dialog.showModal();document.body.classList.add('circle-modal-open');refresh();
  });
  document.getElementById('circle-region-close').addEventListener('click',()=>dialog.close());
  document.getElementById('circle-region-done').addEventListener('click',()=>{
    if(!draft)return;
    const url=current();url.searchParams.set('places',draft.selected.join(','));url.searchParams.set('c_map',draft.stage);
    for(const key of ['region','prefecture','page'])url.searchParams.delete(key);url.hash='';
    if(url.href!==location.href)history.pushState(null,'',url.pathname+url.search);
    committed={selected:[...draft.selected],stage:draft.stage};state={...state,...committed};draft=null;paint();syncFields();dialog.close();
    document.dispatchEvent(new Event('circle-region-change'));
  });
  dialog.addEventListener('close',()=>{
    draft=null;state={...state,...committed};paint();document.body.classList.remove('circle-modal-open');refresh();
  });
  dialog.addEventListener('click',event=>{
    if(event.target!==dialog)return;
    const rect=dialog.getBoundingClientRect();
    if(event.clientX<rect.left||event.clientX>rect.right||event.clientY<rect.top||event.clientY>rect.bottom)dialog.close();
  });
  document.addEventListener('keydown',event=>{if(event.key===' '&&event.target.matches('#circle-region-picker [role=checkbox]')){event.preventDefault();event.target.click()}});
  document.addEventListener('circle-filters-updated',()=>{syncFields();refresh()});
  window.addEventListener('popstate',()=>{syncFields();if(dialog.open){draft=null;dialog.close()}else refresh()});
  paint();syncFields();
})();
