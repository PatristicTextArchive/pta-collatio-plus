"""Exchangeable aligners.

An aligner receives, per witness, a list of ``(token_id, n)`` pairs and returns
alignment rows: a list of ``{witness: [token_id, …]}`` dicts in text order.
Every token of every witness appears exactly once, and the order of tokens per
witness is preserved.
"""

from __future__ import annotations

from .builtin import align_builtin
from .collatex import align_collatex, collatex_available

ALIGNERS = {
    "builtin": "Eingebaut (Inseln + Needleman-Wunsch mit affinen Lücken, ohne Java)",
    "collatex": "CollateX: Dekker-Algorithmus (Java)",
}


def run_aligner(sequences: dict[str, list[tuple[str, str]]], settings: dict,
                meta: dict | None = None) -> list[dict[str, list[str]]]:
    """``meta`` (optional) receives additional findings, e.g. ``meta["transpositions"]``."""
    engine = settings.get("engine", "builtin")
    if engine == "collatex":
        rows = align_collatex(sequences, settings)
    else:
        rows = align_builtin(sequences, settings, meta)
    _check(sequences, rows)
    return rows


def _check(sequences, rows):
    for wit, seq in sequences.items():
        got = [tid for row in rows for tid in row.get(wit, [])]
        want = [tid for tid, _ in seq]
        if got != want:
            raise RuntimeError(f"Aligner hat die Tokenfolge von {wit} verändert ({len(got)} statt {len(want)} Token)")
