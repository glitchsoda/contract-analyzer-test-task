from app.chunks import make_chunks, split_long, split_sections

CONTRACT = "\n".join(
    f"{i}. РАЗДЕЛ {i}\n{i}.1. Текст пункта {i}. " + "слово " * 300
    for i in range(1, 11)
)


def test_sections():
    secs = split_sections(CONTRACT)
    assert len(secs) >= 10
    assert secs[0].startswith("1.")


def test_chunk_limit():
    chunks = make_chunks(CONTRACT, limit=3000)
    assert all(len(c) <= 3000 for c in chunks)
    assert "".join(chunks).count("слово") == CONTRACT.count("слово")


def test_no_numbering():
    text = "\n\n".join(["абзац " * 50] * 10)
    assert len(make_chunks(text, limit=1000)) > 1


def test_amount_not_heading():
    assert len(split_sections("5 000 рублей\n7 дней\n10 штук")) == 1


def test_split_order():
    section = "AAA\n" + "B" * 250 + "\nCCC"
    out = split_long(section, 100)
    assert all(len(x) <= 100 for x in out)
    assert "".join(out).replace("\n", "") == section.replace("\n", "")
