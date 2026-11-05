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
    if (/^ALTO GARDA(?: SQ ?B| SQUADRA B| B)$/.test(key) || key === 'ALTO GARDA NERA') return 'ALTO GARDA (NERA)';
    if (key === 'ALTO GARDA' || key === 'ALTO GARDA BLU') return 'ALTO GARDA (BLU)';
    return value;
  };
  const squadOf = (fixture) => {
    if (slug !== 'pulcini-u11') return 'all';
    const names = [fixture.home, fixture.away].map(name => displayTeam(name).toUpperCase());
    if (names.includes('ALTO GARDA (NERA)')) return 'nera';
    if (names.includes('ALTO GARDA (BLU)')) return 'blu';
    return null;
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
    const rawFixtures = (data.fixtures || []).slice();
    // Pulcini U10: LND può restituire righe di riposo segnaposto anche per
    // giornate in cui Alto Garda ha una partita. Mantieni il riposo solo
    // nelle giornate senza una gara effettiva.
    const playedRounds = new Set(rawFixtures.filter(f => !f.isRest).map(f => Number(f.giornata)));
    const fixtures = rawFixtures
      .filter(f => !(slug === 'pulcini-u10' && f.isRest && playedRounds.has(Number(f.giornata))))
      .sort((a,b) => (a.date || '').localeCompare(b.date || '') || a.giornata-b.giornata);
    if (!fixtures.length) throw new Error('Calendario vuoto');
    const today = new Date(); today.setHours(0,0,0,0);
    const renderMatchCards = (scope, squadFixtures) => {
      const dated = squadFixtures.filter(f => f.date && !f.isRest);
      const previous = dated.filter(f => new Date(`${f.date}T00:00:00`) < today).slice(-1)[0];
      const next = dated.find(f => new Date(`${f.date}T00:00:00`) >= today);
      const cards = scope.querySelectorAll('.base-match-card');
      if (cards[0]) cards[0].innerHTML = `<h2>Ultima partita</h2>${cardContent(previous, false)}`;
      if (cards[1]) cards[1].innerHTML = `<h2>Prossima partita</h2>${cardContent(next, true)}`;
    };
    const renderCalendar = (scope, squadFixtures) => {
      const tbody = scope.querySelector('.base-fixture-table tbody');
      if (tbody) tbody.innerHTML = squadFixtures.map(f => {
        const fixture = f.isRest ? 'Turno di riposo' : matchName(f);
        return `<tr><td>${esc(f.giornata)}</td><td>${esc(fmtDate(f.date))}</td><td>${esc(f.time || '—')}</td><td>${esc(fixture)}</td><td>${esc(venue(f) || '—')}</td></tr>`;
      }).join('');
      const calendarBadge = scope.querySelector('.base-calendar-badge');
      if (calendarBadge) calendarBadge.textContent = data.updatedAt ? `AGGIORNATO ${fmtShortDate(data.updatedAt)}` : 'AGGIORNAMENTO NON DISPONIBILE';
    };
    if (slug === 'pulcini-u11') {
      ['blu','nera'].forEach(squad => {
        const squadFixtures = fixtures.filter(f => squadOf(f) === squad);
        const matchScope = root.querySelector(`[data-squad-matches="${squad}"]`);
        const calendarScope = root.querySelector(`[data-squad-calendar="${squad}"]`);
        if (matchScope) renderMatchCards(matchScope, squadFixtures);
        if (calendarScope) renderCalendar(calendarScope, squadFixtures);
      });
    } else {
      renderMatchCards(root, fixtures);
      renderCalendar(root, fixtures);
    }
    const badge = root.querySelector('.demo-tag'); if (badge) badge.remove();
    root.dataset.loaded = 'true';
    }).catch(err => {
    console.error('Import calendario LND:', err);
    const calendarBadges = root.querySelectorAll('.base-calendar-badge');
    calendarBadges.forEach(calendarBadge => { calendarBadge.textContent = 'DATI NON DISPONIBILI'; calendarBadge.style.background = '#fee2e2'; calendarBadge.style.color = '#991b1b'; });
  });
})();
