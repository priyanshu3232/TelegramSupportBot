from telegram import Update
from telegram.ext import ContextTypes

from database.models import get_or_create_session, update_session
from utils.keyboards import kb_main


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reset session and show the welcome message with main menu."""
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat or not update.message:
        return

    session_key = f"{chat.id}_{user.id}"
    await get_or_create_session(chat.id, user.id)
    await update_session(
        session_key,
        conversation_state="active",
        user_type=None,
        email=None,
        frustration_count=0,
        unrecognized_count=0,
    )

    first_name = user.first_name or ""
    greeting = f"Hey {first_name}! " if first_name else ""

    await update.message.reply_text(
        f"\U0001f44b {greeting}Welcome to <b>Endl Support</b>!\n"
        "I'm here to help you with your account, onboarding, payments, and more.\n\n"
        "How can I help you today?",
        reply_markup=kb_main(),
        parse_mode="HTML",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return

    await update.message.reply_text(
        "Here's what I can help you with — pick an option below:",
        reply_markup=kb_main(),
    )
