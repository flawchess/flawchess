"""Web Push send path: VAPID signing + aes128gcm encryption + the outbound POST.

`app.services.push_crypto` does the VAPID JWT signing and RFC 8291
aes128gcm payload encryption in-process; this module owns the actual
`httpx.AsyncClient` POST to the browser-supplied endpoint. No blocking HTTP
client (e.g. `requests`) may ever touch the event loop on this path.

An unset VAPID keypair means push is gracefully disabled everywhere in
this module -- never an exception at import time, never a startup abort.

Only a 404/410 response means "prune this subscription". The prune branch logs
a warning and sends an info-level `capture_message` (never `capture_exception`:
404/410 is the normal end of a subscription's life, so do not restore an
error-level capture). Its context carries `push_host` (the endpoint's HOST
only, via `urlsplit().hostname` -- never the path, which is a bearer
capability and must never reach Sentry or a log record), `user_agent`,
`user_id` and the subscription id; the message is a fixed literal. Every other
non-2xx status and every transport error is logged and
`sentry_sdk.capture_exception`-ed, with no retry and no deletion.

`ttl_seconds` is computed by the caller
(`train_scheduler.seconds_until_end_of_local_day`); this module does no
timezone arithmetic. Do not use a TTL of 0: a discarded TTL-0 message returns
201 exactly like a delivery, so "sent" would mean nothing measurable.

VAPID key rotation: see `docs/push-vapid-rotation-runbook.md` for the full
operator procedure (when to rotate, what breaks, and how devices recover).
"""

from __future__ import annotations

import json
import logging
import time
from dataclasses import dataclass
from urllib.parse import urlsplit

import httpx
import sentry_sdk
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.repositories import push_repository
from app.services import push_crypto

logger = logging.getLogger(__name__)

# RFC 8292: exp MUST NOT exceed 24h. 12h is the conventional value.
_VAPID_EXPIRATION_SECONDS = 12 * 60 * 60

# Status codes meaning "the push service will never accept this endpoint
# again" (RFC 8030 Sec. 7) -- everything else is either a bug in our
# own send path (400/401/403/413) or transient (429/5xx).
_PRUNE_STATUS_CODES = frozenset({404, 410})

# Bounded so one slow/unreachable push service can never stall a fan-out.
_PUSH_TIMEOUT_SECONDS = 10.0

# RFC 8030 Sec. 5.2 TTL. This default exists ONLY so a caller that omits
# `ttl_seconds` cannot silently send a TTL of 0 -- a TTL of
# 0 tells the push service to deliver only if the device is reachable right
# now, and a discarded message returns 201 just like a real delivery,
# indistinguishable server-side. The one production caller
# (`train_reminder_service._process_candidate`) always passes a computed
# value (`train_scheduler.seconds_until_end_of_local_day`); in practice only
# the dev-only trigger endpoint (`POST /api/push/dev/trigger-reminder`,
# gated on `ENVIRONMENT == "development"`) ever uses this default. MUST
# NEVER be 0.
_DEFAULT_PUSH_TTL_SECONDS = 3600


@dataclass(frozen=True)
class PushFanoutResult:
    """The outcome of fanning one payload out to a user's live subscriptions."""

    attempted: int
    pruned: int
    failed: int


def is_push_configured() -> bool:
    """True only when both VAPID key settings are non-empty."""
    return bool(settings.VAPID_PUBLIC_KEY) and bool(settings.VAPID_PRIVATE_KEY)


def application_server_key() -> str | None:
    """Return the base64url application server key `PushManager.subscribe()` needs.

    Derived from `VAPID_PUBLIC_KEY` at call time rather than stored as a
    fourth env var -- a PEM and a hand-pasted base64url value that drift
    apart would silently 403 every send. Returns None when push is
    unconfigured.
    """
    if not settings.VAPID_PUBLIC_KEY:
        return None
    return push_crypto.application_server_key_from_pem(settings.VAPID_PUBLIC_KEY.encode())


def _push_host(endpoint: str) -> str | None:
    """The endpoint's host only -- safe to report to Sentry
    because the bearer capability is the endpoint PATH, not the host."""
    return urlsplit(endpoint).hostname


def push_http_client() -> httpx.AsyncClient:
    """Build the outbound client for push sends.

    `follow_redirects=False` is an SSRF mitigation (ASVS V4): the
    endpoint is client-supplied, so an outbound redirect must never be
    chased to a different host.
    """
    return httpx.AsyncClient(timeout=_PUSH_TIMEOUT_SECONDS, follow_redirects=False)


async def send_to_subscription(
    client: httpx.AsyncClient,
    *,
    endpoint: str,
    p256dh: str,
    auth: str,
    payload: dict[str, object],
    subscription_id: int | None = None,
    user_agent: str | None = None,
    user_id: int | None = None,
    ttl_seconds: int = _DEFAULT_PUSH_TTL_SECONDS,
) -> bool:
    """Send one push message. Returns True if the subscription should be pruned.

    Only 404/410 return True (prune). Every other non-2xx is logged +
    reported to Sentry and left alone -- no retry, no deletion.

    Args:
        subscription_id: The row's PK, threaded in so the prune capture's
            `set_context` can identify which row was deleted without ever
            carrying the endpoint. Keyword-only and defaulted to None so
            direct callers need not pass it. It must be in hand when the
            prune capture fires (setting it at the `send_to_user` call site
            would attach to a later event), which is why it is threaded in
            rather than set outside.
        user_agent: The device's stored User-Agent, threaded in so the prune
            capture's `set_context` can identify WHICH device died
            -- `send_to_user` deletes the row moments later, taking
            `user_agent` with it. Likewise keyword-only and defaulted to None.
        user_id: The subscription's owning user's internal PK, threaded in
            for the same diagnosability reason as `user_agent`.
            Keyword-only and defaulted to None.
        ttl_seconds: RFC 8030 Sec. 5.2 `Ttl` header value, in seconds.
            Likewise keyword-only and defaulted. The
            CALLER computes this value; this module never derives it. Only
            `train_reminder_service._process_candidate` passes a real
            value (via `train_scheduler.seconds_until_end_of_local_day`);
            every other caller gets the module default.
    """
    if not is_push_configured():
        return False  # VAPID unconfigured, no-op
    encrypted = push_crypto.encrypt_aes128gcm(
        payload=json.dumps(payload).encode(), p256dh=p256dh, auth=auth
    )
    headers = {
        "ttl": str(ttl_seconds),
        "content-encoding": "aes128gcm",
        "authorization": push_crypto.vapid_authorization(
            endpoint=endpoint,
            subject=settings.VAPID_SUBJECT,
            private_key_pem=settings.VAPID_PRIVATE_KEY.encode(),
            public_key_pem=settings.VAPID_PUBLIC_KEY.encode(),
            expiration_seconds=_VAPID_EXPIRATION_SECONDS,
            now=int(time.time()),
        ),
    }
    try:
        resp = await client.post(endpoint, content=encrypted, headers=headers)
    except httpx.HTTPError:
        logger.exception("Push send transport error")
        sentry_sdk.set_tag("source", "push_send")
        sentry_sdk.capture_exception()
        return False

    if resp.status_code in _PRUNE_STATUS_CODES:
        # This branch permanently deletes a push_subscriptions row (via
        # send_to_user below), so it must never be silent: the `logger.warning`
        # line below makes the deletion visible.
        #
        # A 404/410 is normal device lifecycle (PWA removed, browser
        # reinstall, token rotation), not an error, so this is graded
        # `level="info"` via `capture_message` -- never `capture_exception`.
        # The fixed literal string keeps the existing Sentry issue's grouping. The context carries
        # `push_host` (HOST ONLY, via `_push_host()` -- never the endpoint
        # PATH, which remains the bearer capability and must never reach
        # Sentry or a log record) plus `user_agent`/`user_id`, read here
        # while the row is still in hand, so a future prune is diagnosable.
        logger.warning("Push subscription pruned after status %d", resp.status_code)
        sentry_sdk.set_tag("source", "push_send")
        sentry_sdk.set_context(
            "push_send",
            {
                "status_code": resp.status_code,
                "subscription_id": subscription_id,
                "push_host": _push_host(endpoint),
                "user_agent": user_agent,
                "user_id": user_id,
            },
        )
        sentry_sdk.capture_message("Push send returned a prune status", level="info")
        return True
    # Anything outside 2xx is a non-delivery. The bound is 300, not 400: we send
    # with follow_redirects=False (an SSRF mitigation on a client-supplied
    # endpoint), so a 3xx arrives here as an unfollowed redirect and the message
    # was NOT delivered. A >= 400 bound let 3xx fall through and return False,
    # making a silent non-delivery indistinguishable from a real 201.
    if resp.status_code >= 300:  # 3xx unfollowed redirect + 400/401/403/413/429/5xx
        logger.warning("Push send failed with status %d", resp.status_code)
        sentry_sdk.set_tag("source", "push_send")
        sentry_sdk.set_context("push_send", {"status_code": resp.status_code})
        sentry_sdk.capture_exception(RuntimeError("Push send returned a non-success status"))
    return False


async def send_to_user(
    session: AsyncSession,
    *,
    user_id: int,
    payload: dict[str, object],
    ttl_seconds: int = _DEFAULT_PUSH_TTL_SECONDS,
) -> PushFanoutResult:
    """Fan `payload` out to every one of `user_id`'s live subscriptions.

    Opens ONE `push_http_client()` for the whole fan-out (connection pooling
    across a user's devices). Iterates subscriptions sequentially -- never
    `asyncio.gather` on one `AsyncSession` (CLAUDE.md) -- and isolates each
    subscription's failure in its own try/except so one bad device never
    starves the rest of the fan-out. Commits once at the end.

    Args:
        session: AsyncSession. Commits internally (prune deletes + this
            function's own transaction boundary).
        user_id: Authenticated user's internal PK (V4: never client-supplied).
        payload: The notification payload (see
            `app.services.train_reminder_service.build_reminder_payload`).
        ttl_seconds: RFC 8030 Sec. 5.2 `Ttl` header value, threaded straight
            into every `send_to_subscription` call in the fan-out below.
            Keyword-only and defaulted, same contract as
            `send_to_subscription`'s own `ttl_seconds`. This module NEVER
            computes it -- the value is derived by the CALLER, which already
            holds the user's timezone and the current instant; `push_send`
            must never import `train_scheduler` or do timezone arithmetic.
    """
    if not is_push_configured():
        return PushFanoutResult(attempted=0, pruned=0, failed=0)

    subscriptions = await push_repository.list_subscriptions(session, user_id=user_id)
    attempted = 0
    pruned = 0
    failed = 0
    async with push_http_client() as client:
        for subscription in subscriptions:
            attempted += 1
            try:
                should_prune = await send_to_subscription(
                    client,
                    endpoint=subscription.endpoint,
                    p256dh=subscription.p256dh,
                    auth=subscription.auth,
                    payload=payload,
                    subscription_id=subscription.id,
                    user_agent=subscription.user_agent,
                    user_id=user_id,
                    ttl_seconds=ttl_seconds,
                )
            except Exception:
                # Per-subscription isolation: a construction/encryption error
                # on one device must never stop the rest of the fan-out.
                logger.exception("Push send raised unexpectedly")
                sentry_sdk.set_tag("source", "push_send")
                sentry_sdk.capture_exception()
                failed += 1
                continue
            if should_prune:
                await push_repository.delete_subscription_by_id(
                    session, subscription_id=subscription.id
                )
                pruned += 1
            # else: either delivered, or a non-prune failure already logged
            # + captured inside send_to_subscription (leave it alone).
    await session.commit()
    return PushFanoutResult(attempted=attempted, pruned=pruned, failed=failed)


__all__ = [
    "PushFanoutResult",
    "is_push_configured",
    "application_server_key",
    "push_http_client",
    "send_to_subscription",
    "send_to_user",
]
