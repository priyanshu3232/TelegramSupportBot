from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from database.models import get_or_create_session, update_session
from utils.logger import log_interaction


def get_user_type_keyboard() -> InlineKeyboardMarkup:
    """Return inline keyboard with Individual / Business buttons."""
    keyboard = [
        [
            InlineKeyboardButton("Individual", callback_data="user_type:individual"),
            InlineKeyboardButton("Business", callback_data="user_type:business"),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat or not update.message:
        return

    session = await get_or_create_session(chat.id, user.id)
    session_key = f"{chat.id}_{user.id}"
    await update_session(session_key, conversation_state="awaiting_status_choice", user_type=None, email=None)

    greeting = (
        "\U0001f44b Hi! Welcome to Endl Support.\n\n"
        "Would you like to check your onboarding status?\n\n"
        "Reply 'yes' to check status, or just ask me any question."
    )
    await update.message.reply_text(greeting)

    await log_interaction(
        session_key=session_key,
        user_id=user.id,
        chat_id=chat.id,
        chat_type=chat.type,
        user_message="/start",
        bot_response=greeting,
        detected_intent=None,
        user_type=None,
    )


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    if not update.message:
        return

    help_text = (
        "I can help with documents, onboarding status, rejections, "
        "privacy, eligibility, and escalations.\n\n"
        "Just type your question, or use:\n"
        "/start — Restart\n"
        "/help — This message\n"
        "/ticket — Check tickets"
    )
    await update.message.reply_text(help_text)
