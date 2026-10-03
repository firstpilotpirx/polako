// Page smoke test in jsdom: the built page renders every tab, a full round can be played with the
// keyboard-free click path, answers are graded and logged, and the statistics tab draws its charts
// from a simulated 45-day history. Run: node tests/page_smoke.js <path to dist/index.html>
// (needs the jsdom package: NODE_PATH pointing to a folder with node_modules/jsdom).
const fs = require('fs');
const path = require('path');
let JSDOM;
try { ({JSDOM} = require('jsdom')); } catch (e) { console.log('skip: jsdom not installed'); process.exit(0); }
const FSRS = require(path.join(__dirname, '..', 'templates', 'portal', 'fsrs.js'));

const file = process.argv[2] || path.join(__dirname, '..', 'examples', 'sample', 'dist', 'index.html');
const html = fs.readFileSync(file, 'utf8');
const errors = [];
function fakeSpeech(win){
  const voices = [{name: 'Lana', lang: 'hr-HR', default: false}, {name: 'Milena', lang: 'ru-RU', default: true}];
  win.SpeechSynthesisUtterance = function(t){ this.text = t; };
  win.speechSynthesis = {getVoices: () => voices, speaking: false, cancel(){}, addEventListener(){},
    speak(u){ setTimeout(() => u.onend && u.onend(), 5); }};
}
function makeDom(storage){
  const dom = new JSDOM(html, {runScripts: 'dangerously', url: 'https://example.org/', pretendToBeVisual: true,
    beforeParse(win){
      fakeSpeech(win);
      win.matchMedia = () => ({matches: false, addEventListener(){}});
      win.scrollTo = () => {};
      win.addEventListener('error', e => errors.push(e.error ? e.error.stack : e.message));
      win.console.error = (...a) => errors.push(a.join(' '));
      if (storage) for (const k in storage) win.localStorage.setItem(k, storage[k]);
    }});
  return dom;
}
const sleep = ms => new Promise(r => setTimeout(r, ms));
function assert(c, msg){ if (!c){ console.error('FAIL: ' + msg); process.exitCode = 1; throw new Error(msg); } }
function tab(doc, i){ doc.querySelectorAll('#tabs button')[i].click(); }

(async () => {
  // 1. a fresh learner plays one round
  let dom = makeDom(), win = dom.window, doc = win.document;
  await sleep(50);
  assert(doc.querySelectorAll('#tabs button').length === 6, 'six tabs');
  const smart = doc.querySelector('.tr-smart');
  assert(smart, 'the "learn by importance" button');
  smart.click(); await sleep(10);
  let steps = 0, kinds = {};
  while (doc.querySelector('.tr-play') && !doc.querySelector('.tr-done') && steps < 200){
    steps++;
    const lbl = (doc.querySelector('.tr-flag') || {}).title || '';   // the card's side: the flag carries its description
    kinds[lbl.split(' · ')[0]] = (kinds[lbl.split(' · ')[0]] || 0) + 1;
    const opt = doc.querySelector('.tr-choice:not([disabled])');
    if (opt){ opt.click(); await sleep(5); const nx = doc.querySelector('[data-key="next"]'); if (nx) nx.click(); await sleep(5); continue; }
    const show = doc.querySelector('[data-key="show"]'); if (show){ show.click(); await sleep(5); }
    const g = doc.querySelector('[data-key="g3"]'); if (g){ g.click(); await sleep(5); continue; }
    const form = doc.querySelector('.tr-type'); if (form){ form.querySelector('input').value = 'test'; form.dispatchEvent(new win.Event('submit', {cancelable: true})); await sleep(5); const nx = doc.querySelector('[data-key="next"]'); if (nx) nx.click(); continue; }
    break;
  }
  assert(doc.querySelector('.tr-done'), 'the round ends (steps: ' + steps + ')');
  const fb = JSON.parse(win.localStorage.getItem('pl.fallback'));
  assert(Object.keys(fb.T.cards).length >= 10, 'cards graded: ' + Object.keys(fb.T.cards).length);
  assert(fb.LOG.length >= steps * 0.5, 'answers logged: ' + fb.LOG.length);
  assert(Object.keys(kinds).some(k => /послушайте/i.test(k)), 'a listening card appears with a Croatian voice: ' + JSON.stringify(kinds));
  console.log('round:', steps, 'cards, sides seen', JSON.stringify(kinds));
  for (let i = 0; i < 6; i++){ tab(doc, i); await sleep(5); assert(doc.querySelector('#main').children.length, 'tab ' + i + ' renders'); }
  tab(doc, 3); await sleep(5);
  assert(doc.querySelectorAll('.text-card').length === 4, 'own texts shown');
  assert(doc.querySelectorAll('.text-card .tok').length > 50, 'text tokens highlighted');
  tab(doc, 2); await sleep(5);
  assert(doc.querySelectorAll('.sit').length === 5, 'situations shown');
  doc.querySelector('.sit .acts .btn:not(.primary)').click(); await sleep(5);
  assert(doc.querySelector('.dialog .dl-line'), 'dialog opens');
  tab(doc, 1); await sleep(5);
  assert(doc.querySelector('.qcheck'), 'quick check first');
  doc.querySelectorAll('.qbox input').forEach(c => c.checked = true);
  doc.querySelector('.qcheck .acts .btn.primary').click(); await sleep(20);
  dom.window.close();

  // 2. a simulated learner: 45 days, ~15 new words a day, Good 85% of the time → statistics
  const words = JSON.parse(html.match(/<script id="pl-data" type="application\/json">([\s\S]*?)<\/script>/)[1].replace(/<\\\//g, '</')).deck.words;
  const cards = {}, log = [], day = 86400000, t0 = Date.now() - 45 * day;
  let rnd = 42; const rand = () => (rnd = (rnd * 16807) % 2147483647) / 2147483647;
  for (let d = 0; d < 45; d++){
    const now = t0 + d * day + 9 * 3600000;
    const fresh = words.slice(d * 3, d * 3 + 3);
    fresh.forEach(w => ['pick-tr', 'listen', 'pick-sr'].forEach(sd => { cards[w.id + '|' + sd] = null; }));
    Object.keys(cards).forEach((k, i) => {
      const c = cards[k]; if (c && c.due > now) return;
      const g = rand() < 0.85 ? 3 : 1, t = now + i * 9000, r = FSRS.review(c, g, t, 0.9);
      r.card.g = g; cards[k] = r.card; log.push([t, k, g, 2500 + Math.floor(rand() * 6000), r.elapsed, r.sBefore]);
    });
  }
  const T = {cards, goal: 15, retention: 0.9, listening: true, typing: false, hist: {}};
  for (let d = 0; d < 45; d += 3){ const k = new Date(t0 + d * day).toISOString().slice(0, 10); T.hist[k] = {sp: 0.2 + d / 100, my: 0.3 + d / 120, kn: d * 2, lr: d}; }
  dom = makeDom({'pl.fallback': JSON.stringify({T, LOG: log, V: {}}), 'pl.tab': '"stats"'}); win = dom.window; doc = win.document;
  await sleep(50);
  const charts = doc.querySelectorAll('.viz-svg').length, bars = doc.querySelectorAll('.viz-svg .bar').length;
  assert(charts >= 8, 'statistics charts: ' + charts);
  assert(bars > 30, 'bars drawn: ' + bars);
  assert(doc.querySelector('.hero-v').textContent.endsWith('%'), 'coverage hero number');
  assert(doc.querySelectorAll('.hc.l4').length >= 1, 'calendar has activity');
  console.log('stats:', charts, 'charts,', bars, 'bars, hero', doc.querySelector('.hero-v').textContent, '· log', log.length);
  tab(doc, 0); await sleep(10);
  assert(/\d/.test(doc.querySelector('.tr-overall').textContent), 'forecast line');
  console.log('forecast:', doc.querySelector('.tr-overall .meta').textContent);
  tab(doc, 5); await sleep(10);
  assert(doc.querySelectorAll('.deck-t tr').length > 50, 'deck table');
  dom.window.close();
  if (errors.length){ console.error(errors.slice(0, 5).join('\n')); assert(false, 'page errors: ' + errors.length); }
  console.log('page: ok');
})().catch(e => { console.error(e.stack || e); process.exit(1); });
