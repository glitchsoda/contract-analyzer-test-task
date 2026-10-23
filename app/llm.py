import json
import re
from concurrent.futures import ThreadPoolExecutor

from openai import NOT_GIVEN, LengthFinishReasonError, OpenAI

from app import config
from app.chunks import make_chunks
from app.schemas import AnalysisResult, ChunkExtraction

client = OpenAI(base_url=config.LLM_BASE_URL, api_key=config.LLM_API_KEY,
                timeout=config.LLM_TIMEOUT, max_retries=2)

PARTY_RULE = ("name: название стороны как в договоре, например ООО «Ромашка» или "
              "Иванов Иван Иванович, без ИНН, адреса и представителя. "
              "role: роль по договору (Исполнитель, Заказчик, Поставщик, Покупатель).")

AMOUNT_RULE = ("amount: общая цена договора («цена договора», «стоимость услуг, работ "
               "или товара» за весь срок). Не штраф, не аванс и не цена за единицу. "
               "value: число без пробелов. Если суммы нет, null.")

RISK_RULE = ("risks: пункты, невыгодные заказчику или покупателю, каждый отдельно. "
             "Например: штрафы и пени, односторонний отказ, изменение цены, размытые сроки, "
             "автопролонгация, молчаливая приёмка, субподрядчики без согласия, "
             "ограничение ответственности, передача прав, неудобная подсудность. "
             "clause: номер пункта.")

QUOTE_RULE = ("quote: точная цитата из текста, 5-40 слов, одним куском. "
              "Не перефразируй и не склеивай разные пункты через многоточие.")

SUMMARY_RULE = ("summary: 2-3 коротких предложения без повторов. "
                "Если документ не договор, так и напиши.")

PII_RULE = ("Токены вида [PERSON_1], [EMAIL_2], [PHONE_1] заменяют персональные данные. "
            "Переноси их в ответ как есть.")

SINGLE_PROMPT = f"""Ты юрист. Разбери договор и верни JSON по схеме.

parties: все стороны. {PARTY_RULE}
subject: предмет договора одной фразой.
{AMOUNT_RULE}
{RISK_RULE}
{SUMMARY_RULE}

{QUOTE_RULE}
{PII_RULE}
Ничего не выдумывай. Если данных нет, ставь null или пустой список."""

MAP_PROMPT = f"""Ты юрист. Это фрагмент договора, часть {{i}} из {{n}}.
Извлеки только то, что есть в этом фрагменте.

parties и subject_candidates. {PARTY_RULE}
amounts: все суммы. В raw укажи, что это: цена, штраф или аванс.
{RISK_RULE}
key_points: 1-5 тезисов.

{QUOTE_RULE}
{PII_RULE}
Если данных нет, оставь списки пустыми."""

REDUCE_PROMPT = f"""Ты юрист. На входе JSON с извлечениями из фрагментов одного договора.
Сведи их в один ответ.

parties: убери дубли (ООО «Ромашка», Ромашка и Исполнитель могут быть одной стороной). {PARTY_RULE}
subject: одна формулировка.
{AMOUNT_RULE}
risks: объедини похожие, сохрани clause, оцени severity.
{SUMMARY_RULE} Опирайся на key_points.

quote переноси из входа без изменений. {PII_RULE}
Используй только данные из входа."""

MERGE_PROMPT = f"""Ты юрист. На входе JSON с извлечениями из соседних фрагментов одного договора.
Объедини их в одно извлечение того же формата: убери дубли сторон и рисков,
оставь все суммы, key_points сократи до 5-8.

quote переноси из входа без изменений. {PII_RULE}
Используй только данные из входа."""

SENTENCE_END = re.compile(r"(?<=[.!?])\s+")
MAX_CHARS_PER_TOKEN = 6   # выше значит, что вход обрезан


class LLMError(Exception):
    pass


def provider_options() -> dict | None:
    effort = config.LLM_REASONING_EFFORT
    if "openrouter.ai" not in config.LLM_BASE_URL:
        return {"reasoning_effort": effort} if effort else None
    options = {"provider": {"require_parameters": True}}
    if config.LLM_FALLBACK_MODELS:
        options["models"] = [config.LLM_MODEL, *config.LLM_FALLBACK_MODELS][:3]
    if effort:
        options["reasoning"] = {"effort": effort}
    return options


def check_cut(resp, chars):
    tokens = resp.usage.prompt_tokens if resp.usage else None
    if tokens and chars > 2000 and chars / tokens > MAX_CHARS_PER_TOKEN:
        raise LLMError("Вход обрезан: контекст модели меньше текста. "
                       "Увеличьте num_ctx или OLLAMA_CONTEXT_LENGTH")


def ask(schema, system, user):
    try:
        resp = client.chat.completions.parse(
            model=config.LLM_MODEL,
            messages=[{"role": "system", "content": system},
                      {"role": "user", "content": user}],
            response_format=schema,
            temperature=config.LLM_TEMPERATURE,
            frequency_penalty=config.LLM_FREQUENCY_PENALTY or NOT_GIVEN,
            max_tokens=config.LLM_MAX_TOKENS,
            extra_body=provider_options(),
        )
    except LengthFinishReasonError:
        raise LLMError("Ответ не уложился в LLM_MAX_TOKENS")
    except Exception as e:
        raise LLMError(f"Ошибка LLM: {type(e).__name__}")   # текст ошибки может содержать договор
    check_cut(resp, len(system) + len(user))
    msg = resp.choices[0].message
    if msg.refusal:
        raise LLMError("Модель отказалась отвечать")
    if msg.parsed is None:
        raise LLMError("Модель вернула невалидный ответ")
    return msg.parsed


def to_json(parts) -> str:
    return json.dumps([p.model_dump() for p in parts], ensure_ascii=False)


def reduce_parts(parts) -> AnalysisResult:
    group = max(config.REDUCE_GROUP, 2)
    while len(parts) > 1 and len(to_json(parts)) > config.SINGLE_PASS_CHARS:
        groups = [parts[i:i + group] for i in range(0, len(parts), group)]
        parts = [g[0] if len(g) == 1 else ask(ChunkExtraction, MERGE_PROMPT, to_json(g))
                 for g in groups]
    return ask(AnalysisResult, REDUCE_PROMPT, to_json(parts))


def short_summary(text, limit=3) -> str:
    seen, out = set(), []
    for sentence in SENTENCE_END.split(text.strip()):
        key = sentence.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(sentence.strip())
        if len(out) == limit:
            break
    return " ".join(out)


def analyze_contract(text: str) -> tuple[AnalysisResult, int]:
    result, chunks = run_model(text)
    result.summary = short_summary(result.summary)
    return result, chunks


def run_model(text) -> tuple[AnalysisResult, int]:
    if len(text) <= config.SINGLE_PASS_CHARS:
        return ask(AnalysisResult, SINGLE_PROMPT, f"Текст договора:\n\n{text}"), 1

    chunks = make_chunks(text, config.CHUNK_CHARS)
    n = len(chunks)

    def extract(item):
        i, chunk = item
        return ask(ChunkExtraction, MAP_PROMPT.format(i=i, n=n), chunk)

    with ThreadPoolExecutor(max_workers=config.MAP_WORKERS) as pool:
        parts = list(pool.map(extract, enumerate(chunks, start=1)))
    return reduce_parts(parts), n
