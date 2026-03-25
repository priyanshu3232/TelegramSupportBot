import time
from database.models import save_ticket, get_conversation_history, update_session
from ai.claude_client import get_ai_response
from config import SUPPORT_LINK

_HIGH_SEVERITY_KEYWORDS = [
    "fraud", "unauthorized", "locked", "frozen", "suspended", "stolen",
]


async def handle_escalation(
    session_key: str,
    user_id: int,
    chat_id: int,
    user_type: str | None,
    detected_intent: str,
    is_repeat_failure: bool = False,
) -> tuple[str, str]:
    """Create an escalation ticket and return (ticket_id, response_message)."""

    # Determine severity
    severity = "low"
    if is_repeat_failure:
        severity = "high"
    else:
        history = await get_conversation_history(session_key, limit=5)
        transcript_text = "\n".join(f"{m['role']}: {m['content']}" for m in history)
        lower_transcript = transcript_text.lower()
        if any(kw in lower_transcript for kw in _HIGH_SEVERITY_KEYWORDS):
            severity = "high"

    # Get conversation history for transcript
    history = await get_conversation_history(session_key, limit=20)
    transcript = "\n".join(f"{m['role']}: {m['content']}" for m in history)

    # Generate AI summary
    try:
        summary = await get_ai_response(
            system_prompt="Summarize the following support conversation in 1 to 2 sentences. Focus on what the user needs help with.",
            conversation_history=[],
            user_message=transcript,
        )
    except Exception:
        summary = f"User needs help with: {detected_intent}"

    # Create ticket
    ticket_id = f"ESC-{int(time.time())}-{user_id}"

    issue_category = detected_intent if detected_intent != "escalation" else "other"

    await save_ticket(
        ticket_id=ticket_id,
        session_key=session_key,
        user_id=user_id,
        chat_id=chat_id,
        user_type=user_type,
        issue_category=issue_category,
        issue_summary=summary,
        conversation_transcript=transcript,
        severity=severity,
    )

    # Update session state
    await update_session(session_key, conversation_state="escalated")

    # Build response
    if severity == "high":
        response = (
            f"Priority ticket created: {ticket_id}\n"
            f"Our team will follow up ASAP. Direct link: {SUPPORT_LINK}"
        )
    else:
        response = (
            f"Ticket created: {ticket_id}\n"
            f"Our team typically responds within 24h. Link: {SUPPORT_LINK}"
        )

    return ticket_id, response
