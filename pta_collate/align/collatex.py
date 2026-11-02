"""CollateX adapter (Java).

Uses the CollateX 1.8 build with the TSAligner extensions that the PTA
collator already ships. A tiny script-engine shim (``vendor/pta-noscript-shim.jar``)
replaces the Nashorn engine CollateX expects, so CollateX also runs on
Java 15 and newer.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
VENDOR = os.path.normpath(os.path.join(HERE, "..", "..", "vendor"))
JAR = os.environ.get("PTA_COLLATEX_JAR", os.path.join(VENDOR, "collatex-tools-1.8-SNAPSHOT-TSAligner.jar"))
SHIM = os.path.join(VENDOR, "pta-noscript-shim.jar")

ALGORITHMS = ["needleman-wunsch", "dekker"]
COMPARATORS = ["equality", "levenshtein", "levenshteinNormalized", "jaccard"]


def collatex_available() -> tuple[bool, str]:
    if not shutil.which("java"):
        return False, "Java wurde nicht gefunden"
    if not os.path.exists(JAR):
        return False, f"CollateX-Jar fehlt: {JAR}"
    return True, "ok"


def align_collatex(sequences: dict[str, list[tuple[str, str]]], settings: dict) -> list[dict[str, list[str]]]:
    ok, msg = collatex_available()
    if not ok:
        raise RuntimeError(msg)
    algorithm = settings.get("algorithm", "dekker")
    comparator = settings.get("comparator", "equality")
    payload = {
        "algorithm": algorithm,
        "witnesses": [
            {"id": wit, "tokens": [{"t": n + " ", "n": n, "tid": tid} for tid, n in seq]}
            for wit, seq in sequences.items() if seq
        ],
    }
    if comparator and comparator != "equality":
        tc = {"type": comparator}
        if settings.get("distance") is not None:
            tc["distance"] = float(settings["distance"])
        payload["tokenComparator"] = tc
    empty = [wit for wit, seq in sequences.items() if not seq]
    if len(payload["witnesses"]) < 2:
        # nothing to align against – put each token in its own row
        rows = []
        for w in payload["witnesses"]:
            rows += [{w["id"]: [t["tid"]]} for t in w["tokens"]]
        return rows
    with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8") as fh:
        json.dump(payload, fh, ensure_ascii=False)
        path = fh.name
    try:
        cp = os.pathsep.join([JAR, SHIM]) if os.path.exists(SHIM) else JAR
        proc = subprocess.run(
            ["java", "-cp", cp, "eu.interedition.collatex.tools.CollateX", "-t", "-f", "json", path],
            capture_output=True, text=True, encoding="utf-8", timeout=int(settings.get("timeout", 900)),
        )
    finally:
        os.unlink(path)
    out = proc.stdout.strip()
    if not out.startswith("{"):
        err = "\n".join(l for l in proc.stderr.splitlines() if "JAVA_TOOL_OPTIONS" not in l)
        raise RuntimeError(f"CollateX ist fehlgeschlagen ({algorithm}): {(out + ' ' + err).strip()[:600]}")
    data = json.loads(out)
    wits = data["witnesses"]
    rows = []
    for entry in data["table"]:
        row = {}
        for wit, cell in zip(wits, entry):
            if cell:
                row[wit] = [tok["tid"] for tok in cell]
        if row:
            rows.append(row)
    for w in empty:
        pass  # witnesses without tokens simply never appear in a row
    return rows
