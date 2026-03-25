import logging
import random
import smtplib
import time
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from config import (
    SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM_EMAIL,
    OTP_EXPIRY_SECONDS, OTP_MAX_ATTEMPTS,
)
from database.db import get_connection

logger = logging.getLogger(__name__)


def generate_otp() -> str:
    """Generate a 6-digit OTP code."""
    return str(random.randint(100000, 999999))


async def store_otp(email: str, otp_code: str) -> None:
    """Store OTP in the database, replacing any existing OTP for this email."""
    conn = await get_connection()
    try:
        # Delete any existing OTP for this email
        await conn.execute("DELETE FROM otp_codes WHERE email = ?", (email,))
        await conn.execute(
            "INSERT INTO otp_codes (email, otp_code, expires_at, attempts) VALUES (?, ?, ?, ?)",
            (email, otp_code, int(time.time()) + OTP_EXPIRY_SECONDS, 0),
        )
        await conn.commit()
    finally:
        await conn.close()


async def verify_otp(email: str, entered_code: str) -> tuple[bool, str]:
    """Verify OTP. Returns (success, message)."""
    conn = await get_connection()
    try:
        cursor = await conn.execute(
            "SELECT otp_code, expires_at, attempts FROM otp_codes WHERE email = ?",
            (email,),
        )
        row = await cursor.fetchone()

        if not row:
            return False, "No OTP found. Please request a new one."

        stored_code = row["otp_code"]
        expires_at = row["expires_at"]
        attempts = row["attempts"]

        if time.time() > expires_at:
            await conn.execute("DELETE FROM otp_codes WHERE email = ?", (email,))
            await conn.commit()
            return False, "OTP has expired. Would you like me to send a new one? Reply 'yes' to resend."

        if attempts >= OTP_MAX_ATTEMPTS:
            await conn.execute("DELETE FROM otp_codes WHERE email = ?", (email,))
            await conn.commit()
            return False, "Too many failed attempts. Please start over by sending your email again."

        if entered_code.strip() != stored_code:
            await conn.execute(
                "UPDATE otp_codes SET attempts = attempts + 1 WHERE email = ?",
                (email,),
            )
            await conn.commit()
            remaining = OTP_MAX_ATTEMPTS - attempts - 1
            return False, f"Invalid OTP. You have {remaining} attempt(s) remaining."

        # Success — delete the OTP
        await conn.execute("DELETE FROM otp_codes WHERE email = ?", (email,))
        await conn.commit()
        return True, "Email verified successfully!"
    finally:
        await conn.close()


async def send_otp_email(email: str, otp_code: str) -> bool:
    """Send OTP to the user's email via SMTP. Returns True on success."""
    if not SMTP_USER or not SMTP_PASSWORD:
        logger.error("SMTP credentials not configured — cannot send OTP email")
        return False

    msg = MIMEMultipart()
    msg["From"] = SMTP_FROM_EMAIL
    msg["To"] = email
    msg["Subject"] = "Endl Support — Your Verification Code"

    body = (
        f"Your verification code is: {otp_code}\n\n"
        f"This code expires in {OTP_EXPIRY_SECONDS // 60} minutes.\n\n"
        "If you did not request this code, please ignore this email."
    )
    msg.attach(MIMEText(body, "plain"))

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
