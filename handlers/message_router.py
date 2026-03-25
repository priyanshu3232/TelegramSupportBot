"""
Text message router for the Endl Support Bot.
Most content flows are button-driven (see callback_handler.py).
This module handles only cases that require free-text input:
  - Greetings / /start → welcome with account-type buttons
  - status_awaiting_email → validate email, send OTP
  - status_awaiting_otp  → verify OTP code
  - awaiting_flag_query  → capture support flag text
  - General fallback     → frustration detection, menu prompt
"""
import logging
import re
import time
import traceback

from telegram import Update
from telegram.ext import ContextTypes

from config import SUPPORT_LINK, SMTP_USER, SMTP_PASSWORD
from database.models import (
    get_or_create_session, update_session, save_message,
    save_verified_user, get_verified_email, get_conversation_history,
)
from handlers.greeting import is_greeting
from utils.keyboards import (
    KB_ACCOUNT_TYPE, kb_main, KB_SUPPORT, KB_OTP_RESEND_OPTIONS,
    KB_OTP_EXPIRED, KB_OTP_LOCKED, KB_URGENCY, kb_back, _mk,
    get_kb_by_name,
)
from ai.claude_client import get_freetext_response, get_ai_response
from ai.system_prompt import get_group_system_prompt
from utils.otp import generate_otp, store_otp, verify_otp, cancel_otp, send_otp_email
from utils.rate_limiter import is_rate_limited

logger = logging.getLogger(__name__)

_EMAIL_REGEX = re.compile(r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$")
_EMAIL_FIND  = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}")

_FRUSTRATION_KEYWORDS = [
    "waiting for weeks", "taking too long", "this is urgent", "need this today",
    "nobody is helping", "this is unacceptable", "still waiting", "no response",
    "been waiting", "help me now", "urgent", "asap", "immediately",
]

_STATUS_KEYWORDS = [
    "check my status", "what's my status", "kyc status", "kyb status",
    "has my account been approved", "is my account active", "my documents",
    "verification status", "onboarding status", "my application", "am i verified",
    "is my account ready", "did you get my documents", "check status",
]

_MENU_KEYWORDS = ["menu", "back", "start over", "restart", "main menu", "home"]


def _smtp_ok() -> bool:
    return bool(SMTP_USER and SMTP_PASSWORD)


def _is_frustrated(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in _FRUSTRATION_KEYWORDS)


def _wants_status(text: str) -> bool:
    lower = text.lower()
    return any(kw in lower for kw in _STATUS_KEYWORDS)


def _wants_menu(text: str) -> bool:
    lower = text.lower().strip()
    return any(kw in lower for kw in _MENU_KEYWORDS)


# ── Entry points ──────────────────────────────────────────────────────

async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat or not update.message:
        return

    # Group handler passes cleaned text via context
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

    user_id  = user.id
    chat_id  = chat.id
    chat_type = chat.type
    session_key = f"{chat_id}_{user_id}"
    reply_kw = {"reply_to_message_id": reply_to_msg_id} if reply_to_msg_id else {}

    if is_rate_limited(user_id):
        await update.message.reply_text(
            "You're sending messages too quickly — please wait a moment and try again.",
            **reply_kw,
        )
        return

    try:
        await _route(update, user_id, chat_id, chat_type, message_text, session_key, reply_kw)
    except Exception as exc:
        logger.error("Error for user %s: %s\n%s", user_id, exc, traceback.format_exc())
        try:
            await update_session(session_key, conversation_state="active")
        except Exception:
            pass
        try:
            await update.message.reply_text(
                "Something went wrong on my end. Please try again or reach out to "
                f"our live support: {SUPPORT_LINK}",
                **reply_kw,
            )
        except Exception:
            pass


async def handle_non_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle images, stickers, files, etc. (Step 13)."""
    if not update.message:
        return
    user = update.effective_user
    chat = update.effective_chat
    if not user or not chat:
        return
    session = await get_or_create_session(chat.id, user.id)
    account_type = session.get("user_type") or "individual"
    await update.message.reply_text(
        "I can only process text messages at the moment. "
        "If you have a document-related query, please describe it and I'll do my best to help.",
        reply_markup=kb_back(),
    )


# ── Core router ───────────────────────────────────────────────────────

async def _route(
    update: Update,
    user_id: int,
    chat_id: int,
    chat_type: str,
    text: str,
    session_key: str,
    reply_kw: dict,
) -> None:
    start_time = time.time()
    session = await get_or_create_session(chat_id, user_id)
    state = session.get("conversation_state", "greeting")
    account_type = session.get("user_type") or "individual"

    # ── GROUP CHAT — conversational mode, no buttons ────────────────
    is_group = chat_type in ("group", "supergroup")
    if is_group:
        history = await get_conversation_history(session_key, limit=6)
        group_reply = await get_ai_response(get_group_system_prompt(), history, text)
        await save_message(session_key, "user", text)
        await update.message.reply_text(group_reply, **reply_kw)
        await save_message(session_key, "assistant", group_reply)
        return

    # ── GREETING / FIRST MESSAGE ────────────────────────────────────
    if state == "active" and is_greeting(text):
        # Greeting in an active session → welcome back to Step 0
        await update.message.reply_text(
            "\U0001f44b Welcome to <b>Endl Support</b>!\n"
            "I'm here to help with your account, onboarding status, payments, and more.\n\n"
            "Are you using Endl as an <b>Individual</b> or a <b>Business</b>?",
            reply_markup=KB_ACCOUNT_TYPE,
            parse_mode="HTML",
            **reply_kw,
        )
        return

    if state == "greeting":
        await update_session(session_key, conversation_state="active")
        if is_greeting(text):
            # Pure greeting → Step 0 welcome
            await update.message.reply_text(
                "\U0001f44b Welcome to <b>Endl Support</b>!\n"
                "I'm here to help with your account, onboarding status, payments, and more.\n\n"
                "Are you using Endl as an <b>Individual</b> or a <b>Business</b>?",
                reply_markup=KB_ACCOUNT_TYPE,
                parse_mode="HTML",
                **reply_kw,
            )
        else:
            # First message has clear intent — answer it then ask account type
            result = await get_freetext_response(text, None, [])
            intent = result.get("intent", "unknown")
            reply = result.get("reply", "")
            acct_hint = result.get("account_type_hint")
            if acct_hint in ("individual", "business"):
                await update_session(session_key, user_type=acct_hint)
                account_type = acct_hint
            if intent in ("greeting", "menu") or not reply:
                await update.message.reply_text(
                    "\U0001f44b Welcome to <b>Endl Support</b>!\n"
                    "I'm here to help with your account, onboarding status, payments, and more.\n\n"
                    "Are you using Endl as an <b>Individual</b> or a <b>Business</b>?",
                    reply_markup=KB_ACCOUNT_TYPE,
                    parse_mode="HTML",
                    **reply_kw,
                )
            else:
                await save_message(session_key, "user", text)
                await update.message.reply_text(reply, **reply_kw)
                await save_message(session_key, "assistant", reply)
                await update.message.reply_text(
                    "Before I pull that up — are you an <b>Individual</b> or a <b>Business</b> user?",
                    reply_markup=KB_ACCOUNT_TYPE,
                    parse_mode="HTML",
                    **reply_kw,
                )
        return

    # ── STATUS CHECK: AWAITING EMAIL ────────────────────────────────
    if state == "status_awaiting_email":
        found = _EMAIL_FIND.findall(text)

        if len(found) > 1:
            await update.message.reply_text(
                "I can see a couple of email addresses there — which one did you use to "
                "register with Endl?",
                **reply_kw,
            )
            return

        email_input = (found[0] if found else text).strip().lower()

        if not _EMAIL_REGEX.match(email_input):
            await update.message.reply_text(
                "That doesn't look like a valid email address. "
                "Could you double-check and re-enter it?",
                **reply_kw,
            )
            return

        await update_session(session_key, email=email_input)
        await _send_otp(update, session_key, user_id, chat_id, chat_type,
                        email_input, start_time, reply_kw)
        return

    # ── STATUS CHECK: AWAITING OTP ──────────────────────────────────
    if state == "status_awaiting_otp":
        email = session.get("email", "")
        lower = text.lower().strip()

        # Change email
        if any(p in lower for p in ("change email", "wrong email", "different email", "cancel")):
            await cancel_otp(email, user_id)
            await update_session(session_key, conversation_state="status_awaiting_email",
                                 email=None)
            await update.message.reply_text(
                "No problem — could you share the correct email address?\n\n"
                "📧 Please enter your registered email.",
                **reply_kw,
            )
            return

        # Resend
        if lower in ("resend", "new code", "resend otp", "resend code", "send again", "yes"):
            await _send_otp(update, session_key, user_id, chat_id, chat_type,
                            email, start_time, reply_kw)
            return

        # Non-6-digit input
        if not re.match(r"^\d{6}$", text.strip()):
            await update.message.reply_text(
                "I was expecting a 6-digit verification code — what you sent doesn't look "
                "quite right. Could you check your email and share just the 6-digit number?",
                **reply_kw,
            )
            return

        # Verify
        success, msg, reason = await verify_otp(email, user_id, text.strip())

        if success:
            await save_verified_user(chat_id, user_id, email)
            await update.message.reply_text(
                "\u2705 Identity verified successfully!\n"
                "Let me fetch your onboarding status now — one moment\u2026",
                **reply_kw,
            )
            await _status_placeholder(update, session_key, email, reply_kw)

        elif reason == "expired":
            await update.message.reply_text(
                "It looks like that code has expired (codes are only valid for 10 minutes). "
                "Shall I send you a fresh one?",
                reply_markup=_mk(
                    [("Yes, send new code", "otp:resend"), ("No, cancel", "nav:back")]
                ),
                **reply_kw,
            )
        elif reason == "locked":
            await update_session(session_key, conversation_state="active")
            await update.message.reply_text(
                "I'm sorry — your verification session has been locked after multiple incorrect "
                "attempts. This is a security measure to protect your account.\n\n"
                "Please contact our support team directly for assistance.",
                reply_markup=_mk([("🎧 Contact support now", "nav:support")]),
                **reply_kw,
            )
        else:
            # invalid — show remaining attempts + options
            await update.message.reply_text(msg, reply_markup=KB_OTP_RESEND_OPTIONS, **reply_kw)
        return

    # ── SUPPORT FLAG: AWAITING TEXT ─────────────────────────────────
    if state == "awaiting_flag_query":
        await update_session(session_key, conversation_state="active")
        await update.message.reply_text(
            "Got it. Your query has been flagged and our onboarding team will review it and "
            "follow up with you within 1 business day.\n\nIs there anything else I can help with?",
            reply_markup=kb_main(account_type),
            **reply_kw,
        )
        return

    # ── ACTIVE STATE — Free-text via Claude ──────────────────────────

    # Fast paths that don't need an API call
    if _wants_menu(text):
        await update_session(session_key, unrecognized_count=0)
        await update.message.reply_text(
            _main_label(account_type),
            reply_markup=kb_main(account_type),
            **reply_kw,
        )
        return

    # Call Claude for intent detection + natural reply
    history = await get_conversation_history(session_key, limit=6)
    result = await get_freetext_response(text, account_type, history)

    intent            = result.get("intent", "unknown")
    reply             = result.get("reply", "")
    buttons_name      = result.get("buttons", "main_menu")
    acct_hint         = result.get("account_type_hint")

    # Account type switch mid-session
    if intent == "account_switch" and acct_hint in ("individual", "business"):
        account_type = acct_hint
        await update_session(session_key, user_type=acct_hint, unrecognized_count=0)
        await save_message(session_key, "user", text)
        await update.message.reply_text(
            reply or _main_label(acct_hint),
            reply_markup=kb_main(acct_hint),
            **reply_kw,
        )
        await save_message(session_key, "assistant", reply or _main_label(acct_hint))
        return

    # Apply account type hint if we don't have one yet
    if acct_hint and acct_hint in ("individual", "business") and not session.get("user_type"):
        account_type = acct_hint
        await update_session(session_key, user_type=acct_hint)

    # Track frustration
    if intent == "frustration":
        frustration_count = (session.get("frustration_count") or 0) + 1
        await update_session(session_key, frustration_count=frustration_count)
        if frustration_count >= 2 and buttons_name != "urgency":
            buttons_name = "urgency"

    # Greeting — show welcome, don't show a reply
    if intent == "greeting":
        await update.message.reply_text(
            "\U0001f44b Welcome to <b>Endl Support</b>!\n"
            "I'm here to help with your account, onboarding status, payments, and more.\n\n"
            "Are you using Endl as an <b>Individual</b> or a <b>Business</b>?",
            reply_markup=KB_ACCOUNT_TYPE,
            parse_mode="HTML",
            **reply_kw,
        )
        return

    # Menu / back — already handled above but catch it from Claude too
    if intent == "menu":
        await update_session(session_key, unrecognized_count=0)
        await update.message.reply_text(
            _main_label(account_type),
            reply_markup=kb_main(account_type),
            **reply_kw,
        )
        return

    # Resolve keyboard
    kb = get_kb_by_name(buttons_name, account_type)

    # For status_flow intent, check if email is already verified (Step 11)
    if intent in ("check_status", "frustration") and buttons_name == "status_flow":
        if not _smtp_ok():
            reply = (
                "I'm unable to check your status right now due to a configuration issue. "
                f"Please contact our support team: {SUPPORT_LINK}"
            )
            kb = kb_main(account_type)
        else:
            verified_email = await get_verified_email(user_id)
            if verified_email:
                # Step 11: already verified — skip email/OTP, go straight to status fetch
                await update_session(session_key, email=verified_email)
                await save_message(session_key, "user", text)
                if reply:
                    await update.message.reply_text(reply, **reply_kw)
                await update.message.reply_text(
                    f"I already have your verified email on file as <b>{verified_email}</b>. "
                    "Let me check your status again.",
                    parse_mode="HTML",
                    **reply_kw,
                )
                await _status_placeholder(update, session_key, verified_email, reply_kw)
                return

    # Send the reply + buttons
    if reply:
        await save_message(session_key, "user", text)
        await update.message.reply_text(reply, reply_markup=kb, **reply_kw)
        await save_message(session_key, "assistant", reply)
    else:
        # No reply (shouldn't happen but fallback gracefully)
        await update.message.reply_text(
            _main_label(account_type), reply_markup=kb_main(account_type), **reply_kw
        )

    # Reset unrecognized counter on successful match
    if intent != "unknown":
        await update_session(session_key, unrecognized_count=0)
    else:
        unrecognized_count = (session.get("unrecognized_count") or 0) + 1
        await update_session(session_key, unrecognized_count=unrecognized_count)
        if unrecognized_count >= 2:
            await update_session(session_key, unrecognized_count=0)
            await update.message.reply_text(
                "I didn't quite catch that — let me take you back to the main menu.",
                reply_markup=kb_main(account_type),
                **reply_kw,
            )


# ── OTP helpers ───────────────────────────────────────────────────────

async def _send_otp(
    update: Update,
    session_key: str,
    user_id: int,
    chat_id: int,
    chat_type: str,
    email: str,
    start_time: float,
    reply_kw: dict,
) -> None:
    otp_code = generate_otp()
    stored = await store_otp(email, user_id, otp_code)

    if not stored:
        await update.message.reply_text(
            "You've reached the maximum number of resend attempts for security reasons. "
            "Please wait 15 minutes before trying again, or contact our support team.",
            reply_markup=_mk([("🎧 Contact support", "nav:support")]),
            **reply_kw,
        )
        return

    sent = await send_otp_email(email, otp_code)
    if sent:
        await update.message.reply_text(
            f"Thank you! I've sent a <b>6-digit verification code</b> to:\n📧 <b>{email}</b>\n\n"
            "Please check your inbox (and spam folder, just in case) and share the code here.\n"
            "<i>The code is valid for 10 minutes.</i>",
            reply_markup=_mk([("Change my email", "otp:change_email")]),
            parse_mode="HTML",
            **reply_kw,
        )
        await update_session(session_key, conversation_state="status_awaiting_otp")
    else:
        await update.message.reply_text(
            "I wasn't able to send the verification email. Please check the address and try "
            "again, or contact our support team.",
            reply_markup=_mk([("🎧 Contact support", "nav:support"),
                               ("← Back to menu", "nav:back")]),
            **reply_kw,
        )
        await update_session(session_key, conversation_state="active")


async def _status_placeholder(
    update: Update,
    session_key: str,
    email: str,
    reply_kw: dict,
) -> None:
    """
    Placeholder response shown after OTP verification until Sumsub is live.
    Replace this function body when the Sumsub endpoint is ready.
    """
    await update.message.reply_text(
        "I'm sorry — our verification system is temporarily unavailable. "
        "This is a known issue on our end and is being resolved.\n\n"
        "Here's what I can do for you right now:",
        reply_markup=_mk(
            [("🚩 Flag query for onboarding team", "status:flag")],
            [("📋 View general onboarding info", "status:info")],
            [("👤 Connect me to a live agent", "nav:support")],
        ),
        **reply_kw,
    )
    await update_session(session_key, conversation_state="active")


def _main_label(account_type: str) -> str:
    if account_type == "business":
        return "Got it! Here's how I can help your business today \U0001f447"
    return "Got it! Here's how I can help you today \U0001f447"
