REJECTION_GUIDANCE = {
    "blurry": (
        "Please retake the photo in good lighting, ensuring all four corners "
        "of the document are visible and the text is legible."
    ),
    "expired": "Please submit a valid, unexpired document.",
    "name_mismatch": (
        "Ensure the name on your document exactly matches the details "
        "you provided during registration."
    ),
    "address_mismatch": (
        "Ensure the address on your document exactly matches the details "
        "you provided during registration."
    ),
    "proof_of_address": (
        "Please resubmit a utility bill or bank statement dated within "
        "the last 3 months."
    ),
    "general": (
        "Please resubmit clear, valid, and unexpired documents. "
        "Make sure images are legible and all corners are visible."
    ),
}


def get_rejection_guidance(rejection_type: str = "general") -> str:
    return REJECTION_GUIDANCE.get(rejection_type, REJECTION_GUIDANCE["general"])
