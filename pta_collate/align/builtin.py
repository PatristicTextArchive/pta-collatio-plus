"""Built-in aligner without Java.

Combines the strengths of the two classic approaches used by CollateX:

* **Islands (as in Dekker's algorithm):** before any scoring, blocks of four
  consecutive words that occur exactly once in both texts are fixed as anchors
  ("islands"). Repeated short words (καί, τοῦ, ὁ …) can then no longer be matched
  with the wrong occurrence, and long texts fall apart into small pieces.
* **Transpositions:** islands that stand in a different order are not forced into
  the alignment. Long transpositions are then recognised by the collation model
  (``units.py``) for every aligner and linked (PTA: omission and addition
  connected by ``@prev``/``@next``).
* **Global alignment with similarity (as in Needleman-Wunsch with the TSAligner
  comparators):** between the islands, words are aligned with dynamic
  programming. Similar spellings (normalised Levenshtein) count as matches, and
  gaps have affine costs (opening a gap is expensive, extending it cheap), so
  that an omitted phrase stays together instead of being scattered around
  coincidentally matching short words.
* **Progressive alignment with a guide tree (Spencer/Howe):** witnesses are added
  in the order of their similarity, which reduces the dependence on the order in
  which witnesses are listed.
"""

from __future__ import annotations

import bisect
from functools import lru_cache

NEG = float("-inf")

# tuned on synthetic witnesses with known answer (scripts/benchmark.py), checked on held-out seeds
DEFAULTS = dict(threshold=0.6, mismatch=-1.5, gap_open=-1.2, gap_extend=-0.3, island=4)


@lru_cache(maxsize=200_000)
def similarity(a: str, b: str) -> float:
    if a == b:
        return 1.0
    if not a or not b:
        return 0.0
    if len(a) < len(b):
        a, b = b, a
    prev = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        cur = [i]
        for j, cb in enumerate(b, 1):
            cur.append(min(prev[j] + 1, cur[j - 1] + 1, prev[j - 1] + (ca != cb)))
        prev = cur
    return 1.0 - prev[-1] / max(len(a), len(b))


@lru_cache(maxsize=500_000)
def _score(x: str, reps: tuple[str, ...], threshold: float, mismatch: float) -> float:
    if x in reps:
        return 2.0
    best = max(similarity(x, r) for r in reps)
    if best >= threshold:
        return 2.0 * best - 0.4
    return mismatch


# --------------------------------------------------------------------------- DP
def _gotoh(reps: list[tuple[str, ...]], seq: list[str], p: dict) -> list[tuple[str, int, int]]:
    """Banded global alignment with affine gaps (Gotoh).

    Returns the path as a list of ("M", i, j) | ("X", i, -1) | ("Y", -1, j):
    M = column i of the profile with token j, X = column without the new token,
    Y = token without column."""
    n, m = len(reps), len(seq)
    if n == 0:
        return [("Y", -1, j) for j in range(m)]
    if m == 0:
        return [("X", i, -1) for i in range(n)]
    thr, mis, go, ge = p["threshold"], p["mismatch"], p["gap_open"], p["gap_extend"]
    width = p.get("band") or max(80, abs(n - m) + 60)
    if n * m <= 2_000_000:
        width = max(n, m)
    ratio = m / n
    step = int(ratio) + 3

    Mp = [NEG] * (m + 1); Xp = [NEG] * (m + 1); Yp = [NEG] * (m + 1)
    Mc = [NEG] * (m + 1); Xc = [NEG] * (m + 1); Yc = [NEG] * (m + 1)
    Mp[0] = 0.0
    for j in range(1, m + 1):
        Yp[j] = go + (j - 1) * ge
    ptr: list[tuple[int, bytearray]] = [(0, bytearray())]
    for i in range(1, n + 1):
        center = int(i * ratio)
        lo = max(1, center - width)
        hi = min(m, center + width)
        Mc[0], Xc[0], Yc[0] = NEG, go + (i - 1) * ge, NEG
        if lo > 1:
            Mc[lo - 1] = Xc[lo - 1] = Yc[lo - 1] = NEG
        r = reps[i - 1]
        row = bytearray(hi - lo + 1)
        for j in range(lo, hi + 1):
            # M: diagonal
            a, b, c = Mp[j - 1], Xp[j - 1], Yp[j - 1]
            if a >= b and a >= c:
                v, mk = a, 0
            elif b >= c:
                v, mk = b, 1
            else:
                v, mk = c, 2
            Mc[j] = v + _score(seq[j - 1], r, thr, mis) if v != NEG else NEG
            # X: up (profile column without token)
            a, b, c = Mp[j] + go, Xp[j] + ge, Yp[j] + go
            if a >= b and a >= c:
                Xc[j], xk = a, 0
            elif b >= c:
                Xc[j], xk = b, 1
            else:
                Xc[j], xk = c, 2
            # Y: left (token without column)
            a, b, c = Mc[j - 1] + go, Xc[j - 1] + go, Yc[j - 1] + ge
            if a >= c and a >= b:
                Yc[j], yk = a, 0
            elif b >= c:
                Yc[j], yk = b, 1
            else:
                Yc[j], yk = c, 2
            row[j - lo] = mk | (xk << 2) | (yk << 4)
        ptr.append((lo, row))
        for k in range(hi + 1, min(m, hi + step) + 1):
            Mc[k] = Xc[k] = Yc[k] = NEG
        Mp, Mc = Mc, Mp
        Xp, Xc = Xc, Xp
        Yp, Yc = Yc, Yp
    finals = (Mp[m], Xp[m], Yp[m])
    if max(finals) == NEG:
        return _gotoh(reps, seq, dict(p, band=max(n, m)))
    state = finals.index(max(finals))
    path = []
    i, j = n, m
    while i > 0 or j > 0:
        if i == 0:
            path.append(("Y", -1, j - 1)); j -= 1; continue
        if j == 0:
            path.append(("X", i - 1, -1)); i -= 1; continue
        lo, row = ptr[i]
        code = row[j - lo]
        if state == 0:
            path.append(("M", i - 1, j - 1))
            state = code & 3
            i -= 1; j -= 1
        elif state == 1:
            path.append(("X", i - 1, -1))
            state = (code >> 2) & 3
            i -= 1
        else:
            path.append(("Y", -1, j - 1))
            state = (code >> 4) & 3
            j -= 1
    path.reverse()
    return path


# ---------------------------------------------------------------------- islands
def _lis(items: list[tuple[int, int]]) -> list[int]:
    """Indices of the longest chain with increasing first value (items sorted by second)."""
    tails, tails_idx, prev = [], [], [None] * len(items)
    for k, (p, _s) in enumerate(items):
        pos = bisect.bisect_left(tails, p)
        if pos == len(tails):
            tails.append(p); tails_idx.append(k)
        else:
            tails[pos] = p; tails_idx[pos] = k
        prev[k] = tails_idx[pos - 1] if pos else None
    out, k = [], tails_idx[-1] if tails_idx else None
    while k is not None:
        out.append(k); k = prev[k]
    return out[::-1]


def _islands(canon: list[str], seq: list[str], k: int):
    """Unique k-grams shared by profile (canonical words) and new text.

    Returns (anchors, moved): anchors = increasing (profile i, seq j) pairs that are
    fixed; moved = list of blocks [(i, j), …] that match uniquely but out of order."""
    if k < 2 or len(canon) < k or len(seq) < k:
        return [], []

    def grams(xs):
        cnt, pos = {}, {}
        for q in range(len(xs) - k + 1):
            g = tuple(xs[q:q + k])
            cnt[g] = cnt.get(g, 0) + 1
            pos[g] = q
        return cnt, pos

    cc, cp = grams(canon)
    sc, sp = grams(seq)
    cands = sorted(((cp[g], sp[g]) for g, c in sc.items()
                    if c == 1 and cc.get(g) == 1 and sum(len(w) for w in g) >= 3 * k),
                   key=lambda x: x[1])
    if not cands:
        return [], []
    chain = set(_lis(cands))
    anchors, lp, ls = [], -1, -1
    for idx in sorted(chain, key=lambda q: cands[q][1]):
        p0, s0 = cands[idx]
        for d in range(k):
            pi, sj = p0 + d, s0 + d
            if pi > lp and sj > ls:
                anchors.append((pi, sj))
                lp, ls = pi, sj
    # out-of-order islands → transposition blocks (merge consecutive grams on one diagonal)
    moved, cur = [], []
    for idx in range(len(cands)):
        if idx in chain:
            continue
        p0, s0 = cands[idx]
        pairs = [(p0 + d, s0 + d) for d in range(k)]
        if cur and cur[-1][1] >= s0 - 1 and cur[-1][0] - cur[-1][1] == p0 - s0:
            cur += [x for x in pairs if x[1] > cur[-1][1]]
        else:
            if cur:
                moved.append(cur)
            cur = pairs
    if cur:
        moved.append(cur)
    # keep only blocks that are clearly displaced against the surrounding anchors
    anchor_s = [a[1] for a in anchors]
    real = []
    for block in moved:
        s_mid = block[0][1]
        q = bisect.bisect_left(anchor_s, s_mid)
        neighbours = anchors[max(0, q - 1):q + 1]
        if not neighbours:
            continue
        expected = [a[0] + (s_mid - a[1]) for a in neighbours]
        if min(abs(block[0][0] - e) for e in expected) >= 5:
            real.append(block)
    return anchors, real


# --------------------------------------------------------------- profile step
def _align_profile(profile: list[dict], reps: list[tuple[str, ...]], seq: list[tuple[str, str]], wit: str,
                   p: dict, moves: list):
    n, m = len(profile), len(seq)
    if m == 0:
        return [dict(col) for col in profile], list(reps)
    if n == 0:
        return [{wit: tid} for tid, _ in seq], [(x,) for _, x in seq]
    words = [x for _, x in seq]
    anchors, _moved = _islands([r[0] for r in reps], words, int(p.get("island", 4)))
    path = []
    pi, sj = 0, 0
    for ai, aj in anchors + [(n, m)]:
        sub = _gotoh(reps[pi:ai], words[sj:aj], p)
        path += [(op, i + pi if i >= 0 else -1, j + sj if j >= 0 else -1) for op, i, j in sub]
        if ai < n:
            path.append(("M", ai, aj))
        pi, sj = ai + 1, aj + 1
    cols, new_reps, col_of = [], [], {}
    for op, i, j in path:
        if op == "M":
            col = dict(profile[i]); col[wit] = seq[j][0]
            r, x = reps[i], words[j]
            col_of[i] = len(cols)
            cols.append(col); new_reps.append(r if x in r else r + (x,))
        elif op == "X":
            col_of[i] = len(cols)
            cols.append(dict(profile[i])); new_reps.append(reps[i])
        else:
            cols.append({wit: seq[j][0]}); new_reps.append((words[j],))
    return cols, new_reps


def guide_order(sequences: dict[str, list[tuple[str, str]]]) -> list[str]:
    wits = [w for w in sequences]
    if len(wits) <= 2:
        return wits

    def bigrams(seq):
        xs = [x for _, x in seq]
        return set(zip(xs, xs[1:])) or set(xs)

    grams = {w: bigrams(sequences[w]) for w in wits}
    sim = {}
    for a in wits:
        for b in wits:
            if a < b:
                ga, gb = grams[a], grams[b]
                sim[(a, b)] = sim[(b, a)] = len(ga & gb) / max(1, len(ga | gb))
    a, b = max(((x, y) for (x, y) in sim if x < y), key=lambda k: sim[k])
    order = [a, b]
    rest = [w for w in wits if w not in order]
    while rest:
        nxt = max(rest, key=lambda w: max(sim[(w, o)] for o in order))
        order.append(nxt)
        rest.remove(nxt)
    return order


def find_anchors(sequences: dict[str, list[tuple[str, str]]], min_len: int = 4) -> list[str]:
    """Words that occur exactly once in every witness, in the same order everywhere."""
    wits = list(sequences)
    counts, positions = [], {}
    for w in wits:
        c = {}
        for i, (_, x) in enumerate(sequences[w]):
            c[x] = c.get(x, 0) + 1
            positions.setdefault(w, {})[x] = i
        counts.append(c)
    cands = [x for x, k in counts[0].items() if k == 1 and len(x) >= min_len
             and all(c.get(x) == 1 for c in counts[1:])]
    cands.sort(key=lambda x: positions[wits[0]][x])
    for w in wits[1:]:
        # keep the longest subsequence (in the order of the first witness) that is increasing in w
        keep = _lis([(positions[w][x], q) for q, x in enumerate(cands)])
        cands = [cands[q] for q in keep]
    return cands


def _align_all(sequences, order, p, moves):
    profile: list[dict] = []
    reps: list[tuple[str, ...]] = []
    for wit in order:
        profile, reps = _align_profile(profile, reps, sequences[wit], wit, p, moves)
    return profile, reps


def align_builtin(sequences: dict[str, list[tuple[str, str]]], settings: dict,
                  meta: dict | None = None) -> list[dict[str, list[str]]]:
    p = dict(DEFAULTS)
    p.update({k: settings[k] for k in DEFAULTS if settings.get(k) is not None})
    p = {k: float(v) if k != "island" else int(v) for k, v in p.items()}
    if not settings.get("islands", True):
        p["island"] = 0
    moves: list[dict] = []
    order = guide_order(sequences) if settings.get("guide_tree", True) else list(sequences)
    longest = max(len(v) for v in sequences.values())

    # Fragments (less than half as long as the longest witness) would block anchors that must
    # occur in every witness; align the complete witnesses first, then add the fragments.
    core = {w: v for w, v in sequences.items() if len(v) >= 0.5 * longest} if longest > 150 else dict(sequences)
    frags = [w for w in order if w not in core]
    core_order = [w for w in order if w in core]
    anchors = find_anchors(core) if settings.get("anchors", True) and len(core) > 1 and longest > 150 else []
    if anchors:
        spaced, last = [], -10
        pos0 = {x: i for i, (_, x) in enumerate(core[core_order[0]])}
        for a in anchors:
            if pos0[a] - last >= 8:
                spaced.append(a)
                last = pos0[a]
        anchors = spaced
    profile: list[dict] = []
    reps: list[tuple[str, ...]] = []
    if anchors:
        cuts = {w: [{x: i for i, (_, x) in enumerate(seq)}[a] for a in anchors] for w, seq in core.items()}
        start = {w: 0 for w in core}
        for k in range(len(anchors) + 1):
            chunk = {}
            for w, seq in core.items():
                end = cuts[w][k] if k < len(anchors) else len(seq)
                if end > start[w]:
                    chunk[w] = seq[start[w]:end]
            if chunk:
                pr, rp = _align_all(chunk, [w for w in core_order if w in chunk], p, moves)
                profile += pr
                reps += rp
            if k < len(anchors):
                profile.append({w: core[w][cuts[w][k]][0] for w in core})
                reps.append((anchors[k],))
                start = {w: cuts[w][k] + 1 for w in core}
    else:
        profile, reps = _align_all(core, core_order, p, moves)
    for w in frags:
        profile, reps = _align_profile(profile, reps, sequences[w], w, p, moves)
    if meta is not None:
        meta["islands"] = int(p["island"])
    return [{w: [tid] for w, tid in col.items()} for col in profile]
