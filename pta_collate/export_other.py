"""Further export formats: CSV, Nexus, CollateX JSON and the stand-alone synopsis (HTML)."""

from __future__ import annotations

import csv
from html import escape as html_escape
import io
import json
import os
import re

from . import __version__
from .units import Model

STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")


def _cell(v) -> str:
    """Protect against formula injection in spreadsheets (=, +, -, @ at the start)."""
    v = "" if v is None else str(v)
    return "'" + v if v[:1] in ("=", "+", "-", "@", "\t", "\r") else v


def export_csv(model: Model) -> bytes:
    out = io.StringIO()
    wits = [w["id"] for w in model.result["witnesses"]]
    labels = [w["label"] for w in model.result["witnesses"]]
    w = csv.writer(out)
    w.writerow([_cell(x) for x in ["Abschnitt", "Stelle", "Variante", "Lemma"] + labels])
    for i, u in enumerate(model.units, 1):
        lem = next((r["t"] for r in u["readings"] if r["id"] == u["lem"]), "")
        w.writerow([_cell(x) for x in [u["seg"], i, "ja" if u["variant"] else "", lem] +
                    [u["cells"].get(x, {}).get("t", "") if x in u["cells"] else "—" for x in wits]])
    return out.getvalue().encode("utf-8-sig")


def export_nexus(model: Model, include_orthographic: bool = False) -> bytes:
    """Character matrix for phylogenetic software (e.g. SplitsTree): one character per
    variation unit, one state per reading. Witnesses absent from a section are '?'."""
    taxa = [w for w in model.result["witnesses"] if w["layer"] != "ac"]
    chars = []
    for u in model.units:
        if not u["variant"]:
            continue
        rs = [r for r in u["readings"] if r["wits"]]      # editorial readings have no witnesses
        if not include_orthographic:
            # merge orthographic variants into their group head
            heads = {}
            for r in rs:
                key = r["group"] if r["group"] else r["id"]
                heads.setdefault(key, []).append(r)
            if len(heads) < 2:
                continue
            state = {}
            for i, (_, members) in enumerate(heads.items()):
                for r in members:
                    for wit in r["wits"]:
                        state[wit] = i
        else:
            state = {wit: i for i, r in enumerate(rs) for wit in r["wits"]}
        if len(set(state.values())) > 32:
            continue
        chars.append(state)
    symbols = "0123456789ABCDEFGHIJKLMNOPQRSTUV"
    lines = ["#NEXUS", "", "BEGIN TAXA;", f"  DIMENSIONS NTAX={len(taxa)};", "  TAXLABELS"]
    for t in taxa:
        lines.append(f"    {t['siglum']}")
    lines += ["  ;", "END;", "", "BEGIN CHARACTERS;",
              f"  DIMENSIONS NCHAR={len(chars)};",
              f'  FORMAT DATATYPE=STANDARD MISSING=? GAP=- SYMBOLS="{" ".join(symbols)}";', "  MATRIX"]
    for t in taxa:
        row = "".join(symbols[c[t["id"]]] if t["id"] in c else "?" for c in chars)
        lines.append(f"    {t['siglum']:<12} {row}")
    lines += ["  ;", "END;", ""]
    return "\n".join(lines).encode("utf-8")


def export_collatex_json(model: Model) -> bytes:
    """CollateX-compatible alignment table (usable e.g. with collation-viz)."""
    wits = [w["id"] for w in model.result["witnesses"]]
    table = []
    for r in model.rows:
        entry = []
        for w in wits:
            entry.append([{"t": model.tokens[t]["t"], "n": model.tokens[t]["n"]} for t in r["cells"].get(w, [])])
        table.append(entry)
    return json.dumps({"witnesses": [w["label"] for w in model.result["witnesses"]], "table": table},
                      ensure_ascii=False).encode("utf-8")


# fonts embedded in the HTML synopsis: Greek and Latin text, the interface in Latin script
EMBED_FONTS = re.compile(r"^(gentium-plus-(latin|latin-ext|greek|greek-ext)-(400|700)-normal"
                         r"|gentium-plus-(latin|greek|greek-ext)-400-italic"
                         r"|source-sans-3-(latin|latin-ext)-(400|600)-normal)\.woff2$")


def _embedded_fonts() -> str:
    """@font-face rules of static/fonts/fonts.css for EMBED_FONTS, with the fonts as data: URIs."""
    import base64
    folder = os.path.join(STATIC, "fonts")
    with open(os.path.join(folder, "fonts.css"), encoding="utf-8") as fh:
        rules = re.findall(r"@font-face \{.*?\}", fh.read(), re.S)
    out = []
    for rule in rules:
        m = re.search(r"url\(([^)]+\.woff2)\)", rule)
        if not m or not EMBED_FONTS.match(m.group(1)):
            continue
        with open(os.path.join(folder, m.group(1)), "rb") as fh:
            data = base64.b64encode(fh.read()).decode("ascii")
        out.append(rule.replace(m.group(0), f"url(data:font/woff2;base64,{data})"))
    return "\n".join(out) + "\n"


def export_synopsis_html(model: Model, proj: dict, lang: str = "de") -> bytes:
    """Stand-alone, read-only synopsis page with the same rendering as the application."""
    data = model.to_json()
    data["title"] = proj.get("title") or "Kollation"
    data["settings"] = {"base": (proj.get("synopsis") or {}).get("base", "majority")}
    with open(os.path.join(STATIC, "style.css"), encoding="utf-8") as fh:
        css = fh.read()
    # the file is opened on its own: fonts embedded instead of the @import of static/fonts
    css = re.sub(r'@import url\("fonts/fonts\.css"\);[^\n]*\n', "", css)
    css = _embedded_fonts() + css
    lang = lang if lang in ("de", "en") else "de"
    js = f"window.PTA_LANG = {json.dumps(lang)};\n"
    for name in ("i18n-en.js", "i18n.js", "graph.js"):
        with open(os.path.join(STATIC, name), encoding="utf-8") as fh:
            js += fh.read() + "\n"
    with open(os.path.join(STATIC, "synopsis.js"), encoding="utf-8") as fh:
        js += fh.read()
    # inside <script>: no "<" at all (closes neither the element nor opens a comment)
    payload = json.dumps(data, ensure_ascii=False).replace("<", "\\u003c")
    title = html_escape(str(data["title"]))
    html = f"""<!doctype html>
<html lang="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>Synopse – {title}</title>
<style>{css}</style></head>
<body class="standalone">
<header class="topbar"><div class="brand">Synopse <span class="muted">· {title}</span></div></header>
<main id="synopsis-root" class="synopsis-standalone"></main>
<footer class="site-foot">
  <span>PTA Collatio+ {__version__}</span>
  <a href="https://orcid.org/0000-0001-5382-6322" title="ORCID 0000-0001-5382-6322">Annette von Stockhausen</a>
  <a href="https://pta.bbaw.de">Patristisches Textarchiv</a>
  <a href="https://bibelexegese.bbaw.de">AV „Die Alexandrinische und antiochenische Bibelexegese in der Spätantike“</a>
</footer>
<script>window.PTA_DATA = {payload};</script>
<script>{js}</script>
<script>PTASynopsis.mountStandalone(document.getElementById('synopsis-root'), window.PTA_DATA);</script>
</body></html>"""
    return html.encode("utf-8")
