/* ---------- Statistics tab ----------
   Everything is computed here from the review log (LOG: [ts, side key, grade, ms, elapsed days,
   stability before]) and the card states — the same numbers tools/stats.py prints in the chat.
   Charts are plain SVG: thin marks, hairline grid, one value axis, a hover tooltip on every mark,
   and a "table" toggle under each chart so no number is reachable only by hovering. */
var NS = 'http://www.w3.org/2000/svg';
function sv(tag, attrs, text){ var e = document.createElementNS(NS, tag); for (var k in attrs) e.setAttribute(k, attrs[k]); if (text != null) e.textContent = text; return e; }
var TIP = null;
function tipShow(ev, lines){
  if (!TIP){ TIP = el('div', 'viz-tip'); document.body.appendChild(TIP); }
  TIP.innerHTML = ''; lines.forEach(function(l, i){ var r = el('div', i ? 'tl' : 'tv'); if (l[1]){ var k = el('i', 'tk'); k.style.background = l[1]; r.appendChild(k); } r.appendChild(document.createTextNode(l[0])); TIP.appendChild(r); });
  TIP.hidden = false;
  var x = ev.clientX + 14, y = ev.clientY + 14;
  if (x + TIP.offsetWidth > innerWidth - 8) x = ev.clientX - TIP.offsetWidth - 14;
  if (y + TIP.offsetHeight > innerHeight - 8) y = ev.clientY - TIP.offsetHeight - 14;
  TIP.style.left = x + 'px'; TIP.style.top = y + 'px';
}
function tipHide(){ if (TIP) TIP.hidden = true; }
function niceMax(v){ if (v <= 0) return 1; var p = Math.pow(10, Math.floor(Math.log10(v))), f = v / p; return (f <= 1 ? 1 : f <= 2 ? 2 : f <= 5 ? 5 : 10) * p; }
function vizCard(title, sub){ var c = el('div', 'card viz'); c.appendChild(el('h3', null, title)); if (sub) c.appendChild(el('p', 'meta', sub)); return c; }
function tableToggle(card, head, rows){
  var d = el('details', 'viz-table'); d.appendChild(el('summary', null, L('asTable')));
  var t = el('table'), tr = el('tr'); head.forEach(function(h){ tr.appendChild(el('th', null, h)); }); t.appendChild(tr);
  rows.forEach(function(r){ var x = el('tr'); r.forEach(function(v, i){ x.appendChild(el('td', i ? 'num' : null, v)); }); t.appendChild(x); });
  d.appendChild(t); card.appendChild(d);
}
/* vertical bars: data [{label, v, tip, color?}], opts {fmt, max, ref, refLabel, h} */
function barChart(data, opts){
  opts = opts || {};
  var W = 640, H = opts.h || 200, padL = 40, padB = 26, padT = 12, n = data.length, iw = W - padL - 8, ih = H - padB - padT;
  var max = opts.max || niceMax(Math.max.apply(null, data.map(function(d){ return d.v; }).concat([opts.ref || 0, 0.0001])));
  var svg = sv('svg', {viewBox: '0 0 ' + W + ' ' + H, class: 'viz-svg', role: 'img', 'aria-label': opts.aria || ''});
  for (var i = 0; i <= 4; i++){ var y = padT + ih - ih * i / 4; svg.appendChild(sv('line', {x1: padL, x2: W - 8, y1: y, y2: y, class: i ? 'grid' : 'axis'})); svg.appendChild(sv('text', {x: padL - 6, y: y + 4, class: 'tick', 'text-anchor': 'end'}, (opts.fmt || String)(max * i / 4))); }
  var band = iw / Math.max(1, n), bw = Math.min(24, band * 0.7);
  data.forEach(function(d, i){
    var x = padL + band * i + (band - bw) / 2, h = Math.max(0, ih * d.v / max), y = padT + ih - h;
    var g = sv('g', {class: 'mark', tabindex: 0});
    g.appendChild(sv('rect', {x: padL + band * i, y: padT, width: band, height: ih, class: 'hit'}));
    if (h > 0) g.appendChild(sv('path', {d: 'M' + x + ',' + (padT + ih) + 'V' + (y + Math.min(4, h)) + 'q0,-4 4,-4h' + (bw - 8) + 'q4,0 4,4V' + (padT + ih) + 'Z', class: 'bar', style: 'fill:' + (d.color || 'var(--c1)')}));
    var show = function(ev){ tipShow(ev, d.tip || [[(opts.fmt || String)(d.v)], [d.label]]); };
    g.addEventListener('pointermove', show); g.addEventListener('pointerleave', tipHide);
    g.addEventListener('focus', function(){ var r = g.getBoundingClientRect(); show({clientX: r.left + r.width / 2, clientY: r.top}); }); g.addEventListener('blur', tipHide);
    svg.appendChild(g);
    var every = Math.ceil(n / 10);
    if (i % every === 0 || i === n - 1) svg.appendChild(sv('text', {x: padL + band * i + band / 2, y: H - 8, class: 'tick', 'text-anchor': 'middle'}, d.label));
  });
  if (opts.ref != null){ var ry = padT + ih - ih * opts.ref / max; svg.appendChild(sv('line', {x1: padL, x2: W - 8, y1: ry, y2: ry, class: 'ref'})); svg.appendChild(sv('text', {x: W - 10, y: ry - 5, class: 'tick ref-t', 'text-anchor': 'end'}, opts.refLabel || '')); }
  return svg;
}
/* lines over time: series [{name, color, pts:[[ts, y]]}] with a crosshair snapping to the nearest day */
function lineChart(series, opts){
  opts = opts || {};
  var W = 640, H = opts.h || 220, padL = 40, padB = 26, padT = 14, padR = 64, iw = W - padL - padR, ih = H - padT - padB;
  var xs = []; series.forEach(function(s){ s.pts.forEach(function(p){ xs.push(p[0]); }); });
  var x0 = Math.min.apply(null, xs), x1 = Math.max.apply(null, xs); if (x1 === x0) x1 = x0 + DAY;
  var max = opts.max || niceMax(Math.max.apply(null, series.map(function(s){ return Math.max.apply(null, s.pts.map(function(p){ return p[1] || 0; })); }).concat([0.0001])));
  var X = function(t){ return padL + iw * (t - x0) / (x1 - x0); }, Y = function(v){ return padT + ih - ih * v / max; };
  var svg = sv('svg', {viewBox: '0 0 ' + W + ' ' + H, class: 'viz-svg', role: 'img', 'aria-label': opts.aria || ''});
  for (var i = 0; i <= 4; i++){ var y = padT + ih - ih * i / 4; svg.appendChild(sv('line', {x1: padL, x2: W - padR, y1: y, y2: y, class: i ? 'grid' : 'axis'})); svg.appendChild(sv('text', {x: padL - 6, y: y + 4, class: 'tick', 'text-anchor': 'end'}, (opts.fmt || String)(max * i / 4))); }
  [x0, (x0 + x1) / 2, x1].forEach(function(t, i){ svg.appendChild(sv('text', {x: X(t), y: H - 8, class: 'tick', 'text-anchor': i === 0 ? 'start' : i === 2 ? 'end' : 'middle'}, fmtShort(t))); });
  series.forEach(function(s){
    var pts = s.pts.filter(function(p){ return p[1] != null; }); if (!pts.length) return;
    svg.appendChild(sv('path', {d: pts.map(function(p, i){ return (i ? 'L' : 'M') + X(p[0]).toFixed(1) + ',' + Y(p[1]).toFixed(1); }).join(''), class: 'line', style: 'stroke:' + s.color}));
    var last = pts[pts.length - 1];
    svg.appendChild(sv('circle', {cx: X(last[0]), cy: Y(last[1]), r: 4, class: 'dot', style: 'fill:' + s.color}));
    svg.appendChild(sv('text', {x: X(last[0]) + 8, y: Y(last[1]) + 4, class: 'end-l'}, (opts.fmt || String)(last[1])));
  });
  var cross = sv('line', {y1: padT, y2: padT + ih, class: 'cross', visibility: 'hidden'}); svg.appendChild(cross);
  var hit = sv('rect', {x: padL, y: padT, width: iw, height: ih, class: 'hit'}); svg.appendChild(hit);
  hit.addEventListener('pointermove', function(ev){
    var r = svg.getBoundingClientRect(), t = x0 + (x1 - x0) * Math.max(0, Math.min(1, ((ev.clientX - r.left) * W / r.width - padL) / iw));
    var best = null; xs.forEach(function(x){ if (best == null || Math.abs(x - t) < Math.abs(best - t)) best = x; });
    cross.setAttribute('x1', X(best)); cross.setAttribute('x2', X(best)); cross.setAttribute('visibility', 'visible');
    var lines = [[fmtDay(best)]]; series.forEach(function(s){ var p = s.pts.filter(function(q){ return q[0] === best; })[0]; if (p && p[1] != null) lines.push([(opts.fmt || String)(p[1]) + ' · ' + s.name, s.color]); });
    tipShow(ev, lines);
  });
  hit.addEventListener('pointerleave', function(){ cross.setAttribute('visibility', 'hidden'); tipHide(); });
  return svg;
}
/* activity calendar: one cell per day, the last 26 weeks, sequential blue by the number of answers */
function heatmap(byDay){
  var weeks = 26, cell = 14, gap = 3, padL = 26, padT = 16, W = padL + weeks * (cell + gap), H = padT + 7 * (cell + gap) + 4;
  var svg = sv('svg', {viewBox: '0 0 ' + W + ' ' + H, class: 'viz-svg heat', role: 'img', 'aria-label': L('heatTitle')});
  var end = today0(), dow = (new Date(end).getDay() + 6) % 7, start = end - (weeks * 7 - 1 - (6 - dow)) * DAY;
  var vals = Object.keys(byDay).map(function(k){ return byDay[k]; }), mx = Math.max.apply(null, vals.concat([1]));
  ['1', '3', '5'].forEach(function(r){ svg.appendChild(sv('text', {x: 0, y: padT + (+r) * (cell + gap) + 11, class: 'tick'}, new Date(2024, 0, (+r) + 1).toLocaleDateString(TRL, {weekday: 'short'}))); });
  var lastMonth = -1;
  for (var d = start; d <= end; d += DAY){
    var i = Math.round((d - start) / DAY), wk = Math.floor(i / 7), wd = i % 7, n = byDay[day0(d)] || 0;
    var lvl = n ? Math.min(4, Math.ceil(4 * n / mx)) : 0;
    var r = sv('rect', {x: padL + wk * (cell + gap), y: padT + wd * (cell + gap), width: cell, height: cell, rx: 3, class: 'hc l' + lvl, tabindex: -1});
    (function(dd, nn){ r.addEventListener('pointermove', function(ev){ tipShow(ev, [[nWord(nn, 'answersN')], [fmtDay(dd)]]); }); r.addEventListener('pointerleave', tipHide); })(d, n);
    svg.appendChild(r);
    var m = new Date(d).getMonth(); if (wd === 0 && m !== lastMonth){ lastMonth = m; svg.appendChild(sv('text', {x: padL + wk * (cell + gap), y: 10, class: 'tick'}, new Date(d).toLocaleDateString(TRL, {month: 'short'}))); }
  }
  return svg;
}

function logSince(ms){ var from = NOW() - ms; return LOG.filter(function(x){ return x[0] >= from; }); }
function sideOf(k){ return k.split('|')[1] || ''; }
function idOf(k){ return k.split('|')[0]; }
function renderStats(main){
  main.appendChild(el('h2', 'tr-h', L('statsTitle')));
  if (!LOG.length){ main.appendChild(el('p', 'meta', L('statsEmpty'))); }
  snapshot();
  var cov = coverageNow(), words = itemsOfKind('word'), ws = stats(words), last30 = logSince(30 * DAY);
  var rev30 = last30.filter(function(x){ return x[4] >= 1; }), ret30 = rev30.length ? rev30.filter(function(x){ return x[2] > 1; }).length / rev30.length : null;
  var minsWeek = Math.round(logSince(7 * DAY).reduce(function(a, x){ return a + Math.min(60000, x[3] || 0); }, 0) / 60000);
  // hero + tiles
  var hero = el('div', 'hero-stat'), hv = el('div', 'hero-v', pct(cov.spoken));
  hero.appendChild(hv); hero.appendChild(el('div', 'hero-l', L('heroCov')));
  var ceil = COV.spCeil ? ' ' + L('heroCeil').replace('{x}', pct(COV.spCeil)) : ''; hero.appendChild(el('p', 'meta', L('heroCovNote') + ceil));
  main.appendChild(hero);
  var tiles = el('div', 'tr-stats');
  [[cov.my == null ? '—' : pct(cov.my), L('covMyLong')], [ws.learned + ' / ' + words.length, L('wordsLearned')], [ret30 == null ? '—' : pct(ret30), L('retention30')], [minsWeek + ' ' + L('min'), L('minsWeek')], [streak(), L('streak')]].forEach(function(x){
    var c = el('div', 'tr-stat'); c.appendChild(el('b', null, x[0])); c.appendChild(el('span', null, x[1])); tiles.appendChild(c); });
  main.appendChild(tiles);
  var grid = el('div', 'viz-grid'); main.appendChild(grid);

  // 1. coverage over time
  var hk = Object.keys(T.hist || {}).sort();
  if (hk.length){
    var c1 = vizCard(L('covTime'), L('covTimeSub'));
    var tsOf = function(k){ var p = k.split('-'); return new Date(+p[0], +p[1] - 1, +p[2]).getTime(); };
    var s1 = {name: L('covSpoken'), color: 'var(--c1)', pts: hk.map(function(k){ return [tsOf(k), T.hist[k].sp]; })};
    var s2 = {name: L('covMy'), color: 'var(--c2)', pts: hk.map(function(k){ return [tsOf(k), T.hist[k].my]; })};
    var lg = el('div', 'viz-legend'); [s1, s2].forEach(function(s){ var i = el('span'), k = el('i', 'lk'); k.style.background = s.color; i.appendChild(k); i.appendChild(document.createTextNode(s.name)); lg.appendChild(i); });
    c1.appendChild(lg); c1.appendChild(lineChart([s1, s2], {fmt: pct, max: 1, aria: L('covTime')}));
    tableToggle(c1, [L('colDay'), L('covSpoken'), L('covMy')], hk.slice(-30).reverse().map(function(k){ return [k, pct(T.hist[k].sp), pct(T.hist[k].my)]; }));
    grid.appendChild(c1);
  }
  // 2. situations readiness
  if (SITS.length){
    var c2 = vizCard(L('sitReady'), L('sitReadySub')), data = SITS.map(function(s){ var it = sitItems(s.id), p = 0; it.forEach(function(x){ p += itemPct(x); }); var v = it.length ? p / it.length : 0; return {label: s.title_sr || s.title, v: v, tip: [[pct(v)], [s.title]]}; });
    c2.appendChild(barChart(data, {fmt: pct, max: 1, aria: L('sitReady')}));
    tableToggle(c2, [L('colSit'), L('ready')], SITS.map(function(s, i){ return [s.title, pct(data[i].v)]; }));
    grid.appendChild(c2);
  }
  // 3. retention by week vs target
  var weeks = []; for (var w = 11; w >= 0; w--){ var a = today0() - (w * 7 + 6) * DAY, b = today0() - w * 7 * DAY + DAY; var r = LOG.filter(function(x){ return x[0] >= a && x[0] < b && x[4] >= 1; }); weeks.push({from: a, n: r.length, ok: r.filter(function(x){ return x[2] > 1; }).length}); }
  var c3 = vizCard(L('retWeeks'), L('retWeeksSub').replace('{t}', pct(T.retention)));
  c3.appendChild(barChart(weeks.map(function(x){ var v = x.n ? x.ok / x.n : 0; return {label: fmtShort(x.from), v: v, color: x.n && v < T.retention - 0.05 ? 'var(--c2)' : 'var(--c1)', tip: [[x.n ? pct(v) : L('noData')], [L('weekOf') + ' ' + fmtShort(x.from) + ' · ' + nWord(x.n, 'answersN')]]}; }), {fmt: pct, max: 1, ref: T.retention, refLabel: L('target') + ' ' + pct(T.retention), aria: L('retWeeks')}));
  tableToggle(c3, [L('weekOf'), L('answers'), L('remembered')], weeks.slice().reverse().map(function(x){ return [fmtShort(x.from), x.n, x.n ? pct(x.ok / x.n) : '—']; }));
  grid.appendChild(c3);
  // 4. memory by interval (how much is kept after N days)
  var B = [[1, 2, '1'], [2, 4, '2–3'], [4, 8, '4–7'], [8, 15, '8–14'], [15, 31, '15–30'], [31, 1e9, '31+']], bk = B.map(function(x){ var r = LOG.filter(function(y){ return y[4] >= x[0] && y[4] < x[1]; }); return {label: x[2], n: r.length, ok: r.filter(function(y){ return y[2] > 1; }).length}; });
  var c4 = vizCard(L('curve'), L('curveSub'));
  c4.appendChild(barChart(bk.map(function(x){ var v = x.n ? x.ok / x.n : 0; return {label: x.label, v: v, tip: [[x.n ? pct(v) : L('noData')], [x.label + ' ' + L('dShort') + ' · ' + nWord(x.n, 'answersN')]]}; }), {fmt: pct, max: 1, ref: T.retention, refLabel: L('target'), aria: L('curve')}));
  tableToggle(c4, [L('afterDays'), L('answers'), L('remembered')], bk.map(function(x){ return [x.label, x.n, x.n ? pct(x.ok / x.n) : '—']; }));
  grid.appendChild(c4);
  // 5. calendar
  var c5 = vizCard(L('heatTitle'), L('heatSub')); c5.appendChild(heatmap(activeDays()));
  var hl = el('div', 'heat-key'); hl.appendChild(el('span', 'meta', L('less'))); for (var lv = 0; lv <= 4; lv++){ var sq = el('i', 'hc l' + lv); hl.appendChild(sq); } hl.appendChild(el('span', 'meta', L('more'))); c5.appendChild(hl);
  grid.appendChild(c5);
  // 6. minutes per day, last 30 days
  var md = []; for (var dd = 29; dd >= 0; dd--){ var d0 = today0() - dd * DAY, rr = LOG.filter(function(x){ return x[0] >= d0 && x[0] < d0 + DAY; }); md.push({d: d0, m: rr.reduce(function(a, x){ return a + Math.min(60000, x[3] || 0); }, 0) / 60000, n: rr.length}); }
  var c6 = vizCard(L('timeDay'), L('timeDaySub'));
  c6.appendChild(barChart(md.map(function(x){ return {label: new Date(x.d).getDate() + '', v: Math.round(x.m * 10) / 10, tip: [[Math.round(x.m) + ' ' + L('min') + ' · ' + nWord(x.n, 'answersN')], [fmtDay(x.d)]]}; }), {fmt: function(v){ return Math.round(v) + ''; }, aria: L('timeDay')}));
  tableToggle(c6, [L('colDay'), L('min'), L('answers')], md.slice().reverse().filter(function(x){ return x.n; }).map(function(x){ return [fmtShort(x.d), Math.round(x.m), x.n]; }));
  grid.appendChild(c6);
  // 7. by side: accuracy and answer time — where the weak spot is
  var SIDES = ['pick-tr', 'listen', 'pick-sr', 'say-tr', 'say-sr', 'type', 'listen-ph', 'read-ph', 'say-ph', 'cloze', 'aspect', 'reply'];
  var bs = SIDES.map(function(sd){ var r = last30.filter(function(x){ return sideOf(x[1]) === sd; }); return {sd: sd, n: r.length, ok: r.filter(function(x){ return x[2] > 1; }).length, ms: r.length ? r.reduce(function(a, x){ return a + Math.min(60000, x[3] || 0); }, 0) / r.length : 0}; }).filter(function(x){ return x.n; });
  if (bs.length){
    var c7 = vizCard(L('bySide'), L('bySideSub'));
    c7.appendChild(barChart(bs.map(function(x){ var v = x.ok / x.n; return {label: L('sd_' + x.sd), v: v, tip: [[pct(v) + ' · ' + (x.ms / 1000).toFixed(1) + ' ' + L('sec')], [L('sdl_' + x.sd) + ' · ' + nWord(x.n, 'answersN')]]}; }), {fmt: pct, max: 1, aria: L('bySide')}));
    tableToggle(c7, [L('colSide'), L('answers'), L('remembered'), L('avgTime')], bs.map(function(x){ return [L('sdl_' + x.sd), x.n, pct(x.ok / x.n), (x.ms / 1000).toFixed(1) + ' ' + L('sec')]; }));
    grid.appendChild(c7);
  }
  // 8. load: reviews due in each of the next 30 days
  var load = []; for (var k2 = 0; k2 < 30; k2++) load.push(0);
  Object.keys(T.cards).forEach(function(kk){ var c = T.cards[kk]; if (!c || !c.due) return; var i = Math.floor((day0(c.due) - today0()) / DAY); if (i < 0) i = 0; if (i < 30) load[i]++; });
  var c8 = vizCard(L('load'), L('loadSub'));
  c8.appendChild(barChart(load.map(function(v, i){ var d = today0() + i * DAY; return {label: i === 0 ? L('today') : new Date(d).getDate() + '', v: v, tip: [[nWord(v, 'cards')], [fmtDay(d)]]}; }), {aria: L('load')}));
  tableToggle(c8, [L('colDay'), L('cardsDue')], load.map(function(v, i){ return [fmtShort(today0() + i * DAY), v]; }).filter(function(r){ return r[1]; }));
  grid.appendChild(c8);
  // 9. cases and aspect
  var cz = {}; LOG.forEach(function(x){ var id = idOf(x[1]); if (id.indexOf('c:') !== 0 && id.indexOf('v:') !== 0) return; var c = DECK.cloze.filter(function(q){ return q.id === id; })[0]; var cs = id.indexOf('v:') === 0 ? 'aspect' : c && c.case || 'other'; cz[cs] = cz[cs] || {n: 0, ok: 0}; cz[cs].n++; if (x[2] > 1) cz[cs].ok++; });
  var czk = Object.keys(cz);
  if (czk.length){
    var c9 = vizCard(L('cases'), L('casesSub'));
    c9.appendChild(barChart(czk.map(function(kk){ var v = cz[kk].ok / cz[kk].n; return {label: L('case_' + kk), v: v, tip: [[pct(v)], [L('case_' + kk) + ' · ' + nWord(cz[kk].n, 'answersN')]]}; }), {fmt: pct, max: 1, aria: L('cases')}));
    tableToggle(c9, [L('colCase'), L('answers'), L('remembered')], czk.map(function(kk){ return [L('case_' + kk), cz[kk].n, pct(cz[kk].ok / cz[kk].n)]; }));
    grid.appendChild(c9);
  }
  // 10. leeches and the hardest words
  var hard = allItems().filter(seen).map(function(it){ var lp = 0, s = Infinity; sidesOf(it).forEach(function(sd){ var c = cardOf(it, sd); if (c){ lp += c.lapses || 0; s = Math.min(s, c.s); } }); return {it: it, lapses: lp, s: s}; })
    .filter(function(x){ return x.lapses > 0; }).sort(function(a, b){ return b.lapses - a.lapses || a.s - b.s; }).slice(0, 20);
  var c10 = vizCard(L('hardTitle'), L('hardSub'));
  if (!hard.length) c10.appendChild(el('p', 'meta', L('hardNone')));
  else {
    var t = el('table', 'deck-t'), hr = el('tr'); [L('colSr'), L('colTr'), L('lapses'), L('stability')].forEach(function(h){ hr.appendChild(el('th', null, h)); }); t.appendChild(hr);
    hard.forEach(function(x){ var it = x.it, o = it.it || it.me || it.a || {}; var r = el('tr', isLeech(it) ? 'st-leech' : ''); r.appendChild(el('td', 'sr', srx(o.sr || ''))); r.appendChild(el('td', null, o.tr || '')); r.appendChild(el('td', 'num', x.lapses + (isLeech(it) ? ' 🐛' : ''))); r.appendChild(el('td', 'num', (Math.round(x.s * 10) / 10) + ' ' + L('dShort'))); t.appendChild(r); });
    var wrap = el('div', 'table-wrap'); wrap.appendChild(t); c10.appendChild(wrap);
    var msg = el('p', 'meta');
    c10.appendChild(btn('btn', L('hardAsk'), async function(){ try { await sendInbox({type: 'hard', ids: hard.map(function(x){ return x.it.id; }), at: NOW()}); msg.textContent = L('hardSent'); } catch (e){ msg.textContent = L('pasteOffline'); } }));
    c10.appendChild(msg);
  }
  grid.appendChild(c10);
  // 11. forecast by group
  var c11 = vizCard(L('fcTitle'), L('fcSub')), ft = el('table', 'deck-t'), fh = el('tr'); [L('colGroup'), L('progress'), L('fcWhen')].forEach(function(h){ fh.appendChild(el('th', null, h)); }); ft.appendChild(fh);
  var before = 0; decks().forEach(function(dk){ var e = dk.words ? etaOf(dk.items, T.goal, before) : etaOf(dk.items, Math.max(1, T.goal / 4), 0); if (dk.words && e) before += e.fresh; var p = 0; dk.items.forEach(function(it){ p += itemPct(it); });
    var r = el('tr'); r.appendChild(el('td', null, dk.title)); r.appendChild(el('td', 'num', Math.round(p / Math.max(1, dk.items.length) * 100) + '%')); r.appendChild(el('td', null, etaText(e, true))); ft.appendChild(r); });
  var fw = el('div', 'table-wrap'); fw.appendChild(ft); c11.appendChild(fw); c11.appendChild(el('p', 'tr-note-s', L('etaNote')));
  grid.appendChild(c11);
  var ex = el('div', 'acts'); ex.appendChild(btn('btn', L('exportLog'), function(){ download('polako-review-log.json', JSON.stringify({cards: T.cards, log: LOG}, null, 1), 'application/json'); })); main.appendChild(ex);
}
