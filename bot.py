import asyncio
import logging
import sys

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from config import BOT_TOKEN, SUPPORT_LINK, ANTHROPIC_API_KEY, CLAUDE_MODEL
from database.db import init_db
from database.models import get_user_tickets
from handlers.start import start_command, help_command
from handlers.message_router import handle_message, handle_non_text
from handlers.group_handler import handle_group_message, handle_edited_group_message, handle_new_chat_members
from handlers.callback_handler import handle_callback

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("bot_debug.log", encoding="utf-8"),
    ],
)
logger = logging.getLogger(__name__)


async def ticket_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    if not user or not update.message:
        return

    tickets = await get_user_tickets(user.id)
    if not tickets:
        await update.message.reply_text(
            "You have no open support tickets.\n\n"
            "If you need help, just ask your question and I will assist you."
        )
        return

    lines = ["Your recent support tickets:\n"]
    for i, t in enumerate(tickets, 1):
        lines.append(
            f"{i}. {t['ticket_id']}\n"
            f"   Category: {t['issue_category']}\n"
            f"   Severity: {t['severity']}\n"
            f"   Status: {t['status']}\n"
            f"   Created: {t['created_at']}"
        )
    lines.append(f"\nFor updates, contact support: {SUPPORT_LINK}")
    await update.message.reply_text("\n".join(lines))


async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    import traceback
    logger.error("Exception while handling an update:", exc_info=context.error)
    if context.error:
        logger.error(
            "Global error handler: %s: %s",
            type(context.error).__name__, context.error,
        )
        logger.error("Global error traceback: %s", "".join(
            traceback.format_exception(type(context.error), context.error, context.error.__traceback__)
        ))
    if isinstance(update, Update):
        chat = update.effective_chat
        user = update.effective_user
        logger.error(
            "Error context: chat_type=%s, chat_id=%s, user_id=%s, user=%s",
            chat.type if chat else "N/A",
            chat.id if chat else "N/A",
            user.id if user else "N/A",
            user.username if user else "N/A",
        )
        if update.message:
            logger.error("Message text: %s", update.message.text[:100] if update.message.text else "N/A")
            await update.message.reply_text(
                "Oops, something unexpected happened on my end. Please try again, "
                f"and if it persists, our team is here to help: {SUPPORT_LINK}"
            )


async def post_init(application) -> None:
    await init_db()
    logger.info("Database initialized successfully.")

    # Validate Claude API key on startup
    await _validate_api_key()


async def _validate_api_key() -> None:
    """Make a lightweight API call at startup to verify the key works."""
    if not ANTHROPIC_API_KEY:
        logger.error("ANTHROPIC_API_KEY is empty — AI responses will fail!")
        return

    import httpx

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key": ANTHROPIC_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                json={
                    "model": CLAUDE_MODEL,
                    "max_tokens": 16,
                    "messages": [{"role": "user", "content": "ping"}],
                },
            )

        if resp.status_code == 200:
            data = resp.json()
            text = data["content"][0]["text"][:40]
            logger.info("Claude API key validated successfully (model=%s, response=%s)", CLAUDE_MODEL, text)
        elif resp.status_code == 401:
            logger.error(
                "ANTHROPIC_API_KEY is INVALID or EXPIRED. "
                "Please check your .env file and update the key from https://console.anthropic.com"
            )
        elif resp.status_code == 404:
            logger.error(
                "Model '%s' not found. Your API key may not have access to this model. "
                "Try changing CLAUDE_MODEL in .env to 'claude-sonnet-4-20250514' or 'claude-haiku-4-5-20251001'.",
                CLAUDE_MODEL,
            )
        else:
            logger.error("Claude API validation returned status %s: %s", resp.status_code, resp.text[:200])
    except httpx.TimeoutException:
        logger.error("Claude API validation timed out — check your network connection")
    except Exception as e:
        logger.error("Unexpected error validating Claude API key: %s", e)


def main() -> None:
    if not BOT_TOKEN:
        raise RuntimeError("Missing BOT_TOKEN environment variable")

    app = ApplicationBuilder().token(BOT_TOKEN).post_init(post_init).build()

    # Command handlers
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("help", help_command))
    app.add_handler(CommandHandler("ticket", ticket_command))

    # Callback query handler — handles all inline button presses
    app.add_handler(CallbackQueryHandler(handle_callback))

    # Non-text messages (images, stickers, files) — private chats only
    app.add_handler(
        MessageHandler(~filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_non_text)
    )

    # Private chat message handler
    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND & filters.ChatType.PRIVATE, handle_message)
    )

    # Group chat message handler
    app.add_handler(
        MessageHandler(
            filters.TEXT & ~filters.COMMAND & (filters.ChatType.GROUP | filters.ChatType.SUPERGROUP),
            handle_group_message,
        )
    )

    # Bot added to group — send intro message
    app.add_handler(
        MessageHandler(
            filters.StatusUpdate.NEW_CHAT_MEMBERS,
            handle_new_chat_members,
        )
    )

    # Edited group message handler (re-check @mention after edits)
    app.add_handler(
        MessageHandler(
            filters.UpdateType.EDITED_MESSAGE & filters.TEXT & ~filters.COMMAND
            & (filters.ChatType.GROUP | filters.ChatType.SUPERGROUP),
            handle_edited_group_message,
        )
    )

    # Error handler
    app.add_error_handler(error_handler)

    logger.info("Endl Support Bot starting...")
    logger.info("Press Ctrl+C to stop the bot.")

    # On Windows, asyncio event loops do not support add_signal_handler(),
    # so we pass stop_signals=None to prevent the library from trying to
    # register signal handlers.  Ctrl+C will still raise KeyboardInterrupt
    # which we catch below.
    if sys.platform == "win32":
        stop_signals = None
    else:
        import signal
        stop_signals = (signal.SIGINT, signal.SIGTERM)

    try:
        app.run_polling(
            allowed_updates=Update.ALL_TYPES,
            stop_signals=stop_signals,
        )
    except KeyboardInterrupt:
        logger.info("KeyboardInterrupt received — shutting down.")
    except SystemExit:
        pass
    finally:
        logger.info("Endl Support Bot stopped.")


if __name__ == "__main__":
    main()
