"""Keep the PTA schema current.

The PTA schema (https://github.com/PatristicTextArchive/Schema) changes from time to time. The
application ships a copy in ``schema/``; at start and before each validation (at most once an
hour) it compares that copy with the files on GitHub. If they differ, the new files are checked
(XML without DTD or entities, RelaxNG grammar, Schematron that compiles, the rule
"Variation needs a lem" still present), the collation schema is derived from them, and the set
is stored in the user's data folder. From then on that set is used. If GitHub cannot be reached
or the new files do not pass the checks, the last good set stays in use and the reason is shown.

The request goes from the local server to raw.githubusercontent.com and sends no data. It can
be switched off with ``pta-collate serve --no-schema-update`` or ``PTA_COLLATE_SCHEMA_UPDATE=0``.
"""

from __future__ import annotations

import hashlib
import json
import os
import sys
import threading
import time
import urllib.request

from lxml import etree, isoschematron

HERE = os.path.dirname(os.path.abspath(__file__))
BUNDLED = os.path.normpath(os.path.join(HERE, "..", "schema"))
BASE = "https://raw.githubusercontent.com/PatristicTextArchive/Schema/master/"
SOURCE = "https://github.com/PatristicTextArchive/Schema"
FILES = ("tei-pta.odd", "tei-pta.rng", "tei-pta.sch")
DERIVED = {"tei-pta.rng": "tei-pta_collation.rng", "tei-pta.sch": "tei-pta_collation.sch"}
ALL = FILES + tuple(DERIVED.values())
MAX_AGE = 3600            # seconds between two checks
RETRY = 300               # after a failed check (offline): try again after five minutes
MAX_BYTES = 30_000_000    # the RNG is about 1 MB; anything far larger is not the schema

# the collation schema: only "Variation needs a lem" becomes a warning (see schema/tei-pta_collation.odd)
OLD_RULE = 'test="@type=\'variants\' and not(child::tei:lem or child::tei:rdgGrp/tei:lem)">Variation needs a lem<'
NEW_RULE = 'role="warning" test="@type=\'variants\' and not(child::tei:lem or child::tei:rdgGrp/tei:lem)">Variation has no lem yet (collation file)<'

RNG_NS = "http://relaxng.org/ns/structure/1.0"
SCH_NS = "http://purl.oclc.org/dsdl/schematron"

_lock = threading.Lock()


def enabled() -> bool:
    return os.environ.get("PTA_COLLATE_SCHEMA_UPDATE", "1") != "0"


def user_dir() -> str:
    if os.environ.get("PTA_COLLATE_SCHEMA_DIR"):
        return os.environ["PTA_COLLATE_SCHEMA_DIR"]
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or os.path.expanduser("~\\AppData\\Local")
    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")
    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")
    return os.path.join(base, "pta-collate", "schema")


def _state_path() -> str:
    return os.path.join(user_dir(), "state.json")


def _state() -> dict:
    try:
        with open(_state_path(), encoding="utf-8") as fh:
            return json.load(fh)
    except (OSError, ValueError):
        return {}


def _save_state(st: dict):
    os.makedirs(user_dir(), exist_ok=True)
    tmp = _state_path() + ".tmp"
    with open(tmp, "w", encoding="utf-8") as fh:
        json.dump(st, fh, indent=1)
    os.replace(tmp, _state_path())


def _complete(d: str) -> bool:
    return all(os.path.isfile(os.path.join(d, n)) for n in ALL)


def active_dir() -> str:
    """Folder with the schema in use: the updated set if there is one, otherwise the copy shipped."""
    d = user_dir()
    return d if _state().get("installed") and _complete(d) else BUNDLED


def path(name: str) -> str:
    return os.path.join(active_dir(), name)


def derive(name: str, text: str) -> str:
    """Collation variant of tei-pta.rng / tei-pta.sch."""
    if OLD_RULE not in text:
        raise ValueError(f"Regel „Variation needs a lem“ in {name} nicht gefunden – das Schema wurde geändert")
    return text.replace(OLD_RULE, NEW_RULE)


def _fetch(url: str, timeout: float) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": "pta-collate"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        data = r.read(MAX_BYTES + 1)
    if len(data) > MAX_BYTES:
        raise ValueError(f"{url}: unerwartet groß")
    return data


def _parse(data: bytes, name: str):
    from .extract import safe_parser
    try:
        return etree.fromstring(data, safe_parser())
    except etree.XMLSyntaxError as e:
        raise ValueError(f"{name}: kein gültiges XML ({e})") from None


def check_files(files: dict[str, bytes]):
    """Raise ValueError unless the files look like a usable PTA schema."""
    for n in FILES:
        if n not in files or not files[n].strip():
            raise ValueError(f"{n} fehlt oder ist leer")
    for n in ("tei-pta.rng", "tei-pta_collation.rng"):
        root = _parse(files[n], n)
        if etree.QName(root).namespace != RNG_NS:
            raise ValueError(f"{n}: keine RelaxNG-Grammatik")
    _parse(files["tei-pta.odd"], "tei-pta.odd")
    for n in ("tei-pta.sch", "tei-pta_collation.sch"):
        root = _parse(files[n], n)
        if etree.QName(root).namespace != SCH_NS:
            raise ValueError(f"{n}: kein Schematron")
        try:
            isoschematron.Schematron(root)
        except Exception as e:  # noqa: BLE001 – lxml raises several kinds here
            raise ValueError(f"{n}: Schematron lässt sich nicht übersetzen ({e})") from None


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _read(d: str, n: str) -> bytes | None:
    try:
        with open(os.path.join(d, n), "rb") as fh:
            return fh.read()
    except OSError:
        return None


def install(files: dict[str, bytes]) -> bool:
    """Check and store a downloaded set (tei-pta.*). Returns True if it differs from the set in use."""
    files = dict(files)
    for src, dst in DERIVED.items():
        files[dst] = derive(src, files[src].decode("utf-8")).encode("utf-8")
    check_files(files)
    cur = active_dir()
    if all(_read(cur, n) == files[n] for n in ALL):
        return False
    d = user_dir()
    os.makedirs(d, exist_ok=True)
    for n in ALL:                       # write all files first, then switch (state "installed")
        tmp = os.path.join(d, n + ".tmp")
        with open(tmp, "wb") as fh:
            fh.write(files[n])
    for n in ALL:
        os.replace(os.path.join(d, n + ".tmp"), os.path.join(d, n))
    return True


def check(force: bool = False, timeout: float = 10) -> dict:
    """Compare with GitHub (at most once an hour, unless ``force``) and update if needed."""
    if not enabled() and not force:
        return status()
    with _lock:
        st = _state()
        if not force and time.time() < st.get("next", 0):
            return status()
        now = time.time()
        try:
            files = {n: _fetch(BASE + n, timeout) for n in FILES}
            changed = install(files)
            st.update(checked=now, next=now + MAX_AGE, error=None, installed=st.get("installed") or changed)
            if changed:
                st["updated"] = now
                st["installed"] = True
            st["sha"] = _sha(files["tei-pta.rng"])[:12]
        except Exception as e:  # noqa: BLE001 – offline, HTTP error, unusable files
            st.update(checked=now, next=now + RETRY, error=str(e) or e.__class__.__name__)
        try:
            _save_state(st)
        except OSError as e:
            st["error"] = f"Zustand nicht speicherbar: {e}"
    return status()


def check_in_background():
    if enabled():
        threading.Thread(target=check, name="schema-check", daemon=True).start()


def status() -> dict:
    st = _state()
    d = active_dir()
    return {
        "enabled": enabled(),
        "source": "github" if d != BUNDLED else "bundled",
        "dir": d,
        "checked": st.get("checked"),
        "updated": st.get("updated"),
        "error": st.get("error"),
        "url": SOURCE,
    }
