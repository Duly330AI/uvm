from __future__ import annotations

import math
import os

import redis
from django.conf import settings
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.db.models import Count, Q
from django.http import HttpResponseNotAllowed, JsonResponse
from django.shortcuts import get_object_or_404
from django.urls import reverse_lazy
from django.utils import timezone
from django.utils.dateparse import parse_datetime
from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_exempt, ensure_csrf_cookie
from django.views.generic import (
    CreateView,
    DetailView,
    ListView,
    TemplateView,
    UpdateView,
)
from rest_framework import parsers, permissions, status
from rest_framework.exceptions import Throttled
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import ChatSession, Property, UtilityMeter
from .serializers import ChatMessageSerializer, ChatSessionCreateSerializer
from .services.chat_session import confirm as confirm_svc
from .services.chat_session import message as message_svc

_r = redis.from_url(settings.REDIS_URL)


def _per_session_throttle(session_id: str, limit: int | None = None) -> bool:
    now = timezone.now()
    key = f"chat:{session_id}:rate:{int(now.timestamp())}"
    pipe = _r.pipeline()
    pipe.incr(key, 1)
    pipe.expire(key, 2)
    count, _ = pipe.execute()
    lim = limit if limit is not None else int(getattr(settings, "CHAT_BURST_LIMIT", 5))
    return int(count) <= lim


def enforce_burst_throttle(session_id: str) -> None:
    """Per-Session Burst Throttle: max N requests per second.
    Respects CHAT_DISABLE_BURST_THROTTLE / CHAT_BURST_LIMIT and fails open on Redis errors.
    """
    if os.getenv("CHAT_DISABLE_BURST_THROTTLE") == "1" or getattr(settings, "CHAT_DISABLE_BURST_THROTTLE", False):
        return

    limit = int(getattr(settings, "CHAT_BURST_LIMIT", 5))
    if limit <= 0:
        return

    now = timezone.now()
    now_sec = int(now.timestamp())
    key = f"chat:{session_id}:rate:{now_sec}"

    try:
        pipe = _r.pipeline()
        pipe.incr(key, 1)
        pipe.expire(key, 2)  # 1s bucket + small tolerance
        count, _ = pipe.execute()
    except Exception:
        # Redis unavailable -> do not throttle (fail-open for tests/dev)
        return

    if int(count) > limit:
        frac = now.timestamp() - math.floor(now.timestamp())
        wait = max(1.0 - frac, 0.5)
        raise Throttled(wait=wait)


@method_decorator(ensure_csrf_cookie, name="dispatch")
class ChatPageView(TemplateView):
    template_name = "chat/index.html"

    def dispatch(self, request, *args, **kwargs):
        """Require tenant login for chat access"""
        from django.shortcuts import redirect
        from django.urls import reverse

        from landlord.auth import get_tenant_from_session

        # Check if tenant is logged in
        if not get_tenant_from_session(request):
            # Redirect to tenant login page
            return redirect(reverse('tenant_login'))

        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        from landlord.auth import get_tenant_from_session
        context = super().get_context_data(**kwargs)
        context['tenant'] = get_tenant_from_session(self.request)
        return context


class ChatSessionCreateAPIView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes: list = []
    parser_classes = [parsers.FormParser, parsers.JSONParser, parsers.MultiPartParser]

    def get_throttles(self):  # type: ignore[override]
        return []

    def post(self, request):
        # Do not rely on request parsing here to avoid 415 for empty posts
        ser = ChatSessionCreateSerializer(data={})
        ser.is_valid(raise_exception=True)
        session = ser.save()
        # GREETING prompt
        return Response({
            "id": str(session.id),
            "state": "GREETING",
            "next_prompt": "Guten Tag! Bitte beschreiben Sie kurz das Problem.",
            "expires_at": session.expires_at.isoformat() if session.expires_at else None,
        }, status=status.HTTP_201_CREATED)


@csrf_exempt
def chat_session_create_plain(request):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    # Minimal IP throttle: 60/min per IP
    ip = request.META.get("REMOTE_ADDR", "0.0.0.0")
    key = f"chat:create:{ip}:{int(timezone.now().timestamp())//60}"
    count = _r.incr(key, 1)
    if count == 1:
        _r.expire(key, 120)
    rate = int(getattr(settings, "CHAT_CREATE_RATE", 60))
    if int(count) > rate:
        retry = 60 - (int(timezone.now().timestamp()) % 60)
        return JsonResponse({"code": "RATE_LIMITED", "retry_after": retry}, status=429, headers={"Retry-After": str(retry)})
    ser = ChatSessionCreateSerializer(data={})
    ser.is_valid(raise_exception=True)
    session = ser.save()
    return JsonResponse({
        "id": str(session.id),
        "state": "GREETING",
        "next_prompt": "Guten Tag! Bitte beschreiben Sie kurz das Problem.",
        "expires_at": session.expires_at.isoformat() if session.expires_at else None,
    }, status=201)


class ChatMessageView(APIView):
    permission_classes = [permissions.AllowAny]
    parser_classes = [parsers.MultiPartParser, parsers.FormParser, parsers.JSONParser]

    def get_throttles(self):  # type: ignore[override]
        # Set session_id early so ChatRateThrottle can include it in cache key
        try:
            if hasattr(self, 'kwargs') and self.kwargs.get('id'):
                self.session_id = str(self.kwargs['id'])
        except Exception:
            pass
        return super().get_throttles()

    def post(self, request, id: str):
        session = get_object_or_404(ChatSession, id=id)
        if session.expires_at and session.expires_at < timezone.now():
            return Response({"code": "SESSION_EXPIRED"}, status=status.HTTP_410_GONE)

        # Early CAS check: if client sends an old version, respond 409 immediately
        req_ver = None
        try:
            if hasattr(request, "data") and "version" in request.data:
                req_ver = int(request.data.get("version"))
        except Exception:
            req_ver = None
        if req_ver is not None and req_ver != int(session.version):
            return Response({"code": "STATE_VERSION_CONFLICT"}, status=status.HTTP_409_CONFLICT)

        data = request.data.copy()
        # Early STATE_MISMATCH guard before serializer to avoid 400 later in FSM
        if session.state == "CAPTURE_OCCURRED_AT":
            if "occurred_at" not in data and any(k in data for k in ("text", "severity", "location", "contact")):
                return Response({"code": "STATE_MISMATCH", "expected": "CAPTURE_OCCURRED_AT"}, status=status.HTTP_409_CONFLICT)
        if session.state == "CAPTURE_LOCATION":
            if "location" not in data and any(k in data for k in ("text", "severity", "occurred_at", "contact")):
                return Response({"code": "STATE_MISMATCH", "expected": "CAPTURE_LOCATION"}, status=status.HTTP_409_CONFLICT)

        ser = ChatMessageSerializer(data=data, context={"state": session.state})
        if not ser.is_valid():
            return Response({"code": "VALIDATION_ERROR", "detail": ser.errors}, status=status.HTTP_400_BAD_REQUEST)

        version = ser.validated_data["version"]
        files = request.FILES.getlist("files") if hasattr(request, "FILES") else None

        # State mismatch guards: if user posts fields from a different step, respond 409
        st = session.state
        vd = ser.validated_data
        raw_keys = set((data or {}).keys())
        def any_other_fields(keys):
            return any(k in vd for k in keys)
        # If client sent a wrong field for the current step, prefer 409 over 400
        if st == "CAPTURE_OCCURRED_AT" and "occurred_at" not in vd and (any_other_fields(["severity", "location", "contact", "text"]) or ("text" in raw_keys)):
            return Response({"code": "STATE_MISMATCH", "expected": "CAPTURE_OCCURRED_AT"}, status=status.HTTP_409_CONFLICT)
        if st == "CAPTURE_LOCATION" and "location" not in vd and (any_other_fields(["severity", "occurred_at", "contact", "text"]) or ("text" in raw_keys)):
            return Response({"code": "STATE_MISMATCH", "expected": "CAPTURE_LOCATION"}, status=status.HTTP_409_CONFLICT)

        # Apply per-session burst throttle after validation/state checks and before service call
        enforce_burst_throttle(session_id=str(session.id))
        # Ensure 'text' is forwarded if present in request but omitted in validated_data
        msg_payload = dict(ser.validated_data)
        raw_text = (data.get("text") or "").strip()
        if raw_text:
            msg_payload["text"] = raw_text
            # Map text to summary for FSM steps GREETING/CAPTURE_SUMMARY
            if session.state in ("GREETING", "CAPTURE_SUMMARY") and "summary" not in msg_payload:
                msg_payload["summary"] = raw_text
        if "occurred_at" not in msg_payload and data.get("occurred_at"):
            dt = parse_datetime(data.get("occurred_at"))
            if dt is not None:
                msg_payload["occurred_at"] = dt
        try:
            new_state, prompt, delta, warnings, new_version = message_svc(
                session_id=session.id,
                version=version,
                state=session.state,
                message=msg_payload,
                files=files,
            )
        except RuntimeError as e:
            if str(e) == "STATE_VERSION_CONFLICT":
                return Response({"code": "STATE_VERSION_CONFLICT"}, status=status.HTTP_409_CONFLICT)
            return Response({"code": "ERROR"}, status=status.HTTP_400_BAD_REQUEST)
        except ValueError as ve:
            # From FSM
            msg = str(ve)
            if msg.startswith("VALIDATION:"):
                _, field, detail = msg.split(":", 2)
                return Response({"code": "VALIDATION_ERROR", "field": field, "detail": detail}, status=status.HTTP_400_BAD_REQUEST)
            if msg.startswith("PAYLOAD_TOO_LARGE"):
                return Response({"code": "PAYLOAD_TOO_LARGE"}, status=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE)
            if msg.startswith("UNSUPPORTED_MEDIA_TYPE"):
                return Response({"code": "UNSUPPORTED_MEDIA_TYPE"}, status=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE)
            return Response({"code": "STATE_MISMATCH", "expected": session.state}, status=status.HTTP_409_CONFLICT)

        return Response({
            "state": new_state,
            "payload_partial": delta,
            "next_prompt": prompt,
            "version": new_version,
            "warnings": warnings,
        })


class ChatConfirmView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes: list = []

    def get_throttles(self):  # type: ignore[override]
        return []

    def post(self, request, id: str):
        from django.conf import settings

        from landlord.auth import get_tenant_from_session
        from landlord.utils.public_link import make_token

        session = get_object_or_404(ChatSession, id=id)
        if session.expires_at and session.expires_at < timezone.now():
            return Response({"code": "SESSION_EXPIRED"}, status=status.HTTP_410_GONE)

        # Get tenant from session if authenticated
        tenant = get_tenant_from_session(request)

        idem = request.headers.get("Idempotency-Key")
        try:
            issue_id, ticket_no = confirm_svc(
                session_id=session.id,
                idempotency_key=idem,
                tenant=tenant  # ✅ Pass tenant to service
            )
        except RuntimeError as e:
            if str(e) == "ALREADY_CONFIRMED":
                return Response({"code": "ALREADY_CONFIRMED"}, status=status.HTTP_409_CONFLICT)
            return Response({"code": "ERROR"}, status=status.HTTP_400_BAD_REQUEST)

        status_url = f"http://{settings.SITE_DOMAIN}/t/{make_token(ticket_no)}/"
        return Response({"issue_id": issue_id, "ticket_no": ticket_no, "status_url": status_url})


# ============================================================================
# PROPERTY PORTAL VIEWS (Phase 4)
# ============================================================================


class PropertyListView(LoginRequiredMixin, ListView):
    """
    GET /portal/properties/

    List all properties with search, filter, sort, and pagination.
    """
    model = Property
    template_name = 'portal/properties_list.html'
    context_object_name = 'properties'
    paginate_by = 25

    def get_queryset(self):
        """Filter and search properties"""
        qs = Property.objects.all()

        # Filter archived (default: exclude)
        show_archived = self.request.GET.get('show_archived')
        if not show_archived:
            qs = qs.filter(is_archived=False)

        # Search
        query = self.request.GET.get('q')
        if query:
            qs = qs.filter(
                Q(name__icontains=query) |
                Q(city__icontains=query) |
                Q(postal_code__icontains=query)
            )

        # Filter by country
        country = self.request.GET.get('country')
        if country:
            qs = qs.filter(country=country)

        # Annotate meters count
        qs = qs.annotate(meters_count=Count('utility_meters'))

        # Sort with whitelist to prevent FieldError
        ALLOWED_SORT_FIELDS = ['name', 'city', 'created_at', 'postal_code', 'meters_count']
        sort = self.request.GET.get('sort', 'name')
        
        # Validate sort field
        if sort not in ALLOWED_SORT_FIELDS:
            sort = 'name'  # Fallback to default
        
        order = self.request.GET.get('order', 'asc')
        if order == 'desc':
            sort = f'-{sort}'
        qs = qs.order_by(sort)

        return qs


class PropertyDetailView(LoginRequiredMixin, DetailView):
    """
    GET /portal/properties/{id}/

    View property details with meters.
    """
    model = Property
    template_name = 'portal/property_detail.html'
    context_object_name = 'property'

    def get_queryset(self):
        """Prefetch meters to avoid N+1"""
        return Property.objects.prefetch_related('utility_meters')


class PropertyCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    GET/POST /portal/properties/new

    Create a new property.
    """
    model = Property
    template_name = 'portal/property_form.html'
    fields = ['name', 'street', 'postal_code', 'city', 'country', 'geo_lat', 'geo_lng', 'notes']
    permission_required = 'landlord.add_property'

    def get_success_url(self):
        return reverse_lazy('portal_property_detail', kwargs={'pk': self.object.pk})


class PropertyUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    GET/POST /portal/properties/{id}/edit

    Update an existing property.
    """
    model = Property
    template_name = 'portal/property_form.html'
    fields = ['name', 'street', 'postal_code', 'city', 'country', 'geo_lat', 'geo_lng', 'notes']
    permission_required = 'landlord.change_property'

    def get_success_url(self):
        return reverse_lazy('portal_property_detail', kwargs={'pk': self.object.pk})


# ============================================================================
# UTILITY METER PORTAL VIEWS (Phase 5)
# ============================================================================


class MeterCreateView(LoginRequiredMixin, PermissionRequiredMixin, CreateView):
    """
    GET/POST /portal/properties/{property_id}/meters/new

    Create a new utility meter for a property.
    """
    model = UtilityMeter
    template_name = 'portal/meter_form.html'
    fields = ['meter_type', 'serial_number', 'is_default', 'is_active',
              'initial_reading_value', 'installed_at', 'removed_at', 'notes']
    permission_required = 'landlord.add_utilitymeter'

    def dispatch(self, request, *args, **kwargs):
        self.property = get_object_or_404(Property, pk=kwargs['property_id'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['property'] = self.property
        context['meter'] = None
        return context

    def form_valid(self, form):
        form.instance.property = self.property
        return super().form_valid(form)

    def get_success_url(self):
        return reverse_lazy('portal_property_detail', kwargs={'pk': self.property.pk})


class MeterUpdateView(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
    """
    GET/POST /portal/properties/{property_id}/meters/{pk}/edit

    Update an existing utility meter.
    """
    model = UtilityMeter
    template_name = 'portal/meter_form.html'
    fields = ['meter_type', 'serial_number', 'is_default', 'is_active',
              'initial_reading_value', 'installed_at', 'removed_at', 'notes']
    permission_required = 'landlord.change_utilitymeter'

    def dispatch(self, request, *args, **kwargs):
        self.property = get_object_or_404(Property, pk=kwargs['property_id'])
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['property'] = self.property
        return context

    def get_success_url(self):
        return reverse_lazy('portal_property_detail', kwargs={'pk': self.property.pk})
