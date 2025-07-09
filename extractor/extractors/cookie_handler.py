import logging
import time
from selenium.webdriver.common.by import By
from selenium.common.exceptions import (
    NoSuchElementException,
    ElementClickInterceptedException,
    ElementNotInteractableException,
    StaleElementReferenceException,
    WebDriverException,
    TimeoutException,
)
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

logger = logging.getLogger(__name__)

# Patterns for consent buttons (expand as needed)
CONSENT_PATTERNS = [
    {"by": By.ID, "value": "accept"},
    {"by": By.ID, "value": "cookie-accept"},
    {"by": By.ID, "value": "onetrust-accept-btn-handler"},
    {"by": By.CLASS_NAME, "value": "accept-cookies"},
    {"by": By.CLASS_NAME, "value": "cookie-consent-accept"},
    {"by": By.XPATH, "value": "//*[contains(text(),'Accept')]"},
    {"by": By.XPATH, "value": "//*[contains(text(),'I agree')]"},
    {"by": By.XPATH, "value": "//*[contains(text(),'Allow all')]"},
    {"by": By.XPATH, "value": "//*[contains(text(),'Got it')]"},
    # Add more patterns and languages as needed
]

def switch_to_iframe_if_present(driver):
    """Switch to the first iframe if a consent banner is inside it."""
    try:
        iframes = driver.find_elements(By.TAG_NAME, "iframe")
        for iframe in iframes:
            try:
                driver.switch_to.frame(iframe)
                # Try to find a consent button in this iframe
                for pattern in CONSENT_PATTERNS:
                    if driver.find_elements(pattern["by"], pattern["value"]):
                        return True
                driver.switch_to.default_content()
            except Exception:
                driver.switch_to.default_content()
                continue
    except Exception as e:
        logger.debug(f"[COOKIE][IFRAME] Error switching to iframe: {e}")
    return False

def handle_cookie_consent(driver, timeout=7, retry=2):
    """
    Attempts to click cookie consent buttons on common popups.
    - Waits for banners to appear.
    - Handles iframes.
    - Retries and confirms dismissal.
    """
    for attempt in range(retry):
        try:
            # Try in main document
            for pattern in CONSENT_PATTERNS:
                try:
                    element = WebDriverWait(driver, timeout).until(
                        EC.element_to_be_clickable((pattern["by"], pattern["value"]))
                    )
                    element.click()
                    logger.info(f"[COOKIE] Clicked consent button: {pattern}")
                    time.sleep(1)
                    # Confirm banner is gone
                    if not is_consent_banner_present(driver):
                        return True
                except (TimeoutException, NoSuchElementException, ElementClickInterceptedException,
                        ElementNotInteractableException, StaleElementReferenceException):
                    continue
                except WebDriverException as e:
                    logger.warning(f"[COOKIE][CLICK] WebDriverException: {e}")
                    continue

            # Try in iframes
            if switch_to_iframe_if_present(driver):
                for pattern in CONSENT_PATTERNS:
                    try:
                        element = WebDriverWait(driver, timeout).until(
                            EC.element_to_be_clickable((pattern["by"], pattern["value"]))
                        )
                        element.click()
                        logger.info(f"[COOKIE][IFRAME] Clicked consent button: {pattern}")
                        driver.switch_to.default_content()
                        time.sleep(1)
                        if not is_consent_banner_present(driver):
                            return True
                    except Exception:
                        driver.switch_to.default_content()
                        continue
                driver.switch_to.default_content()

            logger.info("[COOKIE] No known consent button found on attempt %d.", attempt + 1)
            time.sleep(1)
        except Exception as e:
            logger.warning(f"[COOKIE_HANDLER] Exception: {e}")
    return False

def is_consent_banner_present(driver):
    """
    Heuristic: checks if any known consent banner/button is still present.
    """
    for pattern in CONSENT_PATTERNS:
        try:
            if driver.find_elements(pattern["by"], pattern["value"]):
                return True
        except Exception:
            continue
    return False
