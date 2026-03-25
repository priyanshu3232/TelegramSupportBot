def classify_user_type(message: str) -> str | None:
    text = message.lower().strip()

    individual_keywords = [
        "individual", "personal", "person", "myself", "just me",
        "i am an individual", "single user",
    ]
    business_keywords = [
        "business", "company", "corporate", "organization", "organisation",
        "enterprise", "firm", "startup", "agency",
    ]

    is_individual = any(kw in text for kw in individual_keywords)
    is_business = any(kw in text for kw in business_keywords)

    if is_individual and not is_business:
        return "individual"
    if is_business and not is_individual:
        return "business"
    return None
