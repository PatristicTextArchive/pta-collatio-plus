"""Derive the collation schema (RNG + Schematron) from the PTA schema.

    python scripts/derive_schema.py [--fetch]

``--fetch`` downloads the current tei-pta.rng / tei-pta.sch / tei-pta.odd from
GitHub first; otherwise the copies in ``schema/`` are used. This updates the copy shipped with
the application; at run time the application itself keeps the schema current
(``pta_collate/schema_store.py``). The only change is
the rule "Variation needs a lem", which becomes a warning (Schematron
``role="warning"``) – exactly what ``schema/tei-pta_collation.odd`` declares.
"""

from __future__ import annotations

import os
import sys
import urllib.request

HERE = os.path.dirname(os.path.abspath(__file__))
SCHEMA = os.path.normpath(os.path.join(HERE, "..", "schema"))

sys.path.insert(0, os.path.join(HERE, ".."))
from pta_collate.schema_store import BASE, derive as derive_text  # noqa: E402  (one place for the rule)


def fetch():
    for name in ("tei-pta.odd", "tei-pta.rng", "tei-pta.sch"):
        with urllib.request.urlopen(BASE + name) as r, open(os.path.join(SCHEMA, name), "wb") as fh:
            fh.write(r.read())
        print("geladen:", name)


def derive():
    for src, dst in (("tei-pta.rng", "tei-pta_collation.rng"), ("tei-pta.sch", "tei-pta_collation.sch")):
        with open(os.path.join(SCHEMA, src), encoding="utf-8") as fh:
            text = fh.read()
        try:
            text = derive_text(src, text)
        except ValueError as e:
            raise SystemExit(str(e))
        with open(os.path.join(SCHEMA, dst), "w", encoding="utf-8") as fh:
            fh.write(text)
        print("erzeugt:", dst)


if __name__ == "__main__":
    if "--fetch" in sys.argv:
        fetch()
    derive()
