import logging
import random
import smtplib
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import (
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM_EMAIL,
    OTP_EXPIRY_SECONDS, OTP_MAX_ATTEMPTS,
)
from database.db import get_connection

logger = logging.getLogger(__name__)

_RESEND_MAX = 3
_RESEND_WINDOW = 900  # 15 minutes


def generate_otp() -> str:
    """Generate a 6-digit OTP code."""
    return str(random.randint(100000, 999999))


async def store_otp(email: str, telegram_user_id: int, otp_code: str) -> bool:
    """
    Store OTP bound to (email, telegram_user_id), enforcing the resend rate limit.
    Returns True on success, False if the resend limit has been exceeded.
    """
    conn = await get_connection()
    try:
        now = int(time.time())

        # Check / update resend count within the 15-min window
        cursor = await conn.execute(
            "SELECT resend_count, window_start FROM otp_resend_counts WHERE email = ?",
            (email,),
        )
        row = await cursor.fetchone()

        if row:
            resend_count = row["resend_count"]
            window_start = row["window_start"]
            if now - window_start < _RESEND_WINDOW:
                if resend_count >= _RESEND_MAX:
                    return False  # Rate limited
                new_count = resend_count + 1
                await conn.execute(
                    "UPDATE otp_resend_counts SET resend_count = ? WHERE email = ?",
                    (new_count, email),
                )
            else:
                # Window expired — reset
                await conn.execute(
                    "UPDATE otp_resend_counts SET resend_count = 1, window_start = ? WHERE email = ?",
                    (now, email),
                )
        else:
            await conn.execute(
                "INSERT INTO otp_resend_counts (email, resend_count, window_start) VALUES (?, 1, ?)",
                (email, now),
            )

        # Delete any existing OTP for this (email, user) pair and insert new one
        await conn.execute(
            "DELETE FROM otp_codes WHERE email = ? AND telegram_user_id = ?",
            (email, telegram_user_id),
        )
        await conn.execute(
            "INSERT INTO otp_codes (email, telegram_user_id, otp_code, expires_at, attempts) "
            "VALUES (?, ?, ?, ?, 0)",
            (email, telegram_user_id, otp_code, now + OTP_EXPIRY_SECONDS),
        )
        await conn.commit()
        return True
    finally:
        await conn.close()


async def verify_otp(
    email: str, telegram_user_id: int, entered_code: str
) -> tuple[bool, str, str | None]:
    """
    Verify OTP for (email, telegram_user_id).
    Returns (success, message, reason) where reason is one of:
      None (success), "expired", "invalid", "locked", "not_found"
    """
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT otp_code, expires_at, attempts FROM otp_codes "
            "WHERE email = ? AND telegram_user_id = ?",
            (email, telegram_user_id),
        )
        row = await cursor.fetchone()

        if not row:
            return False, "No OTP found for this session. Please request a new one.", "not_found"

        stored_code = row["otp_code"]
        expires_at = row["expires_at"]
        attempts = row["attempts"]

        if time.time() > expires_at:
            await conn.execute(
                "DELETE FROM otp_codes WHERE email = ? AND telegram_user_id = ?",
                (email, telegram_user_id),
            )
            await conn.commit()
            return False, "OTP has expired (codes are valid for 10 minutes).", "expired"

        if attempts >= OTP_MAX_ATTEMPTS:
            await conn.execute(
                "DELETE FROM otp_codes WHERE email = ? AND telegram_user_id = ?",
                (email, telegram_user_id),
            )
            await conn.commit()
            return False, "Too many incorrect attempts. Session locked.", "locked"

        if entered_code.strip() != stored_code:
            new_attempts = attempts + 1
            ttl_remaining = int(expires_at - time.time())
            await conn.execute(
                "UPDATE otp_codes SET attempts = ? WHERE email = ? AND telegram_user_id = ?",
                (new_attempts, email, telegram_user_id),
            )
            await conn.commit()
            remaining = OTP_MAX_ATTEMPTS - new_attempts
            if remaining <= 0:
                await conn.execute(
                    "DELETE FROM otp_codes WHERE email = ? AND telegram_user_id = ?",
                    (email, telegram_user_id),
                )
                await conn.commit()
                return False, "Too many incorrect attempts. Session locked.", "locked"
            return (
                False,
                f"That code doesn't seem to match. Could you double-check it and try again? "
                f"You have {remaining} attempt(s) remaining.",
                "invalid",
            )

        # Success — delete the OTP and reset resend counter
        await conn.execute(
            "DELETE FROM otp_codes WHERE email = ? AND telegram_user_id = ?",
            (email, telegram_user_id),
        )
        await conn.execute(
            "DELETE FROM otp_resend_counts WHERE email = ?", (email,)
        )
        await conn.commit()
        return True, "Email verified successfully.", None
    finally:
        await conn.close()


async def cancel_otp(email: str, telegram_user_id: int) -> None:
    """Invalidate an in-progress OTP session for (email, telegram_user_id)."""
    conn = await get_connection()
    try:
        await conn.execute(
            "DELETE FROM otp_codes WHERE email = ? AND telegram_user_id = ?",
            (email, telegram_user_id),
        )
        await conn.commit()
    finally:
        await conn.close()


async def send_otp_email(email: str, otp_code: str) -> bool:
    """Send OTP to the user's email via SMTP. Returns True on success."""
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.error("SMTP credentials not configured — cannot send OTP email")
        return False

    msg = MIMEMultipart("alternative")
    msg["From"] = SMTP_FROM_EMAIL
    msg["To"] = email
    msg["Subject"] = "Endl Support — Your Verification Code"

    plain = (
        f"Your verification code is: {otp_code}\n\n"
        f"This code expires in {OTP_EXPIRY_SECONDS // 60} minutes.\n\n"
        "If you did not request this code, please ignore this email."
    )
    html = f"""
    <div style="font-family: Arial, sans-serif; max-width: 420px; margin: auto;">
      <h2 style="color: #1a1a2e;">Verification Code</h2>
      <p>Use the code below to verify your identity:</p>
      <div style="font-size: 32px; font-weight: bold; letter-spacing: 8px;
                  padding: 16px; background: #f4f4f4; text-align: center;
                  border-radius: 8px; color: #1a1a2e;">
        {otp_code}
      </div>
      <p style="color: #888; font-size: 13px; margin-top: 16px;">
        This code expires in <strong>{OTP_EXPIRY_SECONDS // 60} minutes</strong>.
        Do not share it with anyone.
      </p>
    </div>
    """
    msg.attach(MIMEText(plain, "plain"))
    msg.attach(MIMEText(html, "html"))

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=15) as server:
            server.starttls()
            server.login(SMTP_USER, SMTP_PASSWORD)
            server.sendmail(SMTP_FROM_EMAIL, email, msg.as_string())
        logger.info("OTP email sent to %s", email)
        return True
    except Exception as e:
        logger.error("Failed to send OTP email to %s: %s", email, e)
        return False
