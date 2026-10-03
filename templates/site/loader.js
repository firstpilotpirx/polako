/* ---------- the public site: connect the person's own data, then start the page ----------
   The site holds no personal data. On first visit the person connects a private GitHub repository
   (owner/name + a fine-grained token, "Contents: read and write" on that repository only). Both are kept in this
   browser (localStorage pl.gh) and sent only to api.github.com. Without a repository the site can be tried with a
   ready set; progress then stays in this browser. */
(function(){
  var KEY = 'pl.gh', U = window.POLAKO_UI || {};
  function L(k){ return U[k] != null ? U[k] : k; }
  function lsGet(){ try { return JSON.parse(localStorage.getItem(KEY) || 'null'); } catch (e){ return null; } }
  function lsSet(v){ try { if (v) localStorage.setItem(KEY, JSON.stringify(v)); else localStorage.removeItem(KEY); } catch (e){} }
  function $(id){ return document.getElementById(id); }
  function el(tag, cls, text){ var e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; }
  function start(json){ $('pl-data').textContent = json; window.__polakoStart(); }
  window.polakoDisconnect = function(){ lsSet(null); location.reload(); };

  async function gh(cfg, path, opt){
    opt = opt || {};
    return fetch('https://api.github.com/repos/' + cfg.repo + path, {method: opt.method || 'GET', cache: 'no-store',
      headers: {'Authorization': 'Bearer ' + cfg.token, 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'},
      body: opt.body ? JSON.stringify(opt.body) : undefined});
  }
  function b64dec(s){ return decodeURIComponent(escape(atob(String(s).replace(/\s/g, '')))); }
  function b64enc(s){ return btoa(unescape(encodeURIComponent(s))); }
  async function readDeck(cfg){
    var rr = await gh(cfg, '');   // a private repository without access answers 404 too
    if (!rr.ok){ var e0 = new Error(String(rr.status)); e0.status = rr.status === 404 ? 'repo' : rr.status; throw e0; }
    var r = await gh(cfg, '/contents/deck.json');
    if (r.status === 404) return null;
    if (!r.ok){ var e = new Error(String(r.status)); e.status = r.status; throw e; }
    var j = await r.json();
    if (j.content == null || (j.encoding === 'none' && j.size)){ var b = await (await gh(cfg, '/git/blobs/' + j.sha)).json(); return b64dec(b.content); }
    return b64dec(j.content);
  }

  function screen(build){
    var main = $('main'); main.innerHTML = ''; var c = el('div', 'card setup'); build(c); main.appendChild(c);
    var s = $('summary'); if (s) s.hidden = true;
  }
  function packButtons(box, onPick){
    (window.POLAKO_PACKS || []).forEach(function(p){
      var b = el('button', 'btn', p.title + ' — ' + p.words + ' ' + L('setupWords')); b.type = 'button';
      b.onclick = function(){ onPick(p, b); }; box.appendChild(b);
    });
  }
  async function packJSON(p){ var r = await fetch(p.file, {cache: 'no-store'}); if (!r.ok) throw new Error(p.file + ' ' + r.status); return r.text(); }

  function setupScreen(err){
    screen(function(c){
      c.appendChild(el('h2', null, L('setupTitle')));
      c.appendChild(el('p', null, L('setupIntro')));
      if (err) c.appendChild(el('p', 'setup-err', err));
      var f = el('form', 'setup-form');
      var r1 = el('label', null, L('setupRepo')), i1 = el('input'); i1.placeholder = 'owner/polako-data'; i1.autocapitalize = 'off'; i1.spellcheck = false; i1.value = (lsGet() || {}).repo || ''; r1.appendChild(i1);
      var r2 = el('label', null, L('setupToken')), i2 = el('input'); i2.type = 'password'; i2.placeholder = 'github_pat_…'; i2.autocomplete = 'off'; r2.appendChild(i2);
      var go = el('button', 'btn primary', L('setupConnect')); go.type = 'submit';
      f.appendChild(r1); f.appendChild(r2); f.appendChild(go);
      f.onsubmit = function(ev){ ev.preventDefault(); var repo = i1.value.trim().replace(/^https?:\/\/github\.com\//, '').replace(/\.git$/, '').replace(/\/$/, ''), tok = i2.value.trim();
        if (!/^[\w.-]+\/[\w.-]+$/.test(repo) || !tok) return; lsSet({repo: repo, token: tok}); boot(); };
      c.appendChild(f);
      var help = el('p', 'meta'); var a = el('a', null, L('setupHelp')); a.href = 'https://github.com/firstpilotpirx/polako#readme'; a.target = '_blank'; a.rel = 'noopener'; help.appendChild(a); c.appendChild(help);
      c.appendChild(el('h3', null, L('setupTry')));
      c.appendChild(el('p', 'meta', L('setupTryNote')));
      var box = el('div', 'setup-packs'); packButtons(box, async function(p){ start(await packJSON(p)); }); c.appendChild(box);
    });
  }
  function emptyRepoScreen(cfg){
    screen(function(c){
      c.appendChild(el('h2', null, L('setupEmpty')));
      c.appendChild(el('p', null, L('setupEmptyNote').replace('{repo}', cfg.repo)));
      var box = el('div', 'setup-packs');
      packButtons(box, async function(p, b){
        b.disabled = true; b.textContent = L('setupCreating');
        var json = await packJSON(p);
        var put = await gh(cfg, '/contents/deck.json', {method: 'PUT', body: {message: 'Polako: ' + p.title, content: b64enc(json)}});
        if (!put.ok){ setupScreen(L('setupFail') + ' (' + put.status + ')'); return; }
        await gh(cfg, '/contents/polako.json', {method: 'PUT', body: {message: 'Polako: data repository', content: b64enc(JSON.stringify({kind: 'polako-data', version: 1}, null, 1) + '\n')}});
        start(json);
      });
      c.appendChild(box);
      var x = el('button', 'linkbtn', L('setupOther')); x.type = 'button'; x.onclick = function(){ lsSet(null); setupScreen(); }; c.appendChild(x);
    });
  }
  async function boot(){
    var cfg = lsGet();
    if (!cfg){ setupScreen(); return; }
    screen(function(c){ c.appendChild(el('p', 'meta', L('ghLoading'))); });
    try {
      var json = await readDeck(cfg);
      window.POLAKO_GH = cfg;
      if (json == null){ emptyRepoScreen(cfg); return; }
      start(json);
    } catch (e){
      setupScreen(e.status === 401 ? L('setupBadToken') : e.status === 'repo' || e.status === 403 ? L('setupNoAccess') : L('setupFail') + ' (' + (e.status || e.message) + ')');
    }
  }
  boot();
})();
