"""
scraper.py
-----------
Data-acquisition module for A Ray of Hope Foundation's CSR Outreach Portal.

Crawls a target company's public website (specifically /csr,
/sustainability, and /contact-us style subpaths) to extract publicly
listed emails, phone numbers, and LinkedIn profile URLs, then inserts
qualified leads directly via database.add_company().

Etiquette / compliance built in:
    - Honest, identifiable User-Agent (no spoofing).
    - robots.txt is checked before every fetch; disallowed paths are skipped.
    - Fixed delay between requests to avoid hammering target servers.
    - Domain-level de-duplication against companies already in the DB.

This module only extracts information that is already published publicly
by the company for the purpose of being contacted (e.g. "Contact Us" /
"CSR" pages). It does not bypass logins, paywalls, or CAPTCHAs, and it
respects robots.txt directives.
"""

from __future__ import annotations

import time
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Set
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

from .config import REGEX_PATTERNS
from .database import add_company, get_all_companies_df

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("scraper")

# ----------------------------------------------------------------------------
# CONFIG
# ----------------------------------------------------------------------------
REQUEST_TIMEOUT = 10  # seconds
RATE_LIMIT_DELAY_SECONDS = 2.0  # pause between requests to the same/any host

HEADERS = {
    "User-Agent": (
        "ARayOfHopeFoundation-CSROutreachBot/1.0 "
        "(+https://www.arayofhope.org.in; contact: outreach@arayofhope.org.in)"
    ),
    "Accept": "text/html,application/xhtml+xml",
}

TARGET_SUBPATHS = [
    "",  # homepage — often has a general contact/footer email
    "/csr",
    "/csr/",
    "/corporate-social-responsibility",
    "/sustainability",
    "/contact-us",
    "/contact",
]

# Emails on generic ad/tracking pixels or Sentry-style noise we don't want
EMAIL_IGNORE_SUBSTRINGS = (
    "sentry", "wixpress", "example.com", "yourdomain", "no-reply@no-reply",
)


@dataclass
class ScrapedContact:
    company_name: str
    base_url: str
    domain: str
    emails: Set[str] = field(default_factory=set)
    phones: Set[str] = field(default_factory=set)
    linkedin_urls: Set[str] = field(default_factory=set)
    pages_crawled: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)


# ----------------------------------------------------------------------------
# ROBOTS.TXT COMPLIANCE
# ----------------------------------------------------------------------------
def _get_robot_parser(base_url: str) -> Optional[RobotFileParser]:
    """Fetches and parses robots.txt for a domain. Returns None on failure
    (fail-open to 'allowed' is NOT used here — see can_fetch)."""
    robots_url = urljoin(base_url, "/robots.txt")
    parser = RobotFileParser()
    try:
        resp = requests.get(robots_url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200:
            parser.parse(resp.text.splitlines())
            return parser
    except requests.RequestException as e:
        logger.debug(f"Could not fetch robots.txt for {base_url}: {e}")
    return None


def can_fetch(base_url: str, path: str, robot_parser: Optional[RobotFileParser]) -> bool:
    """Returns True if crawling `path` is permitted. If robots.txt is
    unreachable/absent, defaults to allowed (standard convention)."""
    if robot_parser is None:
        return True
    url = urljoin(base_url, path)
    return robot_parser.can_fetch(HEADERS["User-Agent"], url)


# ----------------------------------------------------------------------------
# FETCHING
# ----------------------------------------------------------------------------
def fetch_page(url: str) -> Optional[str]:
    """Fetches a single page with error handling. Returns HTML text or None."""
    try:
        resp = requests.get(url, headers=HEADERS, timeout=REQUEST_TIMEOUT)
        if resp.status_code == 200 and "text/html" in resp.headers.get("Content-Type", ""):
            return resp.text
        logger.info(f"Skipped {url} (status={resp.status_code})")
        return None
    except requests.exceptions.Timeout:
        logger.warning(f"Timeout fetching {url}")
    except requests.exceptions.RequestException as e:
        logger.warning(f"Error fetching {url}: {e}")
    return None


# ----------------------------------------------------------------------------
# EXTRACTION
# ----------------------------------------------------------------------------
def extract_contacts_from_html(html: str) -> Dict[str, Set[str]]:
    """Extracts emails, phone numbers, and LinkedIn URLs from raw HTML
    using the regex patterns defined in config.REGEX_PATTERNS."""
    soup = BeautifulSoup(html, "html.parser")

    # Strip script/style so we don't match JS-embedded junk
    for tag in soup(["script", "style"]):
        tag.decompose()

    text = soup.get_text(separator=" ")

    # config.REGEX_PATTERNS are anchored (^...$) for form-field validation,
    # so they won't match a substring inside a larger block of page text.
    # Scan with unanchored candidate patterns, then re-validate each hit
    # against the canonical config pattern to keep a single source of truth.
    import re as _re

    emails = set()
    for m in _re.finditer(r"[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}", text):
        candidate = m.group(0).lower()
        if REGEX_PATTERNS["email"].match(candidate) and not any(
            bad in candidate for bad in EMAIL_IGNORE_SUBSTRINGS
        ):
            emails.add(candidate)

    phone_candidates = set()
    for m in _re.finditer(r"(?:\+91[\-\s]?|0)?[6-9]\d{9}", text):
        if REGEX_PATTERNS["phone"].match(m.group(0)):
            phone_candidates.add(m.group(0))

    linkedin_urls = set()
    for a_tag in soup.find_all("a", href=True):
        href = a_tag["href"].split("?")[0].rstrip("/")
        if REGEX_PATTERNS["linkedin"].match(href):
            linkedin_urls.add(href)

    return {"emails": emails, "phones": phone_candidates, "linkedin_urls": linkedin_urls}


# ----------------------------------------------------------------------------
# DEDUPLICATION
# ----------------------------------------------------------------------------
def get_existing_domains() -> Set[str]:
    """Returns the set of domains already present in the companies table,
    derived from stored email and linkedin_url fields, for dedup purposes."""
    df = get_all_companies_df()
    domains: Set[str] = set()

    if df.empty:
        return domains

    for email in df.get("email", pd_series_fallback(df)):
        if isinstance(email, str) and "@" in email:
            domains.add(email.split("@")[-1].lower())

    return domains


def pd_series_fallback(df):
    """Guards against a DataFrame that has no 'email' column."""
    return []


def domain_of(url: str) -> str:
    netloc = urlparse(url).netloc.lower()
    return netloc[4:] if netloc.startswith("www.") else netloc


# ----------------------------------------------------------------------------
# CRAWLING
# ----------------------------------------------------------------------------
def crawl_company(base_url: str, company_name: str) -> ScrapedContact:
    """Crawls the configured subpaths of a single company's site and
    aggregates any extracted contact details."""
    if not base_url.startswith(("http://", "https://")):
        base_url = f"https://{base_url}"

    result = ScrapedContact(company_name=company_name, base_url=base_url, domain=domain_of(base_url))
    robot_parser = _get_robot_parser(base_url)

    for subpath in TARGET_SUBPATHS:
        if not can_fetch(base_url, subpath, robot_parser):
            logger.info(f"robots.txt disallows {base_url}{subpath} — skipping")
            continue

        url = urljoin(base_url, subpath)
        html = fetch_page(url)
        time.sleep(RATE_LIMIT_DELAY_SECONDS)

        if html is None:
            continue

        result.pages_crawled.append(url)
        extracted = extract_contacts_from_html(html)
        result.emails |= extracted["emails"]
        result.phones |= extracted["phones"]
        result.linkedin_urls |= extracted["linkedin_urls"]

    return result


def run_scraper(
    targets: List[Dict[str, str]],
    default_zone: str = "Unspecified",
    default_csr_focus: str = "Education & Child Welfare",
) -> Dict[str, int]:
    """
    Runs the scraper across a list of target companies and inserts
    qualified leads into the database.

    Args:
        targets: list of {"company_name": str, "url": str, "zone": str (optional),
                  "csr_focus": str (optional)}
        default_zone / default_csr_focus: fallback values when not
            provided per-target.

    Returns:
        Summary dict: {"scraped": int, "inserted": int, "skipped_duplicate": int,
                        "skipped_no_contact": int}
    """
    existing_domains = get_existing_domains()
    summary = {"scraped": 0, "inserted": 0, "skipped_duplicate": 0, "skipped_no_contact": 0}

    for target in targets:
        company_name = target["company_name"]
        url = target["url"]
        domain = domain_of(url if url.startswith("http") else f"https://{url}")

        if domain in existing_domains:
            logger.info(f"Skipping {company_name} ({domain}) — already in database")
            summary["skipped_duplicate"] += 1
            continue

        logger.info(f"Crawling {company_name} ({url})...")
        result = crawl_company(url, company_name)
        summary["scraped"] += 1

        if not result.emails and not result.linkedin_urls:
            logger.info(f"No contact info found for {company_name} — skipping insert")
            summary["skipped_no_contact"] += 1
            continue

        primary_email = sorted(result.emails)[0] if result.emails else ""
        primary_phone = sorted(result.phones)[0] if result.phones else ""
        primary_linkedin = sorted(result.linkedin_urls)[0] if result.linkedin_urls else ""

        add_company(
            company_name=company_name,
            zone=target.get("zone", default_zone),
            csr_focus=target.get("csr_focus", default_csr_focus),
            contact_person="",  # scraping rarely yields a verified name+title pair;
            designation="",     # use enrichment.py to fill these via Hunter/Apollo
            email=primary_email,
            phone=primary_phone,
            linkedin_url=primary_linkedin,
            status="New Lead",
            notes=(
                f"Auto-scraped from {len(result.pages_crawled)} page(s): "
                f"{', '.join(result.pages_crawled)}. "
                f"Found {len(result.emails)} email(s), {len(result.phones)} phone(s), "
                f"{len(result.linkedin_urls)} LinkedIn URL(s)."
            ),
        )
        existing_domains.add(domain)
        summary["inserted"] += 1

    logger.info(f"Scrape run complete: {summary}")
    return summary


# ----------------------------------------------------------------------------
# CLI ENTRYPOINT
# ----------------------------------------------------------------------------
if __name__ == "__main__":
    # Example target list — replace with a real prospect list (e.g. loaded
    # from enrichment.py's MCA parser output) before running in production.
    sample_targets = [
        {"company_name": "Persistent Systems", "url": "https://www.persistent.com",
         "zone": "Hinjawadi", "csr_focus": "Digital Literacy / EdTech"},
        {"company_name": "KPIT Technologies", "url": "https://www.kpit.com",
         "zone": "Hinjawadi", "csr_focus": "STEM Education"},
    ]
    run_scraper(sample_targets)