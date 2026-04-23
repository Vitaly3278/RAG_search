import logging

from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes, MessageHandler, filters

from app.config import settings
from app.rag import ask_question, has_index


logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    message = (
        "Привет! Я бот для поиска по документации.\n"
        "Просто отправь вопрос текстом."
    )
    await update.message.reply_text(message)


async def answer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not has_index():
        await update.message.reply_text(
            "Индекс документов не найден. Сначала загрузите и проиндексируйте документы."
        )
        return

    question = (update.message.text or "").strip()
    if not question:
        await update.message.reply_text("Отправьте непустой вопрос.")
        return

    try:
        history = context.chat_data.get("history", [])
        result = ask_question(question, history=history)
        history.append({"user": question, "assistant": str(result["answer"])})
        context.chat_data["history"] = history[-10:]

        source_lines = [
            f"- {item['source']}, стр. {item['page']}" for item in result["sources"]
        ]
        sources_text = "\n".join(source_lines) if source_lines else "- нет"
        text = f"{result['answer']}\n\nИсточники:\n{sources_text}"
        await update.message.reply_text(text[:4000])
    except Exception as exc:  # pragma: no cover
        logger.exception("Failed to process question: %s", exc)
        await update.message.reply_text("Ошибка при обработке вопроса.")


def main() -> None:
    if not settings.telegram_bot_token:
        raise RuntimeError("Set TELEGRAM_BOT_TOKEN in .env first.")

    app = Application.builder().token(settings.telegram_bot_token).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, answer))
    app.run_polling()


if __name__ == "__main__":
    main()
