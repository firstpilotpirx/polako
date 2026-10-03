/* ---------- storage in the person's own GitHub repository (the public site: firstpilotpirx.github.io/polako) ----------
   The site is the same page without personal data. Words and progress live in a private repository the person
   connects once per device (repository name + a fine-grained token with "Contents: read and write" on that one
   repository; both stay in this browser's localStorage, key pl.gh). Layout of the data repository:
     deck.json                    the page data: words, phrases, situations (built by tools/build_page.py)
     prep/trainer-state.json      FSRS cards and settings          ← same files as the local mode,
     prep/vocab-state.json        "I know" marks                     so the Claude plugin reads them as is
     prep/log/YYYY-MM.json        every answer, one file per month
   Saving is batched into one commit: after a pause in answering (45 s), at most every 2 min while answering,
   when a round ends and when the page is hidden. Before writing, the latest version is read and merged:
   cards — the side reviewed last wins; marks — the newer record; answers — union. So two devices never
   overwrite each other. On return to the page the newest state is pulled again. */
var GH = (function(){
  var cfg = window.POLAKO_GH || null, API = 'https://api.github.com', branch = null;
  function on(){ return !!(cfg && cfg.repo && cfg.token); }
  function b64enc(s){ return btoa(unescape(encodeURIComponent(s))); }
  function b64dec(s){ return decodeURIComponent(escape(atob(String(s).replace(/\s/g, '')))); }
  async function req(method, path, body){
    var r = await fetch(API + path, {method: method, cache: 'no-store', headers: {'Authorization': 'Bearer ' + cfg.token, 'Accept': 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28'}, body: body ? JSON.stringify(body) : undefined});
    if (r.status === 404) return null;
    if (!r.ok){ var e = new Error('github ' + r.status); e.status = r.status; throw e; }
    return r.status === 204 ? {} : r.json();
  }
  function repo(p){ return '/repos/' + cfg.repo + p; }
  async function getBranch(){ if (!branch){ var r = await req('GET', repo('')); if (!r) { var e = new Error('no repo'); e.status = 404; throw e; } branch = r.default_branch || 'main'; } return branch; }
  // a file's text (null when absent); files over 1 MB come through the blob API
  async function read(path, ref){
    var r = await req('GET', repo('/contents/' + path + (ref ? '?ref=' + ref : '')));
    if (!r || Array.isArray(r)) return null;
    if (r.content == null || (r.encoding === 'none' && r.size)){ var bl = await req('GET', repo('/git/blobs/' + r.sha)); return bl ? b64dec(bl.content) : null; }
    return b64dec(r.content);
  }
  async function readJSON(path, ref, dflt){ var t = await read(path, ref); if (t == null) return dflt; try { return JSON.parse(t); } catch (e){ return dflt; } }
  async function list(path, ref){ var r = await req('GET', repo('/contents/' + path + (ref ? '?ref=' + ref : ''))); return Array.isArray(r) ? r : []; }
  // first file of an empty repository: the contents API creates the first commit
  async function putFile(path, text, msg){
    var cur = await req('GET', repo('/contents/' + path));
    return req('PUT', repo('/contents/' + path), {message: msg, content: b64enc(text), sha: cur && cur.sha || undefined});
  }
  // several files in one commit; null when the branch moved meanwhile (the caller re-reads and retries)
  async function commit(files, msg){
    var br = await getBranch();
    var ref = await req('GET', repo('/git/ref/heads/' + br));
    if (!ref){   // empty repository
      for (var i = 0; i < files.length; i++) await putFile(files[i].path, files[i].text, msg);
      return true;
    }
    var head = ref.object.sha, c = await req('GET', repo('/git/commits/' + head));
    var tree = await req('POST', repo('/git/trees'), {base_tree: c.tree.sha, tree: files.map(function(f){ return {path: f.path, mode: '100644', type: 'blob', content: f.text}; })});
    var nc = await req('POST', repo('/git/commits'), {message: msg, tree: tree.sha, parents: [head]});
    try { await req('PATCH', repo('/git/refs/heads/' + br), {sha: nc.sha, force: false}); }
    catch (e){ if (e.status === 422 || e.status === 409) return null; throw e; }
    return true;
  }
  async function headSha(){ var br = await getBranch(), ref = await req('GET', repo('/git/ref/heads/' + br)); return ref ? ref.object.sha : null; }
  return {on: on, cfg: function(){ return cfg; }, read: read, readJSON: readJSON, list: list, commit: commit, putFile: putFile, headSha: headSha};
})();

/* ---------- merging two copies of the progress (this device and the repository) ---------- */
function mergeCards(a, b){
  var out = {}, k;
  for (k in a) out[k] = a[k];
  for (k in b){ var x = out[k], y = b[k]; if (!x || (y.last || 0) > (x.last || 0) || ((y.last || 0) === (x.last || 0) && (y.reps || 0) > (x.reps || 0))) out[k] = y; }
  return out;
}
function mergeT(local, remote){
  if (!remote || !remote.cards) return local;
  if (local.reset && local.reset > (remote.updated || 0)) return local;   // a reset made here wins over older progress
  if (remote.reset && remote.reset > (local.updated || 0)) return Object.assign({}, remote);
  var newer = (remote.updated || 0) > (local.updated || 0) ? remote : local;
  var out = Object.assign({}, local, newer);
  out.cards = mergeCards(local.cards || {}, remote.cards || {});
  out.hist = Object.assign({}, remote.hist || {}, local.hist || {});
  return out;
}
function mergeV(local, remote){
  var out = Object.assign({}, remote || {});
  for (var k in local){ var x = out[k], y = local[k]; if (!x || (y && (y.at || 0) >= (x.at || 0))) out[k] = y; }
  return out;
}
function mergeLog(a, b){
  var seen = {}, out = [];
  a.concat(b).forEach(function(x){ var k = x[0] + '|' + x[1]; if (!seen[k]){ seen[k] = 1; out.push(x); } });
  return out.sort(function(x, y){ return x[0] - y[0]; });
}
function monthKey(ts){ var d = new Date(ts); return d.getFullYear() + '-' + String(d.getMonth() + 1).padStart(2, '0'); }

/* read everything from the repository and merge it into this device's copy */
async function ghPull(){
  var ref = await GH.headSha();
  var t = await GH.readJSON('prep/trainer-state.json', ref, null);
  var v = await GH.readJSON('prep/vocab-state.json', ref, null);
  var files = (await GH.list('prep/log', ref)).filter(function(f){ return /\.json$/.test(f.name); });
  var all = [];
  for (var i = 0; i < files.length; i++){ var part = await GH.readJSON('prep/log/' + files[i].name, ref, []); if (Array.isArray(part)) all = all.concat(part); }
  if (t) T = mergeT(T, t);
  if (v) V = mergeV(V, v);
  LOG = mergeLog(LOG, all);
  ITEMS_CACHE = null;
}
/* write this device's changes as one commit (re-reading and merging if another device wrote meanwhile) */
async function ghPush(items){
  for (var attempt = 0; attempt < 3; attempt++){
    var ref = await GH.headSha();
    var rt = await GH.readJSON('prep/trainer-state.json', ref, null), rv = await GH.readJSON('prep/vocab-state.json', ref, null);
    var t = mergeT(T, rt), v = mergeV(V, rv), files = [];
    if (store.dirtyT || !rt){ T = t; files.push({path: 'prep/trainer-state.json', text: JSON.stringify(t)}); }
    if (store.dirtyV || !rv){ V = v; files.push({path: 'prep/vocab-state.json', text: JSON.stringify(v, null, 1)}); }
    var months = {};
    items.forEach(function(x){ (months[monthKey(x[0])] = months[monthKey(x[0])] || []).push(x); });
    for (var m in months){ var old = await GH.readJSON('prep/log/' + m + '.json', ref, []); files.push({path: 'prep/log/' + m + '.json', text: JSON.stringify(mergeLog(Array.isArray(old) ? old : [], months[m]))}); }
    if (!files.length) return;
    var n = items.length, msg = 'Polako: ' + (n ? L('ghAnswers') + ' ' + n : L('ghProgress')) + ' · ' + new Date().toLocaleString(TRL);
    if (await GH.commit(files, msg)) return;
  }
  throw new Error('github: the branch keeps moving');
}
