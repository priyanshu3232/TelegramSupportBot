import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.getenv("CLAUDE_MODEL", "claude-sonnet-4-6-20260401")
CLAUDE_MAX_TOKENS = int(os.getenv("CLAUDE_MAX_TOKENS", "1024"))
CLAUDE_TEMPERATURE = float(os.getenv("CLAUDE_TEMPERATURE", "0.2"))
SUPPORT_LINK = os.getenv("SUPPORT_LINK", "https://t.me/endl_support")
SUPPORT_GROUP_ID = os.getenv("SUPPORT_GROUP_ID", "@Endl_support")
DB_PATH = os.getenv("DB_PATH", "data/endl_bot.db")
RATE_LIMIT_MESSAGES = int(os.getenv("RATE_LIMIT_MESSAGES", "10"))
RATE_LIMIT_WINDOW_SECONDS = int(os.getenv("RATE_LIMIT_WINDOW_SECONDS", "60"))

# SMTP email settings
SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USER = os.getenv("SMTP_USER", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM_EMAIL = os.getenv("SMTP_FROM_EMAIL", "") or SMTP_USER

# OTP settings
OTP_EXPIRY_SECONDS = int(os.getenv("OTP_EXPIRY_SECONDS", "600"))
OTP_MAX_ATTEMPTS = int(os.getenv("OTP_MAX_ATTEMPTS", "3"))

# SumSub API settings
SUMSUB_APP_TOKEN = os.getenv("SUMSUB_APP_TOKEN", "")
SUMSUB_SECRET_KEY = os.getenv("SUMSUB_SECRET_KEY", "")
SUMSUB_BASE_URL = os.getenv("SUMSUB_BASE_URL", "https://api.sumsub.com")

# OCR / Vision settings
_default_tesseract = (
    r"C:/Program Files/Tesseract-OCR/tesseract.exe"
    if os.name == "nt" else "tesseract"
)
TESSERACT_PATH = os.getenv("TESSERACT_PATH", _default_tesseract)
OCR_ENABLED = os.getenv("OCR_ENABLED", "true").lower() == "true"
VISION_ENABLED = os.getenv("VISION_ENABLED", "true").lower() == "true"
MAX_FILE_SIZE_MB = int(os.getenv("MAX_FILE_SIZE_MB", "10"))
SUPPORTED_IMAGE_TYPES = ["image/jpeg", "image/png", "image/webp", "image/bmp", "image/gif"]
SUPPORTED_DOC_TYPES = ["application/pdf"]
TEMP_DIR = os.getenv("TEMP_DIR", "data/temp")
