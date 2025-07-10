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
    logger.info(f"[CRAWL_START] Base URL: {base_url}")
    logger.info(f"[CRAWL_CONFIG] max_pages={max_pages}, max_processes={max_processes}, min_content_length={min_content_length}")
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Step 1: Link Discovery
    try:
        logger.info(f"[LINK_DISCOVERY] Starting link discovery for {base_url}")
        links, errors = discover_internal_links(
            start_url=base_url,
            max_pages=max_pages,
            max_threads=max_threads,
            respect_robots=respect_robots
        )
        
        logger.info(f"[LINK_DISCOVERY] Found {len(links)} links, {len(errors)} errors")
        
        # Debug: Print first few links
        if links:
            logger.info(f"[LINK_DISCOVERY] Sample links: {links[:3]}")
        
        if errors:
            logger.warning(f"[LINK_DISCOVERY] Sample errors: {errors[:3]}")
        
    except Exception as e:
        logger.error(f"[LINK_DISCOVERY_ERROR] Failed to discover links: {e}")
        import traceback
        traceback.print_exc()
        return {}
    
    # If no links found, try base URL directly
    if not links:
        logger.warning(f"[LINK_DISCOVERY] No links found, trying base URL directly")
        links = [base_url]
    
    logger.info(f"[EXTRACTION_START] Processing {len(links)} URLs")
    
    # Step 2: Text Extraction
    proxy = proxy_list[0] if proxy_list and len(proxy_list) > 0 else None
    if proxy:
        logger.info(f"[EXTRACTION] Using proxy: {proxy}")
    
    try:
        url_text_map = extract_texts_from_urls(
            urls=links,
            max_workers=max_processes,
            proxy=proxy,
            headless=True,
            show_progress=show_progress,
            save_screenshot_on_fail=save_screenshot_on_fail,
            lang=lang,
            min_content_length=min_content_length,
            cookie_handler=handle_cookie_consent
        )
        
        # Analyze results
        successful_extractions = {url: text for url, text in url_text_map.items() if text.strip()}
        failed_extractions = {url: text for url, text in url_text_map.items() if not text.strip()}
        
        logger.info(f"[EXTRACTION_COMPLETE] {len(successful_extractions)} successful, {len(failed_extractions)} failed")
        
        if failed_extractions:
            logger.warning(f"[EXTRACTION_FAILED] Failed URLs: {list(failed_extractions.keys())}")
        
        # Debug successful extractions
        if successful_extractions:
            for url, text in successful_extractions.items():
                logger.info(f"[EXTRACTION_SUCCESS] {url}: {len(text)} characters")
        
        # If all extractions failed, provide detailed error info
        if not successful_extractions:
            logger.error(f"[EXTRACTION_TOTAL_FAIL] All extractions failed!")
            logger.error(f"[EXTRACTION_TOTAL_FAIL] URLs attempted: {links}")
            
            # Try a single URL with detailed debugging
            if links:
                test_url = links[0]
                logger.info(f"[DEBUG_EXTRACTION] Testing single URL: {test_url}")
                
                # Import directly for debugging
                from extractor.crawl.text_extractor import extract_text_from_url
                try:
                    debug_url, debug_text = extract_text_from_url(
                        test_url,
                        headless=False,  # Use non-headless for debugging
                        save_screenshot_on_fail=True,
                        min_content_length=min_content_length,
                        lang=lang
                    )
                    logger.info(f"[DEBUG_EXTRACTION] Result: {len(debug_text)} characters")
                    if debug_text:
                        successful_extractions[debug_url] = debug_text
                except Exception as e:
                    logger.error(f"[DEBUG_EXTRACTION] Failed: {e}")
                    import traceback
                    traceback.print_exc()
        
        # Use successful extractions for further processing
        url_text_map = successful_extractions
        
    except Exception as e:
        logger.error(f"[EXTRACTION_ERROR] Failed during text extraction: {e}")
        import traceback
        traceback.print_exc()
        return {}
    
    # Step 3: Save Output
    if save_text and url_text_map:
        logger.info(f"[SAVE_START] Saving {len(url_text_map)} files")
        for url, content in url_text_map.items():
            try:
                filename = sanitize_filename(url) + ".txt"
                path = os.path.join(output_dir, filename)
                save_text_to_file(content, path)
                logger.info(f"[SAVE_SUCCESS] {filename}: {len(content)} characters")
            except Exception as e:
                logger.warning(f"[SAVE_FAIL] Could not save {url}: {e}")
    
    logger.info(f"[CRAWL_COMPLETE] Returned {len(url_text_map)} extracted texts")
    return url_text_map
