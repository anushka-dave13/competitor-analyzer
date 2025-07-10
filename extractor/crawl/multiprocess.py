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
        # extract_text_from_url returns (url, text), we want just the text
        _, text = extract_text_from_url(url, **kwargs)
        return url, text
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
    show_progress=True,
    max_workers=None  # Add this parameter
):
    logger.info(f"[MULTIPROCESS_START] Processing {len(urls)} URLs")
    
    if not urls:
        logger.warning("[MULTIPROCESS] No URLs provided")
        return {}
    
    # Prepare arguments for each URL
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
    
    # Use max_workers if provided, otherwise use the minimum of URLs count and CPU count
    if max_workers is None:
        max_workers = min(len(urls), multiprocessing.cpu_count())
    else:
        max_workers = min(max_workers, len(urls), multiprocessing.cpu_count())
    
    logger.info(f"[MULTIPROCESS] Using {max_workers} workers for {len(urls)} URLs")
    
    try:
        # For small number of URLs, process sequentially for better debugging
        if len(urls) <= 2:
            logger.info("[MULTIPROCESS] Processing sequentially for debugging")
            results = []
            for arg in args:
                result = _safe_extract_url(arg)
                results.append(result)
                logger.info(f"[SEQUENTIAL] Processed {result[0]}: {len(result[1])} chars")
            return dict(results)
        
        # Use multiprocessing for larger batches
        with multiprocessing.Pool(processes=max_workers, initializer=init_worker) as pool:
            results = list(tqdm(pool.imap(_safe_extract_url, args), total=len(args), disable=not show_progress))
        
        # Log results
        successful = sum(1 for _, text in results if text.strip())
        failed = len(results) - successful
        logger.info(f"[MULTIPROCESS_COMPLETE] {successful} successful, {failed} failed")
        
        return dict(results)
        
    except Exception as e:
        logger.error(f"[MULTIPROCESS] Unexpected error: {e}")
        traceback.print_exc()
        return {}
