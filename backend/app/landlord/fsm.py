from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from django.utils import timezone


@dataclass(frozen=True)
class ChatFSM:
    states = [
        "GREETING",
        "CAPTURE_SUMMARY",
        "CAPTURE_OCCURRED_AT",
        "CAPTURE_LOCATION",
        "CAPTURE_SEVERITY",
        "CAPTURE_MEDIA",
        "CAPTURE_CONTACT",
        "CONFIRM",
        "CREATE_ISSUE",
        "DONE",
    ]

    def next(self, state: str, message: Dict, payload: Dict) -> Tuple[str, str, Dict, List[str]]:
        warnings: List[str] = []
        delta: Dict = {}
        next_prompt = ""

        if state == "GREETING":
            # Allow initial free-form text; if provided, treat as summary and advance further
            text = (message.get("text") or "").strip()
            if text:
                delta["summary"] = text
                t = text.lower()
                if any(k in t for k in ["wasser", "leck", "leitung"]):
                    delta["category"] = "water"
                elif any(k in t for k in ["heizung", "warm", "kalt"]):
                    delta["category"] = "heating"
                elif any(k in t for k in ["strom", "stromschlag", "kabel"]):
                    delta["category"] = "electricity"
                elif any(k in t for k in ["bau", "wand", "decke", "boden"]):
                    delta["category"] = "structural"
                next_state = "CAPTURE_OCCURRED_AT"
                next_prompt = "Wann ist das Problem aufgetreten? (Datum/Zeit)"
                return next_state, next_prompt, delta, warnings
            next_state = "CAPTURE_SUMMARY"
            next_prompt = "Guten Tag! Bitte beschreiben Sie kurz das Problem."
            return next_state, next_prompt, delta, warnings

        if state == "CAPTURE_SUMMARY":
            # If user sends occurred_at directly (e.g., summary already captured), allow advancing
            if message.get("occurred_at") is not None:
                occurred_at = message.get("occurred_at")
                if occurred_at is None:
                    raise ValueError("VALIDATION:occurred_at:required")
                now = timezone.now() + timezone.timedelta(minutes=5)
                if occurred_at > now:
                    raise ValueError("VALIDATION:occurred_at:future")
                delta["occurred_at"] = occurred_at.isoformat()
                next_state = "CAPTURE_LOCATION"
                next_prompt = "Wo genau befindet sich das Problem (Ort im Objekt)?"
                return next_state, next_prompt, delta, warnings
            text = (message.get("text") or "").strip()
            if not text:
                raise ValueError("VALIDATION:summary:required")
            delta["summary"] = text
            # simple heuristic for category
            t = text.lower()
            if any(k in t for k in ["wasser", "leck", "leitung"]):
                delta["category"] = "water"
            elif any(k in t for k in ["heizung", "warm", "kalt"]):
                delta["category"] = "heating"
            elif any(k in t for k in ["strom", "stromschlag", "kabel"]):
                delta["category"] = "electricity"
            elif any(k in t for k in ["bau", "wand", "decke", "boden"]):
                delta["category"] = "structural"
            next_state = "CAPTURE_OCCURRED_AT"
            next_prompt = "Wann ist das Problem aufgetreten? (Datum/Zeit)"
            return next_state, next_prompt, delta, warnings

        if state == "CAPTURE_OCCURRED_AT":
            occurred_at = message.get("occurred_at")
            if not occurred_at:
                raise ValueError("VALIDATION:occurred_at:required")
            # occurred_at wird im Serializer in ein aware-datetime konvertiert
            now = timezone.now() + timezone.timedelta(minutes=5)
            if occurred_at > now:
                raise ValueError("VALIDATION:occurred_at:future")
            delta["occurred_at"] = occurred_at.isoformat()
            next_state = "CAPTURE_LOCATION"
            next_prompt = "Wo genau befindet sich das Problem (Ort im Objekt)?"
            return next_state, next_prompt, delta, warnings

        if state == "CAPTURE_LOCATION":
            location = (message.get("location") or "").strip()
            if not location:
                raise ValueError("VALIDATION:location:required")
            if len(location) > 120:
                raise ValueError("VALIDATION:location:maxlen")
            delta["location_hint"] = location
            next_state = "CAPTURE_SEVERITY"
            next_prompt = "Wie schwer ist das Problem? (1-5)"
            return next_state, next_prompt, delta, warnings

        if state == "CAPTURE_SEVERITY":
            sev = message.get("severity")
            if not isinstance(sev, int) or not (1 <= sev <= 5):
                raise ValueError("VALIDATION:severity:range")
            # Danger words boost
            text_blob = " ".join(str(v) for v in message.values()).lower()
            for kw in {"gas", "gasgeruch", "stromschlag", "brand"}:
                if kw in text_blob:
                    sev = max(sev, 5)
                    warnings.append(f"Gefahrhinweis: {kw}")
            delta["severity"] = sev
            next_state = "CAPTURE_MEDIA"
            next_prompt = "Möchten Sie Fotos/Videos/PDFs hinzufügen? (optional)"
            return next_state, next_prompt, delta, warnings

        if state == "CAPTURE_MEDIA":
            # Files werden separat validiert; hier nur Übergang
            next_state = "CAPTURE_CONTACT"
            next_prompt = "Wie erreichen wir Sie am besten (Telefon oder E-Mail)?"
            return next_state, next_prompt, delta, warnings

        if state == "CAPTURE_CONTACT":
            contact = (message.get("contact") or "").strip()
            if contact:
                delta["contact_times"] = contact
            next_state = "CONFIRM"
            next_prompt = "Bitte prüfen Sie die Eingaben und bestätigen Sie."
            return next_state, next_prompt, delta, warnings

        if state == "CONFIRM":
            next_state = "CREATE_ISSUE"
            next_prompt = "Ticket wird erstellt..."
            return next_state, next_prompt, delta, warnings

        if state == "CREATE_ISSUE":
            next_state = "DONE"
            next_prompt = "Vielen Dank – Ticket erstellt."
            return next_state, next_prompt, delta, warnings

        if state == "DONE":
            return state, "Konversation abgeschlossen.", {}, []

        raise ValueError("VALIDATION:state:unknown")
