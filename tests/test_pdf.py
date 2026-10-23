import pymupdf
import pytest

from app import config
from app.pdf import PDFError, extract_text
from tests.conftest import make_pdf

PAGE = "1. SUBJECT. The Contractor shall deliver software. " * 5


def test_text_pdf():
    res = extract_text(make_pdf(PAGE, PAGE))
    assert res.pages == 2 and res.ocr_pages == 0
    assert "--- Страница 2 ---" in res.text


def test_blank_page(monkeypatch):
    monkeypatch.setattr(config, "OCR_ENABLED", False)
    res = extract_text(make_pdf(PAGE, PAGE, ""))
    assert res.pages == 3


def test_scan_without_ocr(monkeypatch):
    monkeypatch.setattr(config, "OCR_ENABLED", False)
    with pytest.raises(PDFError, match="скан"):
        extract_text(make_pdf("", "", PAGE))


def test_owner_password():
    data = make_pdf(PAGE, encryption=pymupdf.PDF_ENCRYPT_AES_256,
                    owner_pw="owner", user_pw="", permissions=0)
    assert "Contractor" in extract_text(data).text


def test_user_password():
    data = make_pdf(PAGE, encryption=pymupdf.PDF_ENCRYPT_AES_256,
                    owner_pw="owner", user_pw="user")
    with pytest.raises(PDFError, match="паролем"):
        extract_text(data)


def test_broken_pdf():
    with pytest.raises(PDFError):
        extract_text(b"%PDF-1.4 garbage")


def test_spaces():
    doc = pymupdf.open()
    doc.new_page().insert_textbox(pymupdf.Rect(50, 50, 550, 800),
                                  "1. SUBJECT.\u00a0\u00a0\u00a0Software  delivery. " * 5)
    text = extract_text(doc.tobytes()).text
    assert "\u00a0" not in text and "  " not in text
    assert "SUBJECT. Software delivery" in text


def test_soft_hyphen():
    from app.pdf import clean
    assert clean("Испол\u00ad\nнитель, договор 2026\u00ad118/П") == "Исполнитель, договор 2026-118/П"
