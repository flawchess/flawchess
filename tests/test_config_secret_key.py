"""Tests for the SECRET_KEY fail-closed startup guard (code-review 2026-07-02, #1.2).

assert_secret_key_configured() must abort a non-development boot when the default
placeholder SECRET_KEY is still in use, but leave development (and any environment with
a real key) untouched.
"""

import pytest

from app.core.config import DEFAULT_SECRET_KEY, assert_secret_key_configured, settings

_STRONG_KEY = "a-strong-random-32-byte-secret-value-for-tests"


def test_raises_in_production_with_default_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "SECRET_KEY", DEFAULT_SECRET_KEY)
    with pytest.raises(RuntimeError, match="SECRET_KEY is still the insecure default"):
        assert_secret_key_configured()


def test_raises_in_any_non_development_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    # Any value other than "development" must fail closed (e.g. staging).
    monkeypatch.setattr(settings, "ENVIRONMENT", "staging")
    monkeypatch.setattr(settings, "SECRET_KEY", DEFAULT_SECRET_KEY)
    with pytest.raises(RuntimeError):
        assert_secret_key_configured()


def test_ok_in_development_with_default_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ENVIRONMENT", "development")
    monkeypatch.setattr(settings, "SECRET_KEY", DEFAULT_SECRET_KEY)
    assert_secret_key_configured()  # must not raise


def test_ok_in_production_with_custom_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    monkeypatch.setattr(settings, "SECRET_KEY", _STRONG_KEY)
    assert_secret_key_configured()  # must not raise
