from __future__ import annotations

from rest_framework.exceptions import Throttled
from rest_framework.views import exception_handler


def custom_exception_handler(exc, ctx):
    resp = exception_handler(exc, ctx)
    if isinstance(exc, Throttled) and resp is not None:
        # Einheitliches Schema + Retry-Header
        resp.data = {"code": "RATE_LIMITED", "retry_after": exc.wait}
        if getattr(exc, "wait", None) is not None:
            try:
                resp["Retry-After"] = str(int(exc.wait))
            except Exception:
                pass
    return resp
