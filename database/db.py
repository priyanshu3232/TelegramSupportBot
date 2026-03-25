import os
import aiosqlite
from config import DB_PATH


async def get_connection() -> aiosqlite.Connection:
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = await aiosqlite.connect(DB_PATH)
    conn.row_factory = aiosqlite.Row
    await conn.execute("PRAGMA journal_mode=WAL")
    return conn


async def init_db() -> None:
    conn = await get_connection()
    try:
        await conn.executescript("""
            CREATE TABLE IF NOT EXISTS sessions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                session_key TEXT UNIQUE NOT NULL,
                user_type TEXT DEFAULT NULL,
                email TEXT DEFAULT NULL,
                conversation_state TEXT DEFAULT 'greeting',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS conversation_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_key TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (session_key) REFERENCES sessions(session_key)
            );

            CREATE TABLE IF NOT EXISTS conversation_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_key TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                chat_type TEXT NOT NULL,
                user_message TEXT NOT NULL,
                bot_response TEXT NOT NULL,
                detected_intent TEXT,
                user_type TEXT,
                was_cached BOOLEAN DEFAULT FALSE,
                was_escalated BOOLEAN DEFAULT FALSE,
                response_time_ms INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS escalation_tickets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ticket_id TEXT UNIQUE NOT NULL,
                session_key TEXT NOT NULL,
                user_id INTEGER NOT NULL,
                chat_id INTEGER NOT NULL,
                user_type TEXT,
                issue_category TEXT NOT NULL,
                issue_summary TEXT NOT NULL,
                conversation_transcript TEXT NOT NULL,
                severity TEXT NOT NULL,
                status TEXT DEFAULT 'open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS otp_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                email TEXT NOT NULL,
                telegram_user_id INTEGER NOT NULL DEFAULT 0,
                otp_code TEXT NOT NULL,
                expires_at INTEGER NOT NULL,
                attempts INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS otp_resend_counts (
                email TEXT PRIMARY KEY,
                resend_count INTEGER DEFAULT 0,
                window_start INTEGER NOT NULL
            );

            CREATE TABLE IF NOT EXISTS verified_users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                chat_id INTEGER NOT NULL,
                user_id INTEGER NOT NULL,
                email TEXT NOT NULL,
                verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, email)
            );
        """)
        await conn.commit()

        # Migrations: add columns that may be missing from pre-existing databases
        migrations = [
            "ALTER TABLE sessions ADD COLUMN email TEXT DEFAULT NULL",
            "ALTER TABLE sessions ADD COLUMN frustration_count INTEGER DEFAULT 0",
            "ALTER TABLE sessions ADD COLUMN unrecognized_count INTEGER DEFAULT 0",
            "ALTER TABLE otp_codes ADD COLUMN telegram_user_id INTEGER NOT NULL DEFAULT 0",
        ]
        for migration in migrations:
            try:
                await conn.execute(migration)
                await conn.commit()
            except Exception:
                pass  # Column already exists
    finally:
        await conn.close()
