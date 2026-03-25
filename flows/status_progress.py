INDIVIDUAL_STATUS = (
    "I do not have access to your individual account status. "
    "Typically, onboarding involves document submission, review by our team, "
    "and final verification. KYC verification for individuals usually takes "
    "approximately 1 business day. You can check your current status in your "
    "Endl dashboard, and you will receive a notification once verification is complete."
)

BUSINESS_STATUS = (
    "I do not have access to your individual account status. "
    "Typically, onboarding involves document submission, review by our team, "
    "and final verification. KYB verification for businesses usually takes "
    "approximately 2 to 4 business days. You can check your current status in your "
    "Endl dashboard, and you will receive a notification once verification is complete."
)


def get_status_guidance(user_type: str | None) -> str:
    if user_type == "business":
        return BUSINESS_STATUS
    return INDIVIDUAL_STATUS
