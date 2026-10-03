/* ---------- browser storage for the public site: IndexedDB key-value (database "polako", store "kv") ----------
   Holds the chosen set ("deck") and the progress ("progress": {T, V, LOG}). IndexedDB keeps much more than
   localStorage and the browser is asked to keep it persistent (navigator.storage.persist). */
window.PolakoIDB = (function(){
  if (!window.indexedDB) return null;
  var dbp = null;
  function open(){
    if (!dbp) dbp = new Promise(function(res, rej){
      var r = indexedDB.open('polako', 1);
      r.onupgradeneeded = function(){ r.result.createObjectStore('kv'); };
      r.onsuccess = function(){ res(r.result); }; r.onerror = function(){ rej(r.error); };
    });
    return dbp;
  }
  function tx(mode, fn){
    return open().then(function(db){ return new Promise(function(res, rej){
      var t = db.transaction('kv', mode), req = fn(t.objectStore('kv'));
      t.oncomplete = function(){ res(req && 'result' in req ? req.result : undefined); };
      t.onerror = function(){ rej(t.error); }; t.onabort = function(){ rej(t.error); };
    }); });
  }
  try { if (navigator.storage && navigator.storage.persist) navigator.storage.persist(); } catch (e){}
  return {
    get: function(k){ return tx('readonly', function(s){ return s.get(k); }); },
    set: function(k, v){ return tx('readwrite', function(s){ return s.put(v, k); }); },
    del: function(k){ return tx('readwrite', function(s){ return s.delete(k); }); }
  };
})();
