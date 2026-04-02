"""
All InlineKeyboardMarkup builders for the Endl Support Bot.
Every public function/constant here maps to a distinct menu or button group
described in the master system prompt.
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def _mk(*rows) -> InlineKeyboardMarkup:
    """Build an InlineKeyboardMarkup from variable (label, callback_data) rows."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data=cb) for label, cb in row]
        for row in rows
    ])


# ── Main menu (unified — no individual/business split) ────────────────
def kb_main(account_type: str = "individual") -> InlineKeyboardMarkup:
    return _mk(
        [("📊 Check my Onboarding Status (KYC/KYB)", "status:check")],
        [("📋 Onboarding & Documents", "nav:onboarding")],
        [("ℹ️ About Endl", "nav:about")],
        [("💱 Currencies & Fees", "nav:currencies")],
        [("📤 Payments & Transfers", "nav:payments")],
        [("💳 Visa Cards for Spending", "nav:card")],
        [("🛡️ Security & Compliance", "nav:security")],
        [("🚀 Getting Started", "nav:getting_started")],
        [("💬 Talk to Support Team", "nav:support")],
    )


# ── Step 2: About Endl ───────────────────────────────────────────────
KB_ABOUT = _mk(
    [("🏦 What is Endl?", "about:what_is")],
    [("👥 Who can use Endl?", "about:who")],
    [("🌍 What countries are supported?", "about:countries")],
    [("📜 Is Endl regulated?", "about:regulated")],
    [("⚡ Endl vs Wise/Payoneer", "about:different")],
    [("◀️ Back to menu", "nav:back")],
)


# ── Step 3: Currencies & fees ─────────────────────────────────────────
KB_CURRENCIES = _mk(
    [("💵 What currencies are supported?", "curr:supported")],
    [("💰 What are the transaction fees?", "curr:fees")],
    [("🔄 Are there FX conversion fees?", "curr:fx")],
    [("🪙 What stablecoins are supported?", "curr:stablecoins")],
    [("◀️ Back to menu", "nav:back")],
)


# ── Payments & Transfers (unified) ───────────────────────────────────
KB_PAYMENTS = _mk(
    [("📥 How do I receive payments?", "pay:receive")],
    [("🏧 What are virtual accounts?", "pay:virtual")],
    [("🔄 How do I convert funds?", "pay:convert")],
    [("🌐 Can I send global payouts?", "pay:payouts")],
    [("📤 Can I send SWIFT transfers?", "pay:swift_out")],
    [("📥 Can I receive SWIFT deposits?", "pay:swift_in")],
    [("🛤️ What payment rails are supported?", "pay:rails")],
    [("⏳ How long do withdrawals take?", "pay:time")],
    [("⚠️ My payment is delayed", "pay:delayed")],
    [("◀️ Back to menu", "nav:back")],
)

# Keep legacy names for backward compat in resolver
KB_PAY_IND = KB_PAYMENTS
KB_PAY_BIZ = KB_PAYMENTS


# ── Step 6: Onboarding & documents (Business) ────────────────────────
KB_ONBOARDING = _mk(
    [("📄 What documents are required?", "onb:docs")],
    [("⏱️ How long does onboarding take?", "onb:time")],
    [("🔍 Why is my onboarding delayed?", "onb:delayed")],
    [("❌ My verification failed", "onb:failed")],
    [("📬 My proof of address was rejected", "onb:poa")],
    [("⏳ KYB still shows 'in progress'", "onb:progress")],
    [("✏️ Can I update my business details?", "onb:update")],
    [("🔔 When will I hear back?", "onb:hear")],
    [("◀️ Back to menu", "nav:back")],
)


# ── Step 7: Visa Cards for Spending ──────────────────────────────────
KB_CARD = _mk(
    [("💳 Does Endl offer Visa cards?", "card:offered")],
    [("👥 How do I issue cards for my team?", "card:issue")],
    [("📏 Can I set spending limits per card?", "card:limits")],
    [("📊 How do I manage expenses?", "card:manage")],
    [("🌍 Which currencies can cards be used in?", "card:currencies")],
    [("🆕 How do I get a Visa card?", "card:apply")],
    [("◀️ Back to menu", "nav:back")],
)


# ── Step 8: Security & Compliance ─────────────────────────────────────
KB_SECURITY = _mk(
    [("🔐 Is my money safe?", "sec:safe")],
    [("🛡️ How is my data protected?", "sec:data")],
    [("📡 How are transactions monitored?", "sec:monitoring")],
    [("◀️ Back to menu", "nav:back")],
)

# Keep legacy names for backward compat
KB_SECURITY_IND = KB_SECURITY
KB_SECURITY_BIZ = KB_SECURITY


# ── Step 9: Talk to Support Team ──────────────────────────────────────
KB_SUPPORT = _mk(
    [("🚩 Flag my query for the onboarding team", "sup:flag")],
    [("👤 Connect me to a live agent", "sup:agent")],
    [("🌐 Visit the Help Centre", "sup:help")],
    [("📝 My support tickets", "nav:tickets")],
    [("◀️ Back to menu", "nav:back")],
)


# ── Getting Started ──────────────────────────────────────────────────
KB_GETTING_STARTED = _mk(
    [("📝 How to sign up", "gs:signup")],
    [("📄 Documents I'll need", "gs:docs")],
    [("⏱️ How long does it take?", "gs:time")],
    [("◀️ Back to menu", "nav:back")],
)


# ── Step 10: Status / OTP flow ────────────────────────────────────────
KB_STATUS_POST = _mk(
    [("🚩 Flag query for onboarding team", "status:flag")],
    [("📋 View general onboarding info", "status:info")],
    [("👤 Connect me to a live agent", "nav:support")],
)

KB_OTP_RESEND_OPTIONS = _mk(
    [("🔄 Resend code", "otp:resend"), ("📧 Change my email", "otp:change_email")],
    [("🎧 Contact support", "nav:support"), ("◀️ Back to menu", "nav:back")],
)

KB_OTP_EXPIRED = _mk(
    [("✅ Yes, send new code", "otp:resend"), ("❌ No, cancel", "nav:back")],
)

KB_OTP_LOCKED = _mk(
    [("🎧 Contact support now", "nav:support")],
    [("◀️ Back to menu", "nav:back")],
)

# Cancel out of OTP flow at any point
KB_OTP_CANCEL = _mk(
    [("📧 Change my email", "otp:change_email")],
    [("◀️ Cancel and go back", "nav:back")],
)


# ── Step 12: Frustration / urgency ───────────────────────────────────
KB_URGENCY = _mk(
    [("👤 Connect me to a live agent now", "sup:agent")],
    [("🚩 Priority flag for onboarding team", "sup:flag")],
    [("◀️ Back to menu", "nav:back")],
)


# ── Feedback ──────────────────────────────────────────────────────────
def kb_feedback(context_id: str = "general") -> InlineKeyboardMarkup:
    """Thumbs up/down feedback after answering a question."""
    return _mk(
        [("👍 Helpful", f"fb:yes:{context_id}"), ("👎 Not helpful", f"fb:no:{context_id}")],
    )


# ── Utility keyboards ─────────────────────────────────────────────────
def kb_ask_back(section: str) -> InlineKeyboardMarkup:
    """'Ask another question' sends user back to the named submenu callback."""
    return _mk(
        [("🔄 Ask another question", f"nav:{section}"), ("◀️ Back to menu", "nav:back")],
    )


def kb_back() -> InlineKeyboardMarkup:
    return _mk([("◀️ Back to menu", "nav:back")])


def kb_support_back() -> InlineKeyboardMarkup:
    return _mk(
        [("🎧 Contact support", "nav:support"), ("◀️ Back to menu", "nav:back")],
    )


# ── Status check confirmation (soft trigger) ─────────────────────────
KB_STATUS_CONFIRM = _mk(
    [("✅ Yes, check my status", "status:check"), ("❌ No, something else", "nav:back")],
)


def kb_status_support_back() -> InlineKeyboardMarkup:
    return _mk(
        [("📊 Check my onboarding status", "status:check"), ("🎧 Talk to support", "nav:support")],
        [("◀️ Back to menu", "nav:back")],
    )


# ── Group Quick Menu keyboards ────────────────────────────────────────

KB_GROUP_MAIN = _mk(
    [("ℹ️ What is Endl?", "grp:about"), ("💱 Currencies & fees", "grp:currencies")],
    [("📤 Payments & transfers", "grp:payments"), ("📋 Onboarding info", "grp:onboarding")],
    [("🛡️ Security", "grp:security"), ("🔐 Check my account status", "grp:status")],
)

KB_GROUP_ABOUT = _mk(
    [("👥 Who is it for?", "grp:about_who")],
    [("📜 Is Endl regulated?", "grp:about_regulated")],
    [("⚡ Endl vs Wise?", "grp:about_wise")],
    [("◀️ Back to menu", "grp:back")],
)

KB_GROUP_CURRENCIES = _mk(
    [("💵 What currencies?", "grp:curr_supported")],
    [("💰 What are the fees?", "grp:curr_fees")],
    [("🪙 What stablecoins?", "grp:curr_stablecoins")],
    [("◀️ Back to menu", "grp:back")],
)

KB_GROUP_PAYMENTS = _mk(
    [("📥 How do I receive payments?", "grp:pay_receive")],
    [("🛤️ What payment rails?", "grp:pay_rails")],
    [("📤 Can I send SWIFT?", "grp:pay_swift")],
    [("⏳ How long do withdrawals take?", "grp:pay_time")],
    [("◀️ Back to menu", "grp:back")],
)

KB_GROUP_ONBOARDING = _mk(
    [("⏱️ How long does onboarding take?", "grp:onb_time")],
    [("📄 What documents do I need?", "grp:onb_docs")],
    [("🔍 Why is my onboarding delayed?", "grp:onb_delayed")],
    [("◀️ Back to menu", "grp:back")],
)

KB_GROUP_SECURITY = _mk(
    [("🔐 Is my money safe?", "grp:sec_safe")],
    [("🛡️ How is my data protected?", "grp:sec_data")],
    [("📡 How are transactions monitored?", "grp:sec_monitoring")],
    [("◀️ Back to menu", "grp:back")],
)

KB_GROUP_BACK = _mk([("◀️ Back to menu", "grp:back")])

KB_GROUP_BACK_WITH_STATUS = _mk(
    [("🔐 Check my account status", "grp:status")],
    [("◀️ Back to menu", "grp:back")],
)


# ── Name → keyboard resolver (used by free-text handler) ─────────────

def get_kb_by_name(name: str, account_type: str = "individual") -> InlineKeyboardMarkup:
    """
    Resolve a button-set name (as returned by Claude's freetext response)
    to the appropriate InlineKeyboardMarkup.
    """
    mapping = {
        "status_flow":    KB_STATUS_CONFIRM,
        "about":          KB_ABOUT,
        "currencies":     KB_CURRENCIES,
        "payments":       KB_PAYMENTS,
        "payments_ind":   KB_PAYMENTS,
        "payments_biz":   KB_PAYMENTS,
        "onboarding":     KB_ONBOARDING,
        "card":           KB_CARD,
        "security":       KB_SECURITY,
        "support":        KB_SUPPORT,
        "urgency":        KB_URGENCY,
        "getting_started": KB_GETTING_STARTED,
        "main_menu":      kb_main(account_type),
    }
    return mapping.get(name, kb_main(account_type))
