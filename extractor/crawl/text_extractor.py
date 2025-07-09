import sys
import types

# --- Python 3.13 patch for distutils ---
try:
    import distutils.version
except ModuleNotFoundError:
    from packaging.version import Version
    distutils = types.ModuleType("distutils")
    distutils.version = types.ModuleType("distutils.version")
    distutils.version.LooseVersion = Version
    sys.modules["distutils"] = distutils
    sys.modules["distutils.version"] = distutils.version

# --- Standard imports ---
import os
import time
import logging
import pdfplumber
from urllib.parse import urlparse
from bs4 import BeautifulSoup
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from langdetect import detect, LangDetectException

# Optional cookie handler if available
try:
    from extractor.extractors.cookie_handler import handle_cookie_consent
except ImportError:
    def handle_cookie_consent(driver):
        pass  # fallback dummy

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def extract_text_from_url(
    url,
    headless=True,
    proxy=None,
    timeout=20,
    scroll_pause=1.5,
    max_scrolls=15,
    min_content_length=400,
    lang="en",
    save_screenshot_on_fail=True,
    cookie_handler=handle_cookie_consent
):
    text = ""

    try:
        options = uc.ChromeOptions()
        if headless:
            options.add_argument("--headless=new")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--window-size=1920,1080")
        if proxy:
            options.add_argument(f"--proxy-server={proxy}")

        driver = uc.Chrome(options=options, use_subprocess=True)
        driver.set_page_load_timeout(timeout)

        driver.get(url)
        time.sleep(2)
        cookie_handler(driver)

        for _ in range(max_scrolls):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(scroll_pause)

        soup = BeautifulSoup(driver.page_source, "html.parser")
        for script in soup(["script", "style", "noscript"]):
            script.decompose()
        text = soup.get_text(separator="\n")
        text = "\n".join(line.strip() for line in text.splitlines() if line.strip())

        try:
            if detect(text) != lang:
                logger.warning(f"[LANG] Skipping non-{lang} page: {url}")
                text = ""
        except LangDetectException:
            logger.warning(f"[LANG] Unable to detect language for: {url}")
            text = ""

        if len(text) < min_content_length:
            logger.warning(f"[SKIP] Content too short from {url}")
            text = ""

    except Exception as e:
        logger.error(f"[ERROR] Failed to extract from {url}: {e}")
        if save_screenshot_on_fail:
            try:
                parsed = urlparse(url)
                domain = parsed.netloc.replace("www.", "").replace(".", "_")
                screenshot_dir = "output/screenshots"
                os.makedirs(screenshot_dir, exist_ok=True)
                screenshot_path = os.path.join(screenshot_dir, f"{domain}.png")
                driver.save_screenshot(screenshot_path)
                logger.info(f"[SCREENSHOT] Saved: {screenshot_path}")
            except Exception as e2:
                logger.warning(f"[SCREENSHOT_FAIL] Could not save screenshot for {url}: {e2}")
    finally:
        try:
            driver.quit()
        except:
            pass

    return url, text.strip()
