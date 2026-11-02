"""Validate TEI against the PTA schema (RelaxNG + Schematron).

RelaxNG is checked with Jing (shipped by the ``jingtrang`` package, needs Java),
because libxml2 needs minutes to compile the large TEI RelaxNG schema. Without
Java, lxml is used as a (slow) fallback. Schematron is checked with lxml.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import tempfile
from functools import lru_cache

from lxml import etree, isoschematron

from . import schema_store

VARIANTS = {
    "collation": ("tei-pta_collation.rng", "tei-pta_collation.sch"),
    "full": ("tei-pta.rng", "tei-pta.sch"),
}


def _jing_jar():
    try:
        import jingtrang
        jar = os.path.join(os.path.dirname(jingtrang.__file__), "jing.jar")
        return jar if os.path.exists(jar) else None
    except ImportError:
        return None


def _relaxng_jing(path: str, rng: str):
    jar = _jing_jar()
    if not jar or not shutil.which("java"):
        return None
    proc = subprocess.run(["java", "-jar", jar, rng, path], capture_output=True, text=True, encoding="utf-8")
    errors = []
    for line in (proc.stdout + proc.stderr).splitlines():
        if "JAVA_TOOL_OPTIONS" in line or not line.strip():
            continue
        m = re.match(r".*?:(\d+):(\d+):\s*(?:error|fatal):\s*(.*)", line)
        errors.append(f"Zeile {m.group(1)}: {m.group(3)}" if m else line)
    return proc.returncode == 0 and not errors, errors


# compiled schemas, keyed by path and modification time (a schema update replaces the files)
@lru_cache(maxsize=4)
def _rng_lxml_cached(path, mtime):
    return etree.RelaxNG(etree.parse(path))


@lru_cache(maxsize=4)
def _sch_cached(path, mtime):
    return isoschematron.Schematron(etree.parse(path), store_report=True)


def _rng_lxml(name):
    p = schema_store.path(name)
    return _rng_lxml_cached(p, os.path.getmtime(p))


def _sch(name):
    p = schema_store.path(name)
    return _sch_cached(p, os.path.getmtime(p))


def _short(loc: str | None) -> str:
    """Turn the verbose SVRL location into a readable path like /TEI/text/body/div/div[1]/p/app[3]."""
    if not loc:
        return ""
    return re.sub(r"\*\[local-name\(\)='([^']+)' and namespace-uri\(\)='[^']*'\]", r"\1", loc)


def validate(xml: bytes | str, variant: str = "collation") -> dict:
    rng_name, sch_name = VARIANTS[variant]
    if isinstance(xml, str):
        xml = xml.encode("utf-8")
    from .extract import safe_parser
    doc = etree.fromstring(xml, safe_parser()).getroottree()
    with tempfile.NamedTemporaryFile("wb", suffix=".xml", delete=False) as fh:
        fh.write(xml)
        path = fh.name
    try:
        res = _relaxng_jing(path, schema_store.path(rng_name))
    finally:
        os.unlink(path)
    engine = "jing"
    if res is None:
        engine = "lxml"
        rng = _rng_lxml(rng_name)
        ok = rng.validate(doc)
        res = ok, [f"Zeile {e.line}: {e.message}" for e in rng.error_log]
    rng_ok, rng_errors = res
    sch = _sch(sch_name)
    sch.validate(doc)
    report = sch.validation_report
    ns = {"svrl": "http://purl.oclc.org/dsdl/svrl"}
    errors, warnings = [], []
    counts: dict[str, int] = {}
    for el in report.xpath("//svrl:failed-assert|//svrl:successful-report", namespaces=ns):
        msg = " ".join("".join(el.itertext()).split())
        if el.get("role") == "warning":
            warnings.append(f"{_short(el.get('location'))}: {msg}")
        else:
            counts.setdefault(msg, 0)
            if counts[msg] == 0:
                errors.append(f"{_short(el.get('location'))}: {msg}")
            counts[msg] += 1
    errors = [e + (f" ({counts[e.split(': ', 1)[1]]}×)" if counts.get(e.split(': ', 1)[1], 1) > 1 else "")
              for e in errors]
    return {
        "variant": variant,
        "valid": rng_ok and not errors,
        "relaxng": {"valid": rng_ok, "errors": rng_errors[:50], "engine": engine},
        "schematron": {"errors": errors[:50], "warnings": len(warnings), "warning_examples": warnings[:3]},
    }
