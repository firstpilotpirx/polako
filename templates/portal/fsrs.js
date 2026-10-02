/* ---------- FSRS-5 scheduler ----------
   Free Spaced Repetition Scheduler (open-spaced-repetition/fsrs4anki, FSRS-5 default weights).
   A card side keeps: s — stability (days until recall drops to 90%), d — difficulty 1..10,
   due (ms), last (ms), reps, lapses. Grades: 1 Again, 2 Hard, 3 Good, 4 Easy.
   The same formulas live in tools/fsrs.py; tests/test_fsrs.py runs both on one script of answers.
   Exported as FSRS (also usable from node: module.exports). */
var FSRS = (function(){
  var W = [0.40255, 1.18385, 3.173, 15.69105, 7.1949, 0.5345, 1.4604, 0.0046, 1.54575, 0.1192,
           1.01925, 1.9395, 0.11, 0.29605, 2.2698, 0.2315, 2.9898, 0.51655, 0.6621];
  var DECAY = -0.5, FACTOR = 19 / 81, DAYMS = 86400000, MAX_IVL = 3650, RELEARN_MS = 10 * 60000;
  function clamp(x, a, b){ return Math.min(b, Math.max(a, x)); }
  function r4(x){ return Math.round(x * 10000) / 10000; }
  function retrievability(elapsedDays, s){ return Math.pow(1 + FACTOR * elapsedDays / s, DECAY); }
  function interval(s, retention){ return s / FACTOR * (Math.pow(retention, 1 / DECAY) - 1); }
  function d0(g){ return clamp(W[4] - Math.exp(W[5] * (g - 1)) + 1, 1, 10); }
  function s0(g){ return Math.max(0.1, W[g - 1]); }
  function nextD(d, g){
    var dd = -W[6] * (g - 3), d1 = d + dd * (10 - d) / 9;
    return clamp(W[7] * d0(4) + (1 - W[7]) * d1, 1, 10);
  }
  function sRecall(d, s, r, g){
    var hard = g === 2 ? W[15] : 1, easy = g === 4 ? W[16] : 1;
    return s * (1 + Math.exp(W[8]) * (11 - d) * Math.pow(s, -W[9]) * (Math.exp(W[10] * (1 - r)) - 1) * hard * easy);
  }
  function sForget(d, s, r){
    return Math.min(s, W[11] * Math.pow(d, -W[12]) * (Math.pow(s + 1, W[13]) - 1) * Math.exp(W[14] * (1 - r)));
  }
  function sShort(s, g){ return s * Math.exp(W[17] * (g - 3 + W[18])); }
  /* review(card or null, grade, now ms, target retention) → new card + log fields */
  function review(c, g, now, retention){
    retention = retention || 0.9;
    var n = {reps: 0, lapses: 0}, elapsed = 0, sBefore = 0, rBefore = 1;
    if (!c || !c.s){
      n.s = s0(g); n.d = d0(g);
    } else {
      elapsed = Math.max(0, (now - (c.last || now)) / DAYMS);
      sBefore = c.s; rBefore = retrievability(elapsed, c.s);
      n.reps = c.reps || 0; n.lapses = c.lapses || 0; n.f = c.f;
      n.d = nextD(c.d || d0(3), g);
      if (elapsed < 1) n.s = sShort(c.s, g);
      else if (g === 1){ n.s = sForget(c.d || d0(3), c.s, rBefore); n.lapses++; }
      else n.s = sRecall(c.d || d0(3), c.s, rBefore, g);
    }
    n.s = clamp(n.s, 0.1, 36500);
    n.reps++;
    n.last = now; if (!n.f) n.f = now;
    if (g === 1) n.due = now + RELEARN_MS;
    else n.due = now + clamp(Math.round(interval(n.s, retention)), 1, MAX_IVL) * DAYMS;
    n.s = r4(n.s); n.d = r4(n.d);
    return {card: n, elapsed: r4(elapsed), sBefore: r4(sBefore), r: r4(rBefore)};
  }
  /* days from now until the side reaches stability `target` if every answer is Good at its due date */
  function daysToStable(c, now, retention, target){
    var s = c && c.s ? c.s : 0, d = c && c.d ? c.d : d0(3), t = 0, guard = 0;
    if (!s){ s = s0(3); d = d0(3); t = 1; }
    else t = Math.max(0, ((c.due || now) - now) / DAYMS);
    while (s < target && guard++ < 40){
      var ivl = clamp(Math.round(interval(s, retention)), 1, MAX_IVL);
      s = sRecall(d, s, retrievability(ivl, s), 3); d = nextD(d, 3);
      if (s < target) t += clamp(Math.round(interval(s, retention)), 1, MAX_IVL);
    }
    return t;
  }
  function setW(w){ if (w && w.length === 19 && w.every(function(x){ return typeof x === 'number' && isFinite(x); })) W = w.slice(); }
  return {setW: setW, weights: function(){ return W.slice(); }, review: review, retrievability: retrievability, interval: interval, daysToStable: daysToStable, DAYMS: DAYMS};
})();
if (typeof module !== 'undefined' && module.exports) module.exports = FSRS;
