"""
OCR service — Tesseract-based text extraction from images and PDFs.
All blocking Tesseract calls are wrapped in asyncio.to_thread().
Falls back gracefully when Tesseract is not installed.
"""
import asyncio
import logging
import os
import tempfile

logger = logging.getLogger(__name__)

# Configure Tesseract path from config before importing pytesseract
try:
    import pytesseract
    from config import TESSERACT_PATH
    pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH
    _TESSERACT_AVAILABLE = True
except ImportError:
    _TESSERACT_AVAILABLE = False
    logger.warning("pytesseract not installed — OCR disabled, will rely on Vision only")

try:
    from PIL import Image, ImageEnhance, ImageFilter
    _PILLOW_AVAILABLE = True
except ImportError:
    _PILLOW_AVAILABLE = False
    logger.warning("Pillow not installed — image preprocessing disabled")


async def preprocess_image(image_path: str) -> str:
    """
    Enhance image for better OCR: grayscale, contrast boost, sharpen.
    Returns path to preprocessed temp image (caller must clean up).
    Falls back to original path if Pillow unavailable.
    """
    if not _PILLOW_AVAILABLE:
        return image_path

    def _process() -> str:
        img = Image.open(image_path).convert("L")          # grayscale
        img = ImageEnhance.Contrast(img).enhance(2.0)       # boost contrast
        img = img.filter(ImageFilter.SHARPEN)               # sharpen edges
        fd, out_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        img.save(out_path, "PNG")
        return out_path

    try:
        return await asyncio.to_thread(_process)
    except Exception as e:
        logger.warning("Image preprocessing failed: %s", e)
        return image_path


async def extract_text_from_image(image_path: str) -> dict:
    """
    Run Tesseract OCR on an image file.
    Returns:
        text: str           — extracted text
        confidence: float   — average OCR confidence 0–100
        language: str       — detected language hint
        success: bool
    """
    if not _TESSERACT_AVAILABLE:
        return {"text": "", "confidence": 0.0, "language": "unknown", "success": False}

    preprocessed_path = await preprocess_image(image_path)
    cleanup_preprocessed = preprocessed_path != image_path

    def _run_ocr() -> dict:
        try:
            data = pytesseract.image_to_data(
                preprocessed_path,
                output_type=pytesseract.Output.DICT,
                config="--psm 6",
            )
            words = [w for w in data["text"] if w.strip()]
            confs = [
                int(c) for c, w in zip(data["conf"], data["text"])
                if w.strip() and str(c).lstrip("-").isdigit()
            ]
            text = pytesseract.image_to_string(preprocessed_path, config="--psm 6").strip()
            avg_conf = sum(confs) / len(confs) if confs else 0.0
            logger.info(
                "OCR complete: %d words, avg_confidence=%.1f",
                len(words), avg_conf,
            )
            return {
                "text": text,
                "confidence": round(avg_conf, 1),
                "language": "auto",
                "success": bool(text),
            }
        except pytesseract.TesseractNotFoundError:
            logger.error(
                "Tesseract binary not found at '%s' — set TESSERACT_PATH in .env",
                TESSERACT_PATH,
            )
            return {"text": "", "confidence": 0.0, "language": "unknown", "success": False}
        except Exception as e:
            logger.error("OCR extraction error: %s", e)
            return {"text": "", "confidence": 0.0, "language": "unknown", "success": False}

    try:
        return await asyncio.to_thread(_run_ocr)
    finally:
        if cleanup_preprocessed and os.path.exists(preprocessed_path):
            try:
                os.unlink(preprocessed_path)
            except OSError:
                pass


async def extract_text_from_pdf(pdf_path: str, max_pages: int = 5) -> dict:
    """
    Convert PDF pages to images, then OCR each page.
    Returns:
        pages: list[dict]   — per-page OCR results
        full_text: str      — concatenated text from all pages
        page_count: int
        success: bool
    """
    try:
        from pdf2image import convert_from_path
    except ImportError:
        logger.warning("pdf2image not installed — PDF OCR disabled")
        return {"pages": [], "full_text": "", "page_count": 0, "success": False}

    def _convert_pdf() -> list:
        return convert_from_path(pdf_path, dpi=200, first_page=1, last_page=max_pages)

    try:
        images = await asyncio.to_thread(_convert_pdf)
    except Exception as e:
        logger.error("PDF conversion error: %s", e)
        return {"pages": [], "full_text": "", "page_count": 0, "success": False}

    pages_result = []
    all_text_parts = []

    for i, pil_img in enumerate(images, start=1):
        fd, tmp_path = tempfile.mkstemp(suffix=".png")
        os.close(fd)
        try:
            pil_img.save(tmp_path, "PNG")
            page_ocr = await extract_text_from_image(tmp_path)
            pages_result.append({
                "page": i,
                "text": page_ocr["text"],
                "confidence": page_ocr["confidence"],
            })
            if page_ocr["text"]:
                all_text_parts.append(f"--- Page {i} ---\n{page_ocr['text']}")
        finally:
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    full_text = "\n\n".join(all_text_parts)
    return {
        "pages": pages_result,
        "full_text": full_text,
        "page_count": len(images),
        "success": bool(full_text),
    }
