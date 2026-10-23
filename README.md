# Contract Analyzer
Микросервис для анализа договоров. Принимает PDF и возвращает JSON со сторонами, предметом, суммой, рисками и кратким резюме.

## Возможности
* Анализ договора через LLM
* OCR для сканов
* Проверка цитат из ответа модели по тексту договора
* Кэширование результатов
* Веб-интерфейс

Дополнительно:
* MCP-сервер для подключения сервиса к агентам: `python -m app.mcp_server`
* Эндпоинт `/jobs` и Redis для фоновой обработки больших файлов

## Запуск

**Docker**

1. `cp .env.example .env`
2. `docker compose up --build`
3. Открыть http://localhost:8000

**Без Docker**

Нужны Python 3.12, Tesseract с русским языком и Ollama.

1. `pip install -r requirements.txt`
2. `ollama pull qwen3:8b`
3. `cp .env.example .env`, указать `LLM_BASE_URL=http://localhost:11434/v1`
4. `uvicorn app.main:app`

Модель и провайдер задаются в `.env`. Время ответа зависит от модели: от нескольких секунд до нескольких минут на договор.

## Пример запроса
`curl -X POST http://localhost:8000/analyze -F "file=@contract.pdf"`

## Структура проекта
`app`: код сервиса  
`app/static`: веб-интерфейс  
`tests`: тесты  
`ollama`: конфигурация модели для Ollama  

## Тесты
`pytest`

Сервис проверен на синтетических договорах и сканах.
