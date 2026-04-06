"""
Claude Vision service — send images to Claude for intelligent analysis.
Uses the same httpx + Anthropic Messages API pattern as claude_client.py.
"""
import base64
import json
import logging
import re

import httpx

from config import ANTHROPIC_API_KEY, CLAUDE_MODEL, SUPPORT_LINK

logger = logging.getLogger(__name__)

_API_URL = "https://api.anthropic.com/v1/messages"
_ANTHROPIC_VERSION = "2023-06-01"
_TIMEOUT = 60.0

_VISION_FALLBACK = {
    "analysis": (
        "I wasn't able to fully analyse that image. "
        "Please describe what you're seeing in text and I'll do my best to help."
    ),
    "intent": "unclear",
    "is_error": False,
    "is_document": False,
    "is_screenshot": False,
    "suggested_action": "Describe the issue in text.",
    "confidence": 0.0,
    "buttons": "support",
}


def build_vision_system_prompt(account_type: str, ocr_text: str | None) -> str:
    ocr_block = (
        f"OCR extracted text from the image:\n{ocr_text}\n"
        if ocr_text
        else "No OCR text was extracted from this image.\n"
    )
    return f"""You are Endl Support Bot's visual analysis system. You analyse images sent by users to provide intelligent support.

CONTEXT: The user is a {account_type} customer of Endl, a global business payments platform.

{ocr_block}
ANALYSIS TASKS:
1. CLASSIFY the image: error screenshot, document/ID, form, transaction receipt, chat screenshot, or other.
2. If ERROR SCREENSHOT: identify the exact error message, what screen/page it is on, and what likely caused it. Provide specific steps to resolve.
3. If DOCUMENT/ID: identify the document type (passport, national ID, utility bill, company registration, etc.). Do NOT read or repeat any personal information (names, ID numbers, dates of birth). Only identify the type and whether it appears complete and legible.
4. If FORM/APPLICATION: identify which fields are shown, whether any have errors or validation messages, and guide the user on how to fill them correctly.
5. If TRANSACTION/RECEIPT: identify the transaction type and status. Do NOT repeat amounts, account numbers, or reference numbers.

RESPONSE FORMAT — Return valid JSON only, no markdown fences:
{{
  "analysis": "Your 1-3 sentence analysis for the user. Be specific and actionable.",
  "intent": "one of: error_screenshot, document_upload, form_issue, transaction_issue, general_image, unclear",
  "is_error": true or false,
  "is_document": true or false,
  "is_screenshot": true or false,
  "suggested_action": "Specific next step the user should take",
  "confidence": 0.0 to 1.0,
  "buttons": "one of: support, main_menu, onboarding, status_flow"
}}

SECURITY RULES:
1. NEVER read out or repeat personal information visible in documents (names, ID numbers, DOB, addresses).
2. NEVER confirm or deny document validity — that is done by the verification team.
3. If the image contains sensitive financial data, acknowledge it without repeating the numbers.
4. If the image is inappropriate or unrelated to support, politely redirect.

BREVITY: Keep analysis under 4 sentences. This is Telegram — short messages only."""


async def analyze_image_with_vision(
    image_path: str,
    mime_type: str,
    user_context: str,
    account_type: str,
    conversation_history: list[dict],
    ocr_text: str | None = None,
) -> dict:
    """
    Send image to Claude Vision API for intelligent analysis.
    Returns structured analysis dict.
    """
    # Read and base64-encode the image
    try:
        with open(image_path, "rb") as f:
            image_data = base64.standard_b64encode(f.read()).decode("utf-8")
    except Exception as e:
        logger.error("Failed to read image for Vision API: %s", e)
        return _VISION_FALLBACK

    system_prompt = build_vision_system_prompt(account_type, ocr_text)

    user_text = user_context if user_context else "The user sent an image without a description."
    if ocr_text:
        user_text += f"\n\nOCR extracted text:\n{ocr_text[:1000]}"

    messages = [
        {
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": mime_type,
                        "data": image_data,
                    },
                },
                {"type": "text", "text": user_text},
            ],
        }
    ]

    payload = {
        "model": CLAUDE_MODEL,
        "max_tokens": 512,
        "temperature": 0.2,
        "system": system_prompt,
        "messages": messages,
    }
    headers = {
        "x-api-key": ANTHROPIC_API_KEY,
        "anthropic-version": _ANTHROPIC_VERSION,
        "content-type": "application/json",
    }

    raw_text = ""
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(_API_URL, headers=headers, json=payload)

        if resp.status_code != 200:
            logger.error(
                "Vision API returned %s: %s", resp.status_code, resp.text[:200]
            )
            return _VISION_FALLBACK

        raw_text = resp.json()["content"][0]["text"].strip()
        logger.info("Vision API response: %s", raw_text[:300])

        # Strip optional markdown code fences
        text = re.sub(r"^```(?:json)?\s*", "", raw_text)
        text = re.sub(r"\s*```$", "", text).strip()

        parsed = json.loads(text)

        # Ensure required keys have defaults
        parsed.setdefault("analysis", _VISION_FALLBACK["analysis"])
        parsed.setdefault("intent", "unclear")
        parsed.setdefault("is_error", False)
        parsed.setdefault("is_document", False)
        parsed.setdefault("is_screenshot", False)
        parsed.setdefault("suggested_action", "")
        parsed.setdefault("confidence", 0.5)
        parsed.setdefault("buttons", "support")

        return parsed

    except (json.JSONDecodeError, KeyError) as exc:
        logger.warning("Vision JSON parse error: %s | raw=%s", exc, raw_text[:300])
        # Try to extract analysis text even if JSON is malformed
        if raw_text and len(raw_text) > 20:
            fallback = dict(_VISION_FALLBACK)
            fallback["analysis"] = raw_text[:400]
            return fallback
        return _VISION_FALLBACK
    except httpx.TimeoutException:
        logger.warning("Vision API request timed out")
        return _VISION_FALLBACK
    except Exception as exc:
        logger.error("Unexpected Vision API error: %s", exc, exc_info=True)
        return _VISION_FALLBACK
