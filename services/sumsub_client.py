import hashlib
import hmac
import logging
import time

import httpx

from config import SUMSUB_APP_TOKEN, SUMSUB_SECRET_KEY, SUMSUB_BASE_URL

logger = logging.getLogger(__name__)

_TIMEOUT = 30.0


def _sign_request(method: str, path: str, body: bytes = b"") -> dict:
    """Generate SumSub HMAC authentication headers."""
    ts = str(int(time.time()))
    sig_data = ts.encode() + method.upper().encode() + path.encode() + body
    signature = hmac.new(
        SUMSUB_SECRET_KEY.encode(), sig_data, hashlib.sha256
    ).hexdigest()
    return {
        "X-App-Token": SUMSUB_APP_TOKEN,
        "X-App-Access-Sig": signature,
        "X-App-Access-Ts": ts,
        "Content-Type": "application/json",
    }


async def search_applicant_by_email(email: str) -> dict | None:
    """Search SumSub for an applicant by email. Returns applicant dict or None."""
    if not SUMSUB_APP_TOKEN or not SUMSUB_SECRET_KEY:
        logger.error("SumSub credentials not configured")
        return None

    path = "/resources/applicants/search"
    body = f'{{"email": "{email}"}}'.encode()
    headers = _sign_request("POST", path, body)

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.post(
                f"{SUMSUB_BASE_URL}{path}", headers=headers, content=body,
            )

        if resp.status_code != 200:
            logger.error("SumSub search failed (%s): %s", resp.status_code, resp.text[:200])
            return None

        data = resp.json()
        items = data.get("items", [])
        if not items:
            return None
        return items[0]
    except Exception as e:
        logger.error("SumSub search error: %s", e)
        return None


async def get_applicant_status(applicant_id: str) -> dict | None:
    """Get the review status for an applicant."""
    path = f"/resources/applicants/{applicant_id}/one"
    headers = _sign_request("GET", path)

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(f"{SUMSUB_BASE_URL}{path}", headers=headers)

        if resp.status_code != 200:
            logger.error("SumSub status failed (%s): %s", resp.status_code, resp.text[:200])
            return None

        return resp.json()
    except Exception as e:
        logger.error("SumSub status error: %s", e)
        return None


async def get_document_status(applicant_id: str) -> list[dict] | None:
    """Get document verification status for an applicant."""
    path = f"/resources/applicants/{applicant_id}/requiredIdDocsStatus"
    headers = _sign_request("GET", path)

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as client:
            resp = await client.get(f"{SUMSUB_BASE_URL}{path}", headers=headers)

        if resp.status_code != 200:
            logger.error("SumSub docs failed (%s): %s", resp.status_code, resp.text[:200])
            return None

        return resp.json()
    except Exception as e:
        logger.error("SumSub docs error: %s", e)
        return None


def format_status_message(applicant: dict, doc_status: list[dict] | None) -> str:
    """Format SumSub applicant data into a user-friendly Telegram message."""
    review = applicant.get("review", {})
    review_status = review.get("reviewStatus", "unknown")
    review_result = review.get("reviewResult", {})
    label = review_result.get("reviewAnswer", "").upper()

    status_emoji = {
        "completed": "\u2705",
        "pending": "\u23f3",
        "queued": "\u23f3",
        "onHold": "\u270b",
        "init": "\U0001f195",
        "prechecked": "\u23f3",
    }
    emoji = status_emoji.get(review_status, "\u2753")

    lines = [
        f"{emoji} Onboarding Status: {review_status.replace('_', ' ').title()}",
    ]

    if label:
        answer_emoji = "\u2705" if label == "GREEN" else "\u274c" if label == "RED" else "\u26a0\ufe0f"
        lines.append(f"{answer_emoji} Review Result: {label}")

    reject_labels = review_result.get("rejectLabels", [])
    if reject_labels:
        lines.append(f"Reason: {', '.join(reject_labels)}")

    if doc_status:
        lines.append("\nDocument Status:")
        for doc in doc_status:
            doc_type = doc.get("idDocType", "Unknown")
            doc_review = doc.get("reviewResult", {})
            doc_answer = doc_review.get("reviewAnswer", "pending")
            doc_emoji = "\u2705" if doc_answer == "GREEN" else "\u274c" if doc_answer == "RED" else "\u23f3"
            lines.append(f"  {doc_emoji} {doc_type}: {doc_answer}")

            reject_reason = doc_review.get("rejectLabels", [])
            if reject_reason:
                lines.append(f"     Reason: {', '.join(reject_reason)}")

    lines.append("\nAnything else I can help with?")
    return "\n".join(lines)
