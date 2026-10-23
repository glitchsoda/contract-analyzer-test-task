import re

from app import config

RULES = [
    ("EMAIL", re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+"), 0),
    ("PHONE", re.compile(
        r"(?<!\d)(?:\+7|8)[\s(-]*\d{3}[\s)-]*\d{3}[\s-]*\d{2}[\s-]*\d{2}(?!\d)"), 0),
    ("SNILS", re.compile(r"(?<!\d)\d{3}-\d{3}-\d{3}[\s-]?\d{2}(?!\d)"), 0),
    ("INN", re.compile(r"ИНН[\s:№]*(\d{12})(?!\d)", re.I), 1),   # 12 цифр, физлицо
    ("PASSPORT", re.compile(
        r"паспорт[^\d]{0,40}(\d{2}\s?\d{2}\s*(?:№|N|номер)?\s*\d{6})(?!\d)", re.I), 1),
    ("CARD", re.compile(r"(?<!\d)(?:\d{4}[\s-]?){3}\d{4}(?!\d)"), 0),
    ("ACCOUNT", re.compile(r"(?<!\d)\d{20}(?!\d)"), 0),
]
LABELS = [label for label, _, _ in RULES] + ["PERSON"]
TOKEN = re.compile(r"\[?\b(" + "|".join(LABELS) + r")_(\d+)\b\]?")

ner = None


def find_names(text) -> list[tuple]:
    global ner
    try:
        from natasha import Doc, NewsEmbedding, NewsNERTagger, Segmenter
    except ImportError:
        return []
    if ner is None:
        ner = (Segmenter(), NewsNERTagger(NewsEmbedding()))
    segmenter, tagger = ner
    doc = Doc(text)
    doc.segment(segmenter)
    doc.tag_ner(tagger)
    return [(s.start, s.stop, "PERSON") for s in doc.spans if s.type == "PER"]


def mask(text: str) -> tuple[str, dict]:
    spans = [(m.start(group), m.end(group), label)
             for label, regex, group in RULES for m in regex.finditer(text)]
    if config.PII_NAMES:
        spans += find_names(text)

    spans.sort(key=lambda s: (s[0], s[0] - s[1]))
    kept, last_end = [], -1
    for s in spans:
        if s[0] >= last_end:
            kept.append(s)
            last_end = s[1]

    tokens, counts = {}, {}
    out, pos = [], 0
    for start, end, label in kept:
        value = text[start:end]
        if value not in tokens:
            counts[label] = counts.get(label, 0) + 1
            tokens[value] = f"[{label}_{counts[label]}]"
        out += [text[pos:start], tokens[value]]
        pos = end
    out.append(text[pos:])
    return "".join(out), {token: value for value, token in tokens.items()}


def unmask_text(text, mapping) -> str:
    return TOKEN.sub(lambda m: mapping.get(f"[{m.group(1)}_{m.group(2)}]", m.group(0)), text)


def unmask(model, mapping):
    def walk(x):
        if isinstance(x, str):
            return unmask_text(x, mapping)
        if isinstance(x, list):
            return [walk(i) for i in x]
        if isinstance(x, dict):
            return {k: walk(v) for k, v in x.items()}
        return x
    return type(model).model_validate(walk(model.model_dump()))
