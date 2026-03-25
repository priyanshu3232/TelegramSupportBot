_CACHE: dict[str, dict[str, str]] = {
    "what is endl": {
        "general": (
            "Endl is a global business payments platform that lets companies collect, "
            "hold, and move money internationally. Features include multi-currency accounts, "
            "stablecoin settlement, local payment collection, FX conversion, global payouts, "
            "and expense management — all from one dashboard.\n\n"
            "Anything else?"
        ),
    },
    "what currencies": {
        "general": (
            "Endl supports USD, EUR, AED, GBP, BRL, and MXN, along with stablecoins "
            "USDC and USDT. More currencies are continuously being added.\n\n"
            "Anything else?"
        ),
    },
    "is endl regulated": {
        "general": (
            "Yes. Endl holds relevant licenses and operates with regulated financial "
            "institution partners, following strict AML, KYC, and transaction monitoring "
            "frameworks.\n\n"
            "Anything else?"
        ),
    },
    "what documents": {
        "individual": (
            "To complete your onboarding as an individual, you will need:\n\n"
            "1. Government ID (passport, national ID, or driver's license)\n"
            "2. Proof of address (utility bill or bank statement)\n"
            "3. Selfie verification\n\n"
            "Anything else?"
        ),
        "business": (
            "To complete your onboarding as a business, you will need:\n\n"
            "1. Company registration documents\n"
            "2. Shareholder details\n"
            "3. Articles or Memorandum of Association\n"
            "4. UBO identity verification\n"
            "5. Proof of business activity (website or invoices)\n"
            "6. Business description\n\n"
            "Anything else?"
        ),
    },
    "corporate cards": {
        "individual": (
            "Corporate cards are currently available for business accounts only. "
            "They are not available for individual accounts.\n\n"
            "Anything else?"
        ),
        "business": (
            "Yes! Endl offers corporate cards with customizable limits and controls "
            "for team expenses and subscriptions. You can manage them from your dashboard.\n\n"
            "Anything else?"
        ),
    },
    "how long onboarding": {
        "individual": (
            "For individual accounts, onboarding typically takes approximately 1 business "
            "day. May vary based on document completeness and compliance checks.\n\n"
            "Anything else?"
        ),
        "business": (
            "For business accounts, onboarding typically takes approximately 2 to 4 "
            "business days. May vary based on document completeness and compliance checks.\n\n"
            "Anything else?"
        ),
    },
    "payment rails": {
        "general": (
            "Endl supports the following payment rails:\n\n"
            "1. USD: ACH and Fedwire\n"
            "2. EUR: SEPA, SEPA Instant (Euro IBAN)\n"
            "3. GBP: Faster Payments (FPS)\n"
            "4. AED: Local UAE bank transfer (IBAN)\n"
            "5. BRL: PIX\n"
            "6. MXN: SPEI / CLABE\n"
            "7. SWIFT outgoing: third-party business payments only\n\n"
            "SWIFT incoming is not supported. Check your virtual account details in the "
            "dashboard for the exact rails available to you.\n\n"
            "Anything else?"
        ),
    },
    "swift": {
        "individual": (
            "SWIFT incoming is not supported on Endl. For outgoing, SWIFT is available "
            "for business accounts only (third-party business payments). You can use the "
            "other payment rails available in your virtual account details.\n\n"
            "Anything else?"
        ),
        "business": (
            "SWIFT incoming is not supported on Endl. For outgoing, yes — SWIFT is available "
            "for third-party business payments. It cannot be sent to individual personal "
            "accounts. Check your virtual account details in the dashboard.\n\n"
            "Anything else?"
        ),
    },
    "available in uae": {
        "general": (
            "Yes! Endl is available for both individuals and companies in the UAE, "
            "including Dubai. AED accounts are available even to non-UAE residents.\n\n"
            "Anything else?"
        ),
    },
}


def get_cached_response(message: str, user_type: str | None) -> str | None:
    lower = message.lower().strip()
    for key, responses in _CACHE.items():
        if key in lower:
            if user_type and user_type in responses:
                return responses[user_type]
            if "general" in responses:
                return responses["general"]
            # Return any available response
            return next(iter(responses.values()))
    return None
