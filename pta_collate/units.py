"""From alignment rows to variation units, with the manual corrections applied.

The aligner result (rows) is never changed on disk. Every correction is an
entry in ``project["edits"]`` and is replayed on top of the rows whenever the
units are computed. After a new collation run the same edits are replayed
again; edits that no longer fit are reported as *not applied*.

Edit operations (all keys refer to token ids, which are stable as long as the
transcriptions and the extraction settings do not change):

``{"op": "move", "token": id, "dir": "prev"|"next"}``
    move a token at the edge of its cell into the neighbouring row
``{"op": "move", "token": id, "dir": "newprev"|"newnext", "with": [id, ...]}``
    move a token at the edge of its cell (and the tokens in ``with``, same row, other witnesses,
    e.g. the other correction layer) into a new row directly above / below
``{"op": "split", "at": id}`` / ``{"op": "join", "at": id}``
    force / remove a unit boundary before the row containing ``at``
``{"op": "attr", "unit": key, "reading": c|None, "key": k, "value": v}``
    set ``type``/``cause`` of a reading or ``note`` of a unit
``{"op": "confirm", "unit": key, "readings": [{"reading": c, "wits": [...], "type": t, "cause": c}, ...]}``
    take over the automatically recognised type and cause of the readings: the values are
    stored in the edit and kept like ``attr`` edits, even if the lemma changes later
``{"op": "lem", "unit": key, "reading": c|None}``
    choose the lemma (``None`` removes it)
``{"op": "nest", "unit": key, "value": bool}``
    nest inner variants inside the lemma (needs a lemma)
``{"op": "link", "a": key, "b": key}`` / ``{"op": "unlink", "a": key}``
    connect an omission and an addition as a long transposition (prev/next)
``{"op": "lacuna", "ms": id, "at": key, "value": bool}``
    the stretch without text of manuscript ``ms`` around the row of ``at`` is a lacuna
    (``True``: the manuscript is absent there, in TEI lacunaStart/lacunaEnd or – at its
    beginning or end – witStart/witEnd) or an omission (``False``)
``{"op": "conj", "unit": key, "id": id, "text": t, "kind": k, "resp": id, "source": id, "cert": c}``
    editorial reading (conjecture, correction, proposition, lacunam_indicavit) at a unit;
    ``"delete": true`` removes it again. Choosing it as lemma: ``{"op": "lem", "editorial": id}``
``{"op": "insert", "id": id, "after": key}`` / ``{"op": "insert", "id": id, "before": key}``
    a new, empty row between two places (key ``"ins:<id>"``), e.g. for a conjectured addition
    or a suspected lacuna where no witness has text; ``"delete": true`` removes it again
"""

from __future__ import annotations

import copy
from collections import Counter, OrderedDict

from .normalize import Profile, forms, strip_punctuation

STRUCTURAL = {"move", "split", "join", "lacuna", "insert"}
# unit-level edit operations
UNIT_OPS = {"attr", "lem", "nest", "link", "unlink", "reject_link", "conj", "confirm"}
EDITORIAL_KINDS = ("conjecture", "correction", "proposition", "lacunam_indicavit")


def structure_signature(proj: dict) -> str:
    """Everything that changes rows or unit boundaries."""
    import json as _json
    structural = [(i, e) for i, e in enumerate(proj.get("edits", [])) if e.get("op") in STRUCTURAL]
    return _json.dumps([structural, proj.get("units", {})], sort_keys=True, ensure_ascii=False)


GAP_TYPES = {"illegible": "illegible", "damage": "damage", "fenestra": "fenestra"}


def _similar(a: str, b: str, threshold: float) -> bool:
    """Equal, or similar enough by character overlap (orthographic keys)."""
    if a == b:
        return True
    if not a or not b:
        return False
    from difflib import SequenceMatcher
    return SequenceMatcher(None, a, b, autojunk=False).ratio() >= threshold


def _cell_text(tokens: dict, tids: list[str], key: str) -> str:
    return " ".join(tokens[t][key] for t in tids if tokens[t][key])


class Model:
    def __init__(self, result: dict, proj: dict):
        self.result = result
        self.proj = proj
        self.tokens = result["tokens"]
        self.wits = [w["id"] for w in result["witnesses"]]
        self.wit_info = {w["id"]: w for w in result["witnesses"]}
        self.ms_of = {w["id"]: w["ms"] for w in result["witnesses"]}
        self.status: list[dict] = []
        self._build()
        self.signature = structure_signature(proj)

    def refresh(self, proj: dict) -> "Model":
        """Re-apply the edits. If only unit-level decisions changed (lemma, type, notes, links),
        the alignment structure is reused, which is much faster for large collations."""
        if structure_signature(proj) != self.signature:
            return Model(self.result, proj)
        self.proj = proj
        self.status = [s for s in self.status if proj["edits"][s["edit"]:s["edit"] + 1]
                       and proj["edits"][s["edit"]].get("op") in STRUCTURAL]
        for u in self.units:
            u["lem"], u["nest"], u["note"], u["link"], u["suggest"] = None, False, "", None, None
            u["transposition"] = u.get("_auto_transposition", False)
            u["readings"] = [r for r in u["readings"] if not r.get("editorial")]
            u["variant"] = u["_variant"]
            for r in u["readings"]:
                r["override"] = {}
        self._apply_auto_links()
        self._apply_unit_edits()
        for u in self.units:
            classify(u)
            assign_parents(u, self.tokens)
        return self

    # ------------------------------------------------------------------ rows
    def _index(self):
        self.where = {}
        for i, r in enumerate(self.rows):
            for w, cell in r["cells"].items():
                for t in cell:
                    self.where[t] = i

    def _apply_moves(self):
        for k, e in enumerate(self.proj.get("edits", [])):
            if e.get("op") != "move":
                continue
            if e.get("dir") in ("newprev", "newnext"):
                ok = self._move_new([e.get("token")] + list(e.get("with") or []), e["dir"] == "newprev")
                if ok:   # the new row stays a unit of its own; its counterpart, if there is one, too
                    self._index()
                    i = self.where[e["token"]]
                    cells = self.rows[i]["cells"]
                    tx = self.tokens[e["token"]]["o"]
                    found = self._counterpart(i, list(cells), tx, int(self.proj.get("units", {}).get("transposition_window", 6)))
                    self.displaced.append((self.rows[i]["id"],) + ((found[1],) if found else ()))
            else:
                ok = self._move(e.get("token"), e.get("dir"))
            self.status.append({"edit": k, "ok": ok})
            if ok:
                self._index()

    def _move(self, tid, direction) -> bool:
        if tid not in self.where:
            return False
        i = self.where[tid]
        j = i - 1 if direction == "prev" else i + 1
        if j < 0 or j >= len(self.rows) or self.rows[j]["seg"] != self.rows[i]["seg"]:
            return False
        wit = self.tokens[tid]["wit"]
        cell = self.rows[i]["cells"][wit]
        if direction == "prev" and cell[0] != tid:
            return False
        if direction == "next" and cell[-1] != tid:
            return False
        cell.remove(tid)
        if not cell:
            del self.rows[i]["cells"][wit]
        target = self.rows[j]["cells"].setdefault(wit, [])
        if direction == "prev":
            target.append(tid)
        else:
            target.insert(0, tid)
        if not self.rows[i]["cells"]:
            del self.rows[i]
        return True

    def _move_new(self, tids, before: bool, rid=None) -> bool:
        """Move tokens of one row (each at the edge of its cell, one per witness) into a new
        row directly before / after it."""
        if not tids or any(t not in self.where for t in tids):
            return False
        i = self.where[tids[0]]
        row = self.rows[i]
        wits = [self.tokens[t]["wit"] for t in tids]
        if any(self.where[t] != i for t in tids) or len(set(wits)) != len(wits):
            return False
        for t, w in zip(tids, wits):
            cell = row["cells"].get(w) or []
            if not cell or cell[0 if before else -1] != t:
                return False
        new = {"id": rid or f"{row['id']}~{tids[0]}", "seg": row["seg"], "cells": {}}
        for t, w in zip(tids, wits):
            row["cells"][w].remove(t)
            if not row["cells"][w]:
                del row["cells"][w]
            new["cells"][w] = [t]
        self.rows.insert(i if before else i + 1, new)
        if not row["cells"]:
            self.rows.remove(row)
        return True

    def _counterpart(self, i, ws, tx, window):
        """Nearest row (within ``window`` rows of the same section) where the witnesses ``ws``
        have no text and most witnesses with text have a reading similar to ``tx``.
        Returns (lies before row i, row id) or None. A directly neighbouring row does not count:
        without text in between it is an alternative reading at the same place, not a
        transposition."""
        tok = self.tokens
        seg = self.rows[i]["seg"]
        for d in range(2, window + 2):
            for j, before in ((i + d, False), (i - d, True)):
                if not 0 <= j < len(self.rows) or self.rows[j]["seg"] != seg:
                    continue
                cj = self.rows[j]["cells"]
                if any(cj.get(w) for w in ws):
                    continue
                have = [" ".join(tok[t]["o"] for t in c if tok[t]["o"]) for c in cj.values() if c]
                have = [h for h in have if h]
                if have and sum(1 for h in have if _similar(tx, h, 0.8)) * 2 > len(have):
                    return before, self.rows[j]["id"]
        return None

    def _split_displaced(self, window: int) -> int:
        """Words that the aligner put against a different word, although the other witnesses
        have the same word a few rows away (a short transposition: Ca "καὶ … ἔλαβεν" against
        Pk "ἔλαβε …"). Such a reading is moved into a row of its own, on the side where its
        counterpart is, so that addition and omission can be recognised as a transposition.

        Conditions: the reading has at most three words and at least four letters, it does not
        resemble any other reading of its row (similarity < 0.5), and within ``window`` rows of
        the same section there is a row where its witnesses have no text while most of the
        witnesses with text there have a similar reading (similarity ≥ 0.8)."""
        tok = self.tokens

        def text(cell):
            return " ".join(tok[t]["o"] for t in cell if tok[t]["o"])

        self.displaced = []           # (row id of the moved reading, row id of its counterpart)
        moved, i = 0, 0
        while i < len(self.rows):
            r = self.rows[i]
            groups: "OrderedDict[str, list]" = OrderedDict()
            for w, c in r["cells"].items():
                tx = text(c)
                if tx:
                    groups.setdefault(tx, []).append(w)
            step = 1
            if len(groups) >= 2:
                for tx, ws in groups.items():
                    if len(tx.split()) > 3 or len(tx.replace(" ", "")) < 4:
                        continue
                    if any(_similar(tx, g, 0.5) for g in groups if g != tx):
                        continue
                    found = self._counterpart(i, ws, tx, window)
                    if found is None:
                        continue
                    side, partner = found
                    # all tokens of these witnesses in this row go into the new row
                    new = {"id": f"{r['id']}~d", "seg": r["seg"], "cells": {w: r["cells"].pop(w) for w in ws}}
                    self.rows.insert(i if side else i + 1, new)
                    self.displaced.append((new["id"], partner))
                    moved += 1
                    step = 2
                    break
            i += step
        return moved

    # ----------------------------------------------------------------- build
    def _build(self):
        self.displaced = []
        self.rows = [{"id": r["id"], "seg": r["seg"], "cells": {w: list(c) for w, c in r["cells"].items()}}
                     for r in self.result["rows"]]
        opts = self.proj.get("units", {})
        if opts.get("split_displaced", True):
            self._split_displaced(int(opts.get("transposition_window", 6)))
        self._index()
        self._apply_moves()
        self._index()
        seg_wits: dict[str, list[str]] = OrderedDict()
        for r in self.rows:
            present = seg_wits.setdefault(r["seg"], [])
            for w in r["cells"]:
                if w not in present:
                    present.append(w)
        self.seg_wits = {s: [w for w in self.wits if w in ws] for s, ws in seg_wits.items()}
        opts = self.proj.get("units", {})
        self._mark_lacunae(int(opts.get("lacuna_min", 40) or 0))

        sigs, inv = [], []
        for i, r in enumerate(self.rows):
            present = self.row_present[i]
            texts = {w: _cell_text(self.tokens, r["cells"].get(w, []), "c") for w in present}
            groups = {}
            for w, c in texts.items():
                groups.setdefault(c, []).append(w)
            sigs.append(frozenset(frozenset(g) for g in groups.values()))
            inv.append(len(groups) == 1 and next(iter(groups)) != "")

        merge = opts.get("merge_adjacent", True)
        n = len(self.rows)
        boundary = [True] * n  # boundary *before* row i
        for i in range(1, n):
            a, b = self.rows[i - 1], self.rows[i]
            if a["seg"] != b["seg"] or self.row_present[i - 1] != self.row_present[i]:
                continue
            if inv[i - 1] and inv[i]:
                boundary[i] = False
            elif not inv[i - 1] and not inv[i] and merge and sigs[i - 1] == sigs[i]:
                boundary[i] = False
        # a reading moved into a row of its own and its counterpart stay separate units,
        # so that they can be recognised as a transposition
        pos = {r["id"]: k for k, r in enumerate(self.rows)}
        for ids in getattr(self, "displaced", []):
            for rid in ids:
                k = pos.get(rid)
                if k is not None:
                    boundary[k] = True
                    if k + 1 < n:
                        boundary[k + 1] = True
        self.auto_transpositions = []
        if opts.get("detect_transpositions", True):
            self._detect_transpositions(boundary, inv, int(opts.get("transposition_window", 6)))
        # long transpositions: each half becomes one unit (edits below can still change that)
        long_pairs = []
        if opts.get("detect_long_transpositions", True):
            for (a0, a1), (b0, b1) in self._find_long_transpositions(int(opts.get("long_transposition_distance", 150))):
                for lo, hi in ((a0, a1), (b0, b1)):
                    boundary[lo] = True
                    if hi + 1 < n:
                        boundary[hi + 1] = True
                    for i in range(lo + 1, hi + 1):
                        boundary[i] = False
                long_pairs.append((a0, b0))
        # manual split / join
        for k, e in enumerate(self.proj.get("edits", [])):
            if e.get("op") not in ("split", "join"):
                continue
            i = self.where.get(e.get("at"))
            ok = i is not None and i > 0 and self.rows[i]["seg"] == self.rows[i - 1]["seg"] \
                and (e["op"] == "split" or self.row_present[i - 1] == self.row_present[i])
            if ok:
                boundary[i] = e["op"] == "split"
            self.status.append({"edit": k, "ok": ok})

        units, cur = [], []
        for i in range(n):
            if boundary[i] and cur:
                units.append(cur)
                cur = []
            cur.append(i)
        if cur:
            units.append(cur)
        self.units = [self._make_unit(idx, inv) for idx in units]
        self.by_key = {u["key"]: u for u in self.units}
        self._apply_inserts()
        self.auto_links = [(self._unit_of_row(a)["key"], self._unit_of_row(b)["key"]) for a, b in long_pairs]
        self.auto_links = [(a, b) for a, b in self.auto_links if a != b]
        self._apply_auto_links()
        for t in self.auto_transpositions:
            u = self._unit_of_row(t)
            if u is not None:
                u["transposition"] = True
                u["_auto_transposition"] = True
        self._apply_unit_edits()
        for u in self.units:
            classify(u)
            assign_parents(u, self.tokens)
        self._absent_kinds()

    def _apply_inserts(self):
        """New empty rows (edit "insert") for readings of the editor where no witness has text."""
        wanted: "OrderedDict[str, tuple[int, dict]]" = OrderedDict()
        for k, e in enumerate(self.proj.get("edits", [])):
            if e.get("op") != "insert":
                continue
            iid = str(e.get("id"))
            if e.get("delete"):
                ok = iid in wanted
                if ok:
                    self.status.append({"edit": wanted.pop(iid)[0], "ok": True})
                self.status.append({"edit": k, "ok": ok})
                continue
            wanted[iid] = (k, e)
        for iid, (k, e) in wanted.items():
            ref = self._unit(e.get("after") or e.get("before"), e.get("anchors"))
            ok = ref is not None and ("ins:" + iid) not in self.by_key
            if ok:
                present = list(ref["cells"])
                cells = {w: {"tokens": [], "t": "", "c": "", "n": "", "o": "", "flags": [], "pages": [], "gap": []}
                         for w in present}
                u = {"key": "ins:" + iid, "seg": ref["seg"], "rows": [], "grid": [], "absent": list(ref["absent"]),
                     "variant": False, "_variant": False, "transposition": False, "inserted": True,
                     "cells": cells,
                     "readings": [{"id": "r0", "c": "", "t": "", "n": "", "o": "", "wits": present, "gap": None,
                                   "type": None, "cause": None, "group": None, "override": {}}],
                     "lem": None, "nest": False, "note": "", "link": None, "suggest": None}
                i = self.units.index(ref)
                self.units.insert(i + (1 if e.get("after") else 0), u)
                self.by_key[u["key"]] = u
            self.status.append({"edit": k, "ok": ok})

    def _absent_kinds(self):
        """For each absent manuscript of a unit: before its beginning, after its end, or lacuna."""
        first, last = {}, {}
        for i, u in enumerate(self.units):
            for cid in u["cells"]:
                ms = self.ms_of[cid]
                first.setdefault(ms, i)
                last[ms] = i
        for i, u in enumerate(self.units):
            kinds = {}
            for cid in u["absent"]:
                ms = self.ms_of[cid]
                kinds[cid] = "before" if i < first.get(ms, len(self.units)) else ("after" if i > last.get(ms, -1) else "lacuna")
            u["absent_kind"] = kinds

    def _mark_lacunae(self, minimum: int):
        """A witness that has no text over at least ``minimum`` consecutive rows is treated as
        *absent* there (lost leaves, fragment begins later), not as omitting the text."""
        self.row_present = [list(self.seg_wits[r["seg"]]) for r in self.rows]
        self.lacunae = {}
        n = len(self.rows)
        for w in (self.wits if minimum > 0 else []):
            i = 0
            while i < n:
                if self.rows[i]["cells"].get(w) or w not in self.seg_wits[self.rows[i]["seg"]]:
                    i += 1
                    continue
                j = i
                while j < n and not self.rows[j]["cells"].get(w) and w in self.seg_wits[self.rows[j]["seg"]]:
                    j += 1
                if j - i >= minimum:
                    for k in range(i, j):
                        self.row_present[k].remove(w)
                    self.lacunae.setdefault(w, []).append((self.rows[i]["id"], self.rows[j - 1]["id"]))
                i = j
        # manual decisions: lacuna or omission
        for k, e in enumerate(self.proj.get("edits", [])):
            if e.get("op") != "lacuna":
                continue
            run = self.empty_run(e.get("ms"), self.where.get(e.get("at")))
            ok = run is not None
            if ok:
                lo, hi = run
                for i in range(lo, hi + 1):
                    for cid in self.cids_of(e["ms"]):
                        if cid not in self.seg_wits[self.rows[i]["seg"]]:
                            continue
                        if e.get("value") and cid in self.row_present[i]:
                            self.row_present[i].remove(cid)
                        elif not e.get("value") and cid not in self.row_present[i]:
                            self.row_present[i] = [w for w in self.seg_wits[self.rows[i]["seg"]]
                                                   if w in self.row_present[i] or w == cid]
            self.status.append({"edit": k, "ok": ok})

    def cids_of(self, ms) -> list[str]:
        return [w for w in self.wits if self.ms_of[w] == ms]

    def empty_run(self, ms, i) -> tuple[int, int] | None:
        """Rows around row i in which manuscript ms (all its layers) has no text."""
        cids = self.cids_of(ms)
        if i is None or not cids:
            return None

        def empty(k):
            r = self.rows[k]
            return any(c in self.seg_wits[r["seg"]] for c in cids) and not any(r["cells"].get(c) for c in cids)
        if not empty(i):
            return None
        lo, hi = i, i
        while lo > 0 and empty(lo - 1):
            lo -= 1
        while hi + 1 < len(self.rows) and empty(hi + 1):
            hi += 1
        return lo, hi

    def _find_long_transpositions(self, max_distance: int) -> list[tuple[tuple[int, int], tuple[int, int]]]:
        """Long transpositions as pairs of row ranges.

        For every witness W, runs of rows where W has words that most other witnesses lack
        ("extra") are compared with runs where W lacks words that most others have ("missing")
        within ``max_distance`` rows (also across sections). If W's words and the words of the
        others agree (orthographic key, Dice ≥ 0.6, at least two words), the two runs are a
        transposition. Works for every aligner, because it only looks at the alignment rows."""
        rows, n = self.rows, len(self.rows)
        tok = self.tokens
        row_words = [{w: [tok[t]["o"] for t in c if tok[t]["o"]] for w, c in r["cells"].items()} for r in rows]
        row_have = [sum(1 for x in self.row_present[i] if row_words[i].get(x)) for i in range(n)]
        present_sets = [set(p) for p in self.row_present]

        def words(i, w):
            return row_words[i].get(w, [])

        def runs(w, extra: bool):
            out, cur = [], None
            for i, r in enumerate(rows):
                if w not in present_sets[i]:
                    flag = False
                else:
                    mine = bool(row_words[i].get(w))
                    others = len(present_sets[i]) - 1
                    have = row_have[i] - (1 if mine else 0)
                    flag = (mine and have * 2 < others) if extra else (not mine and have * 2 > others)
                if flag and cur and cur[1] == i - 1 and rows[cur[0]]["seg"] == r["seg"]:
                    cur[1] = i
                elif flag:
                    cur = [i, i]
                    out.append(cur)
            return out

        def majority(lo, hi, w):
            res = []
            for i in range(lo, hi + 1):
                counts: dict[str, int] = {}
                for x in self.row_present[i]:
                    if x != w:
                        t = " ".join(words(i, x))
                        if t:
                            counts[t] = counts.get(t, 0) + 1
                if counts:
                    res += max(counts, key=counts.get).split()
            return res

        def dice(a, b):
            from collections import Counter
            ca, cb = Counter(a), Counter(b)
            common = sum((ca & cb).values())
            return common, 2 * common / max(1, len(a) + len(b))

        found: list[list[int]] = []
        for w in self.wits:
            ex, mi = runs(w, True), runs(w, False)
            for a0, a1 in ex:
                mine = [x for i in range(a0, a1 + 1) for x in words(i, w)]
                if len(mine) < 2 or len("".join(mine)) < 8:
                    continue
                best = None
                for b0, b1 in mi:
                    if b0 <= a1 + 1 and a0 <= b1 + 1:
                        continue  # adjacent or overlapping: a local variant, not a transposition
                    if min(abs(b0 - a1), abs(a0 - b1)) > max_distance:
                        continue
                    common, d = dice(mine, majority(b0, b1, w))
                    if common >= 2 and d >= 0.6 and (best is None or d > best[0]):
                        best = (d, b0, b1)
                if best:
                    _, b0, b1 = best
                    found.append([a0, a1, b0, b1])
        # witnesses sharing the same transposition give overlapping ranges: merge them
        merged: list[list[int]] = []
        for f in sorted(found):
            for m in merged:
                if f[0] <= m[1] and m[0] <= f[1] and f[2] <= m[3] and m[2] <= f[3]:
                    m[0], m[1] = min(m[0], f[0]), max(m[1], f[1])
                    m[2], m[3] = min(m[2], f[2]), max(m[3], f[3])
                    break
            else:
                merged.append(list(f))
        out, used = [], set()
        for a0, a1, b0, b1 in merged:
            span = set(range(a0, a1 + 1)) | set(range(b0, b1 + 1))
            if span & used:
                continue
            used |= span
            first, second = sorted([(a0, a1), (b0, b1)])
            out.append((first, second))
        return out

    def _apply_auto_links(self):
        """Detected long transpositions are *suggestions*: shown in the synopsis, exported to
        TEI only after the editor confirmed them (edit "link"), removable with "reject_link"."""
        for a, b in getattr(self, "auto_links", []):
            ua, ub = self.by_key.get(a), self.by_key.get(b)
            if ua is None or ub is None:
                continue
            ua["suggest"], ub["suggest"] = {"next": b}, {"prev": a}

    def _unit_of_row(self, row_index):
        rid = self.rows[row_index]["id"]
        for u in self.units:
            if rid in u["rows"]:
                return u
        return None

    def _natural_units(self, boundary):
        units, cur = [], []
        for i in range(len(self.rows)):
            if boundary[i] and cur:
                units.append(cur)
                cur = []
            cur.append(i)
        if cur:
            units.append(cur)
        return units

    def _detect_transpositions(self, boundary, inv, window):
        """Find X…Y where one group of witnesses has a text at X and another group has the
        same text at Y (and nothing at the respective other place). Join X…Y into one unit."""
        units = self._natural_units(boundary)

        def profile(idx):
            seg = self.rows[idx[0]]["seg"]
            present = self.row_present[idx[0]]
            txt = {}
            for w in present:
                tids = [t for i in idx for t in self.rows[i]["cells"].get(w, [])]
                txt[w] = " ".join(self.tokens[t]["o"] for t in tids if self.tokens[t]["o"])
            return seg, txt

        profs = [profile(u) for u in units]
        for a in range(len(units)):
            if all(inv[i] for i in units[a]):
                continue
            seg_a, ta = profs[a]
            full_a = {w for w, t in ta.items() if t}
            empty_a = {w for w, t in ta.items() if not t}
            if not full_a or not empty_a or len({ta[w] for w in full_a}) != 1:
                continue
            text = ta[next(iter(full_a))]
            between = 0
            for b in range(a + 1, len(units)):
                seg_b, tb = profs[b]
                if seg_b != seg_a:
                    break
                full_b = {w for w, t in tb.items() if t}
                if all(inv[i] for i in units[b]):
                    between += len(units[b])
                    if between > window:
                        break
                    continue
                # the other group has (nearly) the same text here and the first group has none;
                # with no text in between, it is an alternative at the same place, not a transposition
                if b > a + 1 and full_b and full_b <= empty_a and full_a <= {w for w, t in tb.items() if not t} \
                        and all(_similar(tb[w], text, 0.8) for w in full_b):
                    for u in range(a + 1, b + 1):
                        boundary[units[u][0]] = False
                    self.auto_transpositions.append(units[a][0])
                    break
                between += len(units[b])
                if between > window:
                    break

    def _make_unit(self, idx: list[int], inv) -> dict:
        rows = [self.rows[i] for i in idx]
        seg = rows[0]["seg"]
        present = self.row_present[idx[0]]
        cells = {}
        for w in present:
            tids = [t for r in rows for t in r["cells"].get(w, [])]
            flags = sorted({f for t in tids for f in self.tokens[t].get("flags", [])})
            pages = []
            for t in tids:
                p = self.tokens[t].get("page")
                if p and (not pages or pages[-1] != p):
                    pages.append(p)
            toks = [self.tokens[t] for t in tids]
            cells[w] = {
                "tokens": tids,
                "t": " ".join(x["t"] for x in toks if x["t"]),
                "c": " ".join(x["c"] for x in toks if x["c"]),
                "n": " ".join(x["n"] for x in toks if x["n"]),
                "o": " ".join(x["o"] for x in toks if x["o"]),
                "flags": flags,
                "pages": pages,
                "gap": [self.tokens[t]["gap"] for t in tids if self.tokens[t].get("gap")],
            }
        key = next((r["cells"][w][0] for r in rows for w in self.wits if r["cells"].get(w)), rows[0]["id"])
        groups: "OrderedDict[str, list[str]]" = OrderedDict()
        for w in present:
            groups.setdefault(cells[w]["c"], []).append(w)
        readings = []
        for i, (c, ws) in enumerate(groups.items()):
            first = cells[ws[0]]
            gap_only = bool(first["tokens"]) and all(self.tokens[t].get("gap") and self.tokens[t]["t"].startswith("[")
                                                    for t in first["tokens"])
            readings.append({"id": f"r{i}", "c": c, "t": first["t"], "n": first["n"], "o": first["o"],
                             "wits": ws, "gap": first["gap"][0] if gap_only else None,
                             "type": None, "cause": None, "group": None, "override": {}})
        grid = [{"id": r["id"], "cells": {w: list(c) for w, c in r["cells"].items()}} for r in rows]
        absent = [w for w in self.seg_wits[seg] if w not in present]
        return {"key": key, "seg": seg, "rows": [r["id"] for r in rows], "grid": grid, "absent": absent,
                "variant": len(readings) > 1, "_variant": len(readings) > 1, "transposition": False,
                "cells": cells, "readings": readings, "lem": None, "nest": False,
                "note": "", "link": None, "suggest": None}

    # ----------------------------------------------------------- unit edits
    def _unit(self, key, anchors=None):
        """Unit by key. If the unit changed (tokens moved, units joined or split), the unit sharing
        most of the edit's anchor tokens is used, then the unit containing the key token."""
        if key in self.by_key:
            return self.by_key[key]
        if anchors:
            wanted = set(anchors)
            best, best_n = None, 0
            for u in self.units:
                n = sum(1 for c in u["cells"].values() for t in c["tokens"] if t in wanted)
                if n > best_n:
                    best, best_n = u, n
            if best is not None:
                return best
        for u in self.units:
            for c in u["cells"].values():
                if key in c["tokens"]:
                    return u
        return None

    def _apply_unit_edits(self):
        for k, e in enumerate(self.proj.get("edits", [])):
            op = e.get("op")
            if op in STRUCTURAL:
                continue
            ok = False
            if op == "attr":
                u = self._unit(e.get("unit"), e.get("anchors"))
                if u:
                    if e.get("reading") is None:
                        if e.get("key") in ("note", "transposition"):
                            u[e["key"]] = e.get("value")
                            ok = True
                    else:
                        r = _find_reading(u, e)
                        if r and e.get("key") in ("type", "cause", "parent"):
                            r["override"][e["key"]] = e.get("value") or None
                            ok = True
            elif op == "confirm":
                u = self._unit(e.get("unit"), e.get("anchors"))
                if u:
                    for item in e.get("readings") or []:
                        r = _find_reading(u, item)
                        if r and not r.get("editorial"):
                            for attr in ("type", "cause", "parent"):
                                if attr in item:
                                    r["override"][attr] = item[attr] or None
                            ok = True
            elif op == "lem":
                u = self._unit(e.get("unit"), e.get("anchors"))
                if u and e.get("editorial"):
                    r = next((r for r in u["readings"] if (r.get("editorial") or {}).get("id") == e["editorial"]), None)
                    if r and r["type"] != "lacunam_indicavit":
                        u["lem"] = r["id"]
                        ok = True
                elif u:
                    if e.get("reading") is None:
                        u["lem"] = None
                        ok = True
                    else:
                        r = _find_reading(u, e)
                        if r:
                            u["lem"] = r["id"]
                            ok = True
            elif op == "conj":
                u = self._unit(e.get("unit"), e.get("anchors"))
                if u:
                    ok = self._editorial(u, e)
            elif op == "nest":
                u = self._unit(e.get("unit"), e.get("anchors"))
                if u:
                    u["nest"] = bool(e.get("value"))
                    ok = True
            elif op == "link":
                a, b = self._unit(e.get("a")), self._unit(e.get("b"))
                if a and b and a is not b:
                    a["link"] = {"next": b["key"]}
                    b["link"] = {"prev": a["key"]}
                    a["suggest"] = b["suggest"] = None
                    a["transposition"] = b["transposition"] = True
                    ok = True
            elif op == "reject_link":
                a = self._unit(e.get("a"))
                if a and a.get("suggest"):
                    other = self._unit(a["suggest"].get("next") or a["suggest"].get("prev"))
                    a["suggest"] = None
                    if other:
                        other["suggest"] = None
                    ok = True
            elif op == "unlink":
                a = self._unit(e.get("a"))
                if a and a.get("link"):
                    other = self._unit(a["link"].get("next") or a["link"].get("prev"))
                    a["link"] = None
                    if other:
                        other["link"] = None
                    ok = True
            self.status.append({"edit": k, "ok": ok})

    def _editorial(self, u, e) -> bool:
        """Add, replace or remove an editorial reading (conjecture, correction …) of a unit."""
        rid = "e:" + str(e.get("id"))
        old = next((r for r in u["readings"] if r["id"] == rid), None)
        if e.get("delete"):
            if old is None:
                return False
            u["readings"].remove(old)
            if u["lem"] == rid:
                u["lem"] = None
            u["variant"] = u["_variant"] or any(r.get("editorial") for r in u["readings"])
            return True
        kind = e.get("kind") if e.get("kind") in EDITORIAL_KINDS else "conjecture"
        text = "" if kind == "lacunam_indicavit" else (e.get("text") or "").strip()
        if not text and kind != "lacunam_indicavit":
            return False
        if not hasattr(self, "_profile"):
            self._profile = Profile.from_dict(self.proj.get("normalization"))
        c, n, o = forms(text, self._profile) if text else ("", "", "")
        r = {"id": rid, "c": c or text, "t": text, "n": n, "o": o, "wits": [], "gap": None,
             "type": kind, "cause": None, "group": None, "override": {},
             "editorial": {"id": str(e.get("id")), "kind": kind, "resp": e.get("resp") or None,
                           "source": e.get("source") or None,
                           "cert": e.get("cert") if kind == "proposition" else None}}
        if old is not None:
            u["readings"][u["readings"].index(old)] = r
        else:
            u["readings"].append(r)
        u["variant"] = True
        return True

    # ---------------------------------------------------------------- output
    def to_json(self) -> dict:
        status = sorted(self.status, key=lambda s: s["edit"])
        return {
            "witnesses": self.result["witnesses"],
            "segments": self.result["segments"],
            "segmentation": self.result["segmentation"],
            "seg_wits": self.seg_wits,
            "units": [_unit_json(u) for u in self.units],
            "tokens": self._tokens_json(),
            "edit_status": status,
            "stats": self.stats(),
        }

    def unit_detail(self, key: str) -> dict | None:
        """Full unit with its alignment rows and token texts (for the detail panel)."""
        u = self._unit(key)
        if u is None:
            return None
        d = _unit_json(u)
        for w, c in u["cells"].items():
            d["cells"][w]["tokens"] = c["tokens"]
        d["grid"] = u["grid"]
        d["tokens"] = {t: _tok_json(self.tokens[t]) for c in u["cells"].values() for t in c["tokens"]}
        d["presence"] = self.presence_options(u)
        return d

    def presence_options(self, u) -> list[dict]:
        """Manuscripts without text in this unit: omission (can become a lacuna) or absent."""
        out = []
        if u.get("inserted"):
            return out
        i = self.where.get(u["key"])
        if i is None:
            i = next((self.where[t] for c in u["cells"].values() for t in c["tokens"] if t in self.where), None)
        for ms in dict.fromkeys(self.ms_of.values()):
            cids = self.cids_of(ms)
            absent = [c for c in cids if c in u["absent"]]
            here = [c for c in cids if c in u["cells"]]
            if absent:
                state = u.get("absent_kind", {}).get(absent[0], "lacuna")
            elif here and all(not u["cells"][c]["tokens"] for c in here):
                state = "omission"
            else:
                continue
            run = self.empty_run(ms, i)
            words = 0
            if run:
                for k in range(run[0], run[1] + 1):
                    words += max((len(v) for w, v in self.rows[k]["cells"].items() if self.ms_of[w] != ms), default=0)
            out.append({"ms": ms, "label": self.wit_info[cids[0]]["siglum"], "state": state,
                        "words": words, "at": u["key"]})
        return out

    def _tokens_json(self) -> dict:
        """Token texts the browser needs: tokens of variation units, unclear tokens and tokens
        referenced by edits. Invariant text is shown from the unit cells directly."""
        need = set()
        for u in self.units:
            for c in u["cells"].values():
                if "unclear" in c["flags"]:
                    need.update(c["tokens"])
        for e in self.proj.get("edits", []):
            for k in ("token", "at", "unit", "a", "b", "after", "before"):
                if e.get(k) in self.tokens:
                    need.add(e[k])
        return {k: _tok_json(self.tokens[k]) for k in need}

    def stats(self) -> dict:
        var = [u for u in self.units if u["variant"]]
        return {
            "units": len(self.units),
            "variant_units": len(var),
            "with_lem": sum(1 for u in var if u["lem"]),
            "orthographic_only": sum(1 for u in var if all(r["cause"] == "orthographic" or r is _head(u) for r in u["readings"])),
            "editorial": sum(1 for u in self.units for r in u["readings"] if r.get("editorial")),
            "lacunae": sum(1 for i, u in enumerate(self.units) for c, k in u.get("absent_kind", {}).items()
                           if k == "lacuna" and not c.endswith("_ac")
                           and (i == 0 or c not in self.units[i - 1].get("absent", []))),
            "tokens": len(self.tokens),
        }


def _unit_json(u: dict) -> dict:
    """Compact form for the browser: no empty fields; invariant units without token lists."""
    cells = {}
    for w, c in u["cells"].items():
        d = {"t": c["t"], "c": c["c"], "o": c["o"]}
        if c["flags"]:
            d["flags"] = c["flags"]
        if c["pages"]:
            d["pages"] = c["pages"]
        if "unclear" in c["flags"]:
            d["tokens"] = c["tokens"]
        d["n_tok"] = len(c["tokens"])
        cells[w] = d
    out = {k: u[k] for k in ("key", "seg", "variant", "transposition", "lem", "nest", "note", "link", "suggest", "absent", "absent_kind", "inserted") if u.get(k) not in (None, "", False) or k in ("key", "seg", "variant")}
    out["cells"] = cells
    out["readings"] = [{k: v for k, v in r.items() if v not in (None, {}, "") or k in ("c", "t", "wits", "id")}
                       for r in u["readings"]] if u["variant"] else [{"id": "r0", "c": u["readings"][0]["c"], "t": "", "wits": []}]
    out["nrows"] = len(u["rows"])
    return out


def _find_reading(u, e):
    """Reading addressed by an edit: by its text, or – after the unit was joined or split –
    by the witnesses that carried it (``e["wits"]``)."""
    r = next((r for r in u["readings"] if r["c"] == e.get("reading")), None)
    if r is None and e.get("wits"):
        for w in e["wits"]:
            r = next((r for r in u["readings"] if w in r["wits"]), None)
            if r:
                break
    return r


def _tok_json(v):
    d = {"t": v["t"], "wit": v["wit"]}
    if v.get("flags"):
        d["flags"] = v["flags"]
    return d


def _head(u):
    if u["lem"]:
        return next(r for r in u["readings"] if r["id"] == u["lem"])
    return max(u["readings"], key=lambda r: len(r["wits"]))


def classify(u: dict):
    """Assign type, cause and orthographic groups to the readings of a unit."""
    for r in u["readings"]:
        if r.get("editorial"):
            r["type"], r["cause"], r["group"] = r["editorial"]["kind"], None, None
    rs = [r for r in u["readings"] if not r.get("editorial")]
    for r in rs:
        r["type"] = r["cause"] = r["group"] = None
    if len(rs) < 2:
        _apply_overrides(u)
        return
    lem = next((r for r in u["readings"] if r["id"] == u["lem"]), None)
    total = sum(len(r["wits"]) for r in rs)
    empty = next((r for r in rs if r["c"] == ""), None)
    empty_major = empty is not None and len(empty["wits"]) * 2 > total
    for r in rs:
        if r["gap"]:
            r["type"] = GAP_TYPES.get(r["gap"].get("reason"), "illegible")
            continue
        if r["c"] == "":
            if lem is not None:
                r["type"] = "omission" if lem["c"] else None
            else:
                r["type"] = None if empty_major else "omission"
        else:
            if lem is not None:
                if lem["c"] == "":
                    r["type"] = "addition"
            elif empty_major:
                r["type"] = "addition"
    # transpositions: same tokens, different order
    perm: dict[tuple, list] = {}
    for r in rs:
        if r["n"]:
            perm.setdefault(tuple(sorted(r["o"].split())), []).append(r)
    for members in perm.values():
        orders = {tuple(m["o"].split()) for m in members}
        if len(orders) < 2:
            continue
        head = lem if lem in members else max(members, key=lambda m: len(m["wits"]))
        for m in members:
            if tuple(m["o"].split()) != tuple(head["o"].split()):
                m["type"] = "transposition"
        u["transposition"] = True
    # orthographic families
    fam: "OrderedDict[str, list]" = OrderedDict()
    for r in rs:
        if r["o"]:
            fam.setdefault(r["o"], []).append(r)
    g = 0
    for members in fam.values():
        if len(members) < 2:
            continue
        g += 1
        head = lem if lem in members else max(members, key=lambda m: len(m["wits"]))
        for m in members:
            m["group"] = g
            if m is not head and strip_punctuation(m["c"]) != strip_punctuation(head["c"]):
                m["cause"] = "orthographic"
    _apply_overrides(u)


def _apply_overrides(u):
    for r in u["readings"]:
        for k, v in r.get("override", {}).items():
            if k != "parent":            # resolved by assign_parents
                r[k] = v


SUB_WARN_WORDS = 3   # a sub-variant lacking more words than this is flagged


def row_profile(u: dict, r: dict, tokens: dict, key: str = "c") -> list[str]:
    """Text of a reading per row of its unit (taken from its first witness)."""
    w = r["wits"][0]
    return [" ".join(tokens[t][key] for t in row["cells"].get(w, []) if tokens[t][key]) for row in u["grid"]]


def assign_parents(u: dict, tokens: dict):
    """Sub-variants: a reading that is another reading of the same unit with a few words left
    out, added or changed becomes a sub-variant of it (``r["parent"]`` = id of that reading).
    In the TEI the differences are then inner apps within the lem or rdg of the parent.

    Automatic proposal (``r["parent_auto"]``), overridable per reading (override "parent": text
    of the parent reading, or None for an own reading). Rules for the proposal:
    a lemma, an omission of the whole unit, a transposition and a gap are own readings; the
    other readings are tried from the most widely attested; a reading becomes a sub-variant of
    the closest own reading if it shares at least one word with it in unchanged rows, has no
    more added words and changed places than shared words, and has no word in a row of its
    own that the parent has elsewhere (that would be a transposition). Left-out words do not
    count against it; more than three are flagged. Nesting is only proposed if at least two own readings remain."""
    rs = [r for r in u["readings"] if not r.get("editorial")]
    for r in u["readings"]:
        r.pop("parent", None), r.pop("parent_auto", None), r.pop("sub_diff", None), r.pop("sub_warn", None)
    if not u["variant"] or len(rs) < 3 or len(u.get("grid") or []) < 1:
        return
    prof = {r["id"]: row_profile(u, r, tokens) for r in rs}
    oprof = {r["id"]: row_profile(u, r, tokens, "o") for r in rs}

    def fixed_root(r):
        return r["id"] == u.get("lem") or not r["c"] or r.get("gap") or r.get("type") == "transposition"

    def diff(r, p):
        """(shared words, missing words, added words, changed rows) of r against p, or None."""
        a, b, ao, bo = prof[r["id"]], prof[p["id"]], oprof[r["id"]], oprof[p["id"]]
        shared = missing = added = changed = 0
        extra, gone = [], []
        for x, y, xo, yo in zip(a, b, ao, bo):
            if x == y:
                shared += len(y.split()) if y else 0
            elif not x:
                missing += len(y.split())
                gone.append(yo)
            elif not y:
                added += len(x.split())
                extra.append(xo)
            else:
                changed += 1
                shared += 0
        # a word added here that the parent has elsewhere: transposition, not a sub-variant
        if any(_similar(e, g, 0.8) for e in extra for g in gone):
            return None
        return shared, missing, added, changed

    order = sorted(rs, key=lambda r: (r["id"] != u.get("lem"), -len(r["wits"])))
    roots, auto = [], {}
    for r in order:
        if fixed_root(r) or not roots:
            roots.append(r)
            continue
        best = None
        for p in roots:
            if not p["c"] or p.get("gap"):
                continue
            d = diff(r, p)
            if d is None:
                continue
            shared, missing, added, changed = d
            # mostly the parent's words: omissions are free (flagged above three words),
            # additions and changed places must not outweigh what is shared
            if shared == 0 or added + changed > shared:
                continue
            cost = missing + added + changed
            if best is None or cost < best[0] or (cost == best[0] and len(p["wits"]) > len(best[1]["wits"])):
                best = (cost, p, d)
        if best:
            auto[r["id"]] = (best[1]["id"], best[2])
        else:
            roots.append(r)
    if len([r for r in rs if r["id"] not in auto]) < 2:
        auto = {}
    by_c = {r["c"]: r for r in rs}
    for r in rs:
        if r["id"] in auto:
            r["parent_auto"] = auto[r["id"]][0]
        if "parent" in r.get("override", {}):
            want = r["override"]["parent"]
            p = by_c.get(want) if want else None
            r["parent"] = p["id"] if p is not None and p is not r else None
        else:
            r["parent"] = r.get("parent_auto")
    # a parent must be an own reading (one level of nesting)
    ids = {r["id"]: r for r in rs}
    for r in rs:
        if r.get("parent") and ids[r["parent"]].get("parent"):
            r["parent"] = None
        if r.get("parent") and r["id"] == u.get("lem"):
            r["parent"] = None
    if len([r for r in rs if not r.get("parent")]) < 2:
        for r in rs:
            r["parent"] = None
    for r in rs:
        if r.get("parent"):
            d = diff(r, ids[r["parent"]]) or (0, 0, 0, 0)
            r["sub_diff"] = {"missing": d[1], "added": d[2], "changed": d[3]}
            if d[1] > SUB_WARN_WORDS:
                r["sub_warn"] = True


def build(result: dict, proj: dict) -> Model:
    return Model(result, proj)


def nested_lemma(u: dict, model: Model):
    """Structure for nesting: outer readings grouped by presence pattern over the
    natural sub-units, inner variation of the lemma group as sub-units.

    Returns ``(outer, inner)`` where ``outer`` is a list of
    ``{"wits", "is_lem", "text"}`` and ``inner`` a list of sub-unit dicts
    ``{"readings": [{"t", "c", "wits", "is_lem"}], "variant": bool}`` covering the lemma group.
    Returns ``None`` if nesting is not possible.
    """
    if not u.get("lem") or not u.get("nest") or len(u["rows"]) < 2:
        return None
    lem = next(r for r in u["readings"] if r["id"] == u["lem"])
    if not lem["wits"]:
        return None     # editorial lemma: nothing to nest
    lem_wit = lem["wits"][0]
    rows = [model.rows[[r["id"] for r in model.rows].index(rid)] for rid in u["rows"]]
    present = list(u["cells"])
    # natural sub-units: consecutive rows with the same presence pattern and grouping
    def row_sig(r):
        groups = {}
        for w in present:
            groups.setdefault(_cell_text(model.tokens, r["cells"].get(w, []), "c"), []).append(w)
        return frozenset(frozenset(v) for v in groups.values())
    subs, cur, last = [], [], None
    for r in rows:
        s = row_sig(r)
        if cur and s != last:
            subs.append(cur)
            cur = []
        cur.append(r)
        last = s
    if cur:
        subs.append(cur)
    if len(subs) < 2:
        return None

    def text(w, sub, key="c"):
        return _cell_text(model.tokens, [t for r in sub for t in r["cells"].get(w, [])], key)

    pattern = {w: tuple(bool(text(w, s)) for s in subs) for w in present}
    outer_groups: "OrderedDict[tuple, list]" = OrderedDict()
    for w in present:
        outer_groups.setdefault(pattern[w], []).append(w)
    lem_pattern = pattern[lem_wit]
    lem_group = outer_groups[lem_pattern]
    if len(outer_groups) < 2:
        return None
    outer = []
    for pat, ws in outer_groups.items():
        if pat == lem_pattern:
            outer.append({"wits": ws, "is_lem": True})
        else:
            # non-lemma groups: one reading per distinct full text
            by_text: "OrderedDict[str, list]" = OrderedDict()
            for w in ws:
                by_text.setdefault(u["cells"][w]["c"], []).append(w)
            for c, ww in by_text.items():
                outer.append({"wits": ww, "is_lem": False, "t": u["cells"][ww[0]]["t"], "c": c})
    inner = []
    for s in subs:
        by: "OrderedDict[str, list]" = OrderedDict()
        for w in lem_group:
            by.setdefault(text(w, s), []).append(w)
        readings = []
        for c, ws in by.items():
            readings.append({"c": c, "t": text(ws[0], s, "t"), "wits": ws, "is_lem": lem_wit in ws,
                             "o": text(ws[0], s, "o")})
        inner.append({"readings": readings, "variant": len(readings) > 1})
    return outer, inner
