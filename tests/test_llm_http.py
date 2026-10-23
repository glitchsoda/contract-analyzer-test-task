import json

import httpx
import pytest
from openai import OpenAI

from app import llm
from app.schemas import AnalysisResult

ANSWER = {"parties": [{"name": "ООО «Ромашка»", "role": "Исполнитель"}],
          "subject": "услуги", "amount": None, "risks": [], "summary": "ок"}


def fake_client(handler) -> OpenAI:
    return OpenAI(base_url="http://fake/v1", api_key="x", max_retries=0,
                  http_client=httpx.Client(transport=httpx.MockTransport(handler)))


def reply(content) -> httpx.Response:
    return httpx.Response(200, json={
        "id": "x", "object": "chat.completion", "created": 0, "model": "m",
        "choices": [{"index": 0, "finish_reason": "stop",
                     "message": {"role": "assistant", "content": content}}]})


def test_strict_schema(monkeypatch):
    seen = {}

    def handler(req):
        seen["body"] = json.loads(req.content)
        return reply(json.dumps(ANSWER, ensure_ascii=False))

    monkeypatch.setattr(llm, "client", fake_client(handler))
    res = llm.ask(AnalysisResult, "sys", "user")
    assert res.parties[0].name == "ООО «Ромашка»"
    rf = seen["body"]["response_format"]
    assert rf["type"] == "json_schema" and rf["json_schema"]["strict"] is True
    assert seen["body"]["temperature"] == 0


def test_invalid_json(monkeypatch):
    monkeypatch.setattr(llm, "client", fake_client(lambda req: reply('{"parties": "oops"}')))
    with pytest.raises(llm.LLMError):
        llm.ask(AnalysisResult, "sys", "user")


def test_error_text_hidden(monkeypatch):
    secret = "фрагмент договора: Заказчик уплачивает пеню"
    monkeypatch.setattr(llm, "client",
                        fake_client(lambda req: httpx.Response(400, json={"error": {"message": secret}})))
    with pytest.raises(llm.LLMError) as e:
        llm.ask(AnalysisResult, "sys", "user")
    assert "пеню" not in str(e.value)


def reply_usage(content, prompt_tokens) -> httpx.Response:
    r = reply(content)
    body = json.loads(r.content)
    body["usage"] = {"prompt_tokens": prompt_tokens, "completion_tokens": 10,
                     "total_tokens": prompt_tokens + 10}
    return httpx.Response(200, json=body)


def test_context_cut(monkeypatch):
    answer = json.dumps(ANSWER, ensure_ascii=False)
    monkeypatch.setattr(llm, "client", fake_client(lambda req: reply_usage(answer, 2050)))
    with pytest.raises(llm.LLMError, match="обрезан"):
        llm.ask(AnalysisResult, "sys", "договор " * 2500)


def test_context_ok(monkeypatch):
    answer = json.dumps(ANSWER, ensure_ascii=False)
    monkeypatch.setattr(llm, "client", fake_client(lambda req: reply_usage(answer, 6000)))
    assert llm.ask(AnalysisResult, "sys", "договор " * 2500).summary == "ок"


def test_max_tokens_hit(monkeypatch):
    def handler(req):
        r = reply('{"parties": [], "subject": null, "amount": null, "risks": [], "summary": "по кругу')
        body = json.loads(r.content)
        body["choices"][0]["finish_reason"] = "length"
        return httpx.Response(200, json=body)

    monkeypatch.setattr(llm, "client", fake_client(handler))
    with pytest.raises(llm.LLMError, match="LLM_MAX_TOKENS"):
        llm.ask(AnalysisResult, "sys", "user")


def test_max_tokens_sent(monkeypatch):
    seen = {}

    def handler(req):
        seen["body"] = json.loads(req.content)
        return reply(json.dumps(ANSWER, ensure_ascii=False))

    monkeypatch.setattr(llm, "client", fake_client(handler))
    llm.ask(AnalysisResult, "sys", "user")
    assert seen["body"]["max_tokens"] > 0 and "frequency_penalty" not in seen["body"]
