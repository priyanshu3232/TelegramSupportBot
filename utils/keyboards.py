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


# ── Step 0: Entry point ───────────────────────────────────────────────
KB_ACCOUNT_TYPE = _mk(
    [("👤 Individual", "acct:individual"), ("🏢 Business", "acct:business")],
)


# ── Steps 1A / 1B: Main menus ─────────────────────────────────────────
def kb_main(account_type: str) -> InlineKeyboardMarkup:
    if account_type == "business":
        return _mk(
            [("🔍 Check my KYB status", "status:check")],
            [("📋 Onboarding & documents", "nav:onboarding")],
            [("🌍 About Endl", "nav:about"), ("💸 Payments & SWIFT", "nav:pay_biz")],
            [("💳 Corporate cards", "nav:card"), ("🔒 Security & compliance", "nav:security")],
            [("🎧 Talk to support", "nav:support")],
        )
    # Individual (default)
    return _mk(
        [("🔍 Check my KYC status", "status:check")],
        [("🌍 About Endl", "nav:about"), ("💱 Currencies & fees", "nav:currencies")],
        [("💸 Payments & transfers", "nav:pay_ind")],
        [("💳 Corporate card", "nav:card"), ("🔒 Security", "nav:security")],
        [("🎧 Talk to support", "nav:support")],
    )


# ── Step 2: About Endl ───────────────────────────────────────────────
KB_ABOUT = _mk(
    [("What is Endl?", "about:what_is")],
    [("Who can use Endl?", "about:who")],
    [("What countries are supported?", "about:countries")],
    [("Is Endl regulated?", "about:regulated")],
    [("How is Endl different from Wise or Payoneer?", "about:different")],
    [("← Back to menu", "nav:back")],
)


# ── Step 3: Currencies & fees ─────────────────────────────────────────
KB_CURRENCIES = _mk(
    [("What currencies are supported?", "curr:supported")],
    [("What are the transaction fees?", "curr:fees")],
    [("Are there FX conversion fees?", "curr:fx")],
    [("What stablecoins are supported?", "curr:stablecoins")],
    [("← Back to menu", "nav:back")],
)


# ── Step 4: Payments (Individual) ────────────────────────────────────
KB_PAY_IND = _mk(
    [("How do I receive payments?", "payi:receive")],
    [("What are virtual accounts?", "payi:virtual")],
    [("How do I convert funds?", "payi:convert")],
    [("Can I send global payouts?", "payi:payouts")],
    [("How long do withdrawals take?", "payi:time")],
    [("My payment is delayed", "payi:delayed")],
    [("← Back to menu", "nav:back")],
)


# ── Step 5: Payments & SWIFT (Business) ──────────────────────────────
KB_PAY_BIZ = _mk(
    [("Can I receive SWIFT deposits?", "payb:swift_in")],
    [("Can I send SWIFT transfers?", "payb:swift_out")],
    [("What payment rails are supported?", "payb:rails")],
    [("How long do withdrawals take?", "payb:time")],
    [("My payment is delayed", "payb:delayed")],
    [("← Back to menu", "nav:back")],
)


# ── Step 6: Onboarding & documents (Business) ────────────────────────
KB_ONBOARDING = _mk(
    [("What documents are required?", "onb:docs")],
    [("How long does onboarding take?", "onb:time")],
    [("Why is my onboarding delayed?", "onb:delayed")],
    [("My verification failed", "onb:failed")],
    [("My proof of address was rejected", "onb:poa")],
    [("KYB still shows 'in progress'", "onb:progress")],
    [("Can I update my business details?", "onb:update")],
    [("When will I hear back?", "onb:hear")],
    [("← Back to menu", "nav:back")],
)


# ── Step 7: Corporate card ────────────────────────────────────────────
KB_CARD = _mk(
    [("Does Endl offer corporate cards?", "card:offered")],
    [("How do I issue cards for my team?", "card:issue")],
    [("Can I set spending limits per card?", "card:limits")],
    [("How do I manage expenses?", "card:manage")],
    [("Which currencies can cards be used in?", "card:currencies")],
    [("← Back to menu", "nav:back")],
)


# ── Step 8: Security ──────────────────────────────────────────────────
KB_SECURITY_IND = _mk(
    [("Is my money safe?", "sec:safe")],
    [("How is my data protected?", "sec:data")],
    [("← Back to menu", "nav:back")],
)

KB_SECURITY_BIZ = _mk(
    [("Is my money safe?", "sec:safe")],
    [("How is my data protected?", "sec:data")],
    [("How are transactions monitored?", "sec:monitoring")],
    [("← Back to menu", "nav:back")],
)


# ── Step 9: Talk to support ───────────────────────────────────────────
KB_SUPPORT = _mk(
    [("🚩 Flag my query for the onboarding team", "sup:flag")],
    [("👤 Connect me to a live agent", "sup:agent")],
    [("🌐 Visit the Help Centre", "sup:help")],
    [("← Back to menu", "nav:back")],
)


# ── Step 10: Status / OTP flow ────────────────────────────────────────
KB_STATUS_POST = _mk(
    [("🚩 Flag query for onboarding team", "status:flag")],
    [("📋 View general onboarding info", "status:info")],
    [("👤 Connect me to a live agent", "nav:support")],
)

KB_OTP_RESEND_OPTIONS = _mk(
    [("Resend code", "otp:resend"), ("Change my email", "otp:change_email")],
    [("🎧 Contact support", "nav:support")],
)

KB_OTP_EXPIRED = _mk(
    [("Yes, send new code", "otp:resend"), ("No, cancel", "nav:back")],
)

KB_OTP_LOCKED = _mk(
    [("🎧 Contact support now", "nav:support")],
)


# ── Step 12: Frustration / urgency ───────────────────────────────────
KB_URGENCY = _mk(
    [("👤 Connect me to a live agent now", "sup:agent")],
    [("🚩 Priority flag for onboarding team", "sup:flag")],
    [("← Back to menu", "nav:back")],
)


# ── Utility keyboards ─────────────────────────────────────────────────
def kb_ask_back(section: str) -> InlineKeyboardMarkup:
    """'Ask another question' sends user back to the named submenu callback."""
    return _mk(
        [("Ask another question", f"nav:{section}"), ("← Back to menu", "nav:back")],
    )


def kb_back() -> InlineKeyboardMarkup:
    return _mk([("← Back to menu", "nav:back")])


def kb_support_back() -> InlineKeyboardMarkup:
    return _mk(
        [("🎧 Contact support now", "nav:support"), ("← Back to menu", "nav:back")],
    )


def kb_status_support_back() -> InlineKeyboardMarkup:
    return _mk(
        [("🔍 Check my KYB status", "status:check"), ("🎧 Talk to support", "nav:support")],
        [("← Back to menu", "nav:back")],
    )
