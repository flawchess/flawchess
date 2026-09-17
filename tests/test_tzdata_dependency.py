"""Regression test for the `tzdata` runtime dependency (Sentry FLAWCHESS-9W).

`PUT /train/settings` with `timezone: "Europe/Kiev"` returned 422
(`Unrecognized IANA timezone: 'Europe/Kiev'`) for real production users. The cause: the
pinned `python:3.14-slim` runtime base image (`Dockerfile` line 1) ships a TRIMMED system
tzdata with no `backward` compatibility links, and the `tzdata` PyPI package — which
`zoneinfo` falls back to once system TZPATH misses — was not a project dependency. Every
already-stored legacy alias (`Europe/Kiev`, `Asia/Calcutta`, etc.) also silently degraded
to the scheduler's UTC fallback in `app/services/train_scheduler.py`, with no error
anywhere.

A bare `TrainSettingsUpdate(timezone="Europe/Kiev", ...)` assertion would be a NO-OP on
this dev machine: the full system tzdata here already resolves every legacy alias, bug or
no bug, so such a test can never go RED before the fix. Every test in this module instead
runs under the `package_only_tzpath` fixture, which empties `zoneinfo`'s TZPATH via
`zoneinfo.reset_tzpath([])` (plus a cache clear) so the `tzdata` PyPI package is the ONLY
possible source of a resolved zone — reproducing the trimmed-base-image condition on any
machine, regardless of what system tzdata it happens to have.

Harness caveat: with TZPATH emptied AND the `tzdata` package absent, even `ZoneInfo("UTC")`
is unavailable, so the scheduler's `except ZoneInfoNotFoundError, ValueError:` fallback
itself raises instead of returning a UTC-fallback date. In production the same
missing-package condition instead degrades SILENTLY (system tzdata there has `UTC`, just
not the `backward` aliases). The tests below therefore never assert on an exception type —
they assert on the correct, alias-resolved value, which is only reachable once `tzdata` is
actually installed and importable, on this harness or in prod alike.
"""

from __future__ import annotations

import datetime
import importlib.metadata
import zoneinfo
from collections.abc import Iterator
from typing import TypedDict
from zoneinfo import ZoneInfo

import pytest

from app.schemas.train import TrainSettingsUpdate
from app.services.train_scheduler import (
    DEFAULT_PUZZLES_PER_SESSION,
    DEFAULT_REMINDER_ENABLED,
    DEFAULT_REMINDER_HOUR,
    DEFAULT_WEEKDAY_MASK,
    local_today,
)

# Legacy IANA aliases that only resolve via the `backward` compatibility links —
# present in the full `tzdata` PyPI package, absent from the trimmed system tzdata
# shipped by the pinned `python:3.14-slim` base image.
LEGACY_ALIASES: tuple[str, ...] = (
    "Europe/Kiev",
    "Asia/Calcutta",
    "US/Pacific",
    "America/Buenos_Aires",
    "Asia/Saigon",
)

# Canonical zones that must keep resolving alongside the legacy aliases above —
# controls proving the package-only fixture did not simply break zone resolution
# outright.
CANONICAL_ZONES: tuple[str, ...] = ("Europe/Kyiv", "UTC")

# The exact Sentry FLAWCHESS-9W payload shape's timezone value.
_SENTRY_ALIAS = "Europe/Kiev"

# 2026-09-17 22:30 UTC is 2026-09-18 01:30 EEST (Kyiv is UTC+3 in September, still on
# summer time) -- verified arithmetic, see plan `<decisions>`.
PROBE_UTC = datetime.datetime(2026, 9, 17, 22, 30, tzinfo=datetime.timezone.utc)
EXPECTED_KYIV_DATE = datetime.date(2026, 9, 18)


class _SettingsPayload(TypedDict):
    timezone: str
    weekday_mask: int
    puzzles_per_session: int
    reminder_enabled: bool
    reminder_hour: int
    reminder_intent_at: datetime.datetime | None


def _settings_payload(timezone: str) -> _SettingsPayload:
    """Build a `TrainSettingsUpdate` payload where only `timezone` varies."""
    return {
        "timezone": timezone,
        "weekday_mask": DEFAULT_WEEKDAY_MASK,
        "puzzles_per_session": DEFAULT_PUZZLES_PER_SESSION,
        "reminder_enabled": DEFAULT_REMINDER_ENABLED,
        "reminder_hour": DEFAULT_REMINDER_HOUR,
        "reminder_intent_at": None,
    }


@pytest.fixture
def package_only_tzpath() -> Iterator[None]:
    """Make the `tzdata` PyPI package the only possible zone-data source.

    The cache clear on entry is load-bearing: `ZoneInfo` memoizes per key, so a zone
    another test already resolved from system tzdata would be handed back from cache
    and every assertion below would pass spuriously, proving nothing.
    """
    zoneinfo.reset_tzpath([])
    ZoneInfo.clear_cache()
    try:
        yield
    finally:
        zoneinfo.reset_tzpath()
        ZoneInfo.clear_cache()


def test_tzdata_distribution_is_installed() -> None:
    version = importlib.metadata.version("tzdata")
    assert version


@pytest.mark.parametrize("zone_name", [*LEGACY_ALIASES, *CANONICAL_ZONES])
def test_legacy_aliases_resolve_from_package_only(
    package_only_tzpath: None, zone_name: str
) -> None:
    ZoneInfo(zone_name)  # must not raise ZoneInfoNotFoundError


def test_train_settings_update_accepts_legacy_alias(package_only_tzpath: None) -> None:
    settings = TrainSettingsUpdate(**_settings_payload(_SENTRY_ALIAS))
    assert settings.timezone == _SENTRY_ALIAS


def test_local_today_resolves_alias_instead_of_falling_back(
    package_only_tzpath: None,
) -> None:
    resolved_date = local_today(_SENTRY_ALIAS, PROBE_UTC)
    assert resolved_date == EXPECTED_KYIV_DATE
    assert resolved_date != PROBE_UTC.date()
