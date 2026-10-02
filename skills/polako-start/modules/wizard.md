<!-- Polako hub module. Called from skills/polako-start/SKILL.md; the person does not run it. -->
<!-- Purpose: the first-run questions — explanation language, why Serbian, level, situations, own texts, daily goal, listening — then the data and the first round. -->

# module `wizard` — getting to know the learner

Five quick screens of buttons, then the work is done by scripts. Record every answer at once:

```bash
run state.py --dir <folder> wizard step <step> --answer key=value …
```

The page is built from the first answer on (hub step 1½) and fills in as the wizard goes.

| step | Question (buttons) | Writes |
|---|---|---|
| explain | Language of translations: Русский (recommended) / Українська / English / Other | `explain=ru` |
| why | What is Serbian for: I live in Serbia / I'm moving / Work, family / Travel | `why=…` |
| level | Your Serbian now: zero (a0) / a few words (a1) / simple conversations (a2) / I talk, but with gaps (b1) | `level=a1` |
| pack | A ready set: `run pack.py list` — e.g. «Белград: первые разговоры» (соседи, магазин, МУП, нотариус/юрист/бухгалтер, коллега). Buttons: the matching pack (recommended when its situations fit) / "Pick situations myself" | installs with `run pack.py --dir <folder> install <name>` — situations, ~250 words, phrases, case cards |
| situations | Only if no pack fits: where you need it — multiSelect from `run situations.py catalog` (show 4 groups, then "More"; pri 1 items first) | `'situations=["pekara","mup",…]'` |
| texts | Do you get messages or letters in Serbian? I'll paste some (recommended) / Later / No | — (→ module `text` after the first round) |
| goal | New words a day: 10 / 15 (recommended) / 20 / 30 | `goal=15` |
| listening | Listening cards (needs a Serbian/Croatian voice in the browser): On (recommended) / Off. Typing is off by default — offer it only if the person asks | `listening=true typing=false` |

Then, without asking:

1. `run wizard finish` · `run migrate.py --dir <folder> --init`.
2. Module `corpus` (download + spoken frequency; one line about coverage: "the top 1000 lemmas are 85% of everything said").
3. A pack chosen → `run pack.py --dir <folder> install <name>` replaces steps 4–5: its words are the first
   round (still checked with "I know" on the page). No pack → module `situations` for the chosen ones,
   then module `vocab` — the first round.
4. Rebuild, open the page on the "Словарь" tab: "Mark what you already know — the rest goes to the trainer."

Changing one answer later: `run state.py profile set key=value` and rebuild; a new situation → module `situations`.
