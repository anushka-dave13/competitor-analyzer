# extractor/crawl/text_extractor.py

import os
import time
import uuid
import random
import logging
import tempfile
import requests
from urllib.parse import urlparse

from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import (
    TimeoutException, WebDriverException,
    NoSuchElementException
)
from langdetect import detect, LangDetectException

from analyzer.utils.pdf_utils import extpdf
from extractor.extractors.cookie_handler import handle_cookie_consent
# extractor/crawl/text_extractor.py

import sys
import types

# Patch for Python 3.13: create fake distutils.version.LooseVersion using packaging.version.Version
try:
    import distutils.version
except ModuleNotFoundError:
    from packaging.version import Version
    distutils = types.ModuleType("distutils")
    distutils.version = types.ModuleType("distutils.version")
    distutils.version.LooseVersion = Version
    sys.modules["distutils"] = distutils
    sys.modules["distutils.version"] = distutils.version

# Now safe to import undetected_chromedriver
import undetected_chromedriver as uc


logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Safari/605.1.15",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
]

def get_stealth_driver(headless=True, proxy=None):
    try:
        options = uc.ChromeOptions()
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-gpu")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument(f"--user-agent={random.choice(USER_AGENTS)}")
        if headless:
            try:
                options.add_argument("--headless=new")
            except:
                options.add_argument("--headless")
        if proxy:
            options.add_argument(f"--proxy-server={proxy}")
        return uc.Chrome(options=options)
    except Exception as e:
        logger.error(f"[DRIVER_INIT_FAIL] {e}")
        return None

def is_blocked_or_captcha(driver):
    page_text = driver.page_source.lower()
    return any(k in page_text for k in ['captcha', 'access denied', 'are you human', 'verify you are human'])

def scroll_to_bottom(driver, pause=1.5, max_scrolls=15):
    for _ in range(max_scrolls):
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(pause)

def extract_clean_text(driver):
    soup = BeautifulSoup(driver.page_source, "html.parser")
    for tag in soup(["script", "style", "nav", "footer", "header", "aside", "section"]):
        tag.decompose()
    for popup in soup.select(".modal, .popup, .overlay, #cookie, #consent"):
        popup.decompose()
    return "\n".join(
        t.get_text(strip=True) for t in soup.find_all(["p", "h1", "h2", "h3", "li", "span", "div"])
        if t.get_text(strip=True)
    )

def content_quality_check(text, min_length=400, lang="en"):
    if len(text) < min_length:
        return False, "Too short"
    try:
        if detect(text) != lang:
            return False, "Language mismatch"
    except LangDetectException:
        return False, "Language detection failed"
    return True, "OK"

def extract_text_from_pdf_url(pdf_url):
    try:
        response = requests.get(pdf_url, timeout=10)
        if response.status_code == 200 and 'application/pdf' in response.headers.get("Content-Type", ""):
            tmp_path = os.path.join(tempfile.gettempdir(), f"{uuid.uuid4().hex}.pdf")
            with open(tmp_path, "wb") as f:
                f.write(response.content)
            text = extpdf(tmp_path)
            os.remove(tmp_path)
            return text.strip()
        logger.warning(f"[PDF_FAIL] Invalid PDF: {pdf_url}")
    except Exception as e:
        logger.error(f"[PDF_ERROR] {pdf_url}: {e}")
    return ""

def extract_text_from_url(
    url,
    headless=True,
    proxy=None,
    timeout=20,
    save_screenshot_on_fail=False,
    screenshot_dir="output/screenshots",
    scroll_pause=1.5,
    max_scrolls=15,
    min_content_length=400,
    lang="en"
):
    if url.lower().endswith(".pdf"):
        text = extract_text_from_pdf_url(url)
        quality, reason = content_quality_check(text, min_content_length, lang)
        if not quality:
            logger.warning(f"[PDF_QUALITY] {url}: {reason}")
        return url, text

    driver = get_stealth_driver(headless=headless, proxy=proxy)
    if not driver:
        return url, ""

    try:
        driver.set_page_load_timeout(timeout)
        driver.get(url)
        WebDriverWait(driver, 10).until(EC.presence_of_element_located((By.TAG_NAME, "body")))
        time.sleep(2)
        handle_cookie_consent(driver)
        scroll_to_bottom(driver, pause=scroll_pause, max_scrolls=max_scrolls)

        if is_blocked_or_captcha(driver):
            logger.warning(f"[BLOCKED] CAPTCHA at {url}")
            if save_screenshot_on_fail:
                os.makedirs(screenshot_dir, exist_ok=True)
                driver.save_screenshot(os.path.join(screenshot_dir, f"{urlparse(url).netloc}.png"))
            return url, ""

        text = extract_clean_text(driver)
        quality, reason = content_quality_check(text, min_content_length, lang)
        if not quality:
            logger.warning(f"[QUALITY_FAIL] {url}: {reason}")
        return url, text

    except Exception as e:
        logger.error(f"[EXTRACT_ERROR] {url}: {e}")
        return url, ""
    finally:
        try:
            driver.quit()
        except Exception:
            pass
