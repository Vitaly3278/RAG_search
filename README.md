# Умный поиск по документам (RAG)

Сервис для поиска ответов по внутренней документации компании с цитированием источников.

Проект содержит два клиентских канала:

- web-интерфейс (`FastAPI + Jinja2`);
- Telegram-бот (`python-telegram-bot`).

Оба канала используют один RAG-движок:

- загрузка документов (`PDF`, `DOCX`, `TXT`, `MD`);
- нарезка на чанки;
- индексация в `Chroma`;
- retrieval + генерация ответа через `OpenAI` или `Ollama`.

## Возможности

- Загрузка и индексация документов через web и API.
- Вопросы к базе знаний с возвратом источников (файл и страница).
- История диалога:
  - в web хранится в сессии браузера;
  - в Telegram хранится в памяти для каждого чата.
- Переключение LLM-провайдера через `.env` без изменения кода.

## Архитектура

Поток запроса:

1. Пользователь задает вопрос (web или Telegram).
2. RAG-ядро ищет релевантные чанки в `Chroma`.
3. Контекст + история диалога передаются в LLM.
4. Возвращается ответ и список источников.

Поток индексации:

1. Документы загружаются через web/API или берутся из папки.
2. Документы читаются загрузчиком (`PyPDF`, `docx2txt`, `TextLoader`).
3. Текст режется на чанки.
4. Чанки сохраняются в векторную БД `Chroma`.

## Структура проекта

- `app/config.py` — конфигурация через переменные окружения.
- `app/document_loader.py` — загрузка и нормализация документов.
- `app/rag.py` — embeddings, Chroma, retrieval, генерация ответа.
- `app/api.py` — web-страницы и HTTP API.
- `web/templates/index.html` — web-интерфейс.
- `bot/telegram_bot.py` — Telegram-бот.
- `scripts/index_documents.py` — CLI-индексация.
- `data/docs/` — локальная папка с документами для CLI.
- `storage/chroma/` — локальное хранилище векторного индекса.

## Требования

- `Python 3.11+`
- `pip`
- (опционально) `Docker` и `Docker Compose`
- Для режима `openai`: ключ API.
- Для режима `ollama`: локально поднятый `Ollama`.

## Быстрый старт (локально)

### 1) Установка зависимостей

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

### 2) Настройка окружения

```bash
cp .env.example .env
```

Заполните `.env` (минимально):

- `LLM_PROVIDER` — `openai` или `ollama`;
- `TELEGRAM_BOT_TOKEN` — если используете бота;
- `SESSION_SECRET_KEY` — секрет для web-сессий.

### 3) Запуск web

```bash
uvicorn app.api:app --reload --host 0.0.0.0 --port 8000
```

Откройте [http://localhost:8000](http://localhost:8000).

Через web доступны:

- загрузка файлов и индексация;
- чат по документации;
- очистка истории диалога.

### 4) Запуск Telegram-бота

```bash
python3 -m bot.telegram_bot
```

В Telegram:

- отправьте `/start`;
- задавайте вопросы обычными сообщениями.

## Быстрый старт (Docker)

```bash
cp .env.example .env
docker compose up --build
```

Сервисы:

- `web` -> [http://localhost:8000](http://localhost:8000)
- `bot` -> long polling в Telegram

## Конфигурация `.env`

### Общие переменные

- `LLM_PROVIDER` — провайдер LLM (`openai` или `ollama`).
- `EMBEDDING_MODEL_NAME` — модель embeddings.
- `VECTOR_DB_DIR` — путь к директории Chroma.
- `COLLECTION_NAME` — имя коллекции Chroma.
- `CHUNK_SIZE` — размер чанка.
- `CHUNK_OVERLAP` — пересечение чанков.
- `TOP_K` — количество извлекаемых чанков.
- `TELEGRAM_BOT_TOKEN` — токен Telegram-бота.
- `SESSION_SECRET_KEY` — ключ подписи web-сессии.

### OpenAI-режим

```env
LLM_PROVIDER=openai
OPENAI_API_KEY=your_api_key
OPENAI_BASE_URL=
MODEL_NAME=gpt-4o-mini
```

Примечание: `OPENAI_BASE_URL` указывайте, если используете OpenAI-compatible endpoint.

### Ollama-режим

```env
LLM_PROVIDER=ollama
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL_NAME=qwen2.5:7b
```

Перед запуском убедитесь, что модель загружена, например:

```bash
ollama pull qwen2.5:7b
```

## Индексация документов

Есть два способа:

### Способ A: через web

1. Откройте главную страницу.
2. Выберите несколько файлов.
3. Нажмите "Загрузить и проиндексировать".

### Способ B: через CLI

1. Положите документы в `data/docs/`.
2. Выполните:

```bash
python3 -m scripts.index_documents --path data/docs
```

## HTTP API

### `POST /api/upload`

Загрузка и индексация документов.

- Формат: `multipart/form-data`
- Поле: `files` (можно несколько)

Пример:

```bash
curl -X POST "http://localhost:8000/api/upload" \
  -F "files=@data/docs/manual.pdf" \
  -F "files=@data/docs/faq.docx"
```

Ожидаемый ответ:

```json
{
  "indexed_chunks": 124,
  "files": ["manual.pdf", "faq.docx"]
}
```

### `POST /api/ask`

Вопрос к RAG-индексу.

Пример:

```bash
curl -X POST "http://localhost:8000/api/ask" \
  -H "Content-Type: application/json" \
  -d '{"question":"Как настроить устройство?"}'
```

Ожидаемый ответ:

```json
{
  "answer": "Текст ответа...",
  "sources": [
    {"source": "manual.pdf", "page": "12"}
  ]
}
```

## Примеры использования

Вопросы:

- "Как сделать первичную настройку устройства?"
- "Какие есть коды ошибок и где они описаны?"
- "Как изменить сетевые параметры?"

Ожидаемое поведение:

- если данные есть в документах, бот отвечает с ссылками на источники;
- если данных нет, бот отвечает: `Не нашёл в документации.`

## Ограничения текущей версии

- История Telegram хранится только в памяти процесса (после перезапуска очищается).
- История web хранится в сессии браузера (локально, не общий чат).
- Индекс Chroma локальный (без распределенного хранения).
- Нет авторизации пользователей.

## Troubleshooting

- `Индекс не найден`:
  - сначала загрузите документы через web/API или запустите CLI-индексацию;
  - проверьте путь `VECTOR_DB_DIR`.
- `OpenAI error / unauthorized`:
  - проверьте `OPENAI_API_KEY`;
  - проверьте `OPENAI_BASE_URL`, если используете совместимый endpoint.
- `Ollama connection refused`:
  - убедитесь, что Ollama запущен;
  - проверьте `OLLAMA_BASE_URL`.
- Бот не отвечает:
  - проверьте `TELEGRAM_BOT_TOKEN`;
  - убедитесь, что процесс `python3 -m bot.telegram_bot` запущен.

## План развития

- Добавить persistent storage для истории диалогов.
- Добавить reranking и оценку релевантности источников.
- Поддержать `Qdrant` как альтернативную векторную БД.
- Добавить авторизацию и роли доступа к документам.

