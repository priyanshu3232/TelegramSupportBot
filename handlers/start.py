from telegram import Update
from telegram.ext import ContextTypes

from database.models import get_or_create_session, update_session
from utils.keyboards import KB_ACCOUNT_TYPE, kb_main


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reset session and show the Step 0 welcome with account-type buttons."""
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

    await update.message.reply_text(
        "\U0001f44b Welcome to <b>Endl Support</b>!\n"
        "I'm here to help you with your account, onboarding status, payments, and more.\n\n"
        "To get started — are you signing up or using Endl as an <b>Individual</b> or a "
        "<b>Business</b>?",
        reply_markup=KB_ACCOUNT_TYPE,
        parse_mode="HTML",
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return

    user = update.effective_user
    chat = update.effective_chat
    session_key = f"{chat.id}_{user.id}" if user and chat else None
    account_type = "individual"
    if session_key:
        session = await get_or_create_session(chat.id, user.id)
        account_type = session.get("user_type") or "individual"

    await update.message.reply_text(
        "Here's what I can help you with — use the menu below to navigate:",
        reply_markup=kb_main(account_type),
    )


# kept for backward-compat imports in message_router (legacy)
def get_user_type_keyboard():
    return KB_ACCOUNT_TYPE
