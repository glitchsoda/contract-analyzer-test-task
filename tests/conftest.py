import os

import pymupdf
import pytest

os.environ.update(LLM_BASE_URL="http://llm.invalid/v1", LLM_API_KEY="test",
                  LLM_MODEL="test-model", LLM_FALLBACK_MODELS="", PII_MASKING="false")


def make_pdf(*pages, **save_kw) -> bytes:
    doc = pymupdf.open()
    for text in pages:
        page = doc.new_page()
        page.insert_textbox(pymupdf.Rect(50, 50, 550, 800), text, fontsize=11)
    return doc.tobytes(**save_kw)


@pytest.fixture
def sample_pdf() -> bytes:
    return make_pdf("1. SUBJECT. The Contractor shall deliver software. " * 5)


@pytest.fixture(autouse=True)
def isolated_cache(monkeypatch, tmp_path):
    from app import cache
    monkeypatch.setattr(cache, "cache_dir", tmp_path / "cache")
