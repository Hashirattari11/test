"""Offline tests for the legal consent gate (master pass §2).

Pure-logic coverage: version constants + consent_required computation. Endpoint
tests require the live Supabase DB (like other suites) so the offline portion
targets the router's pure helpers, plus schema validation via FastAPI's
pydantic models (no network).
"""
from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.routers.consent import CURRENT_PRIVACY_VERSION, CURRENT_TERMS_VERSION, _user_out
from app.schemas import ConsentIn, UserOut


class TestConsentConstants:
    def test_versions_are_set(self):
        assert CURRENT_PRIVACY_VERSION
        assert CURRENT_TERMS_VERSION
        assert CURRENT_PRIVACY_VERSION == CURRENT_TERMS_VERSION

    def test_versions_match_legal_pages(self):
        # Legal pages (frontend /privacy, /terms) state "effective 2026-09-10" —
        # keep in sync when legal docs change.
        assert CURRENT_PRIVACY_VERSION == "2026-09-10"
        assert CURRENT_TERMS_VERSION == "2026-09-10"


class TestConsentInSchema:
    def test_valid_body(self):
        c = ConsentIn(privacy_policy_version="2026-09-10", terms_version="2026-09-10")
        assert c.privacy_policy_version == "2026-09-10"
        assert c.terms_version == "2026-09-10"

    def test_missing_versions_rejected(self):
        with pytest.raises(ValidationError):
            ConsentIn()  # type: ignore[call-arg]
        with pytest.raises(ValidationError):
            ConsentIn(privacy_policy_version="2026-09-10")

    def test_empty_versions_rejected(self):
        with pytest.raises(ValidationError):
            ConsentIn(privacy_policy_version="", terms_version="2026-09-10")


class TestUserOutConsentFields:
    def test_consent_required_when_no_acceptance(self):
        out = _user_out(
            {
                "id": "u1",
                "email": "a@b.com",
                "github_login": "gh",
            }
        )
        assert isinstance(out, UserOut)
        assert out.consent_required is True
        assert out.legal_consent_accepted_at is None

    def test_consent_not_required_after_acceptance(self):
        out = _user_out(
            {
                "id": "u1",
                "email": "a@b.com",
                "github_login": "gh",
                "privacy_policy_version": "2026-09-10",
                "terms_version": "2026-09-10",
                "legal_consent_version": "2026-09-10;2026-09-10",
            }
        )
        assert out.consent_required is False
        assert out.privacy_policy_version == "2026-09-10"
        assert out.terms_version == "2026-09-10"

    def test_user_out_preserves_existing_fields(self):
        out = _user_out(
            {
                "id": "u1",
                "email": "a@b.com",
                "github_login": "gh",
                "plan": "growth",
                "is_admin": True,
                "is_agency": True,
                "notify_daily_status": True,
            }
        )
        assert out.plan == "growth"
        assert out.is_admin is True
        assert out.is_agency is True
        assert out.notify_daily_status is True