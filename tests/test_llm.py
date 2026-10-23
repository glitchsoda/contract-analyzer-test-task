from app import config, llm
from app.schemas import AnalysisResult, ChunkExtraction, Party

EMPTY = ChunkExtraction(parties=[], subject_candidates=[], amounts=[], risks=[], key_points=[])


def fake_ask(log):
    def call(schema, system, user):
        log.append((schema.__name__, system[:40], len(user)))
        if schema is AnalysisResult:
            return AnalysisResult(parties=[Party(name="A", role=None)], subject=None,
                                  amount=None, risks=[], summary="s")
        return EMPTY.model_copy(update={"key_points": ["x" * 200]})
    return call


def test_single_pass(monkeypatch):
    log = []
    monkeypatch.setattr(llm, "ask", fake_ask(log))
    _, n = llm.analyze_contract("короткий договор")
    assert n == 1 and [x[0] for x in log] == ["AnalysisResult"]


def test_map_reduce(monkeypatch):
    log = []
    monkeypatch.setattr(llm, "ask", fake_ask(log))
    monkeypatch.setattr(config, "SINGLE_PASS_CHARS", 2000)
    monkeypatch.setattr(config, "CHUNK_CHARS", 1000)
    text = "\n".join(f"{i}. РАЗДЕЛ {i}\n" + "слово " * 100 for i in range(1, 11))
    _, n = llm.analyze_contract(text)
    assert n > 1
    kinds = [x[0] for x in log]
    assert kinds.count("ChunkExtraction") >= n and kinds[-1] == "AnalysisResult"


def test_hierarchical_reduce(monkeypatch):
    log = []
    monkeypatch.setattr(llm, "ask", fake_ask(log))
    monkeypatch.setattr(config, "SINGLE_PASS_CHARS", 1000)
    monkeypatch.setattr(config, "REDUCE_GROUP", 3)
    partials = [EMPTY.model_copy(update={"key_points": ["x" * 200]}) for _ in range(10)]
    llm.reduce_parts(partials)
    merges = [x for x in log if x[0] == "ChunkExtraction"]
    assert len(merges) == 4
    assert log[-1][0] == "AnalysisResult" and log[-1][2] <= 1000


def test_map_prompt():
    assert "часть 2 из 5" in llm.MAP_PROMPT.format(i=2, n=5)


def test_short_summary():
    text = "Первое. Второе! Первое. Третье? Четвёртое."
    assert llm.short_summary(text) == "Первое. Второе! Третье?"
