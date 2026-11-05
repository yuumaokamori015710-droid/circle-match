/* Read-only DOM audit. Image/gradient text and disabled controls need manual review. */
(() => {
  const rgba = value => {
    const values = value.match(/[\d.]+/g)?.map(Number);
    return values?.length >= 3 ? [values[0], values[1], values[2], values[3] ?? 1] : null;
  };
  const blend = (front, back) => [0, 1, 2].map(i => front[i] * front[3] + back[i] * (1 - front[3])).concat(1);
  const light = rgb => rgb.slice(0, 3).map(v => v / 255).map(v => v <= .04045 ? v / 12.92 : ((v + .055) / 1.055) ** 2.4)
    .reduce((sum, v, i) => sum + v * [.2126, .7152, .0722][i], 0);
  const ratio = (a, b) => (Math.max(light(a), light(b)) + .05) / (Math.min(light(a), light(b)) + .05);
  const background = el => {
    const layers = [];
    for (let node = el; node; node = node.parentElement) {
      const css = getComputedStyle(node);
      if (css.backgroundImage !== 'none') return null;
      const color = rgba(css.backgroundColor);
      if (color) layers.push(color);
      if (color?.[3] === 1) break;
    }
    return layers.reverse().reduce((color, layer) => blend(layer, color), [255, 255, 255, 1]);
  };
  const visible = el => {
    if (el.closest('[hidden], [inert], [disabled], [aria-disabled="true"], .club-sr-only, .sr-only')) return false;
    if (!el.getClientRects().length) return false;
    for (let node = el; node; node = node.parentElement) {
      const css = getComputedStyle(node);
      if (css.display === 'none' || css.visibility === 'hidden' || Number(css.opacity) === 0) return false;
    }
    return true;
  };
  const issues = [], skipped = [], seen = new Set();
  let checked = 0, logotypes = 0;
  const inspect = (el, text, pseudo = null) => {
    if (!visible(el)) return;
    if (el.closest('a.brand')) { logotypes++; return; }
    const css = getComputedStyle(el, pseudo), bg = background(el), fg = rgba(css.color);
    if (!bg || !fg) { skipped.push({selector: el.tagName.toLowerCase() + '.' + el.className, reason: 'image-or-unsupported-color'}); return; }
    let opacity = pseudo ? Number(css.opacity) : 1;
    for (let node = el; node; node = node.parentElement) opacity *= Number(getComputedStyle(node).opacity);
    const front = [...fg.slice(0, 3), fg[3] * opacity];
    const contrast = ratio(blend(front, bg), bg);
    const size = Number(css.fontSize.replace('px', '')), weight = Number(css.fontWeight);
    const minimum = size >= 24 || (size >= 18.66 && weight >= 700) ? 3 : 4.5;
    checked++;
    if (contrast < minimum) {
      const selector = el.tagName.toLowerCase() + (el.id ? '#' + el.id : '') + (el.className ? '.' + String(el.className).trim().replaceAll(' ', '.') : '') + (pseudo || '');
      const key = [selector, css.color, bg.join(), text].join('|');
      if (!seen.has(key)) issues.push({selector, text: text.trim().slice(0, 84), foreground: css.color,
        background: bg.slice(0, 3).map(Math.round), ratio: Math.round(contrast * 100) / 100, minimum});
      seen.add(key);
    }
  };
  for (const el of document.querySelectorAll('body,body *')) {
    if (el.closest('script,style,noscript,option,textarea,svg')) continue;
    for (const node of el.childNodes) {
      if (node.nodeType === 3 && node.textContent.trim()) inspect(el, node.textContent);
    }
  }
  for (const el of document.querySelectorAll('input:not([type=hidden]):not([type=radio]):not([type=checkbox]),textarea,select')) {
    if (el.value || el.tagName === 'SELECT') inspect(el, '[control text]');
    else if (el.placeholder) inspect(el, '[placeholder]', '::placeholder');
  }
  return {url: location.href, viewport: {width: innerWidth, height: innerHeight},
    pageWidth: document.documentElement.scrollWidth, checked, issueCount: issues.length, issues, skipped,
    exemptions: {logotypes}};
})()
