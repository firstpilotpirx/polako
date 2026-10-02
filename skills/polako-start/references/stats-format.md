# Statistics format

The Statistics tab (`templates/portal/stats.js`) and `tools/stats.py` compute from the same review log.

| Block | Meaning | Computed from |
|---|---|---|
| Hero: coverage of spoken Serbian | share of all running words in Serbian dialogs covered by understood lemmas | subtitle lemma counts × understood words |
| Tiles | coverage of own texts · words learned / all · recall on reviews 30 d · minutes in 7 d · streak | log, cards |
| Coverage over time | spoken and own-text coverage, one point per day (`T.hist`) | daily snapshot |
| Readiness by situation | mean of min(1, S/21) over the situation's sides | cards |
| Recall by week vs target | right answers / answers on reviews with ≥ 1 day elapsed; weeks 5+ points below target in orange | log |
| Recall after N days | the same by elapsed-days bucket (1, 2–3, 4–7, 8–14, 15–30, 31+) | log |
| Calendar | answers per day, 26 weeks, sequential blue | log |
| Minutes a day | Σ min(60 s, answer time) per day, 30 days | log |
| Weak spot by side | accuracy per side, mean answer time in the tooltip | log, 30 d |
| Load, 30 days | sides due per day (overdue → today) | cards |
| Cases and aspect | accuracy of cloze cards by case, aspect cards | log |
| Hard words | most lapses, lowest stability; 🐛 leeches; "Разобрать с Claude" → inbox `{type: hard, ids}` | cards |
| Forecast by group | FSRS: days until every side reaches 21 days if answered Good on time; fresh words start at the daily goal; realistic × (1 + 2 · again-rate) | cards, goal |

Charts: SVG, bars ≤ 24 px with rounded data ends, 2 px lines, hairline grid, one value axis, a tooltip
on every mark (crosshair on lines), a "Таблица" view under each chart, light and dark tokens
(validated categorical blue/orange, sequential blue for the calendar).
