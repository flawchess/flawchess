# Phase 122: In-app feedback button (SEED-049) - Research

**Researched:** 2026-06-15
**Domain:** Full-stack vertical slice (FastAPI + SQLAlchemy 2.x async + Alembic / React 19 + TanStack Query + Tailwind + shadcn) — new persisted entity + global floating UI
**Confidence:** HIGH (codebase-pattern mapping; every recommendation grounded in a real file in this repo)

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01** — Trigger surface: global bottom-right auto-hiding floating button on every page (nav/user-menu entry considered and rejected for v1; revisit if noisy).
- **D-02** — Mobile button behavior (locked): hide-on-scroll-down / show-on-scroll-up; yields to open overlays (drawer/modal/bottom sheet → button hides or sits behind, never on top); respect `env(safe-area-inset-bottom)`; tap target ≥ 44×44pt even if icon is smaller; mini/secondary styling (NOT a high-contrast primary FAB); add bottom scroll padding to long containers.
- **D-03** — Form: freeform text **required**; sentiment rating **optional**; use thumbs-up/down or a 3-point sentiment, NOT 1–5 stars. Exact control settled at UI-design time (UI-SPEC).
- **D-04** — Captured context persisted: `user_id` (always present, incl. guests), page URL, freeform text, optional sentiment, `created_at`. Username / platform / ELO bucket are **derivable from the user record** — do NOT denormalize onto the feedback row unless query convenience clearly warrants it.
- **D-05** — Destinations: new `feedback` table (system of record; FK `user_id` with explicit `ondelete`, appropriate column types, `created_at`) AND Sentry (push signal). Sentry capture with `source="feedback"` + username + ELO bucket + platform as Sentry **tags**. A submission is NOT an exception → use a non-exception Sentry signal (`capture_message` / message event); do NOT embed variable data in the message string (use tags/context).
- **D-06** — Frontend conventions: `data-testid` on button/modal/text input/sentiment control/submit; `aria-label` on the icon-only floating button; semantic `<button>`/`<form>`; theme colors from `theme.ts`; modal primary submit = `variant="default"` (brand brown); page URL wired from router at submit time; same behavior on mobile and desktop.
- **D-07** — Abuse guard: basic per-user rate limit and/or max text length; keep simple (no CAPTCHA, no IP throttling for v1).
- **D-08** — Guests are in scope: guests have device-bound `user_id`s; no nullable-user / anonymous code path.

### Claude's Discretion

- Exact `feedback` table column types/lengths and index choices (follow DB rules).
- Exact sentiment control (thumbs vs 3-point) and its enum/storage encoding — settle in UI-SPEC.
- Rate-limit window/threshold values and max text length (sensible named constants).
- Component file structure, hook names, and where the floating button mounts in the app shell.
- Endpoint path/shape and Pydantic schema names (follow the router prefix convention).
- How "open overlay" state is detected for the yield-to-overlay behavior.

### Deferred Ideas (OUT OF SCOPE)

- Admin/read UI for feedback (use prod MCP + Sentry for now).
- Denormalizing cohort fields onto the feedback row (only if query convenience later warrants it).
- Revisiting the nav/user-menu entry pattern if the floating button proves noisy.
</user_constraints>

## Summary

This is a small, well-scoped vertical slice. The backend half maps almost 1:1 onto the existing **position-bookmarks** feature, which is the canonical reference for a user-owned entity spanning `app/models/ → app/schemas/ → app/routers/ → app/repositories/`. The router is thin (HTTP only), DB access lives in a module-level-function repository, and the current user (guests included) is injected with `Depends(current_active_user)`. The async session dependency is `Depends(get_async_session)`, which **auto-commits on success** — repositories call `session.flush()`, never `session.commit()`.

The frontend half has more genuinely new work because there is **no existing scroll-direction hook and no app-level "an overlay is open" signal** — drawer/modal open state is local per-page component state (`useSidebarState`). The floating button must mount globally in `ProtectedLayout` (alongside `<InstallPromptBanner />`), use `react-router-dom`'s `useLocation()` to capture the URL, and implement its own scroll-direction hook. Safe-area is already solved via the `tailwindcss-safe-area` plugin (`pb-safe` / `pt-safe` utilities) — reuse, don't hand-roll `env()`.

The ELO bucket anchors (800/1200/1600/2000/2400, 400-wide) **exist only as a SQL `CASE` expression** (`canonical_slice_sql.elo_bucket_expr`), not as a reusable Python helper, and a user's rating lives in `user_rating_anchors` keyed by (user_id, TC). The plan must add a small Python bucketing helper that mirrors the SQL anchors and decide which TC's anchor to report (or report all/highest).

**Primary recommendation:** Build the backend as a near-clone of `position_bookmarks` (model + schema + thin router + repository, registered in `app/main.py` under `/api`); reuse the in-process `_SlidingWindowRateLimiter` pattern keyed by `user_id`; emit `sentry_sdk.capture_message("feedback submitted", level="info")` with `set_tag("source","feedback")` + username/elo_bucket/platform tags. Build the frontend as a global component in `ProtectedLayout` using a shadcn `Dialog` + a new scroll-direction hook + a derived "overlay open" signal, mini/`variant` styling for the trigger and `variant="default"` for the modal submit.

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Feedback persistence (`feedback` table) | API / Backend (repository) | Database | DB rules require FK + ondelete + typed columns; written via repository |
| Endpoint validation / response shaping | API / Backend (router) | — | Routers are HTTP-only per project convention |
| Sentry push signal (tags: user/elo/platform) | API / Backend (service or router) | — | Derives cohort fields from the user record server-side; never trust client |
| ELO-bucket / username / platform derivation | API / Backend | Database (`user_rating_anchors`, `users`) | Cohort context is derivable server-side from authenticated user; do NOT denormalize (D-04) |
| Rate limiting | API / Backend (in-process limiter) | — | Single-process Uvicorn; existing `_SlidingWindowRateLimiter` pattern |
| Floating trigger + scroll/yield behavior | Browser / Client | — | Pure client UI state (scroll direction, overlay-open) |
| Modal form + submit mutation | Browser / Client | API | TanStack `useMutation` → POST; global mutation error handler covers Sentry |
| Page-URL capture | Browser / Client | — | `react-router-dom` `useLocation()` at submit time |

## Phase Requirements

No REQ-IDs are mapped to this phase (seed-driven). The locked decisions D-01…D-08 in `<user_constraints>` are the authoritative acceptance criteria. The planner should treat each D-NN as a verifiable requirement.

## Standard Stack

No new packages are required. Every capability is covered by libraries already in the lockfile.

### Core (already installed — verify, do not add)

| Library | Where used | Purpose | Why standard |
|---------|-----------|---------|--------------|
| SQLAlchemy 2.x async | `app/models/*`, `app/repositories/*` | ORM model + async DB access | Project ORM (`select()` API) |
| Alembic | `alembic/versions/*` | Migration for the `feedback` table | Project migration tool; runs on container start |
| Pydantic v2 | `app/schemas/*` | Request/response validation, `Literal` sentiment enum | Project validation standard |
| FastAPI-Users | `app/users.py` | `current_active_user` dependency (guests included) | Project auth |
| sentry-sdk | `app/routers/*`, `app/services/*` | `capture_message` push signal + tags/context | Already initialized in `app/main.py` |
| @tanstack/react-query | `frontend/src/hooks/*` | `useMutation` for the POST; global error capture | Project data layer |
| radix-ui Dialog (shadcn) | `frontend/src/components/ui/dialog.tsx` | The feedback modal | Existing modal primitive |
| react-router-dom | `frontend/src/App.tsx` | `useLocation()` to capture page URL | Project router (NOT TanStack Router) |
| tailwindcss-safe-area | `frontend/src/index.css` (`@import`) | `pb-safe` / safe-area utilities | Already imported; D-02 safe-area requirement |
| lucide-react | throughout | Icon for the trigger (`MessageSquare` / `MessagesSquare` etc.) | Project icon set |

**Installation:** none. `npm view`/`pip index` checks unnecessary — no external packages added. (See Package Legitimacy Audit.)

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| In-process `_SlidingWindowRateLimiter` keyed by user_id | DB-backed rate check (count rows in last N min) | DB approach survives restart + multi-process but adds a query per submit; in-process matches the existing guest-create limiter and D-07 "keep simple". For a low-frequency action either is fine — recommend in-process to mirror the existing pattern. |
| shadcn `Dialog` | shadcn `Drawer` (bottom sheet) on mobile | Drawer is more idiomatic on mobile, but Dialog is already used for form modals (`SuggestionsModal`) and works responsively. Settle in UI-SPEC; Dialog is the lower-risk default. |

## Package Legitimacy Audit

No external packages are installed by this phase. All libraries are already in the project lockfile (`pyproject.toml` / `package.json`). Package Legitimacy Gate is **N/A**.

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
[Floating trigger button]  (global, mounted in ProtectedLayout)
   │  click
   ▼
[Feedback modal: <form> required textarea + optional sentiment]
   │  reads useLocation().pathname (+search) at submit
   │  TanStack useMutation → POST /api/feedback { text, sentiment?, page_url }
   ▼
[Backend router  POST /api/feedback]  (thin: validate, auth, rate-check, call service/repo)
   │  user = Depends(current_active_user)   ← guests included
   │  rate guard: feedback_limiter.is_allowed(str(user.id)) → 429 if not
   ├─► [Repository] INSERT feedback row (user_id FK, page_url, text, sentiment?, created_at server-default)
   │        session auto-commits via get_async_session on success
   └─► [Sentry] capture_message("feedback submitted", level="info")
              set_tag source=feedback, platform, elo_bucket; set_context user/page
   ▼
[201 response] → modal shows success toast (sonner), closes

Derivation (server-side, NOT denormalized):
  username/platform ← users.chess_com_username / lichess_username
  elo_bucket        ← user_rating_anchors.anchor_rating → bucket(800/1200/1600/2000/2400)

Yield-to-overlay (client): trigger hidden when (scrollingDown) OR (an overlay is open)
```

### Recommended Project Structure

```
Backend:
app/models/feedback.py            # new ORM model (clone position_bookmark.py shape)
app/schemas/feedback.py           # FeedbackCreate, FeedbackResponse, Sentiment Literal
app/routers/feedback.py           # APIRouter(prefix="/feedback", tags=["feedback"])
app/repositories/feedback_repository.py   # module-level async fns: create_feedback, recent_count
app/services/feedback_service.py  # OPTIONAL — only if Sentry+derivation logic > a few lines
alembic/versions/YYYYMMDD_HHMMSS_<rev>_phase_122_feedback_table.py
# register: app/main.py → app.include_router(feedback.router, prefix="/api")

Frontend:
frontend/src/components/feedback/FeedbackButton.tsx   # the floating trigger
frontend/src/components/feedback/FeedbackModal.tsx    # Dialog + form + mutation
frontend/src/hooks/useFeedback.ts                     # useMutation wrapper
frontend/src/hooks/useScrollDirection.ts              # NEW — no existing analog
frontend/src/api/client.ts                            # add feedbackApi.submit
frontend/src/types/feedback.ts                        # request/response types
# mount FeedbackButton in ProtectedLayout (App.tsx), next to <InstallPromptBanner />
```

### Pattern 1: Thin router + module-level-function repository (the canonical vertical slice)

**What:** Routers do HTTP only (validate, auth, call repo, shape response). Repositories expose module-level `async def` functions taking `(session, ...)`. No service layer is mandatory — `position_bookmarks` has none (router → repository directly). Add `app/services/feedback_service.py` only if the Sentry-tagging + cohort-derivation logic exceeds a few lines (it likely will, so a thin service is the cleaner home for it).

**When to use:** This entire phase.

**Example (router shape):**
```python
# Source: app/routers/position_bookmarks.py:33-152
router = APIRouter(prefix="/position-bookmarks", tags=["position-bookmarks"])

@router.post("", response_model=PositionBookmarkResponse, status_code=201)
async def create_bookmark(
    data: PositionBookmarkCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
) -> PositionBookmarkResponse:
    bookmark = await position_bookmark_repository.create_bookmark(session, user.id, data)
    return PositionBookmarkResponse.model_validate(bookmark)
```
`[VERIFIED: app/routers/position_bookmarks.py]`

**Example (repository shape — `flush()`, never `commit()`):**
```python
# Source: app/repositories/position_bookmark_repository.py:44-70
async def create_bookmark(session: AsyncSession, user_id: int, data: PositionBookmarkCreate) -> PositionBookmark:
    bookmark = PositionBookmark(user_id=user_id, label=data.label, ...)
    session.add(bookmark)
    await session.flush()   # commit happens in get_async_session on success
    return bookmark
```
`[VERIFIED: app/repositories/position_bookmark_repository.py]`

**For feedback, do it like this:** `POST /feedback` → `feedback_repository.create_feedback(session, user.id, data)` → flush → return 201. The session auto-commits (`get_async_session` does `await session.commit()` after yield).

### Pattern 2: Model with FK + ondelete + server-default created_at

```python
# Source: app/models/position_bookmark.py — mirror this for feedback.py
class Feedback(Base):
    __tablename__ = "feedback"
    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    page_url: Mapped[str] = mapped_column(String(500), nullable=False)        # store path+search, not full origin
    text: Mapped[str] = mapped_column(Text, nullable=False)                   # length capped in Pydantic
    sentiment: Mapped[str | None] = mapped_column(String(16), nullable=True)  # Literal-validated; nullable = optional
    created_at: Mapped[datetime.datetime] = mapped_column(
        nullable=False, server_default=func.now()
    )
```
`[VERIFIED: app/models/position_bookmark.py, app/models/base.py]` — `Base` maps `datetime.datetime → DateTime(timezone=True)` automatically, so a bare `Mapped[datetime.datetime]` is timezone-aware. CASCADE matches user-owned data (CLAUDE.md DB rules).

### Pattern 3: Sentiment as a typed `Literal` (Pydantic v2)

```python
# Source pattern: app/schemas/position_bookmarks.py:10-11 (BookmarkMatchSide = Literal[...])
Sentiment = Literal["up", "down"]            # OR Literal["positive", "neutral", "negative"] for 3-point
_MAX_FEEDBACK_LEN = 2000                      # named constant, no magic number

class FeedbackCreate(BaseModel):
    text: str = Field(min_length=1, max_length=_MAX_FEEDBACK_LEN)
    sentiment: Sentiment | None = None
    page_url: str = Field(max_length=500)

class FeedbackResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    created_at: datetime.datetime
```
`[VERIFIED: app/schemas/position_bookmarks.py]`. Pydantic `max_length` is the D-07 text-length guard — enforced at the boundary, not in the service. The exact sentiment encoding is UI-SPEC's call (D-03 / discretion); keep it a `Literal`.

### Pattern 4: Non-exception Sentry signal with tags/context (D-05)

```python
# Source: app/routers/eval_remote.py:263-275 (capture_message + set_context + set_tag)
sentry_sdk.set_tag("source", "feedback")
sentry_sdk.set_tag("platform", platform)        # "chess.com" | "lichess" | "none"
sentry_sdk.set_tag("elo_bucket", str(elo_bucket))  # "800".."2400" or "unknown"
sentry_sdk.set_context("feedback", {
    "user_id": user.id, "page_url": data.page_url, "sentiment": data.sentiment,
})
sentry_sdk.capture_message("feedback submitted", level="info")
```
`[VERIFIED: app/routers/eval_remote.py:272, app/services/eval_drain.py:994]` — `capture_message(..., level=...)` is an established project pattern. **Never** put the username/url/text into the message string (CLAUDE.md: variables fragment Sentry grouping). Tags are filterable dimensions (enables "2000+ rapid" cohort filtering per D-05). `set_tag`/`set_context` are scoped to the current request hub — set them immediately before the capture.

### Pattern 5: In-process per-user rate limiter (D-07)

```python
# Source: app/core/ip_rate_limiter.py:15-49 — clone, key by user_id instead of IP
# new: app/core/feedback_rate_limiter.py
_FEEDBACK_MAX_REQUESTS = 5
_FEEDBACK_WINDOW_SECONDS = 3600
feedback_limiter = _SlidingWindowRateLimiter(_FEEDBACK_MAX_REQUESTS, _FEEDBACK_WINDOW_SECONDS)

# in the router:
if not feedback_limiter.is_allowed(str(user.id)):
    raise HTTPException(status_code=429, detail="Too many feedback submissions. Try again later.")
```
`[VERIFIED: app/core/ip_rate_limiter.py]` — the class is generic (keyed by an arbitrary string). The module docstring already notes it's single-process / resets on restart, which is acceptable for prod (single Uvicorn). Reuse `_SlidingWindowRateLimiter` directly (import it) rather than copying the class.

### Pattern 6: ELO bucket derivation (NEW Python helper required)

The bucket anchors are confirmed (matches SEED) but exist only as SQL:
```python
# Source: app/services/canonical_slice_sql.py:231-248
def elo_bucket_expr(user_elo_alias: str) -> str:
    # < 800 → NULL; <1200→800; <1600→1200; <2000→1600; <2400→2000; else 2400
```
`[VERIFIED: app/services/canonical_slice_sql.py:231]`. A user's rating lives in `user_rating_anchors` (model: `app/models/user_rating_anchors.py`), one `anchor_rating` per (user_id, TC), read via `user_rating_anchors_repository.fetch_anchors_for_user(session, user_id=...)` which returns `dict[TimeControlBucket, RatingAnchorRow]`. `[VERIFIED: app/repositories/user_rating_anchors_repository.py:129]`

**Do it like this:** add a tiny pure helper, e.g. `app/services/feedback_service.py::elo_bucket(rating: int) -> int | None` mirroring the SQL CASE, plus a derivation step: `anchors = await fetch_anchors_for_user(...)`; pick a representative anchor (the user's primary TC if one exists, else the max anchor, else `None`/"unknown"). The exact TC-selection rule is a small plan decision — `[ASSUMED]` the "highest anchor_rating across TCs" is a sensible default for a single cohort tag. Username/platform: `users.chess_com_username` / `users.lichess_username` directly on the `User` object already injected — no extra query. `[VERIFIED: app/models/user.py:19-20]`

### Pattern 7: Global mount point + URL capture (frontend)

```tsx
// Source: app/App.tsx ProtectedLayout (lines 446-462) — InstallPromptBanner mounts here globally
return (
  <>
    <NavHeader />
    <main className="pb-16 sm:pb-0"><Outlet /></main>
    <MobileBottomBar onMoreClick={...} />
    <MobileMoreDrawer ... />
    <InstallPromptBanner />
    {/* mount <FeedbackButton /> here */}
  </>
);
```
`[VERIFIED: frontend/src/App.tsx:446-461]`. Capture URL with `react-router-dom`:
```tsx
import { useLocation } from 'react-router-dom';
const location = useLocation();
// at submit: pageUrl = location.pathname + location.search
```
`[VERIFIED: frontend/src/App.tsx:2,96]` — the app uses `react-router-dom` `useLocation()`, NOT TanStack Router. Capture at submit time (D-06).

### Pattern 8: Modal + mutation (no double Sentry capture)

```tsx
// Source: frontend/src/components/position-bookmarks/SuggestionsModal.tsx + hooks/useImport.ts
export function useFeedback() {
  return useMutation<FeedbackResponse, Error, FeedbackRequest>({
    mutationFn: async (body) => (await apiClient.post<FeedbackResponse>('/feedback', body)).data,
  });
}
```
`[VERIFIED: frontend/src/hooks/useImport.ts:24-31, frontend/src/lib/queryClient.ts]`. **Do NOT** add a `Sentry.captureException` in the modal's catch — `MutationCache.onError` in `queryClient.ts` already captures every mutation failure globally (CLAUDE.md frontend rule). On success: `sonner` toast + `onOpenChange(false)`. Dialog usage: `<Dialog open onOpenChange>` with `DialogContent`/`DialogHeader`/`DialogFooter`; submit button `<Button data-testid="..." onClick=...>` uses `variant="default"` (brand brown) by default (D-06).

### Pattern 9: Scroll-direction + yield-to-overlay (NEW — landmine, see Pitfalls)

No existing scroll-direction hook. Write `useScrollDirection.ts` (debounced `scroll` listener comparing `window.scrollY` to last value; return `'up' | 'down'`). For yield-to-overlay there is **no global overlay signal** — `useSidebarState` is per-page local state (`frontend/src/pages/openings/useSidebarState.ts`). `[VERIFIED: frontend/src/pages/openings/useSidebarState.ts]` Options (Claude's discretion per D-02):
- **Recommended:** a tiny global `useOverlayStore` (zustand — already used: `useFilterStore`, `useFlawFilterStore`) that overlays increment/decrement, OR a DOM-presence check: hide the button when `document.querySelector('[data-slot="dialog-content"], [data-slot="drawer-content"], [role="dialog"]')` exists (radix sets these). DOM check requires no wiring into every drawer but is more brittle.
- The button itself is a radix Dialog, so when its OWN modal is open the button being hidden is harmless.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| iOS safe-area bottom inset | raw `style={{paddingBottom: 'env(safe-area-inset-bottom)'}}` | `pb-safe` utility (`tailwindcss-safe-area`, already `@import`-ed in `index.css`; `pb-safe`/`pt-safe` used in `App.tsx`) | Project already standardizes safe-area via this plugin |
| Modal / focus trap / overlay | custom portal + ESC handling | shadcn `Dialog` (`components/ui/dialog.tsx`, radix) | Focus trap, ESC, `aria` already handled |
| Mutation error → Sentry | `try/catch + Sentry.captureException` in the modal | global `MutationCache.onError` in `queryClient.ts` | Double-capture is an explicit CLAUDE.md anti-pattern |
| Session commit in repo | `await session.commit()` | `await session.flush()` + auto-commit in `get_async_session` | Matches every existing repository; commit-in-repo breaks the request-scoped transaction |
| Rate-limiter class | new sliding-window impl | import `_SlidingWindowRateLimiter` from `app/core/ip_rate_limiter.py` | Generic, keyed by arbitrary string; battle-tested for guest-create |
| ELO bucketing scheme | a new anchor scheme | mirror `elo_bucket_expr` anchors (800/1200/1600/2000/2400) in a Python helper | SEED + canonical SQL already define these exact 400-wide buckets |
| Button colors | hand-rolled `bg-*` on the submit | `Button variant="default"` (brand brown) / mini variant for trigger | CLAUDE.md: never hand-roll button colors |

**Key insight:** The backend is a mechanical clone of an existing feature; nearly all risk is on the frontend's two genuinely-new pieces — the scroll-direction hook and the overlay-yield signal — because no analog exists in the codebase.

## Common Pitfalls

### Pitfall 1: Double Sentry capture on the frontend
**What goes wrong:** Adding `Sentry.captureException` in the modal's mutation `onError`.
**Why:** `MutationCache.onError` in `frontend/src/lib/queryClient.ts` already captures all mutation failures.
**How to avoid:** Let errors propagate to TanStack; show user-facing failure via `isError` / toast only.
**Warning signs:** Two Sentry issues per failed submit; a `captureException` import in the modal.

### Pitfall 2: Embedding variables in the Sentry message string
**What goes wrong:** `capture_message(f"feedback from {username} on {url}")` → every submission becomes a separate Sentry issue (broken grouping).
**Why:** Sentry groups by message; variable text fragments it (explicit CLAUDE.md rule, mirrored in D-05).
**How to avoid:** Static message + `set_tag`/`set_context` for username/elo/platform/url.

### Pitfall 3: Committing in the repository
**What goes wrong:** `await session.commit()` inside `create_feedback`.
**Why:** `get_async_session` already commits after the request; a mid-request commit ends the transaction early and can desync.
**How to avoid:** `session.add(...)` + `await session.flush()`; return the ORM object (PK populated post-flush).
**Note:** Never use `asyncio.gather` on the same `AsyncSession` (CLAUDE.md critical constraint) — not a risk here (single insert), but keep all queries sequential.

### Pitfall 4 (THE design risk per seed): mobile drawer ↔ floating button collision
**What goes wrong:** The button floats on top of an open filter/bookmark drawer or the mobile bottom bar in the same bottom-right corner.
**Why:** There is no global "overlay open" signal — drawer state is local per-page (`useSidebarState`), and `MobileBottomBar` is a `fixed bottom-0` element with `z-40`.
**How to avoid:** (1) Implement the yield-to-overlay signal (zustand store or radix DOM-presence check). (2) Account for the mobile bottom bar: `<main className="pb-16 sm:pb-0">` already reserves 4rem at the bottom on mobile — position the button above the bottom bar (e.g. `bottom-[calc(4rem+env(safe-area-inset-bottom))]` on mobile, or `bottom-4` on `sm:`) and keep it below `z-40` so the bottom bar/drawers win, OR hide it entirely when a drawer is open. (3) Verify against the ACTUAL components: `MobileBottomBar`/`MobileMoreDrawer` (`App.tsx`), filter/bookmark drawers (`useSidebarState` consumers in `pages/openings/`).
**Warning signs:** button overlapping the bottom nav on `/openings` mobile; button visible over an open filter drawer.

### Pitfall 5: `noUncheckedIndexedAccess` + min font + knip
**What goes wrong:** TS strict-mode and CI gates.
**How to avoid:** Narrow every array/Record index access (assign-and-check / `!` when provably in-bounds); never use `text-xs` for primary content (`text-sm` floor — tooltip exception only); ensure every new export is imported somewhere (knip fails CI on dead exports — if `feedback_service.py` has a helper used only in one router, import it). `data-testid` on button/modal/textarea/sentiment/submit + `aria-label` on the icon-only trigger (D-06, browser-automation rules).

### Pitfall 6: ty / type-safety gates
**What goes wrong:** CI `ty check` fails.
**How to avoid:** Explicit return types on all new functions; `Sequence[str]` not `list[str]` for params taking `list[Literal]`; `Sentiment` as `Literal`, not bare `str`; no magic numbers (extract `_MAX_FEEDBACK_LEN`, rate-limit window/threshold as named constants).

## Code Examples

### Backend: full create flow (router → repo, with rate guard + Sentry)
```python
# app/routers/feedback.py — synthesized from position_bookmarks.py + eval_remote.py + ip_rate_limiter.py
@router.post("", response_model=FeedbackResponse, status_code=201)
async def submit_feedback(
    data: FeedbackCreate,
    session: Annotated[AsyncSession, Depends(get_async_session)],
    user: Annotated[User, Depends(current_active_user)],
) -> FeedbackResponse:
    if not feedback_limiter.is_allowed(str(user.id)):
        raise HTTPException(status_code=429, detail="Too many submissions. Try again later.")
    fb = await feedback_repository.create_feedback(session, user.id, data)
    await feedback_service.push_sentry_signal(session, user, data)  # derives platform/elo_bucket
    return FeedbackResponse.model_validate(fb)
```

### Backend test pattern (register → login → authed POST)
```python
# Source: tests/test_bookmarks_router.py:43-77 — clone for feedback
@pytest_asyncio.fixture(scope="module")
async def auth_headers() -> dict[str, str]:
    email = f"feedback_test_{uuid.uuid4().hex[:8]}@example.com"
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
        await client.post("/api/auth/register", json={"email": email, "password": "testpassword123"})
        login = await client.post("/api/auth/jwt/login", data={"username": email, "password": "testpassword123"})
        return {"Authorization": f"Bearer {login.json()['access_token']}"}
```
`[VERIFIED: tests/test_bookmarks_router.py]` — tests run against a per-run isolated DB (`tests/conftest.py`); auth is real (register+login), not mocked. Add a guest-path test (`POST /api/auth/guest/create` then submit) per D-08, mirroring `tests/test_guest_auth.py`.

### Frontend component test pattern
```tsx
// Source: frontend/src/components/__tests__/EvalCoverageHeader.test.tsx
// @vitest-environment jsdom
import { describe, it, expect, vi } from 'vitest';
import { render, screen } from '@testing-library/react';
// mock the hook (useFeedback) to avoid needing a QueryClientProvider; assert testids + form behavior
```
`[VERIFIED: frontend/src/components/__tests__/EvalCoverageHeader.test.tsx]` — vitest + @testing-library/react + jsdom; mock hooks to isolate the component.

## Runtime State Inventory

Not a rename/refactor/migration phase — this is greenfield (one new table, new components). Section omitted by design; the only "migration" is the additive Alembic revision for the `feedback` table (no data migration, no string rename, no live-service/OS/secrets state to update).

## State of the Art

| Old Approach | Current Approach | Where | Impact |
|--------------|------------------|-------|--------|
| Bare `str` for fixed value sets | `Literal[...]` enums | `app/schemas/*` | Sentiment must be `Literal`, not `str` |
| `session.commit()` in repo | `session.flush()` + auto-commit dep | all repositories | Follow the flush pattern |
| raw `env(safe-area-inset-*)` | `tailwindcss-safe-area` `pb-safe` utilities | `frontend/src/index.css` | Reuse the plugin utility |

**Deprecated/outdated:** none relevant to this phase.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Reporting the user's **highest** `anchor_rating` across TCs as the single ELO cohort tag is acceptable | Pattern 6 | Low — cohort tag is for coarse filtering; plan/UI-SPEC can refine TC selection. Could alternatively emit per-TC or the primary-TC bucket. |
| A2 | A thin `feedback_service.py` is warranted (vs. router-only like position_bookmarks) for the Sentry+derivation logic | Structure / Pattern 1 | Low — if logic stays tiny, it can live in the router; knip will flag an unused service module. |
| A3 | DOM-presence check OR a new zustand `useOverlayStore` is the intended "overlay open" detection | Pattern 9 | Medium — D-02 mandates the yield behavior but leaves detection to discretion; if a global signal is preferred over DOM-sniffing, the plan must wire every drawer to it. This is the phase's main design uncertainty. |
| A4 | `page_url` should store `pathname + search` (not full origin) and `String(500)` is sufficient | Pattern 2/3 | Low — paths are short; cap is generous. |
| A5 | In-process rate limiter is acceptable for prod (single Uvicorn process) | Pattern 5 | Low — matches existing guest-create limiter; CLAUDE.md confirms single-process prod. |

## Open Questions (RESOLVED)

1. **Which TC's ELO anchor becomes the Sentry `elo_bucket` tag?**
   - Known: `user_rating_anchors` has one `anchor_rating` per (user_id, TC); buckets are 800/1200/1600/2000/2400.
   - Unclear: single tag vs. per-TC; which TC if single.
   - Recommendation: emit the highest anchor as `elo_bucket` (A1); revisit if cohort filtering needs per-TC granularity. Settle in plan.
   - **RESOLVED:** emit the user's **highest `anchor_rating` across TCs** as the single `elo_bucket` tag (locked in Plan 122-01 `push_sentry_signal`).

2. **Overlay-yield detection mechanism (the real design risk).**
   - Known: no global overlay signal; drawer state is per-page (`useSidebarState`); radix sets `[data-slot="dialog-content"]` / `[role="dialog"]`.
   - Unclear: DOM-presence sniff vs. a new global store wired into drawers.
   - Recommendation: prototype both during UI-SPEC; DOM-presence is lower-wiring, a store is more explicit. A `/gsd-sketch` (seed's suggestion) would de-risk the mobile placement/feel.
   - **RESOLVED:** use the **DOM-presence sniff** (`useOverlayOpen` queries `[role="dialog"], [data-slot="dialog-content"], [data-slot="drawer-content"]`) — lower wiring, no per-drawer changes (locked in Plan 122-02 Task 1 / UI-SPEC yield contract).

3. **Sentiment encoding (thumbs vs 3-point).**
   - Deferred to UI-SPEC (D-03). Storage: `Literal["up","down"]` or `Literal["positive","neutral","negative"]`, nullable column. Plan should leave the column wide enough (`String(16)`) to accommodate either.
   - **RESOLVED:** **3-point** sentiment, `Literal["negative","neutral","positive"]`, optional/nullable, `String(16)` column (locked in UI-SPEC, mirrored in both plans).

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| Dev PostgreSQL (Docker) | running backend + tests | ✓ (per CLAUDE.md `docker-compose.dev.yml`) | PG 18 | — |
| All Python deps (uv lockfile) | backend | ✓ | locked | — |
| Node deps (`tailwindcss-safe-area`, radix, tanstack) | frontend | ✓ | locked | — |

No new external dependencies. No blocking gaps.

## Validation Architecture

> `.planning/config.json` `workflow.nyquist_validation` not inspected as a hard gate here; section included (default-enabled) since the phase ships testable backend + frontend behavior.

### Test Framework
| Property | Value |
|----------|-------|
| Backend framework | pytest + pytest-asyncio + httpx ASGITransport; per-run isolated DB (`tests/conftest.py`) |
| Backend quick run | `uv run pytest tests/test_feedback_router.py` (serial for a single file) |
| Backend full suite | `uv run pytest -n auto` (parallel; safe via per-run DB) |
| Frontend framework | vitest + @testing-library/react + jsdom |
| Frontend run | `cd frontend && npm test -- --run` |

### Phase Requirements → Test Map
| Req | Behavior | Test Type | Command | File Exists? |
|-----|----------|-----------|---------|-------------|
| D-04/D-05 | POST persists a feedback row (user_id, page_url, text, sentiment?, created_at) | integration | `uv run pytest tests/test_feedback_router.py -k persist` | ❌ Wave 0 |
| D-03/D-07 | empty text → 422; over-max text → 422 | integration | `uv run pytest tests/test_feedback_router.py -k validation` | ❌ Wave 0 |
| D-07 | over-rate → 429 | integration | `uv run pytest tests/test_feedback_router.py -k rate_limit` | ❌ Wave 0 |
| D-08 | guest can submit (POST /auth/guest/create then submit) | integration | `uv run pytest tests/test_feedback_router.py -k guest` | ❌ Wave 0 |
| D-05 | sentiment stored as Literal; repo create returns row | unit | `uv run pytest tests/test_feedback_repository.py` | ❌ Wave 0 |
| D-01/D-06 | button renders, has testid+aria-label, opens modal | component | `cd frontend && npm test -- --run FeedbackButton` | ❌ Wave 0 |
| D-03/D-06 | modal: submit disabled until text non-empty; mutation fires | component | `cd frontend && npm test -- --run FeedbackModal` | ❌ Wave 0 |
| D-02 | scroll-direction hook returns up/down | unit | `cd frontend && npm test -- --run useScrollDirection` | ❌ Wave 0 |

### Sampling Rate
- **Per task commit:** the single relevant new test file (serial backend / `--run` frontend).
- **Per wave merge / phase gate:** FULL local gate (CLAUDE.md): `uv run ruff format`, `ruff check --fix`, `ty check app/ tests/`, `pytest -n auto -x`, then `cd frontend && npm run lint && npm test -- --run`. This is the mandatory pre-squash-merge gate to `main`.

### Wave 0 Gaps
- [ ] `tests/test_feedback_router.py` — covers D-04/05/07/08 (clone `tests/test_bookmarks_router.py`)
- [ ] `tests/test_feedback_repository.py` — covers repo create + sentiment (clone `tests/test_bookmark_repository.py`)
- [ ] `frontend/src/components/feedback/__tests__/FeedbackButton.test.tsx` + `FeedbackModal.test.tsx`
- [ ] `frontend/src/hooks/__tests__/useScrollDirection.test.ts`
- No framework install needed — both test stacks already configured.

## Security Domain

> `security_enforcement` treated as enabled (default). Scope is a small authenticated write endpoint.

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | FastAPI-Users `current_active_user` — endpoint requires a valid (guest or full) JWT; no anonymous path (D-08) |
| V3 Session Management | no (reuses existing JWT) | — |
| V4 Access Control | yes | `user_id` taken from the authenticated user, NEVER from the request body (mirrors `fetch_anchors_for_user` V4 note); insert is server-attributed |
| V5 Input Validation | yes | Pydantic `Field(min_length, max_length)` on text; `Literal` on sentiment; `page_url` length-capped |
| V6 Cryptography | no | — |
| V11 Business Logic (anti-automation) | yes | per-user rate limit (`_SlidingWindowRateLimiter`) — D-07 abuse guard |

### Known Threat Patterns for this stack

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Spoofed `user_id` in body (attribute feedback to another user) | Spoofing/Elevation | Derive `user_id` from `current_active_user`, never from request payload |
| Spam / flooding the endpoint | Denial of Service | Per-user sliding-window rate limit + 429 |
| Oversized payload | DoS/Tampering | Pydantic `max_length` on text; `String(500)` on page_url |
| Stored XSS (feedback text rendered later) | Tampering | Out of scope (no read UI in v1); when an admin UI is built, render as text/escape — note for the deferred read-UI phase |
| SQL injection | Tampering | SQLAlchemy ORM parameterizes — no raw SQL in the feedback path |
| PII leakage to Sentry | Info Disclosure | Tags carry username/platform/elo bucket (intentional cohort context per D-05); avoid putting raw email or full text in tags — use context sparingly |

## Sources

### Primary (HIGH confidence — direct codebase reads)
- `app/routers/position_bookmarks.py`, `app/repositories/position_bookmark_repository.py`, `app/schemas/position_bookmarks.py` — canonical vertical slice
- `app/models/position_bookmark.py`, `app/models/base.py`, `app/models/user.py`, `app/models/user_rating_anchors.py` — model conventions
- `app/core/database.py` (`get_async_session` auto-commit), `app/users.py` (`current_active_user`, guests) — DI + auth
- `app/core/ip_rate_limiter.py` — rate-limiter pattern
- `app/routers/eval_remote.py:263-275`, `app/services/eval_drain.py:994` — `capture_message` + tags/context
- `app/services/canonical_slice_sql.py:231` (`elo_bucket_expr`), `app/repositories/user_rating_anchors_repository.py:129` — ELO bucket anchors + rating source
- `app/main.py:140-149` — router registration under `/api`
- `frontend/src/App.tsx` — global mount point, `react-router-dom` `useLocation`, `pb-safe`, mobile bottom bar / drawers
- `frontend/src/components/ui/dialog.tsx`, `.../ui/button.tsx` — modal + Button variants
- `frontend/src/components/position-bookmarks/SuggestionsModal.tsx`, `frontend/src/hooks/useImport.ts`, `frontend/src/lib/queryClient.ts` — modal+mutation, global Sentry capture
- `frontend/src/pages/openings/useSidebarState.ts` — drawer state is per-page (no global overlay signal)
- `frontend/src/index.css` (`@import "tailwindcss-safe-area"`) — safe-area utilities
- `tests/test_bookmarks_router.py`, `frontend/src/components/__tests__/EvalCoverageHeader.test.tsx` — test patterns
- `alembic.ini` (`file_template`), `alembic/versions/` — migration naming (`YYYYMMDD_HHMMSS_<rev>_<slug>`)
- `CLAUDE.md` — all project constraints

### Secondary / Tertiary
- None — no external sources needed; this is a codebase-grounded plan.

## Project Constraints (from CLAUDE.md)

- Routers HTTP-only; business logic in services; DB access in repositories. `APIRouter(prefix=...)` with relative decorator paths.
- DB: FK with explicit `ondelete`; appropriate column types; `server_default` `created_at`; `UniqueConstraint` for natural keys (no natural key here beyond the row id).
- Sentry: `capture_message` for non-exceptions; `set_tag`/`set_context`; never embed variables in message strings; tags = filterable dimensions (`source`, `platform`).
- Never `session.commit()` in a repo; never `asyncio.gather` on one `AsyncSession`; all queries sequential.
- Frontend: `data-testid` on every interactive element; `aria-label` on icon-only buttons; semantic `<button>`/`<form>`; theme colors from `theme.ts`; primary = `variant="default"` (brand brown); secondary = `brand-outline`; min font `text-sm` (tooltip exception); apply changes to mobile AND desktop.
- No double Sentry capture in components using `useMutation` (global handler covers them).
- `noUncheckedIndexedAccess`: narrow all index access. knip: no dead exports. ty: zero errors, explicit return types, `Literal` for fixed sets, `Sequence` not `list` for covariant params.
- No magic numbers — extract `_MAX_FEEDBACK_LEN`, rate-limit window/threshold, etc. as named constants.
- Function size limits: nesting ≤3 (hard 4), logic LOC soft 100; keep routers thin.
- Full local gate (backend ruff/ty/pytest + frontend lint/test) before squash-merge to `main`.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — no new packages; all analogs exist in-repo.
- Architecture (backend): HIGH — near-clone of position_bookmarks, verified end to end.
- Architecture (frontend): MEDIUM-HIGH — mount point, modal, mutation, safe-area all verified; scroll-direction hook and overlay-yield signal are genuinely new (no analog) → the only real implementation uncertainty.
- Pitfalls: HIGH — derived from CLAUDE.md rules + observed code.
- ELO derivation: MEDIUM — anchors verified; TC-selection rule is an open plan decision (A1).

**Research date:** 2026-06-15
**Valid until:** ~2026-07-15 (stable; brownfield patterns change slowly). Re-verify `App.tsx` mount point and `useSidebarState` if the app shell is refactored before planning.
