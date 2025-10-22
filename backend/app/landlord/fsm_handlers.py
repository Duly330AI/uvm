"""
Phase 3.1 - FSM Refactoring (2025-10-23):
State Handler Pattern for Chat FSM - Reduces CC 46 → <10

Each state has its own handler function with single responsibility.
This makes the code:
- More testable (test individual handlers)
- More maintainable (handlers are isolated)
- Lower complexity (each handler is simple)
"""
from __future__ import annotations

from typing import Dict, List, Tuple

from django.utils import timezone


def _detect_category(text: str) -> str | None:
    """
    Detect issue category from text keywords (German).

    Returns:
        Category string or None if no match
    """
    t = text.lower()

    if any(k in t for k in ["wasser", "leck", "leitung"]):
        return "water"
    elif any(k in t for k in ["heizung", "warm", "kalt"]):
        return "heating"
    elif any(k in t for k in ["strom", "stromschlag", "kabel"]):
        return "electricity"
    elif any(k in t for k in ["bau", "wand", "decke", "boden"]):
        return "structural"

    return None


def handle_greeting(message: Dict, payload: Dict) -> Tuple[str, str, Dict, List[str]]:
    """
    GREETING state: Initial message from user.

    If text provided, treat as summary and advance to CAPTURE_OCCURRED_AT.
    Otherwise, ask for summary.
    """
    warnings: List[str] = []
    delta: Dict = {}

    text = (message.get("text") or "").strip()

    if text:
        # User provided initial summary
        delta["summary"] = text
        category = _detect_category(text)
        if category:
            delta["category"] = category

        return (
            "CAPTURE_OCCURRED_AT",
            "Wann ist das Problem aufgetreten? (Datum/Zeit)",
            delta,
            warnings
        )

    # No text, ask for summary
    return (
        "CAPTURE_SUMMARY",
        "Guten Tag! Bitte beschreiben Sie kurz das Problem.",
        delta,
        warnings
    )


def handle_capture_summary(message: Dict, payload: Dict) -> Tuple[str, str, Dict, List[str]]:
    """
    CAPTURE_SUMMARY state: Get problem description.

    If occurred_at provided (skipping ahead), validate and advance.
    Otherwise, capture summary text.
    """
    warnings: List[str] = []
    delta: Dict = {}

    # Check if user skipped ahead with occurred_at
    if message.get("occurred_at") is not None:
        occurred_at = message.get("occurred_at")
        if occurred_at is None:
            raise ValueError("VALIDATION:occurred_at:required")

        now = timezone.now() + timezone.timedelta(minutes=5)
        if occurred_at > now:
            raise ValueError("VALIDATION:occurred_at:future")

        delta["occurred_at"] = occurred_at.isoformat()
        return (
            "CAPTURE_LOCATION",
            "Wo genau befindet sich das Problem (Ort im Objekt)?",
            delta,
            warnings
        )

    # Capture summary text
    text = (message.get("text") or "").strip()
    if not text:
        raise ValueError("VALIDATION:summary:required")

    delta["summary"] = text
    category = _detect_category(text)
    if category:
        delta["category"] = category

    return (
        "CAPTURE_OCCURRED_AT",
        "Wann ist das Problem aufgetreten? (Datum/Zeit)",
        delta,
        warnings
    )


def handle_capture_occurred_at(message: Dict, payload: Dict) -> Tuple[str, str, Dict, List[str]]:
    """
    CAPTURE_OCCURRED_AT state: Get when problem occurred.

    Validates datetime is not in the future.
    """
    warnings: List[str] = []
    delta: Dict = {}

    occurred_at = message.get("occurred_at")
    if not occurred_at:
        raise ValueError("VALIDATION:occurred_at:required")

    # Validate not future (allow 5min grace period)
    now = timezone.now() + timezone.timedelta(minutes=5)
    if occurred_at > now:
        raise ValueError("VALIDATION:occurred_at:future")

    delta["occurred_at"] = occurred_at.isoformat()

    return (
        "CAPTURE_LOCATION",
        "Wo genau befindet sich das Problem (Ort im Objekt)?",
        delta,
        warnings
    )


def handle_capture_location(message: Dict, payload: Dict) -> Tuple[str, str, Dict, List[str]]:
    """
    CAPTURE_LOCATION state: Get location hint.

    Validates max length 120 chars.
    """
    warnings: List[str] = []
    delta: Dict = {}

    location = (message.get("location") or "").strip()
    if not location:
        raise ValueError("VALIDATION:location:required")
    if len(location) > 120:
        raise ValueError("VALIDATION:location:maxlen")

    delta["location_hint"] = location

    return (
        "CAPTURE_SEVERITY",
        "Wie schwer ist das Problem? (1-5)",
        delta,
        warnings
    )


def handle_capture_severity(message: Dict, payload: Dict) -> Tuple[str, str, Dict, List[str]]:
    """
    CAPTURE_SEVERITY state: Get severity level 1-5.

    Boosts severity to 5 if danger keywords detected (gas, fire, electric shock).
    """
    warnings: List[str] = []
    delta: Dict = {}

    sev = message.get("severity")
    if not isinstance(sev, int) or not (1 <= sev <= 5):
        raise ValueError("VALIDATION:severity:range")

    # Check for danger keywords - boost to max severity
    text_blob = " ".join(str(v) for v in message.values()).lower()
    for kw in {"gas", "gasgeruch", "stromschlag", "brand"}:
        if kw in text_blob:
            sev = max(sev, 5)
            warnings.append(f"Gefahrhinweis: {kw}")

    delta["severity"] = sev

    return (
        "CAPTURE_MEDIA",
        "Möchten Sie Fotos/Videos/PDFs hinzufügen? (optional)",
        delta,
        warnings
    )


def handle_capture_media(message: Dict, payload: Dict) -> Tuple[str, str, Dict, List[str]]:
    """
    CAPTURE_MEDIA state: Optional file uploads.

    Files validated separately, just transition to next state.
    """
    warnings: List[str] = []
    delta: Dict = {}

    return (
        "CAPTURE_CONTACT",
        "Wie erreichen wir Sie am besten (Telefon oder E-Mail)?",
        delta,
        warnings
    )


def handle_capture_contact(message: Dict, payload: Dict) -> Tuple[str, str, Dict, List[str]]:
    """
    CAPTURE_CONTACT state: Optional contact preferences.
    """
    warnings: List[str] = []
    delta: Dict = {}

    contact = (message.get("contact") or "").strip()
    if contact:
        delta["contact_times"] = contact

    return (
        "CONFIRM",
        "Bitte prüfen Sie die Eingaben und bestätigen Sie.",
        delta,
        warnings
    )


def handle_confirm(message: Dict, payload: Dict) -> Tuple[str, str, Dict, List[str]]:
    """
    CONFIRM state: User confirms data, trigger issue creation.
    """
    warnings: List[str] = []
    delta: Dict = {}

    return (
        "CREATE_ISSUE",
        "Ticket wird erstellt...",
        delta,
        warnings
    )


def handle_create_issue(message: Dict, payload: Dict) -> Tuple[str, str, Dict, List[str]]:
    """
    CREATE_ISSUE state: Transition to DONE.
    """
    warnings: List[str] = []
    delta: Dict = {}

    return (
        "DONE",
        "Vielen Dank – Ticket erstellt.",
        delta,
        warnings
    )


def handle_done(message: Dict, payload: Dict) -> Tuple[str, str, Dict, List[str]]:
    """
    DONE state: Conversation finished.
    """
    return ("DONE", "Konversation abgeschlossen.", {}, [])


# State handler registry - maps state name to handler function
STATE_HANDLERS = {
    "GREETING": handle_greeting,
    "CAPTURE_SUMMARY": handle_capture_summary,
    "CAPTURE_OCCURRED_AT": handle_capture_occurred_at,
    "CAPTURE_LOCATION": handle_capture_location,
    "CAPTURE_SEVERITY": handle_capture_severity,
    "CAPTURE_MEDIA": handle_capture_media,
    "CAPTURE_CONTACT": handle_capture_contact,
    "CONFIRM": handle_confirm,
    "CREATE_ISSUE": handle_create_issue,
    "DONE": handle_done,
}
