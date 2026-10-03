#!/usr/bin/env python3
"""The public site's storage end to end, against an in-memory GitHub: start in the browser, reload, connect an
empty repository (the set and progress move there), answer more, a second device with its own progress connects
(merged), the first sees it, then back to the browser.

    python3 tests/site_storage.py <built site dir>      # needs playwright + chromium (CHROMIUM=path to override)
"""
import os, sys
SITE_DIR = sys.argv[1] if len(sys.argv) > 1 else "docs"
import json, base64, re, itertools
from playwright.sync_api import sync_playwright
# in-memory GitHub: commits = list of file dicts
repo = {"commits": [], "trees": {}, "pending": {}, "msgs": []}
ids = itertools.count(1)
def head(): return repo["commits"][-1] if repo["commits"] else None
def files_at(sha):
    for c in repo["commits"]:
        if c["sha"] == sha: return c["files"]
    return head()["files"] if head() else {}
def b64(s): return base64.b64encode(s.encode()).decode()
def handle(route, req):
    url = req.url.split("api.github.com")[1]; path, _, q = url.partition("?"); m = req.method
    body = json.loads(req.post_data) if req.post_data else None
    def j(obj, st=200): route.fulfill(status=st, content_type="application/json", body=json.dumps(obj), headers={"access-control-allow-origin": "*"})
    if req.headers.get("authorization") != "Bearer tok": return j({"message": "Bad credentials"}, 401)
    base = "/repos/me/polako-data"
    if not path.startswith(base): return j({}, 404)
    p = path[len(base):]
    if p == "": return j({"default_branch": "main"})
    if p == "/git/ref/heads/main":
        return j({"object": {"sha": head()["sha"]}}) if head() else j({"message": "Git Repository is empty."}, 409)
    if p.startswith("/git/commits/") and m == "GET": return j({"tree": {"sha": "t-" + p.split("/")[-1]}})
    if p == "/git/trees":
        base_files = dict(files_at(body["base_tree"][2:]))
        for f in body["tree"]: base_files[f["path"]] = f["content"]
        sha = "tree%d" % next(ids); repo["trees"][sha] = base_files; return j({"sha": sha}, 201)
    if p == "/git/commits" and m == "POST":
        sha = "c%d" % next(ids); repo["pending"][sha] = (repo["trees"][body["tree"]], body["parents"][0], body["message"]); return j({"sha": sha}, 201)
    if p == "/git/refs/heads/main" and m == "PATCH":
        files, parent, msg = repo["pending"][body["sha"]]
        if head()["sha"] != parent: return j({"message": "not fast forward"}, 422)
        repo["commits"].append({"sha": body["sha"], "files": files}); repo["msgs"].append(msg); return j({})
    if p.startswith("/contents/"):
        fp = p[len("/contents/"):]
        ref = dict(x.split("=") for x in q.split("&") if x).get("ref")
        files = files_at(ref) if ref else (head()["files"] if head() else {})
        if m == "GET":
            if fp in files: return j({"sha": "b" + str(abs(hash(files[fp]))), "content": b64(files[fp]), "encoding": "base64", "size": len(files[fp])})
            kids = [k for k in files if k.startswith(fp + "/")]
            if kids: return j([{"name": k.split("/")[-1], "path": k} for k in kids])
            return j({"message": "Not Found"}, 404)
        if m == "PUT":
            nf = dict(head()["files"]) if head() else {}
            nf[fp] = base64.b64decode(body["content"]).decode()
            sha = "c%d" % next(ids); repo["commits"].append({"sha": sha, "files": nf}); repo["msgs"].append(body["message"]); return j({"content": {}}, 201)
    return j({}, 404)


import http.server, threading, functools
srv = http.server.ThreadingHTTPServer(("127.0.0.1", 8782), functools.partial(http.server.SimpleHTTPRequestHandler, directory=SITE_DIR))
srv.RequestHandlerClass.log_message = lambda *a: None
threading.Thread(target=srv.serve_forever, daemon=True).start()
URL = "http://127.0.0.1:8782/"
def answer(pg, n):
    pg.locator("nav.tabs button").first.click(); pg.wait_for_timeout(200)
    pg.locator("main .tr-smart").first.click(); pg.wait_for_timeout(300)
    for i in range(n):
        pg.locator("main .tr-choices button").first.click(); pg.wait_for_timeout(120); pg.keyboard.press("Enter"); pg.wait_for_timeout(150)
    pg.keyboard.press("Escape"); pg.wait_for_timeout(300)
def open_settings(pg):
    pg.locator("nav.tabs button").first.click(); pg.wait_for_timeout(200)
    pg.evaluate("document.querySelector('details.tr-opts').open = true"); pg.wait_for_timeout(100)
errs = []
with sync_playwright() as p:
    b = p.chromium.launch(**({"executable_path": os.environ["CHROMIUM"]} if os.environ.get("CHROMIUM") else {}))
    ctx = b.new_context(viewport={"width": 430, "height": 932}); ctx.route("https://api.github.com/**", handle)
    pg = ctx.new_page(); pg.on("pageerror", lambda e: errs.append(str(e)))
    pg.goto(URL); pg.wait_for_timeout(700)
    print("1 welcome:", pg.locator(".setup h3").all_inner_texts())
    pg.locator(".setup-packs button").first.click(); pg.wait_for_timeout(1200)
    answer(pg, 3)
    print("  browser state:", pg.evaluate("polakoState()"), "|", pg.locator("#sync").inner_text() if pg.locator("#sync").count() else "")
    pg.reload(); pg.wait_for_timeout(1500)
    print("2 after reload:", pg.evaluate("polakoState()"), "|", pg.locator("#sync").inner_text() if pg.locator("#sync").count() else "")
    open_settings(pg)
    print("  storage options:", pg.locator(".st-opt b").all_inner_texts())
    pg.get_by_role("button", name="Подключить GitHub").click(); pg.wait_for_timeout(200)
    pg.fill(".storage .setup-form input >> nth=0", "me/polako-data"); pg.fill(".storage .setup-form input >> nth=1", "tok")
    pg.locator(".storage .setup-form button").click(); pg.wait_for_timeout(2500)
    f = head()["files"]
    print("3 repo after connect:", sorted(f), "cards:", len(json.loads(f["prep/trainer-state.json"])["cards"]), "log:", sum(len(json.loads(v)) for k, v in f.items() if k.startswith("prep/log/")))
    print("  page now:", pg.evaluate("polakoState()"), "|", pg.locator("#sync").inner_text() if pg.locator("#sync").count() else "")
    answer(pg, 2); pg.evaluate("polakoFlush()"); pg.wait_for_timeout(1500)
    f = head()["files"]; print("4 after 2 more:", "cards", len(json.loads(f["prep/trainer-state.json"])["cards"]), "log", sum(len(json.loads(v)) for k, v in f.items() if k.startswith("prep/log/")))
    # device 2 starts in its own browser with other progress, then connects → merge
    ctx2 = b.new_context(viewport={"width": 430, "height": 932}); ctx2.route("https://api.github.com/**", handle)
    pg2 = ctx2.new_page(); pg2.on("pageerror", lambda e: errs.append(str(e)))
    pg2.goto(URL); pg2.wait_for_timeout(600); pg2.locator(".setup-packs button").first.click(); pg2.wait_for_timeout(1000)
    answer(pg2, 4)
    open_settings(pg2); pg2.get_by_role("button", name="Подключить GitHub").click()
    pg2.fill(".storage .setup-form input >> nth=0", "me/polako-data"); pg2.fill(".storage .setup-form input >> nth=1", "tok"); pg2.locator(".storage .setup-form button").click(); pg2.wait_for_timeout(3000)
    f = head()["files"]; print("5 device 2 merged:", "log", sum(len(json.loads(v)) for k, v in f.items() if k.startswith("prep/log/")), "page:", pg2.evaluate("polakoState()"))
    # back to browser on device 1
    pg.reload(); pg.wait_for_timeout(1500); print("6 device 1 sees:", pg.evaluate("polakoState()"))
    open_settings(pg); pg.locator(".st-opt input >> nth=0").check(); pg.wait_for_timeout(200)
    pg.get_by_role("button", name="Да").click(); pg.wait_for_timeout(2000)
    print("7 back to browser:", pg.evaluate("polakoState()"), "|", pg.locator("#sync").inner_text() if pg.locator("#sync").count() else "", "| cfg", pg.evaluate("localStorage.getItem('pl.storage')"))
    pg.screenshot(path="/tmp/polako-st.png")
    open_settings(pg); pg.wait_for_timeout(200); pg.locator(".storage").screenshot(path="/tmp/polako-st2.png")
    assert not errs, errs
    print("site storage: ok")
    srv.shutdown(); b.close()
