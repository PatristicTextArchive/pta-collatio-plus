"""Build pta_collate/static/varianz/index.html from the stand-alone variance overview
("pta-varianz-arbeitsfassung.html").

Usage:  python3 scripts/build_varianz.py PATH/TO/pta-varianz          (the repository)
        python3 scripts/build_varianz.py PATH/TO/pta-varianz-arbeitsfassung.html

With the repository, the working version is built from its sources with the repository's own
build.py (as dist/pta-varianz-arbeitsfassung.html, which must agree with the sources), so the
result does not depend on whether dist/ was rebuilt.

Every change is a literal replacement that must match exactly once, so a new version of the
source file that no longer fits fails loudly instead of being half patched. Changes:

 1. d3 is loaded from the local d3.min.js instead of the inline copy (checked to be identical)
 2. no fonts from Google: local fonts.css, plus the colour-scheme script of the application
 3. colours and fonts of the application (scripts/varianz/override.css)
 4. title block hidden, no own language switch, no loading of other files
 5. language from ?lang=, sigla without markup characters, ?xml= only for the TEI export
 6. only Grid, Witness combinations and Stemma: no Synopsis and no Graph/TRAViz (the application
    has its own synopsis and variant graph), no Sankey (it needs witness groups); "show in graph"
    in the apparatus entry opens the unit in the synopsis of the application
 7. footer reduced to the explanation of the evaluation
 8. one untranslated note translated
"""
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "pta_collate/static/varianz/index.html"
D3 = ROOT / "pta_collate/static/varianz/d3.min.js"
OVERRIDE = ROOT / "scripts/varianz/override.css"


def rep(s, old, new, count=1):
    n = s.count(old)
    if n != count:
        sys.exit(f"build_varianz: expected {count}x, found {n}x: {old[:90]!r}")
    return s.replace(old, new)


def rep_re(s, pat, new, flags=re.S):
    m = list(re.finditer(pat, s, flags))
    if len(m) != 1:
        sys.exit(f"build_varianz: pattern found {len(m)}x: {pat[:90]!r}")
    return s[: m[0].start()] + m[0].expand(new) + s[m[0].end():]


def from_repo(repo: pathlib.Path) -> str:
    """The working version built from the sources of the repository (its build.py)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("pta_varianz_build", repo / "build.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    html = mod.page(mod.read(repo / "src" / "template.html"), offline=True, work=True)
    dist = repo / "dist" / "pta-varianz-arbeitsfassung.html"
    if dist.exists() and dist.read_text(encoding="utf-8") != html:
        print("build_varianz: Hinweis – dist/pta-varianz-arbeitsfassung.html ist nicht auf dem Stand der Quellen; verwendet werden die Quellen")
    return html


def main(src):
    src = pathlib.Path(src)
    s = from_repo(src) if src.is_dir() else src.read_text(encoding="utf-8")

    # 1. d3
    m = re.search(r"<script>/\* d3 v7\.8\.5[^\n]*\n(.*?)\n?</script>", s, re.S)
    if not m:
        sys.exit("build_varianz: inline d3 not found")
    inline = m.group(1).strip()
    if inline != D3.read_text(encoding="utf-8").strip():
        sys.exit("build_varianz: inline d3 differs from static/varianz/d3.min.js")
    s = s[: m.start()] + '<script src="d3.min.js"></script>' + s[m.end():]

    # 2. fonts / colour scheme
    s = rep_re(s, r'<link rel="preconnect" href="https://fonts\.googleapis\.com">\n<link rel="stylesheet" href="https://fonts\.googleapis\.com/[^"]*">',
               '<script src="../theme.js"></script>\n<link rel="stylesheet" href="../fonts/fonts.css">')
    if "googleapis" in s or "gstatic" in s:
        sys.exit("build_varianz: reference to Google left")

    # 3. colours and fonts of the application
    first = s.index("</style>")
    s = s[:first] + "\n" + OVERRIDE.read_text(encoding="utf-8") + s[first:]

    # 4. header: title block hidden, language switch and loader removed
    s = rep(s, '<header class="work">\n    <div>', '<header class="work">\n    <div hidden>')
    s = rep_re(s, r'\n      <span class="seg lang" role="group"[^\n]*</span>', "")
    s = rep_re(s, r'\n    <div class="loader needs-data" hidden>.*?\n    </div>', "")
    s = rep_re(s, r'(<div class="drop" id="dropzone">).*?(\n      <p class="msg load-err" hidden></p>)',
               r'\1\n      <p class="i18n-de">Der TEI-Export der Kollation wird geladen …</p>'
               r'\n      <p class="i18n-en">Loading the TEI export of the collation …</p>\2')
    s = rep(s, "    document.addEventListener('drop', (e) => { const f = e.dataTransfer && e.dataTransfer.files[0]; if (f) readFile(f); });",
            "    // PTA Collatio+: only the TEI export of the current collation, no other files")

    # 5. language, sigla, ?xml=
    s = rep(s, "  try { const v = localStorage.getItem('pta-varianz-lang'); if (v === 'en' || v === 'de') LANG = v; else if (!/^de/i.test(navigator.language || 'de')) LANG = 'en'; } catch (e) {}",
            "  // PTA Collatio+: the language comes from the application (?lang=de|en)\n"
            "  try { const q = new URLSearchParams(location.search).get('lang'); if (q === 'en' || q === 'de') LANG = q; else { const v = localStorage.getItem('pta-varianz-lang'); if (v === 'en' || v === 'de') LANG = v; else if (!/^de/i.test(navigator.language || 'de')) LANG = 'en'; } } catch (e) {}")
    s = rep(s, "    if (!w) return id;\n    if (!w.sigParts) return w.siglum;\n    if (!SIGCACHE.has(w)) SIGCACHE.set(w, w.sigParts.map((p) => (p.sup ? mapChars(p.t, SUP) : p.sub ? mapChars(p.t, SUB) : p.t)).join(''));",
            "    const clean = (t) => String(t).replace(/[<>&\"']/g, '');   // sigla end up in HTML: no markup characters\n"
            "    if (!w) return clean(id);\n    if (!w.sigParts) return clean(w.siglum);\n"
            "    if (!SIGCACHE.has(w)) SIGCACHE.set(w, clean(w.sigParts.map((p) => (p.sup ? mapChars(p.t, SUP) : p.sub ? mapChars(p.t, SUB) : p.t)).join('')));")
    s = rep(s, "    try { const q = new URLSearchParams(location.search).get('xml'); if (q) loadUrl(q); } catch (e) {}",
            "    try { const q = new URLSearchParams(location.search).get('xml'); if (q && /^\\/api\\/export\\/tei(\\?|$)/.test(q)) loadUrl(q); } catch (e) {}")

    # 6. views
    s = rep(s, "    { id: 'sankey', label: 'Sankey' },", "    // no Sankey here: it needs witness groups, which a collation does not have yet")
    s = rep(s, "    { id: 'synopse', label: 'Synopse' },", "    // the synopsis view is left out here: PTA Collatio+ has its own synopsis")
    s = rep(s, "    { id: 'graph', label: 'Graph' },", "    // no Graph and no TRAViz here: the application shows the variant graph itself")
    s = rep(s, "    { id: 'traviz', label: 'TRAViz' },\n", "")
    # links from the apparatus entry: instead of Graph, TRAViz and Synopsis of the overview one link
    # "show in graph" that opens the unit in the synopsis of the application with its variant graph
    # (the TEI export for the overview carries the unit key in app/@n; only inside the application)
    s = rep_re(s, r"\n      h \+= `<p class=\"note\"><button type=\"button\" class=\"link\" data-show=\"graph\"[^\n]*",
               "\n      { const a = u.dom && u.dom.app && u.dom.app.closest ? u.dom.app.closest('app[n]') : null;"
               "\n        if (a && window.parent !== window) h += `<p class=\"note\"><button type=\"button\" class=\"link\" data-appkey=\"${esc(a.getAttribute('n'))}\">${L('im Graph zeigen')}</button></p>`; }")
    s = rep(s, "    P.querySelectorAll('[data-show]').forEach((el) => (el.onclick = () => {",
            "    P.querySelectorAll('[data-appkey]').forEach((el) => (el.onclick = () => window.parent.postMessage({ type: 'pta-show-unit', key: el.getAttribute('data-appkey') }, location.origin)));\n"
            "    P.querySelectorAll('[data-show]').forEach((el) => (el.onclick = () => {")

    # 7. footer: only the explanation of the evaluation
    s = rep_re(s, r'(<div class="i18n-de">)Ein Werkzeug zum .*? · (<details class="method">)', r"\1\2")
    s = rep_re(s, r'(<div class="i18n-en">)A tool for the .*? · (<details class="method">)', r"\1\2")

    # 8. untranslated note
    de = "Gezählt werden Variationseinheiten mit den gewählten Typen, die vom Bezug (${esc(refLabel())}) abweichen; „je 100 W.“ bezieht sich auf den erhaltenen Text des Zeugen${S.ref === 'leit' ? ', soweit auch der Leitzeuge Text bietet' : ''}."
    if "<p class=\"note\">" + de in s:
        en = "Counted are variation units of the selected types that deviate from the reference (${esc(refLabel())}); “per 100 w.” refers to the extant text of the witness${S.ref === 'leit' ? ', as far as the lead witness has text as well' : ''}."
        s = rep(s, '<p class="note">' + de + "</p>",
                "<p class=\"note\">${LANG === 'en'\n          ? `" + en + "`\n          : `" + de + "`}</p>")

    # checks
    for bad in ("data-lang=", "type=\"file\"", "id: 'sankey'", "id: 'synopse'", "id: 'graph'", "id: 'traviz'", "data-show=\"", "Ein Werkzeug zum", "A tool for the"):
        if bad in s:
            sys.exit(f"build_varianz: {bad!r} still present")
    if "workMode: true" not in s:
        sys.exit("build_varianz: mount(... workMode: true) missing")
    if re.search(r"<script[^>]+src=\"https?:", s) or re.search(r"<link[^>]+href=\"https?:", s):
        sys.exit("build_varianz: external resource left")
    OUT.write_text(s, encoding="utf-8")
    print(f"written {OUT.relative_to(ROOT)} ({len(s):,} characters)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
