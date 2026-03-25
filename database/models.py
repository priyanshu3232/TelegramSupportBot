from database.db import get_connection


async def get_session(chat_id: int, user_id: int) -> dict | None:
    session_key = f"{chat_id}_{user_id}"
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT * FROM sessions WHERE session_key = ?", (session_key,)
        )
        row = await cursor.fetchone()
        if row:
            return dict(row)
        return None
    finally:
        await conn.close()


async def get_or_create_session(chat_id: int, user_id: int) -> dict:
    session_key = f"{chat_id}_{user_id}"
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT * FROM sessions WHERE session_key = ?", (session_key,)
        )
        row = await cursor.fetchone()
        if row:
            return dict(row)
        await conn.execute(
            "INSERT INTO sessions (chat_id, user_id, session_key, conversation_state) VALUES (?, ?, ?, ?)",
            (chat_id, user_id, session_key, "greeting"),
        )
        await conn.commit()
        cursor = await conn.execute(
            "SELECT * FROM sessions WHERE session_key = ?", (session_key,)
        )
        row = await cursor.fetchone()
        return dict(row)
    finally:
        await conn.close()


async def update_session(session_key: str, **kwargs) -> None:
    if not kwargs:
        return
    set_clause = ", ".join(f"{k} = ?" for k in kwargs)
    values = list(kwargs.values())
    values.append(session_key)
    conn = await get_connection()
    try:
        await conn.execute(
            f"UPDATE sessions SET {set_clause}, updated_at = CURRENT_TIMESTAMP WHERE session_key = ?",
            values,
        )
        await conn.commit()
    finally:
        await conn.close()


async def save_message(session_key: str, role: str, content: str) -> None:
    conn = await get_connection()
    try:
        await conn.execute(
            "INSERT INTO conversation_history (session_key, role, content) VALUES (?, ?, ?)",
            (session_key, role, content),
        )
        await conn.commit()
    finally:
        await conn.close()


async def get_conversation_history(session_key: str, limit: int = 10) -> list[dict]:
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT role, content FROM conversation_history WHERE session_key = ? ORDER BY id DESC LIMIT ?",
            (session_key, limit),
        )
        rows = await cursor.fetchall()
        return [{"role": row["role"], "content": row["content"]} for row in reversed(rows)]
    finally:
        await conn.close()


async def save_ticket(
    ticket_id: str,
    session_key: str,
    user_id: int,
    chat_id: int,
    user_type: str | None,
    issue_category: str,
    issue_summary: str,
    conversation_transcript: str,
    severity: str,
) -> None:
    conn = await get_connection()
    try:
        await conn.execute(
            """INSERT INTO escalation_tickets
               (ticket_id, session_key, user_id, chat_id, user_type, issue_category,
                issue_summary, conversation_transcript, severity)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (ticket_id, session_key, user_id, chat_id, user_type, issue_category,
             issue_summary, conversation_transcript, severity),
        )
        await conn.commit()
    finally:
        await conn.close()


async def get_user_tickets(user_id: int) -> list[dict]:
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT ticket_id, issue_category, severity, status, created_at FROM escalation_tickets WHERE user_id = ? ORDER BY created_at DESC LIMIT 5",
            (user_id,),
        )
        rows = await cursor.fetchall()
        return [dict(row) for row in rows]
    finally:
        await conn.close()


async def get_recent_intents(session_key: str, limit: int = 3) -> list[str]:
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT detected_intent FROM conversation_logs WHERE session_key = ? ORDER BY id DESC LIMIT ?",
            (session_key, limit),
        )
        rows = await cursor.fetchall()
        return [row["detected_intent"] for row in rows if row["detected_intent"]]
    finally:
        await conn.close()


async def save_verified_user(chat_id: int, user_id: int, email: str) -> None:
    """Permanently store a verified email ↔ chat_id mapping."""
    conn = await get_connection()
    try:
        await conn.execute(
            """INSERT INTO verified_users (chat_id, user_id, email)
               VALUES (?, ?, ?)
               ON CONFLICT(user_id, email) DO UPDATE SET chat_id = ?, verified_at = CURRENT_TIMESTAMP""",
            (chat_id, user_id, email, chat_id),
        )
        await conn.commit()
    finally:
        await conn.close()


async def get_verified_email(user_id: int) -> str | None:
    """Get the verified email for a user (most recent)."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT email FROM verified_users WHERE user_id = ? ORDER BY verified_at DESC LIMIT 1",
            (user_id,),
        )
        row = await cursor.fetchone()
        return row["email"] if row else None
    finally:
        await conn.close()
