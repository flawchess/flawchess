# Phase 231: Weekly Leaderboard Medals (SEED-186) - Research

**Researched:** 2026-10-04
**Domain:** FastAPI/SQLAlchemy async snapshot table + lazy idempotent finalization; React/TanStack Query prop-driven UI with Radix Dialog, canvas-confetti and Web Audio
**Confidence:** HIGH (everything is in-repo; two PostgreSQL behaviours were probed live on PG 18.3)

## Summary

Phase 231 is almost entirely a composition of existing Phase 230 parts. The ranking for a past week needs
no new logic: `fetch_week_aggregates(session, week_start=..., week_end=...)` already takes an arbitrary
window, and `_entry_for` + `_tiered_order` already yield exactly "public entries, qualified first, ranked,
tentative unranked". A new pure `final_standings(kind, aggregates)` in `app/services/train_leaderboard.py`
filters to `is_public` entries, runs `_tiered_order`, drops rank-`None` (tentative) entries, and attaches
`medal_for(rank, value)`. That satisfies D-01, D-02, D-05 and D-06 with no second ranking implementation.

For finalization, use a tiny companion marker table (one row per finalized week) next to the standings
table. Inserting the marker with `ON CONFLICT DO NOTHING RETURNING` both remembers empty weeks and
serializes concurrent finalizers without an advisory lock. Probed live: a second inserter blocks until the
first transaction commits, then gets 0 rows. Account deletion has **no application code path** (it is a
manual operator `DELETE FROM users` per the runbook), so the only reliable erasure of `display_name` is a
database trigger. Also probed live: an `ON DELETE SET NULL` FK action fires a user-defined
`BEFORE UPDATE OF user_id` row trigger on the referencing table, so the trigger rewrites `display_name` to
"Deleted user" in the same statement.

On the frontend, the work is a seam refactor of `TrainLeaderboardCard` into a prop-driven view plus the
existing thin `useTrainLeaderboard` container. Add three presentational components (`MedalTally`,
`LastWeekPodium`, `MedalClaimDialog`) that take `muted` / `reducedMotion` as props, so the admin demo can
simulate both, and one host on `TrainStartScreen`. No new npm or PyPI packages: lucide-react 1.41.0
already ships `Medal`, and `canvas-confetti`, `radix-ui` Dialog and `tw-animate-css` are already installed.

**Primary recommendation:** Build the snapshot on `final_standings()` (reusing `_entry_for`/`_tiered_order`), with a `train_weekly_finalizations` marker table as the lock and memory, a 5-minute post-deadline grace, a `BEFORE UPDATE OF user_id` erasure trigger, the last-week block and tally folded into `GET /train/leaderboard`, and a separate `GET /train/medals/unclaimed` + `POST /train/medals/claim` pair keyed on `(week_start, board)` and scoped to `current_active_user.id`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

#### Locked upstream (SEED-186 + ROADMAP Phase 231, owner 2026-10-04; do not re-open)
Everything in `../../seeds/closed/SEED-186-weekly-leaderboard-medals.md` § "Locked decisions" is binding:
per-board medals, Accuracy medals for qualified users only, medals follow the public board (opted-out
at finalization time and guests are ineligible), Olympic ties, no Points participation floor,
`MEDALS_START_WEEK = 2026-10-05`, WR-01 accepted (do not fix), snapshot shape (`final_rank`, `value`,
`puzzles`, `display_name`, explicit `medal` SMALLINT IntEnum + CHECK, `celebrated_at`, unique on
week + board + user), lazy finalization with `ON CONFLICT DO NOTHING` and no cron, deletion sets
`user_id` NULL + "Deleted user", opt-out masks past podium names as "Anonymous" while the tally
survives, tally rendering (lucide `Medal`, `theme.ts` gold/silver/bronze, `text-sm` count, no emoji,
`aria-label`, in the wrapping name block), wire format `medals: {gold, silver, bronze}` with no user
id, podium format, Claim button (audio-unlock gesture), `useMuted` / `prefersReducedMotion()`,
server-side claim via `celebrated_at` on Claim or dismiss, no Umami event, admin demo page scenarios.

#### Who gets a final-standings row (Claude's call, owner said "you decide")
- **D-01:** The snapshot freezes the public board exactly. Points: every registered, non-hidden user
  with at least one solve in the week, ranked. Accuracy: qualified users only (20+ non-filler
  solves), ranked. Tentative Accuracy users, users hidden at finalization time, and guests get **no
  row**. This follows the seed's "medals follow the public board exactly" and "final standings skip
  tentative users", and keeps `final_rank` a true public rank (a hidden user's would-be rank would
  sit beside a real user with the same rank number without being a tie).
  — **Reversibility:** costly — rows not written at finalization can only be rebuilt later from
  `drill_solves` with the opt-out flags as they are at rebuild time, not as they were.
- **D-02:** Ranks in the snapshot come from the same service code as the live board
  (`_tiered_order` / `_competition_ranks` in `app/services/train_leaderboard.py`, as amended by
  quick 261004-8rt), never a second ranking implementation. `medal` is assigned from the
  competition rank (1 gold, 2 silver, 3 bronze) and stored explicitly.
- **D-03:** "You finished #N last week" shows on a tab only when the viewer has a snapshot row for
  that board in the immediately previous week and it carries no medal. Medallists get no such line
  (the podium and tally already show it). No row (hidden, tentative, guest, didn't play) means no
  line. It is a **separate line** in the hint area, below this week's hint (pass target, qualify
  count, etc.), not a replacement for it. Copy: plain rank, e.g. "You finished #12 last week".
- **D-04:** A viewer who opted out after the week still sees their own "finished #N" line and
  claims their own medals (it is their own data; masking only applies to what others see).

#### Medal floor (Claude's call)
- **D-05:** A medal needs a value above zero: a Points entry with 0 points, or a qualified Accuracy
  entry at 0%, gets its snapshot row and rank but `medal` NULL. This only matters in a quiet week
  (bronze for 0 points would be silly) and is not a participation floor: one point is enough.
  Flagged as a deliberate refinement of the seed's "no participation floor"; revisit if the owner
  disagrees.
- **D-06:** Fewer than 3 eligible entrants means fewer medals. Ties can produce more than three
  medal rows (1, 1, 3 gives two golds and a bronze; 1, 2, 2 gives a gold and two silvers, no bronze).

#### Podium edge states (Claude's call)
- **D-07:** The podium shows only the immediately previous ISO week, labelled "Last week". No
  fallback to an older finalized week (the label would lie). In the week of 2026-10-05 (nothing
  finalized yet) there is no podium.
- **D-08:** A tab whose board awarded no medals last week (nobody played, or no qualified Accuracy
  users) shows no podium line at all, rather than an empty-state message.
- **D-09:** Podium names: `display_name` as stored at finalization; "Anonymous" for a user who is
  hidden *now*; "Deleted user" for a row whose `user_id` is NULL. Every tied name listed, the line
  wraps on narrow screens. Placed at the top of the tab, above the Accuracy helper and the rows.

#### Medal dialog (Claude's call)
- **D-10:** Shown on the **Train landing only** (both the default and the in-progress branch of
  `TrainStartScreen`), never mid-session or on the score screen. Never for guests. It opens when the
  unclaimed-medals list is non-empty after the landing mounts.
- **D-11:** One dialog lists every unclaimed medal, newest week first, then Points before Accuracy.
  Each entry: a large tinted lucide `Medal` (same `theme.ts` constants as the tally), the medal and
  board ("Gold, Points"), "(shared)" when tied, the week ("Week of Sep 28", the Monday in UTC) and
  the final value ("412 pts" / "87%"). Title scales with count ("You won a medal!" / "You won 3
  medals!"). Medals animate in with a scale/bounce, skipped under reduced motion.
- **D-12:** Sound: reuse the existing `game-win` event (`WinChime`), no new audio asset. It plays
  once per Claim tap regardless of medal count, unless muted.
- **D-13:** Claim tap: call the audio unlock inside the gesture, play the sound, fire
  `fireWinConfetti()` (unless reduced motion), POST the claim for every shown row, close the dialog
  (the confetti canvas keeps playing over the landing). Dismiss (X, Esc, outside click): POST the
  claim with no sound or confetti. A failed POST is not surfaced beyond the global mutation error
  handling; the medals simply reappear on the next visit.

### Claude's Discretion
- **Finalization trigger and concurrency:** which requests run the lazy finalizer (at least
  `GET /train/leaderboard` and the unclaimed-medals read), how a week with zero eligible entrants is
  remembered as finalized (or cheaply recomputed), and whether to add an advisory lock on top of
  `ON CONFLICT DO NOTHING`. `drill_solves.solved_at` is server-set at submit time
  (`app/repositories/train_repository.py:3001`, `solved_at=now_utc`), so a late finalization sees the
  same solves.
- **API shape:** extending `TrainLeaderboardResponse` with a per-board last-week block (podium +
  viewer's final rank) vs a separate endpoint; a separate unclaimed-medals GET plus a claim POST is
  the expected shape. Claim POST must be scoped to the caller's own rows (IDOR guard).
- **Account deletion mechanics:** find every user-deletion path (`app/services/guest_cleanup_service.py`
  deletes guests, who have no rows per D-01; registered-account deletion may be manual). The stored
  `display_name` must actually be erased, not just masked at read time. Read-time "Deleted user" for
  `user_id IS NULL` is the display rule either way.
- **Tally query:** one grouped `COUNT` over the snapshot for the visible rows' user ids, per board.
- **Component seams for the demo page:** split `TrainLeaderboardCard` so the board, podium and dialog
  take data via props with thin fetching hooks, so the demo renders production components.
- **Theme constants:** exact gold/silver/bronze colors in `theme.ts`, readable on the dark surface.
- **Privacy copy:** the one-line addition to `LeaderboardPrivacyCard` ("Hidden users don't earn
  medals" or similar), plus whether `Privacy.tsx` needs a line about the stored weekly results.

### Deferred Ideas (OUT OF SCOPE)
- "You finished #N" (or "N puzzles short of qualifying") for hidden users and tentative Accuracy users: not stored per D-01; revisit only if asked.
- Revisit the D-05 zero-value medal rule if the owner prefers the seed's literal "no floor".

Also out of scope (domain boundary): per-medal popovers with dates, medal history or a profile medal
case, notifications, seasons/leagues/prizes, WR-01 hardening.
</user_constraints>

<phase_requirements>
## Phase Requirements

No REQ-IDs are mapped (ROADMAP: "Requirements: TBD"). Coverage is derived from the CONTEXT decisions and
the ROADMAP locked list. The planner should treat each row below as a requirement.

| ID (derived) | Description | Research Support |
|----|-------------|------------------|
| SNAP (locked + D-01/D-02/D-05/D-06) | Persist full final standings per (week, board, user) with explicit medal | `final_standings()` over `_entry_for`/`_tiered_order` (§Pattern 1), table shape (§Pattern 3) |
| FINAL (locked + discretion) | Lazy idempotent finalization, no cron, `ON CONFLICT DO NOTHING`, from `MEDALS_START_WEEK` | Marker-table lock (§Pattern 2), grace window (Pitfall 1), probe output |
| DEL (locked) | Deletion sets `user_id` NULL and erases `display_name` to "Deleted user" | Trigger (§Pattern 4), probe output, deletion-path inventory |
| TALLY (locked) | `medals: {gold, silver, bronze}` per visible row, one grouped COUNT, no user id | §Pattern 5 |
| PODIUM (locked + D-07/D-08/D-09) | "Last week:" podium per tab, masking rules | §Pattern 6 |
| FINISH (D-03/D-04) | "You finished #N last week" second hint line | §Pattern 6 (`viewer_final_rank`) |
| DIALOG (locked + D-10..D-13) | Claim-and-celebrate dialog on Train landing | §Pattern 8, §Pattern 9 |
| CLAIM (locked) | Server-side `celebrated_at` via POST on Claim or dismiss, IDOR-scoped | §Pattern 7 |
| DEMO (locked) | Admin-only client-side demo rendering real components, works in prod | §Pattern 10 |
| COPY (discretion) | Privacy toggle line + Privacy.tsx sentence | §Pattern 11 |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

Root `CLAUDE.md`:
- SQLAlchemy 2.x async `select()` API, Alembic migrations, asyncpg; PostgreSQL only.
- Router convention: `APIRouter(prefix="/train", tags=["train"])`, relative paths in decorators. Routers are HTTP only, logic in services, SQL in repositories.
- **FKs mandatory with explicit `ondelete`.** Unique constraints for natural keys.
- **Avoid native PG ENUM.** Low-volume domain columns use TEXT + CHECK (or SMALLINT IntEnum + CHECK). The medal column is locked to SMALLINT IntEnum + CHECK.
- Time-dependent endpoints take `now_utc` from `dev_now_utc` (`app/core/dev_clock.py`), never `datetime.now()`.
- **Never `asyncio.gather` on the same `AsyncSession`.** Sequential awaits.
- Sentry: `capture_exception()` in non-trivial `except` blocks in services/routers. Never embed variables in messages; use `set_context`.
- Type safety: `Literal[...]` for fixed sets (never bare `str`), explicit return types, `Sequence[...]` for covariant params, `# ty: ignore[rule]` only when unfixable. `uv run ty check app/ tests/ scripts/` must be zero errors.
- No magic numbers: named constants (`MEDALS_START_WEEK`, `MEDALS_FINALIZE_GRACE`, `MAX_CLAIM_ITEMS`, ...).
- Nesting depth <= 4 (`scripts/check_function_size.py app/ --fail-over-depth 4`), about 100 logic lines per function (soft).
- Comment bug fixes at the fix site.
- API responses never expose internal ids/hashes. (Phase 230 also forbids user ids on the wire.)
- Pre-merge gate (ruff format/check, ty, function-size, `pytest -n auto -x`, frontend lint/build/test/knip) before squash-merge. CHANGELOG `[Unreleased]` entry required.
- Do not run `bin/reset_db.sh`. Plans must not gate on a dev DB reset (memory).

`frontend/CLAUDE.md`:
- Theme colors live in `frontend/src/lib/theme.ts`.
- `noUncheckedIndexedAccess` is on: narrow indexed access.
- Knip runs in CI: every new export must be imported somewhere.
- `max-depth` 4 gates `npm run lint`. `npm run lint` and `npm test` do not type-check, so `npm run build` (tsc -b) is required. Test files are **excluded** from tsc (`tsconfig.app.json:43`), so stale test fixtures fail only at runtime.
- **Minimum font size `text-sm`**, never `text-xs` in new code.
- `data-testid` on every interactive element and on modal dialogs/major containers, kebab-case, component-prefixed. ARIA labels on icon-only buttons. Semantic HTML.
- Button variants: primary `variant="default"`, secondary `variant="brand-outline"`.
- Global TanStack Query errors are already captured. Do not add `Sentry.captureException` in components that use useQuery/useMutation. Every `useQuery` loading/data/empty chain needs an `isError` branch.
- Umami: `/admin` is excluded. The Claim needs no feature event (locked: the DB row is the record).
- Apply changes to mobile too (the card is single-layout, wrapping at 375 px).

## Architectural Responsibility Map

| Capability | Primary Tier | Secondary Tier | Rationale |
|------------|-------------|----------------|-----------|
| Past-week ranking + medal assignment | API / Backend (pure service) | — | Must reuse the live-board ranking code (D-02); never client-side |
| Finalization trigger + concurrency | API / Backend | Database (unique-index wait) | Lazy on read requests; PG unique-insert semantics are the lock |
| Snapshot persistence | Database / Storage | — | New table + marker table, migration |
| Erasure on account deletion | Database (trigger) | — | There is no app deletion path; manual SQL deletes must erase too |
| Podium masking ("Anonymous" if hidden now, "Deleted user") | API / Backend (read time) | — | Depends on current `users.leaderboard_hidden`; hidden users' names must never reach other clients |
| Tally counts | API / Backend (grouped COUNT) | — | Keyed on user id, which never leaves the server |
| Claim state (`celebrated_at`) | API / Backend | Database | Cross-device once-only; IDOR-scoped by `current_active_user.id` |
| Tally/podium/dialog rendering, sound, confetti, animation | Browser / Client | — | Gesture-bound audio unlock, reduced motion, mute pref are browser-only |
| Admin demo | Browser / Client | — | Client-side dummy data only, no backend (works in prod) |

## Standard Stack

No new dependencies. Everything is already installed and pinned.

### Core (in use)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| SQLAlchemy async + `sqlalchemy.dialects.postgresql.insert` | 2.x | `on_conflict_do_nothing(constraint=...)`, `RETURNING` | Already used: `app/repositories/game_repository.py:64`, `train_repository.py:342` [VERIFIED: codebase grep] |
| Alembic | >=1.13 | Migration incl. `op.execute` for the trigger | Project standard |
| PostgreSQL | 18.3 (dev docker) | Trigger + FK `SET NULL` + unique-index insert wait | Probed live this session [VERIFIED: docker psql probe] |
| lucide-react | 1.41.0 installed (`^1.21.0`) | `Medal` icon | `node_modules/lucide-react/dist/esm/icons/medal.mjs` exists [VERIFIED: ls] |
| canvas-confetti | ^1.9.4 | `fireWinConfetti()` via `lib/confetti.ts` | Already wrapped |
| radix-ui Dialog via `components/ui/dialog.tsx` | ^1.4.3 | Medal dialog | Used by `GameResultDialog`, `FeedbackModal`, etc. |
| tw-animate-css | ^1.4.0 | Dialog enter/exit | Already imported in `index.css:2` |

**Installation:** none.

## Package Legitimacy Audit

No external packages are installed in this phase. The audit is not applicable.

| Package | Registry | Age | Downloads | Source Repo | Verdict | Disposition |
|---------|----------|-----|-----------|-------------|---------|-------------|
| (none) | — | — | — | — | — | — |

**Packages removed due to [SLOP] verdict:** none
**Packages flagged as suspicious [SUS]:** none

## Architecture Patterns

### System Architecture Diagram

```
                   GET /train/leaderboard            GET /train/medals/unclaimed       POST /train/medals/claim
                   (landing, score screen)           (landing host, non-guests)        (Claim tap or dismiss)
                              │                                  │                                │
                              ▼                                  ▼                                │
                 ┌──────────────────────────────────────────────────────────┐                     │
                 │ finalize_due_weeks(session, now_utc)                      │                     │
                 │  due = weeks in [MEDALS_START_WEEK, week_window(now-grace)│                     │
                 │        .start) minus SELECT finalized set                 │                     │
                 │  for each due week (ascending):                           │                     │
                 │    INSERT marker ON CONFLICT DO NOTHING RETURNING ──┐     │                     │
                 │      0 rows → skip (another request did/does it;    │     │                     │
                 │               PG made us wait for its commit)       │     │                     │
                 │      1 row  → fetch_week_aggregates(week)           │     │                     │
                 │               → final_standings('points'|'accuracy')│     │                     │
                 │                 (_entry_for → is_public → _tiered_  │     │                     │
                 │                  order → drop rank None → medal_for)│     │                     │
                 │               → INSERT standings ON CONFLICT DO NOTHING   │                     │
                 │  router commits; on error: rollback + Sentry, continue    │                     │
                 └──────────────────────────────────────────────────────────┘                     │
                              │                                  │                                ▼
                              ▼                                  ▼                 UPDATE standings SET celebrated_at
      live board (Phase 230) + medal tallies           SELECT caller's rows        WHERE user_id = caller AND
      (one grouped COUNT over visible keys)            medal NOT NULL AND          (week_start, board) IN body
      + last_week block per board                      celebrated_at IS NULL       AND celebrated_at IS NULL
        (podium w/ read-time masking via               ordered week desc,
         LEFT JOIN users; viewer_final_rank)           points before accuracy
                              │                                  │
                              ▼                                  ▼
         TrainLeaderboardCard (container)            TrainMedalDialogHost (container, not guest,
           → TrainLeaderboardCardView (props)          not impersonating, once per mount)
               ├ LastWeekPodium                        → MedalClaimDialog (props: medals, muted,
               ├ rows + MedalTally                        reducedMotion, onClaim, onDismiss)
               └ hint + "You finished #N last week"       Claim: unlockAudio → playSound('game-win')
                                                                 → fireWinConfetti → onClaim(keys)
   Admin "Leaderboard medals demo" ── dummy fixtures ──► same View / Podium / Tally / Dialog components

   DELETE FROM users (manual, runbook) ──FK ON DELETE SET NULL──► standings.user_id = NULL
                                        └─ BEFORE UPDATE OF user_id trigger ─► display_name = 'Deleted user'
```

### Recommended Project Structure

```
app/
├── models/train_weekly_standing.py      # TrainWeeklyStanding, TrainWeeklyFinalization, Medal IntEnum
├── repositories/train_medals_repository.py  # finalized set, claim_week marker, insert standings,
│                                            # tallies, last-week rows, unclaimed, claim UPDATE
├── services/train_leaderboard.py        # + final_standings, medal_for, MedalTally, build_board(medal_tallies=),
│                                        #   visible_keys, build_last_week; get_weekly_leaderboard reads tallies + last week
├── services/train_medals.py             # MEDALS_START_WEEK, MEDALS_FINALIZE_GRACE, due_weeks (pure),
│                                        #   finalize_due_weeks, get_unclaimed_medals, claim_medals
├── schemas/train.py                     # + LeaderboardMedals, LeaderboardPodiumEntry, LeaderboardLastWeek,
│                                        #   UnclaimedMedal(s)Response, MedalKey, ClaimMedalsRequest, MedalKind
└── routers/train.py                     # finalizer call in GET /leaderboard; GET /medals/unclaimed; POST /medals/claim
alembic/versions/2026MMDD_HHMMSS_<rev>_phase_231_train_weekly_standings.py  # tables + trigger
alembic/env.py                           # + model import line (autogenerate)

frontend/src/
├── types/train.ts                       # + LeaderboardMedals, LeaderboardLastWeek, UnclaimedMedal, ...
├── api/client.ts                        # trainApi.getUnclaimedMedals, trainApi.claimMedals
├── hooks/useTrainMedals.ts              # useUnclaimedMedals(enabled), useClaimMedals()
├── lib/trainMedals.ts                   # pure copy/helpers: tallyAriaLabel, medalLabel, weekOfLabel, dialogTitle, sort guards
├── lib/theme.ts                         # + MEDAL_GOLD / MEDAL_SILVER / MEDAL_BRONZE + MEDAL_COLORS record
├── index.css                            # + @keyframes medal-pop + .animate-medal-pop (fill-mode both)
├── components/train/TrainLeaderboardCard.tsx   # container + exported TrainLeaderboardCardView
├── components/train/medals/MedalIcon.tsx
├── components/train/medals/MedalTally.tsx
├── components/train/medals/LastWeekPodium.tsx
├── components/train/medals/MedalClaimDialog.tsx
├── components/train/medals/TrainMedalDialogHost.tsx
├── components/train/TrainStartScreen.tsx       # mount TrainMedalDialogHost in every rendered landing branch
├── components/admin/LeaderboardMedalsDemo.tsx  # + fixtures in lib/leaderboardMedalsDemoData.ts
├── pages/Admin.tsx                      # new section NOT under import.meta.env.DEV
├── components/settings/LeaderboardPrivacyCard.tsx  # one more sentence
└── pages/Privacy.tsx                    # one more sentence on stored weekly results
```

### Pattern 1: `final_standings` reuses the live ranking (D-01, D-02, D-05, D-06)

The live board's ordering, already read this session [VERIFIED: app/services/train_leaderboard.py:178-200]:

```python
def _competition_ranks(ordered: Sequence[_Entry]) -> list[int]:
    """Competition ranks over an already ordered list: equal values share a rank."""
    ranks: list[int] = []
    for index, entry in enumerate(ordered):
        if index > 0 and entry.value == ordered[index - 1].value:
            ranks.append(ranks[index - 1])
        else:
            ranks.append(index + 1)
    return ranks


def _tiered_order(combined: Sequence[_Entry]) -> tuple[list[_Entry], list[int | None]]:
    ...
    qualified = sorted((e for e in combined if not e.tentative), key=_order_key)
    tentative = sorted((e for e in combined if e.tentative), key=_tentative_order_key)
    ranks: list[int | None] = [*_competition_ranks(qualified), *([None] * len(tentative))]
    return [*qualified, *tentative], ranks
```

`_entry_for` sets `is_public = not aggregate.is_guest and not aggregate.leaderboard_hidden`
[VERIFIED: app/services/train_leaderboard.py:153] and returns `None` on Accuracy when there are no
non-filler puzzles. Points entries are never tentative (`False` at line 155).

**Recommended addition (in `train_leaderboard.py`, beside the privates it reuses):**

```python
@dataclass(frozen=True)
class FinalStanding:
    """One snapshot row before persistence. `user_id` is persisted, never serialized."""
    user_id: int
    display_name: str
    final_rank: int
    value: int
    puzzles: int
    medal: Medal | None


def medal_for(rank: int, value: int) -> Medal | None:
    """Olympic rule from the competition rank (D-02/D-06); no medal for a zero value (D-05)."""
    if value <= 0:
        return None
    return MEDAL_BY_RANK.get(rank)   # {1: GOLD, 2: SILVER, 3: BRONZE}


def final_standings(kind: LeaderboardBoardKind, aggregates: Sequence[WeeklyAggregate]) -> list[FinalStanding]:
    """The public board exactly (D-01): public entries only, qualified only on Accuracy."""
    public = [e for e in (_entry_for(kind, a) for a in aggregates) if e is not None and e.is_public]
    ordered, ranks = _tiered_order(public)
    return [
        FinalStanding(e.key, e.name, rank, e.value, e.puzzles, medal_for(rank, e.value))
        for e, rank in zip(ordered, ranks, strict=True)
        if rank is not None          # tentative Accuracy entries get no row (D-01)
    ]
```

Why this equals the public board: `build_board` ranks `combined = [e for e in entries if e.is_public or e.key == viewer_id]`
[VERIFIED: app/services/train_leaderboard.py:285-286]. For any public viewer, combined is exactly the public
list, so `final_rank` equals the rank every public viewer saw at the deadline (modulo late opt-out flips, which are accepted).

Olympic ties fall out of competition ranks: `1, 1, 3` → GOLD, GOLD, BRONZE. `1, 2, 2, 4` → GOLD, SILVER, SILVER, none.
`1, 1, 1, 4` → three GOLD, none. That matches D-06 exactly, with no extra code.

### Pattern 2: Finalization = marker-table lock + memory (discretion: recommended)

**Recommendation: a second tiny table `train_weekly_finalizations(week_start DATE PRIMARY KEY, finalized_at TIMESTAMPTZ NOT NULL DEFAULT now())`. Do not add an advisory lock.**

Why the marker table:
1. **Remembers empty weeks.** A week with zero public entrants writes no standings rows, so "finalized" cannot be inferred from the standings table alone. Without memory, every request re-scans such weeks. The fast path becomes one `SELECT week_start FROM train_weekly_finalizations WHERE week_start >= :start` (at most 52 rows per year).
2. **Serializes concurrent finalizers without `pg_advisory_xact_lock`.** On first landing mount, the leaderboard GET and the unclaimed GET fire together. Probed live this session [VERIFIED: docker psql probe, PG 18.3]. Session A ran `BEGIN; INSERT INTO fw VALUES ('2026-10-05') ON CONFLICT DO NOTHING RETURNING week_start; SELECT pg_sleep(3); COMMIT;`. Session B ran the same INSERT one second later:
   ```
    week_start
   ------------
   (0 rows)

   INSERT 0 0
   B waited: 2.090755799 s
   ```
   B blocked until A committed, then got 0 rows. If A had aborted, B's insert would succeed and B would do the work. That is exactly the lock semantics needed. Ascending week order in every finalizer prevents deadlocks.
3. **All-or-nothing per week.** Marker and standings rows are written in the same transaction, so a crash never leaves a half-finalized week marked done.
4. **Test isolation.** A test can delete its own week's marker before running (see Validation Architecture). A "max(week) finalized" scheme cannot be reset per week.

`ON CONFLICT DO NOTHING` on the standings unique key stays as the locked belt-and-braces guard.

```python
# app/services/train_medals.py
MEDALS_START_WEEK: Final = datetime.date(2026, 10, 5)       # locked
MEDALS_FINALIZE_GRACE: Final = datetime.timedelta(minutes=5)  # see Pitfall 1

def due_weeks(now_utc: datetime.datetime, finalized: Collection[datetime.date]) -> list[datetime.date]:
    """Completed weeks from MEDALS_START_WEEK not yet finalized, ascending (pure)."""
    first_open = week_window(now_utc - MEDALS_FINALIZE_GRACE)[0].date()
    weeks, week = [], MEDALS_START_WEEK
    while week < first_open:
        if week not in finalized:
            weeks.append(week)
        week += datetime.timedelta(days=DAYS_PER_WEEK)
    return weeks

async def finalize_due_weeks(session: AsyncSession, *, now_utc: datetime.datetime) -> int:
    finalized = await train_medals_repository.fetch_finalized_weeks(session, since=MEDALS_START_WEEK)
    done = 0
    for week in due_weeks(now_utc, finalized):
        if not await train_medals_repository.claim_week(session, week_start=week):
            continue  # another request finalized it (PG made us wait for its commit)
        start = datetime.datetime.combine(week, datetime.time.min, tzinfo=datetime.UTC)
        aggregates = await fetch_week_aggregates(session, week_start=start, week_end=start + WEEK)
        rows = [("points", s) for s in final_standings("points", aggregates)] + \
               [("accuracy", s) for s in final_standings("accuracy", aggregates)]
        await train_medals_repository.insert_standings(session, week_start=week, rows=rows)
        done += 1
    return done
```

Read `MEDALS_START_WEEK` at call time (module global, not a default argument) so tests can `monkeypatch` it.

**Which requests call it:** `GET /train/leaderboard` (landing and score-screen variants, guests included, since finalization is global) and `GET /train/medals/unclaimed`. Not the claim POST: it only touches rows that already exist.

**Commit placement:** the router calls `finalize_due_weeks`, then `await session.commit()`, matching the router-commits convention (`app/routers/train.py` progress handler pattern). Wrap it in `try/except Exception: await session.rollback(); sentry_sdk.set_context(...); sentry_sdk.capture_exception()`, then continue serving the live board. A finalization failure must not 500 the board, but it must reach Sentry. Committing before the leaderboard reads also releases the marker row lock promptly.

**Cost per request:** fast path is 1 query. In production the first post-deadline request finalizes 1 week, about 3 queries plus inserts of about 100 rows.

`drill_solves.solved_at` is server-set [VERIFIED: app/repositories/train_repository.py:3001 `solved_at=now_utc,`], and the window predicate is `DrillSolve.solved_at >= week_start, DrillSolve.solved_at < week_end` [VERIFIED: app/repositories/train_leaderboard_repository.py:84]. A late finalization therefore sees the same solves, except solves of users deleted since (their `drill_solves` cascade: `ForeignKey("users.id", ondelete="CASCADE")` [VERIFIED: app/models/drill_solve.py:148]), which is the correct GDPR outcome.

### Pattern 3: Snapshot table shape (locked fields + recommended types)

```python
# app/models/train_weekly_standing.py
class Medal(IntEnum):
    """Stored medal (locked: SMALLINT IntEnum + CHECK). Value = the competition rank that earns it."""
    GOLD = 1
    SILVER = 2
    BRONZE = 3

class TrainWeeklyStanding(Base):
    __tablename__ = "train_weekly_standings"
    __table_args__ = (
        CheckConstraint("board IN ('points', 'accuracy')", name="ck_train_weekly_standings_board"),
        CheckConstraint("medal IS NULL OR medal IN (1, 2, 3)", name="ck_train_weekly_standings_medal"),
        UniqueConstraint("week_start", "board", "user_id", name="uq_train_weekly_standings_week_board_user"),
        Index("ix_train_weekly_standings_user_id", "user_id"),
    )
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)   # user_id is nullable, so it cannot be in the PK
    week_start: Mapped[datetime.date] = mapped_column(Date, nullable=False)  # Monday, UTC
    board: Mapped[str] = mapped_column(Text, nullable=False)                 # Literal at the service boundary
    user_id: Mapped[int | None] = mapped_column(ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    display_name: Mapped[str] = mapped_column(Text, nullable=False)
    final_rank: Mapped[int] = mapped_column(Integer, nullable=False)
    value: Mapped[int] = mapped_column(Integer, nullable=False)
    puzzles: Mapped[int] = mapped_column(Integer, nullable=False)
    medal: Mapped[int | None] = mapped_column(SmallInteger, nullable=True)
    celebrated_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finalized_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
```

Conventions this follows (read this session):
- CHECK string style `"move_quality IS NULL OR move_quality IN (0, 1, 2)"` with name `ck_drill_solves_move_quality` [VERIFIED: app/models/drill_solve.py:130-133]; TEXT + CHECK `"status IN ('open', 'completed', 'expired')"` named `ck_drill_sessions_status` [VERIFIED: app/models/drill_session.py:45-47].
- `users.id` is `Mapped[int] = mapped_column(primary_key=True, autoincrement=True)` (int4) [VERIFIED: app/models/user.py:17], so `user_id` is `Integer`.
- `board` uses TEXT + CHECK (low-volume domain column, CLAUDE.md). The service boundary types it as `LeaderboardBoardKind = Literal["points", "accuracy"]` [VERIFIED: app/schemas/train.py:440].
- `final_rank`/`value`/`puzzles` are INTEGER, not SMALLINT: they are unbounded counts (a 32767 cap on weekly points is about 10.9k puzzles, which is plausible over time, and rank grows with the user base). `medal` is SMALLINT (locked).
- Index on `user_id`: serves the FK `SET NULL` cascade on user delete, the tally query, the unclaimed query and the claim UPDATE. The unique index (leading `week_start`) serves the podium and viewer-row reads. Volume is about 100 rows per week, so nothing else is needed.
- Migration file name: `YYYYMMDD_HHMMSS_<rev>_<slug>.py` (`file_template = %%(year)d%%(month).2d%%(day).2d_%%(hour).2d%%(minute).2d%%(second).2d_%%(rev)s_%%(slug)s` [VERIFIED: alembic.ini:17]). Down-revision is the current head `c4e7a91d2b58` (`20261003_120000_c4e7a91d2b58_users_leaderboard_hidden.py`) [VERIFIED: alembic/versions listing + file header]. Re-check `uv run alembic heads` at plan time.
- Add `from app.models.train_weekly_standing import TrainWeeklyStanding, TrainWeeklyFinalization  # noqa: F401` to `alembic/env.py` beside the other Train model imports (`drill_solve`, `train_settings`, ...) [VERIFIED: alembic/env.py:23-30].

### Pattern 4: Erasure on deletion via trigger (discretion: recommended)

**Deletion-path inventory (complete, this session):**

| Path | Deletes `users` rows? | Effect on standings |
|------|----------------------|---------------------|
| Manual operator deletion on request (Privacy page: "Upon request, we will delete your account..." [VERIFIED: frontend/src/pages/Privacy.tsx:76]; runbook: "When a user requests deletion, delete the app account first..." [VERIFIED: docs/production-runbook.md:61]) | Yes, raw SQL | Must be erased by the DB itself |
| `app/services/guest_cleanup_service.py` `_purge_guest` | **No.** Deletes games, import jobs, drill_sessions, train_settings. The `User` row survives (module docstring, lines 6-8) | None. Guests never get rows (D-01) |
| FastAPI-Users `get_users_router` (`DELETE /users/{id}`) | Not mounted. `app/routers/auth.py` includes only auth/register/reset routers [VERIFIED: app/routers/auth.py:41-63] | — |
| `scripts/import_benchmark_users.py:343` `delete(User)` | Benchmark DB stub users only (no drill solves) | Trigger is harmless there |
| Tests (16 files call `delete(User)`) | Yes | Trigger runs, rows anonymize |

No application code path deletes a registered account, so an explicit `UPDATE` in a service would never run. **Use a row trigger.** PG 15+'s `ON DELETE SET NULL (col_list)` cannot do it: the column list must be a subset of the FK columns, so it cannot touch `display_name` [ASSUMED]. Probe run this session on PG 18.3 [VERIFIED: docker psql probe]:

```
CREATE TRIGGER t BEFORE UPDATE OF user_id ON m FOR EACH ROW
  WHEN (OLD.user_id IS NOT NULL AND NEW.user_id IS NULL) EXECUTE FUNCTION pg_temp.erase_name();
DELETE FROM u WHERE id=1;
 id | user_id | display_name
----+---------+--------------
  1 |         | Deleted user
  2 |       2 | bob
```

The FK `SET NULL` referential action fires the user-defined column-specific `BEFORE UPDATE OF user_id` trigger.

Migration body (hand-written; autogenerate does not see triggers):

```python
DELETED_USER_DISPLAY_NAME = "Deleted user"   # keep in sync with the service constant; a test pins both

op.execute("""
CREATE FUNCTION train_weekly_standings_erase_name() RETURNS trigger
LANGUAGE plpgsql AS $$
BEGIN
  NEW.display_name := 'Deleted user';
  RETURN NEW;
END $$;
""")
op.execute("""
CREATE TRIGGER trg_train_weekly_standings_erase_name
BEFORE UPDATE OF user_id ON train_weekly_standings
FOR EACH ROW WHEN (OLD.user_id IS NOT NULL AND NEW.user_id IS NULL)
EXECUTE FUNCTION train_weekly_standings_erase_name();
""")
# downgrade: DROP TRIGGER ... ON train_weekly_standings; DROP FUNCTION ...; then drop tables
```

This is the first trigger in the repo (no `CREATE TRIGGER` in `alembic/versions` [VERIFIED: grep]). Document it in the model docstring, since it is invisible to the ORM, and add an existence test in the style of `tests/test_migration_only_indexes_exist.py` (query `pg_trigger` by name). The read-time rule "`user_id IS NULL` renders as Deleted user" is still applied in the service (D-09), so display stays correct even if the trigger were ever missing. A runbook line under "Deleting an account's analytics" can note that standings anonymize automatically.

### Pattern 5: Tally (one grouped COUNT over visible keys, no ids on the wire)

The invariant: "The internal `_Entry.key` (the user id) is never copied onto a response dataclass." [VERIFIED: app/services/train_leaderboard.py:25]. Keep it:

1. Factor the shared ranking/slicing of `build_board` into a private `_rank_board(kind, aggregates, viewer_id)` that returns ordered entries, ranks, slice indices, gap index and viewer index. `build_board` and a new `visible_keys(kind, aggregates, *, viewer_id) -> list[int]` both call it, so slicing logic is not duplicated. Recomputing is trivially cheap (a few hundred entries).
2. `get_weekly_leaderboard` collects `visible_keys` for both boards, then makes **one** repository call:
   ```sql
   SELECT board, user_id, medal, count(*) FROM train_weekly_standings
   WHERE user_id IN (:visible_ids) AND medal IS NOT NULL
   GROUP BY board, user_id, medal
   ```
   It returns `dict[LeaderboardBoardKind, dict[int, MedalTally]]`. Skip the query when there are no keys.
3. `build_board(..., medal_tallies: Mapping[int, MedalTally] | None = None)` sets `BoardRow.medals = tallies.get(entry.key, ZERO_TALLY)`. With the default `None`, all 707 lines of existing DB-free service tests keep passing unchanged. `BoardRow` is not constructed directly in tests [VERIFIED: grep `BoardRow(` in tests/services/test_train_leaderboard.py → none].

The viewer's own row (hidden or public) gets their tally because their key is visible. A guest ghost row gets zero (no rows). Tentative rows show tallies (demo scenario). An "Anonymous" (no-username) row shows its tally.

Wire: `LeaderboardRow.medals: LeaderboardMedals` with `gold: int, silver: int, bronze: int`. `LeaderboardRow` is `from_attributes=True` [VERIFIED: app/schemas/train.py:451], so a nested dataclass `MedalTally(gold, silver, bronze)` validates directly.

### Pattern 6: Last-week block on `GET /train/leaderboard` (discretion: recommended over a separate endpoint)

Extend `LeaderboardBoard` (per board, D-09 places the podium per tab) with `last_week: LeaderboardLastWeek | None`:

```python
MedalKind = Literal["gold", "silver", "bronze"]

class LeaderboardPodiumEntry(BaseModel):
    medal: MedalKind
    name: str                       # read-time masked, see below

class LeaderboardLastWeek(BaseModel):
    week_start: date                # the previous Monday (UTC)
    podium: list[LeaderboardPodiumEntry]   # empty → no podium line (D-08)
    viewer_final_rank: int | None   # only when the viewer has a row there with medal NULL (D-03)
```

`last_week` is `None` when both `podium` is empty and `viewer_final_rank` is `None`. Why one endpoint: the card already fetches on mount with `refetchOnMount: 'always'` [VERIFIED: frontend/src/hooks/useTrainLeaderboard.ts:42]. The finalizer must run on this request anyway, and a second query would need its own loading/error branch.

One repository read for both boards:

```sql
SELECT s.board, s.medal, s.final_rank, s.puzzles, s.display_name, s.user_id, u.leaderboard_hidden
FROM train_weekly_standings s LEFT JOIN users u ON u.id = s.user_id
WHERE s.week_start = :prev_week AND (s.medal IS NOT NULL OR s.user_id = :viewer_id)
```

Pure `build_last_week(rows, viewer_id)` in the service applies the rules:
- name = `DELETED_USER_DISPLAY_NAME` if `user_id is None`; else `ANONYMOUS_DISPLAY_NAME` if `leaderboard_hidden` now **and** `user_id != viewer_id` (D-04: own data is not masked to oneself); else the stored `display_name`. The constant `ANONYMOUS_DISPLAY_NAME: Final = "Anonymous"` exists [VERIFIED: app/services/train_leaderboard.py:51].
- Podium order: medal asc (gold first), then puzzles desc, then stored `display_name.casefold()`. This mirrors the live tie order, which is puzzles desc then name (`_order_key` [VERIFIED: app/services/train_leaderboard.py:169-170]).
- `viewer_final_rank` = the viewer's row's `final_rank` iff it exists and `medal is None`.
- `prev_week = week_start - 7 days`. Before `MEDALS_START_WEEK`, and during the grace window, no rows exist, so the result is naturally `None` (D-07).

A guest viewer has no rows and gets no `viewer_final_rank`. The podium is still shown to guests: public data, and it costs nothing.

### Pattern 7: Unclaimed GET + claim POST (IDOR-scoped)

```python
@router.get("/medals/unclaimed", response_model=UnclaimedMedalsResponse)   # finalizer first, then read
@router.post("/medals/claim", status_code=204)                              # body: ClaimMedalsRequest

class UnclaimedMedal(BaseModel):
    week_start: date
    board: LeaderboardBoardKind
    medal: MedalKind
    value: int
    shared: bool                    # another row in the same week+board holds the same medal (D-11 "(shared)")

class MedalKey(BaseModel):
    week_start: date
    board: LeaderboardBoardKind

class ClaimMedalsRequest(BaseModel):
    medals: list[MedalKey] = Field(min_length=1, max_length=MAX_CLAIM_ITEMS)
```

- Unclaimed SQL: `WHERE user_id = :caller AND medal IS NOT NULL AND celebrated_at IS NULL`, with `shared` via `count(*) OVER (PARTITION BY week_start, board, medal) > 1` computed over the week's rows (subquery, or an `EXISTS` on another row with the same week/board/medal). Order: `week_start DESC`, then Points before Accuracy (explicit `CASE`, because `'accuracy' < 'points'` alphabetically).
- Claim SQL: `UPDATE ... SET celebrated_at = :now_utc WHERE user_id = :caller AND celebrated_at IS NULL AND (week_start, board) IN (...)`. The caller id comes only from `current_active_user.id`. A foreign or unknown key matches nothing (same IDOR shape as `fetch_session_contribution` [VERIFIED: app/repositories/train_leaderboard_repository.py:114-118]). Claiming the **shown keys** rather than "all unclaimed" avoids silently claiming a medal finalized between the GET and the tap. `now_utc` comes from `dev_now_utc`. Idempotent: re-claim is a no-op. A guest gets 204 with nothing to do.
- No row ids or user ids on the wire; `(week_start, board)` is the per-user natural key.
- Optional hardening: skip the dialog under admin impersonation on the client (`profile.impersonation` [VERIFIED: frontend/src/types/users.ts:36-38]), so an admin impersonating a user never consumes their celebration (see Pitfall 6).

### Pattern 8: Frontend seams (container + prop-driven views)

`TrainLeaderboardCard` already has internal subcomponents `LeaderboardRowItem`, `LeaderboardRows`, `LeaderboardTabs`, `LeaderboardHint`, `LeaderboardBoardView`, `LeaderboardGuestCta` and the hook `useLeaderboardCountdown` [VERIFIED: frontend/src/components/train/TrainLeaderboardCard.tsx:73-295]. Split it like this:

- `export function TrainLeaderboardCardView(props: { data?: TrainLeaderboardResponse; isPending: boolean; isError: boolean; remaining: number | null; tab: LeaderboardBoardKind; onTabChange: (v: string) => void; isGuest: boolean })`. It renders lines 314-340 verbatim from props.
- `TrainLeaderboardCard({ isGuest })` stays the thin container: `useTrainLeaderboard()`, `useLeaderboardCountdown`, tab state, `trackFeature`. It renders the view. `TrainStartScreen` call sites are unchanged.
- In `LeaderboardBoardView`: render `<LastWeekPodium lastWeek={data[tab].last_week} />` **first** (above the Accuracy helper, D-09). In `LeaderboardHint`, render the existing hint, then a separate `<p data-testid="train-leaderboard-last-week-finish">You finished #{n} last week</p>` when `data[tab].last_week?.viewer_final_rank` is a number (D-03).
- `MedalTally` goes inside the existing wrapping name block `<span className="flex min-w-0 flex-1 flex-wrap items-baseline gap-x-1">` [VERIFIED: TrainLeaderboardCard.tsx:115], as its own `whitespace-nowrap` item after the name (like the hidden cue). Only the name truncates (IN-02).
- Dialog host: `TrainMedalDialogHost({ isGuest })` uses `useUserProfile()` for `impersonation` and `useUnclaimedMedals({ enabled: !isGuest && !impersonating })` (`refetchOnMount: 'always'`), plus `useClaimMedals()`. It keeps a per-mount `closed` state so a refetch never reopens it in the same visit (D-13: failed POST → reappear on the **next** visit). It passes `muted={useMuted()}` and `reducedMotion={prefersReducedMotion()}`.
- **Mount it in `TrainStartScreen`'s rendered landing branches.** The real branches are `empty` (line 346), `completed` (355) and the default fresh/resume/warmup return (385) [VERIFIED: frontend/src/components/train/TrainStartScreen.tsx:330-407]. CONTEXT's "default and in-progress branch" maps to these. Recommend all three, not `loading`/`error`. `Train.tsx` renders `TrainStartScreen` only when the loop is not active, and the score screen is separate, so "never mid-session or on the score screen" holds by construction.

### Pattern 9: Claim gesture, sound, confetti, animation

APIs (read this session):
- `export function playSound(event: SoundEvent): void` checks `readMuted()` itself [VERIFIED: frontend/src/lib/sounds.ts:321-329]. `'game-win': 'WinChime'` [VERIFIED: sounds.ts:106].
- `export function unlockAudio(): void` resumes the Web Audio context and kicks a silent buffer inside the gesture, calling `requestPlaybackAudioSession()` [VERIFIED: sounds.ts:338-345].
- `export function useMuted(): boolean` [VERIFIED: sounds.ts:183].
- `export function fireWinConfetti(): void`, `export function prefersReducedMotion(): boolean`, `export const CONFETTI_DURATION_MS` [VERIFIED: frontend/src/lib/confetti.ts:47,82,100].

```tsx
// MedalClaimDialog (presentational; the demo renders exactly this)
function handleClaim(): void {
  unlockAudio();                          // inside the tap (iOS)
  if (!muted) playSound('game-win');      // once per tap (D-12)
  if (!reducedMotion) fireWinConfetti();  // canvas outlives the dialog
  onClaim(medals.map(toKey));             // container POSTs; demo is a no-op
}
<Dialog open={open} onOpenChange={(next) => { if (!next) onDismiss(medals.map(toKey)); }}>
  <DialogContent data-testid="train-medal-dialog"> ... <Button data-testid="btn-train-medal-claim" onClick={handleClaim}>Claim</Button>
```

- Radix `onOpenChange` fires only on user dismissal (X, Esc, outside click), not when the controlled `open` flips to false after Claim. So Claim and dismiss never double-POST [ASSUMED: Radix controlled-dialog semantics; cover with a test].
- The built-in X in `DialogContent` (`showCloseButton`) has no `data-testid` [VERIFIED: frontend/src/components/ui/dialog.tsx:62-74]. Either pass `showCloseButton={false}` and render an own close button with `data-testid="btn-train-medal-dialog-close"` and `aria-label="Close"`, or accept the primitive. Prefer the own button for browser-automation rules.
- Animation: add `@keyframes medal-pop` plus `.animate-medal-pop { animation: medal-pop 0.55s cubic-bezier(0.34, 1.4, 0.64, 1) both; }` in `index.css`, with a per-medal inline `animationDelay`. Use fill mode **`both`**, not `forwards` like `.animate-train-score-badge-pop` [VERIFIED: frontend/src/index.css:390-398]: with a delay, `forwards` shows the medal at rest before it pops. Omit the class entirely when `reducedMotion` (the component-level gate, as TrainScoreScreen does), and add the class to the `@media (prefers-reduced-motion: reduce)` block (index.css:535) as a second line of defense.
- Medal colors in `theme.ts`, hex/oklch like neighbours: `MEDAL_GOLD = 'oklch(0.80 0.15 85)'`, `MEDAL_SILVER = 'oklch(0.82 0.01 260)'`, `MEDAL_BRONZE = 'oklch(0.66 0.12 55)'`, and `MEDAL_COLORS: Record<MedalKind, string>` [ASSUMED: visual values, confirm in UAT on the dark card]. They tint the lucide icon via `style={{ color }}` and are not used for confetti, so `CONFETTI_COLORS`' hex-only constraint does not apply.
- Week label: `Week of ${format(parseISO(week_start), 'MMM d')}`, the same date-fns call TrainStartScreen uses. **Never `new Date('2026-10-05')`**: that parses as UTC midnight and renders the Sunday in the Americas.

### Pattern 10: Admin demo (client-only, prod-safe)

- New section in `pages/Admin.tsx` **outside** the `import.meta.env.DEV` gate. That gate exists only because the reminder endpoint 404s in prod [VERIFIED: frontend/src/pages/Admin.tsx:43-56]. Section `data-testid="admin-section-leaderboard-medals-demo"`, heading "Leaderboard medals demo", using the `charcoal-texture rounded-md p-4 space-y-3` card pattern of `TrainReminderTestCard` [VERIFIED: frontend/src/components/admin/TrainReminderTestCard.tsx:29-31].
- `LeaderboardMedalsDemo` renders `TrainLeaderboardCardView`, `LastWeekPodium` (through the view) and `MedalClaimDialog` with fixtures typed as the real wire types (`TrainLeaderboardResponse`, `UnclaimedMedal[]`), so tsc catches drift. Claim/dismiss callbacks only close the demo dialog: no POST, no query hooks.
- Scenario buttons (seed list): celebrate gold/silver/bronze Points, gold Accuracy, gold+bronze both boards, three unclaimed weeks, shared gold. Board states: tallies none / one type / all three two-digit, long names, tentative + tally, Anonymous + tally, podium tie, podium Deleted user, viewer finished #12. Plus a 375 px frame toggle (`max-w-[375px]`) and **simulated** toggles: `muted` and `reducedMotion` booleans passed as props.
- Caveat: `playSound` also checks the real persisted mute pref, so "simulated unmuted" is silent if the admin's real pref is muted. State that in the demo helper text. Likewise the CSS media-query fallback still stops the animation when the OS reduces motion.
- `/admin` is excluded from Umami, so no events are sent [CITED: frontend/CLAUDE.md].

### Pattern 11: Copy

- `LeaderboardPrivacyCard` `HIDE_HELPER` [VERIFIED: frontend/src/components/settings/LeaderboardPrivacyCard.tsx:7-8 `'Your username and weekly Train results stay off the leaderboards other people see. You still see your own position.'`]: append one sentence, e.g. "While hidden you don't earn medals; medals you already won are kept." (locked: one line saying hidden users don't earn medals).
- `Privacy.tsx` already describes the leaderboard at line 29 [VERIFIED: grep]. Recommend one added sentence: final weekly standings are stored so past medals and podiums stay fixed, and on account deletion the name is replaced with "Deleted user". This keeps the "we will delete ... any associated data" promise (line 76) honest.

### Anti-Patterns to Avoid
- **Deriving medals from `final_rank <= 3`** (locked: never). Store `medal` explicitly from `medal_for`.
- **A second ranking implementation** for the snapshot (D-02). Use `_tiered_order` only.
- **Masking at finalization time** for opt-out: masking is read-time ("Anonymous" when hidden *now*). Only *eligibility* is decided at finalization.
- **Exposing user ids or row ids** for tallies or claims. Use internal keys server-side and the `(week_start, board)` natural key for claims.
- **Concurrent queries on one session** (`asyncio.gather`): forbidden. Two *separate* sessions in a concurrency test are fine.
- **Claiming "all unclaimed"** on POST instead of the shown keys.
- **Calling `datetime.now()`** in the finalizer or claim. Use the `now_utc` argument.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Past-week ranking | New sort/rank code | `_entry_for` + `_tiered_order` (+ `_competition_ranks`) | D-02; tie and tier rules already amended by quick 261004-8rt |
| Week boundaries | Date math | `week_window(now_utc)` [VERIFIED: train_leaderboard.py:109-114] | UTC ISO Monday half-open window, already tested |
| Weekly aggregates | New SQL | `fetch_week_aggregates(session, week_start, week_end)` | Same scoring CASE, filler filter and visibility fields |
| Finalization mutex | `pg_advisory_xact_lock` | Marker-table unique insert `ON CONFLICT DO NOTHING RETURNING` | Probed: waits for commit and returns 0 rows; also remembers empty weeks |
| Deletion erasure | App-level delete hook | `BEFORE UPDATE OF user_id` trigger | No app deletion path exists; manual SQL must still erase |
| Audio unlock / mute | Custom `<audio>` handling | `unlockAudio`, `playSound`, `useMuted` | iOS audio-session and sample-rate traps already solved (memory) |
| Confetti | New canvas code | `fireWinConfetti` | Hex palette and duration constants owned |
| Dialog | Custom modal | `components/ui/dialog.tsx` | Focus trap, Esc, outside click |

**Key insight:** the only genuinely new logic is `medal_for`, the due-week loop, and the read-time masking. Everything else is wiring existing, tested pieces together.

## Common Pitfalls

### Pitfall 1: In-flight solves at the deadline
**What goes wrong:** A solve request reads `now_utc` = Sun 23:59:59.9 and commits at Mon 00:00:00.4. A finalizer that ran at 00:00:00.2 misses it, and a close medal race is decided wrong forever (the snapshot is permanent).
**Why it happens:** `solved_at` is the request's start time, but visibility is commit time.
**How to avoid:** a week is due only when `now_utc >= week_end + MEDALS_FINALIZE_GRACE` (recommend 5 minutes; `due_weeks` uses `week_window(now_utc - grace)`). The cost: the podium and dialog appear a few minutes after Monday 00:00. The card's WR-03 rollover refetch at the deadline shows the new week without a podium, and the podium appears on the next mount or refetch. That is acceptable.
**Warning signs:** a test that pins `now` to exactly `week_end` and expects finalization. Pin to `week_end + grace`.

### Pitfall 2: Global state vs. test isolation
**What goes wrong:** finalization is global and permanent. Any request with a later pinned `now` finalizes every earlier week, including a week another test is about to seed. With the marker table that week is then "finalized empty" and the medal test sees nothing. Phase 230 router tests pin `now` in 2032 (`BASE_MONDAY = datetime.datetime(2032, 1, 5, ...)` [VERIFIED: tests/routers/test_train_leaderboard.py:52]), so their first GET per worker will finalize about 274 weeks (2026-10-05 to 2032-01-05). That is a one-time cost of well under a second, and it leaves snapshot rows that the Phase 230 tests then anonymize by deleting their users.
**How to avoid:** new medal tests (a) use their own base Monday (e.g. `2033-01-03`, verified Monday) plus a per-test k table like Phase 230's, (b) `monkeypatch.setattr(train_medals, "MEDALS_START_WEEK", own_week)` so finalization touches only their week, (c) delete their week's marker and standings rows **before** seeding and in `finally`, and (d) delete their users in `finally`. Repository tests on the rollback-scoped `db_session` are safe even if code commits: SQLAlchemy's default join mode makes `session.commit()` not commit an externally begun transaction ("rollback_only": "`.commit()` calls will not be propagated to the given transaction" [CITED: docs.sqlalchemy.org/en/20/orm/session_api.html]).
**Warning signs:** a medal test that passes alone and fails under `-n auto` or in serial CI (memory: serial CI hides isolation bugs).

### Pitfall 3: Response key-set and fixture drift
**What goes wrong:** `test_response_key_set_has_no_user_ids` asserts exact key sets: `{"rows", "viewer", "pass_target"}` per board and an exact row key set [VERIFIED: tests/routers/test_train_leaderboard.py:269-285]. Frontend fixtures (`makeRow`/`makeResponse` in `TrainLeaderboardCard.test.tsx`, the `getLeaderboard` mock in `pages/__tests__/Train.solveLoop.test.tsx:190-197`) lack `medals`/`last_week`. Tests are excluded from tsc, so this fails only at runtime (`row.medals.gold` on undefined).
**How to avoid:** update these in the same plan that changes the schema. Add `last_week` and `medals` to the key-set test, still with no `user_id`/`id`/`email`.

### Pitfall 4: New landing fetch breaks existing landing tests
**What goes wrong:** `Train.solveLoop.test.tsx` replaces `trainApi` with an explicit object [VERIFIED: pages/__tests__/Train.solveLoop.test.tsx:203-219], so `trainApi.getUnclaimedMedals` is undefined and throws inside the host's query. `TrainStartScreen.test.tsx` mocks `TrainLeaderboardCard` (line 162) and `useUserProfile` (line 47) but not the new host.
**How to avoid:** add `getUnclaimedMedals: vi.fn(async () => ({ medals: [] }))` and `claimMedals: vi.fn()` to that mock, and mock `TrainMedalDialogHost` (or `useTrainMedals`) in `TrainStartScreen.test.tsx`, plus one positive test that it mounts on each landing branch.

### Pitfall 5: Dev clock writes permanent finalizations
**What goes wrong:** shifting the dev clock forward past a deadline finalizes the real current week with partial data. Returning to the real clock leaves its marker, so it is never re-finalized. Same family as the documented dev-clock caveat [VERIFIED: app/core/dev_clock.py:32-36].
**How to avoid:** dev-only. Document the cleanup (`DELETE FROM train_weekly_finalizations WHERE week_start >= ...; DELETE FROM train_weekly_standings WHERE week_start >= ...`) in the plan's UAT notes. Do not gate anything on a DB reset (memory). Production is unaffected: `dev_now_utc` is the real clock outside development.

### Pitfall 6: Impersonation consumes a user's celebration
**What goes wrong:** an admin impersonating a user opens Train, the dialog shows the user's medals, dismissing POSTs the claim, and the real user never sees the celebration.
**How to avoid:** host disabled when `profile.impersonation !== null` [VERIFIED: frontend/src/types/users.ts:38].

### Pitfall 7: Opt-out masking applied to the viewer themselves
**What goes wrong:** a hidden-now medallist sees their own podium name as "Anonymous", contradicting D-04.
**How to avoid:** mask only when `user_id != viewer_id`. Add a unit test.

### Pitfall 8: `week_start` timezone rendering
`TrainLeaderboardResponse.week_start` is a `datetime`, but the new fields are `date`. On the client, use `parseISO` for date-only strings (local midnight), never `new Date(...)`.

### Pitfall 9: Gates
`ty`: `Medal` ↔ `MedalKind` via an explicit `dict[Medal, MedalKind]`, Literal returns, `Sequence[...]` params, explicit return types. `rowcount` on DML results needs the existing `# ty: ignore[unresolved-attribute]` pattern if used [VERIFIED: train_repository.py near line 3004]. Nesting depth: keep the due-week loop flat (`continue` on lost claims). Knip: every new export (view, demo fixtures, hooks) must be imported. `text-sm` floor in tally counts and podium.

### Pitfall 10: First production week
`MEDALS_START_WEEK = 2026-10-05`, so the first finalization happens at or after 2026-10-12 00:05 UTC (with grace). If the phase deploys later, the first request finalizes that week late, using then-current opt-out flags (accepted). Before then the UI must render nothing (no podium, no dialog, all tallies zero). Unit-test the empty state.

## Code Examples

### Repository: claim a week, insert standings (pattern from existing `on_conflict_do_nothing` use)
```python
# Source: app/repositories/game_repository.py:64 (constraint= form), train_repository.py:342 (index_elements= form)
from sqlalchemy.dialects.postgresql import insert as pg_insert

async def claim_week(session: AsyncSession, *, week_start: date) -> bool:
    stmt = (
        pg_insert(TrainWeeklyFinalization)
        .values(week_start=week_start)
        .on_conflict_do_nothing(index_elements=["week_start"])
        .returning(TrainWeeklyFinalization.week_start)
    )
    return (await session.execute(stmt)).scalar_one_or_none() is not None

async def insert_standings(session, *, week_start, rows) -> None:
    if not rows:
        return
    stmt = pg_insert(TrainWeeklyStanding).values([...]).on_conflict_do_nothing(
        constraint="uq_train_weekly_standings_week_board_user"
    )
    await session.execute(stmt)
```

### Router: finalize, then serve (Sentry rule, router commits)
```python
try:
    await finalize_due_weeks(session, now_utc=now_utc)
    await session.commit()
except Exception:
    await session.rollback()
    sentry_sdk.set_context("train", {"user_id": str(user.id)})
    sentry_sdk.capture_exception()
# then the existing get_weekly_leaderboard(...) path, unchanged in shape
```

### Wire types (frontend `types/train.ts`, hand-written mirror of `app/schemas/train.py`)
```ts
export type MedalKind = 'gold' | 'silver' | 'bronze';
export interface LeaderboardMedals { gold: number; silver: number; bronze: number; }
export interface LeaderboardPodiumEntry { medal: MedalKind; name: string; }
export interface LeaderboardLastWeek { week_start: string; podium: LeaderboardPodiumEntry[]; viewer_final_rank: number | null; }
// LeaderboardRow gains `medals: LeaderboardMedals`; LeaderboardBoard gains `last_week: LeaderboardLastWeek | null`.
export interface UnclaimedMedal { week_start: string; board: LeaderboardBoardKind; medal: MedalKind; value: number; shared: boolean; }
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Tentative Accuracy entries ranked and interleaved | Qualified first (ranked), tentative unranked below | quick 261004-8rt, c0499df76 (2026-10-04, released #385) | Snapshot skips rank-None entries directly |
| SEED-185: WR-01 must close before medals | WR-01 accepted for medals | Owner 2026-10-04 | Do not touch scoring |

Note: STATE.md still says Phase 230 is "not yet squash-merged". That is stale: `13270c110 feat(230)` and release `#384` are on `main`/`production` [VERIFIED: git log].

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | PG `ON DELETE SET NULL (col_list)` can only list FK columns, so it cannot null/erase `display_name` | Pattern 4 | Low. The trigger is the recommendation either way, and the probe proves it works |
| A2 | Radix controlled Dialog does not fire `onOpenChange(false)` when `open` is set false programmatically | Pattern 9 | Double POST (harmless, idempotent). Cover with a test |
| A3 | 5-minute finalize grace is enough for in-flight solve transactions | Pitfall 1 | A medal decided by a solve committed later than 5 min after its start (practically impossible) |
| A4 | Medal oklch values read well on the dark card | Pattern 9 | Cosmetic. Tune in UAT via the demo |
| A5 | `unlockAudio()` then `playSound()` in the same tap plays on a cold page load (iOS included) | Pattern 9 | Silent first Claim on some devices. Verify on a real phone in UAT (memory: iOS audio-session) |
| A6 | Showing the podium to guests is fine (public data) | Pattern 6 | Product preference only |
| A7 | Table names `train_weekly_standings` / `train_weekly_finalizations` | Pattern 3 | Naming only |

## Open Questions (RESOLVED)

All three fall under CONTEXT.md "Claude's Discretion" (finalization trigger and concurrency) or are product preferences with a cheap reversal; the planner adopted each recommendation (recorded in 231-01-PLAN.md "Decision coverage", row "Discretion").

1. **Grace length (A3).** Recommendation: 5 minutes, as a named constant. The owner may prefer 1 minute for a snappier Monday podium.
   **RESOLVED:** 5 minutes. `MEDALS_FINALIZE_GRACE = timedelta(minutes=5)` in `app/services/train_medals.py` (231-01 Task 1), grace-boundary tests at 00:04:59 / 00:05:00 UTC (231-01 Task 2). Changing it later is a one-constant edit.
2. **Marker table vs. recompute.** Recommended: the marker table (lock + memory + test isolation). If the owner wants a single table, the fallback is recomputing weeks with no standings rows on every request, plus an advisory lock for concurrency.
   **RESOLVED:** marker table `train_weekly_finalizations`, no advisory lock. Its primary-key insert (`ON CONFLICT DO NOTHING RETURNING`) serializes concurrent finalizers and remembers empty weeks (231-01 Task 1); the concurrency and empty-week guarantees are proven in 231-06.
3. **Podium for guests.** Recommended: show it. Trivial to hide if the owner disagrees.
   **RESOLVED:** shown to guests (public data). The 231-01 tracer test asserts a guest GET returns the same Points podium with `viewer_final_rank` null.

## Environment Availability

| Dependency | Required By | Available | Version | Fallback |
|------------|------------|-----------|---------|----------|
| PostgreSQL (dev docker `flawchess-dev-db-1`) | migration, trigger, tests | ✓ | 18.3 | — |
| Python / uv | backend, pytest, ty | ✓ | 3.14.3 / uv 0.10.9 | — |
| Node | frontend build/test | ✓ | v24.19.0 | — |
| lucide-react `Medal` | tally/dialog icon | ✓ | 1.41.0 | — |

**Missing dependencies:** none.

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (backend, per-run cloned DB from a migrated template); vitest + Testing Library (frontend) |
| Config file | `pyproject.toml`, `tests/conftest.py`; `frontend/vite.config.ts` (test block), `frontend/src/vitest.setup.ts` |
| Quick run command | `uv run pytest tests/services/test_train_leaderboard.py tests/services/test_train_medals.py -x` |
| Full suite command | `uv run pytest -n auto -x` and `( cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip )` |

The template DB auto-refreshes when the Alembic head changes, so the trigger and tables exist in tests without manual steps. If a migration is edited **in place** without a new revision id during development, the template will not refresh. Bump the revision or drop `flawchess_test_template`.

### Phase Requirements → Test Map
| Req (derived) | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| SNAP / D-01 | public-only rows; Accuracy qualified-only; hidden/guest/tentative excluded | unit (DB-free) | `uv run pytest tests/services/test_train_leaderboard.py -k final_standings -x` | ✅ file, ❌ tests |
| D-02 / D-06 | ranks equal live-board ranks; Olympic 1,1,3 / 1,2,2 / 1,1,1 | unit | `... -k "final_standings or medal_for"` | ❌ |
| D-05 | 0 pts / 0% gets a row + rank, `medal` None | unit | `... -k medal_for` | ❌ |
| FINAL due weeks | start week, grace boundary, skips finalized, ascending | unit | `uv run pytest tests/services/test_train_medals.py -k due_weeks -x` | ❌ Wave 0 |
| FINAL idempotent | second call inserts nothing; empty week gets a marker | repository (real DB) | `uv run pytest tests/repositories/test_train_medals_repository.py -k finalize -x` | ❌ Wave 0 |
| FINAL concurrency | two separate sessions finalize concurrently → one marker, no duplicate rows | repository/integration | `... -k concurrent` | ❌ |
| DEL | delete user → `user_id` NULL, `display_name` "Deleted user"; trigger exists in `pg_trigger` | repository | `... -k "deleted or trigger"` | ❌ |
| TALLY | grouped counts per board for visible keys only; zero for guests; no ids in payload | unit + router | `uv run pytest tests/services/test_train_leaderboard.py -k tally -x`; `uv run pytest tests/routers/test_train_medals.py -k tally -x` | ❌ |
| PODIUM / D-07..D-09 | prev week only; none before start/grace; Anonymous if hidden now (not for self); Deleted user; tie order | unit + router | `... -k "last_week or podium"` | ❌ |
| FINISH / D-03 / D-04 | line only for own non-medal row; hidden-now viewer still sees own line | unit + router | `... -k viewer_final_rank` | ❌ |
| CLAIM | unclaimed ordering (week desc, points first), `shared`; claim scoped to caller (foreign key no-op), idempotent; guest 204 | router | `uv run pytest tests/routers/test_train_medals.py -k "unclaimed or claim" -x` | ❌ Wave 0 |
| Key-set (no ids) | response keys include `medals`/`last_week`, never `user_id`/`id`/`email` | router | `uv run pytest tests/routers/test_train_leaderboard.py::test_response_key_set_has_no_user_ids` | ✅ (update) |
| TALLY UI | non-zero types only, order gold/silver/bronze, aria-label "3 gold, 1 silver Points medals", in name block | component | `cd frontend && npx vitest run src/components/train/medals` | ❌ |
| PODIUM UI | above helper; hidden when `last_week` null or podium empty; tied names | component | `npx vitest run src/components/train/__tests__/TrainLeaderboardCard.test.tsx` | ✅ (extend) |
| FINISH UI | second hint line below existing hint | component | same | ✅ (extend) |
| DIALOG D-10..D-13 | title count, entry text, newest first; Claim → unlockAudio + playSound once + confetti (not when reducedMotion/muted) + onClaim(keys); dismiss → onDismiss, no sound/confetti; no reopen in the same mount; not for guests/impersonation | component | `npx vitest run src/components/train/medals/__tests__/MedalClaimDialog.test.tsx` and `.../TrainMedalDialogHost.test.tsx` | ❌ |
| Landing mount | host on empty/completed/default branches | component | `npx vitest run src/components/train/__tests__/TrainStartScreen.test.tsx` | ✅ (extend + mock) |
| DEMO | renders real components; scenario buttons; no API calls | component | `npx vitest run src/components/admin/__tests__/LeaderboardMedalsDemo.test.tsx` | ❌ |
| Pure copy | `tallyAriaLabel`, `weekOfLabel` (parseISO), `dialogTitle` | unit | `npx vitest run src/lib/trainMedals.test.ts` | ❌ |
| Real-device audio/visual | first-tap sound on iOS, colors on dark card, 375 px wrap | manual UAT | via the admin demo in dev and prod | n/a |

### Sampling Rate
- **Per task commit:** the targeted command(s) for the touched area above.
- **Per wave merge:** `uv run pytest tests/services tests/repositories tests/routers -n auto -k "leaderboard or medal"` and `cd frontend && npm test -- --run src/components/train src/components/admin src/lib`.
- **Phase gate:** the full pre-merge gate from CLAUDE.md, green before `/gsd-verify-work`. Also run the full **serial** backend suite once (memory: serial CI hides isolation bugs).

### Wave 0 Gaps
- [ ] `tests/services/test_train_medals.py`: `due_weeks` pure tests (start week, grace, finalized skip).
- [ ] `tests/repositories/test_train_medals_repository.py`: claim_week, insert_standings, tallies, last-week rows, unclaimed, claim, trigger. Own week base (e.g. `2033-01-03`) + k table + pre/post cleanup of the week's marker/standings.
- [ ] `tests/routers/test_train_medals.py`: end-to-end via `pin_now` + `monkeypatch MEDALS_START_WEEK`.
- [ ] Update `tests/routers/test_train_leaderboard.py` key-set test.
- [ ] Frontend fixture updates: `TrainLeaderboardCard.test.tsx` (`medals`, `last_week`), `Train.solveLoop.test.tsx` (`getUnclaimedMedals`, `claimMedals`, `last_week: null` in boards), `TrainStartScreen.test.tsx` (mock host).
- [ ] New frontend test files listed in the map.

## Security Domain

### Applicable ASVS Categories

| ASVS Category | Applies | Standard Control |
|---------------|---------|-----------------|
| V2 Authentication | yes | `current_active_user` (FastAPI-Users JWT), already on all `/train` routes |
| V3 Session Management | no | unchanged |
| V4 Access Control | yes | Claim/unclaimed scoped by `current_active_user.id` only (IDOR); no client-supplied user id |
| V5 Input Validation | yes | Pydantic: `date`, `Literal["points","accuracy"]`, `Field(min_length=1, max_length=MAX_CLAIM_ITEMS)` |
| V6 Cryptography | no | — |
| V8 Data Protection / Privacy | yes | No user ids on the wire; read-time "Anonymous" for hidden-now; trigger-based erasure on deletion |

### Known Threat Patterns

| Pattern | STRIDE | Standard Mitigation |
|---------|--------|---------------------|
| Claiming or reading another user's medals (IDOR) | Elevation / Info disclosure | `WHERE user_id = :caller`; foreign keys match nothing; 204 regardless |
| Hidden user's name leaking via podium | Info disclosure | Read-time mask from current `leaderboard_hidden`; podium carries no ids |
| User enumeration via tallies | Info disclosure | Tallies only for already-visible rows, keyed internally |
| Deleted user's name persisting (GDPR) | Info disclosure | `BEFORE UPDATE OF user_id` trigger + read-time rule |
| Stored XSS via usernames on podium/dialog | Tampering | Render as React text children only (T-230-08 precedent) |
| Score manipulation to win medals (WR-01) | Tampering | **Accepted risk** (owner 2026-10-04). Do not fix |
| DoS via repeated finalization | DoS | Fast path is 1 SELECT; marker insert serializes the rest |

## Sources

### Primary (HIGH confidence)
- In-repo files read this session: `app/services/train_leaderboard.py`, `app/repositories/train_leaderboard_repository.py`, `app/schemas/train.py:436-530`, `app/routers/train.py:1-62,260-312`, `app/models/drill_solve.py`, `app/core/dev_clock.py`, `app/services/guest_cleanup_service.py`, `app/routers/auth.py`, `app/models/user.py`, `alembic/env.py`, `alembic.ini`, latest migrations, `tests/conftest.py`, Phase 230 tests, `frontend/src/components/train/TrainLeaderboardCard.tsx`, `TrainStartScreen.tsx`, `lib/trainLeaderboard.ts`, `lib/confetti.ts`, `lib/sounds.ts`, `lib/theme.ts`, `components/ui/dialog.tsx`, `pages/Admin.tsx`, `components/admin/TrainReminderTestCard.tsx`, `components/settings/LeaderboardPrivacyCard.tsx`, `pages/Privacy.tsx`, `docs/production-runbook.md`, `frontend/CLAUDE.md`.
- Live PostgreSQL 18.3 probes (dev docker): FK `SET NULL` fires a `BEFORE UPDATE OF` trigger; concurrent `INSERT ... ON CONFLICT DO NOTHING RETURNING` waits for the first committer and returns 0 rows.

### Secondary (MEDIUM confidence)
- SQLAlchemy 2.0 Session API, `join_transaction_mode` ("rollback_only" commit semantics): https://docs.sqlalchemy.org/en/20/orm/session_api.html

### Tertiary (LOW confidence)
- None used.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH. No new packages; all APIs read in-repo.
- Architecture: HIGH. Reuse points verified line by line; both DB behaviours probed live.
- Pitfalls: HIGH for test isolation and fixture drift (verified against existing tests); MEDIUM for real-device audio (A5).

**Research date:** 2026-10-04
**Valid until:** 2026-11-03 (stable in-repo domain; re-check the Alembic head at plan time)
