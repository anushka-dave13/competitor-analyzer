# --- extractor/crawl/multiprocess.py ---
import logging
import multiprocessing
import traceback
from tqdm import tqdm
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
        logger.error(f"[WORKER_ERROR] {url}: {e}")
        traceback.print_exc()
        return url, ""

def extract_texts_from_urls(
    urls,
    headless=True,
    proxy=None,
    timeout=20,
    scroll_pause=1.5,
    max_scrolls=15,
    min_content_length=400,
    lang="en",
    save_screenshot_on_fail=False,
    cookie_handler=None,
    show_progress=True
):
    args = [
        (url, {
            "headless": headless,
            "proxy": proxy,
            "timeout": timeout,
            "scroll_pause": scroll_pause,
            "max_scrolls": max_scrolls,
            "min_content_length": min_content_length,
            "lang": lang,
            "save_screenshot_on_fail": save_screenshot_on_fail,
            "cookie_handler": cookie_handler
        }) for url in urls
    ]

    try:
        with multiprocessing.Pool(processes=min(len(urls), multiprocessing.cpu_count()), initializer=init_worker) as pool:
            results = list(tqdm(pool.imap(_safe_extract_url, args), total=len(args), disable=not show_progress))
        return dict(results)
    except Exception as e:
        logger.error(f"[MULTIPROCESS] Unexpected error: {e}")
        traceback.print_exc()
        return {}
