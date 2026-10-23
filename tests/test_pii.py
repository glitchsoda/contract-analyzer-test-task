from app.pii import mask, unmask_text


def test_roundtrip():
    text = "Контакт: ivan@mail.ru, тел. +7 (913) 123-45-67, ИНН 540123456789."
    masked, mapping = mask(text)
    for secret in ("ivan@mail.ru", "+7 (913)", "540123456789"):
        assert secret not in masked
    assert unmask_text(masked, mapping) == text


def test_same_token():
    masked, _ = mask("a@b.ru и снова a@b.ru")
    assert masked.count("[EMAIL_1]") == 2


def test_org_inn():
    masked, _ = mask("ООО «Ромашка», ИНН 5401234567")
    assert "5401234567" in masked


def test_no_brackets():
    _, mapping = mask("a@b.ru")
    assert unmask_text("пишите на EMAIL_1", mapping) == "пишите на a@b.ru"


def test_passport():
    masked, mapping = mask("паспорт серии 50 12 № 345678, р/с 40702810900000012345")
    assert "345678" not in masked and "40702810900000012345" not in masked
    assert set(mapping) == {"[PASSPORT_1]", "[ACCOUNT_1]"}
