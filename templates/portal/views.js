/* ---------- Vocabulary tab: the "I know it" check ----------
   First a quick check by frequency band: 10 words of a band, spread evenly by rank, WITHOUT the
   translation (it is a check, not a hint); knows ≥ 9 of 10 → the whole band is known except the
   unticked words. Then batches of 50 with the translation and an "I know" box. Only the words not
   marked go into the trainer; a known word can be sent back to the trainer from the Deck tab. */
var VB = 50, QN = 10, QPASS = 0.9;
function wBand(w){ if (w.band) return w.band; var z = w.zipf || 0; return z >= 5.3 ? 1 : z >= 4.5 ? 2 : z >= 3.5 ? 3 : 4; }
function qDone(b){ var r = V['q' + b]; return !!(r && !r.reset); }
function qSample(list){ if (list.length <= QN) return list.slice(); var out = []; for (var i = 0; i < QN; i++) out.push(list[Math.floor((i + 0.5) * list.length / QN)]); return out; }
function quickBands(words){
  var by = {}; words.forEach(function(w){ var b = wBand(w); (by[b] = by[b] || []).push(w); });
  return Object.keys(by).map(Number).sort().filter(function(b){ return by[b].length >= QN * 2; }).map(function(b){ return {b: b, words: by[b]}; });
}
function renderQuick(main, bands){
  var sec = el('div', 'card qcheck'); sec.appendChild(el('h3', null, L('qTitle'))); sec.appendChild(el('p', 'meta', L('qIntro')));
  var open = bands.filter(function(x){ return !qDone(x.b); })[0];
  bands.forEach(function(x){
    var r = V['q' + x.b], row = el('div', 'qrow');
    row.appendChild(el('b', null, L('band') + ' ' + x.b + ' · ' + L('band' + x.b)));
    row.appendChild(el('span', 'meta', nWord(x.words.length, 'wordsN3')));
    if (qDone(x.b)){
      row.appendChild(el('span', r.pass ? 'tag ok' : 'tag', r.skipped ? L('qSkipped') : r.pass ? L('qPass') : L('qFail')));
      row.appendChild(btn('linkbtn', L('qRedo'), async function(){ await saveVocab('q' + x.b, {reset: true, known: [], unknown: [], at: NOW()}); render(); }));
    }
    sec.appendChild(row);
  });
  if (open){
    var marks = {}, box = el('div', 'qbox');
    qSample(open.words).forEach(function(w){
      var r = el('label', 'vrow'), c = el('input'); c.type = 'checkbox'; marks[w.id] = c;
      r.appendChild(c); r.appendChild(el('span', 'sr', srx(w.sr))); r.appendChild(spk(w.sr, 'sr')); box.appendChild(r);
    });
    sec.appendChild(el('p', 'meta', L('band') + ' ' + open.b + ' · ' + L('band' + open.b) + ' — ' + L('qHint')));
    sec.appendChild(box);
    var acts = el('div', 'acts');
    acts.appendChild(btn('btn primary', L('qCheck'), async function(){
      var ids = Object.keys(marks), kn = ids.filter(function(id){ return marks[id].checked; });
      var pass = kn.length >= Math.ceil(ids.length * QPASS);
      var known = pass ? open.words.map(function(w){ return w.id; }).filter(function(id){ return !marks[id] || marks[id].checked; }) : kn;
      var unknown = ids.filter(function(id){ return !marks[id].checked; });
      await saveVocab('q' + open.b, {band: open.b, pass: pass, known: known, unknown: unknown, at: NOW()});
      ITEMS_CACHE = null; render();
    }));
    acts.appendChild(btn('btn', L('qSkip'), async function(){ for (var i = 0; i < bands.length; i++) if (!qDone(bands[i].b)) await saveVocab('q' + bands[i].b, {band: bands[i].b, pass: false, skipped: true, known: [], unknown: [], at: NOW()}); render(); }));
    sec.appendChild(acts);
  }
  main.appendChild(sec);
}
function renderVocab(main){
  var all = DECK.words.slice().sort(function(a, b){ return a.rank - b.rank; }), bands = quickBands(all);
  main.appendChild(el('h2', 'tr-h', L('vocabTitle')));
  main.appendChild(el('p', 'meta', L('vocabIntro')));
  if (bands.some(function(x){ return !qDone(x.b); })){ renderQuick(main, bands); return; }
  var decided = {}; Object.keys(V).forEach(function(k){ if (k.charAt(0) === 'q' && !V[k].reset) (V[k].known || []).concat(V[k].unknown || []).forEach(function(id){ decided[id] = true; }); });
  var words = all.filter(function(w){ return !decided[w.id]; }), batches = [];
  for (var i = 0; i < words.length; i += VB) batches.push(words.slice(i, i + VB));
  var known = knownSet(), checked = checkedSet(), kn = Object.keys(known).length, ch = Object.keys(checked).length, N = all.length;
  if (bands.length) renderQuick(main, bands);
  var line = el('div', 'progress-line'); line.appendChild(el('span', null, L('checked') + ' ' + ch + ' / ' + N)); line.appendChild(el('span', null, L('know') + ' ' + kn + ' · ' + L('toLearn') + ' ' + (ch - kn)));
  main.appendChild(line); main.appendChild(bar([['d', N ? kn / N : 0], ['l', N ? (ch - kn) / N : 0]]));
  if (!batches.length){ main.appendChild(el('p', 'meta', L('vocabAllChecked'))); return; }
  var cur = batches.findIndex(function(_, i){ return !V['b' + (i + 1)]; }); if (cur < 0) cur = 0; if (ui.vb != null && ui.vb < batches.length) cur = ui.vb;
  var nav = el('div', 'toolbar');
  batches.forEach(function(_, i){ var c = btn('chip', L('batch') + ' ' + (i + 1) + (V['b' + (i + 1)] ? ' ✓' : ''), function(){ ui.vb = i; render(); }); c.setAttribute('aria-pressed', String(i === cur)); nav.appendChild(c); });
  main.appendChild(nav);
  var box = el('div', 'card'), marks = {};
  batches[cur].forEach(function(w){
    var r = el('label', 'vrow'), c = el('input'); c.type = 'checkbox'; c.checked = !!known[w.id]; marks[w.id] = c;
    r.appendChild(c); r.appendChild(el('span', 'sr', srx(w.sr))); r.appendChild(spk(w.sr, 'sr')); r.appendChild(el('span', 'tr', w.tr)); box.appendChild(r);
  });
  main.appendChild(box);
  var acts = el('div', 'acts');
  acts.appendChild(btn('btn primary', L('saveBatch'), async function(){
    var rec = {known: [], unknown: [], at: NOW()};
    Object.keys(marks).forEach(function(id){ (marks[id].checked ? rec.known : rec.unknown).push(id); });
    ui.vb = Math.min(cur + 1, batches.length - 1);
    await saveVocab('b' + (cur + 1), rec); ITEMS_CACHE = null; render(); scrollTo(0, 0);
  }));
  main.appendChild(acts);
}

/* ---------- Situations tab ---------- */
function sitItems(sid){
  return allItems().filter(function(it){
    if (it.kind === 'dialog') return it.sit === sid;
    var x = it.kind === 'word' || it.kind === 'phrase' ? it.it : it.kind === 'cloze' ? it.w : null;
    return x && (x.sit || []).indexOf(sid) >= 0;
  });
}
function renderSituations(main){
  main.appendChild(el('h2', 'tr-h', L('sitTitle')));
  main.appendChild(el('p', 'meta', L('sitIntro')));
  if (!SITS.length){ placeholder(main, L('phSit')); return; }
  var grid = el('div', 'sit-grid');
  SITS.forEach(function(s){
    var items = sitItems(s.id), st = stats(items), p = 0; items.forEach(function(it){ p += itemPct(it); }); p = items.length ? p / items.length : 0;
    var c = el('div', 'card sit' + (ui.open === s.id ? ' open' : ''));
    var h = el('div', 'sit-h'); h.appendChild(el('h3', null, s.title)); if (s.title_sr) h.appendChild(el('span', 'meta', srx(s.title_sr)));
    h.appendChild(el('span', 'tag pri' + s.pri, L('pri' + s.pri))); c.appendChild(h);
    c.appendChild(el('div', 'sit-ready', L('ready') + ' ' + Math.round(p * 100) + '%'));
    c.appendChild(bar(mix(items))); c.appendChild(legend(st));
    var acts = el('div', 'acts');
    if (items.length) acts.appendChild(btn('btn primary', L('trainSit') + ' (' + items.length + ')', function(){ ui.tab = 'train'; lsSet('pl.tab', 'train'); startRound({key: 'sit-' + s.id, items: items, title: s.title}); }));
    acts.appendChild(btn('btn', ui.open === s.id ? L('hide') : L('showDialogs'), function(){ ui.open = ui.open === s.id ? null : s.id; rerenderKeepScroll(); }));
    c.appendChild(acts);
    if (ui.open === s.id){
      (s.dialogs || []).forEach(function(d){
        var dl = el('div', 'dialog'); if (d.title) dl.appendChild(el('h4', null, d.title));
        d.lines.forEach(function(ln){ var r = el('div', 'dl-line ' + ln.who), b = el('b', null, srx(ln.sr)); b.appendChild(spk(ln.sr, 'sr')); r.appendChild(b);
          var t = el('details', 'dl-tr'); t.appendChild(el('summary', null, L('translation'))); t.appendChild(el('div', null, ln.tr)); r.appendChild(t); dl.appendChild(r); });
        if (canSpeak('sr')) dl.appendChild(btn('linkbtn', '▶ ' + L('playDialog'), function(){ var i = 0; (function nx(){ if (i < d.lines.length) speak(d.lines[i++].sr, 'sr', function(){ setTimeout(nx, 500); }); })(); }));
        c.appendChild(dl);
      });
      var ph = items.filter(function(it){ return it.kind === 'phrase'; });
      if (ph.length){ var ul = el('ul', 'sit-ph'); ph.forEach(function(it){ var li = el('li'), b = el('b', null, srx(it.it.sr)); b.appendChild(spk(it.it.sr, 'sr')); li.appendChild(b); li.appendChild(el('span', null, ' — ' + it.it.tr)); ul.appendChild(li); }); c.appendChild(ul); }
    }
    grid.appendChild(c);
  });
  main.appendChild(grid);
}

/* ---------- My texts tab: what the person actually receives, with what they know highlighted ---------- */
var FORM2ID = D.forms || {};
function tokenState(id){
  if (!id) return 'out';
  if (understood()[id]) return 'known';
  var it = allItems().filter(function(x){ return x.id === id; })[0];
  return it && seen(it) ? 'learning' : 'deck';
}
function drawTokens(toks, host){
  var und = understood(), states = {known: 0, learning: 0, deck: 0, out: 0};
  toks.forEach(function(t){
    if (typeof t === 'string'){ host.appendChild(document.createTextNode(srx(t))); return; }
    var id = t[1], st = id ? (und[id] ? 'known' : tokenState(id)) : (t[2] ? 'out' : 'plain');
    if (st !== 'plain') states[st]++;
    var s = el('span', 'tok ' + st, srx(t[0]));
    if (id && WORD_BY_ID[id]){ s.title = WORD_BY_ID[id].sr + ' — ' + WORD_BY_ID[id].tr; s.tabIndex = 0; s.onclick = function(){ popWord(WORD_BY_ID[id], s); }; }
    host.appendChild(s);
  });
  return states;
}
function popWord(w, anchor){
  var pop = $('pop'); pop.innerHTML = '';
  var h = el('h4', null, srx(w.sr)); h.appendChild(spk(w.sr, 'sr')); pop.appendChild(h);
  pop.appendChild(el('div', null, w.tr)); var tg = wordTag(w); if (tg) pop.appendChild(el('div', 'hint', tg));
  var fl = formsLine(w); if (fl) pop.appendChild(el('div', 'hint', fl)); if (w.note) pop.appendChild(el('div', 'note', w.note));
  var r = anchor.getBoundingClientRect(); pop.hidden = false;
  pop.style.left = Math.max(8, Math.min(r.left, innerWidth - pop.offsetWidth - 8)) + 'px';
  pop.style.top = (r.bottom + 6 + pop.offsetHeight > innerHeight ? r.top - pop.offsetHeight - 6 : r.bottom + 6) + 'px';
}
document.addEventListener('click', function(e){ var pop = $('pop'); if (pop && !pop.hidden && !pop.contains(e.target) && !(e.target.classList && e.target.classList.contains('tok'))) pop.hidden = true; });
function renderTexts(main){
  main.appendChild(el('h2', 'tr-h', L('textsTitle')));
  main.appendChild(el('p', 'meta', L('textsIntro')));
  var key = el('div', 'tok-key'); [['known', 'tokKnown'], ['learning', 'tokLearning'], ['deck', 'tokDeck'], ['out', 'tokOut']].forEach(function(x){ key.appendChild(el('span', 'tok ' + x[0], L(x[1]))); }); main.appendChild(key);
  TEXTS.forEach(function(t){
    var c = el('div', 'card text-card'), h = el('div', 'sit-h'); h.appendChild(el('h3', null, t.title)); if (t.from) h.appendChild(el('span', 'meta', t.from)); c.appendChild(h);
    var body = el('div', 'text-body'), st = drawTokens(t.tokens, body), tot = st.known + st.learning + st.deck + st.out;
    var row = el('div', 'meta'); row.textContent = L('youKnow') + ' ' + pct(tot ? st.known / tot : 0) + ' · ' + L('tokLearning') + ' ' + st.learning + ' · ' + L('tokDeck') + ' ' + st.deck + ' · ' + L('tokOut') + ' ' + st.out;
    c.appendChild(row); c.appendChild(bar([['d', tot ? st.known / tot : 0], ['l', tot ? st.learning / tot : 0], ['c', tot ? st.deck / tot : 0]]));
    c.appendChild(body); main.appendChild(c);
  });
  // paste a text: checked against the deck right here; "send to Claude" puts it in the inbox for a proper analysis
  var c2 = el('div', 'card paste'); c2.appendChild(el('h3', null, L('pasteTitle'))); c2.appendChild(el('p', 'meta', L('pasteIntro')));
  var ti = el('input'); ti.type = 'text'; ti.placeholder = L('pasteName'); ti.className = 'inp';
  var ta = el('textarea'); ta.rows = 6; ta.placeholder = L('pasteHere'); ta.className = 'inp';
  var out = el('div', 'text-body'), msg = el('p', 'meta');
  c2.appendChild(ti); c2.appendChild(ta);
  var acts = el('div', 'acts');
  acts.appendChild(btn('btn', L('pasteCheck'), function(){
    out.innerHTML = ''; var toks = [], re = /([A-Za-zČĆŽŠĐčćžšđА-Яа-яЂђЈјЉљЊњЋћЏџ]+)|([^A-Za-zČĆŽŠĐčćžšđА-Яа-яЂђЈјЉљЊњЋћЏџ]+)/g, m, txt = latinOf(ta.value);
    while ((m = re.exec(txt))){ if (m[1]){ var f = normSr(m[1]), id = FORM2ID[f] || FORM2ID[fold(f)] || null; toks.push([m[1], id, 1]); } else toks.push(m[2]); }
    var st = drawTokens(toks, out), tot = st.known + st.learning + st.deck + st.out;
    msg.textContent = L('youKnow') + ' ' + pct(tot ? st.known / tot : 0) + ' · ' + L('tokOut') + ': ' + st.out;
  }));
  acts.appendChild(btn('btn primary', L('pasteSend'), async function(){
    if (!ta.value.trim()) return;
    try { await sendInbox({type: 'text', title: ti.value.trim() || L('pasteDefault'), text: ta.value, at: NOW()}); msg.textContent = L('pasteSent'); }
    catch (e){ msg.textContent = L('pasteOffline'); }
  }));
  c2.appendChild(acts); c2.appendChild(msg); c2.appendChild(out); main.appendChild(c2);
}
var LAT = {'а': 'a', 'б': 'b', 'в': 'v', 'г': 'g', 'д': 'd', 'ђ': 'đ', 'е': 'e', 'ж': 'ž', 'з': 'z', 'и': 'i', 'ј': 'j', 'к': 'k', 'л': 'l', 'љ': 'lj', 'м': 'm', 'н': 'n', 'њ': 'nj', 'о': 'o', 'п': 'p', 'р': 'r', 'с': 's', 'т': 't', 'ћ': 'ć', 'у': 'u', 'ф': 'f', 'х': 'h', 'ц': 'c', 'ч': 'č', 'џ': 'dž', 'ш': 'š'};
function latinOf(t){ return String(t).replace(/[а-яђјљњћџ]/gi, function(ch){ var l = LAT[ch.toLowerCase()]; if (!l) return ch; return ch === ch.toLowerCase() ? l : l.charAt(0).toUpperCase() + l.slice(1); }); }

/* ---------- Deck tab: every card, searchable ---------- */
function renderDeck(main){
  main.appendChild(el('h2', 'tr-h', L('deckTitle')));
  var bar1 = el('div', 'toolbar'), q = el('input'); q.type = 'search'; q.placeholder = L('search'); q.value = ui.q || ''; q.className = 'inp';
  q.oninput = function(){ ui.q = q.value; clearTimeout(ui.qt); ui.qt = setTimeout(function(){ var y = scrollY; render(); scrollTo(0, y); var n = document.querySelector('.toolbar input[type=search]'); if (n){ n.focus(); n.setSelectionRange(n.value.length, n.value.length); } }, 250); };
  bar1.appendChild(q);
  [['all', 'fAll'], ['learning', 'learning'], ['firm', 'firm'], ['learned', 'learned'], ['fresh', 'notStarted'], ['known', 'fKnown'], ['leech', 'fLeech']].forEach(function(x){
    var c = btn('chip', L(x[1]), function(){ ui.filter = x[0]; render(); }); c.setAttribute('aria-pressed', String(ui.filter === x[0])); bar1.appendChild(c); });
  main.appendChild(bar1);
  var k = knownSet(), qq = fold(normSr(ui.q || '')), rows = [];
  itemsOfKind('word').concat(itemsOfKind('phrase')).forEach(function(it){
    var x = it.it, st = k[it.id] ? 'known' : isLeech(it) ? 'leech' : itemState(it);
    if (ui.filter !== 'all' && ui.filter !== st) return;
    if (qq && fold(normSr(x.sr)).indexOf(qq) < 0 && String(x.tr).toLowerCase().indexOf((ui.q || '').toLowerCase()) < 0) return;
    rows.push({it: it, st: st});
  });
  main.appendChild(el('p', 'meta', nWord(rows.length, 'cards')));
  var tb = el('table', 'deck-t'), th = el('tr'); ['#', L('colSr'), L('colTr'), L('colState'), L('colNext'), ''].forEach(function(h){ th.appendChild(el('th', null, h)); }); tb.appendChild(th);
  rows.slice(0, 400).forEach(function(r){
    var x = r.it.it, tr = el('tr', 'st-' + r.st), nxt = null;
    sidesOf(r.it).forEach(function(sd){ var c = cardOf(r.it, sd); if (c && (nxt == null || c.due < nxt)) nxt = c.due; });
    tr.appendChild(el('td', 'num', x.rank || '')); var s = el('td', 'sr'); s.appendChild(document.createTextNode(srx(x.sr))); s.appendChild(spk(x.sr, 'sr')); tr.appendChild(s);
    tr.appendChild(el('td', null, x.tr)); tr.appendChild(el('td', null, L(r.st === 'fresh' ? 'notStarted' : r.st === 'known' ? 'fKnown' : r.st === 'leech' ? 'fLeech' : r.st)));
    tr.appendChild(el('td', 'num', nxt ? (nxt <= NOW() ? L('now') : fmtShort(nxt)) : ''));
    var a = el('td');
    if (r.it.kind === 'word'){
      if (r.st === 'known') a.appendChild(btn('linkbtn', L('backToTrainer'), async function(){ var rec = V.manual || {known: [], unknown: [], back: [], at: NOW()}; rec.back = (rec.back || []).concat([x.id]); rec.known = (rec.known || []).filter(function(i){ return i !== x.id; }); await saveVocab('manual', rec); ITEMS_CACHE = null; rerenderKeepScroll(); }));
      else a.appendChild(btn('linkbtn', L('iKnow'), async function(){ var rec = V.manual || {known: [], unknown: [], back: [], at: NOW()}; rec.known = (rec.known || []).concat([x.id]); rec.back = (rec.back || []).filter(function(i){ return i !== x.id; }); await saveVocab('manual', rec); ITEMS_CACHE = null; rerenderKeepScroll(); }));
    }
    tr.appendChild(a); tb.appendChild(tr);
  });
  var wrap = el('div', 'table-wrap'); wrap.appendChild(tb); main.appendChild(wrap);
  if (rows.length > 400) main.appendChild(el('p', 'meta', L('first400')));
  var exp = el('div', 'acts');
  exp.appendChild(btn('btn', L('exportCsv'), function(){
    var lines = [['rank', 'sr', 'tr', 'pos', 'state'].join(',')];
    rows.forEach(function(r){ var x = r.it.it; lines.push([x.rank || '', x.sr, x.tr, x.pos || '', r.st].map(function(v){ v = String(v); return /[",\n]/.test(v) ? '"' + v.replace(/"/g, '""') + '"' : v; }).join(',')); });
    download('polako-deck.csv', lines.join('\n'), 'text/csv;charset=utf-8');
  }));
  main.appendChild(exp);
}
