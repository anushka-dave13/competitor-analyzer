# extractor/crawl/text_extractor.py

import os
import logging
import traceback
from urllib.parse import urlparse
import time

import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.common.exceptions import TimeoutException, WebDriverException
from langdetect import detect

import pdfplumber
import requests
from extractor.extractors.cookie_handler import handle_cookie_consent

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def is_pdf_url(url):
    return url.lower().endswith(".pdf")

def extract_text_from_pdf_url(url):
    try:
        response = requests.get(url, timeout=15)
        if response.ok:
            with open("temp_download.pdf", "wb") as f:
                f.write(response.content)
            with pdfplumber.open("temp_download.pdf") as pdf:
                text = "\n".join(page.extract_text() or "" for page in pdf.pages)
            os.remove("temp_download.pdf")
            return url, text
        else:
            raise Exception(f"Failed to download PDF: {response.status_code}")
    except Exception as e:
        logger.warning(f"[PDF_FAIL] {url}: {e}")
        return url, ""

def create_driver(headless=True, proxy=None):
    options = uc.ChromeOptions()
    if headless:
        options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1920,1080")
    if proxy:
        options.add_argument(f'--proxy-server={proxy}')
    return uc.Chrome(options=options)

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
        return extract_text_from_pdf_url(url)

    try:
        driver = create_driver(headless=headless, proxy=proxy)
    except WebDriverException as e:
        logger.error(f"[DRIVER_FAIL] Could not create browser instance: {e}")
        return url, ""

    try:
        driver.set_page_load_timeout(timeout)
        driver.get(url)
        time.sleep(2)

        if cookie_handler:
            cookie_handler(driver)

        scroll_count = 0
        last_height = driver.execute_script("return document.body.scrollHeight")
        while scroll_count < max_scrolls:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_pause)
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
            scroll_count += 1

        body = driver.find_element(By.TAG_NAME, "body")
        text = body.text.strip()

        if len(text) < min_content_length:
            logger.warning(f"[SKIP] {url} - Too short ({len(text)} chars)")
            return url, ""

        try:
            detected_lang = detect(text)
            if detected_lang != lang:
                logger.warning(f"[LANG_SKIP] {url} - Detected: {detected_lang}")
                return url, ""
        except Exception:
            logger.warning(f"[LANG_FAIL] Could not detect language for {url}")

        return url, text

    except Exception as e:
        logger.error(f"[SCRAPE_FAIL] {url}: {e}")
        if save_screenshot_on_fail:
            domain = urlparse(url).netloc
            fname = f"screenshot_{domain.replace('.', '_')}.png"
            driver.save_screenshot(fname)
            logger.info(f"[SCREENSHOT] Saved on failure: {fname}")
        traceback.print_exc()
        return url, ""
    finally:
        try:
            driver.quit()
        except Exception:
            pass
