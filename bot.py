import os
import asyncio
from telegram import Update
from telegram.constants import ChatAction
from telegram.ext import (
    ApplicationBuilder, CommandHandler, MessageHandler, ContextTypes, filters
)

from config import logger, TELEGRAM_TOKEN, LECTURE_FOLDER
from loader import load_all_pdfs  # noqa: F401  (warm import)
from search import get_indexed_data, search_relevant_chunks
from history import add_to_history, clear_history, format_history_for_prompt
from prompt import build_prompt
from gemini_client import generate_with_fallback

TELEGRAM_LIMIT = 4096


def _chunks_for_telegram(text: str, limit: int = TELEGRAM_LIMIT) -> list[str]:
    out, buf = [], ""
    for line in text.splitlines(keepends=True):
        if len(buf) + len(line) > limit:
            if buf:
                out.append(buf)
            # split overly long line
            while len(line) > limit:
                out.append(line[:limit])
                line = line[limit:]
            buf = line
        else:
            buf += line
    if buf:
        out.append(buf)
    return out or [""]


async def _safe_reply(update: Update, text: str) -> None:
    for part in _chunks_for_telegram(text):
        await update.message.reply_text(part, disable_web_page_preview=True)


# ========== HANDLERS ==========

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    chunks, _, _ = get_indexed_data()
    await _safe_reply(
        update,
        "👋 Сайн байна уу!\n\n"
        "Би таны хиймэл оюун ухааны ангийн туслах бот байна.\n\n"
        f"📚 Одоогоор {len(chunks)} хэсэг материал ачаалагдсан байна.\n\n"
        "Лекцийн материалаас асуулт асуугаарай!\n"
        "Тусламж: /help"
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _safe_reply(
        update,
        "📖 Хэрхэн ашиглах вэ?\n\n"
        "• Лекцийн материалтай холбоотой асуулт асуугаарай\n"
        "• Би өмнөх яриаг санана\n"
        "• /clear — яриаг цэвэрлэх\n"
        "• /sources — ачаалагдсан PDF жагсаалт\n\n"
        "Жишээ:\n"
        "  Supervised learning гэж юу вэ?\n"
        "  K-means алгоритмыг тайлбарла"
    )


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_history(update.effective_user.id)
    await _safe_reply(update, "🗑️ Яриа цэвэрлэгдлээ.")


async def sources_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not os.path.exists(LECTURE_FOLDER):
        await _safe_reply(update, "Лекцийн хавтас олдсонгүй.")
        return
    pdfs = sorted(f for f in os.listdir(LECTURE_FOLDER) if f.lower().endswith(".pdf"))
    if not pdfs:
        await _safe_reply(update, "PDF файл ачаалагдаагүй байна.")
        return
    await _safe_reply(update, "📚 Ачаалагдсан PDF:\n" + "\n".join(f"• {p}" for p in pdfs))


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    question = (update.message.text or "").strip()
    if not question:
        return

    try:
        await update.message.chat.send_action(ChatAction.TYPING)
    except Exception:
        pass

    try:
        ctx_text, sources = await asyncio.to_thread(search_relevant_chunks, question)
        if not ctx_text:
            await _safe_reply(
                update,
                "Энэ асуултын хариулт өгөгдсөн хичээлийн материал дотор олдсонгүй."
            )
            return

        history_text = format_history_for_prompt(user_id)
        prompt = build_prompt(ctx_text, history_text, question)

        answer = await asyncio.to_thread(generate_with_fallback, prompt)

        if sources and "Эх сурвалж" not in answer:
            answer += "\n\nЭх сурвалж:\n" + "\n".join(f"• {s}" for s in sources)

        add_to_history(user_id, "user", question)
        add_to_history(user_id, "assistant", answer)
        await _safe_reply(update, answer)

    except Exception as e:
        logger.exception(f"handle_message алдаа: {e}")
        await _safe_reply(update, f"⚠️ Алдаа:\n{type(e).__name__}: {e}")    


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Telegram error", exc_info=context.error)


def main() -> None:
    # warm index at startup
    get_indexed_data()

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("clear", clear_command))
    app.add_handler(CommandHandler("sources", sources_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(on_error)

    logger.info("Бот эхэллээ.")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
