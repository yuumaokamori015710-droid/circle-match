"use strict";
(() => {
  const KEY="circlematch.preferences.v1", VENUES="circlematch.venue-search.v1.";
  const defaults={view:"auto",venueArea:"",venueSort:"name",rememberVenueSearch:false};
  function get() {
    let raw={};
    try {raw=JSON.parse(localStorage.getItem(KEY)) || {};} catch {}
    return {view:["auto","mobile","desktop"].includes(raw.view)?raw.view:"auto",
      venueArea:["","23区","多摩","島しょ"].includes(raw.venueArea)?raw.venueArea:"",
      venueSort:["name","price"].includes(raw.venueSort)?raw.venueSort:"name",
      rememberVenueSearch:raw.rememberVenueSearch===true};
  }
  window.CircleMatchSettings={get,
    getVenue(scope) {try {return JSON.parse(localStorage.getItem(VENUES+scope)) || {};}catch{return {}; }},
    saveVenue(scope,filters) {if(get().rememberVenueSearch)try{localStorage.setItem(VENUES+scope,JSON.stringify(filters));}catch{}}
  };
  const originalMedia=new WeakMap();
  let originalViewport=null, requested=false, lastMode="auto";
  function apply() {
    // Settings stay device-sized so a phone can always leave desktop mode.
    const mode=location.pathname==="/settings"?"auto":get().view;
    document.documentElement.dataset.cmView=mode;
    const viewport=document.querySelector('meta[name="viewport"]');
    if(viewport) {
      originalViewport ??= viewport.content;
      viewport.content=mode==="desktop"?"width=1280":originalViewport;
    }
    if(mode==="auto" && lastMode==="auto")return;
    const logicalWidth=mode==="mobile"?390:1280;
    // Use the browser's CSS parser; only viewport-width conditions are overridden.
    // Other media features (motion preferences, print, orientation) remain intact.
    function visit(rules) {
      for(const rule of rules) {
        if(rule instanceof CSSMediaRule) {
          if(!originalMedia.has(rule))originalMedia.set(rule,rule.media.mediaText);
          const original=originalMedia.get(rule);
          rule.media.mediaText=mode==="auto"?original:original.replace(/\((min|max)-width:\s*(\d+(?:\.\d+)?)px\)/g,(_,bound,value)=>
            (bound==="min"?logicalWidth>=Number(value):logicalWidth<=Number(value))?"(min-width: 0px)":"(max-width: 0px)");
        }
        if(rule.cssRules)visit(rule.cssRules);
      }
    }
    for(const sheet of document.styleSheets)try{visit(sheet.cssRules);}catch{}
    lastMode=mode;
  }
  // Apply stored mode before the body is painted, then after styles are available.
  document.documentElement.dataset.cmView=location.pathname==="/settings"?"auto":get().view;
  function schedule(){if(requested)return;requested=true;requestAnimationFrame(()=>{requested=false;apply();});}
  document.addEventListener("load",event=>{if(event.target.tagName==="LINK")schedule();},true);
  window.addEventListener("storage",event=>{if(event.key===KEY || event.key===null)schedule();});
  document.addEventListener("click",event=>{
    const link=event.target.closest?.('a.cm-settings');
    if(link && location.pathname!=="/settings")link.href="/settings?"+new URLSearchParams({return_to:location.pathname+location.search+location.hash});
  },true);
  document.addEventListener("DOMContentLoaded",()=>{
    apply();
    new MutationObserver(schedule).observe(document.head,{childList:true,subtree:true});
    const form=document.getElementById("cm-preferences-form");
    if(!form)return;
    form.querySelectorAll("fieldset,button").forEach(el=>el.disabled=false);
    function populate(){const prefs=get();for(const [name,value] of Object.entries(prefs)){const field=form.elements[name];if(typeof value==="boolean")field.checked=value;else field.value=value;}}
    populate();
    const status=document.getElementById("cm-settings-status");
    form.addEventListener("submit",event=>{
      event.preventDefault();
      const fields=form.elements;
      const value={view:fields.view.value,venueArea:fields.venueArea.value,venueSort:fields.venueSort.value,rememberVenueSearch:fields.rememberVenueSearch.checked};
      try{localStorage.setItem(KEY,JSON.stringify(value));apply();status.textContent="設定を保存しました。";}
      catch{status.textContent="設定を保存できませんでした。ブラウザの保存設定をご確認ください。";}
    });
    document.getElementById("cm-settings-reset").addEventListener("click",()=>{
      try {
        localStorage.setItem(KEY,JSON.stringify(defaults));
        Object.keys(localStorage).filter(key=>key.startsWith(VENUES)).forEach(key=>localStorage.removeItem(key));
        populate();apply();status.textContent="初期設定に戻しました。";
      }catch{status.textContent="設定を保存できませんでした。";}
    });
  });
})();
