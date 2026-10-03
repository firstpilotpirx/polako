/* ---------- boot: theme, first render, storage (local server → artifact db → this browser) ---------- */
$('theme').onclick = function(){ var dark = ui.theme ? ui.theme === 'dark' : matchMedia('(prefers-color-scheme: dark)').matches; ui.theme = dark ? 'light' : 'dark'; lsSet('pl.theme', ui.theme); applyTheme(); };
applyTheme();
if (D.fsrs && D.fsrs.w) FSRS.setW(D.fsrs.w);   // personal weights from tools/fsrs_fit.py
(function(){ var fb = lsGet('pl.fallback', null); if (fb){ if (fb.T && fb.T.cards) T = Object.assign(T, fb.T); LOG = fb.LOG || []; V = fb.V || {}; } })();
if (!TABS.some(function(t){ return t[0] === ui.tab; })) ui.tab = 'train';
render();
setTimeout(function(){ if (TTS.ok){ ttsLoad(); if (!play) render(); } }, 700);   // voices arrive late in some browsers

(async function(){
  var local = /^https?:$/.test(location.protocol) && /^(localhost|127\.0\.0\.1|\[::1\])$/.test(location.hostname);
  if (local){
    try {
      var ping = await fetch('/api/ping', {cache: 'no-store'});
      if (ping.ok){
        store.mode = 'api';
        var tr = await (await fetch('/api/trainer')).json(); if (tr && tr.cards) T = Object.assign(T, tr);
        var lg = await (await fetch('/api/log')).json(); if (Array.isArray(lg)) LOG = lg;
        var vc = await (await fetch('/api/vocab')).json(); if (vc && typeof vc === 'object') V = vc;
        ITEMS_CACHE = null; render(); setSync(L('live')); liveReload(); return;
      }
    } catch (e){}
  }
  if (typeof GH !== 'undefined' && GH.on()){   // the public site with the person's own repository
    try {
      setSync(L('ghLoading')); await ghPull(); store.mode = 'gh'; render(); setSync(L('ghSaved'));
      document.addEventListener('visibilitychange', function(){
        if (document.visibilityState === 'hidden') flush();
        else if (!play) ghPull().then(function(){ render(); setSync(L('ghSaved')); }).catch(function(){});
      });
    } catch (e){ store.mode = 'local'; setSync(L('ghFail') + ' (' + (e.status || e.message) + ')'); }
    return;
  }
  try {
    var h = window.claude && window.claude.use ? await window.claude.use('db') : null;
    if (!h){ setSync(L('savedLocal')); return; }
    // read everything first; writes are enabled only after (store.db = h), so nothing is written unread
    var t = await h.doc('trainer/state').get(), v = await h.collection('vocab').get(), l = await h.collection('log').get();
    if (t.exists && t.data().cards){ var remote = clone(t.data()); remote.cards = Object.assign(remote.cards, store.dirtyT ? T.cards : {}); T = Object.assign(T, remote); }
    V = {}; v.docs.forEach(function(d){ V[d.id] = clone(d.data()); });
    var all = []; l.docs.forEach(function(d){ (d.data().items || []).forEach(function(x){ all.push(x); }); });
    var mine = LOGNEW.slice(); LOG = all.concat(mine).sort(function(a, b){ return a[0] - b[0]; });
    store.db = h; store.mode = 'db';
    ITEMS_CACHE = null; render(); setSync(L('saved'));
    if (store.dirtyT || LOGNEW.length) flush();
  } catch (e){ store.mode = 'local'; setSync(L('savedLocal')); }
})();
/* the agent rebuilt the page → version.json changed → reload in place (never in the middle of a round) */
function liveReload(){
  var y = sessionStorage.getItem('pl.scroll'); if (y){ sessionStorage.removeItem('pl.scroll'); setTimeout(function(){ scrollTo(0, +y); }, 50); }
  setInterval(async function(){
    try {
      var v = await (await fetch('version.json', {cache: 'no-store'})).json();
      if (v.id && v.id !== (D.build || {}).id && !play){ await flush(); try { sessionStorage.setItem('pl.scroll', String(scrollY)); } catch (e){} location.reload(); }
    } catch (e){}
  }, 2500);
}
window.addEventListener('beforeunload', function(){ if (store.mode === 'api' && (store.dirtyT || LOGNEW.length)){ try { navigator.sendBeacon('/api/trainer', new Blob([JSON.stringify(T)], {type: 'application/json'})); if (LOGNEW.length) navigator.sendBeacon('/api/log', new Blob([JSON.stringify({items: LOGNEW})], {type: 'application/json'})); } catch (e){} } });
/* for the page's own tests and the site's loader: save now, read the current state */
window.polakoFlush = function(){ return flush(); };
window.polakoState = function(){ return {cards: Object.keys(T.cards || {}).length, log: LOG.length, mode: store.mode}; };
