#!/usr/bin/env python3
"""The public site: the trainer without personal data (GitHub Pages of the polako repository).

    run site.py --out docs            # → docs/index.html, docs/packs/<pack>.json, icons, manifest

The site asks each visitor to connect their own private GitHub repository (words + progress, shared by all their
devices) or to try a ready set with progress kept in the browser. Everything personal stays in the person's
repository; the site is the same for everybody. Rebuild it after any change in templates/ or data/packs/:
`bash tools/check_all.sh` checks it, `bash tools/release.sh` rebuilds it with the release.

The packs are prebuilt here (pack.py install into a temporary folder → the same data the page gets), so a new
person can start right from the site and the set is copied into their repository on connect.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build_page import PORTAL, app_js, deck_json, render_page, ui_strings  # noqa: E402
from prepio import BUNDLED, REPO, read_yaml, write_text  # noqa: E402

SITE = REPO / "templates" / "site"
ICONS = REPO / "templates" / "pwa"

HEAD = """<link rel="manifest" href="manifest.webmanifest">
<link rel="apple-touch-icon" href="icon-180.png">
<link rel="icon" type="image/png" sizes="192x192" href="icon-192.png">
<meta name="theme-color" content="#f3f5f4">
<meta name="apple-mobile-web-app-capable" content="yes">
<meta name="mobile-web-app-capable" content="yes">
<meta name="apple-mobile-web-app-status-bar-style" content="default">
<meta name="apple-mobile-web-app-title" content="Polako">
"""


def build_pack(name: str, out: Path) -> dict:
    with tempfile.TemporaryDirectory() as td:
        r = subprocess.run([sys.executable, str(Path(__file__).parent / "pack.py"), "--dir", td, "install", name], capture_output=True, text=True)
        if r.returncode:
            raise SystemExit(f"! pack {name}: {(r.stdout + r.stderr)[-1500:]}")
        data = deck_json(Path(td))
    write_text(out / "packs" / f"{name}.json", json.dumps(data, ensure_ascii=False, separators=(",", ":")) + "\n")
    meta = read_yaml(BUNDLED / "packs" / f"{name}.yaml", {}) or {}
    return {"name": name, "title": meta.get("title", name), "file": f"packs/{name}.json", "words": len(data["deck"]["words"])}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    out = Path(a.out).expanduser().resolve()
    out.mkdir(parents=True, exist_ok=True)
    packs = [build_pack(p.stem, out) for p in sorted((BUNDLED / "packs").glob("*.yaml"))]
    ui = ui_strings(Path("/nonexistent"), "ru")
    boot = ("window.POLAKO_UI = " + json.dumps(ui, ensure_ascii=False) + ";\nwindow.POLAKO_PACKS = " + json.dumps(packs, ensure_ascii=False) + ";\n"
            "window.__polakoStart = function(){\n" + app_js() + "\n};\n" + (SITE / "loader.js").read_text(encoding="utf-8"))
    page = render_page("", boot.replace("</script", "<\\/script"), "ru", "Polako", HEAD)
    write_text(out / "index.html", page)
    write_text(out / "manifest.webmanifest", json.dumps({
        "name": "Polako — сербские слова", "short_name": "Polako", "lang": "ru", "start_url": "./", "scope": "./",
        "display": "standalone", "background_color": "#f3f5f4", "theme_color": "#f3f5f4",
        "icons": [{"src": "icon-192.png", "sizes": "192x192", "type": "image/png"},
                  {"src": "icon-512.png", "sizes": "512x512", "type": "image/png", "purpose": "any maskable"}]}, ensure_ascii=False, indent=1) + "\n")
    for n in (180, 192, 512):
        shutil.copy(ICONS / f"icon-{n}.png", out / f"icon-{n}.png")
    write_text(out / ".nojekyll", "")
    print(f"SITE {out} ({(out / 'index.html').stat().st_size // 1024} KB) packs: " + ", ".join(f"{p['name']} ({p['words']} words)" for p in packs))
    return 0


if __name__ == "__main__":
    sys.exit(main())
