/* ---------- the public site: choose where words and progress live, then start the page ----------
   Two kinds of storage, switchable any time in the trainer's settings ("Где хранить прогресс"):
     browser — nothing to set up: the chosen set and all progress live in this browser (IndexedDB, asked to be
               persistent; localStorage as a fallback). One device.
     github  — the person's private repository (owner/name + a fine-grained token with "Contents: read and
               write" on that repository only): words and progress shared by all their devices. Connecting moves
               the progress made in the browser into the repository.
   The choice is kept in localStorage (pl.storage); the token never leaves this browser except to api.github.com.
   The site itself holds no personal data. */
(function(){
  var KEY = 'pl.storage', U = window.POLAKO_UI || {};
  function L(k){ return U[k] != null ? U[k] : k; }
  function cfgGet(){
    try {
      var c = JSON.parse(localStorage.getItem(KEY) || 'null');
      if (!c){ var old = JSON.parse(localStorage.getItem('pl.gh') || 'null'); if (old && old.repo) c = {type: 'github', repo: old.repo, token: old.token}; }
      return c;
    } catch (e){ return null; }
  }
  function cfgSet(v){ try { if (v) localStorage.setItem(KEY, JSON.stringify(v)); else localStorage.removeItem(KEY); localStorage.removeItem('pl.gh'); } catch (e){} }
  window.polakoStorage = {get: cfgGet, set: cfgSet};
  function $(id){ return document.getElementById(id); }
  function el(tag, cls, text){ var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  function start(json){ $('pl-data').textContent = json; window.__polakoStart(); }

  /* the set for browser mode: the site's current version of the pack (fixes arrive), the stored copy offline */
  async function browserDeck(cfg){
    var IDB = window.PolakoIDB, saved = null;
    try { saved = IDB ? await IDB.get('deck') : null; } catch (e){}
    var pack = (window.POLAKO_PACKS || []).filter(function(p){ return 'pack:' + p.name === cfg.source; })[0];
    if (pack){
      try {
        var r = await fetch(pack.file, {cache: 'no-store'});
        if (r.ok){ var t = await r.text(); try { if (IDB) await IDB.set('deck', t); } catch (e){} return t; }
      } catch (e){}
    }
    return saved;
  }
  async function gh(cfg, path){
    return fetch('https://api.github.com/repos/' + cfg.repo + path, {cache: 'no-store',
      headers: {'Authorization': 'Bearer ' + cfg.token, 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}});
  }
  function b64dec(s){ return decodeURIComponent(escape(atob(String(s).replace(/\s/g, '')))); }
  async function githubDeck(cfg){
    var rr = await gh(cfg, '');   // a private repository without access answers 404 too
    if (!rr.ok){ var e0 = new Error(String(rr.status)); e0.status = rr.status === 404 ? 'repo' : rr.status; throw e0; }
    var r = await gh(cfg, '/contents/deck.json');
    if (r.status === 404) return null;
    if (!r.ok){ var e = new Error(String(r.status)); e.status = r.status; throw e; }
    var j = await r.json();
    if (j.content == null || (j.encoding === 'none' && j.size)){ var b = await (await gh(cfg, '/git/blobs/' + j.sha)).json(); return b64dec(b.content); }
    return b64dec(j.content);
  }
  window.polakoGithubError = function(e){
    return e.status === 401 ? L('setupBadToken') : e.status === 'repo' || e.status === 403 ? L('setupNoAccess') : L('setupFail') + ' (' + (e.status || e.message) + ')';
  };

  function screen(build){
    var main = $('main'); main.innerHTML = ''; var c = el('div', 'card setup'); build(c); main.appendChild(c);
    var s = $('summary'); if (s) s.hidden = true;
  }
  function welcome(err){
    screen(function(c){
      c.appendChild(el('h2', null, L('setupTitle')));
      c.appendChild(el('p', null, L('setupIntro')));
      if (err) c.appendChild(el('p', 'setup-err', err));
      c.appendChild(el('h3', null, L('setupStartBrowser')));
      c.appendChild(el('p', 'meta', L('setupStartBrowserNote')));
      var box = el('div', 'setup-packs');
      (window.POLAKO_PACKS || []).forEach(function(p){
        var b = el('button', 'btn primary', p.title + ' — ' + p.words + ' ' + L('setupWords')); b.type = 'button';
        b.onclick = function(){ cfgSet({type: 'browser', source: 'pack:' + p.name}); boot(); }; box.appendChild(b);
      });
      c.appendChild(box);
      c.appendChild(el('h3', null, L('setupStartGithub')));
      c.appendChild(el('p', 'meta', L('setupStartGithubNote')));
      c.appendChild(window.polakoGithubForm(function(cfg){ cfgSet(cfg); boot(); }));
    });
  }
  /* the GitHub form with the step-by-step help; used here and in the trainer's settings */
  window.polakoGithubForm = function(onConnect, prefill){
    var wrap = el('div', 'gh-setup');
    var steps = el('ol', 'gh-steps');
    [['ghStep1', 'https://github.com/new'], ['ghStep2', 'https://github.com/settings/personal-access-tokens/new'], ['ghStep3', null]].forEach(function(s){
      var li = el('li'); li.appendChild(document.createTextNode(L(s[0]) + ' '));
      if (s[1]){ var a = el('a', null, s[1].replace('https://', '')); a.href = s[1]; a.target = '_blank'; a.rel = 'noopener'; li.appendChild(a); }
      steps.appendChild(li);
    });
    var det = el('details', 'gh-help'); det.appendChild(el('summary', null, L('ghHowTo'))); det.appendChild(steps);
    var more = el('p', 'meta'); var a2 = el('a', null, L('setupHelp')); a2.href = 'https://github.com/firstpilotpirx/polako#2-синхронизация-между-устройствами-через-github'; a2.target = '_blank'; a2.rel = 'noopener'; more.appendChild(a2); det.appendChild(more);
    wrap.appendChild(det);
    var f = el('form', 'setup-form');
    var r1 = el('label', null, L('setupRepo')), i1 = el('input'); i1.placeholder = L('setupRepoPh'); i1.autocapitalize = 'off'; i1.spellcheck = false; i1.value = (prefill || {}).repo || ''; r1.appendChild(i1);
    var r2 = el('label', null, L('setupToken')), i2 = el('input'); i2.type = 'password'; i2.placeholder = 'github_pat_…'; i2.autocomplete = 'off'; r2.appendChild(i2);
    var go = el('button', 'btn', L('setupConnect')); go.type = 'submit';
    f.appendChild(r1); f.appendChild(r2); f.appendChild(go);
    f.onsubmit = function(ev){ ev.preventDefault();
      var repo = i1.value.trim().replace(/^https?:\/\/github\.com\//, '').replace(/\.git$/, '').replace(/\/$/, ''), tok = i2.value.trim();
      if (!/^[\w.-]+\/[\w.-]+$/.test(repo)){ i1.focus(); return; } if (!tok){ i2.focus(); return; }
      go.disabled = true; go.textContent = L('ghConnecting');
      Promise.resolve(onConnect({type: 'github', repo: repo, token: tok})).catch(function(){}).then(function(){ go.disabled = false; go.textContent = L('setupConnect'); });
    };
    wrap.appendChild(f);
    return wrap;
  };

  async function boot(){
    var cfg = cfgGet();
    window.POLAKO_SITE = true;
    if (!cfg){ welcome(); return; }
    screen(function(c){ c.appendChild(el('p', 'meta', L(cfg.type === 'github' ? 'ghLoading' : 'loading'))); });
    if (cfg.type === 'browser'){
      var t = await browserDeck(cfg);
      if (!t){ cfgSet(null); welcome(L('setupFail')); return; }
      window.POLAKO_STORE = cfg; start(t); return;
    }
    try {
      var json = await githubDeck(cfg);
      if (json == null){   // an empty repository: the person's current set (from the browser) or a pack goes there on connect
        var local = null; try { local = window.PolakoIDB ? await window.PolakoIDB.get('deck') : null; } catch (e){}
        if (!local){ var p = (window.POLAKO_PACKS || [])[0]; if (p){ var r = await fetch(p.file, {cache: 'no-store'}); local = await r.text(); } }
        window.POLAKO_STORE = cfg; window.POLAKO_GH = cfg; window.POLAKO_GH_EMPTY = true; start(local); return;
      }
      try { if (window.PolakoIDB) await window.PolakoIDB.set('deck', json); } catch (e){}   // the offline copy
      window.POLAKO_STORE = cfg; window.POLAKO_GH = cfg; start(json);
    } catch (e){
      if (e.status === 401 || e.status === 403 || e.status === 'repo'){ welcome(window.polakoGithubError(e)); return; }
      // no network: the last copy from this browser; the page saves here and syncs when GitHub answers again
      var copy = null; try { copy = window.PolakoIDB ? await window.PolakoIDB.get('deck') : null; } catch (e2){}
      if (!copy){ welcome(window.polakoGithubError(e)); return; }
      window.POLAKO_STORE = cfg; window.POLAKO_GH = cfg; start(copy);
    }
  }
  boot();
})();
