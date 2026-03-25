import logging

import httpx
from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, CLAUDE_MAX_TOKENS, CLAUDE_TEMPERATURE, SUPPORT_LINK

logger = logging.getLogger(__name__)

_API_URL = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_VERSION = "2023-06-01"
_TIMEOUT = 60.0


async def get_ai_response(
    system_prompt: str,
    conversation_history: list[dict],
    user_message: str,
) -> str:
    # Build messages: keep last 10 from history + new user message
    messages = conversation_history[-10:]
    messages.append({"role": "user", "content": user_message})

    # Ensure messages alternate correctly starting with user
    cleaned: list[dict] = []
    for msg in messages:
        if cleaned and cleaned[-1]["role"] == msg["role"]:
            cleaned[-1]["content"] += "\n" + msg["content"]
        else:
            cleaned.append(dict(msg))

    # Must start with user role — if the history starts with an assistant
    # message, prepend a synthetic user turn so the API accepts the messages
    if cleaned and cleaned[0]["role"] != "user":
        cleaned.insert(0, {"role": "user", "content": "[conversation started]"})

    if not cleaned:
        cleaned = [{"role": "user", "content": user_message}]

    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": CLAUDE_MAX_TOKENS,
        "temperature": CLAUDE_TEMPERATURE,
        "system": system_prompt,
        "messages": cleaned,
    }

    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": _ANTHROPIC_VERSION,
        "content-type": "application/json",
    }

    try:
        logger.info(
            "Sending request to Claude: model=%s, max_tokens=%s, messages_count=%d",
            CLAUDE_MODEL, CLAUDE_MAX_TOKENS, len(cleaned),
        )
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            response = await client.post(_API_URL, headers=headers, json=payload)

        if response.status_code != 200:
            error_body = response.text[:300]
            logger.error("Claude API returned status %s: %s", response.status_code, error_body)

            if response.status_code == 401:
                logger.error("API key is invalid or expired")
            elif response.status_code == 429:
                return "I am experiencing high demand. Please try again in a moment."
            elif response.status_code == 404:
                logger.error("Model '%s' not found — check CLAUDE_MODEL in .env", CLAUDE_MODEL)

            return (
                "Something went wrong on my end. Please try again, or reach out to "
                f"our live support: {SUPPORT_LINK}"
            )

        data = response.json()
        text = data["content"][0]["text"]
        logger.info(
            "Claude response received: stop_reason=%s, text_length=%d",
            data.get("stop_reason"),
            len(text),
        )
        return text

    except httpx.TimeoutException:
        logger.warning("Claude API request timed out after %ss", _TIMEOUT)
        return "I am taking a bit longer than usual. Please try again in a moment."
    except Exception as e:
        import traceback as tb
        logger.error("Unexpected error calling AI: %s (type=%s)", e, type(e).__name__, exc_info=True)
        logger.error("AI call traceback: %s", tb.format_exc())
        logger.error(
            "AI call context: model=%s, messages_count=%d, user_msg_len=%d",
            CLAUDE_MODEL, len(cleaned), len(user_message),
        )
        return (
            "Something went wrong on my end. Please try again, or reach out to "
            f"our live support: {SUPPORT_LINK}"
        )
