"""Public-page contact discovery for a company's website (Phase 2).

Crawls a handful of well-known public paths (home, /contact-us, /csr,
/sustainability, ...) on a company's own site looking for publicly
listed emails, phone numbers, and LinkedIn profile links.

Etiquette / compliance:
    - identifiable User-Agent (no spoofing)
    - robots.txt is checked once per domain; disallowed paths are skipped
    - a small fixed delay between requests
    - single company site per call; no recursive/offsite crawling

This module only extracts information a company has already published
publicly for the purpose of being contacted (e.g. "Contact Us" / "CSR"
pages). It does not bypass logins, paywalls, or CAPTCHAs.
"""

from __future__ import annotations

import logging
import re
import time
from typing import Optional
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests

logger = logging.getLogger("scraping")

USER_AGENT = "CSROutreachBot/1.0 (CSR Outreach Automation; contact-discovery)"
REQUEST_TIMEOUT_SECONDS = 8
REQUEST_DELAY_SECONDS = 1.0
CANDIDATE_PATHS = ["/", "/contact-us", "/contact", "/csr", "/sustainability", "/about/contact"]

EMAIL_PATTERN = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
PHONE_PATTERN = re.compile(r"\+?\d[\d\-\s()]{8,}\d")
LINKEDIN_PATTERN = re.compile(
    r"https?://(?:[a-z]{2,3}\.)?linkedin\.com/(?:in|company)/[A-Za-z0-9\-_%]+/?", re.IGNORECASE
)


def _base_url(website: str) -> Optional[str]:
    if not website:
        return None
    parsed = urlparse(website if "://" in website else f"https://{website}")
    if not parsed.netloc:
        return None
    return f"{parsed.scheme}://{parsed.netloc}"


def _load_robots(base: str) -> RobotFileParser:
    parser = RobotFileParser()
    parser.set_url(urljoin(base, "/robots.txt"))
    try:
        parser.read()
    except Exception:
        # Unreachable robots.txt: treat as unrestricted, same convention
        # most well-behaved crawlers use for a missing/broken robots.txt.
        parser.parse([])
    return parser


def _fetch_page(url: str) -> Optional[str]:
    try:
        response = requests.get(url, headers={"User-Agent": USER_AGENT}, timeout=REQUEST_TIMEOUT_SECONDS)
    except requests.RequestException as exc:
        logger.info("Could not fetch %s: %s", url, exc)
        return None
    if response.status_code != 200:
        return None
    return response.text


def extract_contacts_from_html(html: str, source_url: str) -> list[dict]:
    """Pure parsing: pull emails/phones/LinkedIn links out of a page's HTML."""
    emails = set(EMAIL_PATTERN.findall(html))
    phones = set(m.strip() for m in PHONE_PATTERN.findall(html) if len(re.sub(r"\D", "", m)) >= 10)
    linkedin_urls = set(LINKEDIN_PATTERN.findall(html))

    contacts: list[dict] = []
    for email in emails:
        contacts.append({"email": email, "phone": None, "linkedin_url": None, "source_url": source_url})
    for phone in phones:
        contacts.append({"email": None, "phone": phone, "linkedin_url": None, "source_url": source_url})
    for linkedin_url in linkedin_urls:
        contacts.append({"email": None, "phone": None, "linkedin_url": linkedin_url, "source_url": source_url})
    return contacts


def _dedupe(contacts: list[dict]) -> list[dict]:
    seen: dict[tuple, dict] = {}
    for contact in contacts:
        key = (contact.get("email"), contact.get("phone"), contact.get("linkedin_url"))
        if key not in seen:
            seen[key] = contact
    return list(seen.values())


def discover_company_contacts(website: str) -> list[dict]:
    """Crawl a company's own site for publicly listed contact details.

    Returns a list of candidate dicts: {email, phone, linkedin_url,
    source_url}. Never raises on network/robots failures for an
    individual path - those paths are just skipped.
    """
    base = _base_url(website)
    if base is None:
        return []

    robots = _load_robots(base)
    found: list[dict] = []

    for index, path in enumerate(CANDIDATE_PATHS):
        url = urljoin(base, path)
        if not robots.can_fetch(USER_AGENT, url):
            logger.info("Skipping %s: disallowed by robots.txt", url)
            continue
        if index > 0:
            time.sleep(REQUEST_DELAY_SECONDS)
        html = _fetch_page(url)
        if html:
            found.extend(extract_contacts_from_html(html, url))

    return _dedupe(found)
