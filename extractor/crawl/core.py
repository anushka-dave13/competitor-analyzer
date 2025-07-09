# extractor/core.py
import os
import logging
from extractor.crawl.link_discovery import discover_internal_links
from extractor.crawl.multiprocess import extract_texts_from_urls
from extractor.extractors.cookie_handler import handle_cookie_consent
from analyzer.utils.helpers import sanitize_filename, save_text_to_file

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def crawl_website(
    base_url,
    output_dir="output/text",
    max_pages=20,
    max_threads=10,
    max_processes=4,
    respect_robots=False,
    proxy_list=None,
    save_text=True,
    show_progress=False,
    save_screenshot_on_fail=True,         # enable screenshots on fail
    lang="en",                             # enforce English content
    min_content_length=400                # enforce minimum content length
):
    """
    Orchestrates the full crawling process:
    1. Discovers internal links from a base URL.
    2. Extracts rendered + PDF content via Selenium + multiprocessing.
    3. Saves content to disk or returns as a dict.
    """
    logger.info(f"[START] Crawling base URL: {base_url}")
    os.makedirs(output_dir, exist_ok=True)

    # Step 1: Link Discovery
    links, errors = discover_internal_links(
        start_url=base_url,
        max_pages=max_pages,
        max_threads=max_threads,
        respect_robots=respect_robots
    )
    if not links:
        logger.warning(f"[EMPTY] No links discovered from {base_url}")
        return {}

    logger.info(f"[DISCOVERY] {len(links)} links discovered.")

    # Step 2: Text Extraction with Multiprocessing
    url_text_map = extract_texts_from_urls(
        urls=links,
        max_workers=max_processes,
        proxy_list=proxy_list,
        headless=True,
        show_progress=show_progress,
        save_screenshot_on_fail=save_screenshot_on_fail,
        lang=lang,
        min_content_length=min_content_length,
        cookie_handler=handle_cookie_consent  # Pass cookie handler
    )

    logger.info(f"[EXTRACTION] {len(url_text_map)} pages successfully extracted.")

    # Step 3: Save Output
    if save_text:
        for url, content in url_text_map.items():
            try:
                filename = sanitize_filename(url) + ".txt"
                path = os.path.join(output_dir, filename)
                save_text_to_file(content, path)
            except Exception as e:
                logger.warning(f"[SAVE_FAIL] Could not save {url}: {e}")

    return url_text_map
