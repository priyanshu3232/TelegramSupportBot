"""
All InlineKeyboardMarkup builders for the Endl Support Bot.
Every public function/constant here maps to a distinct menu or button group
described in the master system prompt.

UX principles applied:
  - 2-column grid layouts to reduce vertical scroll
  - Short button labels (under 25 chars) for mobile readability
  - Emojis only on primary CTAs and category headers, not sub-questions
  - Breadcrumb navigation: "Back to [section]" + "Main Menu"
  - Contextual follow-up buttons after answers (related questions, not generic)
  - Large sub-menus (Payments, Onboarding) split into 2 tiers
"""
from telegram import InlineKeyboardButton, InlineKeyboardMarkup


def _mk(*rows) -> InlineKeyboardMarkup:
    """Build an InlineKeyboardMarkup from variable (label, callback_data) rows."""
    return InlineKeyboardMarkup([
        [InlineKeyboardButton(label, callback_data=cb) for label, cb in row]
        for row in rows
    ])


# ── Main menu (2-column grid layout) ────────────────────────────────
def kb_main(account_type: str = "individual") -> InlineKeyboardMarkup:
    return _mk(
        [("📊 Check My Status", "status:check")],
        [("Onboarding & Docs", "nav:onboarding"), ("Payments", "nav:payments")],
        [("Currencies & Fees", "nav:currencies"), ("Visa Cards", "nav:card")],
        [("About Endl", "nav:about"), ("Security", "nav:security")],
        [("🚀 Getting Started", "nav:getting_started")],
        [("💬 Talk to Support", "nav:support")],
    )


# ── About Endl (2-column questions) ─────────────────────────────────
KB_ABOUT = _mk(
    [("What is Endl?", "about:what_is"), ("Who can use Endl?", "about:who")],
    [("Supported countries", "about:countries"), ("Is Endl regulated?", "about:regulated")],
    [("Endl vs Wise/Payoneer", "about:different")],
    [("◀ Back", "nav:back")],
)


# ── Currencies & fees (2-column questions) ───────────────────────────
KB_CURRENCIES = _mk(
    [("Supported currencies", "curr:supported"), ("Transaction fees", "curr:fees")],
    [("FX conversion fees", "curr:fx"), ("Stablecoins supported", "curr:stablecoins")],
    [("◀ Back", "nav:back")],
)


# ── Payments & Transfers — Tier 1 (top actions) ─────────────────────
KB_PAYMENTS = _mk(
    [("Receive payments", "pay:receive"), ("Send global payouts", "pay:payouts")],
    [("SWIFT transfers", "pay:swift_out"), ("Withdrawal times", "pay:time")],
    [("More questions ▼", "nav:payments_more")],
    [("◀ Back", "nav:back")],
)

# ── Payments & Transfers — Tier 2 (expanded) ────────────────────────
KB_PAYMENTS_MORE = _mk(
    [("Virtual accounts", "pay:virtual"), ("Convert funds", "pay:convert")],
    [("Receive SWIFT", "pay:swift_in"), ("Payment rails", "pay:rails")],
    [("Payment delayed", "pay:delayed")],
    [("◀ Back to Payments", "nav:payments"), ("🏠 Main Menu", "nav:back")],
)

# Keep legacy names for backward compat in resolver
KB_PAY_IND = KB_PAYMENTS
KB_PAY_BIZ = KB_PAYMENTS


# ── Onboarding & Documents — Tier 1 ─────────────────────────────────
KB_ONBOARDING = _mk(
    [("Required documents", "onb:docs"), ("How long does it take?", "onb:time")],
    [("Onboarding delayed", "onb:delayed"), ("Verification failed", "onb:failed")],
    [("More questions ▼", "nav:onboarding_more")],
    [("◀ Back", "nav:back")],
)

# ── Onboarding & Documents — Tier 2 ─────────────────────────────────
KB_ONBOARDING_MORE = _mk(
    [("Address proof rejected", "onb:poa"), ("KYB still in progress", "onb:progress")],
    [("Update business details", "onb:update"), ("When will I hear back?", "onb:hear")],
    [("◀ Back to Onboarding", "nav:onboarding"), ("🏠 Main Menu", "nav:back")],
)


# ── Visa Cards for Spending (2-column) ───────────────────────────────
KB_CARD = _mk(
    [("Does Endl offer cards?", "card:offered"), ("Get a Visa card", "card:apply")],
    [("Issue cards for team", "card:issue"), ("Set spending limits", "card:limits")],
    [("Manage expenses", "card:manage"), ("Card currencies", "card:currencies")],
    [("◀ Back", "nav:back")],
)


# ── Security & Compliance ────────────────────────────────────────────
KB_SECURITY = _mk(
    [("Is my money safe?", "sec:safe"), ("Data protection", "sec:data")],
    [("Transaction monitoring", "sec:monitoring")],
    [("◀ Back", "nav:back")],
)

# Keep legacy names for backward compat
KB_SECURITY_IND = KB_SECURITY
KB_SECURITY_BIZ = KB_SECURITY


# ── Talk to Support Team (2-column where possible) ───────────────────
KB_SUPPORT = _mk(
    [("Flag for onboarding team", "sup:flag"), ("Live agent", "sup:agent")],
    [("Help Centre", "sup:help"), ("My support tickets", "nav:tickets")],
    [("◀ Back", "nav:back")],
)


# ── Getting Started ──────────────────────────────────────────────────
KB_GETTING_STARTED = _mk(
    [("How to sign up", "gs:signup"), ("Documents I'll need", "gs:docs")],
    [("How long does it take?", "gs:time")],
    [("◀ Back", "nav:back")],
)


# ── Status / OTP flow ────────────────────────────────────────────────
KB_STATUS_POST = _mk(
    [("Flag for onboarding team", "status:flag"), ("Live agent", "nav:support")],
    [("View onboarding info", "status:info")],
    [("◀ Back", "nav:back")],
)

KB_OTP_RESEND_OPTIONS = _mk(
    [("Resend code", "otp:resend"), ("Change email", "otp:change_email")],
    [("Contact support", "nav:support"), ("◀ Back", "nav:back")],
)

KB_OTP_EXPIRED = _mk(
    [("Yes, send new code", "otp:resend"), ("No, cancel", "nav:back")],
)

KB_OTP_LOCKED = _mk(
    [("Contact support", "nav:support"), ("◀ Back", "nav:back")],
)

# Cancel out of OTP flow at any point
KB_OTP_CANCEL = _mk(
    [("Change email", "otp:change_email"), ("Cancel", "nav:back")],
)


# ── Frustration / urgency ───────────────────────────────────────────
KB_URGENCY = _mk(
    [("Live agent now", "sup:agent"), ("Priority flag", "sup:flag")],
    [("◀ Back", "nav:back")],
)


# ── Feedback ──────────────────────────────────────────────────────────
def kb_feedback(context_id: str = "general") -> InlineKeyboardMarkup:
    """Thumbs up/down feedback after answering a question."""
    return _mk(
        [("👍 Helpful", f"fb:yes:{context_id}"), ("👎 Not helpful", f"fb:no:{context_id}")],
    )


# ── Utility keyboards with breadcrumb navigation ─────────────────────

def kb_ask_back(section: str) -> InlineKeyboardMarkup:
    """Breadcrumb: back to parent section + main menu."""
    labels = {
        "about": "About Endl",
        "currencies": "Currencies",
        "payments": "Payments",
        "onboarding": "Onboarding",
        "card": "Visa Cards",
        "security": "Security",
        "getting_started": "Getting Started",
        "support": "Support",
    }
    label = labels.get(section, section.title())
    return _mk(
        [(f"◀ Back to {label}", f"nav:{section}"), ("🏠 Main Menu", "nav:back")],
    )


def kb_back() -> InlineKeyboardMarkup:
    return _mk([("◀ Back", "nav:back")])


def kb_support_back() -> InlineKeyboardMarkup:
    return _mk(
        [("Contact support", "nav:support"), ("◀ Back", "nav:back")],
    )


# ── Contextual follow-up keyboards (related questions after answers) ─

def kb_followup_curr_supported() -> InlineKeyboardMarkup:
    """After answering 'supported currencies' → suggest fees & stablecoins."""
    return _mk(
        [("Transaction fees", "curr:fees"), ("Stablecoins supported", "curr:stablecoins")],
        [("◀ Back to Currencies", "nav:currencies"), ("🏠 Main Menu", "nav:back")],
    )

def kb_followup_curr_fees() -> InlineKeyboardMarkup:
    """After answering 'transaction fees' → suggest FX & currencies."""
    return _mk(
        [("FX conversion fees", "curr:fx"), ("Supported currencies", "curr:supported")],
        [("◀ Back to Currencies", "nav:currencies"), ("🏠 Main Menu", "nav:back")],
    )

def kb_followup_curr_fx() -> InlineKeyboardMarkup:
    """After answering 'FX fees' → suggest fees & support."""
    return _mk(
        [("Transaction fees", "curr:fees"), ("Talk to support", "nav:support")],
        [("◀ Back to Currencies", "nav:currencies"), ("🏠 Main Menu", "nav:back")],
    )

def kb_followup_curr_stablecoins() -> InlineKeyboardMarkup:
    """After answering 'stablecoins' → suggest currencies & convert."""
    return _mk(
        [("Supported currencies", "curr:supported"), ("Convert funds", "pay:convert")],
        [("◀ Back to Currencies", "nav:currencies"), ("🏠 Main Menu", "nav:back")],
    )

def kb_followup_pay_receive() -> InlineKeyboardMarkup:
    return _mk(
        [("Virtual accounts", "pay:virtual"), ("Payment rails", "pay:rails")],
        [("◀ Back to Payments", "nav:payments"), ("🏠 Main Menu", "nav:back")],
    )

def kb_followup_pay_virtual() -> InlineKeyboardMarkup:
    return _mk(
        [("Receive payments", "pay:receive"), ("Payment rails", "pay:rails")],
        [("◀ Back to Payments", "nav:payments"), ("🏠 Main Menu", "nav:back")],
    )

def kb_followup_pay_swift_out() -> InlineKeyboardMarkup:
    return _mk(
        [("Receive SWIFT", "pay:swift_in"), ("Payment rails", "pay:rails")],
        [("◀ Back to Payments", "nav:payments"), ("🏠 Main Menu", "nav:back")],
    )

def kb_followup_pay_swift_in() -> InlineKeyboardMarkup:
    return _mk(
        [("Payment rails", "pay:rails"), ("Send SWIFT", "pay:swift_out")],
        [("◀ Back to Payments", "nav:payments"), ("🏠 Main Menu", "nav:back")],
    )

def kb_followup_pay_time() -> InlineKeyboardMarkup:
    return _mk(
        [("Payment rails", "pay:rails"), ("Payment delayed", "pay:delayed")],
        [("◀ Back to Payments", "nav:payments"), ("🏠 Main Menu", "nav:back")],
    )

def kb_followup_pay_rails() -> InlineKeyboardMarkup:
    return _mk(
        [("Withdrawal times", "pay:time"), ("SWIFT transfers", "pay:swift_out")],
        [("◀ Back to Payments", "nav:payments"), ("🏠 Main Menu", "nav:back")],
    )

def kb_followup_pay_delayed() -> InlineKeyboardMarkup:
    return _mk(
        [("Contact support", "nav:support"), ("Withdrawal times", "pay:time")],
        [("◀ Back to Payments", "nav:payments"), ("🏠 Main Menu", "nav:back")],
    )

def kb_followup_onb_docs() -> InlineKeyboardMarkup:
    return _mk(
        [("📊 Check my status", "status:check"), ("How long does it take?", "onb:time")],
        [("◀ Back to Onboarding", "nav:onboarding"), ("🏠 Main Menu", "nav:back")],
    )

def kb_followup_onb_time() -> InlineKeyboardMarkup:
    return _mk(
        [("📊 Check my status", "status:check"), ("Required documents", "onb:docs")],
        [("◀ Back to Onboarding", "nav:onboarding"), ("🏠 Main Menu", "nav:back")],
    )

def kb_followup_card_offered() -> InlineKeyboardMarkup:
    return _mk(
        [("Get a Visa card", "card:apply"), ("Issue for team", "card:issue")],
        [("◀ Back to Visa Cards", "nav:card"), ("🏠 Main Menu", "nav:back")],
    )

def kb_followup_card_issue() -> InlineKeyboardMarkup:
    return _mk(
        [("Set spending limits", "card:limits"), ("Manage expenses", "card:manage")],
        [("◀ Back to Visa Cards", "nav:card"), ("🏠 Main Menu", "nav:back")],
    )

def kb_followup_card_apply() -> InlineKeyboardMarkup:
    return _mk(
        [("Issue for team", "card:issue"), ("Set spending limits", "card:limits")],
        [("◀ Back to Visa Cards", "nav:card"), ("🏠 Main Menu", "nav:back")],
    )

def kb_followup_about(exclude: str = "") -> InlineKeyboardMarkup:
    """Generic about follow-up, excluding the question just answered."""
    options = [
        ("What is Endl?", "about:what_is"),
        ("Who can use Endl?", "about:who"),
        ("Is Endl regulated?", "about:regulated"),
        ("Endl vs Wise/Payoneer", "about:different"),
    ]
    filtered = [(l, c) for l, c in options if c != f"about:{exclude}"][:2]
    return _mk(
        filtered,
        [("◀ Back to About", "nav:about"), ("🏠 Main Menu", "nav:back")],
    )


# ── Status check confirmation (soft trigger) ─────────────────────────
KB_STATUS_CONFIRM = _mk(
    [("Yes, check my status", "status:check"), ("No, something else", "nav:back")],
)


def kb_status_support_back() -> InlineKeyboardMarkup:
    return _mk(
        [("📊 Check my status", "status:check"), ("Talk to support", "nav:support")],
        [("◀ Back", "nav:back")],
    )


# ── Group Quick Menu keyboards ────────────────────────────────────────

KB_GROUP_MAIN = _mk(
    [("ℹ️ What is Endl?", "grp:about"), ("💱 Currencies & fees", "grp:currencies")],
    [("📤 Payments & transfers", "grp:payments"), ("📋 Onboarding info", "grp:onboarding")],
    [("🛡️ Security", "grp:security"), ("🔐 Check my account status", "grp:status")],
)

KB_GROUP_ABOUT = _mk(
    [("Who is it for?", "grp:about_who"), ("Is Endl regulated?", "grp:about_regulated")],
    [("Endl vs Wise?", "grp:about_wise")],
    [("◀ Back", "grp:back")],
)

KB_GROUP_CURRENCIES = _mk(
    [("What currencies?", "grp:curr_supported"), ("What are the fees?", "grp:curr_fees")],
    [("What stablecoins?", "grp:curr_stablecoins")],
    [("◀ Back", "grp:back")],
)

KB_GROUP_PAYMENTS = _mk(
    [("Receive payments", "grp:pay_receive"), ("Payment rails", "grp:pay_rails")],
    [("Send SWIFT", "grp:pay_swift"), ("Withdrawal times", "grp:pay_time")],
    [("◀ Back", "grp:back")],
)

KB_GROUP_ONBOARDING = _mk(
    [("How long?", "grp:onb_time"), ("What documents?", "grp:onb_docs")],
    [("Onboarding delayed?", "grp:onb_delayed")],
    [("◀ Back", "grp:back")],
)

KB_GROUP_SECURITY = _mk(
    [("Is my money safe?", "grp:sec_safe"), ("Data protection", "grp:sec_data")],
    [("Transaction monitoring", "grp:sec_monitoring")],
    [("◀ Back", "grp:back")],
)

KB_GROUP_BACK = _mk([("◀ Back", "grp:back")])

KB_GROUP_BACK_WITH_STATUS = _mk(
    [("🔐 Check my account status", "grp:status")],
    [("◀ Back", "grp:back")],
)


# ── Post image-analysis keyboard ─────────────────────────────────────
KB_IMAGE_ANALYZED = _mk(
    [("Flag for support team", "sup:flag"), ("Upload another image", "nav:back")],
    [("🏠 Main Menu", "nav:back")],
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
        "image_analyzed": KB_IMAGE_ANALYZED,
        "main_menu":      kb_main(account_type),
    }
    return mapping.get(name, kb_main(account_type))
