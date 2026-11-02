"""Benchmark for aligners with a known correct answer.

Synthetic witnesses are derived from a real transcription along a stemma. Every
edge of the stemma applies scribal changes (spelling, word substitution,
omission, addition, local and long transpositions, joined words). Because the
origin of every word is known, the alignment of each aligner can be scored:

    precision  share of word pairs put into one row that really belong together
    recall     share of word pairs that belong together and were put into one row
    long transpositions recognised (only aligners that detect them)

    python scripts/benchmark.py [TRANSKRIPTION.xml] [--words 1500] [--seeds 3] [--engines builtin,dekker]
"""

from __future__ import annotations

import argparse
import os
import random
import sys
import time
import unicodedata

sys.path.insert(0, os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..")))

from pta_collate import extract  # noqa: E402
from pta_collate.align import run_aligner  # noqa: E402
from pta_collate.normalize import Profile, forms  # noqa: E402

DEFAULT_BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tests", "data",
                            "pta0013.pta003.pta-MsPs.xml")

# stemma: archetype ω → α, β; α → A, B, γ; γ → C, D; β → E, F, δ; δ → G, H
STEMMA = {"ω": ["α", "β"], "α": ["A", "B", "γ"], "γ": ["C", "D"], "β": ["E", "F", "δ"], "δ": ["G", "H"]}

RATES = dict(ortho=0.03, lexical=0.008, omit=0.006, add=0.003, swap=0.003, join=0.002, long=0.5)

ORTHO = [("ει", "ι"), ("ι", "ει"), ("η", "ι"), ("ο", "ω"), ("ω", "ο"), ("αι", "ε"), ("ε", "αι"),
         ("λλ", "λ"), ("σσ", "σ"), ("οι", "υ")]
MARKS = "̀́͂̓̔"


def spelling(word: str, rng: random.Random) -> str:
    rules = [r for r in ORTHO if r[0] in word]
    rng.shuffle(rules)
    if rules and rng.random() < 0.7:
        a, b = rules[0]
        k = word.index(a)
        return word[:k] + b + word[k + len(a):]
    d = unicodedata.normalize("NFD", word)
    marks = [i for i, ch in enumerate(d) if ch in MARKS]
    if marks:
        i = rng.choice(marks)
        d = d[:i] + d[i + 1:]
    else:
        d = d + "́" if d else d
    return unicodedata.normalize("NFC", d)


class Generator:
    def __init__(self, base: list[str], seed: int, rates=RATES):
        self.rng = random.Random(seed)
        self.base = base
        self.rates = rates
        self.vocab = sorted(set(base))
        self.next_origin = len(base)
        self.long = []   # (witness-to-be, origins of the moved block)

    def new_origin(self):
        self.next_origin += 1
        return self.next_origin

    def mutate(self, seq, node):
        rng, r = self.rng, self.rates
        out = []
        i = 0
        while i < len(seq):
            o, t = seq[i]
            x = rng.random()
            if x < r["omit"]:
                i += rng.randint(1, 6)
                continue
            x -= r["omit"]
            if x < r["add"]:
                for _ in range(rng.randint(1, 3)):
                    out.append((self.new_origin(), rng.choice(self.vocab)))
            x -= r["add"]
            if x < r["swap"] and i + 1 < len(seq):
                out += [seq[i + 1], seq[i]]
                i += 2
                continue
            x -= r["swap"]
            if x < r["join"] and i + 1 < len(seq):
                out.append((o, t + seq[i + 1][1]))
                i += 2
                continue
            x -= r["join"]
            if x < r["lexical"]:
                t = rng.choice(self.vocab)
            elif x < r["lexical"] + r["ortho"]:
                t = spelling(t, rng)
            out.append((o, t))
            i += 1
        if rng.random() < r["long"] and len(out) > 120:
            k = rng.randint(3, 8)
            a = rng.randint(30, len(out) - 90)
            block = out[a:a + k]
            rest = out[:a] + out[a + k:]
            dest = a + rng.choice([-1, 1]) * rng.randint(15, 60)
            dest = max(0, min(len(rest), dest))
            out = rest[:dest] + block + rest[dest:]
            self.long.append((node, [o for o, _ in block]))
        return out

    def witnesses(self):
        texts = {"ω": [(i, w) for i, w in enumerate(self.base)]}
        todo = ["ω"]
        while todo:
            node = todo.pop(0)
            for child in STEMMA.get(node, []):
                texts[child] = self.mutate(texts[node], child)
                todo.append(child)
        leaves = [n for n in texts if n not in STEMMA]
        # a long transposition is inherited by all leaves below the node where it happened
        below = {}
        for leaf in leaves:
            path, cur = [leaf], leaf
            while cur != "ω":
                cur = next(p for p, cs in STEMMA.items() if cur in cs)
                path.append(cur)
            below[leaf] = set(path)
        self.long_by_leaf = {leaf: [b for node, b in self.long if node in below[leaf]] for leaf in leaves}
        return {w: texts[w] for w in leaves}


def score(rows, origin, wit_of):
    """Pairwise precision / recall against the known origins."""
    pred = set()
    for row in rows:
        toks = [t for cell in row.values() for t in cell]
        for i, a in enumerate(toks):
            for b in toks[i + 1:]:
                if wit_of[a] != wit_of[b]:
                    pred.add((a, b) if a < b else (b, a))
    by_origin = {}
    for t, o in origin.items():
        by_origin.setdefault(o, []).append(t)
    truth = set()
    for toks in by_origin.values():
        for i, a in enumerate(toks):
            for b in toks[i + 1:]:
                if wit_of[a] != wit_of[b]:
                    truth.add((a, b) if a < b else (b, a))
    tp = len(pred & truth)
    return tp / max(1, len(pred)), tp / max(1, len(truth))


ENGINES = {
    "builtin": dict(engine="builtin"),
    "dekker": dict(engine="collatex", algorithm="dekker", comparator="equality"),
}


def transpositions_found(rows, gen, origin, texts):
    """Share of long transpositions that the collation model links (omission ↔ addition)."""
    from pta_collate import units
    profile = Profile.from_dict(None)
    tokens = {}
    for tid, t in texts.items():
        c, n, o = forms(t, profile)
        tokens[tid] = dict(id=tid, wit=tid.split(":")[0], t=t, c=c or t, n=n or t, o=o or t, segment="1", page=None)
    wits = sorted({t["wit"] for t in tokens.values()})
    result = dict(witnesses=[dict(id=w, ms=w, layer=None, siglum=w, label=w, file="", name=w) for w in wits],
                  tokens=tokens, rows=[{"id": f"r{k}", "seg": "1", "cells": r} for k, r in enumerate(rows)],
                  segments=["1"], segmentation="none", settings={})
    proj = {"units": {"merge_adjacent": True, "detect_transpositions": True, "transposition_window": 6,
                      "detect_long_transpositions": True, "long_transposition_distance": 150, "lacuna_min": 0},
            "edits": []}
    model = units.build(result, proj)
    unit_of = {t: u for u in model.units for c in u["cells"].values() for t in c["tokens"]}
    total = found = 0
    moved_units = set()
    for leaf, blocks in gen.long_by_leaf.items():
        for block in blocks:
            mine = [t for t, o in origin.items() if t.startswith(leaf + ":") and o in set(block)]
            if not mine:
                continue
            total += 1
            found += any(unit_of[t].get("suggest") or unit_of[t].get("transposition") for t in mine)
            moved_units |= {unit_of[t]["key"] for t in mine}
            moved_units |= {unit_of[t]["key"] for t, o in origin.items() if o in set(block)}
    links = [u for u in model.units if u.get("suggest") and u["suggest"].get("next")]
    false = sum(1 for u in links if u["key"] not in moved_units and u["suggest"]["next"] not in moved_units)
    transpositions_found.false_links = getattr(transpositions_found, "false_links", 0) + false
    transpositions_found.links = getattr(transpositions_found, "links", 0) + len(links)
    return found / total if total else None


def run(base_file, words, seeds, engines):
    toks = next(iter(extract.extract(base_file, layers="pc").values()))
    profile = Profile.from_dict(None)
    base = [t.t for t in toks if forms(t.t, profile)[1]][:words]
    results = {e: [] for e in engines}
    for seed in range(seeds):
        gen = Generator(base, seed)
        wits = gen.witnesses()
        origin, wit_of, seqs, texts = {}, {}, {}, {}
        for w, seq in wits.items():
            seqs[w] = []
            for i, (o, t) in enumerate(seq):
                tid = f"{w}:{i}"
                origin[tid], wit_of[tid], texts[tid] = o, w, t
                seqs[w].append((tid, forms(t, profile)[1] or t))
        for e in engines:
            t0 = time.time()
            meta = {}
            rows = run_aligner(seqs, dict(ENGINES[e]), meta)
            sec = time.time() - t0
            p, r = score(rows, origin, wit_of)
            fl0, l0 = getattr(transpositions_found, "false_links", 0), getattr(transpositions_found, "links", 0)
            tr = transpositions_found(rows, gen, origin, texts)
            fl = transpositions_found.false_links - fl0
            nl = transpositions_found.links - l0
            results[e].append((p, r, sec, tr, fl, nl))
            print(f"  seed {seed} {e:16s} P {p:.4f}  R {r:.4f}  {sec:6.1f} s"
                  + (f"  Umstellungen {tr:.0%}, {nl} Verknüpfungen, davon falsch {fl}" if tr is not None else ""), flush=True)
    print()
    for e, rs in results.items():
        n = len(rs)
        p = sum(x[0] for x in rs) / n
        r = sum(x[1] for x in rs) / n
        f = 2 * p * r / (p + r)
        trs = [x[3] for x in rs if x[3] is not None]
        print(f"{e:16s} Precision {p:.4f}  Recall {r:.4f}  F1 {f:.4f}  Zeit {sum(x[2] for x in rs) / n:6.1f} s"
              + (f"  weite Umstellungen erkannt {sum(trs) / len(trs):.0%}" if trs else "")
              + f"  falsche Verknüpfungen {sum(x[4] for x in rs)}/{sum(x[5] for x in rs)}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("base", nargs="?", default=DEFAULT_BASE)
    ap.add_argument("--words", type=int, default=1500)
    ap.add_argument("--seeds", type=int, default=3)
    ap.add_argument("--engines", default="builtin,dekker")
    a = ap.parse_args()
    run(a.base, a.words, a.seeds, a.engines.split(","))
