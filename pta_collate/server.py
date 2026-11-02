"""Local web application (FastAPI). Start with ``pta-collate serve``."""

from __future__ import annotations

import json
import os
import re
import threading
import traceback

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, JSONResponse, Response
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.staticfiles import StaticFiles

from . import __version__, collation, export_other, export_tei, extract
from . import project as P
from .project import now
from .align import ALIGNERS, collatex_available
from .normalize import PRESETS
from .units import build
from . import schema_store
from .validate import validate

STATIC = os.path.join(os.path.dirname(os.path.abspath(__file__)), "static")

app = FastAPI(title="PTA Collatio+")
app.add_middleware(GZipMiddleware, minimum_size=2000, compresslevel=5)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


# ------------------------------------------------------------------ security
# The server only listens on 127.0.0.1, but it can read and write files wherever the user can.
# A web page open in the same browser must therefore not be able to use it:
#  * Host check: defeats DNS rebinding (an attacker's domain resolving to 127.0.0.1);
#  * requests to /api must come from this application itself (Sec-Fetch-Site / Origin), which
#    stops cross-site requests (CSRF) also for GET;
#  * Content-Security-Policy: no inline script in the application, scripts only from here.
LOCAL_HOSTS = {"127.0.0.1", "localhost", "[::1]"}


def _hostname(host: str) -> str:
    host = (host or "").strip().lower()
    if host.startswith("["):
        return host[:host.find("]") + 1]
    return host.rsplit(":", 1)[0] if host.count(":") == 1 else host


def _inline_script_hashes(path: str) -> str:
    import base64
    import hashlib
    import re as _re
    try:
        with open(path, encoding="utf-8") as fh:
            page = fh.read()
    except OSError:
        return ""
    out = []
    for m in _re.finditer(r"<script>(.*?)</script>", page, _re.S):
        digest = hashlib.sha256(m.group(1).encode("utf-8")).digest()
        out.append("'sha256-" + base64.b64encode(digest).decode() + "'")
    return " ".join(out)


# no external hosts at all: scripts, styles and fonts come from this server
CSP_APP = ("default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; "
           "font-src 'self'; img-src 'self' data: blob:; connect-src 'self'; "
           "frame-src 'self'; object-src 'none'; base-uri 'none'; form-action 'self'; frame-ancestors 'self'")
VARIANZ_PAGE = "/static/varianz/index.html"
# the variance overview has inline scripts (allowed by hash) and only reads the export of this server
CSP_VARIANZ = ("default-src 'self'; script-src 'self' " + _inline_script_hashes(os.path.join(STATIC, "varianz", "index.html")) +
               "; style-src 'self' 'unsafe-inline'; font-src 'self'; "
               "img-src 'self' data: blob:; connect-src 'self'; object-src 'none'; base-uri 'none'; "
               "form-action 'self'; frame-ancestors 'self'")


@app.middleware("http")
async def _guard(request, call_next):
    if _hostname(request.headers.get("host", "")) not in LOCAL_HOSTS:
        return JSONResponse({"error": "Host not allowed"}, status_code=403)
    if request.url.path.startswith("/api/"):
        site = request.headers.get("sec-fetch-site")
        if site and site not in ("same-origin", "none"):
            return JSONResponse({"error": "Cross-site request refused"}, status_code=403)
        origin = request.headers.get("origin")
        if origin and request.method not in ("GET", "HEAD"):
            from urllib.parse import urlsplit
            o = urlsplit(origin)
            if _hostname(o.netloc) not in LOCAL_HOSTS or o.netloc.lower() != request.headers.get("host", "").lower():
                return JSONResponse({"error": "Cross-origin request refused"}, status_code=403)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    path = request.url.path
    if path == "/" or path.startswith("/static/"):
        # always ask the server (ETag): after an update no outdated script stays in the cache
        response.headers["Cache-Control"] = "no-cache"
    if path == "/":
        response.headers["Content-Security-Policy"] = CSP_APP
    elif path == VARIANZ_PAGE:
        response.headers["Content-Security-Policy"] = CSP_VARIANZ
    return response


class State:
    def __init__(self):
        self.lock = threading.RLock()
        self.proj = P.new_project()
        self.result = None
        self.model = None
        self.stale = False
        self.info_cache: dict[str, dict] = {}

    # ---------------------------------------------------------------
    def info(self, path):
        st = os.stat(path)
        key = f"{path}:{st.st_mtime}"
        if key not in self.info_cache:
            self.info_cache[key] = extract.read_info(path).to_dict()
        return self.info_cache[key]

    def rebuild(self):
        if self.result is None:
            return
        if self.model is not None and self.model.result is self.result:
            self.model = self.model.refresh(self.proj)
        else:
            self.model = build(self.result, self.proj)

    def autosave(self):
        if self.proj.get("_path"):
            P.save(self.proj)

    def load_result(self):
        self.result, self.model = None, None
        rp = P.result_path(self.proj)
        if self.proj.get("_path") and os.path.exists(rp):
            with open(rp, encoding="utf-8") as fh:
                self.result = json.load(fh)
            self.rebuild()


S = State()

# settings whose change makes the alignment stale
ALIGN_KEYS = {"witnesses", "segmentation", "segments", "normalization", "aligner", "nomina_sacra",
              "join_suspicious_breaks", "split_fused_words"}


def _public_project():
    return {k: v for k, v in S.proj.items() if not k.startswith("_")}


def suggested_path(proj: dict) -> str:
    """Default place for a new project file: the folder the transcriptions come from (as a rule
    the repository of the edition), named after the work if all transcriptions belong to one
    (pta0013.pta003.pta-MsLa.xml → pta0013.pta003.kollation.pta.json)."""
    files = [os.path.abspath(w["file"]) for w in proj.get("witnesses", []) if w.get("file")]
    if not files:
        return os.path.join(os.getcwd(), "kollation.pta.json")
    dirs = [os.path.dirname(f) for f in files]
    folder = max(dict.fromkeys(dirs), key=dirs.count)        # the folder most of them are in
    works = {".".join(os.path.basename(f).split(".")[:2]) for f in files
             if re.match(r"[A-Za-z]+\d+\.[A-Za-z]+\d+\.", os.path.basename(f))}
    name = f"{works.pop()}.kollation.pta.json" if len(works) == 1 else "kollation.pta.json"
    return os.path.join(folder, name)


def _state():
    ok, msg = collatex_available()
    return {
        "project": _public_project(),
        "path": S.proj.get("_path"),
        "has_result": S.result is not None,
        "stale": S.stale,
        "result_info": {k: S.result[k] for k in ("created", "seconds", "segmentation", "segments")} if S.result else None,
        "aligners": ALIGNERS,
        "collatex": {"available": ok, "message": msg},
        "presets": PRESETS,
        "cwd": os.getcwd(),
        "suggested_path": suggested_path(S.proj),
        "version": __version__,
    }


@app.exception_handler(Exception)
async def _err(request, exc):
    if isinstance(exc, HTTPException):
        return JSONResponse({"error": exc.detail}, status_code=exc.status_code)
    traceback.print_exc()
    return JSONResponse({"error": str(exc)}, status_code=500)


@app.get("/")
def index():
    return FileResponse(os.path.join(STATIC, "index.html"))


@app.get("/api/state")
def state():
    return _state()


# ------------------------------------------------------------------ project
@app.post("/api/project/new")
def project_new(body: dict | None = None):
    with S.lock:
        S.proj = P.new_project()
        S.result = S.model = None
        S.stale = False
        if body and body.get("path"):
            S.proj["_path"] = os.path.abspath(os.path.expanduser(body["path"]))
        return _state()


@app.post("/api/project/open")
def project_open(body: dict):
    path = os.path.abspath(os.path.expanduser(body["path"]))
    if not os.path.exists(path):
        raise HTTPException(404, f"Projektdatei nicht gefunden: {path}")
    with S.lock:
        S.proj = P.load(path)
        S.stale = False
        S.load_result()
        return _state()


@app.post("/api/project/save")
def project_save(body: dict | None = None):
    with S.lock:
        path = (body or {}).get("path") or S.proj.get("_path")
        if not path:
            raise HTTPException(400, "Bitte einen Speicherort für die Projektdatei angeben.")
        path = os.path.abspath(os.path.expanduser(path))
        if not path.endswith(".json"):
            path += ".pta.json"
        P.save(S.proj, path)
        if S.result is not None:
            with open(P.result_path(S.proj), "w", encoding="utf-8") as fh:
                json.dump(S.result, fh, ensure_ascii=False)
        return _state()


@app.put("/api/project")
def project_update(body: dict):
    with S.lock:
        for k, v in body.items():
            if k.startswith("_") or k == "edits":
                continue
            if k in ALIGN_KEYS and S.proj.get(k) != v:
                S.stale = S.result is not None
            S.proj[k] = v
        if "units" in body and S.result is not None:
            S.rebuild()
        S.autosave()
        return _state()


# --------------------------------------------------------------- files
@app.get("/api/fs")
def fs(path: str = ""):
    path = os.path.abspath(os.path.expanduser(path or os.getcwd()))
    if os.path.isfile(path):
        path = os.path.dirname(path)
    if not os.path.isdir(path):
        raise HTTPException(404, f"Ordner nicht gefunden: {path}")
    dirs, files = [], []
    try:
        for name in sorted(os.listdir(path), key=str.lower):
            if name.startswith("."):
                continue
            full = os.path.join(path, name)
            if os.path.isdir(full):
                dirs.append(name)
            elif name.lower().endswith(".xml") or name.endswith(".pta.json"):
                files.append(name)
    except PermissionError:
        pass
    return {"path": path, "parent": os.path.dirname(path), "dirs": dirs, "files": files}


@app.post("/api/witnesses/add")
def witnesses_add(body: dict):
    paths = []
    for p in body.get("paths", []):
        p = os.path.abspath(os.path.expanduser(p))
        if os.path.isdir(p):
            paths += [os.path.join(p, f) for f in sorted(os.listdir(p)) if f.endswith(".xml") and "__cts__" not in f]
        else:
            paths.append(p)
    added, skipped = [], []
    with S.lock:
        have = {w["file"] for w in S.proj["witnesses"]}
        ids = {w["id"] for w in S.proj["witnesses"]}
        for p in paths:
            if p in have:
                continue
            try:
                info = S.info(p)
            except Exception as exc:  # not a TEI transcription
                skipped.append({"file": p, "reason": str(exc)[:200]})
                continue
            tree = extract.parse(p)
            if tree.getroot().find(".//tei:sourceDesc/tei:msDesc", extract.NS) is None:
                skipped.append({"file": p, "reason": "keine Handschriften-Transkription (msDesc fehlt)"})
                continue
            wid = info["id"]
            while wid in ids:
                wid += "x"
            ids.add(wid)
            S.proj["witnesses"].append({"file": p, "id": wid, "siglum": wid, "include": True, "layers": "both"})
            added.append(wid)
        if added and not S.proj.get("structure_witness"):
            S.proj["structure_witness"] = S.proj["witnesses"][0]["id"]
        if added:
            S.stale = S.result is not None
        S.autosave()
        st = _state()
        st["added"], st["skipped"] = added, skipped
        return st


@app.get("/api/witnesses/info")
def witnesses_info():
    out = {}
    for w in S.proj["witnesses"]:
        try:
            out[w["id"]] = S.info(w["file"])
        except Exception as exc:
            out[w["id"]] = {"error": str(exc)}
    return out


@app.post("/api/preview")
def preview(body: dict):
    w = next((w for w in S.proj["witnesses"] if w["id"] == body.get("id")), None)
    if w is None:
        raise HTTPException(404, "Zeuge nicht gefunden")
    proj = dict(S.proj)
    for k in ("normalization", "segmentation", "nomina_sacra"):
        if k in body:
            proj[k] = body[k]
    return collation.preview(proj, w, body.get("segment") or None, int(body.get("limit", 300)))


@app.post("/api/check")
def check():
    """Transcription check: words probably split by a plain <lb/>."""
    return collation.check(S.proj)


# ------------------------------------------------------------- collation
@app.post("/api/collate")
def collate():
    with S.lock:
        result = collation.run(S.proj)
        S.result = result
        S.stale = False
        S.proj.setdefault("runs", []).append({
            "when": result["created"], "aligner": S.proj["aligner"].get("engine"),
            "seconds": result["seconds"], "segmentation": result["segmentation"]})
        S.rebuild()
        if S.proj.get("_path"):
            P.save(S.proj)
            with open(P.result_path(S.proj), "w", encoding="utf-8") as fh:
                json.dump(result, fh, ensure_ascii=False)
        return _model_payload()


def _model_payload():
    if S.model is None:
        raise HTTPException(409, "Noch keine Kollation vorhanden.")
    data = S.model.to_json()
    data["edits"] = S.proj.get("edits", [])
    data["stale"] = S.stale
    data["settings"] = {"base": (S.proj.get("synopsis") or {}).get("base", "majority")}
    data["title"] = S.proj.get("title") or ""
    # serialise directly: FastAPI's generic encoder is slow for large collations
    return Response(json.dumps(data, ensure_ascii=False), media_type="application/json")


@app.get("/api/model")
def model():
    with S.lock:
        return _model_payload()


@app.get("/api/unit")
def unit(key: str):
    with S.lock:
        if S.model is None:
            raise HTTPException(409, "Noch keine Kollation vorhanden.")
        d = S.model.unit_detail(key)
        if d is None:
            raise HTTPException(404, "Stelle nicht gefunden")
        return d


@app.post("/api/edit")
def edit(body: dict):
    ops = body.get("ops") or [body]
    with S.lock:
        if S.result is None:
            raise HTTPException(409, "Noch keine Kollation vorhanden.")
        batch = f"b{len(S.proj['edits'])}-{now()}" if len(ops) > 1 else None
        for op in ops:
            if op.get("op") not in ("move", "split", "join", "attr", "lem", "nest", "link", "unlink", "reject_link",
                                    "lacuna", "conj", "insert", "confirm"):
                raise HTTPException(400, f"Unbekannte Operation: {op.get('op')}")
            if batch:
                op = dict(op, batch=batch)      # undone together
            S.proj["edits"].append(op)
        S.rebuild()
        S.autosave()
        return _model_payload()


@app.post("/api/undo")
def undo():
    with S.lock:
        if S.proj.get("edits"):
            batch = S.proj["edits"][-1].get("batch")
            S.proj["edits"].pop()
            while batch and S.proj["edits"] and S.proj["edits"][-1].get("batch") == batch:
                S.proj["edits"].pop()
        S.rebuild()
        S.autosave()
        return _model_payload()


@app.post("/api/edits/remove")
def edits_remove(body: dict):
    with S.lock:
        idx = sorted(set(int(i) for i in body.get("indices", [])), reverse=True)
        for i in idx:
            if 0 <= i < len(S.proj["edits"]):
                del S.proj["edits"][i]
        S.rebuild()
        S.autosave()
        return _model_payload()


# ---------------------------------------------------------------- export
FORMATS = {
    "tei": ("application/xml", ".xml"),
    "html": ("text/html", "-synopse.html"),
    "csv": ("text/csv", ".csv"),
    "nexus": ("text/plain", ".nex"),
    "json": ("application/json", "-collatex.json"),
}


def _export(fmt: str, lang: str = "de", keys: bool = False) -> bytes:
    if S.model is None:
        raise HTTPException(409, "Noch keine Kollation vorhanden.")
    if fmt == "tei":
        return export_tei.export_tei(S.model, S.proj, unit_keys=keys)
    if fmt == "html":
        return export_other.export_synopsis_html(S.model, S.proj, lang)
    if fmt == "csv":
        return export_other.export_csv(S.model)
    if fmt == "nexus":
        return export_other.export_nexus(S.model)
    if fmt == "json":
        return export_other.export_collatex_json(S.model)
    raise HTTPException(404, f"Unbekanntes Format: {fmt}")


def _export_name(fmt):
    """File name from the edition URN (without urn:cts:), next to the project file."""
    base = S.proj.get("_path") or os.path.join(os.getcwd(), "kollation.pta.json")
    urn = export_tei.edition_urn(S.model, S.proj)
    return export_tei.export_path(os.path.dirname(base), urn, FORMATS[fmt][1])


@app.get("/api/export/{fmt}")
def export(fmt: str, lang: str = "de", keys: int = 0):
    """keys=1 (TEI only): app/@n carries the unit key, so the variance overview can link back."""
    if fmt not in FORMATS:
        raise HTTPException(404, f"Unbekanntes Format: {fmt}")
    with S.lock:
        data = _export(fmt, lang, bool(keys))
    fname = export_tei.file_stem(export_tei.edition_urn(S.model, S.proj)) + FORMATS[fmt][1]
    return Response(data, media_type=FORMATS[fmt][0],
                    headers={"Content-Disposition": f'attachment; filename="{fname}"'})


@app.post("/api/export/{fmt}/save")
def export_save(fmt: str, body: dict | None = None):
    """Write the export next to the project file (a POST: it changes files on disk)."""
    if fmt not in FORMATS:
        raise HTTPException(404, f"Unbekanntes Format: {fmt}")
    lang = (body or {}).get("lang", "de")
    with S.lock:
        data = _export(fmt, lang)
        name, note = _export_name(fmt)
        with open(name, "wb") as fh:
            fh.write(data)
        if fmt == "tei":
            _copy_schema(os.path.dirname(name))
        return {"saved": name, "note": note}


def _copy_schema(folder):
    """Put the collation schema next to the exported TEI so that oXygen & co. find it."""
    import shutil
    for name in ("tei-pta_collation.rng", "tei-pta_collation.sch"):
        src, dst = schema_store.path(name), os.path.join(folder, name)
        # replaced when the schema in use has changed (these copies always come from here)
        if not os.path.exists(dst) or open(src, "rb").read() != open(dst, "rb").read():
            shutil.copy(src, dst)


@app.post("/api/validate")
def validate_tei(body: dict | None = None):
    schema_store.check(timeout=5)       # at most once an hour: is there a newer PTA schema?
    with S.lock:
        xml = _export("tei")
    out = {"collation": validate(xml, "collation")}
    if (body or {}).get("full", True):
        out["full"] = validate(xml, "full")
    out["schema"] = schema_store.status()
    return out


@app.get("/api/schema")
def schema_status():
    return schema_store.status()


@app.post("/api/schema/check")
def schema_check():
    """Look for a newer PTA schema now (also when the automatic check is switched off)."""
    return schema_store.check(force=True)
