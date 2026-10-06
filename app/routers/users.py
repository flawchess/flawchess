"""Users router: profile GET/PUT endpoints and user account stats.

HTTP layer only — all DB access via user_repository and game_repository.
"""

import datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi_users.jwt import decode_jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_async_session
from app.core.dev_clock import dev_now_utc
from app.models.user import User
from app.repositories import (
    game_repository,
    import_job_repository,
    user_import_settings_repository,
    user_rating_anchors_repository,
    user_repository,
)
from app.repositories.user_import_settings_repository import _import_scope_expanded
from app.schemas.admin import ImpersonationContext
from app.schemas.feedback_ask import FeedbackAskActionRequest, FeedbackAskView
from app.schemas.users import (
    FirstTouchRequest,
    GameCountResponse,
    ImportSettingsResponse,
    ImportSettingsUpdate,
    UserProfileResponse,
    UserProfileUpdate,
)
from app.services import feedback_ask_service
from app.services.current_strength_service import resolve_current_strength_for_user
from app.users import current_active_user

router = APIRouter(prefix="/users", tags=["users"])

# POST /me/first-touch only attributes accounts created this recently. The client
# submits right after guest start / register / Google sign-in, so seconds is the
# norm; the margin covers a slow OAuth round-trip or a flaky first request.
FIRST_TOUCH_MAX_ACCOUNT_AGE = datetime.timedelta(hours=1)

# Matches the audience baked into JWTStrategy (FastAPI-Users default).
_JWT_AUDIENCE = ["fastapi-users:auth"]


async def _get_impersonation_context(
    request: Request,
    session: Annotated[AsyncSession, Depends(get_async_session)],
) -> ImpersonationContext | None:
    """Re-decode the Authorization-header JWT and return impersonation context, or None.

    D-22 Option A (RESEARCH.md §"Detecting 'am I impersonating?'"): simpler
    than threading state through the auth strategy, and the decode cost is
    negligible compared to the DB round-trips already in /me/profile.
    """
    auth_header = request.headers.get("authorization", "")
    if not auth_header.lower().startswith("bearer "):
        return None
    token = auth_header[7:]
    try:
        payload = decode_jwt(token, settings.SECRET_KEY, _JWT_AUDIENCE)
    except Exception:
        return None
    if not payload.get("is_impersonation"):
        return None
    admin_id = payload.get("admin_id")
    act_as = payload.get("act_as")
    if admin_id is None or act_as is None:
        return None
    target = await session.get(User, int(act_as))
    if target is None:
        return None
    return ImpersonationContext(admin_id=int(admin_id), target_email=target.email)


async def _build_profile_response(
    session: AsyncSession,
    *,
    user: User,
    profile_row: User,
    now_utc: datetime.datetime,
    impersonation: ImpersonationContext | None,
) -> UserProfileResponse:
    """Build the profile response shared by GET and PUT /me/profile.

    One builder so the two routes can never drift (234-RESEARCH Pitfall 2: the
    leaderboard toggle writes the PUT response straight into the frontend profile
    cache, so a PUT missing a field would drop it there).
    """
    counts = await game_repository.count_games_by_platform(session, user.id)
    last_syncs = await import_job_repository.get_last_completed_at_by_platform(session, user.id)
    anchors = await user_rating_anchors_repository.fetch_anchors_for_user(session, user_id=user.id)
    current_strength = await resolve_current_strength_for_user(
        session, user_id=user.id, now_utc=now_utc, anchors=anchors
    )
    ask = await feedback_ask_service.build_feedback_ask_snapshot(
        session, user, now_utc=now_utc, impersonated=impersonation is not None
    )
    return UserProfileResponse(
        email=user.email,
        is_superuser=user.is_superuser,
        is_guest=user.is_guest,
        chess_com_username=profile_row.chess_com_username,
        lichess_username=profile_row.lichess_username,
        created_at=profile_row.created_at,
        last_login=profile_row.last_login,
        chess_com_game_count=counts.get("chess.com", 0),
        lichess_game_count=counts.get("lichess", 0),
        chess_com_last_sync_at=last_syncs.get("chess.com"),
        lichess_last_sync_at=last_syncs.get("lichess"),
        impersonation=impersonation,
        beta_enabled=profile_row.beta_enabled,
        leaderboard_hidden=profile_row.leaderboard_hidden,
        current_strength=current_strength,
        active_days=ask.active_days,
        feedback_ask=ask.view,
    )


@router.get("/me/profile", response_model=UserProfileResponse)
async def get_profile(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    impersonation: Annotated[ImpersonationContext | None, Depends(_get_impersonation_context)],
    now_utc: Annotated[datetime.datetime, Depends(dev_now_utc)],
) -> UserProfileResponse:
    """Return the authenticated user's platform usernames and game counts.

    When the request carries an impersonation JWT, `impersonation` is populated
    with the admin_id and target_email so the frontend can render the pill (D-22).
    For regular + guest tokens, `impersonation` is null.
    """
    profile = await user_repository.get_profile(session, user.id)
    return await _build_profile_response(
        session, user=user, profile_row=profile, now_utc=now_utc, impersonation=impersonation
    )


@router.put("/me/profile", response_model=UserProfileResponse)
async def update_profile(
    body: UserProfileUpdate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    # Phase 234: PUT now carries the impersonation context like GET (it used to be
    # null, which also dropped the impersonation pill from the cached profile).
    impersonation: Annotated[ImpersonationContext | None, Depends(_get_impersonation_context)],
    now_utc: Annotated[datetime.datetime, Depends(dev_now_utc)],
) -> UserProfileResponse:
    """Update the authenticated user's platform usernames and leaderboard_hidden flag.

    Omitted (None) fields are left unchanged; `leaderboard_hidden` false un-hides
    the user from the weekly Train leaderboards (Phase 230 D-16).
    """
    updated = await user_repository.update_profile(session, user.id, body.model_dump())
    return await _build_profile_response(
        session, user=user, profile_row=updated, now_utc=now_utc, impersonation=impersonation
    )


@router.get("/me/import-settings", response_model=ImportSettingsResponse)
async def get_import_settings(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
) -> ImportSettingsResponse:
    """Return the authenticated user's import settings (create-on-first-touch, D-16).

    A user with no settings row yet gets the app-layer defaults (bullet=false,
    blitz/rapid/classical=true, game_cap=1000) persisted and returned in one
    call -- same code path for guests and registered users.
    """
    settings_row = await user_import_settings_repository.get_or_create_settings(
        session, user_id=user.id
    )
    imported_counts = await game_repository.count_imported_by_platform_and_tc(session, user.id)
    return ImportSettingsResponse(
        tc_bullet=settings_row.tc_bullet,
        tc_blitz=settings_row.tc_blitz,
        tc_rapid=settings_row.tc_rapid,
        tc_classical=settings_row.tc_classical,
        game_cap=settings_row.game_cap,
        imported_counts=imported_counts,
    )


@router.patch("/me/import-settings", response_model=ImportSettingsResponse)
async def update_import_settings(
    body: ImportSettingsUpdate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
) -> ImportSettingsResponse:
    """Persist the authenticated user's import settings (D-09 auto-save on toggle).

    Never accepts a user id from the body or path -- always scoped to
    `current_active_user.id` (T-186-01 mitigation).
    """
    previous = await user_import_settings_repository.get_settings(session, user_id=user.id)
    settings_row = await user_import_settings_repository.upsert_settings(
        session, user_id=user.id, **body.model_dump()
    )
    # Bug fix (UAT 186): the backfill cursor is per-platform, not per-(platform,
    # TC), so months/chunks already attempted under the OLD scope silently
    # skipped games that only the NEW scope wants (a newly enabled TC's games in
    # already-walked months, or over-cap games dropped by the backward pass's
    # budget gate). Reset the cursors whenever the scope EXPANDS (a TC turned
    # on, or the cap raised) so the next Sync re-walks from the top; re-fetching
    # is budget-safe because already-imported games are deduped (CR-01) and
    # no-op'd on insert. Narrowing (TC off, cap lowered) keeps the cursors --
    # nothing previously skipped becomes wanted.
    if previous is not None and _import_scope_expanded(previous, settings_row):
        await user_import_settings_repository.reset_backfill_cursors(session, user_id=user.id)
    imported_counts = await game_repository.count_imported_by_platform_and_tc(session, user.id)
    return ImportSettingsResponse(
        tc_bullet=settings_row.tc_bullet,
        tc_blitz=settings_row.tc_blitz,
        tc_rapid=settings_row.tc_rapid,
        tc_classical=settings_row.tc_classical,
        game_cap=settings_row.game_cap,
        imported_counts=imported_counts,
    )


@router.post("/me/first-touch", status_code=204)
async def record_first_touch(
    body: FirstTouchRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    now_utc: Annotated[datetime.datetime, Depends(dev_now_utc)],
) -> None:
    """Record where this new account's browser first arrived from (growth item 16).

    Always 204: a repeat call, or a call for an account older than
    FIRST_TOUCH_MAX_ACCOUNT_AGE, is a silent no-op so the client can fire once
    after any sign-in without knowing whether the account is new.
    """
    await user_repository.record_first_touch(
        session,
        user.id,
        # exclude_none keeps the stored object to the keys that carry a value.
        first_touch=body.model_dump(exclude_none=True),
        created_after=now_utc - FIRST_TOUCH_MAX_ACCOUNT_AGE,
    )


@router.post("/me/feedback-ask", response_model=FeedbackAskView)
async def feedback_ask_action(
    body: FeedbackAskActionRequest,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
    impersonation: Annotated[ImpersonationContext | None, Depends(_get_impersonation_context)],
    now_utc: Annotated[datetime.datetime, Depends(dev_now_utc)],
) -> FeedbackAskView:
    """Report a view, snooze or done for the milestone feedback ask (SEED-191).

    The user id comes only from current_active_user (V4). Always 200 and idempotent:
    an ineligible, guest, impersonated or stale-tab call is a no-op that returns the
    current view, so no 4xx reaches Sentry from a stale tab.
    """
    return await feedback_ask_service.apply_feedback_ask_action(
        session, user, body.action, now_utc=now_utc, impersonated=impersonation is not None
    )


@router.get("/games/count", response_model=GameCountResponse)
async def get_game_count(
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
) -> GameCountResponse:
    """Return the total number of games imported by the current user."""
    count = await game_repository.count_games_for_user(session, user.id)
    return GameCountResponse(count=count)


@router.post("/sentry-test-error", status_code=500)
async def sentry_test_error(
    user: Annotated[User, Depends(current_active_user)],
) -> None:
    """Superuser-only: raise an unhandled error to test Sentry backend reporting."""
    if not user.is_superuser:
        raise HTTPException(status_code=403, detail="Superuser access required")
    raise RuntimeError("[Sentry Test] Backend error")
