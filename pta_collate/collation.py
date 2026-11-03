"""Collation pipeline: transcriptions → tokens → (per section) alignment rows."""

from __future__ import annotations

import os
import re
import time

from . import extract as ex
from .align import run_aligner
from .normalize import Profile, forms
from .project import now


def witnesses_ms(cid: str) -> str:
    return cid[:-3] if cid.endswith(("_ac", "_pc")) else cid


def resolve_segmentation(proj: dict, infos: list) -> str:
    mode = (proj.get("segmentation") or {}).get("mode", "auto")
    if mode != "auto":
        return mode
    # milestone keys shared by all witnesses win, then textpart divs, else none
    candidates = {}
    for info in infos:
        for m, keys in info.segments.items():
            candidates.setdefault(m, []).append(tuple(keys))
    for m in sorted(candidates, key=lambda k: (not k.startswith("milestone:"), k)):
        lists = candidates[m]
        if len(lists) == len(infos) and len(set(lists)) == 1 and len(lists[0]) > 1:
            return m
    for m in sorted(candidates, key=lambda k: (not k.startswith("milestone:"), k)):
        lists = candidates[m]
        if len(lists) == len(infos) and len(lists[0]) > 1:
            return m
    return "none"


def witness_tokens(proj: dict, w: dict, seg_mode: str) -> dict[str, list[ex.Token]]:
    return ex.extract(w["file"], wit=w["id"], layers=w.get("layers", "both"), seg_mode=seg_mode,
                      nomsac=proj.get("nomina_sacra", "expan"))


def enrich(tok: ex.Token, profile: Profile) -> dict:
    d = tok.to_dict()
    c, n, o = forms(tok.t, profile, gap=bool(tok.gap) and tok.t.startswith("["))
    d.update(c=c, n=n, o=o)
    return d


def suspicious_breaks(streams: dict[str, list[dict]], files: dict[str, str]) -> list[dict]:
    """Words probably split by a plain <lb/> (or <cb/>, <pb/>) that should carry break="no".

    A pair "a | b" is reported when the two parts, written together, occur as one word in
    other witnesses at least twice, while the first part on its own is rare (≤ 2 occurrences)."""
    from collections import Counter
    vocab = Counter(d["n"] for seq in streams.values() for d in seq if d["n"])
    out, seen = [], set()
    for cid, seq in streams.items():
        for a, b in zip(seq, seq[1:]):
            if not b.get("brk") or not a["n"] or not b["n"] or "gap" in a.get("flags", []):
                continue
            joined = a["n"] + b["n"]
            if vocab[joined] >= 2 and vocab[a["n"]] <= 2 and len(a["n"]) > 1:
                ms = cid[:-3] if cid.endswith(("_ac", "_pc")) else cid
                key = (ms, b["brk"])
                if key in seen:
                    continue
                seen.add(key)
                out.append({"wit": ms, "file": files.get(cid), "line": b["brk"], "a": a["t"], "b": b["t"],
                            "joined": a["t"] + b["t"], "count": vocab[joined], "tokens": [a["id"], b["id"]]})
    return out


def join_pairs(seq: list[dict], pairs: set) -> list[dict]:
    """Merge token a with the following token b for every (a.id, b.id) in pairs."""
    out, skip = [], False
    for i, d in enumerate(seq):
        if skip:
            skip = False
            continue
        if i + 1 < len(seq) and (d["id"], seq[i + 1]["id"]) in pairs:
            b = seq[i + 1]
            m = dict(d)
            for k in ("t", "c", "n", "o"):
                m[k] = d[k] + b[k]
            m["flags"] = sorted(set(d.get("flags", [])) | set(b.get("flags", [])) | {"joined"})
            out.append(m)
            skip = True
        else:
            out.append(d)
    return out


_FILE_TEXT: dict = {}


def source_lines(path: str | None, page: str | None, word: str) -> list[int]:
    """Lines of the XML file where ``word`` stands (on page ``page`` if given), for the
    transcription check. The word is searched in the file text with tags (e.g. <lb break="no"/>,
    <hi>) allowed between its letters; on the page from its <pb n="…"/> to the next <pb/>."""
    import unicodedata
    if not path or not word:
        return []
    try:
        st = os.stat(path)
        key = (path, st.st_mtime)
        if key not in _FILE_TEXT:
            with open(path, encoding="utf-8") as fh:
                _FILE_TEXT.clear()
                _FILE_TEXT[key] = unicodedata.normalize("NFC", fh.read())
        text = _FILE_TEXT[key]
    except (OSError, UnicodeDecodeError):
        return []
    word = unicodedata.normalize("NFC", word)
    pat = re.compile(r"(?:\s*<[^>]*>\s*)*".join(re.escape(ch) for ch in word))
    start, end = 0, len(text)
    if page:
        m = re.search(r'<pb\b[^>]*\bn="' + re.escape(page) + r'"', text)
        if m:
            start = m.end()
            nxt = re.search(r"<pb\b", text[start:])
            end = start + nxt.start() if nxt else len(text)
    hits = [m.start() for m in pat.finditer(text, start, end)]
    if not hits and (start, end) != (0, len(text)):
        hits = [m.start() for m in pat.finditer(text)]
    return sorted({text.count("\n", 0, h) + 1 for h in hits})[:5]


def mixed_script(streams: dict[str, list[dict]], files: dict[str, str]) -> list[dict]:
    """Greek words that contain Latin letters (e.g. a Latin K typed for a Greek Κ)."""
    from .normalize import has_greek, has_latin
    out, seen = [], set()
    for cid, seq in streams.items():
        ms = witnesses_ms(cid)
        for d in seq:
            if has_greek(d["t"]) and has_latin(d["t"]) and (ms, d["t"], d.get("page")) not in seen:
                seen.add((ms, d["t"], d.get("page")))
                latin = "".join(sorted({ch for ch in d["t"] if "a" <= ch.lower() <= "z"}))
                out.append({"wit": ms, "file": files.get(cid), "page": d.get("page"), "word": d["t"], "latin": latin,
                            "lines": source_lines(files.get(cid), d.get("page"), d["t"])})
    return out


ACUTE_GRAVE_CIRC = {"\u0301", "\u0300", "\u0342"}
BREATHING = {"\u0313", "\u0314"}


def fusion_evidence(t: str) -> list[str]:
    """Signs inside a single word that it consists of two words."""
    import unicodedata
    from .normalize import PUNCT_RE
    d = unicodedata.normalize("NFD", t)
    ev = []
    if sum(1 for ch in d if ch in ACUTE_GRAVE_CIRC) >= 2:
        ev.append("zwei Akzente")
    # a breathing after the second letter (initial diphthongs carry it on their second letter)
    letters_before = 0
    for ch in d:
        if ch in BREATHING and letters_before > 2:
            ev.append("Spiritus im Wort")
            break
        if ch.isalpha():
            letters_before += 1
    # punctuation between letters (trailing punctuation is normal)
    core = t.strip().rstrip(".,;:·;·")
    if any(PUNCT_RE.match(ch) for ch in core[1:]):
        ev.append("Interpunktion im Wort")
    return ev


def _split_points(t: str) -> list[int]:
    """Positions in t between two letters (not inside a letter with its combining marks)."""
    import unicodedata
    pts, seen_letter = [], False
    for i, ch in enumerate(t):
        if unicodedata.combining(ch):
            continue
        if seen_letter and i > 0:
            pts.append(i)
        if ch.isalpha():
            seen_letter = True
    return pts


def _similar(a: str, b: str) -> float:
    from .align.builtin import similarity
    return similarity(a, b)


def fused_words(streams: dict[str, list[dict]], files: dict[str, str], profile: Profile) -> list[dict]:
    """Words probably written without the space between two (or three) words, e.g.
    σωτῆροςἑρμηνεία, πατρὶκαὶ, τῶμὲν, ἰωάννουἀρχἰεπισκόπου.

    The check looks at the place itself: the word together with its neighbours is compared with
    the other manuscripts. A split l|r is supported by a manuscript that has the neighbour before
    followed by l and (a form similar to) r, or (a form similar to) l followed by r and the
    neighbour after. Each part is normalised on its own, so ν ephelkystikon or accents do not
    get in the way. Reported when more manuscripts support the split than write the word in
    the same way at this place, and

    * the word carries a sign of fusion (two accents, a breathing inside, punctuation between
      letters), or
    * at least a quarter of the other manuscripts support the split, and – if the word also
      occurs elsewhere in other manuscripts – at least half of them.

    Without local support, the global rule applies as before: the two parts occur as a pair in
    at least a quarter of the other manuscripts (or in one, if the word shows a sign of fusion)."""
    from collections import Counter, defaultdict
    from functools import lru_cache

    @lru_cache(maxsize=None)
    def norm(x: str) -> str:
        return forms(x, profile)[1]

    by_ms: dict[str, list[dict]] = {}
    for cid, seq in streams.items():
        by_ms.setdefault(witnesses_ms(cid), seq)          # first layer of each manuscript
    seqs = {ms: [d["n"] for d in seq] for ms, seq in by_ms.items()}
    pair_pos: dict[str, dict] = {}
    words_of, bigrams_of = {}, {}
    for ms, ns in seqs.items():
        idx = defaultdict(list)
        for j in range(len(ns) - 1):
            idx[(ns[j], ns[j + 1])].append(j)
        pair_pos[ms] = idx
        words_of[ms] = set(ns)
        bigrams_of[ms] = set(idx)
    all_words, all_bigrams = Counter(), Counter()
    for ms in seqs:
        all_words.update(words_of[ms])
        all_bigrams.update(bigrams_of[ms])
    n_ms = len(seqs)
    needed = max(1, round(0.25 * (n_ms - 1)))

    def close(a, b, start: bool):
        """Same word, or – for longer words – a similar form (typos, orthography) that agrees at
        the edge next to the split (otherwise letters were just moved across the split)."""
        if a == b:
            return True
        edge = a[:2] == b[:2] if start else a[-2:] == b[-2:]
        return edge and min(len(a), len(b)) >= 4 and _similar(a, b) >= 0.8

    def half_support(ms, p, l, r, f):
        """Manuscripts that have only one of the two parts next to its neighbour here."""
        return [o for o in seqs if o != ms and ((p and (p, l) in bigrams_of[o]) or (f and (r, f) in bigrams_of[o]))]

    def local_support(ms, p, l, r, f):
        """Manuscripts (other than ms) that have p l r / l r f here (fuzzy on the far part)."""
        sup = []
        for other, ns in seqs.items():
            if other == ms:
                continue
            ok = False
            if p:
                for j in pair_pos[other].get((p, l), ()):
                    if j + 2 < len(ns) and close(ns[j + 2], r, True):
                        ok = True
                        break
            if not ok and f:
                for j in pair_pos[other].get((r, f), ()):
                    if j >= 1 and close(ns[j - 1], l, False):
                        ok = True
                        break
            if ok:
                sup.append(other)
        return sup

    def same_here(ms, p, x, f):
        return [o for o in seqs if o != ms and ((p and (p, x) in bigrams_of[o]) or (f and (x, f) in bigrams_of[o]))]

    def three_split(ms, t, p, f):
        """Three words written together: others have p a b c or a b c f here."""
        pts, best = _split_points(t), None
        for x1 in range(len(pts)):
            for x2 in range(x1 + 1, len(pts)):
                i, j = pts[x1], pts[x2]
                parts = [t[:i], t[i:j], t[j:]]
                a, b, c = (norm(z) for z in parts)
                if not (a and b and c):
                    continue
                sup = []
                for other, ns in seqs.items():
                    if other == ms:
                        continue
                    for k in pair_pos[other].get((a, b), ()):
                        if k + 2 < len(ns) and ns[k + 2] == c and \
                                ((p and k >= 1 and ns[k - 1] == p) or (f and k + 3 < len(ns) and ns[k + 3] == f)):
                            sup.append(other)
                            break
                if sup and (best is None or len(sup) > len(best[0])):
                    best = (sup, parts)
        return best

    def best_split(ms, t, p, f, depth=0):
        """(support list, [parts]) for the best split of the original form t."""
        best = None
        for k in _split_points(t):
            lt, rt = t[:k], t[k:]
            l, r = norm(lt), norm(rt)
            if not l or not r:
                continue
            sup = local_support(ms, p, l, r, f)
            glob = all_bigrams[(l, r)] - (1 if (l, r) in bigrams_of[ms] else 0)
            words_ok = all_words[l] >= 1 and all_words[r] >= 1     # both parts are words somewhere
            score = (len(sup), words_ok and len(half_support(ms, p, l, r, f)), glob, words_ok, -abs(len(l) - len(r)))
            if best is None or score >= best[0]:    # on a tie the later point: punctuation stays left
                best = (score, sup, [lt, rt], glob)
        if best is None:
            return None
        _, sup, parts, glob = best
        if depth == 0 and not sup:
            three = three_split(ms, t, p, f)
            if three:
                return three[0], three[1], 0
        if depth == 0 and sup:
            # a part may itself consist of two words (three words written together)
            lt, rt = parts
            sub_needed = max(1, min(2, n_ms - 1), len(sup) // 2)
            sub_r = best_split(ms, rt, norm(lt), f, 1) if len(norm(rt)) >= 4 else None
            if sub_r and len(sub_r[0]) >= sub_needed:
                parts = [lt] + sub_r[1]
            else:
                sub_l = best_split(ms, lt, p, norm(rt), 1) if len(norm(lt)) >= 4 else None
                if sub_l and len(sub_l[0]) >= sub_needed:
                    parts = sub_l[1] + [rt]
        return sup, parts, glob

    out, seen = [], {}
    for cid, seq in streams.items():
        ms = witnesses_ms(cid)
        for i, d in enumerate(seq):
            x = d["n"]
            if len(x) < 3 or "gap" in d.get("flags", []) or " " in x or "…" in d["t"]:
                continue
            p = seq[i - 1]["n"] if i > 0 else ""
            f = seq[i + 1]["n"] if i + 1 < len(seq) else ""
            evidence = fusion_evidence(d["t"])
            here = same_here(ms, p, x, f)
            known = all_words[x] - (1 if x in words_of[ms] else 0) - len(here) > 0
            if known and not evidence and here:
                continue      # a word that others write the same way at this place
            res = best_split(ms, d["t"], p, f)
            if not res:
                continue
            sup, parts, glob = res
            others = n_ms - 1
            if sup:
                if len(sup) <= len(here):
                    continue      # at least as many manuscripts write the word in the same way here
                if not evidence and len(sup) < needed:
                    continue
                if known and not evidence and len(sup) * 2 < others:
                    continue
                count = len(sup)
            else:
                if known or here or len(parts) != 2:
                    continue
                l, r = norm(parts[0]), norm(parts[1])
                half = half_support(ms, p, l, r, f)
                if evidence and half and min(len(l), len(r)) >= 2 and \
                        all_words[l] >= 1 and all_words[r] >= 1:
                    sup, count = half, len(half)   # one part stands here in other manuscripts, the other is a variant
                elif glob >= (1 if evidence else needed) and (evidence or len(x) >= 5):
                    count = glob
                else:
                    continue
            key = (ms, d["t"], d.get("page"))
            if key in seen:
                seen[key]["tokens"].append(d["id"])
                continue
            entry = {"wit": ms, "file": files.get(cid), "page": d.get("page"), "word": d["t"],
                     "lines": source_lines(files.get(cid), d.get("page"), d["t"]),
                     "split": " ".join(parts), "count": count, "evidence": evidence, "parts": parts,
                     "support": sup, "same": here, "local": bool(sup),
                     "context": " ".join(z for z in (seq[i - 1]["t"] if i else "", d["t"],
                                                     seq[i + 1]["t"] if i + 1 < len(seq) else "") if z),
                     "tokens": [d["id"]]}
            seen[key] = entry
            out.append(entry)
    return out


def split_tokens(seq: list[dict], splits: dict[str, list[str]], profile: Profile) -> tuple[list[dict], list[str]]:
    """Split tokens into the parts found by fused_words(); ``splits`` maps token id → the parts
    of the transcribed form (as reported in ``parts``)."""
    out, done = [], []
    for d in seq:
        parts = list(splits.get(d["id"]) or [])
        if len(parts) < 2 or "".join(parts) != d["t"]:
            out.append(d)
            continue
        for i, part in enumerate(parts):
            c, n, o = forms(part, profile)
            e = dict(d, t=part, c=c, n=n, o=o, id=d["id"] if i == 0 else d["id"] + "+" * i)
            e["flags"] = sorted(set(d.get("flags", [])) | {"split"})
            out.append(e)
        done.append(d["id"])
    return out, done


def check(proj: dict) -> dict:
    """Run the transcription check (without alignment)."""
    active = [w for w in proj["witnesses"] if w.get("include", True)]
    infos = [ex.read_info(w["file"]) for w in active]
    seg_mode = resolve_segmentation(proj, infos)
    profile = Profile.from_dict(proj.get("normalization"))
    streams, files = {}, {}
    for w in active:
        for cid, toks in witness_tokens(proj, w, seg_mode).items():
            streams[cid] = [d for d in (enrich(t, profile) for t in toks) if d["c"]]
            files[cid] = w["file"]
    return {"breaks": suspicious_breaks(streams, files), "fused": fused_words(streams, files, profile),
            "mixed": mixed_script(streams, files)}


def run(proj: dict, progress=None) -> dict:
    """Run the whole collation and return the alignment result (JSON-serialisable)."""
    t0 = time.time()
    active = [w for w in proj["witnesses"] if w.get("include", True)]
    if len(active) < 2:
        raise ValueError("Für eine Kollation werden mindestens zwei Zeugen benötigt.")
    infos = [ex.read_info(w["file"]) for w in active]
    seg_mode = resolve_segmentation(proj, infos)
    profile = Profile.from_dict(proj.get("normalization"))

    tokens: dict[str, dict] = {}
    witnesses: list[dict] = []
    streams: dict[str, list[dict]] = {}
    for w, info in zip(active, infos):
        per = witness_tokens(proj, w, seg_mode)
        for cid, toks in per.items():
            ms, layer = ex.base_witness(cid) if len(per) > 1 else (w["id"], None)
            siglum = w.get("siglum") or w["id"]
            label = siglum + ("*" if layer == "ac" else ("ᶜ" if layer == "pc" else ""))
            witnesses.append({"id": cid, "ms": w["id"], "layer": layer, "siglum": siglum, "label": label,
                              "file": w["file"], "name": info.name, "key": info.key})
            seq = []
            for tok in toks:
                d = enrich(tok, profile)
                if not d["c"]:
                    continue  # punctuation only
                tokens[d["id"]] = d
                seq.append(d)
            streams[cid] = seq

    files = {w["id"]: w["file"] for w in witnesses}
    breaks = suspicious_breaks(streams, files)
    joined = []
    if proj.get("join_suspicious_breaks"):
        pairs = {tuple(b["tokens"]) for b in breaks}
        # the check reports each manuscript once; apply the join to both correction layers
        for cid in list(streams):
            seq = streams[cid]
            idx = {d["id"]: i for i, d in enumerate(seq)}
            lp = set()
            for d0, d1 in zip(seq, seq[1:]):
                if d1.get("brk") and any(d1["brk"] == b["line"] and b["wit"] == witnesses_ms(cid) for b in breaks):
                    lp.add((d0["id"], d1["id"]))
            lp |= {p for p in pairs if p[0] in idx}
            if lp:
                streams[cid] = join_pairs(seq, lp)
                for d in streams[cid]:
                    tokens[d["id"]] = d
                for a, b in lp:
                    tokens.pop(b, None)
                joined += [{"wit": cid, "tokens": [a, b]} for a, b in lp]

    fused = fused_words(streams, files, profile)
    split = []
    if proj.get("split_fused_words"):
        # the check reports a word once per manuscript; split it in every correction layer
        wanted = {(f["wit"], f["word"], f["page"]): f["parts"] for f in fused}
        for cid in list(streams):
            splits = {d["id"]: wanted[(witnesses_ms(cid), d["t"], d.get("page"))] for d in streams[cid]
                      if (witnesses_ms(cid), d["t"], d.get("page")) in wanted}
            if splits:
                streams[cid], done = split_tokens(streams[cid], splits, profile)
                for d in streams[cid]:
                    tokens[d["id"]] = d
                split += [{"wit": cid, "token": t} for t in done]

    order: list[str] = []
    for cid in [w["id"] for w in witnesses]:
        for d in streams[cid]:
            if d["segment"] not in order:
                order.append(d["segment"])
    # keep the order of the witness with most segments if it differs
    selected = proj.get("segments") or []
    segs = [s for s in order if not selected or s in selected]

    rows: list[dict] = []
    aligner = dict(proj.get("aligner") or {})
    for i, seg in enumerate(segs):
        if progress:
            progress(f"Abschnitt {seg} ({i + 1}/{len(segs)})")
        seqs = {cid: [(d["id"], d["n"]) for d in streams[cid] if d["segment"] == seg] for cid in streams}
        seqs = {k: v for k, v in seqs.items() if v}
        if not seqs:
            continue
        if len(seqs) == 1:
            (cid, seq), = seqs.items()
            seg_rows = [{cid: [tid]} for tid, _ in seq]
        else:
            seg_rows = run_aligner(seqs, aligner)
        for r in seg_rows:
            rows.append({"id": f"r{len(rows)}", "seg": seg, "cells": r})

    # drop tokens of unselected segments
    used = {tid for r in rows for cell in r["cells"].values() for tid in cell}
    tokens = {k: v for k, v in tokens.items() if k in used}
    return {
        "created": now(),
        "seconds": round(time.time() - t0, 2),
        "segmentation": seg_mode,
        "segments": segs,
        "witnesses": witnesses,
        "suspicious_breaks": breaks,
        "joined_breaks": joined,
        "fused_words": fused,
        "split_words": split,
        "tokens": tokens,
        "rows": rows,
        "settings": {"aligner": aligner, "normalization": profile.to_dict(),
                     "nomina_sacra": proj.get("nomina_sacra", "expan")},
    }


def preview(proj: dict, w: dict, segment: str | None = None, limit: int = 400) -> dict:
    """Token preview of one witness with the current settings (for the preparation view)."""
    info = ex.read_info(w["file"])
    seg_mode = resolve_segmentation(proj, [info]) if (proj.get("segmentation") or {}).get("mode", "auto") == "auto" \
        else proj["segmentation"]["mode"]
    profile = Profile.from_dict(proj.get("normalization"))
    per = witness_tokens(proj, w, seg_mode)
    out = {}
    for cid, toks in per.items():
        lst = []
        for tok in toks:
            if segment and tok.segment != segment:
                continue
            lst.append(enrich(tok, profile))
            if len(lst) >= limit:
                break
        out[cid] = lst
    return {"segmentation": seg_mode, "layers": out}
