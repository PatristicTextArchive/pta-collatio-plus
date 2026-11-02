import glob
import os

from fastapi.testclient import TestClient

from pta_collate import server

DATA = os.path.join(os.path.dirname(__file__), "data")


def test_full_workflow(tmp_path):
    c = TestClient(server.app, base_url="http://127.0.0.1:8765")
    c.post("/api/project/new", json={})
    st = c.post("/api/witnesses/add", json={"paths": [DATA]}).json()
    assert st["added"] == ["La", "Pg", "Ps", "Vi"]                # reference edition skipped
    assert any("msDesc" in s["reason"] for s in st["skipped"])
    # a new project file goes next to the transcriptions (the repository of the edition)
    assert c.get("/api/state").json()["suggested_path"] == os.path.join(os.path.abspath(DATA), "pta0013.pta003.kollation.pta.json")
    pv = c.post("/api/preview", json={"id": "La"}).json()
    assert set(pv["layers"]) == {"La_ac", "La_pc"}
    assert isinstance(c.post("/api/check").json()["breaks"], list)
    model = c.post("/api/collate").json()
    assert model["stats"]["variant_units"] > 80
    u = next(u for u in model["units"] if u["variant"])
    model = c.post("/api/edit", json={"op": "lem", "unit": u["key"], "reading": u["readings"][0]["c"]}).json()
    assert model["stats"]["with_lem"] == 1
    model = c.post("/api/undo").json()
    assert model["stats"]["with_lem"] == 0
    # taking over the recognised type/cause: kept when the lemma changes afterwards
    ou = next(x for x in model["units"] if any(r.get("cause") == "orthographic" for r in x["readings"]))
    orth = next(r for r in ou["readings"] if r.get("cause") == "orthographic")
    other = next(r for r in ou["readings"] if r is not orth)
    model = c.post("/api/edit", json={"op": "confirm", "unit": ou["key"], "readings": [
        {"reading": r["c"], "wits": r["wits"], "type": r.get("type"), "cause": r.get("cause")} for r in ou["readings"]]}).json()
    assert model["edit_status"][-1]["ok"]
    model = c.post("/api/edit", json={"op": "lem", "unit": ou["key"], "reading": orth["c"]}).json()
    d = c.get("/api/unit", params={"key": ou["key"]}).json()
    assert next(r for r in d["readings"] if r["c"] == orth["c"]).get("cause") == "orthographic"
    assert all(r.get("override") for r in d["readings"] if r["c"] in (orth["c"], other["c"]))
    c.post("/api/undo"); model = c.post("/api/undo").json()
    assert not model["edits"]
    # conjecture as lemma in one batch, undone together
    model = c.post("/api/edit", json={"ops": [
        {"op": "conj", "unit": u["key"], "id": "k1", "kind": "conjecture", "text": "ἄλλο"},
        {"op": "lem", "unit": u["key"], "editorial": "k1"}]}).json()
    assert model["stats"]["editorial"] == 1 and model["stats"]["with_lem"] == 1
    detail = c.get("/api/unit", params={"key": u["key"]}).json()
    assert any(r.get("editorial") for r in detail["readings"]) and "presence" in detail
    model = c.post("/api/undo").json()
    assert model["stats"]["editorial"] == 0 and not model["edits"]
    r = c.get("/api/export/tei")
    assert r.status_code == 200 and b"<TEI" in r.content
    assert b'<app type="variants" n=' not in r.content          # the real export has no unit keys
    keyed = c.get("/api/export/tei", params={"keys": 1}).content   # for the variance overview
    assert ('<app type="variants" n="' + model["units"][0]["key"]).encode() in keyed or b'<app type="variants" n="' in keyed
    v = c.post("/api/validate", json={"full": False}).json()
    assert v["collation"]["valid"]
    path = tmp_path / "proj.pta.json"
    st = c.post("/api/project/save", json={"path": str(path)}).json()
    assert os.path.exists(path) and os.path.exists(str(path).replace(".pta.json", ".alignment.json"))
    st = c.post("/api/project/open", json={"path": str(path)}).json()
    assert st["has_result"]


def test_about_page_and_footer():
    c = TestClient(server.app, base_url="http://127.0.0.1:8765")
    page = c.get("/").text
    assert 'id="view-about"' in page
    assert page.index("/static/theme.js") < page.index("</head>")      # colour scheme set before drawing
    assert all(f'data-theme-set="{t}"' in page for t in ("auto", "light", "dark"))
    for needle in ("https://orcid.org/0000-0001-5382-6322", "https://pta.bbaw.de", "https://bibelexegese.bbaw.de"):
        assert page.count(needle) >= 2, needle  # footer and About page
    from pta_collate import __version__
    assert c.get("/api/state").json()["version"] == __version__


def test_security_guard():
    """DNS rebinding, cross-site requests and the Content-Security-Policy."""
    ok = TestClient(server.app, base_url="http://127.0.0.1:8765")
    r = ok.get("/")
    assert r.status_code == 200
    assert "script-src 'self'" in r.headers["content-security-policy"]
    assert "unsafe-inline" not in r.headers["content-security-policy"].split("script-src")[1].split(";")[0]
    assert r.headers["x-content-type-options"] == "nosniff"
    assert ok.get("/static/i18n.js").headers["cache-control"] == "no-cache"   # no outdated scripts after an update
    # no external hosts (fonts are local): neither in the policies nor in the pages
    for path in ("/", "/static/varianz/index.html"):
        r = ok.get(path)
        assert "https:" not in r.headers["content-security-policy"]
        assert "googleapis" not in r.text and "gstatic" not in r.text
    assert "googleapis" not in ok.get("/static/style.css").text
    fonts = ok.get("/static/fonts/fonts.css")
    assert fonts.status_code == 200 and "Gentium Plus" in fonts.text
    first = __import__("re").search(r"url\(([^)]+)\)", fonts.text).group(1)
    assert ok.get("/static/fonts/" + first).status_code == 200
    assert "sha256-" in ok.get("/static/varianz/index.html").headers["content-security-policy"]
    # foreign host name (DNS rebinding)
    assert TestClient(server.app, base_url="http://evil.example").get("/api/state").status_code == 403
    # request from another site
    assert ok.get("/api/state", headers={"Sec-Fetch-Site": "cross-site"}).status_code == 403
    assert ok.post("/api/project/new", json={}, headers={"Origin": "http://evil.example"}).status_code == 403
    assert ok.post("/api/project/new", json={}, headers={"Origin": "http://127.0.0.1:9999"}).status_code == 403
    assert ok.post("/api/project/new", json={}, headers={"Origin": "http://127.0.0.1:8765",
                                                         "Sec-Fetch-Site": "same-origin"}).status_code == 200
    # saving changes files: only by POST, not by a link or an image
    assert ok.get("/api/export/tei/save").status_code in (404, 405)


def test_xml_without_entity_expansion(tmp_path):
    from pta_collate import extract
    secret = tmp_path / "secret.txt"
    secret.write_text("GEHEIM")
    f = tmp_path / "x.xml"
    f.write_text(f'<?xml version="1.0"?><!DOCTYPE TEI [<!ENTITY x SYSTEM "file://{secret}">]>'
                 '<TEI xmlns="http://www.tei-c.org/ns/1.0"><text><body><p>&x;</p></body></text></TEI>')
    tree = extract.parse(str(f))
    from lxml import etree
    assert b"GEHEIM" not in etree.tostring(tree)
