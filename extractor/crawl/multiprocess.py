# extractor/crawl/multiprocess.py
import logging
import multiprocessing
from multiprocessing import Pool
from tqdm import tqdm
import traceback

from extractor.crawl.text_extractor import extract_text_from_url

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def init_worker():
    import signal
    signal.signal(signal.SIGINT, signal.SIG_IGN)

def _safe_extract_url(args):
    url, kwargs = args
    try:
        return url, extract_text_from_url(url, **kwargs)
    except Exception as e:
        logger.error(f"[WORKER_ERROR] Failed to extract {url}: {e}")
        traceback.print_exc()
        return url, ""

def extract_texts_from_urls(
    urls,
    headless=True,
    timeout=20,
    scroll_pause=1.5,
    max_scrolls=15,
    min_content_length=400,
    lang="en",
    save_screenshot_on_fail=False,
    cookie_handler=None,
    show_progress=False
):
    logger.info("[MULTIPROCESS] Launching extraction with %d workers", multiprocessing.cpu_count())
    args = [
        (url, {
            "headless": headless,
            "timeout": timeout,
            "scroll_pause": scroll_pause,
            "max_scrolls": max_scrolls,
            "min_content_length": min_content_length,
            "lang": lang,
            "save_screenshot_on_fail": save_screenshot_on_fail,
            "cookie_handler": cookie_handler
        })
        for url in urls
    ]

    try:
        with Pool(processes=min(len(urls), multiprocessing.cpu_count()), initializer=init_worker) as pool:
            results = list(tqdm(pool.imap(_safe_extract_url, args), total=len(args))) if show_progress else pool.map(_safe_extract_url, args)
        return dict(results)
    except Exception as e:
        logger.error(f"[MULTIPROCESS] Unexpected error: {e}")
        traceback.print_exc()
        return {}
