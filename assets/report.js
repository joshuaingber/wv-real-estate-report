const C = D.counties, BY = Object.fromEntries(C.map(c => [c.f, c]));
const $ = id => document.getElementById(id);
const NS = 'http://www.w3.org/2000/svg';
const money = v => v == null ? '—' : '$' + Math.round(v).toLocaleString('en-US');
const kMoney = v => '$' + (v >= 1000 ? Math.round(v / 1000) + 'k' : v);
const pct = v => v == null ? '—' : (v > 0 ? '+' : v < 0 ? '−' : '') + Math.abs(v).toFixed(1) + '%';
const int = v => v == null ? '—' : Math.round(v).toLocaleString('en-US');
const ord = n => n + (['th','st','nd','rd'][(n % 100 - 20) % 10] || ['th','st','nd','rd'][n % 100] || 'th');
const esc = s => String(s).replace(/[&<>"]/g, m => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[m]));
const MON = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
const ym = s => MON[+s.slice(5) - 1] + ' ' + s.slice(0, 4);
const lpLast = C.find(c => c.lps.length).lps.slice(-1)[0][0];

const METRICS = {
  hv:   { label:'Home value', title:'Median home value', unit:money, ramp:'s', breaks:[100000,125000,150000,175000,225000,275000], bl:kMoney,
          note:`Median value of owner-occupied homes, Census ACS 5-year estimates ending ${D.acsYear}.` },
  ppsf: { label:'$ / sq ft', title:'Median listing price per square foot', unit:v => v == null ? '—' : '$' + Math.round(v), ramp:'s', breaks:[115,125,135,150,170,190], bl:v => '$' + v,
          note:`Realtor.com median asking price per square foot, ${ym(lpLast)}. Realtor.com publishes this series only for the 12 counties with enough listings.` },
  g:    { label:'Price growth', title:'Home-price growth, 2022 to 2023', unit:pct, ramp:'g', breaks:[0,3,6,10,15,20], bl:v => (v > 0 ? '+' : '') + v + '%',
          note:'One-year change in the FHFA all-transactions index, latest published year. Small counties swing widely year to year because few sales enter the index.' },
  pt:   { label:'Permits', title:'Residential units authorized, 2025', unit:v => v == null ? '—' : int(v) + ' units', ramp:'s', breaks:[10,25,50,100,250,1000], bl:v => int(v),
          note:'New privately owned housing units authorized by building permit in 2025. Authorized, not necessarily started.' },
};
let metric = 'hv', sel = '54037';

/* ---------- ranks ---------- */
function rankOf(key, f) {
  const vals = C.filter(c => c[key] != null).sort((a, b) => b[key] - a[key]);
  const i = vals.findIndex(c => c.f === f);
  return i < 0 ? null : { r: i + 1, n: vals.length };
}
function bin(m, v) { const b = METRICS[m].breaks; let i = 0; while (i < b.length && v >= b[i]) i++; return i; }

/* ---------- masthead ---------- */
function mast() {
  const hv = C.filter(c => c.hv != null).sort((a, b) => a.hv - b.hv);
  const lo = hv[0], hi = hv[hv.length - 1], med = hv[Math.floor(hv.length / 2)];
  $('thesis').innerHTML = `The typical home in <strong>${hi.n} County</strong> is worth ${money(hi.hv)}. In <strong>${lo.n} County</strong> it is ${money(lo.hv)}, a ${(hi.hv / lo.hv).toFixed(1)}× gap inside one state. This report tracks prices, construction, and rents across all 55 counties.`;
  $('acsY').textContent = '(ending ' + D.acsYear + ')';
  $('fmrY').textContent = D.fmrYear;
  // silhouette
  const sil = $('sil'); sil.setAttribute('viewBox', `0 0 ${D.W} ${D.H}`);
  sil.innerHTML = Object.entries(D.paths).map(([f, d]) => `<path data-f="${f}" d="${d}"/>`).join('');
  // ladder
  const svg = $('ladder');
  const defaultRead = () => `Median county: <b>${med.n}</b> ${money(med.hv)}`;
  function draw() {
    const w = svg.clientWidth || 800, padL = 8, padR = 8, x0 = 50000, x1 = 360000;
    const X = v => padL + (v - x0) / (x1 - x0) * (w - padL - padR);
    let s = `<line class="axis" x1="${padL}" x2="${w - padR}" y1="58" y2="58"/>`;
    const step = w < 520 ? 100000 : 50000;
    for (let v = 50000; v <= 350000; v += step) s += `<line class="axis" x1="${X(v)}" x2="${X(v)}" y1="58" y2="63"/><text x="${X(v)}" y="78" text-anchor="${v === 50000 ? 'start' : 'middle'}">${kMoney(v)}</text>`;
    hv.forEach((c, i) => s += `<line class="tick" data-f="${c.f}" style="animation-delay:${i * 12}ms" x1="${X(c.hv)}" x2="${X(c.hv)}" y1="24" y2="56"/>`);
    s += `<text class="end" x="${X(lo.hv)}" y="14" text-anchor="start">${lo.n}</text><text class="end" x="${X(hi.hv)}" y="14" text-anchor="end">${hi.n}</text>`;
    svg.innerHTML = s;
    svg._X = X;
  }
  draw(); new ResizeObserver(draw).observe(svg);
  $('readout').innerHTML = defaultRead();
  const hot = f => {
    svg.querySelectorAll('.tick').forEach(t => t.classList.toggle('hot', t.dataset.f === f));
    sil.querySelectorAll('path').forEach(p => p.classList.toggle('hot', p.dataset.f === f));
  };
  const nearest = ev => {
    const r = svg.getBoundingClientRect(), x = ev.clientX - r.left;
    let best = null, bd = 1e9; hv.forEach(c => { const d = Math.abs(svg._X(c.hv) - x); if (d < bd) { bd = d; best = c; } });
    return best;
  };
  svg.addEventListener('pointermove', ev => { const c = nearest(ev); hot(c.f); const rk = rankOf('hv', c.f);
    $('readout').innerHTML = `<b>${c.n}</b> ${money(c.hv)} · ${ord(rk.r)} of ${rk.n}`; });
  svg.addEventListener('pointerleave', () => { hot(sel); $('readout').innerHTML = defaultRead(); });
  svg.addEventListener('click', ev => select(nearest(ev).f));
  mast.hot = hot;
}

/* ---------- atlas ---------- */
function atlas() {
  $('tabs').innerHTML = Object.entries(METRICS).map(([k, m]) => `<button type="button" id="tab-${k}" data-m="${k}" aria-pressed="${k === metric}">${m.label}</button>`).join('');
  $('tabs').addEventListener('click', e => { const b = e.target.closest('button'); if (!b) return; metric = b.dataset.m; paint(); });
  const map = $('map'); map.setAttribute('viewBox', `-6 -6 ${D.W + 12} ${D.H + 12}`);
  map.innerHTML = `<defs><pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)"><rect width="6" height="6" fill="var(--hatch-bg)"/><line x1="0" y1="0" x2="0" y2="6" stroke="var(--hatch)" stroke-width="1.6"/></pattern></defs>`
    + `<g id="cties">${Object.entries(D.paths).map(([f, d]) => `<path class="cty" data-f="${f}" d="${d}"><title>${BY[f].n} County</title></path>`).join('')}</g><g id="selg"></g>`;
  map.querySelectorAll('title').forEach(t => t.remove()); // custom tooltip instead
  const tip = $('tip'), box = $('mapbox');
  map.addEventListener('pointermove', e => {
    const p = e.target.closest('.cty'); if (!p) { tip.hidden = true; return; }
    const c = BY[p.dataset.f], m = METRICS[metric], rk = rankOf(metric, c.f), r = box.getBoundingClientRect();
    tip.innerHTML = `<b>${c.n} County</b><span>${c[metric] == null ? 'No published data' : m.unit(c[metric]) + (rk ? ` · ${ord(rk.r)} of ${rk.n}` : '')}</span>`;
    tip.hidden = false;
    const x = Math.min(Math.max(e.clientX - r.left, 80), r.width - 80);
    tip.style.left = x + 'px'; tip.style.top = (e.clientY - r.top) + 'px';
  });
  map.addEventListener('pointerleave', () => tip.hidden = true);
  map.addEventListener('click', e => { const p = e.target.closest('.cty'); if (p) select(p.dataset.f); });
  const s = $('county-select');
  s.innerHTML = C.map(c => `<option value="${c.f}">${c.n}</option>`).join('');
  s.addEventListener('change', () => select(s.value));
}
function paint() {
  const m = METRICS[metric];
  document.querySelectorAll('#tabs button').forEach(b => b.setAttribute('aria-pressed', b.dataset.m === metric));
  document.querySelectorAll('#map .cty').forEach(p => {
    const v = BY[p.dataset.f][metric];
    p.classList.toggle('na', v == null);
    p.style.fill = v == null ? '' : `var(--${m.ramp}${bin(metric, v)})`;
  });
  const have = C.filter(c => c[metric] != null).length;
  $('map-title').textContent = m.title;
  $('map-cov').textContent = `${have} of 55 counties reporting`;
  $('map-note').textContent = m.note;
  const b = m.breaks;
  $('legend').innerHTML = `<div class="ramp" role="img" aria-label="Legend: seven bands with breaks at ${b.map(m.bl).join(', ')}">${b.concat([0]).map((_, i) => `<i style="background:var(--${m.ramp}${i})"></i>`).join('')}`
    + b.map((v, i) => `<span class="edge" style="left:${(i + 1) / 7 * 100}%"></span><small style="left:${(i + 1) / 7 * 100}%">${m.bl(v)}</small>`).join('') + `</div>`
    + `<div class="na-key"><i></i><small>No data</small></div>`;
  profile();
}

/* ---------- profile ---------- */
function profile() {
  const c = BY[sel], m = METRICS[metric];
  $('county-select').value = sel;
  $('p-name').textContent = c.n + ' County';
  $('p-fips').textContent = 'FIPS ' + c.f;
  $('t-name').textContent = c.n + ' County';
  const rk = rankOf(metric, sel);
  $('p-rank').innerHTML = rk ? `Ranks <strong>${ord(rk.r)} of ${rk.n}</strong> reporting counties by ${m.title.toLowerCase().replace(', 2025','').replace(', 2022 to 2023','')}.`
    : `No published ${m.title.toLowerCase().replace(', 2025','').replace(', 2022 to 2023','')} for ${c.n} County.`;
  const g = c.g == null ? '<span class="dash">—</span>' : `<span class="${c.g >= 0 ? 'up' : 'down'}">${c.g >= 0 ? '▲' : '▼'} ${pct(c.g)}</span>`;
  const kp = [
    ['Median home value', money(c.hv), `ACS ${D.acsYear}`],
    ['Price per sq ft', c.ppsf == null ? '<span class="dash">—</span>' : '$' + Math.round(c.ppsf), c.ppsf == null ? 'not published' : ym(lpLast)],
    ['Price growth', g, 'FHFA 2023'],
    ['Median gross rent', money(c.rent), `ACS ${D.acsYear}`],
    ['Owner-occupied', c.own.toFixed(1) + '%', 'of occupied homes'],
    ['Units authorized', c.pt == null ? '<span class="dash">—</span>' : int(c.pt), c.pt == null ? 'no 2025 report' : '2025 permits'],
    ['Vacancy rate', c.vac.toFixed(1) + '%', 'of all units'],
    ['Median year built', c.built, 'housing stock'],
    ['Days on market', c.dom == null ? '<span class="dash">—</span>' : int(c.dom), c.dom == null ? 'not published' : ym(lpLast)],
  ];
  posStrip();
  $('kpis').innerHTML = kp.map(([l, v, s]) => `<div><dt>${l}</dt><dd>${v}<small>${s}</small></dd></div>`).join('');
  // selection outline
  const d = D.paths[sel], [cx, cy] = c.c;
  $('selg').innerHTML = `<path class="sel-halo" d="${d}"/><path class="sel-core" d="${d}"/><text class="sel-label" x="${cx > D.W * .8 ? cx - 14 : cx < D.W * .2 ? cx + 14 : cx}" y="${cx > D.W * .8 || cx < D.W * .2 ? cy + 26 : cy + 5}" text-anchor="${cx > D.W * .8 ? 'end' : cx < D.W * .2 ? 'start' : 'middle'}">${esc(c.n)}</text>`;
  document.querySelectorAll('.brow').forEach(r => r.classList.toggle('is-sel', r.dataset.f === sel));
  document.querySelectorAll('#tbl tbody tr').forEach(r => r.classList.toggle('is-sel', r.dataset.f === sel));
  if (mast.hot) mast.hot(sel);
  charts();
}
function posStrip() {
  const svg = $('pos'), m = METRICS[metric], c = BY[sel], vals = C.filter(x => x[metric] != null);
  $('pos-h').textContent = `${m.label} · ${vals.length} reporting counties`;
  const w = svg.clientWidth || 360, lo = Math.min(...vals.map(x => x[metric])), hi = Math.max(...vals.map(x => x[metric]));
  const X = v => 6 + (v - lo) / ((hi - lo) || 1) * (w - 12);
  let s = `<line class="ax" x1="6" x2="${w - 6}" y1="30" y2="30"/>`;
  vals.forEach(x => { if (x.f !== sel) s += `<line class="pt" x1="${X(x[metric])}" x2="${X(x[metric])}" y1="20" y2="30"/>`; });
  if (c[metric] != null) { const x = X(c[metric]); s += `<line class="me-halo" x1="${x}" x2="${x}" y1="14" y2="32"/><line class="pt me" x1="${x}" x2="${x}" y1="12" y2="34"/>`; }
  s += `<text x="6" y="48">${m.unit(lo).replace(' units', '')}</text><text x="${w - 6}" y="48" text-anchor="end">${m.unit(hi).replace(' units', '')}</text>`;
  svg.innerHTML = s;
  svg.setAttribute('aria-label', c[metric] == null ? `${c.n} County has no value for this measure.` : `${c.n} County at ${m.unit(c[metric])}, on a range from ${m.unit(lo)} to ${m.unit(hi)}.`);
}
function select(f) { sel = f; profile(); }

/* ---------- charts ---------- */
function niceTicks(lo, hi, n) {
  const span = hi - lo, step0 = span / n, mag = Math.pow(10, Math.floor(Math.log10(step0)));
  const step = [1, 2, 2.5, 5, 10].map(s => s * mag).find(s => span / s <= n) || 10 * mag;
  const t = [], end = Math.ceil(hi / step - 1e-9) * step; for (let v = Math.floor(lo / step + 1e-9) * step; v <= end + 1e-9; v += step) t.push(+v.toFixed(6));
  return t;
}
function frame(el, h) { const w = Math.max(el.clientWidth, 260); return { w, h, svg: s => `<svg viewBox="0 0 ${w} ${h}" height="${h}">${s}</svg>` }; }
function table(id, head, rows) {
  $(id).innerHTML = `<details class="dt"><summary>Data table</summary><div class="tscroll"><table><thead><tr>${head.map(h => `<th scope="col">${h}</th>`).join('')}</tr></thead><tbody>${rows.map(r => `<tr>${r.map(v => `<td>${v}</td>`).join('')}</tr>`).join('')}</tbody></table></div></details>`;
}
function empty(el, msg) { el.innerHTML = `<div class="empty">${msg}</div>`; }

function lineChart(el, pts, { yFmt, xTicks, xLab, base, endFmt }) {
  const F = frame(el, 230), L = 48, R = 14, T = 16, B = 26;
  const ys = pts.map(p => p[1]), lo0 = Math.min(...ys, base ?? Infinity), hi0 = Math.max(...ys, base ?? -Infinity);
  const yt = niceTicks(lo0, hi0 + (hi0 - lo0) * .06, 4);
  const y0 = yt[0], y1 = yt[yt.length - 1], x0 = pts[0][0], x1 = pts[pts.length - 1][0];
  const X = v => L + (v - x0) / (x1 - x0) * (F.w - L - R), Y = v => T + (1 - (v - y0) / (y1 - y0)) * (F.h - T - B);
  let s = yt.map(v => `<line class="grid" x1="${L}" x2="${F.w - R}" y1="${Y(v)}" y2="${Y(v)}"/><text x="${L - 6}" y="${Y(v) + 4}" text-anchor="end">${yFmt(v)}</text>`).join('');
  s += xTicks.map(v => `<text x="${X(v)}" y="${F.h - 6}" text-anchor="middle">${xLab(v)}</text>`).join('');
  if (base != null) s += `<line class="base" x1="${L}" x2="${F.w - R}" y1="${Y(base)}" y2="${Y(base)}"/>`;
  const d = pts.map((p, i) => (i ? 'L' : 'M') + X(p[0]).toFixed(1) + ',' + Y(p[1]).toFixed(1)).join('');
  s += `<path class="ar" d="${d}L${X(x1)},${Y(y0)}L${X(x0)},${Y(y0)}Z"/><path class="ln" d="${d}"/>`;
  const e = pts[pts.length - 1];
  s += `<circle class="dot" cx="${X(e[0])}" cy="${Y(e[1])}" r="4.5"/><text class="lab" x="${X(e[0]) - 8}" y="${Y(e[1]) - 10}" text-anchor="end">${endFmt(e[1])}</text>`;
  el.innerHTML = F.svg(s);
}

function charts() {
  const c = BY[sel];
  // HPI
  const eh = $('c-hpi');
  if (c.hpi.length > 2) {
    const first = c.hpi[0][0], last = c.hpi[c.hpi.length - 1][0];
    const xt = []; for (let y = Math.ceil(first / 5) * 5; y <= last; y += 5) xt.push(y);
    lineChart(eh, c.hpi, { yFmt: v => v, xTicks: xt, xLab: v => v, base: 100, endFmt: v => `${last}: ${v.toFixed(0)}` });
    eh.setAttribute('aria-label', `Line chart: ${c.n} County house price index rose from 100 in 2000 to ${c.hpi[c.hpi.length - 1][1].toFixed(0)} in ${last}.`);
    table('d-hpi', ['Year', 'Index (2000 = 100)'], c.hpi.slice().reverse().map(r => [r[0], r[1].toFixed(1)]));
  } else { empty(eh, `FHFA does not publish a county index for ${esc(c.n)} County.`); eh.setAttribute('aria-label', 'No data'); $('d-hpi').innerHTML = ''; }
  // Listing price
  const el = $('c-lp');
  if (c.lps.length) {
    const pts = c.lps.filter(p => p[1] != null).map(p => [+p[0].slice(0, 4) + (+p[0].slice(5) - 1) / 12, p[1]]);
    const xt = []; for (let y = Math.ceil(pts[0][0]); y <= pts[pts.length - 1][0]; y += (el.clientWidth < 420 ? 3 : 2)) xt.push(y);
    lineChart(el, pts, { yFmt: kMoney, xTicks: xt, xLab: v => v, endFmt: v => `${ym(lpLast)}: ${money(v)}` });
    el.setAttribute('aria-label', `Line chart: ${c.n} County median listing price by month, latest ${money(pts[pts.length - 1][1])}.`);
    table('d-lp', ['Month', 'Median listing price'], c.lps.slice().reverse().map(r => [ym(r[0]), money(r[1])]));
  } else { empty(el, `Realtor.com publishes no listing series for ${esc(c.n)} County. Coverage is limited to the 12 counties with the most listings.`); el.setAttribute('aria-label', 'No data'); $('d-lp').innerHTML = ''; }
  // Permits
  const ep = $('c-perm'), P = c.perm;
  {
    const F = frame(ep, 230), L = 44, R = 8, T = 14, B = 26, mx = Math.max(...P.map(r => r[1] + r[2]), 4);
    const yt = niceTicks(0, mx * 1.05, 4), y1 = yt[yt.length - 1], n = P.length, bw = (F.w - L - R) / n;
    const X = i => L + i * bw, Y = v => T + (1 - v / y1) * (F.h - T - B);
    let s = yt.map(v => `<line class="grid" x1="${L}" x2="${F.w - R}" y1="${Y(v)}" y2="${Y(v)}"/><text x="${L - 6}" y="${Y(v) + 4}" text-anchor="end">${int(v)}</text>`).join('');
    P.forEach((r, i) => {
      const g = Math.max(bw * .22, 1), x = X(i) + g / 2, w = bw - g;
      s += `<rect class="sf" x="${x}" width="${w}" y="${Y(r[1])}" height="${Y(0) - Y(r[1])}"/>`;
      if (r[2]) s += `<rect class="mf" x="${x}" width="${w}" y="${Y(r[1] + r[2])}" height="${Y(r[1]) - Y(r[1] + r[2])}"/>`;
      if (r[0] % 5 === 0) s += `<text x="${X(i) + bw / 2}" y="${F.h - 6}" text-anchor="middle">${r[0]}</text>`;
    });
    ep.innerHTML = F.svg(s);
    ep.setAttribute('aria-label', `Stacked bar chart of residential units authorized in ${c.n} County, ${P[0][0]} to ${P[n - 1][0]}.`);
    table('d-perm', ['Year', 'Single-family', 'Multifamily', 'Total'], P.slice().reverse().map(r => [r[0], int(r[1]), int(r[2]), int(r[1] + r[2])]));
  }
  // FMR
  const ef = $('c-fmr');
  {
    const F = frame(ef, 230), L = 44, R = 8, T = 22, B = 26, labs = ['Studio', '1 BR', '2 BR', '3 BR', '4 BR'];
    const mx = Math.max(...c.fmr, c.rent || 0), yt = niceTicks(0, mx * 1.12, 4), y1 = yt[yt.length - 1], bw = (F.w - L - R) / 5;
    const Y = v => T + (1 - v / y1) * (F.h - T - B);
    let s = yt.map(v => `<line class="grid" x1="${L}" x2="${F.w - R}" y1="${Y(v)}" y2="${Y(v)}"/><text x="${L - 6}" y="${Y(v) + 4}" text-anchor="end">${kMoney(v).replace(/^\$0k$/, '$0')}</text>`).join('');
    c.fmr.forEach((v, i) => {
      const x = L + i * bw + bw * .16, w = bw * .68;
      s += `<rect class="bar" x="${x}" width="${w}" y="${Y(v)}" height="${Y(0) - Y(v)}"/><text class="inlab" x="${x + w / 2}" y="${Y(v) + 16}" text-anchor="middle">${money(v)}</text>`;
      s += `<text x="${x + w / 2}" y="${F.h - 6}" text-anchor="middle">${labs[i]}</text>`;
    });
    if (c.rent) s += `<line class="rent" x1="${L}" x2="${F.w - R}" y1="${Y(c.rent)}" y2="${Y(c.rent)}"/><text class="rentlab" x="${L + 4}" y="${Y(c.rent) - 6}">ACS median ${money(c.rent)}</text>`;
    ef.innerHTML = F.svg(s);
    ef.setAttribute('aria-label', `Bar chart of HUD Fair Market Rents in ${c.n} County: ${c.fmr.map((v, i) => labs[i] + ' ' + money(v)).join(', ')}.`);
    table('d-fmr', ['Unit', 'Fair Market Rent'], c.fmr.map((v, i) => [labs[i], money(v)]).concat([['ACS median gross rent', money(c.rent)]]));
  }
}

/* ---------- construction ---------- */
let showAll = false;
function build() {
  const rows = C.filter(c => c.pt != null).sort((a, b) => b.pt - a.pt), tot = rows.reduce((s, c) => s + c.pt, 0);
  const top2 = rows[0].pt + rows[1].pt;
  $('share').textContent = Math.round(top2 / tot * 100) + '%';
  $('share-cap').innerHTML = `of the <strong>${int(tot)}</strong> homes authorized statewide in 2025 were in just two Eastern Panhandle counties: <strong>${rows[0].n}</strong> (${int(rows[0].pt)}) and <strong>${rows[1].n}</strong> (${int(rows[1].pt)}).`;
  const mx = rows[0].pt, list = showAll ? rows : rows.slice(0, 15);
  $('bars').innerHTML = list.map(c => `<div class="brow${c.f === sel ? ' is-sel' : ''}" data-f="${c.f}" role="button" tabindex="0" aria-label="${c.n}: ${c.pt} units, ${c.psf} single-family"><span class="bname">${c.n}</span><span class="btrack"><i class="sf" style="width:${c.psf / mx * 100}%"></i><i class="mf" style="width:${(c.pt - c.psf) / mx * 100}%"></i></span><span class="bval">${int(c.pt)}</span></div>`).join('');
  const more = $('more'); more.textContent = showAll ? 'Show top 15' : `Show all ${rows.length} counties`; more.setAttribute('aria-expanded', showAll);
}

/* ---------- table ---------- */
const COLS = [
  ['n', 'County', c => `${esc(c.n)}`, 1], ['f', 'FIPS', c => `<span class="fips">${c.f}</span>`, 1],
  ['hv', 'Home value', c => money(c.hv)], ['ppsf', '$/sq ft', c => c.ppsf == null ? '—' : '$' + Math.round(c.ppsf)],
  ['g', 'Growth 2023', c => pct(c.g)], ['pt', 'Permits 2025', c => int(c.pt)],
  ['rent', 'Median rent', c => money(c.rent)], ['own', 'Owner-occ.', c => c.own.toFixed(1) + '%'],
];
let sortK = 'n', sortD = 1;
function tbl() {
  const t = $('tbl');
  t.tHead.innerHTML = '<tr>' + COLS.map(([k, l]) => `<th scope="col" aria-sort="${k === sortK ? (sortD > 0 ? 'ascending' : 'descending') : 'none'}"><button type="button" data-k="${k}">${l}</button></th>`).join('') + '</tr>';
  const rows = C.slice().sort((a, b) => {
    const x = a[sortK], y = b[sortK];
    if (x == null && y == null) return 0; if (x == null) return 1; if (y == null) return -1;
    return (typeof x === 'string' ? x.localeCompare(y) : x - y) * sortD;
  });
  t.tBodies[0].innerHTML = rows.map(c => `<tr data-f="${c.f}"${c.f === sel ? ' class="is-sel"' : ''}>${COLS.map(([k, , fn], i) => i === 0 ? `<th scope="row" style="font-weight:600">${fn(c)}</th>` : `<td${c[k] == null ? ' class="m"' : ''}>${fn(c)}</td>`).join('')}</tr>`).join('');
}

/* ---------- wire up ---------- */
mast(); atlas(); build(); tbl(); paint();
$('more').addEventListener('click', () => { showAll = !showAll; build(); });
$('bars').addEventListener('click', e => { const r = e.target.closest('.brow'); if (r) select(r.dataset.f); });
$('bars').addEventListener('keydown', e => { const r = e.target.closest('.brow'); if (r && (e.key === 'Enter' || e.key === ' ')) { e.preventDefault(); select(r.dataset.f); } });
$('tbl').addEventListener('click', e => {
  const b = e.target.closest('thead button');
  if (b) { const k = b.dataset.k; sortD = k === sortK ? -sortD : (k === 'n' || k === 'f' ? 1 : -1); sortK = k; tbl(); return; }
  const r = e.target.closest('tbody tr'); if (r) { select(r.dataset.f); document.querySelector('.atlas').scrollIntoView({ behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'auto' : 'smooth', block: 'start' }); }
});
let rt; new ResizeObserver(() => { clearTimeout(rt); rt = setTimeout(() => { charts(); posStrip(); }, 120); }).observe(document.querySelector('.charts'));
