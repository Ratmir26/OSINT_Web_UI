"""Email lookup module - checks breaches, reputation, and web presence."""

from __future__ import annotations

import logging
from typing import Any

from utils.helpers import extract_emails
from utils.web_scraper import safe_get

logger = logging.getLogger(__name__)

try:
    from ddgs import DDGS

    _DDGS_AVAILABLE = True
except ImportError:
    _DDGS_AVAILABLE = False


def lookup_email(email: str) -> dict[str, Any]:
    """Look up an email across multiple sources for breaches, reputation, and web presence.

    Args:
        email: The email address to investigate.

    Returns:
        Dict with keys: email, reputation, breaches, found_on_web, sources.
    """
    result: dict[str, Any] = {
        "email": email,
        "reputation": "clean",
        "breaches": [],
        "found_on_web": [],
        "sources": [],
    }

    _check_emailrep(email, result)
    _check_hibp(email, result)
    _search_web(email, result)

    if not result["sources"]:
        result["reputation"] = "unknown"

    return result


def _check_emailrep(email: str, result: dict) -> None:
    """Check email reputation via emailrep.io public API."""
    try:
        url = f"https://emailrep.io/{email}"
        resp = safe_get(url, timeout=10)
        if resp is None:
            return

        data = resp.json()
        details = data.get("details") or {}

        if data.get("suspicious"):
            result["reputation"] = "suspicious"
        if details.get("malicious_activity"):
            result["reputation"] = "malicious"
        if details.get("credentials_leaked") and result["reputation"] == "clean":
            result["reputation"] = "suspicious"

        result["sources"].append("emailrep.io")
    except Exception as exc:
        logger.debug("emailrep.io lookup failed for %s: %s", email, exc)


def _check_hibp(email: str, result: dict) -> None:
    """Check haveibeenpwned for known breaches."""
    try:
        url = f"https://haveibeenpwned.com/api/v3/breachedaccount/{email}"
        resp = safe_get(url, timeout=10)
        if resp is None:
            return

        breaches = resp.json()
        for b in breaches:
            result["breaches"].append(
                {
                    "name": b.get("Name", ""),
                    "domain": b.get("Domain", ""),
                    "date": b.get("BreachDate", ""),
                    "pwn_count": b.get("PwnCount", 0),
                    "data_classes": b.get("DataClasses", []),
                    "description": (b.get("Description") or "")[:300],
                }
            )

        result["sources"].append("haveibeenpwned.com")
    except Exception as exc:
        logger.debug("HIBP lookup failed for %s: %s", email, exc)


def _search_web(email: str, result: dict) -> None:
    """Search for the email on DuckDuckGo and collect public mentions."""
    if not _DDGS_AVAILABLE:
        return

    try:
        ddgs = DDGS()
        raw_results = ddgs.text(email, max_results=5)

        for item in raw_results:
            link = item.get("href") or item.get("link") or ""
            title = item.get("title") or ""
            snippet = item.get("body") or item.get("snippet") or ""

            if link:
                result["found_on_web"].append(
                    {
                        "url": link,
                        "title": title,
                        "snippet": snippet,
                    }
                )

        if result["found_on_web"]:
            result["sources"].append("duckduckgo.com")
    except Exception as exc:
        logger.debug("DuckDuckGo search failed for %s: %s", email, exc)
