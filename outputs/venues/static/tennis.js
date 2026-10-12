"use strict";

(() => {
  const directory = document.querySelector(".venue-directory");
  if (!directory || !directory.querySelector("#venue-court-filters")) return;
  const $ = selector => directory.querySelector(selector);
  const list = value => Array.isArray(value) ? value : [];
  const esc = value => String(value ?? "").replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));
  const PAGE_SIZE = 50;
  const browser = typeof window === "undefined" ? null : window;
  const URL_FILTER_NAMES = ["q","name","price_status","places","map","operator_type","facility_kind","venue_type","booking_channel","registration","open_from","open_until","price_max","sort","night_lighting","indoor","show_suspended"];
  const SELECT_VALUES = {operator_type:["","PUBLIC","PRIVATE"],facility_kind:["","COURT","SCHOOL","VENUE"],venue_type:["","gym","field","court","track","meeting","karaoke","boardgame","golf","other"],booking_channel:["","web","phone","counter","unknown"],registration:["","required","not_required","unknown"],price_status:["","available","missing","hourly"],sort:[...$('#venue-sort').options].map(option=>option.value)};
  const AREA_STAGES = {'23区':'wards','多摩':'tama','島しょ':'islands'};
  const placeParents = Object.fromEntries([...$('#venue-places-filter').options].map(option=>[option.value,option.dataset.parent]));
  const state = {courts:[],meta:{},matches:[],visibleCount:PAGE_SIZE,loaded:false};
  let loadingRequest = null;
  let searchTimer;
  let mapRequest;
  let regionDraft = null;

  function ancestors(place) {
    const result=[];
    while(placeParents[place]) {place=placeParents[place];result.push(place);}
    return result;
  }
  function getPlaces() {return [...$('#venue-places-filter').selectedOptions].map(option=>option.value);}
  function setPlaces(places) {
    const field=$('#venue-places-filter');
    for(const place of places) if(![...field.options].some(option=>option.value===place)) field.add(new Option(place,place));
    for(const option of field.options) option.selected=places.includes(option.value);
  }
  function placeLabel(places) {
    if(!places.length) return '地域指定なし';
    return places.length===1 && placeParents[places[0]] ? `東京都 / ${places[0]}` : places.join('・');
  }
  function defaultStage(places) {
    const stages=[...new Set(places.map(place=>[place,...ancestors(place)].map(key=>AREA_STAGES[key]).find(Boolean)))];
    if(stages.length===1 && stages[0]) return stages[0];
    return places.length && places.every(place=>place in placeParents && !placeParents[place]) ? 'kanto' : 'tokyo';
  }
  function paintMap() {
    const places=regionDraft?.places || getPlaces();
    for(const control of $('#venue-region-selector').querySelectorAll('[data-place]')) {
      const active=places.includes(control.dataset.place);
      if(control.matches('input')) {control.checked=active;control.closest('label').classList.toggle('is-active',active);}
      else {control.classList.toggle('is-active',active);control.setAttribute('aria-checked',String(active));}
    }
    updateRegionSummary();
  }
  function previewRegion() {
    if(state.loaded) {
      state.matches=sortCourts(filterCourts(state.courts,{...readFilters(),places:regionDraft.places}),readFilters().sort);
      state.visibleCount=PAGE_SIZE;
      renderResults();
    }
    paintMap();
  }
  function togglePlace(place) {
    if(!regionDraft) return;
    regionDraft.places=regionDraft.places.includes(place) ? regionDraft.places.filter(item=>item!==place)
      : [...regionDraft.places.filter(item=>!ancestors(place).includes(item)&&!ancestors(item).includes(place)),place];
    previewRegion();
  }

  function syncMap(force = false) {
    const fields = $("#venue-court-filters").elements;
    const stage = regionDraft?.stage || fields.map.value || defaultStage(getPlaces());
    const panel = $('.venue-region-panel');
    if (!force && panel?.dataset.stage === stage) {
      mapRequest?.abort();
      $('#venue-region-selector').removeAttribute('aria-busy');
      $('#venue-map-error').hidden=true;
      paintMap();
      return;
    }
    mapRequest?.abort();
    mapRequest = new AbortController();
    const signal = mapRequest.signal;
    $('#venue-region-selector').setAttribute('aria-busy','true');
    $('#venue-map-error').hidden = true;
    const url=currentUrl();
    url.searchParams.set('v_map',stage);
    url.searchParams.set('v_places',(regionDraft?.places || getPlaces()).join(','));
    fetch(url.href,{credentials:'omit',signal}).then(response => {
      if (!response.ok) throw new Error('Map unavailable');
      return response.text();
    }).then(html => {
      if (signal.aborted) return;
      const replacement = new DOMParser().parseFromString(html,'text/html').querySelector('#venue-region-selector');
      if (!replacement) throw new Error('Map unavailable');
      $('#venue-region-selector').innerHTML = replacement.innerHTML;
      paintMap();
      if ($('#venue-region-dialog').open) $('#venue-region-dialog-title').focus({preventScroll:true});
    }).catch(() => {
      if (!signal.aborted) $('#venue-map-error').hidden = false;
    }).finally(() => {
      if (!signal.aborted) $('#venue-region-selector').removeAttribute('aria-busy');
    });
  }

  function updateRegionSummary() {
    const selected = placeLabel(getPlaces());
    $('#venue-region-label').textContent = selected;
    $('#venue-open-region').title = selected;
    $('#venue-region-selection').textContent = placeLabel(regionDraft?.places || getPlaces());
    $('#venue-region-result').textContent = state.loaded ? $('#venue-result-count').textContent : '';
  }

  function numberOrNull(value) {
    return typeof value === "number" && Number.isFinite(value) && value >= 0 ? value : null;
  }
  function safeUrl(value) {
    try {
      if (typeof value !== "string") return null;
      const url = new URL(value);
      return ["https:","http:"].includes(url.protocol) && !url.username && !url.password ? url.href : null;
    } catch { return null; }
  }
  function externalLink(url, label, className = "") {
    const safe = safeUrl(url);
    return safe ? `<a href="${esc(safe)}" class="${esc(className)}" target="_blank" rel="noopener noreferrer">${esc(label)}<span aria-hidden="true"> ↗</span></a>` : "";
  }
  const normalize = value => String(value ?? "").normalize("NFKC").toLocaleLowerCase("ja").trim();
  const yen = value => `¥${value.toLocaleString("ja-JP",{maximumFractionDigits:2})}`;
  const minutes = value => /^(?:[01]\d|2[0-3]):[0-5]\d$/.test(value || "") ? Number(value.slice(0,2))*60+Number(value.slice(3)) : null;
  const hasPrice = court => numberOrNull(court.price_from)!==null || list(court.fee_options).length>0;
  function withinHours(court, from, until) {
    const start=minutes(from), end=minutes(until);
    if(start===null && end===null) return true;
    return list(court.opening_windows).some(([opening,closing])=>{
      if(start!==null && end!==null) {const finish=end+(end<start?1440:0);return opening<=start && start<finish && finish<=closing;}
      return start!==null ? opening<=start && start<closing : opening<end && end<=closing;
    });
  }
  function priceLabel(court) {
    const minimum = numberOrNull(court.price_from), maximum = numberOrNull(court.price_to);
    const plans=list(court.fee_options);
    const groups=new Map();
    for(const plan of plans) {
      const group=groups.get(plan.unit)||{unit:plan.unit,minimum:Number(plan.amount),maximum:Number(plan.amount)};
      group.minimum=Math.min(group.minimum,Number(plan.amount));
      group.maximum=Math.max(group.maximum,Number(plan.amount));
      groups.set(plan.unit,group);
    }
    const ranges=groups.size?[...groups.values()]:minimum===null?[]:[{unit:court.price_unit,minimum,maximum:maximum??minimum}];
    if (!ranges.length) return '<span class="venue-unconfirmed">金額未取得</span>';
    const amount = value => `${value.toLocaleString("ja-JP",{maximumFractionDigits:2})}円`;
    return ranges.slice(0,2).map(range=>`<div class="venue-rate-preview"><span class="venue-price-amount">${amount(range.minimum)}${range.maximum===range.minimum?'':`〜${amount(range.maximum)}`}</span><p class="venue-price-unit">${esc(range.unit)}</p></div>`).join('');
  }
  function checkedDate(value) {
    const match = /^(\d{4})-(\d{2})-(\d{2})$/.exec(String(value || ""));
    return match ? `${match[1]}年${Number(match[2])}月${Number(match[3])}日` : "確認日未記録";
  }
  function mapSearchUrl(court) {
    return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent([court.name,court.address].filter(Boolean).join(" "))}`;
  }
  function filterCourts(courts, filters) {
    const terms = normalize(filters.q).split(/\s+/).filter(Boolean);
    const nameTerms = normalize(filters.name).split(/\s+/).filter(Boolean);
    const maxPrice = numberOrNull(filters.price_max);
    return list(courts).filter(court => {
      const searchable = normalize([court.name,court.operator,court.municipality,court.area,court.address,court.surface,court.booking_method,court.booking_note,court.price_note].filter(Boolean).join(" "));
      const price = numberOrNull(court.price_per_hour);
      return (filters.show_suspended || court.availability_status !== "SUSPENDED") && terms.every(term => searchable.includes(term)) &&
        nameTerms.every(term=>normalize(court.name).includes(term)) &&
        (!filters.price_status || ({available:hasPrice(court),missing:!hasPrice(court),hourly:price!==null})[filters.price_status]) &&
        (!filters.places.length || filters.places.some(place=>[court.prefecture||'東京都',court.area,court.municipality].includes(place))) &&
        (!filters.operator_type || court.operator_type === filters.operator_type) &&
        (!filters.facility_kind || (court.facility_kind || "COURT") === filters.facility_kind) &&
        (!filters.venue_type || list(court.venue_types).includes(filters.venue_type)) &&
        (!filters.booking_channel || (filters.booking_channel === "unknown" ? !list(court.booking_channels).length : list(court.booking_channels).includes(filters.booking_channel))) &&
        (!filters.registration || (court.registration_required ?? null) === {required:true,not_required:false,unknown:null}[filters.registration]) &&
        withinHours(court,filters.open_from,filters.open_until) &&
        (maxPrice === null || price !== null && price <= maxPrice) &&
        (!filters.night_lighting || court.night_lighting === true) &&
        (!filters.indoor || court.indoor === true);
    });
  }
  function sortCourts(courts, sort) {
    const compare=(a,b)=>a<b?-1:a>b?1:0;
    return [...list(courts)].sort((a,b) => {
      const fallback=compare(String(a.name||''),String(b.name||'')) || compare(String(a.id||''),String(b.id||''));
      if(sort==='available') return Number(hasPrice(b))-Number(hasPrice(a)) || fallback;
      if(sort==='location'||sort==='location_desc') return compare(a.municipality,b.municipality)*(sort.endsWith('_desc')?-1:1)||fallback;
      if(sort==='checked'||sort==='checked_asc') return compare(a.checked_at,b.checked_at)*(sort==='checked'?-1:1)||fallback;
      if (['price','price_desc','booking','booking_desc','registration','registration_desc'].includes(sort)) {
        const fact=court=>sort.startsWith('price')?numberOrNull(court.price_per_hour):sort.startsWith('booking')?(list(court.booking_channels).join('・')||null):(court.registration_required??null);
        const left = fact(a), right = fact(b);
        if (left === null && right !== null) return 1;
        if (left !== null && right === null) return -1;
        if (left !== null && right !== null && left !== right) return compare(left,right)*(sort.endsWith('_desc')?-1:1);
      }
      return sort==='name_desc'?compare(a.name,b.name)*-1||compare(a.id,b.id):fallback;
    });
  }
  function courtCard(court, index) {
    const suspended = court.availability_status === "SUSPENDED";
    const hourlyPrice = numberOrNull(court.price_per_hour), courtCount = numberOrNull(court.courts_count);
    const operatorType = court.operator_type === "PUBLIC" ? "公営" : court.operator_type === "PRIVATE" ? "民営" : "運営区分は要確認";
    const registration = court.registration_required === true ? "必要" : court.registration_required === false ? "不要" : "未確認";
    const hours = court.opening_hours ? `${esc(court.opening_hours)} ${esc(court.opening_note)} ${externalLink(court.official_url,"利用時間の公式案内")}` : "利用時間は未確認";
    const sources = list(court.sources).map(source => externalLink(source.url,source.title || "公式情報")).filter(Boolean);
    const plans=list(court.fee_options);
    const feeSource = plans.length ? {url:plans[0].source_url} : list(court.sources).find(source => String(source.title || "").includes("公式料金表"));
    const feeLink = feeSource && (plans.length || numberOrNull(court.price_from) !== null) ? externalLink(feeSource.url,"公式料金表","venue-fee-link") : "";
    const bookingLabel = /Web|ウェブ|ネット|オンライン/i.test(court.booking_method || "") ? "公式予約へ" : "予約方法を確認";
    const bookingLink = suspended ? externalLink(court.official_url,"営業案内","venue-primary-link") : externalLink(court.booking_url,"公式予約先","venue-primary-link");
    const officialLink = externalLink(court.official_url,"公式案内","venue-secondary-link");
    const knownEquipment = courtCount !== null || court.surface || typeof court.indoor === "boolean" || typeof court.night_lighting === "boolean";
    const features = [...list(court.sports), ...(court.facility_kind === "VENUE" ? [court.facility_label || ""] : knownEquipment ? [courtCount === null ? "面数は要確認" : `${courtCount}面`, court.surface || "サーフェスは要確認", court.indoor === true ? "屋内あり" : court.indoor === false ? "屋外" : "屋内・屋外は要確認", court.night_lighting === true ? "夜間照明あり" : court.night_lighting === false ? "夜間照明なし" : "夜間照明は要確認"] : ["設備情報は要確認"])].filter(Boolean);
    const createParams = new URLSearchParams({venue:court.id,sport:state.meta.sport || list(court.sports)[0] || "",prefecture:"東京都"});
    const createLink = suspended ? "" : `<a class="venue-secondary-link" href="/events/new?${esc(createParams.toString())}">この会場で募集を作る</a>`;
    const channels=list(court.booking_channels).map(c=>({web:'Web',phone:'電話',counter:'窓口'}[c]||c)).join('・')||'公式案内';
    const tariff=plans.length?`<table class="venue-tariff"><caption>条件別料金</caption><thead><tr><th>利用区分</th><th>金額</th><th>単位</th><th>適用条件</th></tr></thead><tbody>${plans.map(p=>`<tr><th scope="row">${esc(p.label)}</th><td class="venue-tariff-amount">${Number(p.amount).toLocaleString('ja-JP')}円</td><td>${esc(p.unit)}</td><td>${esc(p.conditions)}</td></tr>`).join('')}</tbody></table>`:'';
    return `<tr class="venue-court-card" aria-labelledby="venue-court-title-${index}"><th scope="row" class="venue-court-main"><h3 id="venue-court-title-${index}">${esc(court.name)}</h3>${suspended?`<p class="venue-availability-note">休止中：${esc(court.availability_note)}</p>`:''}<p class="venue-court-features">${list(court.sports).map(esc).join(' / ')}</p></th>
      <td class="venue-location-cell" data-label="所在地">${esc(court.municipality)}</td><td class="venue-court-price" data-label="料金"><div class="venue-original-price">${priceLabel(court)}</div>${feeLink}</td><td class="venue-booking-cell" data-label="予約方法">${esc(channels)}</td><td class="venue-registration-cell" data-label="事前登録">${registration}</td><td class="venue-action-cell"><div class="venue-court-links">${bookingLink}${createLink}</div></td></tr>
      <tr class="venue-details-row"><td colspan="6"><details id="venue-details-${index}" class="venue-court-details"><summary>料金表・施設詳細</summary><div class="venue-detail-content"><div>${tariff}<p class="venue-court-note">${esc(court.price_note)}</p><p class="venue-court-note">${esc(court.fee_note)}</p><p class="venue-opening-hours"><strong>通常利用時間</strong> ${hours}</p></div><div><dl><dt>住所</dt><dd>${externalLink(mapSearchUrl(court),court.address)}</dd><dt>予約方法</dt><dd>${esc(court.booking_method)}</dd><dt>利用条件</dt><dd>${esc(court.booking_note)}</dd><dt>施設</dt><dd>${esc(court.facility_label)}</dd><dt>運営</dt><dd>${esc(court.operator)}（${operatorType}）</dd><dt>確認日</dt><dd>${esc(checkedDate(court.checked_at))}</dd></dl>${officialLink}<ul class="venue-source-list">${sources.map(source=>`<li>${source}</li>`).join('')}</ul></div></div></details></td></tr>`;
  }
  function readFilters() {
    const fields = $("#venue-court-filters").elements;
    const rawPrice = normalize(fields.price_max.value).replaceAll(",", "");
    const filters=Object.fromEntries(URL_FILTER_NAMES.map(name=>[name,fields[name].value]));
    filters.places=getPlaces();
    filters.price_max=rawPrice === "" ? null : numberOrNull(Number(rawPrice));
    for(const name of ["night_lighting","indoor","show_suspended"]) filters[name]=fields[name].checked;
    return filters;
  }
  function currentUrl() {
    try { return browser ? new URL(browser.location.href) : null; }
    catch { return null; }
  }
  function restoreUrlFilters(usePreferences = false) {
    const url = currentUrl();
    if (!url) return;
    const fields = $("#venue-court-filters").elements;
    $("#venue-court-filters").reset();
    const preferences=browser.CircleMatchSettings?.get() || {};
    const explicit=[...URL_FILTER_NAMES,'area','municipality'].some(name=>url.searchParams.has(`v_${name}`)||url.searchParams.has(name));
    const saved=usePreferences && !explicit && preferences.rememberVenueSearch ? browser.CircleMatchSettings?.getVenue(state.meta.sport || "all") || {} : {};
    const read = name => url.searchParams.get(`v_${name}`) ?? url.searchParams.get(name) ?? (usePreferences && !explicit ? saved[name] ?? (name==="area"?preferences.venueArea:name==="sort"?preferences.venueSort:null) : null);
    fields.q.value = (read("q") || "").slice(0,200);
    fields.name.value = (read("name") || "").slice(0,200);
    fields.map.value = read('map') || '';
    for (const [name,allowed] of Object.entries(SELECT_VALUES)) {
      const value = read(name) || (name === "sort" ? "available" : "");
      fields[name].value = allowed.includes(value) ? value : name === "sort" ? "available" : "";
    }
    const rawPlaces=url.searchParams.has('v_places') ? url.searchParams.getAll('v_places') : url.searchParams.has('places') ? url.searchParams.getAll('places') : read('places');
    const legacyPlace=read('municipality') || read('area') || (usePreferences && !explicit ? preferences.venueArea : '') || '';
    setPlaces(rawPlaces!==null && rawPlaces!==undefined ? [...new Set((Array.isArray(rawPlaces)?rawPlaces:[rawPlaces]).flatMap(value=>String(value).split(',')).map(value=>value.trim().slice(0,80)).filter(Boolean))].slice(0,100) : legacyPlace?[legacyPlace]:[]);
    const rawPrice = read("price_max");
    const price = rawPrice !== null && String(rawPrice).trim() ? numberOrNull(Number(normalize(rawPrice).replaceAll(",", ""))) : null;
    fields.price_max.value = price === null ? "" : String(price);
    for(const name of ["open_from","open_until"]) fields[name].value=minutes(read(name))===null?"":read(name);
    for (const name of ["night_lighting","indoor","show_suspended"]) {
      fields[name].checked = [true,"1","true","on"].includes(read(name));
    }
  }
  function persistUrlFilters(filters, push = false) {
    const url = currentUrl();
    if (!url || !browser.history) return;
    for(const key of ['v_area','area','v_municipality','municipality']) url.searchParams.delete(key);
    for (const name of URL_FILTER_NAMES) {
      const key = `v_${name}`, value = filters[name];
      url.searchParams.delete(key);
      url.searchParams.delete(name);
      if (typeof value === "boolean") {
        if (value) url.searchParams.set(key,"1");
      } else if (Array.isArray(value)) {
        if(value.length) url.searchParams.set(key,value.join(','));
      } else if (value !== null && value !== "" && value !== undefined && !(name === "sort" && value === "available")) {
        url.searchParams.set(key,String(value));
      }
    }
    url.searchParams.delete("v_page");
    if (url.href !== browser.location.href) {
      browser.history[push ? 'pushState' : 'replaceState'](browser.history.state,"",url.pathname + url.search + url.hash);
    }
  }
  function renderResults() {
    const count = state.matches.length;
    const visible = state.matches.slice(0,state.visibleCount);
    $("#venue-court-list").innerHTML = visible.map(courtCard).join("");
    $("#venue-result-count").textContent = state.loaded ? `${count.toLocaleString("ja-JP")} 件` : "";
    $("#venue-visible-count").textContent = count ? `${visible.length.toLocaleString("ja-JP")} / ${count.toLocaleString("ja-JP")} 件を表示` : "";
    $("#venue-empty-state").hidden = !state.loaded || count > 0;
    $("#venue-pagination").hidden = visible.length >= count;
    $("#venue-show-more").textContent = `さらに${Math.min(PAGE_SIZE,count-visible.length)}件表示`;
    updateRegionSummary();
    updateColumns();
  }
  function updateColumns() {
    const filters=readFilters();
    for(const link of directory.querySelectorAll('[data-venue-control]')) {
      const key=link.dataset.venueControl, value=link.dataset.value;
      const url=currentUrl();
      url.searchParams.delete(key);url.searchParams.delete('v_'+key);url.searchParams.delete('v_page');
      if(key==='places')for(const legacy of ['area','v_area','municipality','v_municipality'])url.searchParams.delete(legacy);
      if(value) url.searchParams.set('v_'+key,value);
      url.hash='venue-court-results';link.href=url.pathname+url.search+url.hash;
      const selected=key==='sort'?filters.sort===value:key==='places'?!filters.places.length:String(filters[key]===true?'1':filters[key]||'')===value;
      link.classList.toggle('is-active',selected);
      if(selected)link.setAttribute('aria-current','true');else link.removeAttribute('aria-current');
    }
    for(const th of directory.querySelectorAll('[data-venue-column]')) {
      const column=th.dataset.venueColumn, sort=filters.sort;
      const sorted=column==='checked_asc'?sort.startsWith('checked'):sort===column||sort===column+'_desc';
      th.setAttribute('aria-sort',sorted?(sort.endsWith('_desc')||sort==='checked'?'descending':'ascending'):column==='price'&&sort==='available'?'other':'none');
      const active={name:!!filters.name,location:filters.places.length>0,price:!!filters.price_status||filters.price_max!==null,booking:!!filters.booking_channel,registration:!!filters.registration,checked_asc:filters.show_suspended}[column];
      th.querySelector('summary').classList.toggle('is-filtered',!!active);
    }
  }
  function applyFilters(updateUrl = true, pushUrl = false) {
    if (!state.loaded) return;
    const filters = readFilters();
    const invalidPrice=fieldsPriceInvalid();
    $("#venue-filter-error").textContent=invalidPrice?"料金上限は0以上の金額で入力してください。":"";
    $("#venue-filter-error").hidden=!invalidPrice;
    if(invalidPrice) return;
    if (updateUrl) persistUrlFilters(filters, pushUrl);
    if(updateUrl) browser.CircleMatchSettings?.saveVenue(state.meta.sport || "all",filters);
    state.matches = sortCourts(filterCourts(state.courts,filters),filters.sort);
    state.visibleCount = PAGE_SIZE;
    renderResults();
    syncMap();
  }
  function fieldsPriceInvalid() {
    const raw=normalize($("#venue-court-filters").elements.price_max.value).replaceAll(",", "");
    return raw!=="" && (!/^\d+(?:\.\d+)?$/.test(raw) || numberOrNull(Number(raw))===null);
  }
  function resetFilters() {
    clearTimeout(searchTimer);
    const fields = $("#venue-court-filters").elements;
    for (const name of URL_FILTER_NAMES) {
      if (["night_lighting","indoor","show_suspended"].includes(name)) fields[name].checked = false;
      else if(name==='places') setPlaces([]);
      else fields[name].value = name === "sort" ? "available" : "";
    }
    applyFilters();
  }
  function renderMetadata() {
    $("#venue-catalog-total").textContent = `掲載 ${(numberOrNull(state.meta.total) ?? state.courts.length).toLocaleString("ja-JP")} 施設`;
    $("#venue-catalog-checked").textContent = `情報確認 ${checkedDate(state.meta.checked_at)}`;
    $("#venue-coverage-note").textContent = state.meta.coverage_note || "掲載施設は都内の全施設を網羅したものではありません。利用前に公式サイトで最新情報をご確認ください。";
    const municipalities = [...new Set([...list(state.meta.municipalities).filter(value => typeof value === "string"),...state.courts.map(court => court.municipality)].filter(value => typeof value === "string" && value.trim()))].sort((a,b) => a.localeCompare(b,"ja"));
    $("#venue-catalog-total").textContent += ` · ${municipalities.length} 自治体`;
  }
  function loadCourts() {
    if (loadingRequest) return loadingRequest;
    $("#venue-loading-state").hidden = false;
    $("#venue-error-state").hidden = true;
    $("#venue-empty-state").hidden = true;
    $("#venue-retry-load").disabled = true;
    $("#venue-filter-fields").disabled = true;
    $("#venue-sort").disabled=true;
    loadingRequest = (async () => {
      try {
        const response = await fetch(directory.dataset.catalogUrl,{credentials:"omit",headers:{Accept:"application/json"}});
        if (!response.ok) throw new Error("Unable to load courts");
        const data = await response.json();
        if (!data || !Array.isArray(data.courts)) throw new Error("Invalid court listing");
        state.courts = data.courts.filter(court => court && typeof court === "object");
        state.meta = data.meta && typeof data.meta === "object" ? data.meta : {};
        state.loaded = true;
        renderMetadata();
        restoreUrlFilters(true);
        $("#venue-filter-fields").disabled = false;
        $("#venue-sort").disabled=false;
        persistUrlFilters(readFilters());
        applyFilters(false);
        browser.CircleMatchSettings?.saveVenue(state.meta.sport || 'all',readFilters());
      } catch {
        $("#venue-error-state").hidden = false;
        // Keep server-rendered records and counts readable on network failure.
        $("#venue-empty-state").hidden = $("#venue-court-list").children.length > 0;
      } finally {
        $("#venue-filter-fields").disabled = false;
        $("#venue-sort").disabled=false;
        $("#venue-loading-state").hidden = true;
        $("#venue-retry-load").disabled = false;
        loadingRequest = null;
      }
    })();
    return loadingRequest;
  }

  $("#venue-court-filters").addEventListener("submit",event => {if(!state.loaded)return;event.preventDefault();clearTimeout(searchTimer);applyFilters();});
  $("#venue-court-filters").addEventListener("input",event => {
    clearTimeout(searchTimer);
    if (state.loaded) persistUrlFilters(readFilters());
    if (event.target.name === "q") searchTimer = setTimeout(applyFilters,150);
    else applyFilters();
  });
  $("#venue-court-filters").addEventListener("change",()=>{clearTimeout(searchTimer);applyFilters();});
  $("#venue-sort").addEventListener("change",()=>applyFilters());
  directory.addEventListener('input',event=>{
    if(event.target.matches('[name="name"][form]')) {clearTimeout(searchTimer);searchTimer=setTimeout(()=>applyFilters(true,true),150);}
  });
  directory.addEventListener('click',event=>{
    const link=event.target.closest('[data-venue-control]');
    if(link && state.loaded && !event.ctrlKey && !event.metaKey && !event.shiftKey && !event.altKey) {
      event.preventDefault();
      const key=link.dataset.venueControl, field=$('#venue-court-filters').elements[key];
      if(key==='places')setPlaces([]);else if(field.type==='checkbox')field.checked=link.dataset.value==='1';else field.value=link.dataset.value;
      link.closest('details').open=false;applyFilters(true,true);
    }
    const region=event.target.closest('[data-venue-open-region]');
    if(region) {event.preventDefault();region.closest('details').open=false;$('#venue-open-region').click();}
  });
  function positionColumnMenu(menu) {
    const panel=menu.querySelector('.venue-column-options'), rect=menu.querySelector('summary').getBoundingClientRect();
    panel.style.position='fixed';panel.style.width=Math.min(260,innerWidth-24)+'px';panel.style.maxHeight=Math.min(420,innerHeight-24)+'px';
    panel.style.left=Math.max(12,Math.min(rect.left,innerWidth-panel.offsetWidth-12))+'px';
    const height=panel.offsetHeight;
    panel.style.top=Math.max(12,Math.min(rect.bottom+4,innerHeight-height-12))+'px';
  }
  directory.addEventListener('toggle',event=>{
    const menu=event.target;
    if(!menu.matches('.venue-column-menu')||!menu.open)return;
    for(const other of directory.querySelectorAll('.venue-column-menu[open]'))if(other!==menu)other.open=false;
    positionColumnMenu(menu);
  },true);
  document.addEventListener('click',event=>{if(!event.target.closest('.venue-column-menu'))for(const menu of directory.querySelectorAll('.venue-column-menu[open]'))menu.open=false;});
  document.addEventListener('keydown',event=>{if(event.key==='Escape')for(const menu of directory.querySelectorAll('.venue-column-menu[open]')){event.preventDefault();menu.open=false;menu.querySelector('summary').focus();}});
  window.addEventListener('resize',()=>directory.querySelectorAll('.venue-column-menu[open]').forEach(positionColumnMenu));
  window.addEventListener('scroll',()=>directory.querySelectorAll('.venue-column-menu[open]').forEach(positionColumnMenu));
  $("#venue-reset-filters").addEventListener("click",resetFilters);
  $("#venue-empty-reset").addEventListener("click",resetFilters);
  $("#venue-retry-load").addEventListener("click",loadCourts);
  $("#venue-show-more").addEventListener("click",() => {state.visibleCount += PAGE_SIZE;renderResults();});
  $("#venue-show-all").addEventListener("click",() => {state.visibleCount = state.matches.length;renderResults();});
  const regionDialog = $('#venue-region-dialog');
  $('#venue-open-region').addEventListener('click',() => {
    if (state.loaded && fieldsPriceInvalid()) {
      applyFilters();
      $('#venue-court-filters').elements.price_max.focus();
      return;
    }
    regionDraft={places:getPlaces(),stage:$('#venue-court-filters').elements.map.value || defaultStage(getPlaces())};
    paintMap();
    regionDialog.showModal();
    document.body.classList.add('venue-modal-open');
    syncMap();
  });
  $('#venue-region-close').addEventListener('click',()=>regionDialog.close());
  $('#venue-region-done').addEventListener('click',()=>{
    const fields=$('#venue-court-filters').elements;
    setPlaces(regionDraft.places);
    fields.map.value=regionDraft.stage;
    regionDraft=null;
    if(!state.loaded) {persistUrlFilters(readFilters());browser.location.assign(browser.location.href);return;}
    applyFilters(true,true);
    regionDialog.close();
  });
  regionDialog.addEventListener('close',()=>{
    document.body.classList.remove('venue-modal-open');
    if(regionDraft) {regionDraft=null;applyFilters(false);}
  });
  $('#venue-region-clear').addEventListener('click',()=>{regionDraft.places=[];previewRegion();});
  regionDialog.addEventListener('click',event=>{
    if (event.target !== regionDialog) return;
    const rect = regionDialog.getBoundingClientRect();
    if (event.clientX < rect.left || event.clientX > rect.right || event.clientY < rect.top || event.clientY > rect.bottom) regionDialog.close();
  });
  $('#venue-map-retry').addEventListener('click',()=>syncMap(true));
  $('#venue-region-selector').addEventListener('change',event=>{if(event.target.dataset.place)togglePlace(event.target.dataset.place);});
  $('#venue-region-selector').addEventListener('keydown',event=>{
    if(event.key===' ' && event.target.matches('a[data-place]')) {event.preventDefault();togglePlace(event.target.dataset.place);}
  });
  directory.addEventListener('click',event => {
    const link = event.target.closest('a');
    if (!link || event.button !== 0 || event.ctrlKey || event.metaKey || event.shiftKey || event.altKey) return;
    if (link.closest('#venue-region-selector')) {
      const target = new URL(link.href), url = currentUrl();
      if (!url || target.origin !== url.origin || target.pathname !== '/venues') return;
      event.preventDefault();
      if(link.dataset.place) togglePlace(link.dataset.place);
      else if(regionDraft) {regionDraft.stage=target.searchParams.get('v_map')||'tokyo';syncMap();}
    }
  });
  if (browser) browser.addEventListener("popstate",() => {
    clearTimeout(searchTimer);
    regionDraft=null;
    if(regionDialog.open) regionDialog.close();
    restoreUrlFilters();
    applyFilters(false);
  });
  loadCourts();
})();
