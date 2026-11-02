"""Command line interface.

    pta-collate serve [PROJEKT] [--port 8765] [--no-browser]
    pta-collate run PROJEKT [--export tei,html,csv,nexus,json] [--validate]
    pta-collate init PROJEKT DATEI_ODER_ORDNER… [--engine builtin|collatex]
"""

from __future__ import annotations

import argparse
import json
import os
import sys
import threading
import webbrowser

from . import collation, export_other, export_tei, extract
from . import project as P
from .units import build

EXPORTS = {
    "tei": (".xml", lambda m, p: export_tei.export_tei(m, p)),
    "html": ("-synopse.html", lambda m, p: export_other.export_synopsis_html(m, p)),
    "csv": (".csv", lambda m, p: export_other.export_csv(m)),
    "nexus": (".nex", lambda m, p: export_other.export_nexus(m)),
    "json": ("-collatex.json", lambda m, p: export_other.export_collatex_json(m)),
}


def cmd_serve(args):
    import uvicorn
    from . import server
    if args.project:
        path = os.path.abspath(args.project)
        if os.path.exists(path):
            server.S.proj = P.load(path)
            server.S.load_result()
        else:
            server.S.proj["_path"] = path
    from . import schema_store
    if args.no_schema_update:
        os.environ["PTA_COLLATE_SCHEMA_UPDATE"] = "0"
    schema_store.check_in_background()
    url = f"http://127.0.0.1:{args.port}/"
    print(f"PTA Collatio+ läuft unter {url}  (Beenden mit Strg+C)")
    if not args.no_browser:
        threading.Timer(1.0, lambda: webbrowser.open(url)).start()
    uvicorn.run(server.app, host="127.0.0.1", port=args.port, log_level="warning")


def cmd_init(args):
    proj = P.new_project()
    proj["aligner"]["engine"] = args.engine
    for item in args.files:
        paths = [os.path.join(item, f) for f in sorted(os.listdir(item))] if os.path.isdir(item) else [item]
        for p in paths:
            if not p.endswith(".xml") or "__cts__" in p:
                continue
            tree = extract.parse(p)
            if tree.getroot().find(".//tei:sourceDesc/tei:msDesc", extract.NS) is None:
                continue
            info = extract.read_info(p)
            proj["witnesses"].append({"file": os.path.abspath(p), "id": info.id, "siglum": info.id,
                                      "include": True, "layers": "both"})
    if proj["witnesses"]:
        proj["structure_witness"] = proj["witnesses"][0]["id"]
    path = P.save(proj, args.project)
    print(f"{len(proj['witnesses'])} Zeugen eingetragen: {path}")


def cmd_run(args):
    proj = P.load(args.project)
    rp = P.result_path(proj)
    if args.reuse and os.path.exists(rp):
        with open(rp, encoding="utf-8") as fh:
            result = json.load(fh)
    else:
        result = collation.run(proj, progress=lambda m: print("  " + m, file=sys.stderr))
        with open(rp, "w", encoding="utf-8") as fh:
            json.dump(result, fh, ensure_ascii=False)
        proj.setdefault("runs", []).append({"when": result["created"], "aligner": proj["aligner"].get("engine"),
                                            "seconds": result["seconds"], "segmentation": result["segmentation"]})
        P.save(proj)
    model = build(result, proj)
    st = model.stats()
    print(f"{st['variant_units']} Variationsstellen ({st['orthographic_only']} rein orthographisch), "
          f"{st['tokens']} Token, {result['seconds']} s")
    bad = [s for s in model.status if not s["ok"]]
    if bad:
        print(f"Achtung: {len(bad)} Korrekturen nicht angewendet: Nr. {', '.join(str(s['edit'] + 1) for s in bad)}")
    folder = os.path.dirname(os.path.abspath(args.project))
    urn = export_tei.edition_urn(model, proj)
    for fmt in [f for f in (args.export or "").split(",") if f]:
        suffix, fn = EXPORTS[fmt]
        data = fn(model, proj)
        target, note = export_tei.export_path(folder, urn, suffix)
        with open(target, "wb") as fh:
            fh.write(data)
        print("geschrieben:", target + (f"  ({note})" if note else ""))
        if fmt == "tei" and args.validate:
            from .validate import validate
            from . import schema_store
            if args.no_schema_update:
                os.environ["PTA_COLLATE_SCHEMA_UPDATE"] = "0"
            sst = schema_store.check()
            print("  Schema:", "aktualisiert aus GitHub" if sst["source"] == "github" else "mitgeliefert",
                  f"(Prüfung nicht möglich: {sst['error']})" if sst.get("error") else "")
            for v in ("collation", "full"):
                r = validate(data, v)
                n = len(r["relaxng"]["errors"]) + len(r["schematron"]["errors"])
                print(f"  {v}: {'gültig' if r['valid'] else f'{n} Fehler'}"
                      + (f" ({r['schematron']['warnings']} Stellen ohne Lemma)" if r['schematron']['warnings'] else ""))
                for e in (r["relaxng"]["errors"] + r["schematron"]["errors"])[:5]:
                    print("    " + e[-200:])


def main(argv=None):
    ap = argparse.ArgumentParser(prog="pta-collate", description="Kollation von PTA-Transkriptionen")
    sub = ap.add_subparsers(dest="cmd")
    s = sub.add_parser("serve", help="Web-Oberfläche starten")
    s.add_argument("project", nargs="?")
    s.add_argument("--port", type=int, default=8765)
    s.add_argument("--no-browser", action="store_true")
    s.add_argument("--no-schema-update", action="store_true", help="nicht auf GitHub nach einer neuen Fassung des PTA-Schemas sehen")
    s.set_defaults(fn=cmd_serve)
    i = sub.add_parser("init", help="Projektdatei aus Transkriptionen anlegen")
    i.add_argument("project")
    i.add_argument("files", nargs="+")
    i.add_argument("--engine", default="builtin", choices=["builtin", "collatex"])
    i.set_defaults(fn=cmd_init)
    r = sub.add_parser("run", help="Kollation ohne Oberfläche ausführen und exportieren")
    r.add_argument("project")
    r.add_argument("--export", default="tei,html")
    r.add_argument("--validate", action="store_true")
    r.add_argument("--no-schema-update", action="store_true", help="nicht auf GitHub nach einer neuen Fassung des PTA-Schemas sehen")
    r.add_argument("--reuse", action="store_true", help="vorhandenes Alignment wiederverwenden")
    r.set_defaults(fn=cmd_run)
    args = ap.parse_args(argv)
    if not getattr(args, "fn", None):
        args = ap.parse_args(["serve"] + (argv or sys.argv[1:]))
    args.fn(args)


if __name__ == "__main__":
    main()
