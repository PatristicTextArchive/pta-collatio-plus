"""Keeping the PTA schema current (no network: GitHub is replaced by a function)."""
import os

import pytest

from pta_collate import schema_store, validate

SHIPPED = {n: open(os.path.join(schema_store.BUNDLED, n), "rb").read() for n in schema_store.FILES}


@pytest.fixture
def store(tmp_path, monkeypatch):
    monkeypatch.setenv("PTA_COLLATE_SCHEMA_DIR", str(tmp_path / "schema"))
    monkeypatch.setenv("PTA_COLLATE_SCHEMA_UPDATE", "1")
    remote = dict(SHIPPED)

    def fake_fetch(url, timeout):
        name = url.rsplit("/", 1)[-1]
        if remote.get("offline"):
            raise OSError("keine Verbindung")
        return remote[name]
    monkeypatch.setattr(schema_store, "_fetch", fake_fetch)
    return remote


def test_unchanged_schema_keeps_shipped_copy(store):
    st = schema_store.check(force=True)
    assert st["source"] == "bundled" and not st["error"] and st["checked"]
    assert schema_store.active_dir() == schema_store.BUNDLED


def test_newer_schema_is_taken_over_and_used(store, tmp_path):
    marker = b"<!-- newer upstream version -->"
    store["tei-pta.sch"] = SHIPPED["tei-pta.sch"].replace(b"?>", b"?>" + marker, 1)
    st = schema_store.check(force=True)
    assert st["source"] == "github" and st["updated"] and not st["error"]
    d = schema_store.active_dir()
    assert d == str(tmp_path / "schema")
    for n in schema_store.ALL:                       # complete set, collation variant derived
        assert os.path.isfile(os.path.join(d, n))
    derived = open(os.path.join(d, "tei-pta_collation.sch"), "rb").read()
    assert marker in derived and b'role="warning"' in derived
    # validation now compiles the new Schematron
    xml = open(os.path.join(os.path.dirname(__file__), "data", "reference-edition-grc1.xml"), "rb").read()
    assert validate._sch("tei-pta_collation.sch") is not None
    assert "schematron" in validate.validate(xml, "collation")


def test_unusable_schema_is_refused(store):
    store["tei-pta.sch"] = SHIPPED["tei-pta.sch"].replace(b"Variation needs a lem", b"Something else")
    st = schema_store.check(force=True)
    assert "nicht gefunden" in st["error"] and st["source"] == "bundled"
    store["tei-pta.sch"] = SHIPPED["tei-pta.sch"] + b"<broken"
    assert "kein gültiges XML" in schema_store.check(force=True)["error"]
    store["tei-pta.sch"] = SHIPPED["tei-pta.sch"]
    store["tei-pta.rng"] = b'<?xml version="1.0"?><html xmlns="http://www.w3.org/1999/xhtml">' \
                           b'<p>Variation needs a lem</p></html>'
    assert schema_store.check(force=True)["source"] == "bundled"


def test_offline_keeps_last_good_version(store):
    store["tei-pta.odd"] = SHIPPED["tei-pta.odd"] + b"\n"
    assert schema_store.check(force=True)["source"] == "github"
    store["offline"] = True
    st = schema_store.check(force=True)
    assert st["source"] == "github" and "Verbindung" in st["error"]


def test_check_is_rate_limited_and_can_be_switched_off(store, monkeypatch):
    schema_store.check(force=True)
    store["offline"] = True
    assert not schema_store.check()["error"]       # within the hour: no new request
    monkeypatch.setenv("PTA_COLLATE_SCHEMA_UPDATE", "0")
    assert schema_store.check()["enabled"] is False
