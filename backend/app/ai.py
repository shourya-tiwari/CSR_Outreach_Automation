"""Google Gemini integration for AI-assisted content (Phase 3).

Every public function here degrades gracefully when GEMINI_API_KEY
isn't set - callers check `is_configured()` first and show a "not
configured" state rather than erroring, the same pattern as
Hunter/Apollo in app/enrichment.py (Phase 2).

Everything produced here is a DRAFT for NGO staff to review and edit -
nothing in this module sends an email or takes any outreach action on
its own.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

import requests

from .config import settings

logger = logging.getLogger("ai")

REQUEST_TIMEOUT_SECONDS = 20
GEMINI_ENDPOINT = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"

EMAIL_TYPE_LABELS = {
    "first_outreach": "a first outreach / introduction email",
    "follow_up": "a polite follow-up email after no response yet",
    "meeting_request": "an email requesting a meeting",
    "thank_you": "a thank-you email after a positive interaction",
}

EMAIL_JSON_SCHEMA = {
    "type": "object",
    "properties": {
        "subject": {"type": "string"},
        "body": {"type": "string"},
    },
    "required": ["subject", "body"],
}


def is_configured() -> bool:
    return bool(settings.gemini_api_key)


def _call_gemini(prompt: str, *, json_schema: Optional[dict] = None) -> Optional[str]:
    """Low-level Gemini call. Returns the raw text response, or None on any failure."""
    if not settings.gemini_api_key:
        return None

    body: dict = {"contents": [{"parts": [{"text": prompt}]}]}
    if json_schema is not None:
        body["generationConfig"] = {
            "responseMimeType": "application/json",
            "responseSchema": json_schema,
        }

    url = GEMINI_ENDPOINT.format(model=settings.gemini_model)
    try:
        response = requests.post(
            url, params={"key": settings.gemini_api_key}, json=body, timeout=REQUEST_TIMEOUT_SECONDS
        )
        response.raise_for_status()
    except requests.RequestException as exc:
        logger.warning("Gemini request failed: %s", exc)
        return None

    try:
        data = response.json()
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, ValueError) as exc:
        logger.warning("Unexpected Gemini response shape: %s", exc)
        return None


def explain_lead_score(company_name: str, factors: dict, score: int, priority: str) -> Optional[str]:
    prompt = (
        "You are helping an NGO's outreach team understand a CSR lead score.\n"
        f"Company: {company_name}\n"
        f"Total score: {score}/100 ({priority} priority)\n"
        f"Score breakdown (points out of a max per factor): {factors}\n\n"
        "Write 2-3 short bullet points (plain text, one per line, no markdown headers) "
        "explaining why this company scored this way, in plain language for non-technical "
        "NGO staff."
    )
    return _call_gemini(prompt)


def generate_email(
    *,
    ngo_name: str,
    ngo_work_area: str,
    company_name: str,
    contact_name: Optional[str],
    contact_designation: Optional[str],
    csr_focus: Optional[str],
    email_type: str,
) -> Optional[dict]:
    kind = EMAIL_TYPE_LABELS.get(email_type, email_type)
    prompt = (
        f"Write {kind} from {ngo_name}, an NGO focused on {ngo_work_area}, "
        f"to {contact_name or 'the CSR contact'} ({contact_designation or 'CSR contact'}) "
        f"at {company_name}. {company_name}'s CSR focus area is "
        f"{csr_focus or 'not specified'}. Keep it concise, professional, and warm. This is "
        "a DRAFT the NGO staff will review and edit before sending - do not include "
        "placeholder brackets like [Name], write natural text throughout."
    )
    raw = _call_gemini(prompt, json_schema=EMAIL_JSON_SCHEMA)
    if not raw:
        return None
    try:
        data = json.loads(raw)
        return {"subject": data["subject"], "body": data["body"]}
    except (ValueError, KeyError, TypeError) as exc:
        logger.warning("Could not parse Gemini email JSON (%s): %r", exc, raw)
        return None


def generate_company_summary(
    *,
    company_name: str,
    industry: Optional[str],
    city: Optional[str],
    state: Optional[str],
    csr_focus: Optional[str],
    csr_spending: Optional[float],
    ngo_name: str,
    ngo_work_area: str,
) -> Optional[str]:
    location = " ".join(part for part in [city, state] if part) or "an unspecified location"
    spending_clause = (
        f" with reported CSR spending around Rs. {csr_spending:,.0f}." if csr_spending else "."
    )
    prompt = (
        f"Write a short (4-6 sentence) briefing for an NGO outreach team about {company_name}, "
        f"a company in the {industry or 'unspecified'} industry based in {location}. "
        f"Its CSR focus area is {csr_focus or 'not publicly specified'}{spending_clause} "
        f"Cover: a brief business overview, their apparent CSR initiatives/focus, how well "
        f"this fits {ngo_name} (which works on {ngo_work_area}), and 2-3 key talking points "
        "for an initial conversation. Plain text, no markdown headers."
    )
    return _call_gemini(prompt)


def generate_meeting_brief(
    *,
    company_name: str,
    industry: Optional[str],
    city: Optional[str],
    state: Optional[str],
    csr_focus: Optional[str],
    notes: list[str],
) -> Optional[str]:
    location = " ".join(part for part in [city, state] if part) or "an unspecified location"
    notes_text = "\n".join(f"- {note}" for note in notes) if notes else "(no notes recorded yet)"
    prompt = (
        f"Prepare a short meeting brief for an NGO team about to meet with {company_name} "
        f"({industry or 'unspecified industry'}, {location}). Their CSR focus area is "
        f"{csr_focus or 'not publicly specified'}. Past notes on this relationship:\n"
        f"{notes_text}\n\n"
        "Include: company background (2-3 sentences), likely CSR priorities, 3-4 suggested "
        "discussion points, 2-3 questions to ask, and 1-2 collaboration ideas. Plain text, "
        "no markdown headers."
    )
    return _call_gemini(prompt)
