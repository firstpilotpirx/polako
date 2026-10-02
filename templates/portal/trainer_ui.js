/* ---------- Trainer tab: overview ---------- */
function ring(size, frac, label, cls){
  var NS = 'http://www.w3.org/2000/svg', sw = Math.max(4, Math.round(size / 9)), r = (size - sw) / 2, c = 2 * Math.PI * r;
  var svg = document.createElementNS(NS, 'svg'); svg.setAttribute('width', size); svg.setAttribute('height', size); svg.setAttribute('viewBox', '0 0 ' + size + ' ' + size);
  svg.setAttribute('class', 'ring' + (frac >= 1 ? ' full' : '') + (cls ? ' ' + cls : '')); svg.setAttribute('role', 'img'); svg.setAttribute('aria-label', label);
  function circ(k){ var e = document.createElementNS(NS, 'circle'); e.setAttribute('cx', size / 2); e.setAttribute('cy', size / 2); e.setAttribute('r', r); e.setAttribute('fill', 'none'); e.setAttribute('stroke-width', sw); e.setAttribute('class', k); return e; }
  svg.appendChild(circ('ring-bg'));
  if (frac > 0){ var fg = circ('ring-fg'); fg.setAttribute('stroke-linecap', 'round'); fg.setAttribute('stroke-dasharray', c); fg.setAttribute('stroke-dashoffset', c * (1 - Math.max(0, Math.min(1, frac)))); fg.setAttribute('transform', 'rotate(-90 ' + size / 2 + ' ' + size / 2 + ')'); svg.appendChild(fg); }
  var tx = document.createElementNS(NS, 'text'); tx.setAttribute('x', '50%'); tx.setAttribute('y', '50%'); tx.setAttribute('text-anchor', 'middle'); tx.setAttribute('dominant-baseline', 'central'); tx.setAttribute('class', 'ring-t'); tx.textContent = label; svg.appendChild(tx);
  return svg;
}
function drawGoal(){
  var by = newWordsByDay(), t0 = today0(), done = by[t0] || 0, box = el('div', 'goal');
  var big = el('div', 'goal-ring'); big.appendChild(ring(120, done / T.goal, done + '/' + T.goal));
  var cap = el('div', 'goal-cap');
  cap.appendChild(el('b', null, done >= T.goal ? '✓ ' + L('goalDone') : L('goalToday') + ': ' + done + ' / ' + T.goal));
  if (done < T.goal) cap.appendChild(el('span', 'meta', L('goalLeft') + ' ' + (T.goal - done)));
  var st = streak(); if (st) cap.appendChild(el('span', 'goal-streak', '🔥 ' + L('streak') + ': ' + nWord(st, 'days')));
  big.appendChild(cap); box.appendChild(big);
  var wk = el('div', 'goal-week'), row = el('div', 'goal-days'), act = activeDays();
  wk.appendChild(el('div', 'goal-wk-h', L('goalWeek')));
  for (var i = 6; i >= 0; i--){
    var day = t0 - i * DAY, n = by[day] || 0, cell = el('div', 'goal-day' + (i === 0 ? ' today' : ''));
    cell.appendChild(ring(40, n / T.goal, String(n))); cell.title = (act[day] || 0) + ' ' + L('answers');
    cell.appendChild(el('span', null, new Date(day).toLocaleDateString(TRL, {weekday: 'short'}))); row.appendChild(cell);
  }
  wk.appendChild(row); box.appendChild(wk);
  var adj = el('label', 'goal-adj'), val = el('b', null, nWord(T.goal, 'wordsPerDay'));
  adj.appendChild(el('span', null, L('goalLabel') + ': ')); adj.appendChild(val);
  var rg = el('input'); rg.type = 'range'; rg.min = 5; rg.max = 40; rg.step = 5; rg.value = Math.min(40, Math.max(5, T.goal)); rg.setAttribute('aria-label', L('goalLabel'));
  rg.oninput = function(){ val.textContent = nWord(+rg.value, 'wordsPerDay'); };
  rg.onchange = function(){ T.goal = +rg.value; save(); rerenderKeepScroll(); };
  adj.appendChild(rg); box.appendChild(adj);
  return box;
}
function renderTrainer(main){
  if (play) return renderPlay(main);
  var all = decks(), words = itemsOfKind('word').filter(function(it){ return !knownSet()[it.id]; });
  main.appendChild(el('h2', 'tr-h', L('trTitle')));
  main.appendChild(el('p', 'meta tr-intro', L('trIntro')));
  main.appendChild(drawGoal());
  var s = stats(allItems().filter(function(it){ return !(it.kind === 'word' && knownSet()[it.id]); })), cov = coverageNow();
  var tiles = el('div', 'tr-stats');
  [[pct(cov.spoken), L('covSpokenLong')], [s.learned, L('trLearned')], [s.firm + s.learning, L('trInProgress')], [s.due, L('dueNow')]].forEach(function(x){
    var c = el('div', 'tr-stat'); c.appendChild(el('b', null, x[0])); c.appendChild(el('span', null, x[1])); tiles.appendChild(c); });
  main.appendChild(tiles);
  // the main button: what is due, by importance, then new words up to today's goal
  var sm = smartDeck(), inRound = queueFor(sm.items, ui.size, {smart: true}).length;
  if (!inRound) sm.extra = true;
  var big = el('button', 'tr-smart' + (sm.extra ? ' extra' : '')); big.type = 'button';
  var r = el('div', 'row'), l = el('div');
  l.appendChild(el('h3', null, sm.extra ? L('goalDone') + ' · ' + L('extraRound') : L('smart'))); l.appendChild(el('p', null, sm.extra ? L('extraDesc') : L('smartDesc')));
  var go = el('div', 'go'); go.appendChild(el('b', null, sm.extra ? Math.min(ui.size, queueFor(sm.items, ui.size, {smart: true, extra: true}).length) : inRound)); go.appendChild(document.createTextNode(L('cardsGo')));
  r.appendChild(l); r.appendChild(go); big.appendChild(r); big.onclick = function(){ startRound(sm); }; main.appendChild(big);
  var modes = el('div', 'tr-modes');
  if (listenOn()) modes.appendChild(btn('btn', '🎧 ' + L('listenOnly'), function(){ startRound({key: 'listen', items: allItems().filter(seen)}, {only: ['listen', 'listen-ph']}); }));
  modes.appendChild(btn('btn', '🗣 ' + L('sayOnly'), function(){ startRound({key: 'say', items: allItems().filter(seen)}, {only: ['say-sr', 'say-ph', 'aspect', 'type', 'type-ph']}); }));
  main.appendChild(modes);
  // overall forecast
  var wp = T.goal, fc = etaOf(words, wp, 0), ov = el('div', 'tr-overall');
  var prog = 0; words.forEach(function(it){ prog += itemPct(it); }); prog = words.length ? prog / words.length : 0;
  ov.appendChild(el('div', 'tr-ov-h', L('overall') + ' ' + Math.round(prog * 100) + '%'));
  var ob = el('div', 'bar tr-ov-bar'), oi = el('i', 'd'); oi.style.width = Math.round(prog * 100) + '%'; ob.appendChild(oi); ov.appendChild(ob);
  ov.appendChild(el('div', 'meta', L('wordsN') + ' (' + words.length + '): ' + etaText(fc, true)));
  ov.appendChild(el('div', 'tr-note-s', L('etaNote')));
  main.appendChild(ov);
  var list = el('div', 'tr-decks'), grp = null, before = 0;
  all.forEach(function(dk){
    if (dk.grp !== grp){ grp = dk.grp; list.appendChild(el('div', 'tr-grp', grp)); }
    var st = stats(dk.items), b = el('button', 'tr-deck' + (st.learned === st.total ? ' done' : '')); b.type = 'button';
    var row = el('div', 'row'), left = el('div');
    left.appendChild(el('h3', null, dk.title)); left.appendChild(el('p', null, dk.desc + ' · ' + nWord(st.total, 'cards')));
    var g2 = el('div', 'go' + (st.due ? '' : ' zero')); g2.appendChild(el('b', null, st.due)); g2.appendChild(document.createTextNode(st.due ? L('due') : L('nothingDue')));
    row.appendChild(left); row.appendChild(g2); b.appendChild(row);
    b.appendChild(bar(mix(dk.items))); b.appendChild(legend(st));
    var e = dk.words ? etaOf(dk.items, wp, before) : etaOf(dk.items, Math.max(1, wp / 4), 0); if (dk.words && e) before += e.fresh;
    var p = 0; dk.items.forEach(function(it){ p += itemPct(it); });
    b.appendChild(el('div', 'tr-eta', L('progress') + ' ' + Math.round(p / Math.max(1, dk.items.length) * 100) + '% · ' + etaText(e)));
    b.onclick = function(){ startRound(dk); };
    list.appendChild(b);
  });
  main.appendChild(list);
  main.appendChild(trainerOptions());
}
function trainerOptions(){
  var opts = el('details', 'tr-opts'); opts.appendChild(el('summary', null, L('settings')));
  var row = el('div', 'opt-row');
  var lab = el('label', null, L('size') + ' '), sel = el('select');
  [10, 20, 30, 50].forEach(function(v){ var o = el('option', null, String(v)); o.value = v; o.selected = v === ui.size; sel.appendChild(o); });
  sel.onchange = function(){ ui.size = +sel.value; lsSet('pl.size', ui.size); }; lab.appendChild(sel); row.appendChild(lab);
  var rl = el('label', null, L('retention') + ' '), rs = el('select');
  [[0.85, '85%'], [0.9, '90%'], [0.95, '95%']].forEach(function(x){ var o = el('option', null, x[1] + ' — ' + L('ret_' + Math.round(x[0] * 100))); o.value = x[0]; o.selected = Math.abs(T.retention - x[0]) < 0.001; rs.appendChild(o); });
  rs.onchange = function(){ T.retention = +rs.value; save(); }; rl.appendChild(rs); row.appendChild(rl);
  opts.appendChild(row);
  [['listening', L('optListening')], ['typing', L('optTyping')]].forEach(function(x){
    var lb = el('label', 'opt-check'), c = el('input'); c.type = 'checkbox'; c.checked = !!T[x[0]];
    c.onchange = function(){ T[x[0]] = c.checked; save(); rerenderKeepScroll(); }; lb.appendChild(c); lb.appendChild(document.createTextNode(' ' + x[1])); opts.appendChild(lb);
  });
  opts.appendChild(ttsControls());
  var rsb = btn('linkbtn', L('reset')), armed = false;
  rsb.onclick = function(){ if (!armed){ armed = true; rsb.textContent = L('resetSure'); setTimeout(function(){ armed = false; rsb.textContent = L('reset'); }, 4000); return; }
    T.cards = {}; T.reset = NOW(); save(); flush(); render(); };
  opts.appendChild(rsb);
  return opts;
}

/* ---------- a round ---------- */
function endRound(){ play = null; snapshot(); flush(); render(); }
function renderPlay(main){
  var p = play, box = el('div', 'tr-play');
  var hud = el('div', 'tr-hud'); hud.appendChild(btn('btn', '← ' + L('toDecks'), endRound));
  if (p.idx < p.queue.length){
    hud.appendChild(el('span', 'tr-pill', (p.idx + 1) + ' / ' + p.queue.length));
    hud.appendChild(el('span', 'tr-pill g', '✓ ' + p.right)); hud.appendChild(el('span', 'tr-pill r', '✗ ' + p.wrong));
  }
  box.appendChild(hud);
  if (p.idx >= p.queue.length){
    snapshot();
    var c = el('div', 'tr-done'), mins = Math.max(1, Math.round((NOW() - p.startedAt) / 60000));
    c.appendChild(el('h3', null, L('endTitle')));
    c.appendChild(el('p', null, L('right') + ': ' + p.right + ' · ' + L('wrong') + ': ' + p.wrong + ' · ' + mins + ' ' + L('min')));
    var cov = coverageNow(); c.appendChild(el('p', 'meta', L('covSpokenLong') + ': ' + pct(cov.spoken) + (cov.my != null ? ' · ' + L('covMy') + ': ' + pct(cov.my) : '')));
    var left = queueFor(p.deck.items, ui.size, {smart: p.deck.smart}).length;
    c.appendChild(el('p', 'meta', left ? L('dueNow') + ': ' + left : L('allDoneTomorrow')));
    var a = el('div', 'tr-acts');
    a.appendChild(btn('btn primary', left ? L('again') : L('toDecks'), function(){ if (left) startRound(p.deck, p.opts); else endRound(); }, 'next'));
    if (left) a.appendChild(btn('btn', L('toDecks'), endRound));
    c.appendChild(a); box.appendChild(c); main.appendChild(box); flush(); return;
  }
  box.appendChild(bar([['d', p.idx / p.queue.length]]));
  var e = p.queue[p.idx], it = e.it, q = questionOf(e), ch = q.pick ? (p.ch || (p.ch = choicesOf(e))) : null;
  if (q.pick && !ch) q.pick = null;   // too few options: fall back to self-grading
  var c2 = el('div', 'tr-box' + (p.picked ? (p.pickedOk ? ' ok' : ' bad') : ''));
  c2.appendChild(el('div', 'tr-lbl', q.lbl + (e.again ? ' · ' + L('againMark') : '')));
  var qEl = el('div', 'tr-q' + (q.small ? ' small' : '') + (q.listen ? ' listen' : ''));
  if (q.listen){ var lb = btn('listen-btn', '🔊', function(){ speak(q.sr, 'sr'); }); lb.setAttribute('aria-label', L('ttsPlay')); qEl.appendChild(lb); if (p.shown) qEl.appendChild(el('div', 'tr-q small', srx(q.sr))); }
  else { qEl.appendChild(document.createTextNode(q.q)); var qs = questionSpeech(e, q); if (qs && !q.type) qEl.appendChild(spk(qs[0], qs[1])); }
  c2.appendChild(qEl);
  if (q.hint) c2.appendChild(el('div', 'tr-hint', q.hint));
  if (p.shown) c2.appendChild(answerBlock(e));
  box.appendChild(c2);
  var below = el('div');
  if (q.pick){
    var chs = el('div', 'tr-choices' + (q.small || q.pick === 'form' ? ' wide' : ''));
    ch.opts.forEach(function(o, i){
      var b = btn('tr-choice', (i + 1) + '. ' + (q.pick === 'tr' ? o : srx(o)), null, 'opt' + (i + 1));
      if (p.picked){ b.disabled = true; if (o === ch.right) b.className = 'tr-choice ok'; else if (o === p.picked) b.className = 'tr-choice no'; }
      b.onclick = function(){
        if (p.picked) return;
        var ok = o === ch.right, idx = p.idx, ms = NOW() - p.t0;
        p.picked = o; p.pickedOk = ok; p.shown = true; p.spoken = idx + ':1'; p.g = gradeChoice(ok, ms, it.kind);
        render(); sfx(ok ? 'ok' : 'bad');
        function next(){
          if (!TTS_CFG.next || play !== p || p.idx !== idx || !p.picked) return;
          var nb = document.querySelector('.tr-play [data-key="next"]'), wait = Math.round((ok ? TTS_CFG.pauseOk : TTS_CFG.pauseBad) * 1000);
          if (nb){ nb.style.setProperty('--auto', wait + 'ms'); nb.classList.add('counting'); }
          setTimeout(function(){ if (play === p && p.idx === idx && p.picked){ p.ch = null; grade(p.g); } }, wait);
        }
        var sa = answerSpeech(e);
        setTimeout(function(){ if (TTS_CFG.auto && sa) speak(sa[0], sa[1], next); else next(); }, ok ? 150 : 380);
      };
      chs.appendChild(b);
    });
    below.appendChild(chs);
    if (p.shown){ var a1 = el('div', 'tr-acts'); a1.appendChild(btn('btn primary wide', L('next'), function(){ p.ch = null; grade(p.g); }, 'next')); below.appendChild(a1); }
    below.appendChild(el('p', 'tr-keys', p.shown ? L('keysNext') : L('keysPick')));
  } else if (q.type && !p.shown){
    var form = el('form', 'tr-type'), inp = el('input'); inp.type = 'text'; inp.autocomplete = 'off'; inp.spellcheck = false; inp.setAttribute('autocapitalize', 'off'); inp.placeholder = L('typeHere');
    form.appendChild(inp); form.appendChild(btn('btn primary', L('check')));
    form.onsubmit = function(ev){
      ev.preventDefault(); var v = inp.value.trim(); if (!v) return;
      var right = normSr(q.type), got = normSr(v), ms = NOW() - p.t0, g;
      if (got === right) g = ms < 9000 ? 3 : 2;
      else if (fold(got) === fold(right)) { g = 2; p.typedNote = L('typeDiacritics'); }
      else if (right.length >= 5 && lev(got, right) <= 1) { g = 2; p.typedNote = L('typeAlmost'); }
      else g = 1;
      p.typed = v; p.g = g; p.shown = true; p.picked = v; p.pickedOk = g > 1; sfx(g > 1 ? 'ok' : 'bad'); render();
      var sa = answerSpeech(e); if (TTS_CFG.auto && sa) speak(sa[0], sa[1]);
    };
    below.appendChild(form); setTimeout(function(){ inp.focus(); }, 30);
    below.appendChild(el('p', 'tr-keys', L('keysType')));
  } else if (q.type){
    below.appendChild(el('div', 'tr-typed ' + (p.pickedOk ? 'ok' : 'no'), L('youTyped') + ': ' + p.typed + (p.typedNote ? ' · ' + p.typedNote : '')));
    var a4 = el('div', 'tr-acts'); a4.appendChild(btn('btn primary wide', L('next'), function(){ grade(p.g); }, 'next')); below.appendChild(a4);
  } else if (!p.shown){
    var a2 = el('div', 'tr-acts'); a2.appendChild(btn('btn primary wide', L('show'), function(){ p.shown = true; render(); }, 'show')); below.appendChild(a2);
    below.appendChild(el('p', 'tr-keys', L('keysShow')));
  } else {
    var a3 = el('div', 'tr-grades');
    [[1, 'gAgain', 'bad'], [2, 'gHard', 'hard'], [3, 'gGood', 'good'], [4, 'gEasy', 'easy']].forEach(function(x){
      var b = btn('btn grade ' + x[2], null, function(){ sfx(x[0] > 1 ? 'ok' : 'bad'); grade(x[0]); }, 'g' + x[0]);
      b.appendChild(el('b', null, x[0] + ' · ' + L(x[1]))); b.appendChild(el('span', null, previewIvl(e, x[0]))); a3.appendChild(b);
    });
    below.appendChild(a3);
    below.appendChild(el('p', 'tr-keys', L('keysGrade')));
  }
  if (TTS.ok && canSpeak('sr')) below.appendChild(el('p', 'tr-keys', L('keysSpeak')));
  box.appendChild(below); main.appendChild(box);
  // auto-play once per card side: the question when it opens (a listening card plays its sound), the answer when revealed
  var k = p.idx + ':' + (p.shown ? 1 : 0);
  if (TTS_CFG.auto && p.spoken !== k){ p.spoken = k; var s = p.shown ? answerSpeech(e) : (q.listen ? [q.sr, 'sr'] : questionSpeech(e, q));
    if (s && s[0] && !(p.shown && q.pick)) setTimeout(function(){ if (play === p && p.idx === +k.split(':')[0]) speak(s[0], s[1]); }, 120); }
}
function lev(a, b){
  var m = a.length, n = b.length, d = []; for (var i = 0; i <= m; i++){ d[i] = [i]; } for (var j = 1; j <= n; j++) d[0][j] = j;
  for (i = 1; i <= m; i++) for (j = 1; j <= n; j++) d[i][j] = Math.min(d[i - 1][j] + 1, d[i][j - 1] + 1, d[i - 1][j - 1] + (a[i - 1] === b[j - 1] ? 0 : 1));
  return d[m][n];
}
document.addEventListener('keydown', function(ev){
  if (!play || ui.tab !== 'train' || /INPUT|SELECT|TEXTAREA/.test((ev.target || {}).tagName || '')) return;
  var q = function(k){ return document.querySelector('.tr-play [data-key="' + k + '"]'); };
  if (ev.key === 'Escape'){ endRound(); return; }
  if (ev.key === ' ' || ev.key === 'Enter'){ var b = q('next') || q('show') || q('g3'); if (b){ ev.preventDefault(); b.click(); } return; }
  if (/^[1-6]$/.test(ev.key)){ var o = q('opt' + ev.key) || q('g' + ev.key); if (o && !o.disabled){ ev.preventDefault(); o.click(); } return; }
  if ((ev.key === 'v' || ev.key === 'V' || ev.key === 'м' || ev.key === 'М') && play.idx < play.queue.length){
    var e = play.queue[play.idx], qq = questionOf(e), s = play.shown ? answerSpeech(e) : (qq.listen ? [qq.sr, 'sr'] : questionSpeech(e, qq));
    if (s){ ev.preventDefault(); speak(s[0], s[1]); } }
});
