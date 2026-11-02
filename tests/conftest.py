import pytest


@pytest.fixture(autouse=True)
def _no_schema_download(monkeypatch, tmp_path):
    """Tests never contact GitHub and never touch the user's schema folder."""
    monkeypatch.setenv("PTA_COLLATE_SCHEMA_UPDATE", "0")
    monkeypatch.setenv("PTA_COLLATE_SCHEMA_DIR", str(tmp_path / "user-schema"))
