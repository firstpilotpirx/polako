/* ============================================================
   Polako page — core: data, storage, tabs, helpers.
   Built by tools/build_page.py from templates/portal/*.js in this order:
   core.js · fsrs.js · tts.js · trainer.js · vocab.js · situations.js · texts.js · deck.js · stats.js · boot.js
   Data comes from <script id="pl-data"> (deck, situations, own texts, coverage shares, UI strings).
   Progress lives apart from content, so a rebuild never loses it:
     local server (tools/serve.py)  → prep/trainer-state.json, prep/review-log.json, prep/vocab-state.json
     artifact db                    → doc trainer/state, collection log (one doc per day), collection vocab
     neither                        → this browser only (localStorage), with a note
   ============================================================ */
var D = JSON.parse(document.getElementById('pl-data').textContent);
var DAY = 86400000, NOW = function(){ return Date.now(); };
var PROF = D.profile || {}, DECK = D.deck || {words: [], phrases: [], cloze: []}, SITS = D.situations || [], TEXTS = D.texts || [];
var COV = D.cov || {}, UI = D.ui || {}, TRL = PROF.explain || 'ru';
['words', 'phrases', 'cloze'].forEach(function(k){ DECK[k] = (DECK[k] || []).filter(function(x){ return !x.retired; }); });

function L(k){ return UI[k] != null ? UI[k] : k; }
function $(id){ return document.getElementById(id); }
function el(tag, cls, text){ var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
function btn(cls, text, fn, key){ var b = el('button', cls, text); b.type = 'button'; if (fn) b.onclick = fn; if (key) b.dataset.key = key; return b; }
function shuffle(a){ for (var i = a.length - 1; i > 0; i--){ var j = Math.floor(Math.random() * (i + 1)); var t = a[i]; a[i] = a[j]; a[j] = t; } return a; }
function lsGet(k, d){ try { var v = localStorage.getItem(k); return v == null ? d : JSON.parse(v); } catch (e){ return d; } }
function lsSet(k, v){ try { localStorage.setItem(k, JSON.stringify(v)); } catch (e){} }
function clone(x){ return x == null ? x : JSON.parse(JSON.stringify(x)); }
function pct(x){ return x == null || isNaN(x) ? '—' : Math.round(x * 100) + '%'; }
function plural(n, one, few, many){ var a = n % 10, b = n % 100; return a === 1 && b !== 11 ? one : a >= 2 && a <= 4 && (b < 12 || b > 14) ? few : many; }
function nWord(n, key){ var f = L(key).split('|'); return n + ' ' + (f.length === 3 ? plural(n, f[0], f[1], f[2]) : f[0]); }
function today0(){ var d = new Date(); d.setHours(0, 0, 0, 0); return d.getTime(); }
function day0(ts){ var d = new Date(ts); d.setHours(0, 0, 0, 0); return d.getTime(); }
function dayKey(ts){ var d = new Date(ts); return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0') + '-' + String(d.getDate()).padStart(2, '0'); }
function fmtDay(ts){ return new Date(ts).toLocaleDateString(TRL === 'en' ? 'en-GB' : TRL, {day: 'numeric', month: 'long'}); }
function fmtShort(ts){ return new Date(ts).toLocaleDateString(TRL === 'en' ? 'en-GB' : TRL, {day: 'numeric', month: 'short'}); }
function bar(parts){ var b = el('div', 'bar'); parts.forEach(function(p){ if (p[1] > 0){ var i = el('i', p[0]); i.style.width = (p[1] * 100) + '%'; b.appendChild(i); } }); return b; }

/* ---------- Serbian script: Latin is stored, Cyrillic is a display option ---------- */
var CYR = {a: 'а', b: 'б', v: 'в', g: 'г', d: 'д', 'đ': 'ђ', e: 'е', 'ž': 'ж', z: 'з', i: 'и', j: 'ј', k: 'к', l: 'л', m: 'м', n: 'н', o: 'о', p: 'п', r: 'р', s: 'с', t: 'т', 'ć': 'ћ', u: 'у', f: 'ф', h: 'х', c: 'ц', 'č': 'ч', 'š': 'ш'};
var DIG = {lj: 'љ', nj: 'њ', 'dž': 'џ'};
var SPLIT = /^(?:in(?=jek)|kon(?=junk)|nad(?=ž)|pod(?=ž)|od(?=ž))/i;
function cyrWord(w){
  var lw = w.toLowerCase(), m = SPLIT.exec(lw), guard = m ? m[0].length : -1, out = '', i = 0;
  while (i < w.length){
    var pair = lw.substr(i, 2);
    if (DIG[pair] && i + 1 !== guard){ var c2 = DIG[pair]; out += w[i] !== lw[i] ? c2.toUpperCase() : c2; i += 2; continue; }
    var ch = w[i], c = CYR[ch.toLowerCase()];
    out += c ? (ch !== ch.toLowerCase() ? c.toUpperCase() : c) : ch; i++;
  }
  return out;
}
function toCyr(t){ return String(t).replace(/[A-Za-zČĆŽŠĐčćžšđ]+/g, cyrWord); }
function srx(t){ return ui.cyr ? toCyr(t) : t; }   // every Serbian text on screen goes through this
function fold(s){ return String(s).toLowerCase().replace(/[čć]/g, 'c').replace(/š/g, 's').replace(/ž/g, 'z').replace(/đ/g, 'dj'); }
function normSr(s){ return String(s).toLowerCase().normalize('NFD').replace(/(?![̌́])[̀-ͯ]/g, '').normalize('NFC').trim(); }

/* ---------- ui state ---------- */
var ui = {tab: lsGet('pl.tab', 'train'), theme: lsGet('pl.theme', ''), size: lsGet('pl.size', 20), cyr: !!lsGet('pl.cyr', false), q: '', filter: 'all', open: null};
var TABS = [['train', 'tabTrain'], ['vocab', 'tabVocab'], ['sit', 'tabSit'], ['texts', 'tabTexts'], ['stats', 'tabStats'], ['deck', 'tabDeck']];

/* ---------- progress state ---------- */
var T = {cards: {}, goal: PROF.goal || 15, retention: PROF.retention || 0.9, listening: PROF.listening !== false, typing: !!PROF.typing, hist: {}, updated: 0};
var LOG = [];      // [ts, key, grade, ms, elapsedDays, stabilityBefore] — every answer, the basis of statistics
var LOGNEW = [];   // answers not yet written to storage
var V = {};        // "I know" check: batchKey → {known:[ids], unknown:[ids], at}
var store = {mode: 'local', db: null, timer: null, dirtyT: false};

function setSync(msg){ var s = $('sync'); if (s) s.textContent = msg || ''; }
function post(path, body){ return fetch(path, {method: 'POST', headers: {'Content-Type': 'application/json'}, body: JSON.stringify(body)}).then(function(r){ if (!r.ok) throw new Error(r.status); return r.json(); }); }
function save(){
  store.dirtyT = true;
  lsSet('pl.fallback', {T: T, LOG: LOG.slice(-6000), V: V});
  if (store.mode === 'local') return;
  clearTimeout(store.timer); store.timer = setTimeout(flush, 900);
}
async function flush(){
  if (store.mode === 'local') return;
  var items = LOGNEW; LOGNEW = [];
  try {
    T.updated = NOW();
    if (store.mode === 'api'){
      if (store.dirtyT) await post('/api/trainer', T);
      if (items.length) await post('/api/log', {items: items});
    } else {
      if (store.dirtyT) await store.db.doc('trainer/state').set(clone(T));
      var byDay = {};
      items.forEach(function(x){ (byDay[dayKey(x[0])] = byDay[dayKey(x[0])] || []).push(x); });
      for (var k in byDay){
        var all = LOG.filter(function(x){ return dayKey(x[0]) === k; });
        await store.db.collection('log').doc(k).set({day: k, items: all});
      }
    }
    store.dirtyT = false; delete T.reset; setSync(L('saved'));
  } catch (e){ LOGNEW = items.concat(LOGNEW); setSync(L('savedLocal')); }
}
async function saveVocab(key, rec){
  V[key] = rec; lsSet('pl.fallback', {T: T, LOG: LOG.slice(-6000), V: V});
  try {
    if (store.mode === 'api') await post('/api/vocab', V);
    else if (store.mode === 'db') await store.db.collection('vocab').doc(key).set(rec);
    setSync(L('saved'));
  } catch (e){ setSync(L('savedLocal')); }
}
async function sendInbox(rec){
  if (store.mode === 'api') return post('/api/inbox', rec);
  if (store.mode === 'db') return store.db.collection('inbox').add(rec);
  throw new Error('offline');
}
async function download(filename, data, type){
  try { var dl = window.claude && window.claude.use ? await window.claude.use('downloads') : null; if (dl){ await dl.save({filename: filename, data: data}); return; } } catch (e){}
  var url = URL.createObjectURL(new Blob([data], {type: type || 'text/plain;charset=utf-8'}));
  var a = el('a'); a.href = url; a.download = filename; document.body.appendChild(a); a.click(); a.remove();
  setTimeout(function(){ URL.revokeObjectURL(url); }, 2000);
}

/* ---------- what is known ---------- */
function knownSet(){
  var k = {}, back = {};
  Object.keys(V).forEach(function(b){ var r = V[b]; if (!r || r.reset) return; (r.known || []).forEach(function(id){ k[id] = true; }); (r.back || []).forEach(function(id){ back[id] = true; }); });
  Object.keys(back).forEach(function(id){ delete k[id]; });   // "back to the trainer" wins over any earlier "I know"
  return k;
}
function checkedSet(){
  var k = {};
  Object.keys(V).forEach(function(b){ var r = V[b]; if (!r || r.reset) return; (r.known || []).concat(r.unknown || []).forEach(function(id){ k[id] = true; }); });
  return k;
}
var WORD_BY_ID = {}; DECK.words.forEach(function(w){ WORD_BY_ID[w.id] = w; });
var PHRASE_BY_ID = {}; DECK.phrases.forEach(function(p){ PHRASE_BY_ID[p.id] = p; });
var SIT_BY_ID = {}; SITS.forEach(function(s){ SIT_BY_ID[s.id] = s; });

/* ---------- header and tabs ---------- */
function renderHead(){
  $('title').textContent = D.title || 'Polako';
  var nav = $('tabs'); nav.innerHTML = '';
  TABS.forEach(function(t){
    var b = btn(null, L(t[1]), function(){ ui.tab = t[0]; ui.open = null; lsSet('pl.tab', ui.tab); if (play) { play = null; flush(); } render(); scrollTo(0, 0); });
    b.setAttribute('role', 'tab'); b.setAttribute('aria-selected', String(ui.tab === t[0])); nav.appendChild(b);
  });
  var sc = $('script'); sc.innerHTML = '';
  [['lat', 'Lat'], ['cyr', 'Ћир']].forEach(function(x){
    var b = btn(null, x[1], function(){ ui.cyr = x[0] === 'cyr'; lsSet('pl.cyr', ui.cyr); render(); });
    b.setAttribute('aria-pressed', String((x[0] === 'cyr') === ui.cyr)); b.title = L('scriptToggle'); sc.appendChild(b);
  });
  var sum = $('summary'); sum.innerHTML = '';
  if (DECK.words.length && typeof coverageNow === 'function'){
    var c = coverageNow(), due = dueCount();
    var line = el('div', 'wrap summary');
    line.appendChild(el('span', null, L('covSpoken') + ' ' + pct(c.spoken)));
    if (c.my != null) line.appendChild(el('span', null, L('covMy') + ' ' + pct(c.my)));
    line.appendChild(el('span', null, L('dueNow') + ': ' + due));
    var st = streak(); if (st) line.appendChild(el('span', null, '🔥 ' + nWord(st, 'days')));
    line.appendChild(el('span', 'sync', '')).id = 'sync';
    sum.appendChild(line); sum.hidden = false;
  } else sum.hidden = true;
}
function placeholder(main, text){ var c = el('div', 'card ph'); c.appendChild(el('div', 'ph-icon', '◌')); c.appendChild(el('p', null, text)); main.appendChild(c); }
function render(){
  renderHead();
  var main = $('main'); main.innerHTML = '';
  if (!DECK.words.length && ui.tab !== 'sit' && ui.tab !== 'texts'){ placeholder(main, L('phEmpty')); return; }
  if (ui.tab === 'vocab') renderVocab(main);
  else if (ui.tab === 'sit') renderSituations(main);
  else if (ui.tab === 'texts') renderTexts(main);
  else if (ui.tab === 'stats') renderStats(main);
  else if (ui.tab === 'deck') renderDeck(main);
  else renderTrainer(main);
}
function rerenderKeepScroll(){ var y = scrollY; render(); scrollTo(0, y); }
function applyTheme(){ if (ui.theme) document.documentElement.setAttribute('data-theme', ui.theme); else document.documentElement.removeAttribute('data-theme'); }
