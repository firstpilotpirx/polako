"""Transliteration, lemmatization and the core paradigm — the parts every frequency count rests on."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "tools"))
from translit import fold, norm, slug, strip_accents, to_cyrillic, to_latin, tokens  # noqa: E402


def test_translit():
    assert to_latin("Љубав, ЊЕГОШ, џеп, ђак") == "Ljubav, NJEGOŠ, džep, đak"
    assert to_cyrillic("Ljubav Njegoš džep đak") == "Љубав Његош џеп ђак"
    assert to_cyrillic("injekcija nadživeti konjunkcija") == "инјекција надживети конјункција"   # not digraphs
    assert strip_accents("kȕća pòsao tèrmīn čaša ćao") == "kuća posao termin čaša ćao"
    assert fold("kuća đak Šta") == "kuca djak Sta"
    assert slug("kuća") == "kucja" and slug("kuca") == "kuca" and slug("Đorđe") == "djordje"
    assert tokens("Šta-ti-je? 3 km, https://x.rs") == ["Šta", "ti", "je", "km"]
    assert norm("Ку́ћа") == "kuća"


def test_lemmas():
    try:
        from sr_lemma import load
        lex = load()
    except Exception as e:  # pragma: no cover
        print("skip lemmas:", e)
        return
    cases = {"kućama": "kuća", "idemo": "ići", "nisam": "biti", "ćeš": "hteti", "mnom": "ja", "ljudi": "čovek",
             "oči": "oko~noun", "bolje": "dobar", "radiću": "raditi", "mlijeko": "mleko", "kruh": "hleb", "tko": "ko",
             "posla": "posao", "momci": "momak", "dvije": "dva"}
    for form, lemma in cases.items():
        assert lex.lemma(form)[0] == lemma, (form, lex.lemma(form))
    assert "stan" in lex.candidates("stanu")       # ambiguous: stati / stan
    assert lex.variant("mlijeko") == "mleko"


def test_paradigm():
    from sr_lemma import adj_forms, noun_forms
    assert set(noun_forms({"l": "kuća", "g": "f"})) >= {"kuće", "kući", "kuću", "kućom", "kućama"}
    assert set(noun_forms({"l": "grad", "g": "m", "pl": "gradovi"})) >= {"grada", "gradu", "gradom", "gradovi", "gradova", "gradovima", "gradove"}
    assert set(noun_forms({"l": "posao", "g": "m", "st": "posl", "pl": "poslovi"})) >= {"posla", "poslu", "poslom", "poslovi"}
    assert set(noun_forms({"l": "prijatelj", "g": "m"})) >= {"prijatelja", "prijateljem", "prijatelji"}
    assert set(adj_forms({"l": "dobar", "st": "dobr", "cmp": "bolji"})) >= {"dobra", "dobrog", "bolji", "najbolji", "boljeg"}
    assert "našeg" in adj_forms({"l": "naš"})


if __name__ == "__main__":
    test_translit()
    test_paradigm()
    test_lemmas()
    print("serbian: ok")
