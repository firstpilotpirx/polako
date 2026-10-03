/* ---------- Trainer ----------
   Learning items: words, phrases, cloze (a form in a sentence), aspect pairs (kupiti / kupovati),
   dialog replies (they say → I answer). Each item is asked from several SIDES, each side with its own
   FSRS card (key "<id>|<side>"):
     word    stage 1 (recognition): pick-tr (sr → choose the meaning of 6), listen (hear → choose the
             meaning; when a Serbian/Croatian/Bosnian voice exists), pick-sr (meaning → choose sr of 6)
             stage 2 (recall, from the next day once stage 1 is answered): say-tr, say-sr, type (if on)
     phrase  listen-ph (or read-ph without a voice) → then say-ph (meaning → say it, self-grade)
     cloze   choose the right form · pair: name both aspects · dialog: choose my reply
   A choice answer is graded by itself: right and fast → Good, right but slow → Hard, wrong → Again.
   Recall sides are self-graded with four buttons (Again · Hard · Good · Easy), each showing its next
   interval. A wrong answer returns the side to the end of the same round. A side forgotten 6+ times
   is a "leech": it leaves the rounds and waits on the statistics tab for a mnemonic. */
var LEARNED_S = 21, FIRM_S = 7, KNOWN_S = 7, LEECH = 6, TRB = 50;
var play = null;
function listenOn(){ return T.listening && canSpeak('sr'); }
var ITEMS_CACHE = null;
function allItems(){
  if (ITEMS_CACHE) return ITEMS_CACHE;
  var out = [], ids = {};
  DECK.words.forEach(function(w){ out.push({kind: 'word', id: w.id, it: w, rank: w.rank}); ids[w.id] = w; });
  DECK.phrases.forEach(function(p){ out.push({kind: 'phrase', id: p.id, it: p, rank: (p.rank || 1) * 2 + 20, words: p.words || []}); });
  DECK.cloze.forEach(function(c){ var w = ids[c.word]; if (w) out.push({kind: 'cloze', id: c.id, it: c, w: w, rank: w.rank + 0.5, words: [w.id]}); });
  var done = {};
  DECK.words.forEach(function(w){ var o = w.pair && ids[w.pair]; if (!o) return;
    var a = w.asp === 'pf' ? w : o, b = a === w ? o : w, id = 'v:' + a.id.slice(2) + '--' + b.id.slice(2);
    if (done[id]) return; done[id] = 1; out.push({kind: 'pair', id: id, a: a, b: b, rank: Math.max(a.rank, b.rank) + 0.5, words: [a.id, b.id]}); });
  SITS.forEach(function(s){ (s.dialogs || []).forEach(function(d){ (d.lines || []).forEach(function(ln, i){
    if (ln.who === 'me' && i > 0 && d.lines[i - 1].who === 'they')
      out.push({kind: 'dialog', id: 'd:' + d.id + ':' + i, they: d.lines[i - 1], me: ln, sit: s.id, rank: 30 + (s.pri || 2) * 20 + i}); }); }); });
  ITEMS_CACHE = out; return out;
}
function itemsOfKind(k){ return allItems().filter(function(x){ return x.kind === k; }); }
function key(item, side){ return item.id + '|' + side; }
function cardOf(item, side){ return T.cards[key(item, side)]; }
function stage1(item){
  if (item.kind === 'word') return listenOn() ? ['pick-tr', 'listen', 'pick-sr'] : ['pick-tr', 'pick-sr'];
  if (item.kind === 'phrase') return [listenOn() ? 'listen-ph' : 'read-ph'];
  return [item.kind === 'cloze' ? 'cloze' : item.kind === 'pair' ? 'aspect' : 'reply'];
}
function stage2(item){
  if (item.kind === 'word') return T.typing ? ['say-tr', 'say-sr', 'type'] : ['say-tr', 'say-sr'];
  if (item.kind === 'phrase') return T.typing ? ['say-ph', 'type-ph'] : ['say-ph'];
  return [];
}
function unlocked(item){
  var t0 = today0();
  return stage1(item).every(function(sd){ var c = cardOf(item, sd); return c && c.s >= 1 && c.f < t0; });
}
function sidesOf(item){ var s1 = stage1(item); return unlocked(item) ? s1.concat(stage2(item)) : s1; }
function seen(item){ return stage1(item).concat(stage2(item)).some(function(sd){ return !!cardOf(item, sd); }); }
function sideDue(item, sd){ var c = cardOf(item, sd); return !c || c.due <= NOW(); }
function isLeech(item){ return sidesOf(item).some(function(sd){ var c = cardOf(item, sd); return c && c.lapses >= LEECH; }); }
function minS(item){ var m = Infinity; sidesOf(item).forEach(function(sd){ var c = cardOf(item, sd); m = Math.min(m, c ? c.s : 0); }); return m === Infinity ? 0 : m; }
function itemState(item){ if (!seen(item)) return 'fresh'; var m = minS(item); return m >= LEARNED_S ? 'learned' : m >= FIRM_S ? 'firm' : 'learning'; }
function itemDue(item){ return seen(item) && sidesOf(item).some(function(sd){ return sideDue(item, sd); }); }
function itemPct(item){ var ss = stage1(item).concat(stage2(item)), sum = 0; ss.forEach(function(sd){ var c = cardOf(item, sd); if (c) sum += Math.min(1, c.s / LEARNED_S); }); return sum / ss.length; }
function firstSeen(item){ var m = null; stage1(item).forEach(function(sd){ var c = cardOf(item, sd); if (c && c.f && (m == null || c.f < m)) m = c.f; }); return m; }
function learnWords(){ var k = knownSet(); return DECK.words.filter(function(w){ return !k[w.id]; }).sort(function(a, b){ return a.rank - b.rank; }); }
function newWordsByDay(){ var m = {}; itemsOfKind('word').forEach(function(it){ var f = firstSeen(it); if (f == null) return; var d = day0(f); m[d] = (m[d] || 0) + 1; }); return m; }
function newToday(kind){ var t0 = today0(), n = 0; itemsOfKind(kind).forEach(function(it){ var f = firstSeen(it); if (f != null && f >= t0) n++; }); return n; }
function dueCount(){ var k = knownSet(), n = 0; allItems().forEach(function(it){ if (it.kind === 'word' && k[it.id]) return; if (!isLeech(it) && itemDue(it)) n++; }); return n; }
function stats(items){
  var s = {learned: 0, firm: 0, learning: 0, fresh: 0, total: 0, due: 0};
  items.forEach(function(it){ s.total++; var st = itemState(it); s[st]++; if (itemDue(it)) s.due++; });
  return s;
}
function mix(items){ var s = stats(items), n = s.total || 1; return [['d', s.learned / n], ['c', s.firm / n], ['l', s.learning / n]]; }
function legend(s){
  var lg = el('div', 'tr-legend');
  [['--done', 'learned', s.learned], ['--consolidating', 'firm', s.firm], ['--learning', 'learning', s.learning], ['--notstarted', 'notStarted', s.fresh]].forEach(function(x){
    var w = el('span'), i = el('em'); i.style.background = 'var(' + x[0] + ')'; w.appendChild(i); w.appendChild(document.createTextNode(L(x[1]) + ' ')); w.appendChild(el('b', null, x[2])); lg.appendChild(w);
  });
  return lg;
}

/* ---------- coverage, streak, history ---------- */
function understood(){
  var k = knownSet();
  itemsOfKind('word').forEach(function(it){
    var best = 0; ['say-tr', 'pick-tr', 'listen'].forEach(function(sd){ var c = cardOf(it, sd); if (c && c.s > best) best = c.s; });
    if (best >= KNOWN_S) k[it.id] = true;
  });
  return k;
}
function coverageNow(){
  var k = understood(), sp = 0, my = 0;
  Object.keys(k).forEach(function(id){ sp += (COV.sp || {})[id] || 0; my += (COV.my || {})[id] || 0; });
  return {spoken: sp, my: COV.myTotal ? my / COV.myTotal : null, known: Object.keys(k).length};
}
function activeDays(){ var d = {}; LOG.forEach(function(x){ d[day0(x[0])] = (d[day0(x[0])] || 0) + 1; }); return d; }
function streak(){
  var by = activeDays(), n = 0, d = today0();
  if (!by[d]) d -= DAY;
  while (by[d]){ n++; d -= DAY; }
  return n;
}
function snapshot(){
  if (!DECK.words.length) return;
  var c = coverageNow(), s = stats(itemsOfKind('word')), k = dayKey(NOW());
  var rec = {sp: Math.round(c.spoken * 1000) / 1000, my: c.my == null ? null : Math.round(c.my * 1000) / 1000, kn: c.known, lr: s.learned};
  var old = T.hist[k];
  if (!old || old.sp !== rec.sp || old.my !== rec.my || old.kn !== rec.kn || old.lr !== rec.lr){ T.hist[k] = rec; save(); }
}

/* ---------- forecast: FSRS says how many days each side needs to reach 21 days of stability ---------- */
function againRate(){
  var from = NOW() - 30 * DAY, n = 0, bad = 0;
  LOG.forEach(function(x){ if (x[0] >= from && x[4] >= 1){ n++; if (x[2] === 1) bad++; } });
  return n >= 30 ? bad / n : null;
}
function itemDaysLeft(item){
  var mx = 0, now = NOW();
  stage1(item).concat(stage2(item)).forEach(function(sd){
    var c = cardOf(item, sd), d = c && c.s >= LEARNED_S ? 0 : FSRS.daysToStable(c, now, T.retention, LEARNED_S) + (c || stage1(item).indexOf(sd) >= 0 ? 0 : 1);
    if (d > mx) mx = d;
  });
  return mx;
}
function etaOf(items, pace, freshBefore){
  var fresh = 0, end = 0;
  items.forEach(function(it){
    if (!seen(it)){ var start = (freshBefore + fresh) / pace; fresh++; end = Math.max(end, start + itemDaysLeft(it)); }
    else end = Math.max(end, itemDaysLeft(it));
  });
  if (fresh && !(pace > 0)) return null;
  return {fresh: fresh, start: fresh ? Math.ceil(freshBefore / pace) : 0, learn: Math.ceil(end)};
}
function etaText(e, realistic){
  if (!e) return L('etaUnknown');
  if (!e.learn) return L('allLearned');
  var r = againRate(), parts = [];
  if (e.fresh && e.start) parts.push(L('startIn') + ' ' + nWord(e.start, 'days'));
  parts.push(L('learnBy') + ' ' + fmtDay(NOW() + e.learn * DAY));
  if (realistic && r != null && r > 0.02) parts.push(L('realistic') + ' ' + fmtDay(NOW() + Math.ceil(e.learn * (1 + 2 * r)) * DAY));
  return parts.join(' · ');
}

/* ---------- decks ---------- */
function wordDecks(){
  var learn = learnWords().map(function(w){ return allItems().filter(function(x){ return x.id === w.id; })[0]; }).filter(Boolean);
  var n = Math.ceil(learn.length / TRB), out = [];
  for (var i = 0; i < n; i++){
    var items = learn.slice(i * TRB, (i + 1) * TRB);
    out.push({key: 'w' + (i + 1), grp: L('byImportance'), items: items, title: L('wordsN') + ' ' + (i * TRB + 1) + '–' + (i * TRB + items.length), desc: L('group') + ' ' + (i + 1) + ' ' + L('of') + ' ' + n, words: true});
  }
  return out;
}
function decks(){
  var out = wordDecks();
  var ph = itemsOfKind('phrase'); if (ph.length) out.push({key: 'phrases', grp: L('other'), items: ph, title: L('phrases'), desc: L('phrasesDesc')});
  var gr = itemsOfKind('cloze').concat(itemsOfKind('pair')); if (gr.length) out.push({key: 'grammar', grp: L('other'), items: gr, title: L('grammar'), desc: L('grammarDesc')});
  var dl = itemsOfKind('dialog'); if (dl.length) out.push({key: 'dialogs', grp: L('other'), items: dl, title: L('dialogs'), desc: L('dialogsDesc')});
  return out;
}
function interleave(entries){
  // entries: [{it, sides:[…]}] → random order, an item never twice in a row, its sides in order (recognition before recall)
  var per = entries.map(function(e){ return {it: e.it, fs: e.sides.slice()}; }), q = [], last = null;
  while (per.some(function(x){ return x.fs.length; })){
    var cand = per.filter(function(x){ return x.fs.length && x.it !== last; });
    if (!cand.length) cand = per.filter(function(x){ return x.fs.length; });
    var pool = []; cand.forEach(function(x){ for (var r = 0; r < x.fs.length; r++) pool.push(x); });
    var pick = pool[Math.floor(Math.random() * pool.length)];
    q.push({it: pick.it, f: pick.fs.shift()}); last = pick.it;
  }
  return q;
}
function queueFor(items, n, opts){
  opts = opts || {};
  var k = knownSet(), byRank = function(a, b){ return a.rank - b.rank; };
  var pool = items.filter(function(it){ return !(it.kind === 'word' && k[it.id]) && !isLeech(it); });
  var rev = pool.filter(function(it){ return seen(it) && itemDue(it); }).sort(byRank);
  var fresh = pool.filter(function(it){ return !seen(it); }).sort(byRank);
  if (opts.smart && !opts.extra){
    var wLeft = Math.max(0, T.goal - newToday('word')), pLeft = Math.max(0, Math.max(3, Math.round(T.goal / 4)) - newToday('phrase')), oLeft = 5;
    var startedW = {}; itemsOfKind('word').forEach(function(it){ if (seen(it)) startedW[it.id] = true; });
    fresh = fresh.filter(function(it){
      if (it.kind === 'word') return wLeft-- > 0;
      if (it.kind === 'phrase') return pLeft-- > 0;
      if (it.kind === 'dialog') return oLeft-- > 0;
      return (it.words || []).every(function(id){ return startedW[id]; }) && oLeft-- > 0;   // cloze and pairs follow their words
    });
  }
  var out = [], count = 0;
  function take(list){ var e = [];
    for (var i = 0; i < list.length && count < n; i++){ var sides = sidesOf(list[i]).filter(function(sd){ return sideDue(list[i], sd); }); if (!sides.length) continue;
      if (opts.only) sides = sides.filter(function(sd){ return opts.only.indexOf(sd) >= 0; }); if (!sides.length) continue;
      sides = sides.slice(0, Math.max(1, n - count)); e.push({it: list[i], sides: sides}); count += sides.length; }
    return e; }
  out = interleave(take(rev)).concat(interleave(take(fresh)));
  return out;
}
function smartDeck(){ return {key: 'smart', items: allItems(), title: L('smart'), smart: true}; }
function startRound(dk, opts){
  opts = opts || {};
  var q = queueFor(dk.items, ui.size, {smart: dk.smart, extra: dk.extra, only: opts.only});
  if (!q.length && !dk.smart){   // nothing due: a short practice round of what is already started
    var started = shuffle(dk.items.filter(seen)).slice(0, 6);
    q = interleave(started.map(function(it){ return {it: it, sides: stage1(it)}; }));
    if (opts.only) q = q.filter(function(e){ return opts.only.indexOf(e.f) >= 0; });
  }
  if (!q.length) return;
  play = {deck: dk, queue: q, idx: 0, right: 0, wrong: 0, shown: false, picked: null, t0: NOW(), opts: opts, startedAt: NOW()};
  render(); scrollTo(0, 0);
}

/* ---------- grading ---------- */
var FAST_MS = {word: 6000, phrase: 10000, cloze: 9000, pair: 9000, dialog: 10000};
function gradeChoice(ok, ms, kind){ return !ok ? 1 : ms <= (FAST_MS[kind] || 8000) ? 3 : 2; }
function grade(g){
  var e = play.queue[play.idx], k = key(e.it, e.f), ms = Math.min(120000, NOW() - play.t0);
  var res = FSRS.review(T.cards[k], g, NOW(), T.retention);
  res.card.g = g; T.cards[k] = res.card;
  var entry = [NOW(), k, g, ms, res.elapsed, res.sBefore];
  LOG.push(entry); LOGNEW.push(entry);
  if (g === 1){ play.wrong++; play.queue.push({it: e.it, f: e.f, again: true}); } else play.right++;
  save();
  play.idx++; play.shown = false; play.picked = null; play.pickedOk = null; play.ch = null; play.typed = null; play.typedNote = null; play.t0 = NOW(); render();
}
function previewIvl(e, g){
  var r = FSRS.review(T.cards[key(e.it, e.f)], g, NOW(), T.retention).card, m = (r.due - NOW()) / 60000;
  return m < 60 ? Math.round(m) + ' ' + L('min') : m < 1440 ? Math.round(m / 60) + ' ' + L('hrs') : Math.round(m / 1440) + ' ' + L('dShort');
}

/* ---------- card content ---------- */
var POS_KEY = {noun: 'posNoun', verb: 'posVerb', adj: 'posAdj', adv: 'posAdv', pron: 'posPron', prep: 'posPrep', conj: 'posConj', part: 'posPart', num: 'posNum', interj: 'posInterj', phrase: 'posPhrase'};
function wordTag(w){
  var t = [];
  if (w.pos) t.push(L(POS_KEY[w.pos] || w.pos));
  if (w.gender) t.push(L('g_' + w.gender));
  if (w.asp) t.push(L('asp_' + w.asp));
  return t.join(' · ');
}
function formsLine(w){
  if (!w.forms) return '';
  return Object.keys(w.forms).map(function(k){ return L('f_' + k) + ' ' + srx(w.forms[k]); }).join(' · ');
}
function questionOf(e){
  var it = e.it, f = e.f, w = it.it;
  switch (f){
    case 'pick-tr': return {lbl: L('qPickTr'), q: srx(w.sr), sr: w.sr, hint: wordTag(w), pick: 'tr'};
    case 'listen': return {lbl: L('qListen'), q: '🔊', sr: w.sr, listen: true, pick: 'tr'};
    case 'pick-sr': return {lbl: L('qPickSr'), q: w.tr, hint: wordTag(w), pick: 'sr', say: [w.tr, TRL]};
    case 'say-tr': return {lbl: L('qSayTr'), q: srx(w.sr), sr: w.sr, hint: wordTag(w)};
    case 'say-sr': return {lbl: L('qSaySr'), q: w.tr, hint: wordTag(w), say: [w.tr, TRL]};
    case 'type': return {lbl: L('qType'), q: w.tr, hint: wordTag(w), type: w.sr, say: [w.tr, TRL]};
    case 'listen-ph': return {lbl: L('qListenPh'), q: '🔊', sr: w.sr, listen: true, pick: 'tr', small: true};
    case 'read-ph': return {lbl: L('qReadPh'), q: srx(w.sr), sr: w.sr, pick: 'tr', small: true};
    case 'say-ph': return {lbl: L('qSayPh'), q: w.tr, small: true, say: [w.tr, TRL]};
    case 'type-ph': return {lbl: L('qTypePh'), q: w.tr, small: true, type: w.sr, say: [w.tr, TRL]};
    case 'cloze': return {lbl: L('qCloze'), q: srx(w.sr.replace(/\{[^}]*\}/, '____')), small: true, hint: (w.hint ? srx(w.hint) + ' · ' : '') + w.tr, pick: 'form'};
    case 'aspect': return {lbl: L('qAspect'), q: it.a.tr + '  /  ' + it.b.tr, small: true, hint: L('aspectHint')};
    case 'reply': return {lbl: L('qReply') + ' · ' + ((SIT_BY_ID[it.sit] || {}).title || ''), q: srx(it.they.sr), sr: it.they.sr, small: true, pick: 'reply'};
  }
  return {lbl: '', q: ''};
}
/* a translation as a choice: without the example in brackets ("из (Ja sam iz Rusije — …)" → "из"),
   so options stay short and do not give the answer away; the full text is on the answer side */
function shortTr(t){ var s = String(t || '').replace(/\s*\([^()]*[a-zčćšžđ][^()]*\)/gi, function(m){ return /[a-zčćšžđ]/i.test(m.replace(/[а-яё]/gi, '')) ? '' : m; }).trim(); var d = s.search(/\s[—–-]\s/); if (d > 0 && /[a-zčćšžđ]/i.test(s.slice(d))) s = s.slice(0, d).trim(); return s || String(t || ''); }
function choicesOf(e){
  var it = e.it, f = e.f, w = it.it, right, pool = [];
  if (f === 'pick-tr' || f === 'listen' || f === 'pick-sr'){
    var field = f === 'pick-sr' ? 'sr' : 'tr';
    var cut = field === 'tr' ? shortTr : function(x){ return x; };
    right = cut(w[field]);
    var same = DECK.words.filter(function(o){ return o.id !== w.id && o.pos === w.pos && o[field] !== right; });
    var near = same.filter(function(o){ return Math.abs(o.rank - w.rank) < 120; });
    pool = shuffle((near.length >= 5 ? near : same.length >= 5 ? same : DECK.words.filter(function(o){ return o.id !== w.id; })).slice()).map(function(o){ return cut(o[field]); });
  } else if (f === 'listen-ph' || f === 'read-ph'){
    right = w.tr; pool = shuffle(DECK.phrases.filter(function(o){ return o.id !== w.id; }).map(function(o){ return o.tr; }));
  } else if (f === 'cloze'){
    var m = /\{([^}]*)\}/.exec(w.sr); right = m ? m[1] : '';
    var forms = (w.opts || []).concat(it.w.forms ? Object.keys(it.w.forms).map(function(k){ return it.w.forms[k]; }) : []).concat([it.w.sr]);
    pool = shuffle(forms.filter(function(x){ return x && x.indexOf('/') < 0 && normSr(x) !== normSr(right); }));
  } else if (f === 'reply'){
    right = it.me.sr;
    var mine = [], other = [];
    itemsOfKind('dialog').forEach(function(o){ if (o.id === it.id || o.me.sr === right) return; (o.sit === it.sit ? mine : other).push(o.me.sr); });
    pool = shuffle(mine).concat(shuffle(other));
  } else return null;
  var n = f === 'cloze' || f === 'reply' || f === 'listen-ph' || f === 'read-ph' ? 4 : 6, uniq = [right], seenT = {}; seenT[normSr(right)] = 1;
  pool.forEach(function(x){ if (uniq.length < n && x && !seenT[normSr(x)]){ seenT[normSr(x)] = 1; uniq.push(x); } });
  if (uniq.length < 2) return null;
  return {right: right, opts: shuffle(uniq)};
}
function answerBlock(e){
  var it = e.it, box = el('div', 'tr-ans');
  if (it.kind === 'word'){
    var w = it.it, h = el('div', 'tr-a'); h.appendChild(document.createTextNode(srx(w.accent && !ui.cyr ? w.accent : w.sr))); h.appendChild(spk(w.sr, 'sr')); box.appendChild(h);
    box.appendChild(el('div', 'tr-tr', w.tr));
    var tag = wordTag(w); if (tag) box.appendChild(el('div', 'tr-tag', tag));
    var fl = formsLine(w); if (fl) box.appendChild(el('div', 'tr-forms', fl));
    if (w.pair && WORD_BY_ID[w.pair]) box.appendChild(el('div', 'tr-forms', L('pairWith') + ' ' + srx(WORD_BY_ID[w.pair].sr) + ' — ' + WORD_BY_ID[w.pair].tr));
    if (w.note) box.appendChild(el('div', 'tr-note', w.note));
    var ex = (w.ex || []); if (ex.length){ var x = ex[Math.floor(Math.random() * ex.length)], d = el('div', 'tr-ex'), b = el('b', null, srx(x.sr)); b.appendChild(spk(x.sr, 'sr')); d.appendChild(b); d.appendChild(el('div', null, x.tr)); if (x.about) d.appendChild(el('span', 'tr-src', L('ex_' + x.about))); box.appendChild(d); }
    if ((w.sit || []).length){ var chips = el('div', 'chips'); w.sit.forEach(function(s){ if (SIT_BY_ID[s]) chips.appendChild(el('span', 'chip', SIT_BY_ID[s].title)); }); box.appendChild(chips); }
  } else if (it.kind === 'phrase' || it.kind === 'cloze'){
    var p = it.it, full = p.sr.replace(/[{}]/g, ''), a = el('div', 'tr-a small'); a.appendChild(document.createTextNode(srx(full))); a.appendChild(spk(full, 'sr')); box.appendChild(a);
    box.appendChild(el('div', 'tr-tr', p.tr));
    if (p.note) box.appendChild(el('div', 'tr-note', p.note));
    if (it.kind === 'cloze' && p.case) box.appendChild(el('div', 'tr-tag', L('case_' + p.case)));
  } else if (it.kind === 'pair'){
    [it.a, it.b].forEach(function(w){ var r = el('div', 'tr-a small'); r.appendChild(document.createTextNode(srx(w.sr) + ' — ' + L('asp_' + (w.asp || '')))); r.appendChild(spk(w.sr, 'sr')); box.appendChild(r);
      box.appendChild(el('div', 'tr-tr', w.tr)); var x = (w.ex || [])[0]; if (x){ var d = el('div', 'tr-ex'); d.appendChild(el('b', null, srx(x.sr))); d.appendChild(el('div', null, x.tr)); box.appendChild(d); } });
  } else if (it.kind === 'dialog'){
    [['they', it.they], ['me', it.me]].forEach(function(x){ var r = el('div', 'dl-line ' + x[0]); var s = el('b', null, srx(x[1].sr)); s.appendChild(spk(x[1].sr, 'sr')); r.appendChild(s); r.appendChild(el('div', null, x[1].tr)); box.appendChild(r); });
  }
  return box;
}
function answerSpeech(e){
  var it = e.it;
  if (it.kind === 'word') return e.f === 'pick-tr' || e.f === 'say-tr' || e.f === 'listen' ? [it.it.sr, 'sr'] : [it.it.sr, 'sr'];
  if (it.kind === 'phrase') return [it.it.sr, 'sr'];
  if (it.kind === 'cloze') return [it.it.sr.replace(/[{}]/g, ''), 'sr'];
  if (it.kind === 'pair') return [it.a.sr + ', ' + it.b.sr, 'sr'];
  if (it.kind === 'dialog') return [it.me.sr, 'sr'];
  return null;
}
function questionSpeech(e, q){ if (q.listen || q.sr) return [q.sr, 'sr']; if (q.say) return q.say; return null; }
