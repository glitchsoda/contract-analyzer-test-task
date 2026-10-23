import time

from app import cache, config, pii
from app.llm import LLMError, analyze_contract
from app.log import log
from app.pdf import PDFError, extract_text
from app.schemas import AnalysisResponse, Meta
from app.verify import verify

MAX_SIZE = config.MAX_FILE_MB * 1024 * 1024


class AnalyzeError(Exception):
    def __init__(self, status, message):
        super().__init__(message)
        self.status = status
        self.message = message


def check_pdf(data):
    if len(data) > MAX_SIZE:
        raise AnalyzeError(413, "Файл слишком большой")
    if b"%PDF-" not in data[:1024]:
        raise AnalyzeError(415, "Ожидается PDF")


def analyze(data: bytes) -> AnalysisResponse:
    start = time.perf_counter()
    check_pdf(data)
    sha = cache.sha256(data)

    if cached := cache.get(sha):
        cached.meta.cached = True
        log(event="analyze", sha=sha, cached=True, status=200)
        return cached

    try:
        pdf = extract_text(data)
    except PDFError as e:
        log(event="analyze", sha=sha, status=422, error="pdf")
        raise AnalyzeError(422, str(e))

    text, mapping = pdf.text, {}
    if config.PII_MASKING:
        text, mapping = pii.mask(text)

    try:
        result, chunks = analyze_contract(text)
    except LLMError as e:
        log(event="analyze", sha=sha, status=502, error=str(e))
        raise AnalyzeError(502, str(e))

    threshold = config.QUOTE_THRESHOLD_OCR if pdf.ocr_pages else config.QUOTE_THRESHOLD
    meta = Meta(sha256=sha, pages=pdf.pages, chunks=chunks, model=config.LLM_MODEL,
                ocr_pages=pdf.ocr_pages, pii_masked=bool(mapping),
                duration_ms=int((time.perf_counter() - start) * 1000))

    resp = verify(result, text, meta, threshold)   # модель видела маскированный текст
    if mapping:
        resp = pii.unmask(resp, mapping)

    cache.put(sha, resp)
    log(event="analyze", sha=sha, pages=pdf.pages, ocr_pages=pdf.ocr_pages, chars=len(text),
        chunks=chunks, cached=False, duration_ms=meta.duration_ms, status=200,
        risks=len(resp.risks), unverified=sum(not r.verified for r in resp.risks))
    return resp
