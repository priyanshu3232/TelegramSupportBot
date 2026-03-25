import re

# Patterns that indicate the AI generated a forbidden welcome/intro message
_WELCOME_PATTERNS = [
    re.compile(r"welcome to endl", re.IGNORECASE),
    re.compile(r"your trusted platform", re.IGNORECASE),
    re.compile(r"with endl,?\s+you can", re.IGNORECASE),
    re.compile(r"what would you like to do today", re.IGNORECASE),
    re.compile(r"(register|view wallet|send coins|get help).*\n.*(register|view wallet|send coins|get help)", re.IGNORECASE | re.DOTALL),
    re.compile(r"global payments and stablecoin", re.IGNORECASE),
    re.compile(r"send and receive funds globally", re.IGNORECASE),
    re.compile(r"multi.?currency accounts", re.IGNORECASE),
    re.compile(r"instant settlements", re.IGNORECASE),
    re.compile(r"minimal fx fees", re.IGNORECASE),
    re.compile(r"here.s what (endl|we) (can|offer)", re.IGNORECASE),
    re.compile(r"endl (is|offers|provides|allows)", re.IGNORECASE),
    re.compile(r"stablecoin (transfers|settlement)", re.IGNORECASE),
    re.compile(r"how can i assist you today", re.IGNORECASE),
    re.compile(r"manage.+from (one|your) dashboard", re.IGNORECASE),
]

_FALLBACK_RESPONSE = "How can I help you today?"


def _is_welcome_message(text: str) -> bool:
    """Return True if the response looks like a forbidden welcome/intro block."""
    # Strong match: "welcome to endl" is always a welcome message
    if re.search(r"welcome to endl", text, re.IGNORECASE):
        return True
    # Weaker patterns: need 3+ matches to avoid false positives on legitimate
    # responses that happen to mention features like "register" or "stablecoin"
    matches = sum(1 for p in _WELCOME_PATTERNS if p.search(text))
    return matches >= 3


def sanitize_response(text: str) -> str:
    # Catch AI-generated welcome messages that violate the system prompt
    if _is_welcome_message(text):
        return _FALLBACK_RESPONSE

    # Replace dash bullets at start of lines with numbered format
    lines = text.split("\n")
    counter = 0
    result_lines = []
    for line in lines:
        stripped = line.lstrip()
        if stripped.startswith("- ") or stripped.startswith("— ") or stripped.startswith("– "):
            counter += 1
            indent = line[: len(line) - len(stripped)]
            content = stripped[2:]
            result_lines.append(f"{indent}{counter}. {content}")
        else:
            if not (stripped.startswith("- ") or stripped.startswith("— ") or stripped.startswith("– ")):
                counter = 0
            result_lines.append(line)
    text = "\n".join(result_lines)

    # Replace remaining em/en dashes used as separators (not in words)
    text = re.sub(r"\s[—–]\s", " ", text)

    # Remove markdown bold
    text = re.sub(r"\*\*(.+?)\*\*", r"\1", text)

    # Telegram message limit
    if len(text) > 4096:
        text = text[:4050] + "\n\n... For more details, please reach out to our support team."

    return text.strip()
