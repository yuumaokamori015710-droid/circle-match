"use strict";

(() => {
  const directory = document.querySelector(".venue-directory");
  if (!directory || !directory.querySelector("#venue-court-filters")) return;
  const $ = selector => directory.querySelector(selector);
  const list = value => Array.isArray(value) ? value : [];
  const esc = value => String(value ?? "").replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));
  const PAGE_SIZE = 50;
  const browser = typeof window === "undefined" ? null : window;
  const URL_FILTER_NAMES = ["q","places","map","operator_type","facility_kind","venue_type","booking_channel","registration","open_from","open_until","price_max","sort","night_lighting","indoor","show_suspended"];
  const SELECT_VALUES = {operator_type:["","PUBLIC","PRIVATE"],facility_kind:["","COURT","SCHOOL","VENUE"],venue_type:["","gym","field","court","track","meeting","karaoke","boardgame","golf","other"],booking_channel:["","web","phone","counter","unknown"],registration:["","required","not_required","unknown"],sort:["name","price"]};
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
    if(plans.length) return plans.slice(0,2).map(plan=>`<span class="venue-rate-preview"><span>${esc(plan.label)}</span><span class="venue-price-amount">${Number(plan.amount).toLocaleString('ja-JP')}円</span></span>`).join('');
    if (minimum === null) return '<span class="venue-unconfirmed">金額未取得</span>';
    const amount = value => `${value.toLocaleString("ja-JP",{maximumFractionDigits:2})}円`;
    const span = value => `<span class="venue-price-amount">${amount(value)}</span>`;
    if (maximum !== null && maximum >= minimum) {
      return maximum === minimum ? span(minimum) : `${span(minimum)}<span class="venue-price-amount"><small>〜</small>${amount(maximum)}</span>`;
    }
    return span(minimum);
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
    const maxPrice = numberOrNull(filters.price_max);
    return list(courts).filter(court => {
      const searchable = normalize([court.name,court.operator,court.municipality,court.area,court.address,court.surface,court.booking_method,court.booking_note,court.price_note].filter(Boolean).join(" "));
      const price = numberOrNull(court.price_per_hour);
      return (filters.show_suspended || court.availability_status !== "SUSPENDED") && terms.every(term => searchable.includes(term)) &&
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
    return [...list(courts)].sort((a,b) => {
      if (sort === "price") {
        const left = numberOrNull(a.price_per_hour), right = numberOrNull(b.price_per_hour);
        if (left === null && right !== null) return 1;
        if (left !== null && right === null) return -1;
        if (left !== null && right !== null && left !== right) return left-right;
      }
      return String(a.name || "").localeCompare(String(b.name || ""),"ja",{numeric:true}) || String(a.id || "").localeCompare(String(b.id || ""));
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
    const tariff=plans.length?`<table class="venue-tariff"><caption>条件別料金</caption><thead><tr><th>利用区分</th><th>金額</th><th>単位</th><th>適用条件</th></tr></thead><tbody>${plans.map(p=>`<tr><th scope="row">${esc(p.label)}</th><td>${Number(p.amount).toLocaleString('ja-JP')}円</td><td>${esc(p.unit)}</td><td>${esc(p.conditions)}</td></tr>`).join('')}</tbody></table>`:'';
    return `<tr class="venue-court-card" aria-labelledby="venue-court-title-${index}"><th scope="row" class="venue-court-main"><h3 id="venue-court-title-${index}">${esc(court.name)}</h3>${suspended?`<p class="venue-availability-note">休止中：${esc(court.availability_note)}</p>`:''}<p class="venue-court-features">${list(court.sports).map(esc).join(' / ')}</p></th>
      <td class="venue-location-cell" data-label="所在地">${esc(court.municipality)}</td><td class="venue-court-price" data-label="料金"><div class="venue-original-price">${priceLabel(court)}</div><p class="venue-price-unit">${esc(plans[0]?.unit||court.price_unit)}</p>${plans.length?`<a class="venue-tariff-more" href="#venue-details-${index}">全${plans.length}区分の料金</a>`:''}${feeLink}</td><td class="venue-booking-cell" data-label="予約方法">${esc(channels)}</td><td class="venue-registration-cell" data-label="事前登録">${registration}</td><td class="venue-action-cell"><div class="venue-court-links">${bookingLink}${createLink}</div></td></tr>
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
    fields.map.value = read('map') || '';
    for (const [name,allowed] of Object.entries(SELECT_VALUES)) {
      const value = read(name) || (name === "sort" ? "name" : "");
      fields[name].value = allowed.includes(value) ? value : name === "sort" ? "name" : "";
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
      } else if (value !== null && value !== "" && value !== undefined && !(name === "sort" && value === "name")) {
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
      else fields[name].value = name === "sort" ? "name" : "";
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
    } else if (link.classList.contains('venue-tariff-more')) {
      const details = directory.querySelector(link.getAttribute('href'));
      if (!details) return;
      event.preventDefault();
      details.open = true;
      details.scrollIntoView({block:'nearest'});
      details.querySelector('summary').focus();
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
