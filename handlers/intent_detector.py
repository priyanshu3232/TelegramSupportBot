_INTENT_KEYWORDS: dict[str, list[str]] = {
    "escalation": [
        "human", "agent", "speak to someone", "live support", "call me", "phone",
        "locked", "frozen", "suspended", "fraud", "unauthorized", "stolen",
        "dispute", "legal", "tax", "regulatory", "bug", "glitch", "broken",
        "transaction id", "reference number",
        "tax id", "tax number", "trn", "no tax id", "don't have tax id",
        "personal iban", "personal european iban", "personal account iban",
        "only swift", "can only send swift", "must use swift", "swift only option",
    ],
    "rejection_error": [
        "rejected", "failed", "error", "blurry", "expired", "mismatch",
        "declined", "not accepted", "resubmit", "try again", "wrong",
        "issue with my", "problem with",
    ],
    "status_progress": [
        "status", "progress", "where am i", "how long", "waiting", "when will",
        "approved", "pending", "in progress", "review", "how long does it take",
        "onboarding time", "still waiting", "any update", "dashboard",
        "verification successful", "partner bank",
    ],
    "document_help": [
        "document", "upload", "passport", "driver", "license", "licence",
        "proof of address", "utility bill", "bank statement", "selfie",
        "liveness", "photo", "file format", "file size", "what do i need",
        "what documents", "company registration", "shareholder", "memorandum",
        "moa", "ubo",
    ],
    "payment_receiving": [
        "receive payment", "receive money", "receive transfer", "incoming payment",
        "virtual account", "iban", "sepa", "ach", "fedwire", "faster payments",
        "pix", "spei", "clabe", "swift incoming", "receive swift",
        "receive from", "how do i get paid", "collect payment",
    ],
    "payment_sending": [
        "send payment", "send money", "payout", "payouts", "swift outgoing",
        "send swift", "salary", "salaries", "pay employee", "pay vendor",
        "withdrawal", "withdraw", "send to personal", "business only",
    ],
    "privacy_data": [
        "privacy", "data", "gdpr", "delete my data", "who can see",
        "retention", "how long do you keep", "personal information", "security",
    ],
    "eligibility": [
        "eligible", "qualify", "supported countries", "can i use", "age",
        "minor", "non citizen", "which countries", "available in", "requirements",
        "uae", "dubai", "emirates",
    ],
}

# Priority order for when multiple intents match
_PRIORITY = [
    "escalation", "rejection_error", "status_progress",
    "payment_receiving", "payment_sending",
    "document_help", "privacy_data", "eligibility",
]


def detect_intent(message: str, user_type: str | None = None) -> str:
    lower = message.lower()

    matched = []
    for intent, keywords in _INTENT_KEYWORDS.items():
        if any(kw in lower for kw in keywords):
            matched.append(intent)

    if not matched:
        return "general"

    for intent in _PRIORITY:
        if intent in matched:
            return intent

    return matched[0]
