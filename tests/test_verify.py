from app.verify import name_found, normalize, quote_found

TEXT = normalize("4.2. За просрочку  оплаты Заказчик уплачивает\nпеню 1% в день.")


def test_exact_quote():
    assert quote_found("За просрочку оплаты Заказчик уплачивает пеню 1% в день", TEXT)


def test_quote_marks():
    text = normalize("Договор «О поставке» — действует до 2027 г.")
    assert quote_found('Договор "О поставке" - действует до 2027', text)


def test_fake_quote():
    assert not quote_found("Исполнитель вправе расторгнуть договор в одностороннем порядке", TEXT)


def test_short_quote():
    assert not quote_found("пеню", TEXT)


def test_zero_threshold():
    assert quote_found("совсем другой текст про погоду", TEXT, threshold=0)


def test_ellipsis():
    text = normalize("3.1. Поставка осуществляется в срок 45 дней. Прочее. "
                 "7.1. За нарушение сроков поставки уплачивается неустойка 0,1 %.")
    assert quote_found("Поставка осуществляется в срок 45 дней... За нарушение сроков поставки "
                         "уплачивается неустойка 0,1 %", text)
    assert not quote_found("Поставка осуществляется в срок 45 дней… Покупатель вправе "
                             "отказаться от договора в любой момент", text)


def test_party_name():
    text = normalize("Общество с ограниченной ответственностью «ИнфоСервис» (ООО «ИнфоСервис»)")
    assert name_found("ООО «ИнфоСервис»", text)
    assert name_found('ООО "ИнфоСервис"', text)
    assert not name_found("ООО «ИнфoSервис»", text)
