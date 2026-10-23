import re

HEADING = re.compile(
    r"^\s*(?:(?:Раздел|РАЗДЕЛ|Статья|СТАТЬЯ|Глава|ГЛАВА)\s+\d+"
    r"|\d{1,2}(?:\.\d{1,2}){0,3}\.?\s+[А-ЯЁA-Z«\"])",
    re.MULTILINE,
)


def split_sections(text) -> list[str]:
    starts = [m.start() for m in HEADING.finditer(text)]
    if len(starts) < 3:
        return [p for p in text.split("\n\n") if p.strip()]
    if starts[0] != 0:
        starts.insert(0, 0)
    starts.append(len(text))
    return [text[a:b].strip() for a, b in zip(starts, starts[1:]) if text[a:b].strip()]


def split_long(section, limit) -> list[str]:
    out, cur = [], ""
    for line in section.split("\n"):
        if len(line) > limit:
            if cur:
                out.append(cur)
                cur = ""
            while len(line) > limit:
                out.append(line[:limit])
                line = line[limit:]
        if cur and len(cur) + len(line) + 1 > limit:
            out.append(cur)
            cur = ""
        cur = f"{cur}\n{line}" if cur else line
    if cur:
        out.append(cur)
    return out


def make_chunks(text, limit=12_000) -> list[str]:
    chunks, cur = [], ""
    for section in split_sections(text):
        pieces = split_long(section, limit) if len(section) > limit else [section]
        for piece in pieces:
            if cur and len(cur) + len(piece) + 2 > limit:
                chunks.append(cur)
                cur = ""
            cur = f"{cur}\n\n{piece}" if cur else piece
    if cur:
        chunks.append(cur)
    return chunks
