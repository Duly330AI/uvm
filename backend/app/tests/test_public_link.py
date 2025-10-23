"""
Tests for public link token utilities
Coverage Target: 100% (from 71%)
"""
from __future__ import annotations

import pytest
from django.core.signing import BadSignature
from landlord.utils.public_link import make_token, parse_token


class TestPublicLinkTokens:
    """Test public link token generation and parsing."""

    def test_make_token_returns_string(self):
        """make_token returns a non-empty string."""
        token = make_token("TCK-2025-00001")

        assert isinstance(token, str)
        assert len(token) > 0

    def test_parse_token_returns_original_ticket(self):
        """parse_token returns the original ticket number."""
        ticket_no = "TCK-2025-00001"
        token = make_token(ticket_no)

        parsed = parse_token(token)

        assert parsed == ticket_no

    def test_tokens_are_unique_per_ticket(self):
        """Different tickets produce different tokens."""
        token1 = make_token("TCK-2025-00001")
        token2 = make_token("TCK-2025-00002")

        assert token1 != token2

    def test_same_ticket_produces_same_token(self):
        """Same ticket produces same token (deterministic)."""
        ticket_no = "TCK-2025-00001"

        token1 = make_token(ticket_no)
        token2 = make_token(ticket_no)

        assert token1 == token2

    def test_parse_invalid_token_raises(self):
        """Parsing invalid token raises BadSignature."""
        with pytest.raises(BadSignature):
            parse_token("invalid_token_12345")

    def test_parse_tampered_token_raises(self):
        """Parsing tampered token raises BadSignature."""
        token = make_token("TCK-2025-00001")
        # Tamper with token
        tampered = token[:-5] + "XXXXX"

        with pytest.raises(BadSignature):
            parse_token(tampered)

    def test_round_trip_with_special_characters(self):
        """Round-trip works with special characters in ticket number."""
        ticket_no = "TCK-2025-00001-ÄÖÜ"
        token = make_token(ticket_no)
        parsed = parse_token(token)

        assert parsed == ticket_no

    def test_empty_ticket_number(self):
        """Empty ticket number can be tokenized."""
        token = make_token("")
        parsed = parse_token(token)

        assert parsed == ""
