import re

from rest_framework.throttling import AnonRateThrottle


class ChatRateThrottle(AnonRateThrottle):
    scope = "chat"

    def get_cache_key(self, request, view):  # type: ignore[override]
        # Allow tests to disable throttling explicitly
        if request.META.get("HTTP_X_NO_THROTTLE"):
            return None
        # Per-session throttle: include session_id to scope limits to a session
        session_id = getattr(view, "session_id", None)
        if not session_id:
            try:
                rm = getattr(request, "resolver_match", None)
                if rm and rm.kwargs:
                    session_id = rm.kwargs.get("id")
            except Exception:
                session_id = None
        if not session_id:
            # Final fallback: parse from path /api/chat/sessions/{id}/message
            m = re.search(r"/api/chat/sessions/([^/]+)/message", request.path or "")
            if m:
                session_id = m.group(1)
        if not session_id:
            # If we cannot determine session-id, do not throttle this request to avoid global IP coupling
            return None
        # Combine session and client ident (IP) for runtime parity
        ident = self.get_ident(request)
        return f"throttle:{self.scope}:{session_id}:{ident}"
