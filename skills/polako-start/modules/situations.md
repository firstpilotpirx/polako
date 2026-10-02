<!-- Polako hub module. Called from skills/polako-start/SKILL.md; the person does not run it. -->
<!-- Purpose: the person's real situations — short dialogs and phrases they will hear and say; phrase cards from them. -->

# module `situations` — where the person needs Serbian

## Step 1. Which situations

From the profile (`situations`) or a new one the person names. The catalog:
`run situations.py --dir <folder> catalog` (ids, titles, default priority). A situation of their own
("school meeting", "renting a car") gets a new slug id. Ask its priority with buttons only if it is not
in the catalog: every week (1) / sometimes (2) / rare but important (3).

## Step 2. Dialogs — written by the agent

For each situation, 1–3 dialogs of 4–8 lines, written the way it really goes in Serbia (Belgrade,
ekavian, Latin): a cashier, a clerk at the MUP window, a pharmacist, a landlord, a neighbour.

- `who: they` — what the person **hears**: natural speed and words, including the usual formulas
  (Izvolite. · Za ovde ili za poneti? · Imate li karticu lojalnosti? · Sledeći!).
- `who: me` — what the person **says**: short, simple, correct sentences at their level; always include
  the life-savers: Izvinite, možete li da ponovite sporije? · Ne razumem. · Da li može karticom?
- Translations natural, in the explanation language. No transliteration hints, no stress marks.
- Real details: dinars, working hours, documents (lična karta, pasoš, beli karton, potvrda o smeštaju),
  but no real names of people.

Draft (`prep/sit-draft.yaml`), then:

```bash
run situations.py --dir <folder> add prep/sit-draft.yaml
run text_freq.py --dir <folder>          # the new lines count for word candidates
```

Format: [../references/card-format.md](../references/card-format.md#situations).

## Step 3. Phrases

```bash
run phrases.py --dir <folder>            # → prep/phrases-draft.yaml: every "me" line, short "they" lines, recurring chunks of own texts
```

Check the draft: delete trivial or duplicate lines, translate the chunks from own texts (`tr` empty),
keep `sit`. Then:

```bash
run words.py --dir <folder> add prep/phrases-draft.yaml --kind phrases
```

The page makes from each dialog the "what do you answer?" cards itself, and from phrases — listening
and saying cards. The Situations tab shows readiness per situation and a "Train" button.

## Before an appointment

"Tomorrow I go to the MUP" → check the situation exists (add it if not), raise its priority
(`situations.py set mup pri=1`), add 3–5 phrases for exactly that visit (documents to bring, asking to
repeat), rebuild, and send the person to the Situations tab → "Train". Suggest target recall 95% in the
trainer settings until the appointment.
