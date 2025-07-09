# extractor/crawl/link_discovery.py
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urlunparse, parse_qsl, urlencode
from concurrent.futures import ThreadPoolExecutor, as_completed
import logging
import re
import time
import random
from urllib.robotparser import RobotFileParser

logger = logging.getLogger(__name__)

EXCLUDED_EXTENSIONS = ('.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.zip', '.rar', '.exe', '.mp4', '.avi')

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
}

def is_valid_url(href, domain):
    if not href or href.startswith(('mailto:', 'tel:')):
        return False
    parsed = urlparse(href)
    return (parsed.netloc == '' or parsed.netloc == domain) and not href.lower().endswith(EXCLUDED_EXTENSIONS)

def normalize_url(href, base_url):
    href = href.strip().split('#')[0]
    abs_url = urljoin(base_url, href)
    parsed = urlparse(abs_url)
    query = urlencode(sorted(parse_qsl(parsed.query)))
    path = parsed.path.rstrip('/') if parsed.path != '/' else parsed.path
    normalized = urlunparse((parsed.scheme, parsed.netloc, path, '', query, ''))
    return normalized

def get_canonical_url(soup, url):
    tag = soup.find('link', rel='canonical')
    if tag and tag.get('href'):
        return urljoin(url, tag['href'])
    return url

def robots_txt_allows(url, rp):
    try:
        return rp.can_fetch(HEADERS["User-Agent"], url)
    except Exception:
        return True

def discover_internal_links(start_url, max_pages=20, max_threads=10, respect_robots=False):
    parsed = urlparse(start_url)
    domain = parsed.netloc
    visited = set()
    to_visit = [normalize_url(start_url, start_url)]
    all_discovered = []
    error_stats = []

    # robots.txt setup
    rp = None
    if respect_robots:
        try:
            rp = RobotFileParser()
            rp.set_url(f"{parsed.scheme}://{domain}/robots.txt")
            rp.read()
        except Exception as e:
            logger.warning(f"[ROBOTS] Failed to read robots.txt: {e}")
            rp = None

    with ThreadPoolExecutor(max_workers=max_threads) as executor:
        while to_visit and len(visited) < max_pages:
            futures = {
                executor.submit(extract_links_from_page, url, domain): url
                for url in to_visit
                if url not in visited and (not respect_robots or robots_txt_allows(url, rp))
            }
            to_visit = []
            for future in as_completed(futures):
                base_url = futures[future]
                visited.add(base_url)
                try:
                    new_links = future.result()
                    for link in new_links:
                        if link not in visited and link not in to_visit and len(visited) + len(to_visit) < max_pages:
                            to_visit.append(link)
                    all_discovered.append(base_url)
                except Exception as e:
                    logger.warning(f"[THREAD_ERROR] Failed on {base_url}: {e}")
                    error_stats.append((base_url, str(e)))

    logger.info(f"[LINK_DISCOVERY] {len(all_discovered)} pages discovered. {len(error_stats)} errors.")
    return list(set(all_discovered)), error_stats

def extract_links_from_page(url, domain, retries=2, delay_range=(0.5, 1.5)):
    for attempt in range(retries):
        try:
            response = requests.get(url, headers=HEADERS, timeout=10)
            if 'text/html' not in response.headers.get('Content-Type', ''):
                return []
            soup = BeautifulSoup(response.text, 'html.parser')
            canonical_url = get_canonical_url(soup, url)
            links = set()
            for tag in soup.find_all('a', href=True):
                full_url = normalize_url(tag['href'], canonical_url)
                if is_valid_url(full_url, domain):
                    links.add(full_url)
            logger.info(f"[LINKS] {url}: {len(links)} links found")
            time.sleep(random.uniform(*delay_range))
            return list(links)
        except Exception as e:
            logger.warning(f"[DISCOVERY_FAIL] {url} (attempt {attempt+1}): {e}")
            time.sleep(2 ** attempt + random.uniform(0, 1))
    return []
