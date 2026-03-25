import time

from telegram import Update
from telegram.ext import ContextTypes

from database.models import get_or_create_session, update_session, save_message
from utils.logger import log_interaction


async def handle_user_type_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle Individual / Business button presses."""
    query = update.callback_query
    if not query or not query.data:
        return

    await query.answer()

    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat:
        return

    start_time = time.time()

    if not query.data.startswith("user_type:"):
        return

    user_type = query.data.split(":", 1)[1]  # "individual" or "business"
    session_key = f"{chat.id}_{user.id}"

    session = await get_or_create_session(chat.id, user.id)

    await update_session(session_key, user_type=user_type, conversation_state="active")

    # Edit the original message to show what they selected (remove buttons)
    label = user_type.capitalize()
    try:
        await query.edit_message_reply_markup(reply_markup=None)
    except Exception:
        pass

    response = f"Great, you selected {label}! How can I help you today?"
    await query.message.reply_text(response)

    # Seed conversation history so the AI knows the user has already been greeted
    await save_message(session_key, "user", f"I am an {user_type}.")
    await save_message(session_key, "assistant", response)

    elapsed = int((time.time() - start_time) * 1000)
    await log_interaction(
        session_key=session_key,
        user_id=user.id,
        chat_id=chat.id,
        chat_type=chat.type,
        user_message=f"[Button: {label}]",
        bot_response=response,
        detected_intent=None,
        user_type=user_type,
        response_time_ms=elapsed,
    )
