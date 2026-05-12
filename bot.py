import os
import asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.constants import ChatAction
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

from config import logger, TELEGRAM_TOKEN, CATEGORIES, LOCAL_MATERIALS_DIR
from search import (
    search_relevant_chunks,
    clear_indexes,
    get_category_chunk_count,
    get_category_sources,
)
from history import (
    add_to_history,
    clear_history,
    format_history_for_prompt,
    set_user_category,
    get_user_category,
    get_user_status,
)
from prompt import build_prompt, NOT_FOUND_MESSAGE
from gemini_client import generate_with_fallback


TELEGRAM_LIMIT = 4096


# =========================
# TELEGRAM HELPERS
# =========================

def category_keyboard() -> ReplyKeyboardMarkup:
    buttons = [[label] for label in CATEGORIES.values()]
    return ReplyKeyboardMarkup(
        buttons,
        resize_keyboard=True,
        one_time_keyboard=False,
    )


def category_from_label(label: str) -> str | None:
    for key, value in CATEGORIES.items():
        if value == label:
            return key
    return None


def _chunks_for_telegram(text: str, limit: int = TELEGRAM_LIMIT) -> list[str]:
    out = []
    buf = ""

    for line in text.splitlines(keepends=True):
        if len(buf) + len(line) > limit:
            if buf:
                out.append(buf)

            while len(line) > limit:
                out.append(line[:limit])
                line = line[limit:]

            buf = line
        else:
            buf += line

    if buf:
        out.append(buf)

    return out or [""]


async def _safe_reply(update: Update, text: str, reply_markup=None) -> None:
    try:
        parts = _chunks_for_telegram(text)

        for i, part in enumerate(parts):
            await update.message.reply_text(
                part,
                reply_markup=reply_markup if i == 0 else None,
                disable_web_page_preview=True,
            )

    except Exception as e:
        logger.error(f"Reply error: {e}", exc_info=True)


# =========================
# COMMANDS
# =========================

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _safe_reply(
        update,
        "👋 Сайн байна уу!\n\n"
        "Би таны хичээлийн AI туслах бот байна.\n\n"
        "Эхлээд ямар төрлийн материалаас асуухаа сонгоно уу:",
        reply_markup=category_keyboard(),
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _safe_reply(
        update,
        "📖 Хэрхэн ашиглах вэ?\n\n"
        "1. /start эсвэл /category ашиглаад материалын төрлөө сонгоно.\n"
        "2. Дараа нь асуултаа асууна.\n"
        "3. Бот зөвхөн сонгосон материалын folder-оос хайна.\n\n"
        "Командууд:\n"
        "• /category — материалын төрөл солих\n"
        "• /status — одоогийн сонголт харах\n"
        "• /sources — сонгосон төрөл доторх PDF жагсаалт\n"
        "• /reindex — PDF index шинэчлэх\n"
        "• /clear — ярианы түүх цэвэрлэх\n\n"
        "Төрлүүд:\n"
        "• 🏫 Course Info\n"
        "• 📚 Lecture\n"
        "• 🧪 Laboratory",
    )


async def category_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await _safe_reply(
        update,
        "Материалын төрлөө сонгоно уу:",
        reply_markup=category_keyboard(),
    )


async def clear_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_history(update.effective_user.id)
    await _safe_reply(update, "🗑️ Ярианы түүх цэвэрлэгдлээ.")


async def status_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    category = get_user_category(user_id)

    if not category:
        await _safe_reply(
            update,
            "Одоогоор материалын төрөл сонгоогүй байна.\n"
            "Эхлээд /category ашиглаад сонгоно уу.",
            reply_markup=category_keyboard(),
        )
        return

    chunk_count = await asyncio.to_thread(get_category_chunk_count, category)

    await _safe_reply(
        update,
        f"{get_user_status(user_id)}\n"
        f"Index-д орсон chunk тоо: {chunk_count}",
    )


async def sources_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    category = get_user_category(user_id)

    if not category:
        await _safe_reply(
            update,
            "Эхлээд материалын төрлөө сонгоно уу:",
            reply_markup=category_keyboard(),
        )
        return

    sources = await asyncio.to_thread(get_category_sources, category)

    if not sources:
        await _safe_reply(
            update,
            f"{CATEGORIES[category]} дотор PDF файл олдсонгүй.\n"
            f"Folder шалга: {os.path.join(LOCAL_MATERIALS_DIR, category)}",
        )
        return

    await _safe_reply(
        update,
        f"📚 {CATEGORIES[category]} доторх PDF файлууд:\n\n"
        + "\n".join(f"• {source}" for source in sources),
    )


async def reindex_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    clear_indexes()
    await _safe_reply(
        update,
        "🔄 Index cache цэвэрлэгдлээ.\n"
        "Дараагийн асуулт дээр материалууд шинээр уншигдана.",
    )


# =========================
# MESSAGE HANDLER
# =========================

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = (update.message.text or "").strip()

    if not text:
        return

    selected_category = category_from_label(text)

    if selected_category:
        ok = set_user_category(user_id, selected_category)

        if not ok:
            await _safe_reply(update, "Ийм материалын төрөл байхгүй байна.")
            return

        await _safe_reply(
            update,
            f"✅ Та {CATEGORIES[selected_category]} сонголоо.\n\n"
            "Одоо асуултаа асуугаарай.",
        )
        return

    category = get_user_category(user_id)

    if not category:
        await _safe_reply(
            update,
            "Эхлээд ямар төрлийн материалаас асуухаа сонгоно уу:",
            reply_markup=category_keyboard(),
        )
        return

    logger.info(f"User {user_id} asked in category={category}: {text}")

    try:
        await update.message.chat.send_action(ChatAction.TYPING)
    except Exception:
        pass

    try:
        ctx_text, sources = await asyncio.to_thread(
            search_relevant_chunks,
            text,
            category,
        )

        if not ctx_text:
            await _safe_reply(update, NOT_FOUND_MESSAGE)
            return

        history_text = format_history_for_prompt(user_id)

        prompt = build_prompt(
            context=ctx_text,
            history_text=history_text,
            question=text,
            category=category,
        )

        answer = await asyncio.to_thread(generate_with_fallback, prompt)
        answer = answer.strip()

        if sources and "Эх сурвалж" not in answer:
            answer += "\n\nЭх сурвалж:\n" + "\n".join(f"• {s}" for s in sources)

        add_to_history(user_id, "user", text)
        add_to_history(user_id, "assistant", answer)

        await _safe_reply(update, answer)

    except Exception as e:
        logger.exception(f"handle_message алдаа: {e}")
        await _safe_reply(update, f"⚠️ Алдаа:\n{type(e).__name__}: {e}")


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Telegram error", exc_info=context.error)


# =========================
# MAIN
# =========================

def main() -> None:
    logger.info("Бот эхэлж байна...")

    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("category", category_command))
    app.add_handler(CommandHandler("status", status_command))
    app.add_handler(CommandHandler("sources", sources_command))
    app.add_handler(CommandHandler("reindex", reindex_command))
    app.add_handler(CommandHandler("clear", clear_command))

    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(on_error)

    logger.info("Бот ажиллаж байна.")
    app.run_polling(drop_pending_updates=True, allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()