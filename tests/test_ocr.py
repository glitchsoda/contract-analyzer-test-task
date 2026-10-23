import shutil

import pymupdf
import pytest

from app import config
from app.pdf import extract_text


@pytest.mark.skipif(not (shutil.which("tesseract") or config.TESSERACT_CMD), reason="нет tesseract")
def test_ocr():
    src = pymupdf.open()
    src.new_page().insert_textbox(pymupdf.Rect(50, 50, 550, 800),
                                  "CONTRACT No 15. The Customer shall pay 100000 RUB. " * 5,
                                  fontsize=14)
    pix = src[0].get_pixmap(dpi=200)
    scan = pymupdf.open()
    page = scan.new_page()
    page.insert_image(page.rect, pixmap=pix)

    res = extract_text(scan.tobytes())
    assert res.ocr_pages == 1
    assert "100000" in res.text.replace(" ", "")
