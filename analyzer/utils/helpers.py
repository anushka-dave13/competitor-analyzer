import os
import re
import logging

logger = logging.getLogger(__name__)

def sanitize_filename(url: str, max_length: int = 100) -> str:
    """
    Converts a URL into a filesystem-safe filename.
    """
    filename = url.strip().lower()
    filename = re.sub(r'^https?://', '', filename)           # remove protocol
    filename = re.sub(r'[^a-zA-Z0-9_-]', '_', filename)       # replace non-safe chars
    filename = re.sub(r'_+', '_', filename)                   # collapse underscores
    filename = filename.strip('_')

    return filename[:max_length] or "output"

def save_text_to_file(text: str, filepath: str) -> None:
    """
    Saves text content to a UTF-8 file, creating parent directories if needed.
    """
    try:
        os.makedirs(os.path.dirname(filepath), exist_ok=True)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(text)
        logger.info(f"[SAVED] Text written to {filepath}")
    except Exception as e:
        logger.error(f"[SAVE_FAIL] Could not write to {filepath}: {e}")
