from app import cache, config
from app.schemas import AnalysisResponse, Meta

RESP = AnalysisResponse(parties=[], subject=None, amount=None, risks=[], summary="s",
                        meta=Meta(sha256="a" * 64, pages=1, chunks=1, model="m"))


def test_roundtrip():
    cache.put("abc", RESP)
    assert cache.get("abc") == RESP


def test_settings_change(monkeypatch):
    cache.put("abc", RESP)
    monkeypatch.setattr(config, "DROP_UNVERIFIED", not config.DROP_UNVERIFIED)
    assert cache.get("abc") is None


def test_corrupt_entry():
    cache.put("abc", RESP)
    p = cache.path_for("abc")
    p.write_text("{not json", "utf-8")
    assert cache.get("abc") is None and not p.exists()


def test_write_failure(monkeypatch, tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    monkeypatch.setattr(cache, "cache_dir", blocker / "sub")
    cache.put("abc", RESP)
    assert cache.get("abc") is None
