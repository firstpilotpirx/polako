<!-- Polako hub module. Called from skills/polako-start/SKILL.md; the person does not run it. -->
<!-- Purpose: "how am I doing?" in the chat, and the personal FSRS fit. -->

# module `stats` — progress

```bash
run stats.py --dir <folder>            # coverage, cards by state, recall on reviews vs target, weak sides, load, streak, leeches
run coverage.py --dir <folder>         # coverage per own text and situation
```

Answer in 3–5 lines, the most useful first:

1. **Coverage** — "you understand ~X% of the words of ordinary conversation and Y% of your own texts"
   (the main number; it grows fastest with the top of the list and with own words).
2. Recall on reviews vs the target: below target by 5+ points → suggest a smaller daily goal or more
   frequent short sessions; far above → raise the goal or lower the target to 85%.
3. The weakest card side (e.g. listening 62%) → one concrete suggestion («Только на слух» on the way to work).
4. Load for the week, streak; leeches → offer "Разобрать трудные слова".

Details and charts are on the page (tab «Статистика»): definitions in
[../references/stats-format.md](../references/stats-format.md).

## Personal intervals (menu "Настроить интервалы под меня")

```bash
run fsrs_fit.py --dir <folder> --dry      # calibration: predicted vs actual recall
run fsrs_fit.py --dir <folder>            # with ≥ 300 second reviews: prep/fsrs-params.json
run build_page.py --dir <folder>
```

Say in one line what changed ("after the first «Good» you keep a word ~5 days, not 3 — reviews will be
rarer"). Too little data → say when to come back (≈ 2–3 weeks of daily practice).
