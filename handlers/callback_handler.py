"""
Handles all InlineKeyboardButton callback queries.
Every callback_data prefix maps to a handler block below.
"""
import logging

from telegram import Update, InlineKeyboardMarkup
from telegram.constants import ChatAction
from telegram.error import BadRequest
from telegram.ext import ContextTypes

from config import SUPPORT_LINK, SMTP_USER, SMTP_PASSWORD
from database.models import (
    get_or_create_session, update_session,
    save_verified_user, get_verified_email, get_user_tickets,
)
from utils.keyboards import (
    _mk, kb_main, kb_ask_back, kb_back, kb_support_back, kb_status_support_back,
    kb_feedback,
    KB_ABOUT, KB_CURRENCIES, KB_PAYMENTS, KB_PAYMENTS_MORE,
    KB_ONBOARDING, KB_ONBOARDING_MORE, KB_CARD, KB_SECURITY, KB_SUPPORT,
    KB_OTP_RESEND_OPTIONS, KB_OTP_CANCEL, KB_GETTING_STARTED,
    KB_GROUP_MAIN, KB_GROUP_ABOUT, KB_GROUP_CURRENCIES, KB_GROUP_PAYMENTS,
    KB_GROUP_ONBOARDING, KB_GROUP_SECURITY, KB_GROUP_BACK, KB_GROUP_BACK_WITH_STATUS,
    kb_followup_curr_supported, kb_followup_curr_fees, kb_followup_curr_fx,
    kb_followup_curr_stablecoins,
    kb_followup_pay_receive, kb_followup_pay_virtual, kb_followup_pay_swift_out,
    kb_followup_pay_swift_in, kb_followup_pay_time, kb_followup_pay_rails,
    kb_followup_pay_delayed,
    kb_followup_onb_docs, kb_followup_onb_time,
    kb_followup_card_offered, kb_followup_card_issue, kb_followup_card_apply,
    kb_followup_about,
)
from utils.otp import generate_otp, store_otp, send_otp_email, cancel_otp
from flows.status_progress import get_status_guidance

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


def _main_text(account_type: str = "individual") -> str:
    return "How can I help you today? \U0001f447"


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
            "about": (
                "<b>About Endl</b>\n"
                "Global business payments — collect, convert, and send from one dashboard.",
                KB_ABOUT,
            ),
            "currencies": (
                "<b>Currencies & Fees</b>\n"
                "6+ fiat currencies and stablecoins, fees from 0.5%.",
                KB_CURRENCIES,
            ),
            "payments": (
                "<b>Payments & Transfers</b>\n"
                "Receive local payments, send global payouts, and manage SWIFT.",
                KB_PAYMENTS,
            ),
            "payments_more": (
                "<b>Payments & Transfers</b> — more options\n"
                "Virtual accounts, fund conversion, payment rails, and more.",
                KB_PAYMENTS_MORE,
            ),
            "pay_ind": (
                "<b>Payments & Transfers</b>\n"
                "Receive local payments, send global payouts, and manage SWIFT.",
                KB_PAYMENTS,
            ),
            "pay_biz": (
                "<b>Payments & Transfers</b>\n"
                "Receive local payments, send global payouts, and manage SWIFT.",
                KB_PAYMENTS,
            ),
            "onboarding": (
                "<b>Onboarding & Documents</b>\n"
                "KYC in ~1 day, KYB in 2-4 days. See what you need below.",
                KB_ONBOARDING,
            ),
            "onboarding_more": (
                "<b>Onboarding & Documents</b> — more options\n"
                "Address proof, KYB progress, and updating your details.",
                KB_ONBOARDING_MORE,
            ),
            "card": (
                "<b>Visa Cards</b>\n"
                "Issue cards, set limits, and manage team spending.",
                KB_CARD,
            ),
            "support": (
                "How would you like to get help?",
                KB_SUPPORT,
            ),
            "getting_started": (
                "<b>Getting Started</b>\n"
                "New to Endl? Here's everything you need to get set up.",
                KB_GETTING_STARTED,
            ),
        }
        if dest in nav_map:
            text, kb = nav_map[dest]
            await _edit(query, text, kb)
            return

        if dest == "security":
            await _edit(
                query,
                "<b>Security & Compliance</b>\n"
                "Regulated partners, AML monitoring, and strict data protection.",
                KB_SECURITY,
            )
            return

        if dest == "tickets":
            tickets = await get_user_tickets(user_id)
            if not tickets:
                await _edit(
                    query,
                    "You have no open support tickets.\n\n"
                    "If you need help, just ask your question and I'll assist you.",
                    kb_back(),
                )
            else:
                lines = ["<b>Your recent support tickets:</b>\n"]
                for i, t in enumerate(tickets, 1):
                    lines.append(
                        f"{i}. <code>{t['ticket_id']}</code>\n"
                        f"   Category: {t['issue_category']}\n"
                        f"   Severity: {t['severity']}\n"
                        f"   Status: {t['status']}\n"
                        f"   Created: {t['created_at']}"
                    )
                lines.append(f"\nFor updates, contact support: {SUPPORT_LINK}")
                await _edit(query, "\n".join(lines), kb_back())
            return

        logger.warning("Unhandled nav dest: %s", dest)
        await _edit(query, _main_text(account_type), kb_main(account_type))
        return

    # ── GETTING STARTED (gs: prefix) ─────────────────────────────────
    if data.startswith("gs:"):
        key = data[3:]
        if key == "signup":
            await _edit(
                query,
                "<b>How to sign up with Endl:</b>\n\n"
                "1. Visit the Endl platform and create your account\n"
                "2. Choose Individual or Business account type\n"
                "3. Complete identity verification (KYC/KYB)\n"
                "4. Submit required documents\n"
                "5. Once approved, start using your dashboard!\n\n"
                "The whole process is quick and straightforward.",
                _mk(
                    [("Documents I'll need", "gs:docs"), ("How long?", "gs:time")],
                    [("◀ Back to Getting Started", "nav:getting_started"), ("🏠 Main Menu", "nav:back")],
                ),
            )
        elif key == "docs":
            if account_type == "business":
                await _edit(
                    query,
                    "<b>Documents you'll need (Business):</b>\n\n"
                    "1. Company registration documents\n"
                    "2. Shareholder details\n"
                    "3. Articles or Memorandum of Association\n"
                    "4. UBO identity verification\n"
                    "5. Proof of business activity (website, invoices, or contracts)\n"
                    "6. Business description\n\n"
                    "Additional documents may be requested depending on your jurisdiction.",
                    _mk(
                        [("How to sign up", "gs:signup"), ("How long?", "gs:time")],
                        [("◀ Back to Getting Started", "nav:getting_started"), ("🏠 Main Menu", "nav:back")],
                    ),
                )
            else:
                await _edit(
                    query,
                    "<b>Documents you'll need (Individual):</b>\n\n"
                    "1. Government-issued ID (passport, national ID, or driver's licence)\n"
                    "2. Proof of address (utility bill or bank statement, last 3 months)\n"
                    "3. Selfie verification\n\n"
                    "Make sure documents are clear, valid, and not expired.",
                    _mk(
                        [("How to sign up", "gs:signup"), ("How long?", "gs:time")],
                        [("◀ Back to Getting Started", "nav:getting_started"), ("🏠 Main Menu", "nav:back")],
                    ),
                )
        elif key == "time":
            await _edit(
                query,
                "<b>How long does it take?</b>\n\n"
                "<b>Individual (KYC):</b> ~1 business day\n"
                "<b>Business (KYB):</b> 2-4 business days\n\n"
                "Timelines start after all required documents are submitted. "
                "You'll be notified in your dashboard once verification is complete.",
                _mk(
                    [("How to sign up", "gs:signup"), ("Documents I'll need", "gs:docs")],
                    [("◀ Back to Getting Started", "nav:getting_started"), ("🏠 Main Menu", "nav:back")],
                ),
            )
        return

    # ── FEEDBACK (fb: prefix) ────────────────────────────────────────
    if data.startswith("fb:"):
        parts = data.split(":", 2)
        vote = parts[1] if len(parts) > 1 else ""
        if vote == "yes":
            await _edit(query, "Thanks for the feedback! Glad I could help. \U0001f44d\n\nAnything else I can help with?", kb_back())
        else:
            await _edit(
                query,
                "Thanks for letting me know. I'll try to do better!\n\n"
                "Would you like to talk to our support team for more help?",
                _mk(
                    [("Live agent", "sup:agent"), ("◀ Back", "nav:back")],
                ),
            )
        return

    # ── ABOUT ENDL ───────────────────────────────────────────────────
    if data.startswith("about:"):
        key = data[6:]
        answers = {
            "what_is": (
                "Endl is a global business payments platform. You can collect payments locally, "
                "hold funds in multiple currencies, convert between fiat and stablecoins, and send "
                "global payouts — all from one dashboard.",
                kb_followup_about("what_is"),
            ),
            "who": (
                "Endl is designed for businesses and individuals who receive local payments or send "
                "international payments — including startups, agencies, SaaS companies, trading "
                "firms, and global service providers.",
                kb_followup_about("who"),
            ),
            "countries": (
                "Endl supports businesses operating globally. Availability depends on compliance "
                "checks and regulatory requirements. Businesses in globally sanctioned countries "
                "are not supported. Your jurisdiction is verified during onboarding.",
                kb_followup_about("countries"),
            ),
            "regulated": (
                "Yes. Endl holds relevant licences and operates in partnership with regulated "
                "financial institutions. The platform follows strict compliance frameworks including "
                "AML screening, transaction monitoring, and KYC/KYB verification.",
                kb_followup_about("regulated"),
            ),
            "different": (
                "Endl combines multi-currency business accounts with stablecoin settlement "
                "infrastructure. This means faster global transfers, lower FX costs, and the "
                "ability to move between fiat currencies and digital dollars (USDC/USDT) when needed.",
                kb_followup_about("different"),
            ),
        }
        if key in answers:
            text, kb = answers[key]
            await _edit(query, text, kb)
        return

    # ── CURRENCIES & FEES ────────────────────────────────────────────
    if data.startswith("curr:"):
        key = data[5:]
        if key == "supported":
            await _edit(
                query,
                "Endl supports:\n\n"
                "🇺🇸 <b>USD</b> · 🇪🇺 <b>EUR</b> · 🇦🇪 <b>AED</b> · 🇬🇧 <b>GBP</b> · "
                "🇧🇷 <b>BRL</b> · 🇲🇽 <b>MXN</b>\n\n"
                "Plus stablecoins <b>USDC</b> and <b>USDT</b>.\n"
                "More currencies and local rails are continuously being added.",
                kb_followup_curr_supported(),
            )
        elif key == "fees":
            await _edit(
                query,
                "Typical transaction fees are approximately <b>0.5% per deposit or withdrawal "
                "transaction</b>. Full pricing is shared once your account is approved.",
                kb_followup_curr_fees(),
            )
        elif key == "fx":
            await _edit(
                query,
                "FX conversion fees depend on the currency pair. Detailed pricing is shared once "
                "your account is approved. For specifics, our support team can assist.",
                kb_followup_curr_fx(),
            )
        elif key == "stablecoins":
            await _edit(
                query,
                "Endl supports <b>USDC and USDT</b>. You can convert between fiat currencies and "
                "digital dollars directly within the dashboard.",
                kb_followup_curr_stablecoins(),
            )
        return

    # ── PAYMENTS & TRANSFERS ─────────────────────────────────────────
    if data.startswith("pay:"):
        key = data[4:]
        if key == "receive":
            await _edit(
                query,
                "Once your account is active, generate virtual account details directly from your "
                "Endl dashboard. Share these with your clients to receive local bank transfers.",
                kb_followup_pay_receive(),
            )
        elif key == "virtual":
            await _edit(
                query,
                "Virtual accounts give you local bank account details in supported "
                "currencies (e.g. USD, EUR). Your clients send payments as if to a local bank — "
                "no international wires needed.",
                kb_followup_pay_virtual(),
            )
        elif key == "convert":
            await _edit(
                query,
                "Funds can be converted directly within the Endl dashboard between supported fiat "
                "currencies and stablecoins (USDC/USDT).",
                _mk(
                    [("Stablecoins supported", "curr:stablecoins"), ("Supported currencies", "curr:supported")],
                    [("◀ Back to Payments", "nav:payments"), ("🏠 Main Menu", "nav:back")],
                ),
            )
        elif key == "payouts":
            await _edit(
                query,
                "Yes. Endl allows you to send payouts to partners or vendors across multiple "
                "countries from your dashboard.",
                _mk(
                    [("SWIFT transfers", "pay:swift_out"), ("Payment rails", "pay:rails")],
                    [("◀ Back to Payments", "nav:payments"), ("🏠 Main Menu", "nav:back")],
                ),
            )
        elif key == "swift_out":
            await _edit(
                query,
                "Yes. SWIFT transfers are supported for <b>third-party business payments</b> "
                "only. SWIFT cannot be used to send to individual personal accounts.",
                kb_followup_pay_swift_out(),
            )
        elif key == "swift_in":
            await _edit(
                query,
                "Incoming SWIFT deposits aren't available yet — but here's how you can "
                "receive funds instead:\n\n"
                "Use the local payment rails shown in your virtual account details inside "
                "the dashboard (ACH, SEPA, FPS, PIX, etc.). These are often faster and "
                "more cost-effective than SWIFT.",
                kb_followup_pay_swift_in(),
            )
        elif key == "rails":
            await _edit(
                query,
                "Supported rails by currency:\n\n"
                "🇺🇸 <b>USD</b> — ACH and Fedwire\n"
                "🇪🇺 <b>EUR</b> — SEPA and SEPA Instant\n"
                "🇬🇧 <b>GBP</b> — Faster Payments (FPS)\n"
                "🇧🇷 <b>BRL</b> — PIX\n"
                "🇲🇽 <b>MXN</b> — SPEI or CLABE\n"
                "🇦🇪 <b>AED</b> — Local UAE bank transfer\n"
                "🌐 <b>SWIFT outgoing</b> — B2B third-party payments only\n\n"
                "Incoming SWIFT is not supported.",
                kb_followup_pay_rails(),
            )
        elif key == "time":
            await _edit(
                query,
                "Withdrawal times depend on the destination currency and payment rail. Some "
                "transfers settle instantly; others may take <b>1–3 business days</b>.",
                kb_followup_pay_time(),
            )
        elif key == "delayed":
            await _edit(
                query,
                "Most delays are caused by banking processing times or compliance checks. "
                "If your payment hasn't arrived within the expected timeframe, please contact "
                "support with your <b>transaction reference number</b>.",
                kb_followup_pay_delayed(),
            )
        return

    # ── ONBOARDING & DOCUMENTS ───────────────────────────────────────
    if data.startswith("onb:"):
        key = data[4:]
        if key == "docs":
            await _edit(
                query,
                "For business onboarding, you will need:\n\n"
                "1. Company registration documents\n"
                "2. Shareholder details\n"
                "3. Articles or Memorandum of Association\n"
                "4. UBO identity verification\n"
                "5. Proof of business activity (website, invoices, or contracts)\n"
                "6. Business description\n\n"
                "Additional documents may be requested depending on your jurisdiction.",
                kb_followup_onb_docs(),
            )
        elif key == "time":
            await _edit(
                query,
                "KYB verification typically takes <b>2–4 business days</b> after all required "
                "documents are submitted. Individual KYC is usually <b>1 business day</b>. "
                "Exact timelines may vary depending on document completeness and compliance checks.",
                kb_followup_onb_time(),
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
                _mk(
                    [("Contact support", "nav:support"), ("Required documents", "onb:docs")],
                    [("◀ Back to Onboarding", "nav:onboarding"), ("🏠 Main Menu", "nav:back")],
                ),
            )
        elif key == "progress":
            await _edit(
                query,
                "Once your documents are submitted, they are first reviewed by the Endl compliance "
                "team. After approval, the application is forwarded to our partner banks to open "
                "your virtual accounts. Your status will update to <b>Verification Successful</b> "
                "only after the partner bank approves.",
                _mk(
                    [("📊 Check my status", "status:check"), ("Talk to support", "nav:support")],
                    [("◀ Back to Onboarding", "nav:onboarding"), ("🏠 Main Menu", "nav:back")],
                ),
            )
        elif key == "update":
            await _edit(
                query,
                "Yes — if you need to update any submitted information, please contact our support "
                "team and the onboarding team will assist you.",
                _mk(
                    [("Contact support", "nav:support")],
                    [("◀ Back to Onboarding", "nav:onboarding"), ("🏠 Main Menu", "nav:back")],
                ),
            )
        elif key == "hear":
            await _edit(
                query,
                "You will receive a notification in your <b>account dashboard</b> once "
                "verification is completed and your account is ready to use.",
                _mk(
                    [("📊 Check my status", "status:check")],
                    [("◀ Back to Onboarding", "nav:onboarding"), ("🏠 Main Menu", "nav:back")],
                ),
            )
        return

    # ── CORPORATE CARD ───────────────────────────────────────────────
    if data.startswith("card:"):
        key = data[5:]
        if key == "offered":
            await _edit(
                query,
                "Yes! Endl offers Visa cards for managing your expenses, subscriptions, "
                "and team spending — with customisable limits and controls.",
                kb_followup_card_offered(),
            )
        elif key == "issue":
            await _edit(
                query,
                "Multiple Visa cards can be issued directly from your Endl dashboard. Each "
                "card can be assigned to a team member with individual spending controls.",
                kb_followup_card_issue(),
            )
        elif key == "limits":
            await _edit(
                query,
                "Yes — you can set customisable spending limits and controls per employee or per "
                "department from the dashboard.",
                _mk(
                    [("Manage expenses", "card:manage"), ("Card currencies", "card:currencies")],
                    [("◀ Back to Visa Cards", "nav:card"), ("🏠 Main Menu", "nav:back")],
                ),
            )
        elif key == "manage":
            await _edit(
                query,
                "The Endl dashboard gives you a centralised view of all card activity, with "
                "controls to adjust limits, pause cards, and review transactions.",
                _mk(
                    [("Set spending limits", "card:limits"), ("Card currencies", "card:currencies")],
                    [("◀ Back to Visa Cards", "nav:card"), ("🏠 Main Menu", "nav:back")],
                ),
            )
        elif key == "currencies":
            await _edit(
                query,
                "Cards are supported for all currencies active on your Endl account.",
                _mk(
                    [("Does Endl offer cards?", "card:offered"), ("Get a Visa card", "card:apply")],
                    [("◀ Back to Visa Cards", "nav:card"), ("🏠 Main Menu", "nav:back")],
                ),
            )
        elif key == "apply":
            await _edit(
                query,
                "<b>How to get a Visa card:</b>\n\n"
                "1. Complete your onboarding verification (KYC/KYB)\n"
                "2. Once your account is active, go to the Cards section in your dashboard\n"
                "3. Request a new Visa card and assign it to a team member\n"
                "4. Set spending limits and controls\n\n"
                "Cards are available for all approved accounts.",
                kb_followup_card_apply(),
            )
        return

    # ── SECURITY ─────────────────────────────────────────────────────
    if data.startswith("sec:"):
        key = data[4:]
        answers = {
            "safe": (
                "Yes. Endl follows strict compliance and security practices including AML "
                "monitoring, KYC/KYB verification, and regulated financial partners to protect "
                "your funds.",
                _mk(
                    [("Data protection", "sec:data"), ("Transaction monitoring", "sec:monitoring")],
                    [("◀ Back to Security", "nav:security"), ("🏠 Main Menu", "nav:back")],
                ),
            ),
            "data": (
                "Endl applies strict compliance frameworks and security practices to protect all "
                "personal and business data.",
                _mk(
                    [("Is my money safe?", "sec:safe"), ("Transaction monitoring", "sec:monitoring")],
                    [("◀ Back to Security", "nav:security"), ("🏠 Main Menu", "nav:back")],
                ),
            ),
            "monitoring": (
                "All transactions are subject to ongoing AML screening and compliance review. "
                "Any flagged activity is reviewed by our compliance team.",
                _mk(
                    [("Is my money safe?", "sec:safe"), ("Data protection", "sec:data")],
                    [("◀ Back to Security", "nav:security"), ("🏠 Main Menu", "nav:back")],
                ),
            ),
        }
        if key in answers:
            text, kb = answers[key]
            await _edit(query, text, kb)
        return

    # ── SUPPORT ──────────────────────────────────────────────────────
    if data.startswith("sup:"):
        key = data[4:]
        if key == "flag":
            await _edit(
                query,
                "Understood — could you briefly describe your query so our team has context "
                "when they review it?\n\n<i>Please type your message below.</i>",
                _mk([("Cancel", "nav:back")]),
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

    # ── STATUS / KYC / KYB FLOW ──────────────────────────────────────
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
                await _edit(
                    query,
                    f"I have your verified email on file: <b>{verified_email}</b>.\n\n"
                    "Would you like to check your status with this email, or use a different one?",
                    _mk(
                        [(f"Use {verified_email}", "status:use_verified"),
                         ("Different email", "status:new_email")],
                        [("◀ Back", "nav:back")],
                    ),
                )
                return

            await _edit(
                query,
                "To look up your status, I need to verify your registered email address.\n\n"
                "📧 Please type the email you used when signing up with Endl.\n"
                "<i>(e.g., name@company.com)</i>",
                _mk([("Cancel", "nav:back")]),
            )
            await update_session(session_key, conversation_state="status_awaiting_email")
            return

        if key == "use_verified":
            verified_email = await get_verified_email(user_id)
            if verified_email:
                await update_session(session_key, email=verified_email)
                await _do_status_lookup(query, session_key, user_id, verified_email, account_type)
            return

        if key == "new_email":
            email = session.get("email", "")
            if email:
                await cancel_otp(email, user_id)
            await _edit(
                query,
                "No problem — could you share the correct email address?\n\n"
                "📧 Please type your registered email.\n"
                "<i>(e.g., name@company.com)</i>",
                _mk([("Cancel", "nav:back")]),
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
                    _mk([("Contact support", "nav:support"),
                         ("◀ Back", "nav:back")]),
                )
                return
            sent = await send_otp_email(email, otp_code)
            if sent:
                await _edit(
                    query,
                    f"I've resent the code to <b>{email}</b>. It's valid for 10 minutes.\n\n"
                    "Please check your inbox (and spam folder) and type the 6-digit code here.",
                    KB_OTP_CANCEL,
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
                "📧 Please type your registered email.\n"
                "<i>(e.g., name@company.com)</i>",
                _mk([("Cancel", "nav:back")]),
            )
            await update_session(session_key, conversation_state="status_awaiting_email",
                                 email=None)
            return

    # ── GROUP QUICK MENU (grp: prefix) ───────────────────────────────
    if data.startswith("grp:"):
        key = data[4:]

        if key == "back":
            await _edit(query, "What can I help you with?", KB_GROUP_MAIN)
            return

        # ── Top-level sub-menus ──────────────────────────────────────
        if key == "about":
            await _edit(
                query,
                "Endl is a global business payments platform — collect payments locally, "
                "hold funds in multiple currencies, convert between fiat and stablecoins, "
                "and send global payouts from one dashboard.",
                KB_GROUP_ABOUT,
            )
            return

        if key == "currencies":
            await _edit(query, "What would you like to know?", KB_GROUP_CURRENCIES)
            return

        if key == "payments":
            await _edit(query, "What would you like to know about payments?", KB_GROUP_PAYMENTS)
            return

        if key == "onboarding":
            await _edit(query, "What would you like to know about onboarding?", KB_GROUP_ONBOARDING)
            return

        if key == "security":
            await _edit(query, "What would you like to know about security?", KB_GROUP_SECURITY)
            return

        if key == "status":
            await _edit(
                query,
                "Account and verification queries need to stay private to keep your "
                "details secure \U0001f512\n\nDM me directly and I'll walk you through your "
                "KYC or KYB status right away.",
                KB_GROUP_BACK,
            )
            return

        # ── About sub-menu ───────────────────────────────────────────
        if key == "about_who":
            await _edit(
                query,
                "Endl is built for businesses and individuals that send or receive "
                "international payments — startups, agencies, SaaS companies, trading "
                "firms, and global service providers.",
                KB_GROUP_BACK,
            )
            return

        if key == "about_regulated":
            await _edit(
                query,
                "Yes. Endl operates with regulated financial institution partners and applies "
                "AML screening, transaction monitoring, and KYC/KYB verification across all accounts.",
                KB_GROUP_BACK,
            )
            return

        if key == "about_wise":
            await _edit(
                query,
                "Endl adds stablecoin settlement on top of multi-currency accounts — meaning "
                "faster transfers, lower FX costs, and the ability to move between fiat and "
                "digital dollars (USDC/USDT) when needed.",
                KB_GROUP_BACK,
            )
            return

        # ── Currencies sub-menu ──────────────────────────────────────
        if key == "curr_supported":
            await _edit(
                query,
                "Endl supports USD, EUR, AED, GBP, BRL, and MXN — plus USDC and USDT. "
                "More currencies and local rails are continuously being added.",
                _mk(
                    [("What are the fees?", "grp:curr_fees"),
                     ("◀ Back", "grp:back")],
                ),
            )
            return

        if key == "curr_fees":
            await _edit(
                query,
                "Transaction fees are approximately 0.5% per deposit or withdrawal. "
                "Full pricing is confirmed at account approval.",
                KB_GROUP_BACK,
            )
            return

        if key == "curr_stablecoins":
            await _edit(
                query,
                "Endl supports USDC and USDT. You can convert between fiat currencies and "
                "digital dollars directly within the dashboard.",
                KB_GROUP_BACK,
            )
            return

        # ── Payments sub-menu ────────────────────────────────────────
        if key == "pay_receive":
            await _edit(
                query,
                "Once your account is active, generate virtual account details from the "
                "Endl dashboard and share them with your clients. They send a local transfer — "
                "no international wire needed on their end.",
                _mk(
                    [("Payment rails", "grp:pay_rails"),
                     ("◀ Back", "grp:back")],
                ),
            )
            return

        if key == "pay_rails":
            await _edit(
                query,
                "🇺🇸 USD: ACH and Fedwire · 🇪🇺 EUR: SEPA · 🇬🇧 GBP: FPS · 🇧🇷 BRL: PIX · "
                "🇲🇽 MXN: SPEI or CLABE · 🇦🇪 AED: local UAE transfer · "
                "SWIFT outgoing: B2B third-party payments only.",
                _mk(
                    [("Send SWIFT", "grp:pay_swift"),
                     ("◀ Back", "grp:back")],
                ),
            )
            return

        if key == "pay_swift":
            await _edit(
                query,
                "Yes — SWIFT outgoing is supported for business-to-business third-party "
                "payments only. Incoming SWIFT deposits are not supported; use the virtual "
                "account details in your dashboard instead.",
                KB_GROUP_BACK,
            )
            return

        if key == "pay_time":
            await _edit(
                query,
                "Some transfers settle instantly, others take 1–3 business days depending "
                "on the destination currency and payment rail.",
                KB_GROUP_BACK,
            )
            return

        # ── Onboarding sub-menu ──────────────────────────────────────
        if key == "onb_time":
            await _edit(
                query,
                "Individual KYC takes approximately 1 business day. Business KYB typically "
                "takes 2–4 business days after all required documents are submitted.",
                _mk(
                    [("What documents?", "grp:onb_docs"),
                     ("◀ Back", "grp:back")],
                ),
            )
            return

        if key == "onb_docs":
            await _edit(
                query,
                "For individuals: government ID, proof of address, and selfie verification.\n"
                "For businesses: company registration, shareholder details, articles of "
                "association, UBO verification, and proof of business activity.",
                KB_GROUP_BACK,
            )
            return

        if key == "onb_delayed":
            await _edit(
                query,
                "Some applications require additional compliance or partner bank review. "
                "If you're waiting on a status update, DM me and I'll check what's "
                "happening for you \U0001f512",
                KB_GROUP_BACK_WITH_STATUS,
            )
            return

        # ── Security sub-menu ────────────────────────────────────────
        if key == "sec_safe":
            await _edit(
                query,
                "Yes. Endl applies AML monitoring, KYC/KYB verification, and works "
                "exclusively with regulated financial partners.",
                KB_GROUP_BACK,
            )
            return

        if key == "sec_data":
            await _edit(
                query,
                "Endl applies strict compliance frameworks and security practices to "
                "protect all personal and business data.",
                KB_GROUP_BACK,
            )
            return

        if key == "sec_monitoring":
            await _edit(
                query,
                "All transactions go through ongoing AML screening and compliance review. "
                "Any flagged activity is reviewed by our compliance team.",
                KB_GROUP_BACK,
            )
            return

        logger.warning("Unhandled grp: callback key: %s", key)
        await _edit(query, "What can I help you with?", KB_GROUP_MAIN)
        return

    logger.warning("Unhandled callback data: %s", data)
    await _edit(query, _main_text(account_type), kb_main(account_type))


# ── Shared status lookup ──────────────────────────────────────────────

async def _do_status_lookup(query, session_key: str, user_id: int, email: str, account_type: str = "individual") -> None:
    guidance = get_status_guidance(account_type)
    await _edit(query, guidance)
    await query.message.reply_text(
        "Would you like further assistance?",
        reply_markup=_mk(
            [("Flag for onboarding team", "status:flag"), ("Live agent", "nav:support")],
            [("◀ Back", "nav:back")],
        ),
    )
    await update_session(session_key, conversation_state="active")
