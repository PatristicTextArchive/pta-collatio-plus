"""TEI export following the PTA schema (parallel segmentation, positive apparatus).

Without a chosen lemma every variation unit is written as
``<app type="variants">`` containing only ``<rdg>`` elements. Such files validate
against ``schema/tei-pta_collation.*`` (the PTA schema without the lemma
constraint). As soon as a lemma is chosen for every unit, the same file also
validates against the full PTA schema.
"""

from __future__ import annotations

import copy
import os
from collections import OrderedDict

from lxml import etree

from . import __version__
from . import extract as ex
from .project import now
from .normalize import strip_punctuation
from .units import Model, nested_lemma

TEI = ex.TEI
XML = "http://www.w3.org/XML/1998/namespace"
SCHEMA_URL = "https://raw.githubusercontent.com/PatristicTextArchive/Schema/master/tei-pta.rng"
COLLATION_SCHEMA = "tei-pta_collation.rng"

# refsDecl the PTA schema requires in every file (added when the source transcription lacks them)
DEFAULT_REFSDECL = {
    "biblical": ("(.+):(.+):([0-9]+):([0-9]+)[\\-\\.]*[0-9]*",
                 "https://www.bibelwissenschaft.de/bibelstelle/$2$3,$4/$1",
                 "Noted are references to a biblical book, chapter, verse, sc. LXX:Gn:1:1."),
    "pta": ("(.+)", "https://pta.bbaw.de/text/$1", "References to texts in the PTA are given as PTA-URNs."),
    "perseus": ("(.+)", "https://scaife.perseus.org/reader/$1",
                "References to texts in the Perseus Digital Library are given as CTS-URNs."),
    "cllg": ("(.+)", "https://gitlab.inria.fr/almanach/cllg/freed-corpus/-/search?search=$1",
             "References to texts of the Corpus Liberatum Linguae Graecae are given as CTS-URNs."),
}


def E(tag, attrib=None, text=None, *children):
    el = etree.Element(f"{{{TEI}}}{tag}", {k: v for k, v in (attrib or {}).items() if v not in (None, "")},
                       nsmap={None: TEI})
    if text:
        el.text = text
    for c in children:
        el.append(c)
    return el


def _sub(parent, tag, attrib=None, text=None):
    el = etree.SubElement(parent, f"{{{TEI}}}{tag}", {k: v for k, v in (attrib or {}).items() if v not in (None, "")})
    if text:
        el.text = text
    return el


def _append_text(parent, text):
    """Append text to the end of an element (as text or tail of the last child)."""
    if not text:
        return
    if len(parent):
        last = parent[-1]
        cur = last.tail or ""
        if cur.endswith(" ") and text.startswith(" "):
            text = text.lstrip(" ")
        last.tail = cur + text
    else:
        cur = parent.text or ""
        if (cur.endswith(" ") or not cur) and text.startswith(" "):
            text = text.lstrip(" ")
        parent.text = cur + text


class TeiExporter:
    def __init__(self, model: Model, proj: dict, schema_href: str | None = None, unit_keys: bool = False):
        self.m = model
        self.unit_keys = unit_keys  # @n = unit key, only for the variance overview (link back to the synopsis)
        self.proj = proj
        self.schema_href = schema_href
        self.wit = {w["id"]: w for w in model.result["witnesses"]}
        # manuscripts in project order
        self.ms_order = []
        for w in model.result["witnesses"]:
            if w["ms"] not in self.ms_order:
                self.ms_order.append(w["ms"])
        self.layers = {ms: [w["id"] for w in model.result["witnesses"] if w["ms"] == ms] for ms in self.ms_order}
        self.pages = {ms: None for ms in self.ms_order}
        self.editor_id = (proj.get("editor") or {}).get("id") or "editor"
        self.used_sources: set = set()
        self.app_ids = {}
        n = 0
        for u in model.units:
            if u.get("link"):
                n += 1
                self.app_ids[u["key"]] = f"app-{n:03d}"

    # ------------------------------------------------------------- helpers
    def wit_attr(self, mss):
        order = {m: i for i, m in enumerate(self.ms_order)}
        return " ".join(f"#{m}" for m in sorted(set(mss), key=lambda m: order[m]))

    def _structure_file(self):
        sw = self.proj.get("structure_witness")
        for w in self.m.result["witnesses"]:
            if w["ms"] == sw:
                return w["file"]
        return self.m.result["witnesses"][0]["file"]

    def _hand(self, cid, cell):
        for t in cell["tokens"]:
            h = self.m.tokens[t].get("hand")
            if h:
                return h.lstrip("#")
        return None

    def _fill(self, el, cell_or_tokens, markup: bool = False):
        """Write the text of tokens into an element, wrapping unclear tokens. With ``markup``
        (reading after a correction, varSeq 2) the <add>/<del>/<subst> of the transcription
        are kept inside the reading, as in the PTA guidelines."""
        tids = cell_or_tokens["tokens"] if isinstance(cell_or_tokens, dict) else cell_or_tokens
        parts = []
        for t in tids:
            tok = self.m.tokens[t]
            if tok.get("gap") and tok["t"].startswith("["):
                g = tok["gap"]
                parts.append(("gap", g))
            elif markup and tok.get("markup"):
                parts.append(("markup", tok["markup"]))
            else:
                parts.append(("unclear" if "unclear" in tok.get("flags", []) else "text", self._clean(tok["t"])))
        first = True
        for kind, val in parts:
            sep = "" if first else " "
            first = False
            if kind == "text":
                _append_text(el, sep + val)
            elif kind == "unclear":
                _append_text(el, sep)
                _sub(el, "unclear", None, val)
            elif kind == "markup":
                _append_text(el, sep)
                self._markup(el, val)
            else:
                _append_text(el, sep)
                _sub(el, "gap", {"reason": val.get("reason"), "unit": val.get("unit"), "quantity": val.get("quantity")})

    def _markup(self, el, segs):
        """Segments of one word (see extract._attach_markup) → text, <add>, <del>, <subst>."""
        def attrs(sg):
            a = {}
            if sg.get("hand"):
                a["hand"] = sg["hand"] if sg["hand"].startswith("#") else "#" + sg["hand"]
            if sg["k"] == "add" and sg.get("place"):
                a["place"] = sg["place"]
            if sg["k"] == "del" and sg.get("rend"):
                a["rend"] = sg["rend"]
            return a
        i = 0
        while i < len(segs):
            sg = segs[i]
            if sg["k"] == "t":
                _append_text(el, self._clean(sg["t"]))
                i += 1
                continue
            if sg.get("subst"):
                group = [x for x in segs[i:] if x.get("subst") == sg["subst"]]
                sub = _sub(el, "subst")
                # @hand of the substitution: on <subst>, as in the transcription guidelines
                hands = {x.get("hand") for x in group if x.get("hand")}
                if len(hands) == 1:
                    h = hands.pop()
                    sub.set("hand", h if h.startswith("#") else "#" + h)
                for x in group:
                    a = attrs(x)
                    if "hand" in a and sub.get("hand"):
                        del a["hand"]
                    _sub(sub, x["k"], a, x["t"] or None)
                i += len(group)
                continue
            _sub(el, sg["k"], attrs(sg), sg["t"] or None)
            i += 1

    @staticmethod
    def _clean(t):
        return t.replace("…", "")  # character gaps inside words are not encoded in the reading text

    # --------------------------------------------------------------- units
    def emit_pbs(self, parent, u):
        for ms in self.ms_order:
            cid = next((c for c in self.layers[ms] if c in u["cells"]), None)
            if cid is None:
                continue
            for p in u["cells"][cid]["pages"]:
                if p != self.pages[ms]:
                    _sub(parent, "pb", {"n": p, "edRef": f"#{ms}"})
                    _append_text(parent, " ")
                    self.pages[ms] = p

    def readings_split(self, u, readings):
        """Turn readings of collation witnesses (layers) into reading elements per manuscript.

        Returns a list of dicts ``{reading, mss, varSeq, hand, deletion}``."""
        where = {}
        for r in readings:
            for cid in r["wits"]:
                where[cid] = r
        out: "OrderedDict[str, dict]" = OrderedDict()
        for r in readings:
            plain, special = [], []
            for ms in self.ms_order:
                lay = [c for c in self.layers[ms] if c in where]
                if not lay:
                    continue
                if len(lay) == 1:
                    if where[lay[0]] is r:
                        plain.append(ms)
                    continue
                ac = next(c for c in lay if c.endswith("_ac"))
                pc = next(c for c in lay if c.endswith("_pc"))
                if where[ac] is where[pc]:
                    if where[ac] is r:
                        plain.append(ms)
                else:
                    if where[ac] is r:
                        special.append({"mss": [ms], "varSeq": "1", "hand": None, "deletion": False})
                    if where[pc] is r:
                        special.append({"mss": [ms], "varSeq": "2", "hand": self._hand(pc, u["cells"][pc]),
                                        "deletion": r["c"] == "" and where[ac]["c"] != ""})
            if plain:
                out[r["id"] + ":plain"] = {"reading": r, "mss": plain, "varSeq": None, "hand": None, "deletion": False}
            for i, s in enumerate(special):
                out[f"{r['id']}:{i}:{s['mss'][0]}"] = dict(s, reading=r)
        return list(out.values())

    def reading_el(self, item, u, is_lem):
        r = item["reading"]
        attrs = {"wit": self.wit_attr(item["mss"])}
        if item["varSeq"]:
            attrs["varSeq"] = item["varSeq"]
        cell = None
        if r["c"] and not r.get("gap"):
            cid = next(c for c in r["wits"] if self.wit[c]["ms"] in item["mss"])
            if item["varSeq"] == "2":
                cid = next((c for c in r["wits"] if self.wit[c]["ms"] in item["mss"] and c.endswith("_pc")), cid)
            cell = u["cells"][cid]
        markup = item["varSeq"] == "2" and cell is not None and \
            any(self.m.tokens[t].get("markup") for t in cell["tokens"])
        marked_hand = markup and any(sg.get("hand") for t in cell["tokens"]
                                     for sg in (self.m.tokens[t].get("markup") or []))
        if item["hand"] and not marked_hand:
            attrs["hand"] = "#" + item["hand"]
        rtype = r["type"]
        if item["deletion"]:
            rtype = "deletion"
        if rtype and not (is_lem and rtype in ("omission", "addition")):
            attrs["type"] = rtype
        if r["cause"] and not is_lem:
            attrs["cause"] = r["cause"]
        el = E("lem" if is_lem else "rdg", attrs)
        if r.get("gap"):
            return el  # illegible / damage / fenestra: empty reading with @type
        if cell is not None:
            self._fill(el, cell, markup=markup)
        return el

    def app_el(self, u):
        attrs = {"type": "variants"}
        if self.unit_keys:
            attrs["n"] = u["key"]
        if u["key"] in self.app_ids:
            attrs[f"{{{XML}}}id"] = self.app_ids[u["key"]]
            link = u["link"]
            if link.get("next"):
                attrs["next"] = "#" + self.app_ids.get(link["next"], "")
            if link.get("prev"):
                attrs["prev"] = "#" + self.app_ids.get(link["prev"], "")
        app = E("app", attrs)
        editorial = [r for r in u["readings"] if r.get("editorial")]
        ed_lem = next((r for r in editorial if r["id"] == u["lem"]), None)
        if ed_lem is not None:
            app.append(self.editorial_el(ed_lem, True))
        nested = nested_lemma(u, self.m)
        if any(r.get("parent") for r in u["readings"] if not r.get("editorial")):
            self._families(app, u)
        elif nested:
            self._nested(app, u, *nested)
        else:
            readings = [r for r in u["readings"] if not r.get("editorial")]
            lem = next((r for r in readings if r["id"] == u["lem"]), None)
            if lem:
                readings.remove(lem)
                readings.insert(0, lem)
            items = self.readings_split(u, readings)
            # rdgGrp: orthographic families, and a reading of a correction layer (varSeq) together
            # with the witnesses that have the same text (cf. the PTA guidelines, ὁ γενναῖος ἐκεῖνος)
            groups: "OrderedDict[object, list]" = OrderedDict()
            for it in items:
                g = it["reading"]["group"]
                groups.setdefault(("ortho", g) if g else ("same", it["reading"]["id"]), []).append(it)
            lem_done = False
            for g, its in groups.items():
                container = app
                if len(its) > 1:
                    container = _sub(app, "rdgGrp")
                for it in its:
                    is_lem = (lem is not None and it["reading"] is lem and not lem_done)
                    if is_lem:
                        lem_done = True
                    container.append(self.reading_el(it, u, is_lem))
        for r in editorial:
            if r is not ed_lem:
                app.append(self.editorial_el(r, False))
        if u.get("note"):
            _sub(app, "note", None, u["note"])
        return app

    # ------------------------------------------------------------ sub-variants
    def _families(self, app, u):
        """Readings with sub-variants (units.assign_parents): each own reading becomes one lem or
        rdg for itself and its sub-variants; where they differ, an inner app (with lem = the text
        of the own reading) shows the omitted, added or changed words."""
        readings = [r for r in u["readings"] if not r.get("editorial")]
        kids: "OrderedDict[str, list]" = OrderedDict()
        for r in readings:
            if r.get("parent"):
                kids.setdefault(r["parent"], []).append(r)
        roots = [r for r in readings if not r.get("parent")]
        lem = next((r for r in roots if r["id"] == u["lem"]), None)
        if lem:
            roots.remove(lem)
            roots.insert(0, lem)
        # one proxy reading per family: own witnesses first (their text is the text of the element)
        proxies, fam = [], {}
        for r in roots:
            members = [r] + kids.get(r["id"], [])
            px = dict(r, wits=[w for m in members for w in m["wits"]])
            proxies.append(px)
            fam[px["id"]] = members
        items = self.readings_split(u, proxies)
        groups: "OrderedDict[object, list]" = OrderedDict()
        for it in items:
            g = it["reading"]["group"]
            groups.setdefault(("ortho", g) if g else ("same", it["reading"]["id"]), []).append(it)
        lem_done = False
        for g, its in groups.items():
            container = _sub(app, "rdgGrp") if len(its) > 1 else app
            for it in its:
                is_lem = lem is not None and it["reading"]["id"] == lem["id"] and not lem_done
                if is_lem:
                    lem_done = True
                el = self.reading_el(it, u, is_lem)
                members = fam[it["reading"]["id"]]
                if len(members) > 1 and not it["varSeq"] and not it["reading"].get("gap"):
                    self._fill_family(el, u, members, set(it["mss"]))
                container.append(el)

    def _fill_family(self, el, u, members, mss):
        """Content of the lem/rdg of a family: common text, inner apps where the members differ."""
        el.text = None
        for c in list(el):
            el.remove(c)
        tok = self.m.tokens
        root = members[0]
        cids = [w for m in members for w in m["wits"] if self.wit[w]["ms"] in mss]
        rep = next((w for w in root["wits"] if w in cids), root["wits"][0])

        def row_text(row, w, key="c"):
            return " ".join(tok[t][key] for t in row["cells"].get(w, []) if tok[t][key])

        # runs of rows with the same partition of the witnesses
        runs, last = [], None
        for row in u["grid"]:
            by: "OrderedDict[str, list]" = OrderedDict()
            for w in cids:
                by.setdefault(row_text(row, w), []).append(w)
            part = frozenset(frozenset(v) for v in by.values())
            if runs and part == last:
                runs[-1].append(row)
            else:
                runs.append([row])
            last = part
        for k, rows in enumerate(runs):
            toks = {w: [t for row in rows for t in row["cells"].get(w, [])] for w in cids}
            text = {w: " ".join(tok[t]["c"] for t in toks[w] if tok[t]["c"]) for w in cids}
            if len(set(text.values())) == 1:
                if toks[rep]:
                    _append_text(el, " ")
                    self._fill(el, toks[rep])
                continue
            _append_text(el, " ")
            inner = _sub(el, "app", {"type": "variants"})
            by: "OrderedDict[str, list]" = OrderedDict()
            by[text[rep]] = []
            for w in cids:
                by.setdefault(text[w], []).append(w)
            base = text[rep]
            base_o = " ".join(tok[t]["o"] for t in toks[rep] if tok[t]["o"])
            sub_readings, cells = [], {}
            for i, (c, ws) in enumerate(by.items()):
                first = toks[ws[0]]
                o = " ".join(tok[t]["o"] for t in first if tok[t]["o"])
                rtype = cause = None
                if c != base:
                    if not c:
                        rtype = "omission"
                    elif not base:
                        rtype = "addition"
                    elif o == base_o and strip_punctuation(c) != strip_punctuation(base):
                        cause = "orthographic"
                sub_readings.append({"id": f"s{k}.{i}", "c": c, "t": " ".join(tok[t]["t"] for t in first),
                                     "wits": ws, "type": rtype, "cause": cause, "group": None, "gap": None})
            for w in cids:
                cells[w] = {"tokens": toks[w]}
            pu = {"cells": cells}
            done = False
            for it in self.readings_split(pu, sub_readings):
                is_lem = it["reading"]["c"] == base and not done
                if is_lem:
                    done = True
                inner.append(self.reading_el(it, pu, is_lem))
        if el.text:
            el.text = el.text.lstrip(" ")

    def editorial_el(self, r, is_lem):
        """lem or rdg of an editor: @type conjecture/correction/proposition/lacunam_indicavit,
        @resp (person, also the collating editor) or @source (edition)."""
        ed = r["editorial"]
        attrs = {"type": ed["kind"]}
        if ed.get("source"):
            attrs["source"] = "#" + ed["source"]
        else:
            attrs["resp"] = "#" + (ed.get("resp") or self.editor_id)
            self.used_sources.add(ed.get("resp") or self.editor_id)
        if ed.get("source"):
            self.used_sources.add(ed["source"])
        if ed.get("cert") and ed["kind"] == "proposition" and not is_lem:
            attrs["cert"] = ed["cert"]
        el = E("lem" if is_lem else "rdg", attrs)
        if r["t"]:
            _append_text(el, r["t"])
        return el

    def _nested(self, app, u, outer, inner):
        for grp in outer:
            if grp["is_lem"]:
                lem = _sub(app, "lem", {"wit": self.wit_attr({self.wit[c]["ms"] for c in grp["wits"]})})
                for i, sub in enumerate(inner):
                    sep = " " if i else ""
                    if not sub["variant"]:
                        _append_text(lem, sep + sub["readings"][0]["t"])
                        continue
                    _append_text(lem, sep)
                    inner_app = _sub(lem, "app", {"type": "variants"})
                    rs = sorted(sub["readings"], key=lambda r: not r["is_lem"])
                    head = rs[0]
                    for r in rs:
                        a = {"wit": self.wit_attr({self.wit[c]["ms"] for c in r["wits"]})}
                        if not r["is_lem"]:
                            if r["c"] == "":
                                a["type"] = "omission"
                            elif head["c"] == "":
                                a["type"] = "addition"
                            elif r["o"] == head["o"]:
                                a["cause"] = "orthographic"
                        el = _sub(inner_app, "lem" if r["is_lem"] else "rdg", a)
                        if r["t"]:
                            el.text = r["t"]
            else:
                a = {"wit": self.wit_attr({self.wit[c]["ms"] for c in grp["wits"]})}
                if grp["c"] == "":
                    a["type"] = "omission"
                el = _sub(app, "rdg", a)
                if grp["t"]:
                    el.text = grp["t"]

    def invariant_text(self, u):
        sw = self.proj.get("structure_witness")
        cid = None
        if sw:
            cid = next((c for c in self.layers.get(sw, []) if c in u["cells"] and c.endswith("_pc")), None) \
                or next((c for c in self.layers.get(sw, []) if c in u["cells"]), None)
        if cid is None:
            cid = next(iter(u["cells"]))
        return u["cells"][cid]

    # ------------------------------------------------------------ document
    def body(self):
        urn = self.proj.get("edition_urn") or self._default_urn()
        edition = E("div", {"type": "edition", f"{{{XML}}}lang": "grc", "n": urn})
        units_by_seg: "OrderedDict[str, list]" = OrderedDict()
        for u in self.m.units:
            units_by_seg.setdefault(u["seg"], []).append(u)
        segs = list(units_by_seg)
        mode = self.m.result["segmentation"]
        subtype = mode.split(":", 1)[1] if mode.startswith("milestone:") else "section"
        # presence of every manuscript per unit (absent = lost text / fragment, see units.lacuna_min)
        units = self.m.units
        present = [{self.wit[c]["ms"] for c in u["cells"]} for u in units]
        first = {ms: next((i for i, p in enumerate(present) if ms in p), None) for ms in self.ms_order}
        last = {ms: max((i for i, p in enumerate(present) if ms in p), default=None) for ms in self.ms_order}
        idx = {id(u): i for i, u in enumerate(units)}
        prev_present: set = set()
        last_container = None
        for si, seg in enumerate(segs):
            if seg == "0" and mode != "none" and si == 0 and len(segs) > 1:
                head = _sub(edition, "head")
                container = _sub(head, "title")
            else:
                div = _sub(edition, "div", {"type": "textpart", "subtype": subtype,
                                            "n": seg if mode != "none" else "1"})
                container = _sub(div, "p")
            for u in units_by_seg[seg]:
                i = idx[id(u)]
                now = present[i]
                marks = OrderedDict()
                for ms in self.ms_order:
                    if ms in now and ms not in prev_present:
                        marks.setdefault("witStart" if first[ms] == i else "lacunaEnd", []).append(ms)
                    elif ms not in now and ms in prev_present and last[ms] is not None and last[ms] >= i:
                        marks.setdefault("lacunaStart", []).append(ms)
                    elif ms not in now and ms in prev_present:
                        marks.setdefault("witEnd", []).append(ms)
                # witEnd / lacunaStart close the previous text, witStart / lacunaEnd open the next one
                for kind in ("witEnd", "lacunaStart", "witStart", "lacunaEnd"):
                    if kind in marks:
                        wit_app = _sub(container, "app", {"type": "witnesses"})
                        rdg = _sub(wit_app, "rdg", {"wit": self.wit_attr(marks[kind])})
                        _sub(rdg, kind)
                        _append_text(container, " ")
                prev_present = now
                self.emit_pbs(container, u)
                if u["variant"]:
                    container.append(self.app_el(u))
                    _append_text(container, " ")
                else:
                    tmp = E("x")
                    self._fill(tmp, self.invariant_text(u))
                    _append_text(container, " " + (tmp.text or ""))
                    for child in list(tmp):
                        container.append(child)
                    _append_text(container, " ")
            last_container = container
        if last_container is not None and prev_present:
            wit_app = _sub(last_container, "app", {"type": "witnesses"})
            rdg = _sub(wit_app, "rdg", {"wit": self.wit_attr(prev_present)})
            _sub(rdg, "witEnd")
        return edition

    def _default_urn(self):
        work = None
        for w in self.m.result["witnesses"]:
            info = ex.read_info(w["file"])
            work = info.work
            if work:
                break
        return f"urn:cts:pta:{work or 'pta0000.pta000'}.pta-grc1"

    def header(self):
        src = ex.parse(self._structure_file()).getroot()
        old = src.find("tei:teiHeader", ex.NS)
        header = E("teiHeader")
        # ---- fileDesc
        fd = _sub(header, "fileDesc")
        ts = _sub(fd, "titleStmt")
        old_title = old.find("tei:fileDesc/tei:titleStmt/tei:title", ex.NS)
        title_text = self.proj.get("title") or (ex._text(old_title).split(" (")[0] + " (Kollation)" if old_title is not None else "Kollation")
        t = _sub(ts, "title", {f"{{{XML}}}lang": old_title.get(f"{{{XML}}}lang") if old_title is not None else None}, title_text)
        for a in old.findall("tei:fileDesc/tei:titleStmt/tei:author", ex.NS):
            ts.append(copy.deepcopy(a))
        ed = self.proj.get("editor") or {}
        resp = _sub(ts, "respStmt")
        _sub(resp, "resp", None, "kollationiert von")
        pid = self.editor_id
        _sub(resp, "persName", {f"{{{XML}}}id": pid, "ref": ed.get("ref")}, ed.get("name") or "N.N.")
        ps = old.find("tei:fileDesc/tei:publicationStmt", ex.NS)
        if ps is not None:
            fd.append(copy.deepcopy(ps))
        sd = _sub(fd, "sourceDesc")
        lw = _sub(sd, "listWit")
        _sub(lw, "head", None, "Conspectus codicum")
        seen = set()
        for w in self.m.result["witnesses"]:
            ms = w["ms"]
            if ms in seen:
                continue
            seen.add(ms)
            info = ex.read_info(w["file"])
            wit = _sub(lw, "witness", {f"{{{XML}}}id": ms, "corresp": os.path.basename(w["file"])})
            _sub(wit, "abbr", {"type": "siglum"}, w["siglum"])
            _sub(wit, "name", {"key": info.key}, info.name)
            _sub(wit, "origDate", None, info.orig_date or None)
            locus = None
            if info.first_page:
                locus = f"f. {info.first_page}" + (f"–{info.last_page}" if info.last_page and info.last_page != info.first_page else "")
            _sub(wit, "locus", None, locus)
        sources = {x.get("id"): x for x in self.proj.get("sources", []) if x.get("id")}
        used = [sources[i] for i in sorted(self.used_sources) if i in sources and i != self.editor_id]
        bibls = [x for x in used if x.get("kind") == "bibl"]
        persons = [x for x in used if x.get("kind") != "bibl"]
        if bibls:
            lb = _sub(sd, "listBibl")
            for x in bibls:
                b = _sub(lb, "bibl", {f"{{{XML}}}id": x["id"]})
                _append_text(b, x.get("name") or x["id"])
                if x.get("ref"):
                    _sub(b, "ptr", {"target": x["ref"]})
        if persons:
            lp = _sub(sd, "listPerson")
            for x in persons:
                pe = _sub(lp, "person", {f"{{{XML}}}id": x["id"]})
                _sub(pe, "persName", {"ref": x.get("ref") or None}, x.get("name") or x["id"])
        # ---- encodingDesc
        enc = _sub(header, "encodingDesc")
        _sub(enc, "variantEncoding", {"method": "parallel-segmentation", "location": "internal"})
        mode = self.m.result["segmentation"]
        subtype = mode.split(":", 1)[1] if mode.startswith("milestone:") else "section"
        rd = _sub(enc, "refsDecl", {"n": "CTS"})
        _sub(rd, "cRefPattern", {"n": subtype, "matchPattern": "(.+)",
                                 "replacementPattern": "#xpath(/tei:TEI/tei:text/tei:body/tei:div[@type='edition']/tei:div[@n='$1'])"})
        oldenc = old.find("tei:encodingDesc", ex.NS)
        refs, rest = [], []
        if oldenc is not None:
            for child in oldenc:
                name = etree.QName(child).localname
                if name in ("variantEncoding", "schemaRef") or (name == "refsDecl" and child.get("n") == "CTS"):
                    continue
                (refs if name == "refsDecl" else rest).append(copy.deepcopy(child))
        have = {r.get(f"{{{XML}}}id") for r in refs}
        for rid, (pattern, repl, note) in DEFAULT_REFSDECL.items():
            if rid not in have:
                el = E("refsDecl", {f"{{{XML}}}id": rid})
                cp = _sub(el, "cRefPattern", {"matchPattern": pattern, "replacementPattern": repl})
                _sub(cp, "p", None, note)
                refs.append(el)
        for el in refs + rest:
            enc.append(el)
        names = {etree.QName(c).localname for c in enc}
        if "editorialDecl" not in names:
            ed_el = _sub(enc, "editorialDecl")
            interp = _sub(ed_el, "interpretation")
            _sub(interp, "p", None, "This file is encoded according to the guidelines of the Patristic Text Archive (PTA).")
        if "classDecl" not in names:
            cd = _sub(enc, "classDecl")
            tx = _sub(cd, "taxonomy", {f"{{{XML}}}id": "editionstatus"})
            _sub(tx, "bibl", None, "Patristic Text Archive Status of edition")
        _sub(enc, "schemaRef", {"key": "v3", "url": SCHEMA_URL})
        # ---- profileDesc
        pd = old.find("tei:profileDesc", ex.NS)
        if pd is not None:
            pd = copy.deepcopy(pd)
            term = pd.find("tei:textClass/tei:keywords[@scheme='#editionstatus']/tei:term", ex.NS)
            if term is not None:
                term.text = None
            header.append(pd)
        # ---- revisionDesc
        rev = _sub(header, "revisionDesc", {"status": "draft"})
        res = self.m.result
        al = res["settings"]["aligner"]
        engine = al.get("engine", "builtin")
        algo = "eingebauter Aligner (progressives Needleman-Wunsch)" if engine == "builtin" else \
            f"CollateX ({al.get('algorithm')}, {al.get('comparator')})"
        when = res.get("created", now())[:10]
        _sub(rev, "change", {"who": f"#{self.editor_id}", "when": when},
             f"Automatische Kollation mit PTA Collatio+ {__version__}: {algo}; Segmentierung {res['segmentation']}; "
             f"{len([e for e in self.proj.get('edits', [])])} manuelle Korrekturen")
        for ch in old.findall("tei:revisionDesc/tei:change", ex.NS)[:0]:
            rev.append(copy.deepcopy(ch))
        return header

    def document(self):
        root = E("TEI")
        edition = self.body()          # first: collects the persons and editions referred to
        root.append(self.header())
        text = _sub(root, "text")
        body = _sub(text, "body")
        body.append(edition)
        tree = etree.ElementTree(root)
        return tree

    def serialize(self) -> bytes:
        tree = self.document()
        # inside readings whitespace is text: keep it exactly as written (no line breaks
        # between <subst>, <add> or <del> inside a word), indent everything else
        untouched = []
        for r in tree.iter(f"{{{TEI}}}rdg", f"{{{TEI}}}lem"):
            if not len(r):
                continue
            if not r.text:
                untouched.append((r, "text"))
            for el in r.iterdescendants():
                if not el.text:
                    untouched.append((el, "text"))
                if not el.tail:
                    untouched.append((el, "tail"))
        etree.indent(tree, space="   ")
        for el, attr in untouched:
            setattr(el, attr, None)
        xml = etree.tostring(tree, encoding="UTF-8", xml_declaration=False, pretty_print=True).decode("utf-8")
        href = self.schema_href or COLLATION_SCHEMA
        sch = href[:-4] + ".sch" if href.endswith(".rng") else href
        pis = (
            '<?xml version="1.0" encoding="UTF-8"?>\n'
            f'<?xml-model href="{href}" schematypens="http://relaxng.org/ns/structure/1.0"?>\n'
            f'<?xml-model href="{sch}" type="application/xml" schematypens="http://purl.oclc.org/dsdl/schematron"?>\n'
        )
        return (pis + xml).encode("utf-8")


def edition_urn(model: Model, proj: dict) -> str:
    return proj.get("edition_urn") or TeiExporter(model, proj)._default_urn()


def file_stem(urn: str) -> str:
    """File name for an edition URN, following the PTA naming of files:
    urn:cts:pta:pta0013.pta003.pta-grc1 → pta0013.pta003.pta-grc1"""
    stem = urn
    if stem.startswith("urn:cts:"):
        stem = stem[len("urn:cts:"):]
    stem = stem.split(":")[-1]          # drop the CTS namespace ("pta:")
    return "".join(ch if ch.isalnum() or ch in "._-" else "_" for ch in stem) or "kollation"


MARKER = "PTA Collatio+"
OLD_MARKERS = ("PTA Collation Studio",)   # earlier name: its exports are recognised as well


def export_path(folder: str, urn: str, suffix: str) -> tuple[str, str | None]:
    """Target path for an export. An existing file that was not written by this tool (e.g. the
    published edition with the same URN) is never overwritten; '.kollation' is added instead."""
    path = os.path.join(folder, file_stem(urn) + suffix)
    if suffix == ".xml" and os.path.exists(path):
        try:
            with open(path, "rb") as fh:
                head = fh.read()
            ours = any(m.encode() in head for m in (MARKER, *OLD_MARKERS))
        except OSError:
            ours = False
        if not ours:
            alt = os.path.join(folder, file_stem(urn) + ".kollation" + suffix)
            return alt, f"{os.path.basename(path)} existiert bereits und stammt nicht aus der Kollation; gespeichert als {os.path.basename(alt)}"
    return path, None


def export_tei(model: Model, proj: dict, schema_href: str | None = None, unit_keys: bool = False) -> bytes:
    return TeiExporter(model, proj, schema_href, unit_keys).serialize()
