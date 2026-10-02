# Card and situation format

The files are written only by scripts (`words.py`, `situations.py`, `forms.py`, `score_words.py`);
the agent writes drafts. Schemas: `schemas/words.schema.json`, `schemas/situations.schema.json`,
`schemas/profile.schema.json`.

## prep/words.yaml

```yaml
version: 1
explain: ru                 # language of tr
group_size: 50
rounds: 2
words:
  - id: w:kirija            # slug of sr (č→ch ć→cj š→sh ž→zh đ→dj); NEVER changes — progress is tied to it
    sr: kirija              # dictionary form, Latin, ekavian
    tr: аренда, квартплата
    pos: noun               # noun verb adj adv pron prep conj part num interj phrase
    gender: f               # nouns, from the core lexicon only (a guess is never written)
    forms: {gen: kirije, acc: kiriju, loc: kiriji, ins: kirijom, pl: kirije}
    accent: kìrija          # only from UniMorph
    asp: pf                 # verbs; pair: w:… — the aspect partner
    rank: 96                # importance for this person (score_words.py), groups of 50 → grp
    grp: 2
    score: 7.553
    zipf: 4.01              # lemma frequency (max of written and spoken)
    band: 3                 # frequency band for the quick check (1 ≥ 5.3, 2 ≥ 4.5, 3 ≥ 3.5, 4 below)
    pm: 10.34               # per million in subtitles
    src: [base, my, sit]    # spoken frequency / own texts / situations / manual
    sit: [stan]
    my: [my.stanodavka]
    note: …                 # false friends, government, gender surprises
    round: 1
    ex:
      - {sr: "Kirija za ovaj mesec je 450 evra.", tr: "…", about: my, from: my.stanodavka}
      - {sr: "Da li su računi uključeni u kiriju?", tr: "…", about: sit, from: sit.stan}
phrases:
  - {id: "p:koliko-koshta", sr: "Koliko košta?", tr: "Сколько стоит?", sit: [pekara], words: [w:koliko, w:koshtati], note: говорю я}
cloze:
  - {id: "c:idem-u-prodavnicu", sr: "Idem u {prodavnicu}.", tr: "Иду в магазин.", word: w:prodavnica, case: acc, hint: "prodavnica — куда?"}
```

Retired cards keep `retired: true` and are never removed. `validate.py` keeps `prep/ids.lock.json`
with every id ever published and fails when one disappears.

## Drafts the agent writes

- **words** (`words.py add`): a list of `{sr, tr, [pos], [note], [sit], [my], [src], [ex], [pair_sr]}`;
  everything else is filled by scripts. `words.py candidates` and `unknown_in.py --draft` produce it ready.
- **phrases** (`--kind phrases`): `{sr, tr, [sit], [note], [from]}`.
- **cloze** (`--kind cloze`): `{sr: "… {form} …", tr, word: <sr or w:id>, case, [hint], [opts]}`.

## Situations

```yaml
version: 1
situations:
  - id: mup
    title: МУП, ВНЖ (боравак)
    title_sr: MUP i boravak
    pri: 1                  # 1 every week · 2 sometimes · 3 rare but important
    dialogs:
      - id: mup-1
        title: Подаю документы на боравак
        lines:
          - {who: they, sr: "Sledeći! Izvolite.", tr: "Следующий! Прошу."}
          - {who: me, sr: "Dobar dan. Došao sam da predam zahtev za privremeni boravak.", tr: "…"}
```

Each `me` line after a `they` line becomes a "what do you answer?" card on the page (`d:<dialog>:<line>`).

## Own texts — my/*.txt

```
---
title: Сообщение от хозяйки квартиры
from: viber
added: 2026-10-02
---
Dobar dan! Kirija za ovaj mesec je 450 evra…
```

Written by `unknown_in.py --save`; Cyrillic is converted to Latin on saving.
