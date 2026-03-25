import logging
import re
import time
import traceback

from telegram import Update
from telegram.ext import ContextTypes

from database.models import (
    get_or_create_session, update_session, save_message,
    get_conversation_history, get_recent_intents,
    save_verified_user, get_verified_email,
)
from handlers.classifier import classify_user_type
from handlers.greeting import is_greeting
from handlers.intent_detector import detect_intent
from handlers.escalation import handle_escalation
from handlers.start import get_user_type_keyboard
from ai.claude_client import get_ai_response
from ai.system_prompt import get_system_prompt
from utils.rate_limiter import is_rate_limited
from utils.cache import get_cached_response
from utils.formatter import sanitize_response
from utils.logger import log_interaction
from utils.otp import generate_otp, store_otp, verify_otp, send_otp_email
from services.sumsub_client import (
    search_applicant_by_email, get_applicant_status,
    get_document_status, format_status_message,
)
from config import (
    SUPPORT_LINK,
    SUMSUB_APP_TOKEN,
    SUMSUB_SECRET_KEY,
    SMTP_USER,
    SMTP_PASSWORD,
)

logger = logging.getLogger(__name__)

_ESCALATION_KEYWORDS = [
    "locked", "frozen", "fraud", "unauthorized", "speak to human",
    "talk to agent", "legal", "tax", "human", "agent",
    "tax id", "no tax id", "don't have tax id",
    "personal iban", "personal european iban",
    "only swift", "can only send swift", "must use swift",
]

_EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")

# Keywords that trigger the status-check flow
_STATUS_KEYWORDS = [
    "status", "onboarding status", "check status", "my status",
    "kyc status", "kyb status", "check my", "application status",
    "verification status", "where is my application",
]


def _wants_status_check(text: str) -> bool:
    lower = text.lower().strip()
    return any(kw in lower for kw in _STATUS_KEYWORDS)


def _status_feature_available() -> tuple[bool, str]:
    """Check whether status/OTP flow has the required credentials."""
    missing = []
    if not SUMSUB_APP_TOKEN or not SUMSUB_SECRET_KEY:
        missing.append("SumSub API credentials")
    if not SMTP_USER or not SMTP_PASSWORD:
        missing.append("SMTP credentials for sending OTPs")
    if missing:
        return False, ", ".join(missing)
    return True, ""


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat or not update.message:
        return

    # Group handler passes cleaned text and threading info via context
    group_msg = context.user_data.get("_group_msg") if context.user_data else None

    if group_msg:
        message_text = group_msg.get("clean_text", "").strip()
        reply_to_msg_id = group_msg.get("reply_to_msg_id")
    else:
        raw_text = update.message.text
        if not raw_text:
            return
        message_text = raw_text.strip()
        reply_to_msg_id = None

    if not message_text:
        return

    user_id = user.id
    chat_id = chat.id
    chat_type = chat.type
    session_key = f"{chat_id}_{user_id}"

    reply_kw = {"reply_to_message_id": reply_to_msg_id} if reply_to_msg_id else {}

    logger.info(
        "Message from user %s (chat_type=%s, chat_id=%s): %s",
        user_id, chat_type, chat_id, message_text[:80],
    )

    try:
        await _process_message(
            update, user_id, chat_id, chat_type, message_text, session_key, reply_kw,
        )
    except Exception as e:
        logger.error("Error processing message from user %s: %s", user_id, e, exc_info=True)
        logger.error("Full traceback: %s", traceback.format_exc())
        try:
            await update_session(session_key, conversation_state="active")
        except Exception as session_err:
            logger.error("Failed to reset session state after error: %s", session_err)
        try:
            await update.message.reply_text(
                "Something went wrong on my end. Please try again, or reach out to "
                f"our live support: {SUPPORT_LINK}",
                **reply_kw,
            )
        except Exception as reply_err:
            logger.error("Failed to send error reply: %s", reply_err)


async def _process_message(
    update: Update,
    user_id: int,
    chat_id: int,
    chat_type: str,
    message_text: str,
    session_key: str,
    reply_kw: dict | None = None,
) -> None:
    if reply_kw is None:
        reply_kw = {}

    # Rate limit check
    if is_rate_limited(user_id):
        await update.message.reply_text(
            "You are sending messages too quickly. Please wait a moment and try again.",
            **reply_kw,
        )
        return

    start_time = time.time()

    # Get or create session
    session = await get_or_create_session(chat_id, user_id)
    state = session.get("conversation_state", "greeting")
    user_type = session.get("user_type")

    logger.info("Session state=%s, user_type=%s for %s", state, user_type, session_key)

    # In group chats, skip onboarding flow entirely
    is_group = chat_type in ("group", "supergroup")
    if is_group and state in ("greeting", "awaiting_email", "awaiting_classification",
                               "status_awaiting_email", "status_awaiting_otp"):
        user_type = user_type or "individual"
        await update_session(session_key, conversation_state="active", user_type=user_type)
        state = "active"
        logger.info("Group chat — skipped flows, set state=active for %s", session_key)

    # ─── GREETING STATE ─────────────────────────────────────────────
    if state == "greeting":
        if is_greeting(message_text):
            response = (
                "\U0001f44b Hi! Welcome to Endl Support.\n\n"
                "Would you like to check your onboarding status?\n\n"
                "Reply 'yes' to check status, or just ask me any question."
            )
            await update_session(session_key, conversation_state="awaiting_status_choice")
            await update.message.reply_text(response, **reply_kw)
            elapsed = int((time.time() - start_time) * 1000)
            await log_interaction(
                session_key, user_id, chat_id, chat_type,
                message_text, response, None, user_type,
                response_time_ms=elapsed,
            )
            return
        else:
            # Not a greeting — skip onboarding, answer directly
            await update_session(session_key, conversation_state="active", user_type=user_type or "individual")
            user_type = user_type or "individual"
            # Fall through to active state

    # ─── AWAITING STATUS CHOICE ─────────────────────────────────────
    if state == "awaiting_status_choice":
        lower = message_text.lower().strip()
        if lower in ("yes", "y", "yeah", "sure", "ok", "check status", "status"):
            available, reason = _status_feature_available()
            if not available:
                response = (
                    "I can't check onboarding status right now because required "
                    f"credentials are missing ({reason}). Please contact support: {SUPPORT_LINK}"
                )
                await update_session(session_key, conversation_state="active")
                await update.message.reply_text(response, **reply_kw)
                return
            # Check if user already has a verified email
            verified_email = await get_verified_email(user_id)
            if verified_email:
                response = (
                    f"I have your verified email: {verified_email}\n\n"
                    "Would you like to check status with this email? Reply 'yes' or enter a different email."
                )
                await update_session(session_key, conversation_state="status_confirm_email")
                await update.message.reply_text(response, **reply_kw)
                return

            response = "Please enter your email address."
            await update_session(session_key, conversation_state="status_awaiting_email")
            await update.message.reply_text(response, **reply_kw)
            return
        else:
            # User wants to ask a question instead — move to onboarding or active
            await update_session(session_key, conversation_state="awaiting_email")
            # Treat as email collection step
            response = "No problem! Could you please share your email address so I can assist you better?"
            await update.message.reply_text(response, **reply_kw)
            return

    # ─── STATUS: CONFIRM PREVIOUSLY VERIFIED EMAIL ──────────────────
    if state == "status_confirm_email":
        lower = message_text.lower().strip()
        if lower in ("yes", "y", "yeah", "sure"):
            verified_email = await get_verified_email(user_id)
            if verified_email:
                await update.message.reply_text("\u23f3 Fetching your status...", **reply_kw)
                await _fetch_and_send_status(update, session_key, user_id, chat_id,
                                              chat_type, verified_email, start_time, reply_kw)
                return
        # User entered a different email
        if _EMAIL_REGEX.match(message_text.strip()):
            email = message_text.strip().lower()
            await update_session(session_key, email=email)
            await _send_otp_and_transition(update, session_key, user_id, chat_id,
                                            chat_type, email, start_time, reply_kw)
            return
        response = "Please reply 'yes' to use your saved email, or enter a different email address."
        await update.message.reply_text(response, **reply_kw)
        return

    # ─── STATUS: AWAITING EMAIL ─────────────────────────────────────
    if state == "status_awaiting_email":
        email = message_text.strip().lower()
        if not _EMAIL_REGEX.match(email):
            response = "That doesn't look like a valid email address. Please try again."
            await update.message.reply_text(response, **reply_kw)
            return

        await update_session(session_key, email=email)
        await _send_otp_and_transition(update, session_key, user_id, chat_id,
                                        chat_type, email, start_time, reply_kw)
        return

    # ─── STATUS: AWAITING OTP ───────────────────────────────────────
    if state == "status_awaiting_otp":
        email = session.get("email", "")

        # Allow user to request a new OTP
        lower = message_text.lower().strip()
        if lower in ("resend", "new code", "resend otp", "yes"):
            await _send_otp_and_transition(update, session_key, user_id, chat_id,
                                            chat_type, email, start_time, reply_kw)
            return

        # Verify the OTP
        success, msg = await verify_otp(email, message_text.strip())
        if success:
            # Save verified user permanently
            await save_verified_user(chat_id, user_id, email)
            await update.message.reply_text(
                "\u2705 Email verified!\n\n\u23f3 Fetching your onboarding status...",
                **reply_kw,
            )
            await _fetch_and_send_status(update, session_key, user_id, chat_id,
                                          chat_type, email, start_time, reply_kw)
        else:
            await update.message.reply_text(msg, **reply_kw)
        return

    # ─── ORIGINAL ONBOARDING: AWAITING EMAIL ────────────────────────
    if state == "awaiting_email":
        email = message_text.strip()
        await update_session(session_key, email=email, conversation_state="awaiting_classification")
        response = "Thanks! Are you an Individual or a Business?"
        await update.message.reply_text(response, reply_markup=get_user_type_keyboard(), **reply_kw)
        await save_message(session_key, "user", message_text)
        await save_message(session_key, "assistant", response)
        elapsed = int((time.time() - start_time) * 1000)
        await log_interaction(
            session_key, user_id, chat_id, chat_type,
            message_text, response, None, user_type,
            response_time_ms=elapsed,
        )
        return

    # ─── ORIGINAL ONBOARDING: AWAITING CLASSIFICATION ───────────────
    if state == "awaiting_classification":
        classification = classify_user_type(message_text)
        if classification:
            await update_session(session_key, user_type=classification, conversation_state="active")
            response = "Great, thank you! How can I help you today?"
            await update.message.reply_text(response, **reply_kw)
            await save_message(session_key, "user", message_text)
            await save_message(session_key, "assistant", response)
            elapsed = int((time.time() - start_time) * 1000)
            await log_interaction(
                session_key, user_id, chat_id, chat_type,
                message_text, response, None, classification,
                response_time_ms=elapsed,
            )
            return

        if not is_greeting(message_text):
            await update_session(session_key, conversation_state="active", user_type=user_type or "individual")
            user_type = user_type or "individual"
            # Fall through to active state
        else:
            response = "Are you an Individual or a Business?"
            await update.message.reply_text(response, reply_markup=get_user_type_keyboard(), **reply_kw)
            elapsed = int((time.time() - start_time) * 1000)
            await log_interaction(
                session_key, user_id, chat_id, chat_type,
                message_text, response, None, user_type,
                response_time_ms=elapsed,
            )
            return

    # ─── ESCALATED STATE ────────────────────────────────────────────
    if state == "escalated":
        new_intent = detect_intent(message_text, user_type)
        recent = await get_recent_intents(session_key, limit=1)
        if recent and new_intent != recent[0] and new_intent != "escalation":
            await update_session(session_key, conversation_state="active")
        else:
            response = (
                "Your concern has been escalated to our support team. If you have "
                "a new question, feel free to ask. Otherwise, the team will follow "
                f"up with you at {SUPPORT_LINK}."
            )
            await update.message.reply_text(response, **reply_kw)
            elapsed = int((time.time() - start_time) * 1000)
            await log_interaction(
                session_key, user_id, chat_id, chat_type,
                message_text, response, "escalation", user_type,
                response_time_ms=elapsed,
            )
            return

    # ─── ACTIVE STATE ───────────────────────────────────────────────

    # If user asks for status check while in active state, start the flow
    if _wants_status_check(message_text):
        available, reason = _status_feature_available()
        if not available:
            response = (
                "I can't check onboarding status right now because required "
                f"credentials are missing ({reason}). Please contact support: {SUPPORT_LINK}"
            )
            await update_session(session_key, conversation_state="active")
            await update.message.reply_text(response, **reply_kw)
            return
        verified_email = await get_verified_email(user_id)
        if verified_email:
            response = (
                f"I have your verified email: {verified_email}\n\n"
                "Would you like to check status with this email? Reply 'yes' or enter a different email."
            )
            await update_session(session_key, conversation_state="status_confirm_email")
            await update.message.reply_text(response, **reply_kw)
            return
        else:
            response = "Sure! Please enter your email address to check your onboarding status."
            await update_session(session_key, conversation_state="status_awaiting_email")
            await update.message.reply_text(response, **reply_kw)
            return

    # Check cache
    cached = get_cached_response(message_text, user_type)
    if cached:
        await update.message.reply_text(cached, **reply_kw)
        elapsed = int((time.time() - start_time) * 1000)
        await save_message(session_key, "user", message_text)
        await save_message(session_key, "assistant", cached)
        await log_interaction(
            session_key, user_id, chat_id, chat_type,
            message_text, cached, "general", user_type,
            was_cached=True, response_time_ms=elapsed,
        )
        return

    # Detect intent
    detected_intent = detect_intent(message_text, user_type)
    logger.info("Detected intent=%s for user %s", detected_intent, user_id)

    # Check for auto-escalation triggers
    is_repeat_failure = False
    should_escalate = detected_intent == "escalation"

    if not should_escalate:
        lower_msg = message_text.lower()
        if any(kw in lower_msg for kw in _ESCALATION_KEYWORDS):
            should_escalate = True

    if not should_escalate:
        if detected_intent != "general":
            recent_intents = await get_recent_intents(session_key, limit=2)
            if len(recent_intents) >= 2 and all(i == detected_intent for i in recent_intents):
                should_escalate = True
                is_repeat_failure = True

    # Handle escalation
    if should_escalate:
        await save_message(session_key, "user", message_text)
        ticket_id, esc_response = await handle_escalation(
            session_key, user_id, chat_id, user_type,
            detected_intent, is_repeat_failure,
        )
        esc_response = sanitize_response(esc_response)
        await save_message(session_key, "assistant", esc_response)
        await update.message.reply_text(esc_response, **reply_kw)
        elapsed = int((time.time() - start_time) * 1000)
        await log_interaction(
            session_key, user_id, chat_id, chat_type,
            message_text, esc_response, detected_intent, user_type,
            was_escalated=True, response_time_ms=elapsed,
        )
        return

    # Build conversation history and call Claude AI
    history = await get_conversation_history(session_key, limit=10)
    system_prompt = get_system_prompt(user_type or "unknown", SUPPORT_LINK, detected_intent)

    logger.info("Calling Claude API for user %s (intent=%s)", user_id, detected_intent)
    ai_response = await get_ai_response(system_prompt, history, message_text)
    ai_response = sanitize_response(ai_response)
    logger.info("AI response for user %s: %s", user_id, ai_response[:80])

    await save_message(session_key, "user", message_text)
    await save_message(session_key, "assistant", ai_response)

    await update.message.reply_text(ai_response, **reply_kw)
    elapsed = int((time.time() - start_time) * 1000)
    await log_interaction(
        session_key, user_id, chat_id, chat_type,
        message_text, ai_response, detected_intent, user_type,
        response_time_ms=elapsed,
    )


# ─── HELPER FUNCTIONS ───────────────────────────────────────────────


async def _send_otp_and_transition(
    update: Update, session_key: str, user_id: int, chat_id: int,
    chat_type: str, email: str, start_time: float, reply_kw: dict,
) -> None:
    """Generate OTP, send it via email, and transition to awaiting_otp state."""
    otp_code = generate_otp()
    await store_otp(email, otp_code)

    sent = await send_otp_email(email, otp_code)
    if sent:
        response = (
            f"I've sent a 6-digit verification code to {email}.\n\n"
            "Please enter the code here. It expires in 5 minutes.\n"
            "Type 'resend' if you need a new code."
        )
        await update_session(session_key, conversation_state="status_awaiting_otp")
    else:
        response = (
            "I wasn't able to send the verification email. Please check your email "
            "address and try again, or contact our support team."
        )
        await update_session(session_key, conversation_state="active")

    await update.message.reply_text(response, **reply_kw)
    elapsed = int((time.time() - start_time) * 1000)
    await log_interaction(
        session_key, user_id, chat_id, chat_type,
        f"[email: {email}]", response, "status_check", None,
        response_time_ms=elapsed,
    )


async def _fetch_and_send_status(
    update: Update, session_key: str, user_id: int, chat_id: int,
    chat_type: str, email: str, start_time: float, reply_kw: dict,
) -> None:
    """Look up the user's onboarding status from SumSub and send the result."""
    applicant = await search_applicant_by_email(email)

    if not applicant:
        response = (
            f"I couldn't find an account associated with {email} in our system.\n\n"
            "Please make sure you're using the same email you registered with on Endl. "
            f"If you need help, contact our support team: {SUPPORT_LINK}"
        )
        await update_session(session_key, conversation_state="active")
        await update.message.reply_text(response, **reply_kw)
        elapsed = int((time.time() - start_time) * 1000)
        await log_interaction(
            session_key, user_id, chat_id, chat_type,
            f"[status check: {email}]", response, "status_check", None,
            response_time_ms=elapsed,
        )
        return

    applicant_id = applicant.get("id") or applicant.get("applicantId", "")

    # Fetch detailed status and document status
    full_applicant = await get_applicant_status(applicant_id) if applicant_id else None
    doc_status = await get_document_status(applicant_id) if applicant_id else None

    # Use the full applicant data if available, otherwise use the search result
    status_data = full_applicant or applicant
    response = format_status_message(status_data, doc_status)

    await update_session(session_key, conversation_state="active")
    await update.message.reply_text(response, **reply_kw)

    elapsed = int((time.time() - start_time) * 1000)
    await log_interaction(
        session_key, user_id, chat_id, chat_type,
        f"[status check: {email}]", response, "status_check", None,
        response_time_ms=elapsed,
    )
