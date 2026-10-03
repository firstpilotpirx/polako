#!/usr/bin/env python3
"""The trainer as an app for the phone's home screen (PWA): its own site, own icon, full screen, offline.

    run pwa.py --dir ~/polako                       # → dist/pwa/ (index.html, manifest, service worker, icons)
    run pwa.py --dir ~/polako --out ~/site/polako   # build into another folder (e.g. a GitHub Pages repo)

Why: a home-screen shortcut to a claude.ai link opens the Claude app (an empty chat), not the page. A page
on its own site does not have that problem. Host the folder on any static hosting over https — e.g. a
GitHub repo named <user>.github.io publishes itself at https://<user>.github.io/ with no settings.

Progress in this mode lives in the phone's browser storage of that site (the page's "this browser" mode);
it does not sync with the claude.ai page or the local server. An installed home-screen app keeps its
storage; the page asks the browser to keep it persistent.

Updates: rebuild and upload the folder again. The service worker fetches the page from the network first
and falls back to its copy offline, so a new version shows up on the next launch with network.
"""
from __future__ import annotations

import argparse
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepio import Fail  # noqa: E402

TOOLS = Path(__file__).resolve().parent
BUNDLED_ICONS = TOOLS.parent / "templates" / "pwa"
ACCENT = "#1f5f74"
BG = "#f3f5f4"

HEAD = """<link rel="manifest" href="manifest.webmanifest">
<link rel="apple-touch-icon" href="icon-180.png">
<link rel="icon" type="image/png" sizes="192x192" href="icon-192.png">
<meta name="theme-color" content="{bg}">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="Polako">
"""

TAIL = """<script>
/* PWA: offline copy + ask the browser to keep this site's storage (progress lives there) */
if ('serviceWorker' in navigator) navigator.serviceWorker.register('sw.js').catch(function(){});
if (navigator.storage && navigator.storage.persist) navigator.storage.persist().catch(function(){});
</script>
"""

SW = """/* Polako service worker: network first for the page (updates arrive on launch), cache as offline fallback. */
const CACHE = 'polako-{build}';
const CORE = ['./', 'index.html', 'manifest.webmanifest', 'icon-180.png', 'icon-192.png', 'icon-512.png'];
self.addEventListener('install', e => {{ e.waitUntil(caches.open(CACHE).then(c => c.addAll(CORE)).then(() => self.skipWaiting())); }});
self.addEventListener('activate', e => {{
  e.waitUntil(caches.keys().then(ks => Promise.all(ks.filter(k => k !== CACHE).map(k => caches.delete(k)))).then(() => self.clients.claim()));
}});
self.addEventListener('fetch', e => {{
  const req = e.request;
  if (req.method !== 'GET') return;
  const page = req.mode === 'navigate' || req.url.endsWith('index.html');
  if (page) {{
    e.respondWith(fetch(req).then(r => {{ const c = r.clone(); caches.open(CACHE).then(x => x.put('index.html', c)); return r; }})
      .catch(() => caches.match('index.html')));
    return;
  }}
  // everything else (icons, fonts): cache first, fill the cache on the way
  e.respondWith(caches.match(req).then(hit => hit || fetch(req).then(r => {{
    if (r && (r.ok || r.type === 'opaque')) {{ const c = r.clone(); caches.open(CACHE).then(x => x.put(req, c)); }}
    return r;
  }}).catch(() => hit)));
}});
"""


def icon(size: int, path: Path) -> None:
    """Regenerates templates/pwa/icon-*.png (needs Pillow; not run by the build). The brand mark: a white dot ring with "P" on the accent colour, full-bleed (iOS rounds the corners)."""
    from PIL import Image, ImageDraw, ImageFont
    s = size * 4
    im = Image.new("RGB", (s, s), ACCENT)
    d = ImageDraw.Draw(im)
    font = None
    for f in ("/usr/share/fonts/opentype/inter/Inter-Bold.otf", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"):
        if Path(f).exists():
            font = ImageFont.truetype(f, int(s * 0.56))
            break
    font = font or ImageFont.load_default()
    d.text((s * 0.5, s * 0.53), "P", fill="#ffffff", font=font, anchor="mm")
    r = s * 0.075
    cx, cy = s * 0.735, s * 0.27
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill="#9fd3e0")
    im.resize((size, size), Image.LANCZOS).save(path, optimize=True)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=".")
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    root = Path(a.dir).expanduser().resolve()
    r = subprocess.run([sys.executable, str(TOOLS / "build_page.py"), "--dir", str(root)], capture_output=True, text=True)
    if r.returncode:
        raise Fail("! build_page.py failed:\n" + (r.stdout + r.stderr)[-2000:])
    src = root / "dist" / "index.html"
    html = src.read_text(encoding="utf-8")
    build = json.loads((root / "dist" / "version.json").read_text()).get("id", "1")
    out = Path(a.out).expanduser().resolve() if a.out else root / "dist" / "pwa"
    out.mkdir(parents=True, exist_ok=True)
    head = HEAD.format(bg=BG)
    if "</title>" in html:
        html = html.replace("</title>", "</title>\n" + head, 1)
    else:
        html = head + html
    html = re.sub(r"<title>[^<]*</title>", "<title>Polako</title>", html, count=1)
    html = html.replace("</body>", TAIL + "</body>", 1) if "</body>" in html else html + TAIL
    (out / "index.html").write_text(html, encoding="utf-8")
    (out / "manifest.webmanifest").write_text(json.dumps({
        "name": "Polako — сербский", "short_name": "Polako", "lang": "sr-Latn",
        "start_url": "./", "scope": "./", "display": "standalone",
        "background_color": BG, "theme_color": BG,
        "icons": [{"src": "icon-192.png", "sizes": "192x192", "type": "image/png"},
                  {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}],
    }, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "sw.js").write_text(SW.format(build=re.sub(r"[^A-Za-z0-9_-]", "", str(build))[:40] or "1"), encoding="utf-8")
    for n in (180, 192, 512):   # bundled (made once by icon(); Pillow is not a plugin dependency)
        shutil.copy(BUNDLED_ICONS / f"icon-{n}.png", out / f"icon-{n}.png")
    (out / ".nojekyll").write_text("")
    shutil.copy(root / "dist" / "version.json", out / "version.json")
    print(f"PWA {out} ({(out / 'index.html').stat().st_size // 1024} KB) — host it over https; on the phone open it in Safari → Share → Add to Home Screen")
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Fail as e:
        print(e, file=sys.stderr)
        sys.exit(2)
