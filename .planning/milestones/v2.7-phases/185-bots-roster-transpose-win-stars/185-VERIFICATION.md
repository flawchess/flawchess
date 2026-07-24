---
phase: 185-bots-roster-transpose-win-stars
verified: 2026-07-22T18:55:00Z
status: passed
score: 12/13 must-haves verified
behavior_unverified: 0
overrides_applied: 0
human_verification:
  - test: "No-row-labels legibility backstop: open /bots and visually confirm each card's own ~ELO/calibratedLabel is enough to tell which rung a row belongs to, without a row label (personas in a row share ~800/~1000/etc modulo per-persona calibration offsets)"
    expected: "A user can scan the 6 rows and identify the rung of each purely from the cards' own ELO text, without needing a row label/gutter"
    why_human: "185-02-PLAN.md explicitly marks this must-have `verification: backstop` — a visual-scan/legibility judgment, not something a DOM assertion can prove. 185-02-SUMMARY.md itself records `human_judgment: true` with no automated evidence for this item."
  - test: "Open /bots at a 320px-wide viewport (or the mobile drawer) and confirm all 4 style header names (Attacker/Trickster/Grinder/Wall) render on one line at text-sm with no wrapping/clipping"
    expected: "All 4 header cells display their full style name without truncation or overlap at the narrowest supported width"
    why_human: "No automated test exercises a specific viewport width (jsdom does not lay out real column widths); the header cells have no `truncate`/`whitespace-nowrap` class, so a too-narrow column would wrap rather than silently truncate, but whether it visually fits at 320px is a rendering judgment, not a DOM/CSS-source fact."
  - test: "Play and finish a real persona bot game (a win), return to the roster ('New game'), and confirm a gold star appears on that persona's card without a full page reload"
    expected: "The star count updates in the same session immediately after the game, reflecting the CR-01 cache-invalidation fix"
    why_human: "Full user-flow / real-time behavior needing a live backend + browser session; covered by unit-level mutation-verified tests (see below) but not by an actual played game."
gaps: []
---

# Phase 185: Bots roster transpose + win stars Verification Report

**Phase Goal:** Bots page follow-ups to Phase 184: (1) transpose PersonaGrid to 6 rung rows (800 top) x 4 style columns with a single accent-colored header row, no row labels; (2) PersonaCard gains a bottom stars row; (3) server-side per-persona win tracking — nullable `persona_id` on `StoreBotGameRequest`/`games` (persona games only, custom stays NULL), a win-aggregation endpoint, frontend renders min(wins,3) gold + grey-outline stars.
**Verified:** 2026-07-22T18:55Z
**Status:** passed (human verification confirmed via 185-UAT.md, all 3 items passed)
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | A finished persona game's `persona_id` persists to `games.persona_id`; custom-mode games (omitted/None) stay NULL | VERIFIED | `app/services/store_bot_game_service.py:189-195` writes only inside the existing `if created:` gate; `tests/routers/test_bots.py::test_persona_id_persisted_on_create` and `::test_persona_win_round_trips_to_persona_wins_endpoint` pass (ran live: 33/33 in the scoped test files) |
| 2 | `GET /bots/persona-wins` returns per-user win-only, non-NULL-persona counts | VERIFIED | `app/repositories/game_repository.py::count_wins_by_persona` — verbatim `win_cond`, `persona_id.is_not(None)`, `platform=="flawchess"`, now with `.having(win_count > 0)` (WR-01 fix, confirmed present in source); `tests/repositories/test_game_repository_persona_wins.py::TestCountWinsByPersona` (8 cases incl. `test_persona_with_only_losses_is_absent_not_zero`) — ran live, passed |
| 3 | Overlong (>30 char) and empty-string `persona_id` are rejected with 422 at the Pydantic boundary | VERIFIED | `app/schemas/bots.py:57` — `Field(default=None, min_length=1, max_length=_MAX_PERSONA_ID_LENGTH)` (WR-03 fix present in source); `test_persona_id_over_max_length_rejected` + `test_persona_id_empty_string_rejected` ran live, passed |
| 4 | `GET /bots/persona-wins` requires auth; user_id derives only from JWT (no cross-user leakage) | VERIFIED | `app/routers/bots.py:43` route uses the same `current_active_user`+session dependency pair, no user_id param; `test_persona_wins_requires_auth` + `test_persona_wins_scoped_to_authenticated_user` pass |
| 5 | Duplicate resubmit of the same `game_uuid` does not re-write `persona_id` (D-11) | VERIFIED | Write occurs only in the `if created:` branch; `test_persona_id_unchanged_on_idempotent_resubmit` passes |
| 6 | Migration adds a nullable column with no backfill/`server_default` (pre-existing games earn nothing) | VERIFIED | `alembic/versions/20260722_160246_411a8de89c4b_add_persona_id_to_games.py` — `upgrade()` is a single `op.add_column(..., nullable=True)`, `downgrade()` a bare `op.drop_column`; no `UPDATE`/`server_default`/`op.execute` in the operational code |
| 7 | Bots roster renders 6 rung rows (800 top -> 1800 bottom) x 4 style columns, one accent-colored header row, no row labels | VERIFIED | `frontend/src/components/bots/PersonaGrid.tsx` — single `grid grid-cols-4` container, header row of 4 `STYLE_ACCENT`-colored cells + `RUNGS.flatMap(personasForRung)` body, no row-label markup; `PersonaGrid.test.tsx` header-row + DOM-order tests pass (ran live) |
| 8 | Persona-card DOM order is rung-major (rung 800's 4 personas, then 1000, ... to 1800) | VERIFIED | Test asserts `actualIds === RUNGS.flatMap((rung) => personasForRung(rung).map(...))` mapped to testids — ran live, passed; mutation-verified per 02-SUMMARY (reverting to style-major iteration was confirmed to fail this exact assertion) |
| 9 | All 4 style header names fit at text-sm in the header row down to a 320px viewport with no truncation | ⚠️ PRESENT_BEHAVIOR_UNVERIFIED | Header cells use `text-sm font-semibold` with no `truncate`/`whitespace-nowrap`/fixed-width class (so worst case is wrap, not silent clipping), but no automated test exercises an actual 320px layout — jsdom does not perform real box-model layout. Routed to human verification. |
| 10 | Every one of the 6 rung rows renders exactly 4 personas (no missing-cell state) | VERIFIED | `personasForRung` is `STYLE_SECTION_ORDER.map(...)` over a `Record<PersonaId, Persona>`-backed registry (exhaustive by construction, no optional lookup); test asserts exactly 24 total cards |
| 11 | PersonaCard renders `min(wins, 3)` gold-filled stars + grey-outline remainder, capped at 3 | VERIFIED | `PersonaCard.tsx`'s `PersonaStars` — `filledCount = Math.min(winCount, MAX_DISPLAY_STARS)`; 8 win-stars tests in `PersonaCard.test.tsx` (overflow, 1-filled, zero, undefined, aria-label separation, singular "1 win", mutation-check) all ran live and passed |
| 12 | Win counts fetched once at `Bots.tsx` page level via `useBotPersonaWins`, prop-drilled through `PersonaGrid` -> `PersonaCard`; no `useQuery` inside either component | VERIFIED | `grep useQuery PersonaGrid.tsx PersonaCard.tsx` — 0 real calls (1 doc-comment mention only, confirmed by reading the line); `Bots.tsx:540` — single `useBotPersonaWins()` call |
| 13 | A finished persona game's `persona_id` is sent on the store request; old queued localStorage entries missing the field still round-trip | VERIFIED | `useStoreBotGame.ts`'s `toStoreRequest` adds `persona_id: entry.settings.personaId ?? null`; `isValidPendingEntry` NOT tightened (grep confirms no new required-field check); `useStoreBotGame.test.ts` mapping tests pass |

**Score:** 12/13 truths verified (1 present, behavior-unverified — routed to human verification alongside 2 additional visual/live-session items)

### No-Row-Labels Legibility Backstop (Step 3b/5b)

This must-have was explicitly declared `verification: backstop` in 185-02-PLAN.md's frontmatter, and 185-02-SUMMARY.md records `human_judgment: true` with `verification: []` (no automated evidence). Per the honest-verifier contract this abstains from a pass/fail programmatic verdict and is carried to human verification below rather than silently marked VERIFIED.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `alembic/versions/20260722_160246_411a8de89c4b_add_persona_id_to_games.py` | nullable String(30), no backfill | VERIFIED | Read directly; `upgrade()`/`downgrade()` match exactly |
| `app/models/game.py` | `Game.persona_id` mapped column | VERIFIED | `persona_id: Mapped[str \| None] = mapped_column(String(30), nullable=True)` |
| `app/schemas/bots.py` | `StoreBotGameRequest.persona_id`, `_MAX_PERSONA_ID_LENGTH`, `PersonaWinsResponse` | VERIFIED | All three present; `min_length=1` fix confirmed |
| `app/repositories/game_repository.py` | `update_bot_game_persona_id` + `count_wins_by_persona` | VERIFIED | Both present; `count_wins_by_persona` has the WR-01 `.having()` fix |
| `app/routers/bots.py` | `GET /bots/persona-wins` route | VERIFIED | Present, `current_active_user`-scoped, no `user_id` param |
| `frontend/src/lib/personas/personaRegistry.ts` | `RUNGS`, `personasForRung` exports | VERIFIED | Both exported, mirror `personasForSection`'s abstraction level |
| `frontend/src/components/bots/PersonaGrid.tsx` | transposed layout + header testids | VERIFIED | `bots-persona-header-{style}` present, no leftover `bots-persona-section-*` |
| `frontend/src/lib/theme.ts` | `STAR_FILLED`/`STAR_EMPTY` | VERIFIED | Present as independent named constants, not aliased to `FLAWCHESS_ENGINE_ACCENT` |
| `frontend/src/hooks/useBotPersonaWins.ts` | new hook | VERIFIED | Present; `BOT_PERSONA_WINS_QUERY_KEY` exported (CR-01 fix); `queryFn` calls `botsApi.getPersonaWins()` (WR-02 fix, not duplicated) |
| `frontend/src/components/bots/PersonaCard.tsx` | `PersonaStars` + `winsForPersona` prop | VERIFIED | Present, matches UI-SPEC exactly |

### Key Link Verification

| From | To | Via | Status | Details |
|------|-----|-----|--------|---------|
| `store_bot_game_service.py`'s `if created:` block | `update_bot_game_persona_id` | direct call, gated on `request.persona_id is not None` | WIRED | Confirmed in source; idempotency test passes |
| `count_wins_by_persona` | `stats_repository`'s `win_cond` | verbatim copy | WIRED | Byte-identical `or_(and_(...), and_(...))` expression confirmed |
| `PersonaGrid.tsx` | `RUNGS`/`personasForRung` | rows-outer, cols-inner iteration | WIRED | `RUNGS.flatMap((rung) => personasForRung(rung))` — no manual `Object.values` sort |
| `Bots.tsx`'s `useBotPersonaWins()` | `PersonaGrid` -> `PersonaCard` | `winsByPersona` prop -> `winsForPersona` prop | WIRED | Confirmed single fetch site + prop threading; 0 `useQuery` calls in either child |
| `useStoreBotGame.ts`'s `toStoreRequest` / `useDrainPendingStore` / `Bots.tsx`'s finish-time store effect | `BOT_PERSONA_WINS_QUERY_KEY` cache | `queryClient.invalidateQueries()` on successful store (CR-01 fix) | WIRED | Confirmed in both `Bots.tsx:288` and `useStoreBotGame.ts:166`; **mutation-verified live** — reverting the `Bots.tsx` invalidation call broke `Bots.test.tsx`'s CR-01 regression test (restored afterward, `git status` clean) |

### Behavioral Spot-Checks / Live Test Runs

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full frontend suite | `npm test -- --run` | 183 files / 2521 tests passed | PASS |
| Full backend suite | `uv run pytest -n auto -q` | 3543 passed, 21 skipped | PASS |
| `ty check` | `uv run ty check app/ tests/` | 3 pre-existing unresolved-import errors in `app/services/maia_engine.py` (missing optional `maia-inference` uv group) — unrelated to this phase | PASS (no new errors) |
| `ruff check` | `uv run ruff check app/ tests/` | All checks passed | PASS |
| `tsc -b` | `npx tsc -b` | Clean | PASS |
| frontend lint | `npm run lint` | 0 errors, 3 pre-existing unrelated `coverage/` dir warnings | PASS |
| knip | `npm run knip` | Clean | PASS |
| CR-01 mutation check | Reverted the `Bots.tsx` `invalidateQueries` call, re-ran `Bots.test.tsx -t "CR-01"` | Failed as expected (`getPersonaWins` never called again) | PASS — proves the fix is load-bearing, not cosmetic |
| Targeted persona-only backend tests | `uv run pytest tests/routers/test_bots.py tests/schemas/test_bots.py tests/repositories/test_game_repository_persona_wins.py -q` | 33 passed | PASS |
| Targeted persona-only frontend tests | `npx vitest run PersonaGrid.test.tsx PersonaCard.test.tsx useStoreBotGame.test.ts` | 41 passed | PASS |

### Requirements Coverage

No formal REQ-IDs are mapped to Phase 185 (`grep -n "185" .planning/REQUIREMENTS.md` returns nothing; all 3 plans declare `requirements: []` and document this as an intentional post-milestone follow-up with `Requirements: TBD` in ROADMAP.md). No orphaned requirements found. Coverage is behavior-based per each plan's `must_haves`/`coverage` blocks, cross-checked above.

### Anti-Patterns Found

None. Scanned all 20 files listed in 185-REVIEW.md's `files_reviewed_list` for `TBD|FIXME|XXX|TODO|HACK|PLACEHOLDER`, hardcoded empty stubs, and empty handlers — no unresolved debt markers. The one prior code-review Info item (IN-01, no DB-level CHECK/FK tying `persona_id` to the known roster) is explicitly acknowledged-by-design with a documented rationale (frontend-only, milestone-evolving roster; low blast radius) and requires no fix.

### Code Review Fix Verification (185-REVIEW.md)

All 4 actionable findings from the code review were independently re-verified in source (not trusted from the review's own "FIXED" annotations):

| Finding | Claimed fix commit | Verified in source | Verified by test |
|---------|--------------------|---------------------|-------------------|
| CR-01 (stale win cache) | `50de6676` | Yes — `BOT_PERSONA_WINS_QUERY_KEY` exported + invalidated at both call sites | Yes — live-run + mutation check (see above) |
| WR-01 (`count_wins_by_persona` docstring/behavior mismatch) | `fbc32416` | Yes — `.having(win_count > 0)` present | Yes — `test_persona_with_only_losses_is_absent_not_zero` ran live, passed |
| WR-02 (`useBotPersonaWins` duplicated `botsApi.getPersonaWins`) | `f81812eb` | Yes — `queryFn: () => botsApi.getPersonaWins()` | N/A (structural fix; confirmed by source read + 0 grep hits for the old inline `apiClient.get` in this hook) |
| WR-03 (`persona_id` missing `min_length=1`) | `bb988fe5` | Yes — `min_length=1` present | Yes — `test_persona_id_empty_string_rejected` ran live, passed |
| IN-01 (no DB CHECK/FK) | acknowledged, no fix | N/A — intentional | N/A |

### Human Verification Required

1. **No-row-labels legibility backstop** — Open `/bots` and visually confirm a user can tell which row is which rung purely from each card's own `~ELO`/`calibratedLabel`, without a row label. *Why human:* explicitly flagged `verification: backstop` in the plan; a visual-scan judgment, not a DOM-provable fact.
2. **Header row fits at 320px** — Open `/bots` at a 320px-wide viewport (or the mobile drawer) and confirm all 4 style names (Attacker/Trickster/Grinder/Wall) render without truncation/overlap at `text-sm`. *Why human:* no automated test exercises real box-model layout at a specific width.
3. **Live gold-star appearance after a real game** — Play and finish a persona bot game, return to the roster, confirm a gold star appears without a full reload. *Why human:* full user-flow / live-session behavior; the underlying cache-invalidation wiring is unit-tested and mutation-verified, but an actual played game through the UI is not.

### Gaps Summary

No gaps. All 4 code-review findings (1 critical, 3 warnings) were independently re-verified as genuinely fixed in source and covered by passing, mutation-verified tests — not just claimed fixed in the review's own frontmatter. Both full test suites (backend 3543/21 skipped, frontend 2521) ran live during this verification and matched the executor's claimed evidence exactly. The only unresolved items are two visual/viewport judgments and one live-session UAT check, none of which indicate a broken implementation — they are the class of check that structurally cannot be settled by static analysis.

---

*Verified: 2026-07-22T18:55Z*
*Verifier: Claude (gsd-verifier)*
