import copy
import glob
import os
import shutil

import pytest
from lxml import etree

from pta_collate import collation, export_other, export_tei, extract, project
from pta_collate.align import run_aligner
from pta_collate.normalize import Profile, forms
from pta_collate.units import build
from pta_collate.validate import validate

DATA = os.path.join(os.path.dirname(__file__), "data")
TEI = {"t": "http://www.tei-c.org/ns/1.0"}


def make_project(engine="builtin"):
    p = project.new_project()
    p["structure_witness"] = "Ps"
    p["editor"] = {"name": "Test", "id": "TT"}
    p["aligner"]["engine"] = engine
    for f in sorted(glob.glob(os.path.join(DATA, "pta0013*Ms*.xml"))):
        wid = f.split("pta-Ms")[1][:-4]
        p["witnesses"].append({"file": f, "id": wid, "siglum": wid, "include": True, "layers": "both"})
    return p


@pytest.fixture(scope="module")
def run():
    p = make_project()
    return p, collation.run(p)


# ------------------------------------------------------------------ extraction
def test_layers_and_word_internal_correction():
    toks = extract.extract(os.path.join(DATA, "pta0013.pta003.pta-MsLa.xml"))
    assert set(toks) == {"La_ac", "La_pc"}
    ac = [t.t for t in toks["La_ac"]]
    pc = [t.t for t in toks["La_pc"]]
    assert "περιήγγειλεν" in ac and "περιήγγελεν" in pc       # <subst> inside a word
    assert "γράμματα," in pc                                    # <lb break="no"/> joins
    assert any("nomSac" in t.flags for t in toks["La_pc"])      # nomina sacra expanded
    assert toks["La_pc"][0].page == "131v"


def test_witness_without_corrections_has_one_layer(tmp_path):
    src = os.path.join(DATA, "pta0013.pta003.pta-MsLa.xml")
    tree = etree.parse(src)
    for el in list(tree.getroot().iter("{http://www.tei-c.org/ns/1.0}subst", "{http://www.tei-c.org/ns/1.0}del",
                                       "{http://www.tei-c.org/ns/1.0}add")):
        if el.getparent() is not None:
            el.getparent().remove(el)
    out = tmp_path / "x.xml"
    tree.write(str(out), encoding="utf-8")
    assert list(extract.extract(str(out))) == ["La"]


def test_segments_found():
    info = extract.read_info(os.path.join(DATA, "pta0013.pta003.pta-MsPs.xml"))
    assert info.segments["milestone:section"] == ["1", "2", "3", "4"]


# --------------------------------------------------------------- normalisation
def test_normalisation_forms():
    p = Profile.from_dict(None)
    c, n, o = forms("Χριστοῦ·", p)
    assert c == "χριστοῦ" and n == "χριστου"
    assert forms("ἀκραιφνὲς.", p)[2] == forms("ἀκρεφνὲς,", p)[2]   # itacism folded in o only
    assert forms("ἀκραιφνὲς.", p)[1] != forms("ἀκρεφνὲς,", p)[1]
    assert forms("εἶπεν", p)[1] == forms("εἶπε", p)[1]            # ν ephelkystikon
    assert forms("οὐδέν", p)[1] != forms("οὐδέ", p)[1]            # but not in οὐδέν
    assert forms("·", p) == ("", "", "")


# --------------------------------------------------------------------- aligner
def test_builtin_aligner_keeps_order_and_matches_similar_words():
    seqs = {"A": [("a1", "και"), ("a2", "πριν"), ("a3", "κομιζεσθαι")],
            "B": [("b1", "και"), ("b2", "κομιζεσθε")]}
    rows = run_aligner(seqs, {"engine": "builtin"})
    assert {"A": ["a3"], "B": ["b2"]} in rows
    assert {"A": ["a2"]} in rows


@pytest.mark.skipif(not shutil.which("java"), reason="Java fehlt")
def test_collatex_runs_on_current_java():
    seqs = {"A": [("a1", "και"), ("a2", "πριν")], "B": [("b1", "και"), ("b2", "πριν")]}
    rows = run_aligner(seqs, {"engine": "collatex", "algorithm": "dekker", "comparator": "equality"})
    assert rows == [{"A": ["a1"], "B": ["b1"]}, {"A": ["a2"], "B": ["b2"]}]


# ----------------------------------------------------------------------- units
def test_units_classification(run):
    p, res = run
    m = build(res, p)
    var = [u for u in m.units if u["variant"]]
    assert len(var) > 80
    # περιήγγελλεν (Ps) is an orthographic variant of περιήγγελεν (La^c, Vi)
    u = next(u for u in var if any(r["t"] == "περιήγγελλεν" for r in u["readings"]))
    ps = next(r for r in u["readings"] if r["t"] == "περιήγγελλεν")
    assert ps["cause"] == "orthographic" and ps["group"]
    # Pg transposes ὑμῶν ἀγάπης
    assert any(r["type"] == "transposition" for u in var for r in u["readings"])


def test_merge_adjacent_units(run):
    p, res = run
    m1 = build(res, p)
    p2 = copy.deepcopy(p)
    p2["units"]["merge_adjacent"] = False
    p2["units"]["detect_transpositions"] = False
    m2 = build(res, p2)
    assert len([u for u in m1.units if u["variant"]]) <= len([u for u in m2.units if u["variant"]])


def test_edits_join_split_lem_and_replay(run):
    p, res = run
    p = copy.deepcopy(p)
    m = build(res, p)
    var = [u for u in m.units if u["variant"]]
    u = var[3]
    idx = m.units.index(u)
    nxt = m.units[idx + 1]
    p["edits"].append({"op": "join", "at": nxt["key"]})
    m = build(res, p)
    joined = m.by_key[u["key"]]
    assert len(joined["rows"]) == len(u["rows"]) + len(nxt["rows"])
    p["edits"].append({"op": "split", "at": nxt["key"]})
    m = build(res, p)
    assert m.by_key[u["key"]]["rows"] == u["rows"]
    r = u["readings"][0]
    p["edits"].append({"op": "lem", "unit": u["key"], "reading": r["c"]})
    m = build(res, p)
    assert m.by_key[u["key"]]["lem"] == r["id"]
    assert all(s["ok"] for s in m.status)


def test_move_token(run):
    p, res = run
    p = copy.deepcopy(p)
    m = build(res, p)
    u = next(u for u in m.units if u["variant"] and len(u["grid"]) == 1 and u["seg"] != "0")
    prev = m.units[m.units.index(u) - 1]
    wit = next(w for w in m.wits if u["cells"].get(w, {}).get("tokens"))
    tok = u["cells"][wit]["tokens"][0]
    p["edits"].append({"op": "move", "token": tok, "dir": "prev"})
    m2 = build(res, p)
    assert m2.status[0]["ok"]
    assert tok not in [t for x in m2.units if x["key"] == u["key"] for t in x["cells"].get(wit, {}).get("tokens", [])]


# ------------------------------------------------------------------------- TEI
def test_tei_valid_against_collation_schema(run):
    p, res = run
    xml = export_tei.export_tei(build(res, p), p)
    r = validate(xml, "collation")
    assert r["valid"], r
    assert r["schematron"]["warnings"] > 0     # units without lem are reported as warnings only
    doc = etree.fromstring(xml)
    assert doc.find(".//t:listWit/t:witness[@xml:id='La']", {**TEI, "xml": "http://www.w3.org/XML/1998/namespace"}) is not None
    assert doc.xpath("//t:rdg[@varSeq='1'][@wit='#La']", namespaces=TEI)
    assert doc.xpath("//t:rdgGrp/t:rdg[@cause='orthographic']", namespaces=TEI)
    # correction layers: own rdg with varSeq, grouped with the witnesses that read the same
    assert doc.xpath("//t:rdgGrp[t:rdg[@varSeq='2'] and t:rdg[not(@varSeq)]]", namespaces=TEI)
    for grp in doc.xpath("//t:rdgGrp[t:rdg[@varSeq]][not(t:rdg[@cause])]", namespaces=TEI):
        from pta_collate.normalize import strip_punctuation
        texts = {strip_punctuation("".join(r.xpath(".//text()[not(ancestor::t:del)]", namespaces=TEI))).strip()
                 for r in grp}
        assert len(texts) == 1, texts
    # the reading after correction keeps the markup of the transcription (PTA guidelines)
    subst = doc.xpath("//t:rdg[@varSeq='2']/t:subst[t:del][t:add]", namespaces=TEI)
    assert subst, "subst in varSeq 2"
    assert doc.xpath("//t:rdg[@varSeq='2']//t:add[@place]", namespaces=TEI)
    assert doc.xpath("//t:rdg[@varSeq='2']//t:del[@rend]", namespaces=TEI)
    assert not doc.xpath("//t:rdg[@varSeq='1']//t:del | //t:rdg[@varSeq='1']//t:add", namespaces=TEI)
    assert not doc.xpath("//t:lem", namespaces=TEI)


def test_tei_with_all_lemmata_is_valid_against_full_schema(run):
    p, res = run
    p = copy.deepcopy(p)
    m = build(res, p)
    for u in m.units:
        if u["variant"]:
            best = max(u["readings"], key=lambda r: (len(r["wits"]), bool(r["c"])))
            p["edits"].append({"op": "lem", "unit": u["key"], "reading": best["c"]})
    m = build(res, p)
    xml = export_tei.export_tei(m, p)
    r = validate(xml, "full")
    assert r["valid"], (r["relaxng"]["errors"][:5], r["schematron"]["errors"][:5])


def test_nested_variants(run):
    p, res = run
    p = copy.deepcopy(p)
    m = build(res, p)
    # a unit where La omits text, followed by a unit with orthographic variation among the others
    target = None
    for i, u in enumerate(m.units[:-1]):
        nxt = m.units[i + 1]
        if u["variant"] and nxt["variant"] and u["seg"] == nxt["seg"]:
            target = (u, nxt)
            break
    u, nxt = target
    p["edits"].append({"op": "join", "at": nxt["key"]})
    m = build(res, p)
    joined = m.by_key[u["key"]]
    lem = max(joined["readings"], key=lambda r: len(r["wits"]))
    p["edits"] += [{"op": "lem", "unit": u["key"], "reading": lem["c"]}, {"op": "nest", "unit": u["key"], "value": True}]
    m = build(res, p)
    xml = export_tei.export_tei(m, p)
    assert validate(xml, "collation")["valid"]


def test_other_exports(run):
    p, res = run
    m = build(res, p)
    assert export_other.export_csv(m).decode("utf-8-sig").startswith("Abschnitt,")
    assert b"MATRIX" in export_other.export_nexus(m)
    assert b'"table"' in export_other.export_collatex_json(m)
    html = export_other.export_synopsis_html(m, p)
    assert b"PTASynopsis.mountStandalone" in html
    assert b"PTAGraph" in html and b"bibelexegese.bbaw.de" in html and b"0000-0001-5382-6322" in html
    assert b"googleapis" not in html and b"@import" not in html
    assert b"font-family: 'Gentium Plus'" in html and b"data:font/woff2;base64," in html


def test_project_roundtrip(tmp_path, run):
    p, _ = run
    path = tmp_path / "x.pta.json"
    project.save(copy.deepcopy(p), str(path))
    q = project.load(str(path))
    assert [w["file"] for w in q["witnesses"]] == [w["file"] for w in p["witnesses"]]


def test_lemma_survives_token_move(run):
    p, res = run
    p = copy.deepcopy(p)
    m = build(res, p)
    u = next(u for u in m.units if u["variant"] and len(u["grid"]) == 1 and u["seg"] != "0"
             and m.units[m.units.index(u) - 1]["seg"] == u["seg"])
    anchors = [t for c in u["cells"].values() for t in c["tokens"]]
    r = max(u["readings"], key=lambda r: len(r["wits"]))
    p["edits"].append({"op": "lem", "unit": u["key"], "reading": r["c"], "wits": r["wits"], "anchors": anchors})
    p["edits"].insert(0, {"op": "move", "token": u["key"], "dir": "prev"})
    m2 = build(res, p)
    assert all(s["ok"] for s in m2.status)
    holder = max(m2.units, key=lambda x: sum(t in anchors for c in x["cells"].values() for t in c["tokens"]))
    assert holder["lem"] is not None


def test_refresh_matches_full_rebuild(run):
    p, res = run
    p = copy.deepcopy(p)
    m = build(res, p)
    var = [u for u in m.units if u["variant"]]
    p["edits"].append({"op": "lem", "unit": var[0]["key"], "reading": var[0]["readings"][-1]["c"]})
    p["edits"].append({"op": "attr", "unit": var[1]["key"], "reading": var[1]["readings"][0]["c"], "key": "cause", "value": "homoioteleuton"})
    fast = m.refresh(p)
    assert fast is m                      # structure reused
    full = build(res, p)
    assert fast.to_json()["units"] == full.to_json()["units"]
    p["edits"].append({"op": "join", "at": var[2]["key"]})
    assert m.refresh(p) is not m          # structural edit → full rebuild


def _mini(tmp_path, body):
    xml = f"""<TEI xmlns="http://www.tei-c.org/ns/1.0"><teiHeader><fileDesc><sourceDesc><msDesc>
      <msIdentifier xml:id="X"/></msDesc></sourceDesc></fileDesc></teiHeader>
      <text><body><div type="edition"><p>{body}</p></div></body></text></TEI>"""
    f = tmp_path / "x.xml"
    f.write_text(xml, encoding="utf-8")
    return [t.t for t in extract.extract(str(f))["X"]]


def test_break_no_joins_words(tmp_path):
    # whitespace before and after the break, line/column/page breaks, notes in between
    assert _mini(tmp_path, "τῆς ἀναστά <lb break=\"no\"/>\n   σεως ἡμῶν") == ["τῆς", "ἀναστάσεως", "ἡμῶν"]
    assert _mini(tmp_path, "μυ<cb n=\"b\" break=\"no\"/>στικόν") == ["μυστικόν"]
    assert _mini(tmp_path, "ἀ<pb n=\"2r\" break=\"no\"/>\n <fw>ρνζ</fw>\n <note>x</note>\n πὸ γῆς") == ["ἀπὸ", "γῆς"]
    assert _mini(tmp_path, "γράμ<lb break=\"no\"/>ματα<lb/>καὶ") == ["γράμματα", "καὶ"]


def test_initial_ekthesis_and_signs(tmp_path):
    # layout whitespace inside/after an initial or ekthesis is no word boundary; a plain space is
    body = ('<hi rend="initial">\n  <hi rend="rubricated">Κ</hi>\n</hi>αλοὶ τῆς '
            '<lb/>\n<g type="paragraphos"/>\n<hi rend="rubricated">\n<hi rend="ekthesis">ἐ</hi>\n</hi>ξ αὐτῶν '
            '<hi rend="ekthesis">ὁ</hi> λόγος μαί<lb break="no"/>\n<g type="doubled_diple"/>νονται')
    words = _mini(tmp_path, body)
    assert words == ["Καλοὶ", "τῆς", "ἐξ", "αὐτῶν", "ὁ", "λόγος", "μαίνονται"]
    f = tmp_path / "x.xml"
    toks = extract.extract(str(f))["X"]
    assert "g:paragraphos" in toks[2].flags and "g:doubled_diple" in toks[6].flags


def test_latin_lookalikes():
    p = Profile.from_dict(None)
    assert forms("Kαλοὶ", p) == forms("Καλοὶ", p)


def test_islands_and_affine_gaps_keep_phrases_together():
    from pta_collate.align.builtin import align_builtin
    a = "και ο λογοσ ην προσ τον θεον και θεοσ ην ο λογοσ ουτοσ ην εν αρχη".split()
    # B omits "και θεοσ ην ο λογοσ" (a repeated-word phrase) and adds one word at the end
    b = "και ο λογοσ ην προσ τον θεον ουτοσ ην εν αρχη προσ".split()
    rows = align_builtin({"A": [(f"a{i}", x) for i, x in enumerate(a)], "B": [(f"b{i}", x) for i, x in enumerate(b)]}, {})
    gaps = [i for i, r in enumerate(rows) if "B" not in r]
    assert gaps == list(range(gaps[0], gaps[0] + 5))      # one contiguous omission of five words
    assert rows[-1] == {"B": ["b11"]}                       # the added word stays alone at the end


def test_long_transposition_is_suggested_and_confirmable(run):
    import random
    from pta_collate.normalize import Profile, forms
    p = Profile.from_dict(None)
    base = "τὸν δὲ ἄνθρωπον πλάσας ἐκ γῆς ἐνεφύσησεν εἰς τὸ πρόσωπον αὐτοῦ πνοὴν ζωῆς καὶ ἐγένετο ὁ ἄνθρωπος εἰς ψυχὴν ζῶσαν· ταῦτα μὲν οὖν ἡ γραφὴ διδάσκει ἡμᾶς περὶ τῆς πλάσεως τοῦ ἀνθρώπου καὶ τῆς ψυχῆς αὐτοῦ".split()
    moved = base[:4] + base[9:22] + base[4:9] + base[22:]          # "ἐκ γῆς ἐνεφύσησεν εἰς τὸ" moved
    seqs = {w: [(f"{w}:{i}", forms(x, p)[1]) for i, x in enumerate(txt)]
            for w, txt in (("A", base), ("B", base), ("C", moved))}
    from pta_collate.align import run_aligner
    rows = run_aligner(seqs, {"engine": "builtin"})
    tokens = {}
    for w, txt in (("A", base), ("B", base), ("C", moved)):
        for i, x in enumerate(txt):
            c, n, o = forms(x, p)
            tokens[f"{w}:{i}"] = dict(id=f"{w}:{i}", wit=w, t=x, c=c, n=n, o=o, segment="1", page=None)
    result = dict(witnesses=[dict(id=w, ms=w, layer=None, siglum=w, label=w, file="", name=w) for w in "ABC"],
                  tokens=tokens, rows=[{"id": f"r{k}", "seg": "1", "cells": r} for k, r in enumerate(rows)],
                  segments=["1"], segmentation="none", settings={})
    proj = {"units": {"merge_adjacent": True, "detect_transpositions": True, "transposition_window": 6,
                      "detect_long_transpositions": True, "long_transposition_distance": 150, "lacuna_min": 0},
            "edits": []}
    m = build(result, proj)
    sug = [u for u in m.units if u.get("suggest") and u["suggest"].get("next")]
    assert len(sug) == 1
    a, b = sug[0]["key"], sug[0]["suggest"]["next"]
    assert not any(u.get("link") for u in m.units)              # only a suggestion so far
    proj["edits"].append({"op": "link", "a": a, "b": b})
    m = m.refresh(proj)
    assert m.by_key[a]["link"] == {"next": b} and not m.by_key[a].get("suggest")
    proj["edits"] = [{"op": "reject_link", "a": a}]
    m = m.refresh(proj)
    assert not any(u.get("suggest") or u.get("link") for u in m.units)


def test_fused_words_found_and_split(tmp_path):
    from pta_collate.collation import fused_words, split_tokens, fusion_evidence
    from pta_collate.normalize import Profile
    p = Profile.from_dict(None)
    text = "ὁ σωτὴρ ἡμῶν εἶπε τῷ πατρὶ καὶ τῷ υἱῷ"
    wits = {"A": text, "B": text, "C": text, "D": "ὁ σωτὴρ ἡμῶν εἶπε τῷ πατρὶκαὶ τῷ υἱῷ"}
    from pta_collate.normalize import forms
    streams = {}
    for w, t in wits.items():
        streams[w] = []
        for i, x in enumerate(t.split()):
            c, n, o = forms(x, p)
            streams[w].append(dict(id=f"{w}:{i}", wit=w, t=x, c=c, n=n, o=o, page="1r", flags=[]))
    found = fused_words(streams, {}, p)
    assert [(f["wit"], f["word"], f["split"]) for f in found] == [("D", "πατρὶκαὶ", "πατρὶ καὶ")]
    assert found[0]["evidence"] == ["zwei Akzente"]
    assert found[0]["parts"] == ["πατρὶ", "καὶ"] and set(found[0]["support"]) == {"A", "B", "C"}
    seq, done = split_tokens(streams["D"], {"D:5": found[0]["parts"]}, p)
    assert [d["t"] for d in seq] == "ὁ σωτὴρ ἡμῶν εἶπε τῷ πατρὶ καὶ τῷ υἱῷ".split() and done == ["D:5"]
    assert fusion_evidence("σωτῆροςἑρμηνεία,") == ["zwei Akzente", "Spiritus im Wort"]
    assert fusion_evidence("εὐσέβεια") == [] and fusion_evidence("αὐτοῦ·") == []


def _streams(wits, p):
    from pta_collate.normalize import forms
    out = {}
    for w, t in wits.items():
        out[w] = []
        for i, x in enumerate(t.split()):
            c, n, o = forms(x, p)
            out[w].append(dict(id=f"{w}:{i}", wit=w, t=x, c=c, n=n, o=o, page="1r", flags=[]))
    return out


def test_fused_words_in_context():
    """Local comparison: real words written together (ἐπεὶτὰ ~ ἔπειτα), ν ephelkystikon (τῶμὲν),
    three words, only two manuscripts, and words that others write in the same way."""
    from pta_collate.collation import fused_words
    from pta_collate.normalize import Profile
    p = Profile.from_dict(None)
    base = "ἔπειτα λέγει ἐπεὶ τὰ μὲν ἐν τῷ μὲν εἶναι καὶ τὸν θεὸν ὁρᾷ διὰ τοῦτο"
    wits = {"A": base, "B": base, "C": base.replace("διὰ τοῦτο", "διατοῦτο"), "E": base.replace("διὰ τοῦτο", "διατοῦτο"),
            "D": base.replace("ἐπεὶ τὰ", "ἐπεὶτὰ").replace("τῷ μὲν", "τῷμὲν").replace("καὶ τὸν θεὸν", "καὶτὸνθεὸν")
                     .replace("διὰ τοῦτο", "διατοῦτο")}
    found = {f["word"]: f for f in fused_words(_streams(wits, p), {}, p) if f["wit"] == "D"}
    assert found["ἐπεὶτὰ"]["split"] == "ἐπεὶ τὰ"
    assert found["τῷμὲν"]["split"] == "τῷ μὲν"
    assert found["καὶτὸνθεὸν"]["split"] == "καὶ τὸν θεὸν"
    assert "διατοῦτο" not in found          # as many manuscripts write it so as separate it: no error
    two = fused_words(_streams({"A": "ὁ σωτὴρ ἡμῶν εἶπε", "B": "ὁ σωτὴρἡμῶν εἶπε"}, p), {}, p)
    assert [f["split"] for f in two] == ["σωτὴρ ἡμῶν"]


def test_ignore_punctuation_option():
    from pta_collate.normalize import Profile, forms
    on, off = Profile.from_dict(None), Profile.from_dict({"ignore_punctuation": False})
    assert forms("γράμματα,", on)[0] == forms("γράμματα·", on)[0]
    assert forms("γράμματα,", off)[0] != forms("γράμματα·", off)[0]
    assert forms("γράμματα,", off)[1] == forms("γράμματα·", off)[1]      # alignment unaffected
    assert forms("·", on) == ("", "", "") and forms("·", off)[0] == "·"   # punctuation tokens kept


def test_punctuation_only_difference_is_not_orthographic(run):
    p, _ = run
    p = copy.deepcopy(p)
    p["normalization"] = dict(p["normalization"], ignore_punctuation=False)
    res = collation.run(p)
    m = build(res, p)
    punct = [r for u in m.units if u["variant"] for r in u["readings"]
             if r["group"] and r["cause"] is None and r["c"] != r["t"].lower().strip()]
    for u in m.units:
        for r in u["readings"]:
            if r["cause"] == "orthographic":
                from pta_collate.normalize import strip_punctuation
                heads = [x for x in u["readings"] if x["group"] == r["group"] and x is not r]
                assert any(strip_punctuation(h["c"]) != strip_punctuation(r["c"]) for h in heads)


def test_editorial_readings_and_lacunae(run):
    """Conjecture as lemma (resp: collating editor), correction from an earlier edition (source),
    proposition with cert, manual lacuna, and validity against both schemas."""
    p, res = run
    p = copy.deepcopy(p)
    p["sources"] = [{"id": "Oberg", "kind": "bibl", "name": "Oberg 1969"},
                    {"id": "Maas", "kind": "person", "name": "Paul Maas", "ref": "https://d-nb.info/gnd/118575384"}]
    m = build(res, p)
    var = [u for u in m.units if u["variant"]]
    inv = next(u for u in m.units if not u["variant"])
    a, b = var[3], var[5]
    p["edits"] += [
        {"op": "conj", "unit": a["key"], "id": "c1", "kind": "conjecture", "text": "δοκιμάζεσθαι"},
        {"op": "lem", "unit": a["key"], "editorial": "c1"},
        {"op": "conj", "unit": b["key"], "id": "c2", "kind": "correction", "text": "λέγει", "source": "Oberg"},
        {"op": "conj", "unit": b["key"], "id": "c3", "kind": "proposition", "text": "λέγων", "resp": "Maas", "cert": "low"},
        {"op": "conj", "unit": inv["key"], "id": "c4", "kind": "lacunam_indicavit", "resp": "Maas"},
    ]
    m = build(res, p)
    ua = m._unit(a["key"])
    assert ua["lem"] == "e:c1" and any(r["type"] == "conjecture" for r in ua["readings"])
    assert m._unit(inv["key"])["variant"]
    # refresh (unit edits only) gives the same result, and deleting removes the reading again
    p2 = copy.deepcopy(p)
    p2["edits"].append({"op": "conj", "unit": b["key"], "id": "c2", "delete": True})
    m2 = m.refresh(p2)
    assert not any(r["id"] == "e:c2" for r in m2._unit(b["key"])["readings"])
    m = build(res, p)
    xml = export_tei.export_tei(m, p)
    doc = etree.fromstring(xml)
    assert doc.xpath("//t:app/t:lem[@type='conjecture'][@resp='#TT']", namespaces=TEI)
    assert doc.xpath("//t:app/t:rdg[@type='correction'][@source='#Oberg']", namespaces=TEI)
    assert doc.xpath("//t:app/t:rdg[@type='proposition'][@resp='#Maas'][@cert='low']", namespaces=TEI)
    assert doc.xpath("//t:app/t:rdg[@type='lacunam_indicavit'][not(node())]", namespaces=TEI)
    assert doc.xpath("//t:sourceDesc/t:listBibl/t:bibl[@xml:id='Oberg']", namespaces={**TEI, "xml": "http://www.w3.org/XML/1998/namespace"})
    assert doc.xpath("//t:sourceDesc/t:listPerson/t:person/t:persName[@ref]", namespaces=TEI)
    r = validate(xml, "collation")
    assert r["valid"], (r["relaxng"]["errors"][:5], r["schematron"]["errors"][:5])


def test_manual_lacuna_and_witness_markers(run):
    p, res = run
    p = copy.deepcopy(p)
    p["units"]["lacuna_min"] = 0
    m = build(res, p)
    # an omission of one manuscript becomes a lacuna and back
    u = next(u for u in m.units if u["variant"] and any(r["c"] == "" and len({m.ms_of[w] for w in r["wits"]}) == 1
                                                         for r in u["readings"]))
    r = next(r for r in u["readings"] if r["c"] == "" and len({m.ms_of[w] for w in r["wits"]}) == 1)
    ms = m.ms_of[r["wits"][0]]
    opts = {o["ms"]: o for o in m.presence_options(u)}
    assert opts[ms]["state"] == "omission"
    p["edits"].append({"op": "lacuna", "ms": ms, "at": u["key"], "value": True})
    m = build(res, p)
    u2 = m._unit(u["key"])
    assert all(c in u2["absent"] for c in m.cids_of(ms)) and u2["absent_kind"][m.cids_of(ms)[0]] == "lacuna"
    xml = export_tei.export_tei(m, p)
    doc = etree.fromstring(xml)
    assert doc.xpath(f"//t:app[@type='witnesses']/t:rdg[@wit='#{ms}']/t:lacunaStart", namespaces=TEI)
    assert doc.xpath(f"//t:app[@type='witnesses']/t:rdg[@wit='#{ms}']/t:lacunaEnd", namespaces=TEI)
    assert doc.xpath("//t:app[@type='witnesses']/t:rdg/t:witStart", namespaces=TEI)
    assert validate(xml, "collation")["valid"]
    p["edits"].append({"op": "lacuna", "ms": ms, "at": u["key"], "value": False})
    m = build(res, p)
    assert not m._unit(u["key"])["absent"]


def test_inserted_rows_for_editorial_readings(run):
    """A conjectured addition and a suspected lacuna in new rows between two places."""
    p, res = run
    p = copy.deepcopy(p)
    m = build(res, p)
    inv = [u for u in m.units if not u["variant"]]
    a, b = inv[2], inv[4]
    p["edits"] += [
        {"op": "insert", "id": "i1", "after": a["key"]},
        {"op": "conj", "unit": "ins:i1", "id": "k1", "kind": "conjecture", "text": "δή"},
        {"op": "lem", "unit": "ins:i1", "editorial": "k1"},
        {"op": "insert", "id": "i2", "before": b["key"]},
        {"op": "conj", "unit": "ins:i2", "id": "k2", "kind": "lacunam_indicavit", "resp": "TT"},
    ]
    m = build(res, p)
    assert all(s["ok"] for s in m.status), [s for s in m.status if not s["ok"]]
    keys = [u["key"] for u in m.units]
    assert keys.index("ins:i1") == keys.index(m._unit(a["key"])["key"]) + 1
    assert keys.index("ins:i2") == keys.index(m._unit(b["key"])["key"]) - 1
    u1 = m.by_key["ins:i1"]
    assert u1["variant"] and u1["lem"] == "e:k1" and not u1["rows"]
    xml = export_tei.export_tei(m, p)
    doc = etree.fromstring(xml)
    app = doc.xpath("//t:app[t:lem[@type='conjecture'] = 'δή']", namespaces=TEI)
    assert app and app[0].xpath("t:rdg[not(node())]/@wit", namespaces=TEI)
    assert doc.xpath("//t:app[t:rdg[@type='lacunam_indicavit']]/t:rdg[@wit][not(node())]", namespaces=TEI)
    assert validate(xml, "collation")["valid"]
    # the refresh path (unit edits only) keeps the inserted rows; deleting removes them
    p2 = copy.deepcopy(p)
    p2["edits"].append({"op": "conj", "unit": "ins:i1", "id": "k1", "delete": True})
    m2 = m.refresh(p2)
    assert "ins:i1" in m2.by_key and not m2.by_key["ins:i1"]["variant"]
    p["edits"].append({"op": "insert", "id": "i1", "delete": True})
    m = build(res, p)
    assert "ins:i1" not in m.by_key and "ins:i2" in m.by_key


def _three_witnesses(texts, units=None, edits=()):
    from pta_collate.normalize import Profile, forms
    p = Profile.from_dict(None)
    seqs = {w: [(f"{w}:{i}", forms(x, p)[1]) for i, x in enumerate(t)] for w, t in texts.items()}
    rows = run_aligner(seqs, {"engine": "builtin"})
    tokens = {}
    for w, t in texts.items():
        for i, x in enumerate(t):
            c, n, o = forms(x, p)
            tokens[f"{w}:{i}"] = dict(id=f"{w}:{i}", wit=w, t=x, c=c, n=n, o=o, segment="1", page=None)
    result = dict(witnesses=[dict(id=w, ms=w, layer=None, siglum=w, label=w, file="", name=w) for w in texts],
                  tokens=tokens, rows=[{"id": f"r{k}", "seg": "1", "cells": r} for k, r in enumerate(rows)],
                  segments=["1"], segmentation="none", settings={})
    u = {"merge_adjacent": True, "detect_transpositions": True, "transposition_window": 6, "split_displaced": True,
         "detect_long_transpositions": True, "long_transposition_distance": 150, "lacuna_min": 0}
    u.update(units or {})
    return result, {"units": u, "edits": list(edits)}


DISPLACED = {
    "A": "τοῦτο γὰρ ὁ θεὸς ἐποίησεν ὅτε ὁ ἀδὰμ διεπλάσθη καὶ τὴν ψυχὴν ἔλαβεν καὶ οὕτως ἐγένετο ἄνθρωπος ζῶν".split(),
    "B": "τοῦτο γὰρ ὁ θεὸς ἐποίησεν ὅτε ὁ ἀδὰμ διεπλάσθη καὶ τὴν ψυχὴν ἔλαβεν καὶ οὕτως ἐγένετο ἄνθρωπος ζῶν".split(),
    "C": "τοῦτο γὰρ ὁ θεὸς ἐποίησεν ὅτε ὁ ἀδὰμ διεπλάσθη ἔλαβε τὴν ψυχήν καὶ οὕτως ἐγένετο ἄνθρωπος ζῶν".split(),
}


def test_displaced_word_becomes_transposition():
    result, proj = _three_witnesses(DISPLACED, {"split_displaced": False})
    m = build(result, proj)
    assert not any(u["transposition"] for u in m.units)            # aligner: ἔλαβε against καὶ
    result, proj = _three_witnesses(DISPLACED)
    m = build(result, proj)
    tr = [u for u in m.units if u["transposition"]]
    assert len(tr) == 1
    texts = {r["t"] for r in tr[0]["readings"]}
    assert texts == {"τὴν ψυχὴν ἔλαβεν", "ἔλαβε τὴν ψυχήν"}
    kai = next(u for u in m.units if u["variant"] and any(r["t"] == "καὶ" for r in u["readings"]))
    assert {r["type"] for r in kai["readings"]} >= {"omission"}


def test_move_into_new_row():
    result, proj = _three_witnesses(DISPLACED, {"split_displaced": False})
    m = build(result, proj)
    u = next(u for u in m.units if u["variant"] and any(r["t"] == "ἔλαβε" for r in u["readings"]))
    tid = u["cells"]["C"]["tokens"][0]
    n = len(m.rows)
    proj["edits"].append({"op": "move", "token": tid, "dir": "newnext"})
    m2 = build(result, proj)
    assert m2.status[0]["ok"] and len(m2.rows) == n + 1
    i = m2.where[tid]
    assert list(m2.rows[i]["cells"]) == ["C"] and "C" not in m2.rows[i - 1]["cells"]
    assert any(u["transposition"] for u in m2.units)               # now recognisable
    # a token that is not at the edge of its cell cannot be moved
    proj["edits"] = [{"op": "move", "token": "A:1", "dir": "newprev", "with": ["A:2"]}]
    assert not build(result, proj).status[0]["ok"]


SUBVARIANTS = {
    **{w: "ὅτε ὁ ἀδὰμ διεπλάσθη τὴν ψυχὴν ἔλαβεν καὶ οὕτως ἐγένετο ἄνθρωπος ζῶν κατὰ τὴν γραφήν".split() for w in "ABEG"},
    "Mc": "ὅτε ὁ ἀδὰμ διεπλάσθη τὴν ψυχὴν καὶ οὕτως ἐγένετο ἄνθρωπος ζῶν κατὰ τὴν γραφήν".split(),
    "Md": "ὅτε ὁ ἀδὰμ διεπλάσθη ψυχὴν ἔλαβεν καὶ οὕτως ἐγένετο ἄνθρωπος ζῶν κατὰ τὴν γραφήν".split(),
    "Mx": "ὅτε ὁ ἀδὰμ διεπλάσθη τὴν ψυχήν ἔλαβεν καὶ οὕτως ἐγένετο ἄνθρωπος ζῶν κατὰ τὴν γραφήν".split(),
    "Pk": "ὅτε ὁ ἀδὰμ διεπλάσθη ἔλαβε τὴν ψυχήν καὶ οὕτως ἐγένετο ἄνθρωπος ζῶν κατὰ τὴν γραφήν".split(),
    "F": "ὅτε ὁ ἀδὰμ διεπλάσθη καὶ οὕτως ἐγένετο ἄνθρωπος ζῶν κατὰ τὴν γραφήν".split(),
}


def test_sub_variants_are_proposed_and_exported_as_inner_apps():
    result, proj = _three_witnesses(SUBVARIANTS)
    m = build(result, proj)
    u = next(u for u in m.units if u["transposition"])
    by = {r["t"]: r for r in u["readings"]}
    main = by["τὴν ψυχὴν ἔλαβεν"]
    assert by["τὴν ψυχὴν"]["parent"] == main["id"] and by["τὴν ψυχὴν"]["sub_diff"]["missing"] == 1
    assert by["ψυχὴν ἔλαβεν"]["parent"] == main["id"]
    assert by["τὴν ψυχήν ἔλαβεν"]["parent"] == main["id"]
    assert not by["ἔλαβε τὴν ψυχήν"].get("parent") and not by[""].get("parent")   # transposition, omission
    ex = export_tei.TeiExporter(m, proj)
    app = ex.app_el(u)
    T = "{http://www.tei-c.org/ns/1.0}"
    outer = [c for c in app if c.tag in (T + "lem", T + "rdg")]
    assert len(outer) == 3
    fam = next(c for c in outer if "Mc" in c.get("wit"))
    inner = fam.findall(T + "app")
    assert len(inner) == 3 and all(a.find(T + "lem") is not None for a in inner)
    assert inner[0].find(T + "rdg").get("wit") == "#Md" and inner[0].find(T + "rdg").get("type") == "omission"
    assert inner[1].find(T + "rdg").get("cause") == "orthographic"
    assert inner[2].find(T + "rdg").get("wit") == "#Mc"
    # the editor can make a sub-variant an own reading again; confirm keeps the proposal
    proj["edits"] = [{"op": "attr", "unit": u["key"], "reading": "τὴν ψυχὴν", "key": "parent", "value": None}]
    m2 = build(result, proj)
    u2 = m2.by_key[u["key"]]
    assert not next(r for r in u2["readings"] if r["t"] == "τὴν ψυχὴν").get("parent")
    assert next(r for r in u2["readings"] if r["t"] == "ψυχὴν ἔλαβεν")["parent"]


def test_sub_variant_with_many_missing_words_is_flagged():
    from pta_collate.units import assign_parents
    words = "α1 β2 γ3 δ4 ε5 ζ6".split() + ["ηη7"]
    tokens, grid = {}, []
    texts = {"A": words, "B": words, "C": words[:1] + [""] * 4 + words[5:], "D": ["ωω"] + words[1:],
             "E": words[:6] + ["θθ"], "F": [""] * 7}
    for k in range(len(words)):
        cells = {}
        for w, tx in texts.items():
            if tx[k]:
                tid = f"{w}:{k}"
                tokens[tid] = {"t": tx[k], "c": tx[k], "o": tx[k]}
                cells[w] = [tid]
        grid.append({"id": f"r{k}", "cells": cells})
    readings = []
    for i, (w, tx) in enumerate([("A", words), ("C", texts["C"]), ("D", texts["D"]), ("E", texts["E"]), ("F", texts["F"])]):
        c = " ".join(x for x in tx if x)
        readings.append({"id": f"r{i}", "c": c, "t": c, "wits": ["A", "B"] if w == "A" else [w], "gap": None,
                         "type": None, "cause": None, "group": None, "override": {}})
    u = {"variant": True, "grid": grid, "readings": readings, "lem": None}
    assign_parents(u, tokens)
    c = readings[1]
    assert c["parent"] == "r0" and c["sub_diff"]["missing"] == 4 and c.get("sub_warn")
    assert readings[3]["parent"] == "r0" and not readings[3].get("sub_warn")
    assert not readings[4].get("parent")                      # omission of the whole unit: own reading


def test_check_reports_lines_in_file(run):
    p, _ = run
    res = collation.check(p)
    fu = [f for f in res["fused"] if f["word"] == "διατοῦτο" and f["wit"] == "La"]
    assert fu and fu[0]["lines"]
    line = open(fu[0]["file"], encoding="utf-8").read().split("\n")[fu[0]["lines"][0] - 1]
    assert "διατοῦτο" in line


def test_source_lines_across_tags(tmp_path):
    f = tmp_path / "t.xml"
    f.write_text('<TEI>\n<pb n="1r"/>\nκαὶ ἄλ<lb break="no"/>\nλος\n<pb n="1v"/>\nKαὶ\n</TEI>\n', encoding="utf-8")
    assert collation.source_lines(str(f), "1r", "ἄλλος") == [3]
    assert collation.source_lines(str(f), "1v", "Kαὶ") == [6]
    assert collation.source_lines(str(f), "1v", "nicht da") == []


def test_witness_date_from_history_origin(tmp_path, run):
    src = os.path.join(DATA, "pta0013.pta003.pta-MsLa.xml")
    txt = open(src, encoding="utf-8").read()
    dated = txt.replace("</msIdentifier>", '</msIdentifier><history><origin><origDate notAfter="1300" notBefore="1200">13th cent.</origDate></origin></history>', 1)
    f = tmp_path / "pta0013.pta003.pta-MsLa.xml"
    f.write_text(dated, encoding="utf-8")
    info = extract.read_info(str(f))
    assert info.orig_date == "13th cent." and info.orig_date_attrs == {"notBefore": "1200", "notAfter": "1300"}
    other = tmp_path / "other.xml"
    other.write_text(txt.replace("</msIdentifier>", '</msIdentifier><history><origin><origDate xml:id="d1" when-iso="1263-05" '
                                 'calendar="#julian" datingMethod="#julian">1263</origDate></origin></history>', 1), encoding="utf-8")
    assert extract.read_info(str(other)).orig_date_attrs == {"when-iso": "1263-05", "calendar": "#julian", "datingMethod": "#julian"}
    assert extract.read_info(src).orig_date is None                # nothing there: stays empty
    p, res = run
    p = copy.deepcopy(p)
    for w in p["witnesses"]:
        if w["id"] == "La":
            w["file"] = str(f)
    res = collation.run(p)
    xml = export_tei.export_tei(build(res, p), p)
    root = etree.fromstring(xml)
    od = root.find(".//t:listWit/t:witness[@xml:id='La']/t:origDate", {**TEI, "xml": "http://www.w3.org/XML/1998/namespace"})
    assert od is not None and od.text == "13th cent." and od.get("notBefore") == "1200" and od.get("notAfter") == "1300"


def test_refsdecl_cllg_is_last(run):
    p, res = run
    root = etree.fromstring(export_tei.export_tei(build(res, p), p))
    enc = root.find(".//t:encodingDesc", TEI)
    names = [(etree.QName(c).localname, c.get("{http://www.w3.org/XML/1998/namespace}id")) for c in enc]
    refs = [i for n, i in names if n == "refsDecl"]
    assert refs[-1] == "cllg" and names.index(("refsDecl", "cllg")) + 1 == names.index(("editorialDecl", None))
    cp = enc.find("t:refsDecl[@xml:id='cllg']/t:cRefPattern", {**TEI, "xml": "http://www.w3.org/XML/1998/namespace"})
    assert cp.get("matchPattern") == r"urn:cts:greekLit:(tlg[0-9]{4})\.(tlg[0-9]{3})\.(.+)"
    assert cp.get("replacementPattern") == "https://gitlab.inria.fr/almanach/cllg/freed-corpus/-/blob/main/data/$1/$2/$1.$2.$3"
    assert cp.findtext("t:p", namespaces=TEI) == "References to CLLG-CTS-URNs"
