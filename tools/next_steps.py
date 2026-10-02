#!/usr/bin/env python3
"""The hub menu: what to do next, computed from the learner's files.

    run next_steps.py --dir ~/polako --json     # {status, menu: [up to 4], all: [...]}
    run next_steps.py --dir ~/polako            # the same, readable

Each option: {id, label, description, module, args, why}. The hub shows `menu` as buttons, the first
one recommended. Labels are Russian (the default explanation language); for another language the
agent translates them on the fly. Rules, roughly in priority order:
  no profile → the wizard · no corpora → download them · inbox texts / hard words from the page →
  analyse them · situations chosen without dialogs → write them · no deck → first round ·
  round not checked → check on the page · round checked → next round or learn · cards due → train ·
  situations without phrases → phrases · few cloze/aspect cards → grammar · then: add a text,
  statistics, personal FSRS fit (after enough reviews), an update when the plugin is newer.
"""
from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from prepio import data_dir, read_json, read_yaml  # noqa: E402


def opt(i, label, desc, module, why, args=None):
    return {"id": i, "label": label, "description": desc, "module": module, "args": args or {}, "why": why}


def compute(root: Path) -> dict:
    prep = root / "prep"
    prof = read_yaml(prep / "profile.yaml", None)
    deck = read_yaml(prep / "words.yaml", {}) or {}
    sits = (read_yaml(prep / "situations.yaml", {}) or {}).get("situations", [])
    st = read_json(prep / "trainer-state.json", {}) or {}
    log = read_json(prep / "review-log.json", []) or []
    inbox = [x for x in (read_json(prep / "inbox.json", []) or []) if not x.get("done")]
    sess = read_yaml(prep / "session.yaml", {}) or {}
    now = int(time.time() * 1000)
    out = []
    wz = (prof or {}).get("wizard") or {}
    if not prof or not wz.get("finished"):
        out.append(opt("wizard", "Начать (5 вопросов)" if not prof else "Продолжить настройку", "Язык, уровень, ситуации, цель в день — дальше всё соберу сам.", "wizard", "no profile"))
    d = data_dir()
    if not (d / "subs-sr-50k.txt").exists() or not (d / "unimorph-hbs.tsv").exists():
        out.append(opt("data", "Скачать словари", "Частотный список разговорного сербского и словарь форм (≈ 33 МБ, один раз).", "corpus", "no corpora"))
    texts = [x for x in inbox if x.get("type") == "text"]
    if texts:
        out.append(opt("inbox-text", f"Разобрать присланный текст ({len(texts)})", "Найду незнакомые слова и добавлю в колоду с примерами из текста.", "text", "inbox text", {"inbox": True}))
    if any(x.get("type") == "hard" for x in inbox):
        out.append(opt("hard", "Разобрать трудные слова", "Ассоциации, свои примеры и разбор ошибок для слов, которые забываются.", "trainer", "inbox hard", {"mode": "hard"}))
    chosen = (prof or {}).get("situations") or []
    have = {s["id"] for s in sits if s.get("dialogs")}
    missing = [s for s in chosen if s not in have]
    if prof and missing:
        out.append(opt("situations", f"Написать ситуации ({len(missing)})", "Короткие живые диалоги и фразы: " + ", ".join(missing[:4]) + ".", "situations", "chosen without dialogs", {"ids": missing}))
    words = [w for w in deck.get("words", []) if not w.get("retired")]
    if prof and not words:
        packs = sorted((Path(__file__).resolve().parent.parent / "data" / "packs").glob("*.yaml"))
        for pk in packs[:1]:
            title = (read_yaml(pk, {}) or {}).get("title", pk.stem)
            out.append(opt("pack", f"Набор «{title}»", "Готовые диалоги, ~250 слов и фразы для этих ситуаций — сразу в тренажёр.", "pack", "no deck", {"name": pk.stem}))
        out.append(opt("round", "Собрать первые слова", "Частотный анализ + ваши ситуации и тексты → первая колода.", "vocab", "no deck"))
    if words:
        from words import known_ids
        rnd = max((w.get("round", 1) for w in words), default=1)
        rw = [w for w in words if w.get("round", 1) == rnd]
        known, checked = known_ids(root)
        c = [w for w in rw if w["id"] in checked]
        share = sum(1 for w in c if w["id"] in known) / len(c) if c else 0
        if len(c) < len(rw) * 0.9:
            out.append(opt("check", "Отметить, что я уже знаю", f"Раунд {rnd}: проверено {len(c)} из {len(rw)} на вкладке «Словарь».", "page", "round unchecked", {"tab": "vocab"}))
        elif share >= 0.5:
            out.append(opt("round", "Следующий раунд слов", f"Вы знаете {share:.0%} раунда {rnd} — идём глубже по частотному списку.", "vocab", "round known", {"deeper": True}))
    cards = st.get("cards") or {}
    due = sum(1 for c in cards.values() if c.get("due", now + 1) <= now)
    if words and (due or not cards):
        out.append(opt("train", f"Повторить ({due})" if due else "Начать учить", "Открою тренажёр: сначала повторения, потом новые слова до цели.", "page", "due", {"tab": "train"}))
    if sits and words:
        ph_sit = {s for p in deck.get("phrases", []) for s in p.get("sit", [])}
        no_ph = [s["id"] for s in sits if s.get("dialogs") and s["id"] not in ph_sit]
        if no_ph:
            out.append(opt("phrases", "Добавить фразы ситуаций", "Реплики из диалогов — карточками «на слух» и «сказать»: " + ", ".join(no_ph[:4]) + ".", "situations", "situations without phrases", {"ids": no_ph}))
    if len(words) >= 60 and len(deck.get("cloze", [])) < len(words) // 15:
        out.append(opt("grammar", "Падежи и вид глагола", "Карточки «нужная форма в предложении» и пары kupiti/kupovati для частых слов.", "vocab", "few cloze", {"mode": "grammar"}))
    if prof:
        out.append(opt("text", "Добавить свой текст", "Сообщение, письмо, объявление — покажу, что в нём незнакомо, и добавлю в колоду.", "text", "always"))
    if log:
        out.append(opt("stats", "Как у меня дела?", "Покрытие речи, что держится в памяти, где слабое место, нагрузка на неделю.", "stats", "has log"))
    if sum(1 for x in log if x[4] >= 0.5) >= 600 and not (prep / "fsrs-params.json").exists():
        out.append(opt("fit", "Настроить интервалы под меня", "Подберу параметры FSRS по вашей истории ответов.", "stats", "enough reviews", {"fit": True}))
    try:
        pv = json.loads((Path(__file__).resolve().parent.parent / ".claude-plugin" / "plugin.json").read_text())["version"]
        if sess.get("plugin_version") and sess["plugin_version"] != pv:
            out.insert(0, opt("upgrade", f"Обновить до {pv}", "Что нового, бэкап и перенос прогресса.", "upgrade", "plugin newer"))
    except Exception:
        pass
    status = []
    if words:
        status.append(f"слов в колоде {len(words)}")
    if cards:
        status.append(f"к повторению {due}")
    if log:
        days = {time.strftime('%Y-%m-%d', time.localtime(x[0] / 1000)) for x in log}
        status.append(f"дней занятий {len(days)}")
    return {"status": " · ".join(status), "menu": out[:4], "all": out}


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--dir", default=".")
    ap.add_argument("--json", action="store_true")
    a = ap.parse_args()
    r = compute(Path(a.dir).expanduser().resolve())
    if a.json:
        print(json.dumps(r, ensure_ascii=False))
        return 0
    print(r["status"] or "(новая папка)")
    for i, o in enumerate(r["all"], 1):
        print(f"{i}. {o['label']} — {o['description']}  [{o['module']}]")
    return 0


if __name__ == "__main__":
    sys.exit(main())
