"""
File download and processing pipeline for the Endl Support Bot.
Handles: download from Telegram → OCR → Vision → combined response.
All temp files are cleaned up in finally blocks.
"""
import logging
import os
import uuid

from config import (
    MAX_FILE_SIZE_MB,
    OCR_ENABLED,
    VISION_ENABLED,
    SUPPORTED_IMAGE_TYPES,
    SUPPORTED_DOC_TYPES,
    TEMP_DIR,
)
from services.ocr_service import extract_text_from_image, extract_text_from_pdf
from services.vision_service import analyze_image_with_vision

logger = logging.getLogger(__name__)

_MAX_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024


def _ensure_temp_dir() -> None:
    os.makedirs(TEMP_DIR, exist_ok=True)


async def download_telegram_file(
    bot,
    file_id: str,
    file_name: str | None,
    mime_type: str | None,
) -> dict:
    """
    Download a file from Telegram servers into TEMP_DIR.
    Returns download result dict.
    """
    _ensure_temp_dir()

    ext = ""
    if file_name and "." in file_name:
        ext = "." + file_name.rsplit(".", 1)[-1].lower()
    elif mime_type:
        _mime_ext = {
            "image/jpeg": ".jpg",
            "image/png": ".png",
            "image/webp": ".webp",
            "image/bmp": ".bmp",
            "image/gif": ".gif",
            "application/pdf": ".pdf",
        }
        ext = _mime_ext.get(mime_type, "")

    unique_name = f"{uuid.uuid4().hex}{ext}"
    local_path = os.path.join(TEMP_DIR, unique_name)

    try:
        tg_file = await bot.get_file(file_id)

        # Size check before downloading
        file_size = getattr(tg_file, "file_size", None)
        if file_size and file_size > _MAX_BYTES:
            size_mb = file_size / (1024 * 1024)
            return {
                "local_path": None,
                "file_name": file_name or unique_name,
                "mime_type": mime_type,
                "file_size": file_size,
                "success": False,
                "error": f"file_too_large:{size_mb:.1f}MB",
            }

        await tg_file.download_to_drive(local_path)
        actual_size = os.path.getsize(local_path)
        logger.info(
            "Downloaded file: %s (%d bytes, mime=%s)", local_path, actual_size, mime_type
        )
        return {
            "local_path": local_path,
            "file_name": file_name or unique_name,
            "mime_type": mime_type or "application/octet-stream",
            "file_size": actual_size,
            "success": True,
            "error": None,
        }
    except Exception as e:
        logger.error("File download error: %s", e)
        return {
            "local_path": None,
            "file_name": file_name or unique_name,
            "mime_type": mime_type,
            "file_size": 0,
            "success": False,
            "error": str(e),
        }


async def cleanup_temp_files(file_paths: list[str]) -> None:
    """Remove temporary files; ignore errors silently."""
    for path in file_paths:
        if path and os.path.exists(path):
            try:
                os.unlink(path)
                logger.debug("Cleaned up temp file: %s", path)
            except OSError as e:
                logger.debug("Could not remove temp file %s: %s", path, e)


def _build_combined_response(
    vision: dict | None,
    ocr_text: str | None,
    mime_type: str,
    account_type: str,
) -> tuple[str, str]:
    """
    Merge Vision analysis + OCR text into a single user-facing message.
    Returns (response_text, buttons_name).
    """
    is_pdf = mime_type == "application/pdf"

    if vision and vision.get("confidence", 0) >= 0.4:
        analysis = vision.get("analysis", "")
        action = vision.get("suggested_action", "")
        buttons = vision.get("buttons", "support")

        parts = []
        if analysis:
            parts.append(analysis)
        if action and action.lower() not in analysis.lower():
            parts.append(f"Next step: {action}")

        response = " ".join(parts).strip()

        # Append low-OCR-confidence note
        if ocr_text and len(ocr_text.strip()) < 20:
            response += "\n\nThe text in the image was a bit hard to read — if my analysis missed something, please describe it in text."

        return response or _fallback_message(is_pdf), buttons

    # Vision not available or low confidence — use OCR text directly
    if ocr_text and len(ocr_text.strip()) > 20:
        if is_pdf:
            return (
                f"I extracted the following text from your PDF:\n\n{ocr_text[:600]}\n\n"
                "Is there a specific part you need help with?",
                "support",
            )
        return (
            "I can see text in your image. Based on what I can read, could you confirm "
            "what you need help with? Here's what I extracted:\n\n"
            f"{ocr_text[:400]}",
            "support",
        )

    return _fallback_message(is_pdf), "support"


def _fallback_message(is_pdf: bool) -> str:
    if is_pdf:
        return (
            "I received your PDF but had difficulty extracting its content. "
            "Could you describe what's in the document, or what you need help with?"
        )
    return (
        "I received your image but had difficulty analysing it. "
        "Could you describe what you're seeing in text? I'll do my best to help."
    )


async def process_uploaded_file(
    bot,
    file_id: str,
    file_name: str | None,
    mime_type: str | None,
    user_context: str,
    account_type: str,
    conversation_history: list[dict],
) -> dict:
    """
    Full pipeline: download → OCR + Vision (parallel) → combined response.
    Returns processing result dict.
    """
    temp_files: list[str] = []

    try:
        # Step 1 — Download
        dl = await download_telegram_file(bot, file_id, file_name, mime_type)

        if not dl["success"]:
            error = dl.get("error", "")
            if error.startswith("file_too_large"):
                size_info = error.split(":")[1] if ":" in error else ""
                return {
                    "response_text": (
                        f"That file is too large ({size_info}) — the maximum I can process is "
                        f"{MAX_FILE_SIZE_MB}MB. "
                        "Try cropping or compressing the image, then send it again."
                    ),
                    "intent": "file_too_large",
                    "ocr_text": None,
                    "vision_analysis": None,
                    "buttons": "support",
                    "success": False,
                }
            return {
                "response_text": (
                    "I had trouble downloading that file. "
                    "Please try again, or describe your issue in text."
                ),
                "intent": "download_error",
                "ocr_text": None,
                "vision_analysis": None,
                "buttons": "support",
                "success": False,
            }

        local_path = dl["local_path"]
        resolved_mime = dl["mime_type"]
        temp_files.append(local_path)

        ocr_result: dict | None = None
        vision_result: dict | None = None

        # Step 2 — Process based on type
        is_pdf = resolved_mime == "application/pdf"
        is_image = resolved_mime in SUPPORTED_IMAGE_TYPES

        if is_pdf:
            if OCR_ENABLED:
                ocr_result = await extract_text_from_pdf(local_path)
            ocr_text = ocr_result["full_text"] if ocr_result and ocr_result.get("success") else None

        elif is_image:
            if OCR_ENABLED:
                ocr_result = await extract_text_from_image(local_path)
                ocr_text = ocr_result["text"] if ocr_result and ocr_result["success"] else None
            else:
                ocr_text = None

            if VISION_ENABLED:
                vision_result = await analyze_image_with_vision(
                    image_path=local_path,
                    mime_type=resolved_mime,
                    user_context=user_context,
                    account_type=account_type,
                    conversation_history=conversation_history,
                    ocr_text=ocr_text,
                )

        else:
            ocr_text = None

        # Step 3 — Build response
        if not OCR_ENABLED and not VISION_ENABLED:
            return {
                "response_text": (
                    "I received your file, but image analysis is currently disabled. "
                    "Please describe what you're seeing in text and I'll help you from there."
                ),
                "intent": "analysis_disabled",
                "ocr_text": None,
                "vision_analysis": None,
                "buttons": "support",
                "success": True,
            }

        # Get OCR text for non-image paths
        if is_pdf:
            ocr_text = ocr_result["full_text"] if ocr_result and ocr_result.get("success") else None

        response_text, buttons = _build_combined_response(
            vision=vision_result,
            ocr_text=ocr_text,
            mime_type=resolved_mime,
            account_type=account_type,
        )

        intent = "unclear"
        if vision_result:
            intent = vision_result.get("intent", "unclear")
        elif ocr_text:
            intent = "ocr_only"

        return {
            "response_text": response_text,
            "intent": intent,
            "ocr_text": ocr_text,
            "vision_analysis": vision_result,
            "buttons": buttons,
            "success": True,
        }

    except Exception as e:
        logger.error("file_processor error: %s", e, exc_info=True)
        return {
            "response_text": (
                "Something went wrong while processing your file. "
                "Please try again or describe your issue in text."
            ),
            "intent": "processing_error",
            "ocr_text": None,
            "vision_analysis": None,
            "buttons": "support",
            "success": False,
        }
    finally:
        await cleanup_temp_files(temp_files)
