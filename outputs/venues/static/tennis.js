"use strict";

(() => {
  const directory = document.querySelector(".venue-directory");
  if (!directory || !directory.querySelector("#venue-court-filters")) return;
  const $ = selector => directory.querySelector(selector);
  const list = value => Array.isArray(value) ? value : [];
  const esc = value => String(value ?? "").replace(/[&<>"']/g, char => ({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;","'":"&#39;"}[char]));
  const PAGE_SIZE = 50;
  const browser = typeof window === "undefined" ? null : window;
  const URL_FILTER_NAMES = ["q","municipality","area","operator_type","facility_kind","price_max","sort","night_lighting","indoor","show_suspended"];
  const SELECT_VALUES = {area:["","23区","多摩","島しょ"],operator_type:["","PUBLIC","PRIVATE"],facility_kind:["","COURT","SCHOOL","VENUE"],sort:["name","price"]};
  const state = {courts:[],meta:{},matches:[],visibleCount:PAGE_SIZE,loaded:false};
  let loadingRequest = null;
  let searchTimer;

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
  function priceLabel(court) {
    const minimum = numberOrNull(court.price_from), maximum = numberOrNull(court.price_to);
    if (minimum === null) return '<span class="venue-unconfirmed">料金は要確認</span>';
    const amount = value => `${value.toLocaleString("ja-JP",{maximumFractionDigits:2})}円`;
    const span = value => `<span class="venue-price-amount">${amount(value)}</span>`;
    if (maximum !== null && maximum >= minimum) {
      return maximum === minimum ? span(minimum) : `${span(minimum)}<span class="venue-price-amount"><small>〜</small>${amount(maximum)}</span>`;
    }
    return `<span class="venue-price-amount">${yen(minimum)}<small>〜</small></span>`;
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
        (!filters.municipality || court.municipality === filters.municipality) &&
        (!filters.area || court.area === filters.area) &&
        (!filters.operator_type || court.operator_type === filters.operator_type) &&
        (!filters.facility_kind || (court.facility_kind || "COURT") === filters.facility_kind) &&
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
    const operatorType = court.facility_kind === "SCHOOL" ? "学校開放" : court.operator_type === "PUBLIC" ? "公営" : court.operator_type === "PRIVATE" ? "民営" : "運営区分は要確認";
    const sources = list(court.sources).map(source => externalLink(source.url,source.title || "公式情報")).filter(Boolean);
    const feeSource = list(court.sources).find(source => String(source.title || "").includes("公式料金表"));
    const feeLink = feeSource && numberOrNull(court.price_from) !== null ? externalLink(feeSource.url,"公式料金表","venue-fee-link") : "";
    const bookingLabel = /Web|ウェブ|ネット|オンライン/i.test(court.booking_method || "") ? "公式予約へ" : "予約方法を確認";
    const bookingLink = suspended ? externalLink(court.official_url,"公式の営業案内","venue-secondary-link") || externalLink(court.booking_url,"公式情報を確認","venue-secondary-link") : externalLink(court.booking_url,bookingLabel,"venue-primary-link");
    const officialLink = externalLink(court.official_url,"公式案内","venue-secondary-link");
    const knownEquipment = courtCount !== null || court.surface || typeof court.indoor === "boolean" || typeof court.night_lighting === "boolean";
    const features = [...list(court.sports), ...(court.facility_kind === "VENUE" ? [court.facility_label || ""] : knownEquipment ? [courtCount === null ? "面数は要確認" : `${courtCount}面`, court.surface || "サーフェスは要確認", court.indoor === true ? "屋内あり" : court.indoor === false ? "屋外" : "屋内・屋外は要確認", court.night_lighting === true ? "夜間照明あり" : court.night_lighting === false ? "夜間照明なし" : "夜間照明は要確認"] : ["設備情報は要確認"])].filter(Boolean);
    const createParams = new URLSearchParams({venue:court.id,sport:state.meta.sport || list(court.sports)[0] || "",prefecture:"東京都"});
    const createLink = suspended ? "" : `<a class="venue-secondary-link" href="/events/new?${esc(createParams.toString())}">この会場で募集を作る</a>`;
    return `<article class="venue-court-card" aria-labelledby="venue-court-title-${index}">
      <div class="venue-court-main"><div class="venue-court-location"><span class="venue-operator-badge ${court.operator_type === "PRIVATE" ? "venue-private" : ""}">${esc(operatorType)}</span>${suspended ? '<span class="venue-suspended-badge">休止中</span>' : ""}<span>${esc([court.municipality,court.area].filter(Boolean).join(" · "))}</span></div><h3 id="venue-court-title-${index}">${esc(court.name || "施設名は要確認")}</h3>${suspended ? `<p class="venue-availability-note">${esc(court.availability_note || "現在は休止中です。営業再開の案内は公式サイトでご確認ください。")}</p>` : ""}<p class="venue-court-address">${court.address ? externalLink(mapSearchUrl(court),court.address,"venue-map-link") : "住所は要確認"}</p><ul class="venue-court-features">${features.map(feature => `<li>${esc(feature)}</li>`).join("")}</ul></div>
      <div class="venue-court-price"><p class="venue-column-label">掲載の参考料金</p><p class="venue-original-price">${priceLabel(court)}</p><p class="venue-price-unit">${esc(court.price_unit || "料金の単位は要確認")}</p>${feeLink}${court.price_note ? `<p class="venue-court-note">${esc(court.price_note)}</p>` : ""}${court.facility_kind === "VENUE" ? "" : `<p class="venue-hourly-price">${hourlyPrice === null ? "1面1時間換算: 要確認" : `比較用: ${yen(hourlyPrice)} / 1面・1時間`}</p>`}</div>
      <div class="venue-court-booking"><p class="venue-column-label">予約方法</p><p class="venue-booking-method">${esc(court.booking_method || "公式案内で確認してください")}</p>${court.booking_note ? `<p class="venue-court-note">${esc(court.booking_note)}</p>` : ""}<div class="venue-court-links">${bookingLink || '<span class="venue-link-unconfirmed">予約ページは要確認</span>'}${suspended || safeUrl(court.booking_url) === safeUrl(court.official_url) ? "" : officialLink}${createLink}</div></div>
      <details class="venue-court-details"><summary>施設情報・根拠を確認</summary><div class="venue-detail-content"><dl><dt>運営</dt><dd>${esc(court.operator || "要確認")}</dd><dt>情報確認日</dt><dd>${esc(checkedDate(court.checked_at))}</dd></dl><div><p class="venue-column-label">根拠リンク</p>${sources.length ? `<ul class="venue-source-list">${sources.map(source => `<li>${source}</li>`).join("")}</ul>` : officialLink || '<p class="venue-court-note">根拠リンクは要確認です。</p>'}<p class="venue-source-note">料金・登録資格・抽選や先着の条件は変更されることがあります。利用前に公式案内をご確認ください。</p></div></div></details>
    </article>`;
  }
  function readFilters() {
    const fields = $("#venue-court-filters").elements;
    const rawPrice = fields.price_max.value;
    return {q:fields.q.value,municipality:fields.municipality.value,area:fields.area.value,operator_type:fields.operator_type.value,facility_kind:fields.facility_kind.value,price_max:rawPrice === "" ? null : numberOrNull(Number(rawPrice)),sort:fields.sort.value,night_lighting:fields.night_lighting.checked,indoor:fields.indoor.checked,show_suspended:fields.show_suspended.checked};
  }
  function currentUrl() {
    try { return browser ? new URL(browser.location.href) : null; }
    catch { return null; }
  }
  function restoreUrlFilters() {
    const url = currentUrl();
    if (!url) return;
    const fields = $("#venue-court-filters").elements;
    $("#venue-court-filters").reset();
    const read = name => url.searchParams.get(`v_${name}`) ?? url.searchParams.get(name);
    fields.q.value = (read("q") || "").slice(0,200);
    for (const [name,allowed] of Object.entries(SELECT_VALUES)) {
      const value = read(name) || (name === "sort" ? "name" : "");
      fields[name].value = allowed.includes(value) ? value : name === "sort" ? "name" : "";
    }
    const municipality = read("municipality") || "";
    const municipalities = [...list(state.meta.municipalities),...state.courts.map(court => court.municipality)];
    fields.municipality.value = municipalities.includes(municipality) ? municipality : "";
    const rawPrice = read("price_max");
    const price = rawPrice && rawPrice.trim() ? numberOrNull(Number(rawPrice)) : null;
    fields.price_max.value = price === null ? "" : String(price);
    for (const name of ["night_lighting","indoor","show_suspended"]) {
      fields[name].checked = ["1","true","on"].includes(read(name));
    }
  }
  function persistUrlFilters(filters) {
    const url = currentUrl();
    if (!url || !browser.history) return;
    for (const name of URL_FILTER_NAMES) {
      const key = `v_${name}`, value = filters[name];
      url.searchParams.delete(key);
      url.searchParams.delete(name);
      if (typeof value === "boolean") {
        if (value) url.searchParams.set(key,"1");
      } else if (value !== null && value !== "" && value !== undefined && !(name === "sort" && value === "name")) {
        url.searchParams.set(key,String(value));
      }
    }
    url.searchParams.delete("v_page");
    if (url.href !== browser.location.href) {
      browser.history.replaceState(browser.history.state,"",url.pathname + url.search + url.hash);
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
  }
  function applyFilters(updateUrl = true) {
    if (!state.loaded) return;
    const filters = readFilters();
    if (updateUrl) persistUrlFilters(filters);
    state.matches = sortCourts(filterCourts(state.courts,filters),filters.sort);
    state.visibleCount = PAGE_SIZE;
    renderResults();
  }
  function resetFilters() {
    clearTimeout(searchTimer);
    const fields = $("#venue-court-filters").elements;
    for (const name of URL_FILTER_NAMES) {
      if (["night_lighting","indoor","show_suspended"].includes(name)) fields[name].checked = false;
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
    const current = $("#venue-municipality-filter").value;
    $("#venue-municipality-filter").innerHTML = '<option value="">すべての自治体</option>' + municipalities.map(value => `<option value="${esc(value)}">${esc(value)}</option>`).join("");
    $("#venue-municipality-filter").value = municipalities.includes(current) ? current : "";
  }
  function loadCourts() {
    if (loadingRequest) return loadingRequest;
    $("#venue-loading-state").hidden = false;
    $("#venue-error-state").hidden = true;
    $("#venue-empty-state").hidden = true;
    $("#venue-retry-load").disabled = true;
    $("#venue-filter-fields").disabled = true;
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
        restoreUrlFilters();
        $("#venue-filter-fields").disabled = false;
        applyFilters(false);
      } catch {
        $("#venue-error-state").hidden = false;
        // Keep server-rendered records and counts readable on network failure.
        $("#venue-empty-state").hidden = $("#venue-court-list").children.length > 0;
      } finally {
        $("#venue-loading-state").hidden = true;
        $("#venue-retry-load").disabled = false;
        loadingRequest = null;
      }
    })();
    return loadingRequest;
  }

  $("#venue-court-filters").addEventListener("submit",event => {event.preventDefault();clearTimeout(searchTimer);applyFilters();});
  $("#venue-court-filters").addEventListener("input",event => {
    clearTimeout(searchTimer);
    if (state.loaded) persistUrlFilters(readFilters());
    if (event.target.name === "q") searchTimer = setTimeout(applyFilters,150);
    else applyFilters();
  });
  $("#venue-court-filters").addEventListener("change",() => {clearTimeout(searchTimer);applyFilters();});
  $("#venue-reset-filters").addEventListener("click",resetFilters);
  $("#venue-empty-reset").addEventListener("click",resetFilters);
  $("#venue-retry-load").addEventListener("click",loadCourts);
  $("#venue-show-more").addEventListener("click",() => {state.visibleCount += PAGE_SIZE;renderResults();});
  $("#venue-show-all").addEventListener("click",() => {state.visibleCount = state.matches.length;renderResults();});
  if (browser) browser.addEventListener("popstate",() => {
    clearTimeout(searchTimer);
    restoreUrlFilters();
    applyFilters(false);
  });
  loadCourts();
})();
