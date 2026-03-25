import sys
from database.db import get_connection


async def log_interaction(
    session_key: str,
    user_id: int,
    chat_id: int,
    chat_type: str,
    user_message: str,
    bot_response: str,
    detected_intent: str | None = None,
    user_type: str | None = None,
    was_cached: bool = False,
    was_escalated: bool = False,
    response_time_ms: int = 0,
) -> None:
    try:
        conn = await get_connection()
        try:
            await conn.execute(
                """INSERT INTO conversation_logs
                   (session_key, user_id, chat_id, chat_type, user_message, bot_response,
                    detected_intent, user_type, was_cached, was_escalated, response_time_ms)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    session_key, user_id, chat_id, chat_type, user_message, bot_response,
                    detected_intent, user_type, was_cached, was_escalated, response_time_ms,
                ),
            )
            await conn.commit()
        finally:
            await conn.close()
    except Exception as e:
        print(f"[logger] Failed to log interaction: {e}", file=sys.stderr)
