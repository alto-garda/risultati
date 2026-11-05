(function () {
  const root = document.querySelector('[data-lnd-team]');
  if (!root) return;
  const slug = root.dataset.lndTeam;
  const dataUrl = `../../data/${slug}.json`;
  const fmtDate = (value) => {
    if (!value) return 'Data da definire';
    const [y, m, d] = value.split('-');
    return `${d}/${m}/${y}`;
  };
  const fmtShortDate = (value) => {
    if (!value) return '';
    const [y, m, d] = value.split('-');
    return `${d}/${m}/${String(y).slice(-2)}`;
  };
  const esc = (value) => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  const displayTeam = (name) => {
    const value = String(name ?? '').trim();
    if (slug !== 'pulcini-u11') return value;
    const key = value.toUpperCase().replace(/[.\s_-]+/g, ' ').trim();
    if (/^ALTO GARDA(?: SQ ?B| SQUADRA B| B)$/.test(key)) return 'ALTO GARDA (NERA)';
    if (key === 'ALTO GARDA') return 'ALTO GARDA (BLU)';
    return value;
  };
  const matchName = (f) => f.isRest ? 'Turno di riposo' : `${displayTeam(f.home)} – ${displayTeam(f.away)}`;
  const venue = (f) => [f.field, f.fieldAddress].filter(Boolean).join(' · ');
  const cardContent = (f, next) => {
    if (!f) return `<div class="base-match-placeholder">${next ? 'Il prossimo appuntamento non è ancora disponibile.' : 'Non risultano appuntamenti precedenti.'}</div>`;
    return `<div class="base-match-placeholder">${esc(matchName(f) || 'Turno di riposo')}</div><p class="base-match-meta">${esc(fmtDate(f.date))}${f.time ? ' · '+esc(f.time) : ''}${venue(f) ? '<br>'+esc(venue(f)) : ''}</p>`;
  };
  fetch(dataUrl, { cache: 'no-store' }).then(r => {
    if (!r.ok) throw new Error('Dati LND non disponibili');
    return r.json();
  }).then(data => {
    const fixtures = (data.fixtures || []).slice().sort((a,b) => (a.date || '').localeCompare(b.date || '') || a.giornata-b.giornata);
    if (!fixtures.length) throw new Error('Calendario vuoto');
    const today = new Date(); today.setHours(0,0,0,0);
    const dated = fixtures.filter(f => f.date && !f.isRest);
    const previous = dated.filter(f => new Date(`${f.date}T00:00:00`) < today).slice(-1)[0];
    const next = dated.find(f => new Date(`${f.date}T00:00:00`) >= today);
    const cards = root.querySelectorAll('.base-match-card');
    if (cards[0]) cards[0].innerHTML = `<h2>Ultima partita</h2>${cardContent(previous, false)}`;
    if (cards[1]) cards[1].innerHTML = `<h2>Prossima partita</h2>${cardContent(next, true)}`;
    const badge = root.querySelector('.demo-tag'); if (badge) badge.remove();
    const tbody = root.querySelector('.base-fixture-table tbody');
    if (tbody) tbody.innerHTML = fixtures.map(f => {
      const fixture = f.isRest ? 'Turno di riposo' : matchName(f);
      return `<tr><td>${esc(f.giornata)}</td><td>${esc(fmtDate(f.date))}</td><td>${esc(f.time || '—')}</td><td>${esc(fixture)}</td><td>${esc(venue(f) || '—')}</td></tr>`;
    }).join('');
    const calendarBadge = root.querySelector('.base-calendar-badge');
    if (calendarBadge) calendarBadge.textContent = data.updatedAt ? `AGGIORNATO ${fmtShortDate(data.updatedAt)}` : 'AGGIORNAMENTO NON DISPONIBILE';
    root.dataset.loaded = 'true';
  }).catch(err => {
    console.error('Import calendario LND:', err);
    const calendarBadge = root.querySelector('.base-calendar-badge');
    if (calendarBadge) { calendarBadge.textContent = 'DATI NON DISPONIBILI'; calendarBadge.style.background = '#fee2e2'; calendarBadge.style.color = '#991b1b'; }
  });
})();
