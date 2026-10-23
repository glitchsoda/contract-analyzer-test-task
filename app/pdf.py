import io
import os
import re
from dataclasses import dataclass

import pymupdf

from app import config

MIN_PAGE_CHARS = 50
MIN_TEXT_CHARS = 100

SPACES = re.compile(r"[ \t\xa0\u2007\u2009\u202f]+")
HYPHEN_WRAP = re.compile(r"\xad[ \t]*\n[ \t]*")


class PDFError(Exception):
    pass


@dataclass
class PDFText:
    text: str
    pages: int
    ocr_pages: int


def clean(text) -> str:
    text = HYPHEN_WRAP.sub("", text).replace("\xad", "-")   # мягкий перенос бывает и дефисом
    return SPACES.sub(" ", text).strip()


def ocr(page) -> str:
    import pytesseract
    from PIL import Image

    if config.TESSERACT_CMD:
        pytesseract.pytesseract.tesseract_cmd = config.TESSERACT_CMD
    if config.TESSDATA_DIR:
        os.environ["TESSDATA_PREFIX"] = config.TESSDATA_DIR
    pix = page.get_pixmap(dpi=config.OCR_DPI)
    img = Image.open(io.BytesIO(pix.tobytes("png")))
    return pytesseract.image_to_string(img, lang=config.OCR_LANG, timeout=120)


def extract_text(data: bytes) -> PDFText:
    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
    except Exception as e:
        raise PDFError(f"Не удалось открыть PDF: {type(e).__name__}")

    parts, ocr_pages, empty, total_chars = [], 0, 0, 0
    with doc:
        if doc.needs_pass:
            raise PDFError("PDF защищён паролем")
        pages = doc.page_count
        if pages == 0:
            raise PDFError("Пустой PDF")

        for i, page in enumerate(doc, start=1):
            text = clean(page.get_text("text"))
            if len(text) < MIN_PAGE_CHARS:
                if not config.OCR_ENABLED:
                    empty += 1
                elif ocr_pages >= config.OCR_MAX_PAGES:
                    raise PDFError(f"Слишком много страниц для OCR (>{config.OCR_MAX_PAGES})")
                else:
                    try:
                        text = clean(ocr(page))
                    except Exception as e:
                        raise PDFError(f"OCR не удался: {type(e).__name__}")
                    ocr_pages += 1
            total_chars += len(text)
            parts.append(f"--- Страница {i} ---\n{text}")

    if not config.OCR_ENABLED and empty / pages > 0.5:
        raise PDFError("Похоже на скан, а OCR выключен")
    if total_chars < MIN_TEXT_CHARS:
        raise PDFError("Не удалось извлечь текст")
    return PDFText("\n\n".join(parts), pages, ocr_pages)
