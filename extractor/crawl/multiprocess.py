# extractor/crawl/multiprocess.py

import logging
import multiprocessing
from multiprocessing import Pool
from tqdm import tqdm
import traceback
import random

from extractor.crawl.text_extractor import extract_text_from_url

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)


def init_worker():
    """Ignore keyboard interrupts in worker processes to avoid hanging."""
    import signal
    signal.signal(signal.SIGINT, signal.SIG_IGN)


def _safe_extract_url(args):
    """Helper to safely extract text and log exceptions in workers."""
    url, kwargs = args
    try:
        return extract_text_from_url(url, **kwargs)
    except Exception as e:
        logger.error(f"[WORKER_ERROR] Failed to extract {url}: {e}")
        traceback.print_exc()
        return url, ""


def extract_texts_from_urls(
    urls,
    headless=True,
    proxy_list=None,
    timeout=20,
    scroll_pause=1.5,
    max_scrolls=15,
    min_content_length=400,
    lang="en",
    show_progress=False,
    max_workers=None,
    save_screenshot_on_fail=False,
    cookie_handler=None
):
    logger.info("[MULTIPROCESS] Starting with up to %d workers", multiprocessing.cpu_count())
    workers = max_workers or min(len(urls), multiprocessing.cpu_count())

    args = []
    for url in urls:
        proxy = random.choice(proxy_list) if proxy_list else None
        args.append((url, {
            "headless": headless,
            "proxy": proxy,
            "timeout": timeout,
            "scroll_pause": scroll_pause,
            "max_scrolls": max_scrolls,
            "min_content_length": min_content_length,
            "lang": lang,
            "save_screenshot_on_fail": save_screenshot_on_fail,
            "cookie_handler": cookie_handler,
        }))

    try:
        with Pool(processes=workers, initializer=init_worker) as pool:
            results = pool.imap(_safe_extract_url, args)
            if show_progress:
                results = tqdm(results, total=len(args))
            return dict(results)
    except Exception as e:
        logger.error(f"[MULTIPROCESS] Fatal multiprocessing error: {e}")
        traceback.print_exc()
        return {}
