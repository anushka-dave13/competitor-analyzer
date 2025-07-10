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
        options.headless = True
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    if proxy:
        options.add_argument(f'--proxy-server={proxy}')
    try:
        driver = uc.Chrome(options=options, enable_cdp_events=True)
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
    if is_pdf_url(url):
        return url, extract_text_from_pdf(url)
    
    driver = init_driver(headless=headless, proxy=proxy)
    if not driver:
        return url, ""
    
    try:
        driver.set_page_load_timeout(timeout)
        driver.get(url)
        time.sleep(2)
        
        if cookie_handler:
            try:
                cookie_handler(driver)
            except Exception as e:
                logger.warning(f"[COOKIE_FAIL] {url}: {e}")
        
        body = driver.find_element(By.TAG_NAME, "body")
        for i in range(max_scrolls):  # Fixed: replaced * with i
            body.send_keys(Keys.END)
            time.sleep(scroll_pause)
        
        text = driver.find_element(By.TAG_NAME, "body").text.strip()
        
        if not text or len(text) < min_content_length:
            raise ValueError(f"Extracted text too short or empty: {len(text)} characters")
        
        detected_lang = detect(text)
        if lang and detected_lang != lang:
            raise ValueError(f"Non-target language: {detected_lang}")
        
        return url, text
        
    except Exception as e:
        if save_screenshot_on_fail:
            screenshot_name = f"screenshot_fail_{url.replace('https://','').replace('http://','').replace('/','_')}.png"
            try:
                driver.save_screenshot(screenshot_name)
                logger.warning(f"[SCREENSHOT] Saved: {screenshot_name}")
            except Exception as sse:
                logger.warning(f"[SCREENSHOT_FAIL] Could not save screenshot for {url}: {sse}")
        
        logger.warning(f"[EXTRACT_FAIL] {url}: {e}")
        traceback.print_exc()
        return url, ""
    finally:
        driver.quit()
