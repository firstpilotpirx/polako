"""The page's scheduler (fsrs.js) and the Python one (tools/fsrs.py) give the same cards."""
import json
import random
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import fsrs  # noqa: E402

DAY = fsrs.DAYMS


def script(seed=7, n=400):
    rnd = random.Random(seed)
    steps, t = [], 1_790_000_000_000
    for _ in range(n):
        t += int(rnd.choice([0.002, 0.3, 1, 2, 3, 6, 11, 25, 60]) * DAY)
        steps.append((t, rnd.choice([1, 2, 3, 3, 3, 4])))
    return steps


def run_py(steps, retention=0.9):
    out, cards = [], {}
    for i, (t, g) in enumerate(steps):
        k = i % 5
        res = fsrs.review(cards.get(k), g, t, retention)
        cards[k] = res["card"]
        out.append([res["card"]["s"], res["card"]["d"], res["card"]["due"], res["card"]["lapses"], res["elapsed"], res["r"]])
    return out


def run_js(steps, retention=0.9):
    js = (ROOT / "templates/portal/fsrs.js").read_text()
    prog = js + f"""
var steps = {json.dumps(steps)}, cards = {{}}, out = [];
steps.forEach(function(st, i){{ var k = i % 5, res = FSRS.review(cards[k], st[1], st[0], {retention}); cards[k] = res.card;
  out.push([res.card.s, res.card.d, res.card.due, res.card.lapses, res.elapsed, res.r]); }});
process.stdout.write(JSON.stringify(out));"""
    r = subprocess.run(["node", "-e", prog], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def test_same_numbers():
    if not shutil.which("node"):
        print("skip: node not installed")
        return
    for ret in (0.9, 0.85):
        steps = script()
        a, b = run_py(steps, ret), run_js(steps, ret)
        assert len(a) == len(b)
        for i, (x, y) in enumerate(zip(a, b)):
            assert all(abs(p - q) < 1e-6 for p, q in zip(x, y)), (i, x, y)


def test_shape():
    t0 = 1_790_000_000_000
    c = fsrs.review(None, 3, t0)["card"]
    assert abs(c["s"] - fsrs.W[2]) < 1e-3 and c["due"] == t0 + 3 * DAY   # Good on a new card: ~3 days
    c2 = fsrs.review(c, 3, c["due"])["card"]
    assert c2["s"] > c["s"] * 2                                           # success at the due date grows stability
    c3 = fsrs.review(c2, 1, c2["due"])["card"]
    assert c3["s"] < c2["s"] and c3["lapses"] == 1 and c3["due"] - c2["due"] == 10 * 60000
    assert fsrs.review(None, 4, t0)["card"]["s"] > fsrs.review(None, 2, t0)["card"]["s"]


if __name__ == "__main__":
    test_shape()
    test_same_numbers()
    print("fsrs: ok")
