import os
import time
import logging
import traceback
from langdetect import detect
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import undetected_chromedriver as uc
import pdfplumber
import requests
from extractor.extractors.cookie_handler import handle_cookie_consent

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def is_pdf_url(url):
    return url.lower().endswith(".pdf")

def extract_text_from_pdf(url):
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        with open("temp.pdf", "wb") as f:
            f.write(response.content)
        with pdfplumber.open("temp.pdf") as pdf:
            text = "\n".join(page.extract_text() or "" for page in pdf.pages)
        os.remove("temp.pdf")
        return text
    except Exception as e:
        logger.warning(f"[PDF_FAIL] Failed to extract PDF {url}: {e}")
        return ""

def init_driver(headless=True, proxy=None):
    options = uc.ChromeOptions()
    if headless:
        options.add_argument("--headless")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)
    
    if proxy:
        options.add_argument(f'--proxy-server={proxy}')
    
    try:
        driver = uc.Chrome(options=options)
        # Remove webdriver property
        driver.execute_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        return driver
    except Exception as e:
        logger.error(f"[DRIVER_FAIL] Failed to initialize driver: {e}")
        return None

def extract_text_from_url(
    url,
    headless=True,
    proxy=None,
    timeout=20,
    scroll_pause=1.5,
    max_scrolls=15,
    min_content_length=400,
    lang="en",
    save_screenshot_on_fail=False,
    cookie_handler=handle_cookie_consent
):
    logger.info(f"[EXTRACT_START] Processing URL: {url}")
    
    if is_pdf_url(url):
        logger.info(f"[PDF_DETECTED] {url}")
        pdf_text = extract_text_from_pdf(url)
        return url, pdf_text
    
    driver = init_driver(headless=headless, proxy=proxy)
    if not driver:
        logger.error(f"[DRIVER_FAIL] Could not initialize driver for {url}")
        return url, ""
    
    try:
        driver.set_page_load_timeout(timeout)
        logger.info(f"[LOADING] {url}")
        driver.get(url)
        time.sleep(3)  # Give page time to load
        
        # Check if page actually loaded
        current_url = driver.current_url
        if current_url != url:
            logger.warning(f"[REDIRECT] {url} -> {current_url}")
        
        # Handle cookie consent
        if cookie_handler:
            try:
                logger.info(f"[COOKIE] Handling consent for {url}")
                cookie_handler(driver)
            except Exception as e:
                logger.warning(f"[COOKIE_FAIL] {url}: {e}")
        
        # Scroll to load dynamic content
        try:
            body = driver.find_element(By.TAG_NAME, "body")
            logger.info(f"[SCROLL] Scrolling {max_scrolls} times for {url}")
            for i in range(max_scrolls):
                body.send_keys(Keys.END)
                time.sleep(scroll_pause)
        except Exception as e:
            logger.warning(f"[SCROLL_FAIL] {url}: {e}")
        
        # Extract text
        try:
            text = driver.find_element(By.TAG_NAME, "body").text.strip()
            logger.info(f"[TEXT_EXTRACTED] {url}: {len(text)} characters")
        except Exception as e:
            logger.error(f"[TEXT_EXTRACT_FAIL] {url}: {e}")
            text = ""
        
        # Validate text length
        if not text or len(text) < min_content_length:
            error_msg = f"Extracted text too short or empty: {len(text)} characters (min: {min_content_length})"
            logger.warning(f"[SHORT_TEXT] {url}: {error_msg}")
            
            # Try alternative extraction methods
            try:
                # Try getting text from main content areas
                selectors = ['main', 'article', '.content', '#content', '.post', '.entry']
                for selector in selectors:
                    try:
                        element = driver.find_element(By.CSS_SELECTOR, selector)
                        alt_text = element.text.strip()
                        if alt_text and len(alt_text) >= min_content_length:
                            logger.info(f"[ALT_EXTRACT] {url}: Found text using {selector}: {len(alt_text)} chars")
                            text = alt_text
                            break
                    except:
                        continue
            except Exception as e:
                logger.warning(f"[ALT_EXTRACT_FAIL] {url}: {e}")
            
            if not text or len(text) < min_content_length:
                raise ValueError(error_msg)
        
        # Language detection (make it optional)
        if lang and text:
            try:
                detected_lang = detect(text)
                if detected_lang != lang:
                    logger.warning(f"[LANG_MISMATCH] {url}: Expected {lang}, got {detected_lang}")
                    # Don't fail on language mismatch, just warn
                    # raise ValueError(f"Non-target language: {detected_lang}")
            except Exception as e:
                logger.warning(f"[LANG_DETECT_FAIL] {url}: {e}")
        
        logger.info(f"[SUCCESS] {url}: Extracted {len(text)} characters")
        return url, text
        
    except Exception as e:
        error_msg = f"[EXTRACT_FAIL] {url}: {e}"
        logger.error(error_msg)
        
        if save_screenshot_on_fail:
            screenshot_name = f"screenshot_fail_{url.replace('https://','').replace('http://','').replace('/','_')}.png"
            try:
                driver.save_screenshot(screenshot_name)
                logger.warning(f"[SCREENSHOT] Saved: {screenshot_name}")
            except Exception as sse:
                logger.warning(f"[SCREENSHOT_FAIL] Could not save screenshot for {url}: {sse}")
        
        # Print more debug info
        try:
            page_source_len = len(driver.page_source) if driver.page_source else 0
            logger.error(f"[DEBUG] {url}: Page source length: {page_source_len}")
            logger.error(f"[DEBUG] {url}: Current URL: {driver.current_url}")
            logger.error(f"[DEBUG] {url}: Page title: {driver.title}")
        except:
            pass
        
        return url, ""
    finally:
        try:
            driver.quit()
        except:
            pass
