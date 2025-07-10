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
    try:
        links, errors = discover_internal_links(
            start_url=base_url,
            max_pages=max_pages,
            max_threads=max_threads,
            respect_robots=respect_robots
        )
        
        logger.info(f"[DISCOVERY] Links found: {len(links)}")
        logger.info(f"[DISCOVERY] Errors: {len(errors)}")
        
        # Debug: Print first few links
        if links:
            logger.info(f"[DISCOVERY] First few links: {list(links)[:5]}")
        
        if errors:
            logger.warning(f"[DISCOVERY] First few errors: {list(errors)[:3]}")
        
    except Exception as e:
        logger.error(f"[DISCOVERY_ERROR] Failed to discover links: {e}")
        return {}
    
    if not links:
        logger.warning(f"[EMPTY] No links discovered from {base_url}")
        # Try to extract from the base URL directly
        logger.info(f"[FALLBACK] Attempting to extract from base URL directly")
        links = [base_url]
    
    logger.info(f"[DISCOVERY] {len(links)} links to process.")
    
    # Step 2: Text Extraction with Multiprocessing
    # Note: Using the first proxy from proxy_list if available, or None
    proxy = proxy_list[0] if proxy_list and len(proxy_list) > 0 else None
    
    try:
        url_text_map = extract_texts_from_urls(
            urls=links,
            max_workers=max_processes,          # This parameter now exists in multiprocess.py
            proxy=proxy,                        # Fixed: changed from proxy_list to proxy
            headless=True,
            show_progress=show_progress,
            save_screenshot_on_fail=save_screenshot_on_fail,
            lang=lang,
            min_content_length=min_content_length,
            cookie_handler=handle_cookie_consent  # Pass cookie handler
        )
        
        logger.info(f"[EXTRACTION] {len(url_text_map)} pages successfully extracted.")
        
        # Debug: Check what we got
        successful_extractions = {url: text for url, text in url_text_map.items() if text.strip()}
        failed_extractions = {url: text for url, text in url_text_map.items() if not text.strip()}
        
        logger.info(f"[EXTRACTION] Successful: {len(successful_extractions)}")
        logger.info(f"[EXTRACTION] Failed: {len(failed_extractions)}")
        
        if failed_extractions:
            logger.warning(f"[EXTRACTION] Failed URLs: {list(failed_extractions.keys())}")
        
        # If all extractions failed, log more details
        if not successful_extractions:
            logger.error(f"[EXTRACTION] All extractions failed!")
            logger.error(f"[EXTRACTION] Original links: {links}")
            logger.error(f"[EXTRACTION] Results: {url_text_map}")
            
    except Exception as e:
        logger.error(f"[EXTRACTION_ERROR] Failed during text extraction: {e}")
        import traceback
        traceback.print_exc()
        return {}
    
    # Step 3: Save Output
    if save_text and successful_extractions:
        for url, content in successful_extractions.items():
            try:
                filename = sanitize_filename(url) + ".txt"
                path = os.path.join(output_dir, filename)
                save_text_to_file(content, path)
                logger.info(f"[SAVE]
