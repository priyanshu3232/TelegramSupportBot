INDIVIDUAL_DOCS = (
    "To complete your onboarding as an individual, you will need:\n\n"
    "1. Identity document (passport, national ID, or driver's license)\n"
    "2. Proof of address (utility bill or bank statement within the last 3 months)\n"
    "3. Selfie verification\n\n"
    "Please ensure all documents are clear, legible, and all four corners are visible."
)

BUSINESS_DOCS = (
    "To complete your onboarding as a business, you will need:\n\n"
    "1. Company registration documents\n"
    "2. Shareholder details\n"
    "3. Articles or Memorandum of Association\n"
    "4. UBO identity verification\n"
    "5. Proof of business activity (website, invoices, or contracts)\n"
    "6. Business description\n\n"
    "Additional documents may be requested depending on your jurisdiction."
)


def get_document_guidance(user_type: str | None) -> str:
    if user_type == "business":
        return BUSINESS_DOCS
    return INDIVIDUAL_DOCS
