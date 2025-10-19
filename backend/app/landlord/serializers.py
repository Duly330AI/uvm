from __future__ import annotations

import re

from django.utils import timezone
from rest_framework import serializers

from .models import ChatSession, Issue, IssueAttachment, IssueNote, Unit


class ChatSessionCreateSerializer(serializers.Serializer):
    unit_id = serializers.IntegerField(required=False)
    tenant_token = serializers.CharField(required=False, allow_blank=True)

    def create(self, validated_data: dict) -> ChatSession:
        unit = None
        if uid := validated_data.get("unit_id"):
            unit = Unit.objects.filter(id=uid).first()
        # Ensure a unit exists for downstream Issue creation when DB requires it
        if unit is None:
            unit = Unit.objects.select_related("property").first()
            if unit is None:
                from .models import Property
                from .models import Unit as UnitModel
                prop = Property.objects.create(name="Demo Objekt", street="Demo Straße 1", postal_code="00000", city="Demo")
                unit = UnitModel.objects.create(property=prop, unit_label="A")
        expires_at = timezone.now() + timezone.timedelta(minutes=60)
        return ChatSession.objects.create(unit=unit, expires_at=expires_at)


class ChatMessageSerializer(serializers.Serializer):
    version = serializers.IntegerField(required=True)
    text = serializers.CharField(required=False, allow_blank=True)
    occurred_at = serializers.DateTimeField(required=False)
    location = serializers.CharField(required=False, allow_blank=True)
    severity = serializers.IntegerField(required=False)
    contact = serializers.CharField(required=False, allow_blank=True)
    files = serializers.ListField(child=serializers.FileField(), required=False)

    def validate(self, attrs: dict) -> dict:
        state = self.context.get("state")
        # Cross-field checks are in FSM; basic shape is enough here
        if state == "CAPTURE_OCCURRED_AT" and "occurred_at" in attrs:
            now = timezone.now() + timezone.timedelta(minutes=5)
            if attrs["occurred_at"] > now:
                raise serializers.ValidationError({
                    "occurred_at": {"code": "VALIDATION_ERROR", "detail": "must be in the past"}
                })
        if state == "CAPTURE_LOCATION" and "location" in attrs:
            if len(attrs["location"]) > 120:
                raise serializers.ValidationError({
                    "location": {"code": "VALIDATION_ERROR", "detail": "max 120 chars"}
                })
        if state == "CAPTURE_SEVERITY" and "severity" in attrs:
            if not (1 <= int(attrs["severity"]) <= 5):
                raise serializers.ValidationError({
                    "severity": {"code": "VALIDATION_ERROR", "detail": "range 1..5"}
                })
        if state == "CAPTURE_CONTACT" and "contact" in attrs and attrs["contact"]:
            contact = attrs["contact"]
            phone_re = re.compile(r"^\+?[0-9\s\-()/]{6,20}$")
            email_re = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
            if not (phone_re.match(contact) or email_re.match(contact)):
                raise serializers.ValidationError({
                    "contact": {"code": "VALIDATION_ERROR", "detail": "invalid phone/email"}
                })
        return attrs


class ChatConfirmSerializer(serializers.Serializer):
    idempotency_key = serializers.UUIDField(required=False)


# ===== Admin API serializers =====

class IssueListSerializer(serializers.ModelSerializer):
    tenant_email = serializers.SerializerMethodField()
    property_id = serializers.IntegerField(source="unit.property_id", read_only=True)

    class Meta:
        model = Issue
        fields = [
            "id",
            "ticket_no",
            "status",
            "category",
            "severity",
            "created_at",
            "unit_id",
            "property_id",
            "tenant_email",
            "summary",
        ]

    def get_tenant_email(self, obj):
        email = getattr(getattr(obj.tenant, "user", None), "email", None) or getattr(obj.tenant, "primary_email", None)
        return email or ""


class IssueNoteSerializer(serializers.ModelSerializer):
    created_by = serializers.SerializerMethodField()

    class Meta:
        model = IssueNote
        fields = ["id", "text", "created_at", "created_by", "visibility"]

    def get_created_by(self, obj):
        u = getattr(obj, "author", None)
        return getattr(u, "email", None) or getattr(u, "username", None) if u else None


class IssueNoteCreateSerializer(serializers.ModelSerializer):
    # accept is_internal boolean and map to visibility
    is_internal = serializers.BooleanField(required=False, default=True)

    class Meta:
        model = IssueNote
        fields = ["text", "is_internal"]

    def create(self, validated_data):
        is_internal = validated_data.pop("is_internal", True)
        visibility = IssueNote.Visibility.INTERNAL if is_internal else IssueNote.Visibility.PUBLIC
        return IssueNote.objects.create(visibility=visibility, **validated_data)


class IssueAttachmentSerializer(serializers.ModelSerializer):
    class Meta:
        model = IssueAttachment
        fields = ["id", "file", "mime", "size_bytes", "created_at"]
        read_only_fields = ["id", "created_at", "mime", "size_bytes"]
