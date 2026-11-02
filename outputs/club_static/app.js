/* Club Edit: native scrolling, progressive enhancement, no application state. */
(() => {
  const rail = document.getElementById('clubSports');
  if (!rail) return;
  const all = document.querySelector('[data-all-sports]');
  const arrows = [...document.querySelectorAll('[data-rail-direction]')];
  const reduced = window.matchMedia('(prefers-reduced-motion: reduce)');
  const key = 'cm-club-sport-scroll';
  let beforeGrid = 0;
  const filters = document.getElementById('eventFilters');
  const syncFilterLinks = () => {
    if (!filters) return;
    const current = new URLSearchParams(location.search);
    rail.querySelectorAll('a[href]').forEach(link => {
      const target = new URL(link.href);
      for (const name of ['region', 'prefecture', 'q', 'date_from', 'date_to', 'event_type', 'participation']) {
        const field = filters.elements.namedItem(name);
        const value = field ? field.value : current.get(name);
        if (value) target.searchParams.set(name, value);
        else target.searchParams.delete(name);
      }
      link.href = target.pathname + target.search;
    });
  };
  if (filters) filters.addEventListener('change', syncFilterLinks);
  window.addEventListener('popstate', syncFilterLinks);
  const update = () => {
    const grid = rail.classList.contains('club-sports-grid');
    arrows.forEach(button => {
      button.hidden = grid;
      button.disabled = Number(button.dataset.railDirection) < 0 ? rail.scrollLeft < 2 :
        rail.scrollLeft + rail.clientWidth >= rail.scrollWidth - 2;
    });
  };
  all.hidden = false;
  all.addEventListener('click', () => {
    if (!rail.classList.contains('club-sports-grid')) beforeGrid = rail.scrollLeft;
    const expanded = rail.classList.toggle('club-sports-grid');
    if (!expanded) rail.scrollLeft = beforeGrid;
    all.setAttribute('aria-expanded', String(expanded));
    all.lastChild.textContent = expanded ? '閉じる' : '一覧';
    update();
  });
  arrows.forEach(button => button.addEventListener('click', () => {
    rail.scrollBy({left: Number(button.dataset.railDirection) * rail.clientWidth * 0.75,
      behavior: reduced.matches ? 'instant' : 'smooth'});
  }));
  rail.addEventListener('scroll', update, {passive: true});
  window.addEventListener('resize', update);
  rail.addEventListener('click', event => {
    if (event.target.closest('a')) {
      syncFilterLinks();
      try { sessionStorage.setItem(key, String(rail.scrollLeft)); } catch (_) {}
    }
  });
  rail.addEventListener('keydown', event => {
    const items = [...rail.querySelectorAll('a')];
    const index = items.indexOf(document.activeElement);
    if (index < 0) return;
    const next = {ArrowRight: Math.min(index + 1, items.length - 1),
      ArrowLeft: Math.max(index - 1, 0), Home: 0, End: items.length - 1}[event.key];
    if (next === undefined) return;
    event.preventDefault();
    items[next].focus({preventScroll: true});
    items[next].scrollIntoView({block: 'nearest', inline: 'nearest', behavior: 'instant'});
  });
  try { rail.scrollLeft = Number(sessionStorage.getItem(key)) || 0; } catch (_) {}
  const selected = rail.querySelector('[aria-current]');
  if (selected && (selected.offsetLeft < rail.scrollLeft ||
      selected.offsetLeft + selected.offsetWidth > rail.scrollLeft + rail.clientWidth)) {
    rail.scrollLeft = selected.offsetLeft - rail.offsetLeft - 12;
  }
  update();
})();
