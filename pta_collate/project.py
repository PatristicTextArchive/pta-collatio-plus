"""Project file: every setting and every manual correction of a collation.

The project file (JSON) is meant to live in the git repository of the edition
next to the transcriptions. Paths of witnesses are stored relative to it.
"""

from __future__ import annotations

import copy
import datetime as _dt
import json
import os

from .normalize import PRESETS

DEFAULTS = {
    "version": 1,
    "title": "",
    "editor": {"name": "", "id": ""},
    "edition_urn": "",            # e.g. urn:cts:pta:pta0013.pta003.pta-grc1; empty = derived
    "witnesses": [],              # [{file, id, siglum, include, layers: both|pc|ac}]
    "structure_witness": "",      # witness whose header/structure is used for the export
    "segmentation": {"mode": "auto"},   # auto | none | div | milestone:<unit>
    "segments": [],               # selected section keys ([] = all)
    "nomina_sacra": "expan",
    "join_suspicious_breaks": False,   # join words split by a plain <lb/> (see Prüfung)
    "split_fused_words": False,        # split words written without space (see Prüfung)
    "normalization": dict(PRESETS["standard"], preset="standard"),
    "aligner": {"engine": "builtin", "threshold": 0.6, "algorithm": "dekker",
                "comparator": "equality", "distance": 0.6},
    "units": {"merge_adjacent": True, "detect_transpositions": True, "transposition_window": 6, "split_displaced": True,
              "detect_long_transpositions": True, "long_transposition_distance": 150,
              "lacuna_min": 40},
    "synopsis": {"base": "majority"},
    "sources": [],                # conjecturers and earlier editions: [{id, name, kind: person|bibl, ref}]
    "edits": [],
    "runs": [],                   # history of collation runs (for revisionDesc)
}


def new_project() -> dict:
    return copy.deepcopy(DEFAULTS)


def _merge(base: dict, data: dict) -> dict:
    out = copy.deepcopy(base)
    for k, v in (data or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _merge(out[k], v)
        else:
            out[k] = v
    return out


def load(path: str) -> dict:
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    proj = _merge(DEFAULTS, data)
    base = os.path.dirname(os.path.abspath(path))
    for w in proj["witnesses"]:
        if not os.path.isabs(w["file"]):
            w["file"] = os.path.normpath(os.path.join(base, w["file"]))
    proj["_path"] = os.path.abspath(path)
    return proj


def save(proj: dict, path: str | None = None) -> str:
    path = os.path.abspath(path or proj.get("_path") or "collation.pta.json")
    base = os.path.dirname(path)
    data = {k: v for k, v in proj.items() if not k.startswith("_")}
    data = copy.deepcopy(data)
    for w in data["witnesses"]:
        try:
            w["file"] = os.path.relpath(w["file"], base)
        except ValueError:  # different drive on Windows
            pass
    os.makedirs(base, exist_ok=True)
    with open(path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, ensure_ascii=False, indent=2)
    proj["_path"] = path
    return path


def result_path(proj: dict) -> str:
    p = proj.get("_path") or os.path.abspath("collation.pta.json")
    stem = p[:-9] if p.endswith(".pta.json") else os.path.splitext(p)[0]
    return stem + ".alignment.json"


def now() -> str:
    return _dt.datetime.now().replace(microsecond=0).isoformat()
