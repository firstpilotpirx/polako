/* ---------- pronunciation: Web Speech API (speechSynthesis) ----------
   Built into the browser: no keys, no network for system voices. A Serbian voice is not on every
   system, so the chain is sr → hr → bs (Croatian and Bosnian voices read Serbian Latin text well;
   the page says which voice it uses). Edge has online sr-RS voices; macOS/iOS have a Croatian one.
   Settings per device (localStorage pl.tts). No voice at all → no 🔊 buttons and no listening side. */
var TTS = {ok: typeof window.speechSynthesis !== 'undefined' && typeof window.SpeechSynthesisUtterance !== 'undefined', voices: []};
function secs(v, d){ v = parseFloat(v); return v >= 0 && v <= 5 ? Math.round(v * 10) / 10 : d; }
var TTS_CFG = (function(c){ c = c && typeof c === 'object' ? c : {}; return {auto: c.auto !== false, sfx: c.sfx !== false, next: c.next !== false, pauseOk: secs(c.pauseOk, 1.6), pauseBad: secs(c.pauseBad, 3), voice: c.voice || '', rate: +c.rate > 0 ? +c.rate : 0.85}; })(lsGet('pl.tts', null));
var SR_CHAIN = ['sr', 'hr', 'bs'];
function ttsLoad(){ try { TTS.voices = speechSynthesis.getVoices() || []; } catch (e){ TTS.voices = []; } }
if (TTS.ok){ ttsLoad(); try { speechSynthesis.addEventListener('voiceschanged', function(){ ttsLoad(); }); } catch (e){} }
function voicesFor(lang){ return TTS.voices.filter(function(v){ return (v.lang || '').toLowerCase().replace('_', '-').indexOf(lang) === 0; }); }
function bestOf(vs){
  function score(v){ var n = v.name || '', s = 0; if (/enhanced|premium|natural|neural|online|google/i.test(n)) s += 4; if (v.default) s += 1; return s; }
  return vs.slice().sort(function(a, b){ return score(b) - score(a); })[0] || null;
}
function ttsVoice(lang){
  if (lang === 'sr'){
    if (TTS_CFG.voice){ var ch = TTS.voices.filter(function(v){ return v.name === TTS_CFG.voice; })[0]; if (ch) return ch; }
    for (var i = 0; i < SR_CHAIN.length; i++){ var v = bestOf(voicesFor(SR_CHAIN[i])); if (v) return v; }
    return null;
  }
  return bestOf(voicesFor(lang));
}
function srVoiceInfo(){ var v = ttsVoice('sr'); if (!v) return null; var l = (v.lang || '').slice(0, 2).toLowerCase(); return {name: v.name, lang: v.lang, fallback: l !== 'sr'}; }
function canSpeak(lang){ return TTS.ok && (!TTS.voices.length ? false : !!ttsVoice(lang)); }
function speak(text, lang, done){
  var fired = false; function fin(){ if (!fired){ fired = true; if (done) done(); } }
  if (!TTS.ok || !text){ fin(); return false; }
  if (!TTS.voices.length) ttsLoad();
  var v = ttsVoice(lang);
  if (!v){ fin(); return false; }
  try {
    speechSynthesis.cancel();
    var s = String(text).replace(/\s*\(.*?\)\s*/g, ' ').replace(/[{}]/g, '').trim();
    var u = new SpeechSynthesisUtterance(s);
    u.lang = v.lang; u.voice = v; u.rate = lang === 'sr' ? TTS_CFG.rate : 1;
    u.onend = fin; u.onerror = fin;
    var t0 = Date.now();
    setTimeout(function wait(){ var busy = false; try { busy = speechSynthesis.speaking; } catch (e){}
      if (busy && Date.now() - t0 < 20000) setTimeout(wait, 200); else fin(); }, (900 + 85 * s.length) / (u.rate || 1));
    speechSynthesis.speak(u); return true;
  } catch (e){ fin(); return false; }
}
var SFX = null;
function sfx(kind){
  if (!TTS_CFG.sfx) return;
  try {
    var AC = window.AudioContext || window.webkitAudioContext; if (!AC) return;
    SFX = SFX || new AC(); if (SFX.state === 'suspended') SFX.resume();
    var t0 = SFX.currentTime + 0.01;
    function tone(type, f1, f2, start, dur, vol){
      var o = SFX.createOscillator(), g = SFX.createGain();
      o.type = type; o.frequency.setValueAtTime(f1, start); if (f2) o.frequency.linearRampToValueAtTime(f2, start + dur);
      g.gain.setValueAtTime(0.0001, start); g.gain.exponentialRampToValueAtTime(vol, start + 0.015); g.gain.exponentialRampToValueAtTime(0.0001, start + dur);
      o.connect(g); g.connect(SFX.destination); o.start(start); o.stop(start + dur + 0.02);
    }
    if (kind === 'ok'){ tone('sine', 880, 0, t0, 0.12, 0.12); tone('sine', 1320, 0, t0 + 0.1, 0.18, 0.12); }
    else { tone('sawtooth', 150, 110, t0, 0.32, 0.09); tone('square', 75, 0, t0, 0.32, 0.04); }
  } catch (e){}
}
function spk(text, lang){
  if (!text || !canSpeak(lang)) return document.createTextNode('');
  var b = btn('spk', '🔊', function(e){ e.preventDefault(); e.stopPropagation(); speak(text, lang); });
  b.title = L('ttsPlay'); b.setAttribute('aria-label', L('ttsPlay') + ': ' + text);
  return b;
}
function ttsSave(){ lsSet('pl.tts', TTS_CFG); }
function pauseSlider(key, label){
  var lb = el('label', 'tts-pause'), v = el('b', null, TTS_CFG[key].toFixed(1) + ' ' + L('sec')), r = el('input');
  r.type = 'range'; r.min = 0; r.max = 5; r.step = 0.1; r.value = TTS_CFG[key]; r.setAttribute('aria-label', label);
  r.oninput = function(){ TTS_CFG[key] = +r.value; v.textContent = TTS_CFG[key].toFixed(1) + ' ' + L('sec'); ttsSave(); };
  lb.appendChild(document.createTextNode(label + ' ')); lb.appendChild(r); lb.appendChild(v); return lb;
}
function ttsControls(){
  var box = el('div', 'tts-opts');
  var info = srVoiceInfo();
  box.appendChild(el('p', 'meta', !TTS.ok || !info ? L('ttsNoVoice') : info.fallback ? L('ttsFallback').replace('{v}', info.name + ' · ' + info.lang) : L('ttsVoiceOk').replace('{v}', info.name)));
  [['auto', L('ttsAuto')], ['sfx', L('ttsSfx')], ['next', L('ttsNext')]].forEach(function(x){
    var lb = el('label'), c = el('input'); c.type = 'checkbox'; c.checked = TTS_CFG[x[0]];
    c.onchange = function(){ TTS_CFG[x[0]] = c.checked; ttsSave(); if (x[0] === 'sfx' && c.checked) sfx('ok'); };
    lb.appendChild(c); lb.appendChild(document.createTextNode(' ' + x[1])); box.appendChild(lb);
  });
  var pl = el('div', 'tts-pauses'); pl.appendChild(pauseSlider('pauseOk', L('ttsPauseOk'))); pl.appendChild(pauseSlider('pauseBad', L('ttsPauseBad'))); box.appendChild(pl);
  var vl = el('label', null, L('ttsVoice') + ' '), vs = el('select');
  function fill(){ vs.innerHTML = ''; var o0 = el('option', null, L('ttsAny')); o0.value = ''; vs.appendChild(o0);
    TTS.voices.filter(function(v){ return /^(sr|hr|bs)/i.test(v.lang || ''); }).forEach(function(v){ var o = el('option', null, v.name + ' · ' + v.lang); o.value = v.name; o.selected = v.name === TTS_CFG.voice; vs.appendChild(o); }); }
  fill(); try { speechSynthesis.addEventListener('voiceschanged', fill); } catch (e){}
  vs.onchange = function(){ TTS_CFG.voice = vs.value; ttsSave(); speak('Dobar dan, kako ste?', 'sr'); }; vl.appendChild(vs); box.appendChild(vl);
  var rl = el('label', null, L('ttsRate') + ' '), rs = el('select');
  [[0.7, '0.7×'], [0.85, '0.85×'], [1, '1×'], [1.15, '1.15×']].forEach(function(x){ var o = el('option', null, x[1]); o.value = x[0]; o.selected = Math.abs(x[0] - TTS_CFG.rate) < 0.01; rs.appendChild(o); });
  rs.onchange = function(){ TTS_CFG.rate = +rs.value; ttsSave(); speak('Polako, polako.', 'sr'); }; rl.appendChild(rs); box.appendChild(rl);
  return box;
}
