from fastapi.testclient import TestClient

from app import config, main, pipeline
from app.schemas import AnalysisResult, Party, Risk

client = TestClient(main.app)

FAKE = AnalysisResult(
    parties=[Party(name="ACME", role="Customer")],
    subject="Software delivery", amount=None,
    risks=[Risk(description="x", severity="low", clause="1",
                quote="The Contractor shall deliver software"),
           Risk(description="y", severity="high", clause="2",
                quote="The Customer waives all claims forever and ever")],
    summary="ok",
)


def test_analyze_ok(sample_pdf, monkeypatch):
    calls = []
    monkeypatch.setattr(pipeline, "analyze_contract", lambda text: calls.append(1) or (FAKE, 1))
    files = {"file": ("c.pdf", sample_pdf, "application/pdf")}

    r = client.post("/analyze", files=files)
    assert r.status_code == 200
    risks = r.json()["risks"]
    assert [x["verified"] for x in risks] == [True, False]
    assert r.json()["meta"]["cached"] is False

    r2 = client.post("/analyze", files=files)
    assert r2.json()["meta"]["cached"] is True
    assert len(calls) == 1


def test_octet_stream(sample_pdf, monkeypatch):
    monkeypatch.setattr(pipeline, "analyze_contract", lambda text: (FAKE, 1))
    r = client.post("/analyze", files={"file": ("c.pdf", sample_pdf, "application/octet-stream")})
    assert r.status_code == 200


def test_not_pdf():
    r = client.post("/analyze", files={"file": ("a.txt", b"hello", "text/plain")})
    assert r.status_code == 415


def test_too_large(monkeypatch):
    monkeypatch.setattr(pipeline, "MAX_SIZE", 100)
    r = client.post("/analyze", files={"file": ("c.pdf", b"%PDF-" + b"0" * 200, "application/pdf")})
    assert r.status_code == 413


def test_broken_pdf():
    r = client.post("/analyze", files={"file": ("c.pdf", b"%PDF-1.4 broken", "application/pdf")})
    assert r.status_code == 422


def test_llm_error(sample_pdf, monkeypatch):
    def boom(text):
        raise pipeline.LLMError("Ошибка LLM: APIConnectionError")
    monkeypatch.setattr(pipeline, "analyze_contract", boom)
    r = client.post("/analyze", files={"file": ("c.pdf", sample_pdf, "application/pdf")})
    assert r.status_code == 502


def test_pii_masking(monkeypatch):
    from tests.conftest import make_pdf
    pdf = make_pdf("1. PARTIES. Contact the Customer at ivan.petrov@mail.ru for all notices. " * 3)
    seen = {}

    def fake(text):
        seen["text"] = text
        return AnalysisResult(
            parties=[Party(name="[EMAIL_1]", role="contact")], subject=None, amount=None,
            risks=[Risk(description="d", severity="low", clause=None,
                        quote="Contact the Customer at [EMAIL_1] for all notices")],
            summary="Write to EMAIL_1"), 1

    monkeypatch.setattr(config, "PII_MASKING", True)
    monkeypatch.setattr(pipeline, "analyze_contract", fake)
    r = client.post("/analyze", files={"file": ("c.pdf", pdf, "application/pdf")}).json()
    assert "ivan.petrov@mail.ru" not in seen["text"]
    assert r["parties"][0]["name"] == "ivan.petrov@mail.ru"
    assert r["summary"] == "Write to ivan.petrov@mail.ru"
    assert r["risks"][0]["verified"] is True
    assert r["meta"]["pii_masked"] is True


def test_index_page():
    r = client.get("/")
    assert r.status_code == 200
    assert "Анализ договоров" in r.text


def test_health():
    assert client.get("/health").json() == {"status": "ok", "async": False}


def test_jobs_disabled():
    r = client.post("/jobs", files={"file": ("c.pdf", b"%PDF-1.4", "application/pdf")})
    assert r.status_code == 503
