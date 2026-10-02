#!/usr/bin/env python3
"""Local server for the Polako page: serves dist/ and writes the page's progress into the folder.

    run serve.py --dir ~/polako            # start in background (or find the one already running)
    run serve.py --dir ~/polako --stop     # stop
    run serve.py --dir ~/polako --foreground

Prints `POLAKO_URL http://localhost:<port>/` — the hub opens it in the built-in browser and gives
it to the person for their own browser. Binds to 127.0.0.1 only and accepts writes from localhost only.

API:
    GET  /api/ping           {"ok":true,"dir":...}
    GET  /api/trainer        prep/trainer-state.json   (FSRS cards per side, goal, retention, history)
    POST /api/trainer        write it (a state with fewer cards than on disk is refused: no silent loss)
    GET  /api/log            prep/review-log.json      (every answer: [ts, key, grade, ms, elapsed, s])
    POST /api/log            {items:[…]} appended, duplicates (same ts and key) skipped
    GET  /api/vocab          prep/vocab-state.json     ("I know" check)
    POST /api/vocab          write it
    POST /api/inbox          append a record to prep/inbox.json (a text sent for analysis, hard words)
The page polls /version.json and reloads itself when the build changes.
"""
from __future__ import annotations

import argparse
import json
import os
import signal
import socket
import subprocess
import sys
import time
import urllib.request
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

DEFAULT_PORT = 8790
MAX_BODY = 8 * 1024 * 1024
DOCS = {"trainer": "trainer-state.json", "vocab": "vocab-state.json"}


def make_handler(root: Path):
    dist, prep = root / "dist", root / "prep"

    class H(SimpleHTTPRequestHandler):
        def __init__(self, *a, **kw):
            super().__init__(*a, directory=str(dist), **kw)

        def log_message(self, *a):  # quiet
            pass

        extensions_map = {**SimpleHTTPRequestHandler.extensions_map,
                          ".html": "text/html; charset=utf-8", ".json": "application/json; charset=utf-8",
                          ".md": "text/markdown; charset=utf-8", ".txt": "text/plain; charset=utf-8"}

        def end_headers(self):
            self.send_header("Cache-Control", "no-store")
            super().end_headers()

        def _json(self, code, obj):
            body = json.dumps(obj, ensure_ascii=False).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def _local(self):
            return self.client_address[0] in ("127.0.0.1", "::1", "localhost")

        def do_GET(self):
            p = self.path.split("?")[0]
            if p == "/api/ping":
                return self._json(200, {"ok": True, "dir": str(root)})
            if p == "/api/log":
                f = prep / "review-log.json"
                return self._json(200, json.loads(f.read_text(encoding="utf-8")) if f.exists() else [])
            if p.startswith("/api/") and p[5:] in DOCS:
                f = prep / DOCS[p[5:]]
                return self._json(200, json.loads(f.read_text(encoding="utf-8")) if f.exists() else {})
            return super().do_GET()

        def do_POST(self):
            if not self._local():
                return self._json(403, {"error": "local only"})
            n = int(self.headers.get("Content-Length") or 0)
            if n > MAX_BODY:
                return self._json(413, {"error": "too large"})
            try:
                data = json.loads(self.rfile.read(n) or b"{}")
            except json.JSONDecodeError:
                return self._json(400, {"error": "bad json"})
            p = self.path.split("?")[0]
            prep.mkdir(parents=True, exist_ok=True)
            if p == "/api/trainer":
                cur = prep / DOCS["trainer"]
                if cur.exists():
                    try:
                        old = json.loads(cur.read_text(encoding="utf-8"))
                        if len(old.get("cards") or {}) > len(data.get("cards") or {}) and not data.get("reset"):
                            # a tab with stale state must not wipe progress: keep the union, newest side wins
                            merged = dict(old.get("cards") or {})
                            for k, c in (data.get("cards") or {}).items():
                                if k not in merged or (c.get("last") or 0) >= (merged[k].get("last") or 0):
                                    merged[k] = c
                            data["cards"] = merged
                    except (json.JSONDecodeError, AttributeError):
                        pass
                data.pop("reset", None)   # an explicit "reset progress" from the page is applied once
            if p == "/api/log":
                f = prep / "review-log.json"
                items = json.loads(f.read_text(encoding="utf-8")) if f.exists() else []
                have = {(x[0], x[1]) for x in items}
                new = [x for x in (data.get("items") or []) if isinstance(x, list) and len(x) >= 3 and (x[0], x[1]) not in have]
                items.extend(new)
                tmp = prep / "review-log.json.tmp"
                tmp.write_text(json.dumps(items, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
                tmp.replace(f)
                return self._json(200, {"ok": True, "added": len(new), "total": len(items)})
            if p.startswith("/api/") and p[5:] in DOCS:
                tmp = prep / (DOCS[p[5:]] + ".tmp")
                tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
                tmp.replace(prep / DOCS[p[5:]])
                return self._json(200, {"ok": True})
            if p == "/api/inbox":
                f = prep / "inbox.json"
                items = json.loads(f.read_text(encoding="utf-8")) if f.exists() else []
                data["received"] = int(time.time() * 1000)
                items.append(data)
                f.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")
                return self._json(200, {"ok": True, "count": len(items)})
            return self._json(404, {"error": "unknown"})

    return H


def ping(port: int):
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/ping", timeout=1) as r:
            return json.loads(r.read())
    except Exception:
        return None


def free_port(start: int) -> int:
    for port in range(start, start + 50):
        with socket.socket() as s:
            try:
                s.bind(("127.0.0.1", port))
                return port
            except OSError:
                continue
    sys.exit("no free port")


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=".")
    ap.add_argument("--port", type=int, default=DEFAULT_PORT)
    ap.add_argument("--foreground", action="store_true")
    ap.add_argument("--stop", action="store_true")
    args = ap.parse_args()
    root = Path(args.dir).expanduser().resolve()
    pidfile = root / "prep" / ".serve.json"

    info = json.loads(pidfile.read_text()) if pidfile.exists() else {}
    if args.stop:
        if info.get("pid"):
            try:
                os.kill(info["pid"], signal.SIGTERM)
            except ProcessLookupError:
                pass
        pidfile.unlink(missing_ok=True)
        print("stopped")
        return 0

    # already running for this folder?
    for port in [info.get("port"), args.port]:
        if port:
            r = ping(port)
            if r and r.get("dir") == str(root):
                print(f"POLAKO_URL http://localhost:{port}/")
                return 0

    (root / "dist").mkdir(parents=True, exist_ok=True)
    port = free_port(args.port)

    if args.foreground:
        srv = ThreadingHTTPServer(("127.0.0.1", port), make_handler(root))
        pidfile.parent.mkdir(parents=True, exist_ok=True)
        pidfile.write_text(json.dumps({"pid": os.getpid(), "port": port}))
        print(f"POLAKO_URL http://localhost:{port}/", flush=True)
        try:
            srv.serve_forever()
        except KeyboardInterrupt:
            pass
        return 0

    log = open(root / "dist" / ".serve.log", "a")
    proc = subprocess.Popen([sys.executable, __file__, "--dir", str(root), "--port", str(port), "--foreground"],
                            stdout=log, stderr=log, stdin=subprocess.DEVNULL, start_new_session=True)
    for _ in range(50):
        if ping(port):
            print(f"POLAKO_URL http://localhost:{port}/")
            return 0
        if proc.poll() is not None:
            break
        time.sleep(0.1)
    print("server did not start — see dist/.serve.log", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
