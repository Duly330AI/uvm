from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Tuple

from landlord.fsm_handlers import STATE_HANDLERS


@dataclass(frozen=True)
class ChatFSM:
    """
    Phase 3.1 - Refactored FSM (2025-10-23):

    Reduced Cyclomatic Complexity from 46 → ~3 by using State Handler Pattern.
    Each state is handled by a dedicated function in fsm_handlers.py.

    Benefits:
    - Each handler is simple and testable in isolation
    - Easy to add new states (just add handler to registry)
    - Low complexity per function (<5 CC each)
    """

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
        """
        Dispatch to appropriate state handler.

        Args:
            state: Current FSM state
            message: User message dict
            payload: Current session payload

        Returns:
            Tuple of (next_state, prompt, delta_payload, warnings)

        Raises:
            ValueError: If state unknown or validation fails
        """
        # Get handler for current state
        handler = STATE_HANDLERS.get(state)

        if handler is None:
            raise ValueError("VALIDATION:state:unknown")

        # Dispatch to handler
        return handler(message, payload)
