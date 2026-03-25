"""
Handles all InlineKeyboardButton callback queries.
Every callback_data prefix maps to a handler block below.
"""
import logging

from telegram import Update, InlineKeyboardMarkup
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from config import SUPPORT_LINK, SMTP_USER, SMTP_PASSWORD
from database.models import (
    get_or_create_session, update_session,
    save_verified_user, get_verified_email,
)
from utils.keyboards import (
    _mk, kb_main, kb_ask_back, kb_back, kb_support_back, kb_status_support_back,
    KB_ABOUT, KB_CURRENCIES, KB_PAY_IND, KB_PAY_BIZ,
    KB_ONBOARDING, KB_CARD, KB_SECURITY_IND, KB_SECURITY_BIZ, KB_SUPPORT,
    KB_OTP_RESEND_OPTIONS,
)
from utils.otp import generate_otp, store_otp, send_otp_email, cancel_otp

logger = logging.getLogger(__name__)


# ── Helpers ──────────────────────────────────────────────────────────

async def _edit(
    query,
    text: str,
    markup: InlineKeyboardMarkup | None = None,
    parse_mode: str = "HTML",
) -> None:
    """Edit the original button message, suppressing 'not modified' errors."""
    try:
        await query.edit_message_text(text, reply_markup=markup, parse_mode=parse_mode)
    except BadRequest as e:
        if "Message is not modified" not in str(e):
            logger.warning("edit_message_text failed: %s", e)


def _main_text(account_type: str) -> str:
    if account_type == "business":
        return "Got it! Here's how I can help your business today \U0001f447"
    return "Got it! Here's how I can help you today \U0001f447"


def _smtp_ok() -> bool:
    return bool(SMTP_USER and SMTP_PASSWORD)


# ── Entry point ───────────────────────────────────────────────────────

async def handle_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()

    data = query.data or ""
    user = update.effective_user
    chat = update.effective_chat

    if not user or not chat:
        return

    user_id = user.id
    chat_id = chat.id
    session_key = f"{chat_id}_{user_id}"

    session = await get_or_create_session(chat_id, user_id)
    account_type = session.get("user_type") or "individual"

    # ── ACCOUNT TYPE ─────────────────────────────────────────────────
    if data.startswith("acct:"):
        t = data[5:]
        await update_session(session_key, user_type=t, conversation_state="active",
                             unrecognized_count=0)
        await _edit(query, _main_text(t), kb_main(t))
        return

    # ── NAVIGATION ───────────────────────────────────────────────────
    if data.startswith("nav:"):
        dest = data[4:]

        if dest == "back":
            await update_session(session_key, conversation_state="active",
                                 unrecognized_count=0)
            await _edit(query, _main_text(account_type), kb_main(account_type))
            return

        nav_map = {
            "about":     ("What would you like to know about Endl?", KB_ABOUT),
            "currencies": ("What would you like to know about currencies and fees?", KB_CURRENCIES),
            "pay_ind":   ("What would you like to know about payments?", KB_PAY_IND),
            "pay_biz":   ("What would you like to know about payments and SWIFT?", KB_PAY_BIZ),
            "onboarding": ("What would you like to know about onboarding?", KB_ONBOARDING),
            "card":      ("What would you like to know about corporate cards?", KB_CARD),
            "support":   ("I'm here to help! How would you like to proceed?", KB_SUPPORT),
        }
        if dest in nav_map:
            text, kb = nav_map[dest]
            await _edit(query, text, kb)
            return

        if dest == "security":
            kb = KB_SECURITY_BIZ if account_type == "business" else KB_SECURITY_IND
            await _edit(query, "What would you like to know about security?", kb)
            return

        logger.warning("Unhandled nav dest: %s", dest)
        await _edit(query, _main_text(account_type), kb_main(account_type))
        return

    # ── ABOUT ENDL (Step 2) ──────────────────────────────────────────
    if data.startswith("about:"):
        key = data[6:]
        answers = {
            "what_is": (
                "Endl is a global business payments platform. You can collect payments locally, "
                "hold funds in multiple currencies, convert between fiat and stablecoins, and send "
                "global payouts — all from one dashboard."
            ),
            "who": (
                "Endl is designed for businesses and individuals who receive local payments or send "
                "international payments — including startups, agencies, SaaS companies, trading "
                "firms, and global service providers."
            ),
            "countries": (
                "Endl supports businesses operating globally. Availability depends on compliance "
                "checks and regulatory requirements. Businesses in globally sanctioned countries "
                "are not supported. Your jurisdiction is verified during onboarding."
            ),
            "regulated": (
                "Yes. Endl holds relevant licences and operates in partnership with regulated "
                "financial institutions. The platform follows strict compliance frameworks including "
                "AML screening, transaction monitoring, and KYC/KYB verification."
            ),
            "different": (
                "Endl combines multi-currency business accounts with stablecoin settlement "
                "infrastructure. This means faster global transfers, lower FX costs, and the "
                "ability to move between fiat currencies and digital dollars (USDC/USDT) when needed."
            ),
        }
        if key in answers:
            await _edit(query, answers[key], kb_ask_back("about"))
        return

    # ── CURRENCIES & FEES (Step 3) ───────────────────────────────────
    if data.startswith("curr:"):
        key = data[5:]
        if key == "supported":
            await _edit(
                query,
                "Endl supports: <b>USD, EUR, AED, GBP, BRL, and MXN</b> — along with stablecoins "
                "<b>USDC and USDT</b>. More currencies and local rails are continuously being added.",
                kb_ask_back("currencies"),
            )
        elif key == "fees":
            await _edit(
                query,
                "Typical transaction fees are approximately <b>0.5% per deposit or withdrawal "
                "transaction</b>. Full pricing is shared once your account is approved.",
                kb_ask_back("currencies"),
            )
        elif key == "fx":
            await _edit(
                query,
                "FX conversion fees depend on the currency pair. Detailed pricing is shared once "
                "your account is approved. For specifics, our support team can assist.",
                _mk(
                    [("Ask another question", "nav:currencies"),
                     ("🎧 Talk to support", "nav:support")],
                    [("← Back to menu", "nav:back")],
                ),
            )
        elif key == "stablecoins":
            await _edit(
                query,
                "Endl supports <b>USDC and USDT</b>. You can convert between fiat currencies and "
                "digital dollars directly within the dashboard.",
                kb_ask_back("currencies"),
            )
        return

    # ── PAYMENTS — INDIVIDUAL (Step 4) ───────────────────────────────
    if data.startswith("payi:"):
        key = data[5:]
        answers = {
            "receive": None,  # handled separately below for custom buttons
            "virtual": (
                "Virtual accounts give your business local bank account details in supported "
                "currencies (e.g. USD, EUR). Your clients send payments as if to a local bank — "
                "no international wires needed."
            ),
            "convert": (
                "Funds can be converted directly within the Endl dashboard between supported fiat "
                "currencies and stablecoins (USDC/USDT)."
            ),
            "payouts": (
                "Yes. Endl allows you to send payouts to partners or vendors across multiple "
                "countries from your dashboard."
            ),
            "time": None,  # handled separately below for custom buttons
        }
        if key == "receive":
            await _edit(
                query,
                "Once your account is active, generate virtual account details directly from your "
                "Endl dashboard. Share these with your clients to receive local bank transfers.",
                _mk(
                    [("What are virtual accounts?", "payi:virtual"),
                     ("← Back to menu", "nav:back")],
                ),
            )
        elif key == "time":
            await _edit(
                query,
                "Withdrawal times depend on the destination currency and payment rail. Some "
                "transfers settle instantly; others may take <b>1–3 business days</b>.",
                _mk(
                    [("What payment rails are supported?", "payi:rails"),
                     ("Ask another question", "nav:pay_ind"),
                     ("← Back to menu", "nav:back")],
                ),
            )
        elif key == "rails":
            await _edit(
                query,
                "Supported receiving rails by currency:\n"
                "• <b>USD</b> — ACH and Fedwire\n"
                "• <b>EUR</b> — SEPA and SEPA Instant\n"
                "• <b>GBP</b> — Faster Payments (FPS)\n"
                "• <b>BRL</b> — PIX\n"
                "• <b>MXN</b> — SPEI or CLABE\n"
                "• <b>AED</b> — Local UAE bank transfer\n\n"
                "Incoming SWIFT is not supported.",
                kb_ask_back("pay_ind"),
            )
        elif key == "delayed":
            await _edit(
                query,
                "Most delays are caused by banking processing times or compliance checks. "
                "If your payment hasn't arrived within the expected timeframe, please contact "
                "support with the transaction details.",
                _mk([("🎧 Contact support now", "nav:support"), ("← Back to menu", "nav:back")]),
            )
        elif key in answers and answers[key] is not None:
            await _edit(query, answers[key], kb_ask_back("pay_ind"))
        return

    # ── PAYMENTS — BUSINESS / SWIFT (Step 5) ─────────────────────────
    if data.startswith("payb:"):
        key = data[5:]
        if key == "swift_in":
            await _edit(
                query,
                "❌ Endl accounts do not currently support <b>incoming SWIFT deposits</b>. "
                "Please use the payment rails shown in your virtual account details inside the "
                "dashboard.",
                _mk(
                    [("What rails are supported?", "payb:rails"),
                     ("← Back to menu", "nav:back")],
                ),
            )
        elif key == "swift_out":
            await _edit(
                query,
                "✅ Yes. SWIFT transfers are supported for <b>third-party business payments</b> "
                "only. SWIFT cannot be used to send to individual personal accounts.",
                kb_ask_back("pay_biz"),
            )
        elif key == "rails":
            await _edit(
                query,
                "Supported rails by currency:\n"
                "• <b>USD</b> — ACH and Fedwire\n"
                "• <b>EUR</b> — SEPA\n"
                "• <b>GBP</b> — Faster Payments (FPS)\n"
                "• <b>BRL</b> — PIX\n"
                "• <b>MXN</b> — SPEI or CLABE\n"
                "• <b>AED</b> — Local UAE bank transfer\n"
                "• <b>SWIFT outgoing</b> — B2B third-party payments only",
                kb_ask_back("pay_biz"),
            )
        elif key == "time":
            await _edit(
                query,
                "Withdrawal times depend on the destination currency and payment rail. Some "
                "transfers settle instantly; others may take <b>1–3 business days</b>.",
                kb_ask_back("pay_biz"),
            )
        elif key == "delayed":
            await _edit(
                query,
                "Please contact our support team with your <b>transaction reference number</b> "
                "and the expected settlement date. Most delays are caused by banking processing "
                "times or compliance checks.",
                _mk([("🎧 Contact support now", "nav:support"), ("← Back to menu", "nav:back")]),
            )
        return

    # ── ONBOARDING & DOCUMENTS (Step 6) ──────────────────────────────
    if data.startswith("onb:"):
        key = data[4:]
        if key == "docs":
            await _edit(
                query,
                "For business onboarding, you will need:\n"
                "📄 Company registration documents\n"
                "👥 Shareholder details\n"
                "📜 Articles or Memorandum of Association\n"
                "🔎 UBO identity verification\n"
                "🌐 Proof of business activity (website, invoices, or contracts)\n"
                "📝 Business description\n\n"
                "Additional documents may be requested depending on your jurisdiction.",
                _mk(
                    [("🔍 Check my KYB status", "status:check"),
                     ("Ask another question", "nav:onboarding")],
                    [("← Back to menu", "nav:back")],
                ),
            )
        elif key == "time":
            await _edit(
                query,
                "KYB verification typically takes <b>2–4 business days</b> after all required "
                "documents are submitted. Individual KYC is usually <b>1 business day</b>. "
                "Exact timelines may vary depending on document completeness and compliance checks.",
                _mk(
                    [("🔍 Check my KYB status", "status:check")],
                    [("← Back to menu", "nav:back")],
                ),
            )
        elif key == "delayed":
            await _edit(
                query,
                "Some applications require additional compliance checks or partner bank review. "
                "If our compliance team needs more information, they will contact you directly.\n\n"
                "If you'd like to check your current status:",
                kb_status_support_back(),
            )
        elif key == "failed":
            await _edit(
                query,
                "Verification may fail if documents are unclear, incomplete, or expired. Please "
                "resubmit clear, valid documents. Our support team can guide you on exactly what "
                "to resubmit.",
                kb_support_back(),
            )
        elif key == "poa":
            await _edit(
                query,
                "Please resubmit a valid proof of address — a <b>utility bill or bank statement "
                "dated within the last 3 months</b>. Make sure the document clearly shows your "
                "name and address.",
                kb_support_back(),
            )
        elif key == "progress":
            await _edit(
                query,
                "Once your documents are submitted, they are first reviewed by the Endl compliance "
                "team. After approval, the application is forwarded to our partner banks to open "
                "your virtual accounts. Your status will update to <b>Verification Successful</b> "
                "only after the partner bank approves.",
                _mk(
                    [("🔍 Check my KYB status", "status:check"),
                     ("🎧 Talk to support", "nav:support")],
                    [("← Back to menu", "nav:back")],
                ),
            )
        elif key == "update":
            await _edit(
                query,
                "Yes — if you need to update any submitted information, please contact our support "
                "team and the onboarding team will assist you.",
                kb_support_back(),
            )
        elif key == "hear":
            await _edit(
                query,
                "You will receive a notification in your <b>account dashboard</b> once "
                "verification is completed and your account is ready to use.",
                _mk(
                    [("🔍 Check my KYB status", "status:check")],
                    [("← Back to menu", "nav:back")],
                ),
            )
        return

    # ── CORPORATE CARD (Step 7) ───────────────────────────────────────
    if data.startswith("card:"):
        key = data[5:]
        if key == "offered":
            await _edit(
                query,
                "Yes! Endl offers corporate cards for managing company expenses, subscriptions, "
                "and employee spending — with customisable limits and controls.",
                _mk(
                    [("How do I issue cards for my team?", "card:issue"),
                     ("← Back to menu", "nav:back")],
                ),
            )
        elif key == "issue":
            await _edit(
                query,
                "Multiple corporate cards can be issued directly from your Endl dashboard. Each "
                "card can be assigned to a team member with individual spending controls.",
                _mk(
                    [("Can I set spending limits per card?", "card:limits"),
                     ("← Back to menu", "nav:back")],
                ),
            )
        elif key == "limits":
            await _edit(
                query,
                "Yes — you can set customisable spending limits and controls per employee or per "
                "department from the dashboard.",
                kb_ask_back("card"),
            )
        elif key == "manage":
            await _edit(
                query,
                "The Endl dashboard gives you a centralised view of all card activity, with "
                "controls to adjust limits, pause cards, and review transactions.",
                kb_ask_back("card"),
            )
        elif key == "currencies":
            await _edit(
                query,
                "Cards are supported for all currencies active on your Endl account.",
                kb_ask_back("card"),
            )
        return

    # ── SECURITY (Step 8) ─────────────────────────────────────────────
    if data.startswith("sec:"):
        key = data[4:]
        answers = {
            "safe": (
                "Yes. Endl follows strict compliance and security practices including AML "
                "monitoring, KYC/KYB verification, and regulated financial partners to protect "
                "your funds."
            ),
            "data": (
                "Endl applies strict compliance frameworks and security practices to protect all "
                "personal and business data."
            ),
            "monitoring": (
                "All transactions are subject to ongoing AML screening and compliance review. "
                "Any flagged activity is reviewed by our compliance team."
            ),
        }
        if key in answers:
            await _edit(query, answers[key], kb_ask_back("security"))
        return

    # ── SUPPORT (Step 9) ──────────────────────────────────────────────
    if data.startswith("sup:"):
        key = data[4:]
        if key == "flag":
            await _edit(
                query,
                "Understood — could you briefly describe your query so our team has context "
                "when they review it?\n\n<i>Please type your message below.</i>",
                kb_back(),
            )
            await update_session(session_key, conversation_state="awaiting_flag_query")
            return

        if key == "agent":
            await _edit(
                query,
                f"Of course — please reach out to our support team directly:\n\n"
                f"👉 {SUPPORT_LINK}\n\n"
                "Feel free to describe your issue so they can assist you quickly.",
                kb_back(),
            )
            return

        if key == "help":
            await _edit(
                query,
                "You can find guides and FAQs at 👉 "
                "<a href='https://endl.io/help'>endl.io/help</a>",
                kb_back(),
            )
            return

    # ── STATUS / KYC / KYB FLOW (Step 10) ────────────────────────────
    if data.startswith("status:"):
        key = data[7:]

        if key == "check":
            if not _smtp_ok():
                await _edit(
                    query,
                    "I'm unable to verify your status right now due to a configuration issue. "
                    f"Please contact our support team directly: {SUPPORT_LINK}",
                    kb_back(),
                )
                return

            verified_email = await get_verified_email(user_id)
            if verified_email:
                # Step 11: already verified — skip email/OTP, go straight to status
                await update_session(session_key, email=verified_email)
                await _edit(
                    query,
                    f"I already have your verified email on file as <b>{verified_email}</b>. "
                    "Let me check your status again\u2026",
                )
                await _do_status_lookup(query, session_key, user_id, verified_email)
                return

            await _edit(
                query,
                "To look up your status, I need to verify your registered email address.\n\n"
                "📧 Please type the email you used when signing up with Endl.",
                None,
            )
            await update_session(session_key, conversation_state="status_awaiting_email")
            return

        if key == "use_verified":
            verified_email = await get_verified_email(user_id)
            if verified_email:
                await update_session(session_key, email=verified_email)
                await _do_status_lookup(query, session_key, user_id, verified_email)
            return

        if key == "new_email":
            email = session.get("email", "")
            if email:
                await cancel_otp(email, user_id)
            await _edit(
                query,
                "No problem — could you share the correct email address?\n\n"
                "📧 Please type your registered email.",
                None,
            )
            await update_session(session_key, conversation_state="status_awaiting_email",
                                 email=None)
            return

        if key == "flag":
            email = session.get("email", "")
            await _edit(
                query,
                f"Understood. I've flagged your query and your email <b>{email}</b> has been "
                "noted for our onboarding team. You should expect a response within 1 business "
                "day.\n\nIs there anything else I can help you with?",
                kb_back(),
            )
            await update_session(session_key, conversation_state="active")
            return

        if key == "info":
            await _edit(
                query,
                "<b>Onboarding overview:</b>\n\n"
                "<b>Individuals</b> — government-issued ID, proof of address (utility bill or "
                "bank statement, last 3 months), and a selfie. Verification: ~1 business day.\n\n"
                "<b>Businesses</b> — company registration, shareholder details, MOA/AOA, UBO "
                "verification, proof of business activity, and a business description. "
                "Verification: 2–4 business days.",
                kb_back(),
            )
            await update_session(session_key, conversation_state="active")
            return

    # ── OTP CALLBACKS ─────────────────────────────────────────────────
    if data.startswith("otp:"):
        key = data[4:]
        email = session.get("email", "")

        if key == "resend":
            if not email:
                await _edit(query, "Your session has expired. Please start over.", kb_back())
                return
            otp_code = generate_otp()
            stored = await store_otp(email, user_id, otp_code)
            if not stored:
                await _edit(
                    query,
                    "You've reached the maximum resend limit for security reasons. "
                    "Please wait <b>15 minutes</b> before trying again.",
                    _mk([("🎧 Contact support", "nav:support"),
                         ("← Back to menu", "nav:back")]),
                )
                return
            sent = await send_otp_email(email, otp_code)
            if sent:
                await _edit(
                    query,
                    f"I've resent the code to <b>{email}</b>. It's valid for 10 minutes.\n\n"
                    "Please check your inbox (and spam folder) and type the 6-digit code here.",
                    _mk([("Change my email", "otp:change_email")]),
                )
                await update_session(session_key, conversation_state="status_awaiting_otp")
            else:
                await _edit(
                    query,
                    "I wasn't able to send the email. Please try again or contact support.",
                    kb_support_back(),
                )
            return

        if key == "change_email":
            await cancel_otp(email, user_id)
            await _edit(
                query,
                "No problem — could you share the correct email address?\n\n"
                "📧 Please type your registered email.",
                None,
            )
            await update_session(session_key, conversation_state="status_awaiting_email",
                                 email=None)
            return

    logger.warning("Unhandled callback data: %s", data)
    await _edit(query, _main_text(account_type), kb_main(account_type))


# ── Shared status lookup (placeholder until Sumsub is live) ──────────

async def _do_status_lookup(query, session_key: str, user_id: int, email: str) -> None:
    """
    Placeholder: Sumsub API not yet active.
    Replace this function body when the endpoint is ready.
    """
    await _edit(query, "I'm checking your onboarding status now\u2026 one moment.")
    await query.message.reply_text(
        "I'm sorry — our verification system is temporarily unavailable. "
        "This is a known issue on our end and is being resolved.\n\n"
        "Here's what I can do for you right now:",
        reply_markup=_mk(
            [("🚩 Flag query for onboarding team", "status:flag")],
            [("📋 View general onboarding info", "status:info")],
            [("👤 Connect me to a live agent", "nav:support")],
        ),
    )
    await update_session(session_key, conversation_state="active")
