import io
import logging

logger = logging.getLogger(__name__)

MAX_CHARS = 12000  # cap CV text passed to the LLM


def extract_text_from_pdf(data: bytes) -> str | None:
    """
    Best-effort PDF text extraction. Returns the extracted text, or None if the
    PDF can't be read (spec §3.2: extraction failure must never block matching).
    """
    try:
        from pypdf import PdfReader
    except ImportError:
        logger.warning("pypdf not installed; skipping CV text extraction")
        return None

    try:
        reader = PdfReader(io.BytesIO(data))
        parts = []
        for page in reader.pages:
            parts.append(page.extract_text() or "")
        text = "\n".join(parts).strip()
        return text[:MAX_CHARS] if text else None
    except Exception as e:
        logger.warning(f"CV text extraction failed: {e}")
        return None
