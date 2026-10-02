<!-- Polako hub module. Called from skills/polako-start/SKILL.md; the person does not run it. -->
<!-- Purpose: get the open corpora, compute what spoken Serbian sounds like, explain the coverage curve. -->

# module `corpus` — what Serbian sounds like

## Step 1. Corpora (once per machine)

```bash
run fetch_data.py               # UniMorph forms + subtitle frequency lists (sr, hr), ≈ 33 MB from GitHub
run fetch_data.py --tatoeba --lang <explain>   # optional: sentence pairs for examples (downloads.tatoeba.org)
run fetch_data.py --status
```

Exit 6 / `POLAKO_OFFLINE` — no network: one line to the person; the bundled core lexicon still works
(lemmas for the ~480 most frequent words), base_freq and candidates wait until the data is there.
Offer Tatoeba as a button only for Russian/English/Ukrainian explanation languages; it improves examples.

## Step 2. Spoken frequency

```bash
run base_freq.py --top 40
```

It lemmatizes the subtitle list (Cyrillic → Latin, Croatian/ijekavian forms folded into Serbian,
Croatianisms flagged) and prints the coverage table. Tell the person in one line, with their numbers:
"the 100 most frequent lemmas are ~60% of everything said, 1000 — ~85%: so we go from the top, and add
your own words on top of that".

How lemmas are found (sr_lemma.py): the curated core lexicon first (pronouns, biti/imati/moći/ići…,
everyday nouns, with all forms), then UniMorph, then fallbacks — restoring diacritics (kuca → kuća),
ending stripping (marked `stem`), otherwise the form itself (`self`). `self`/`stem` entries are checked
by the agent when making cards: names from subtitles (Džek, Majkl) and junk are deleted, a form is
replaced by its dictionary form (privremenog → privremeni).

## Step 3. Own material

```bash
run text_freq.py --dir <folder> --top 30
```

Counts the person's texts (`my/`) and situations. Rerun it whenever a text or a situation is added —
`words.py candidates` reads its output.
