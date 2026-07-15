---
phase: 171
slug: bots-page-setup-screen-nav
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-14
---

# Phase 171 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `171-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework (frontend)** | Vitest 4.1.7 + @testing-library/react (`frontend/package.json:13-14,54-69`) |
| **Framework (backend)** | pytest + pytest-asyncio, per-run isolated DB (`tests/conftest.py`) |
| **Config file** | `frontend/vite.config.ts` (vitest colocated); backend via `pyproject.toml` |
| **Quick run (frontend)** | `npx vitest run <path> -t "<name>"` |
| **Quick run (backend)** | `uv run pytest tests/test_users_router.py -k <expr>` |
| **Full suite (frontend)** | `cd frontend && npm test -- --run` |
| **Full suite (backend)** | `uv run pytest -n auto` |
| **Estimated runtime** | frontend full ~60s; backend full ~3-5 min (`-n auto`) |

**No framework install needed** — Vitest and pytest are already configured.

---

## Sampling Rate

- **After every task commit:** the scoped test file(s) for that task only (`-t` / `-k`).
- **After every plan wave:** `npm test -- --run` (frontend) + `uv run pytest -n auto` (backend, if the wave touched backend).
- **Before `/gsd-verify-work`:** full suite green, both stacks.
- **Phase gate (before squash-merge to `main`):** the full CLAUDE.md pre-merge gate — `ruff format app/ tests/`, `ruff check app/ tests/ --fix`, `ty check app/ tests/`, `pytest -n auto -x`, `(cd frontend && npm run lint && npm test -- --run)`. Also `npx tsc -b` (memory: lint+test do NOT type-check).
- **Max feedback latency:** < 60s per task.

---

## Per-Task Verification Map

> Task IDs are filled in by the planner. The rows below are the **behaviors that must be covered**;
> every one must map to at least one `<verify>` in a PLAN.md task.

| # | Requirement / Decision | Behavior to prove | Test Type | Automated Command | File Exists |
|---|------------------------|-------------------|-----------|-------------------|-------------|
| V-01 | **D-03 / SEED-100** (BLOCKER) | At `blend = 0`, `selectBotMove` never consults `deps.search` | unit | `npx vitest run selectBotMove.test.ts -t "blend=0"` | ✅ `selectBotMove.test.ts:85-96` |
| V-02 | **D-03 / SEED-100** (BLOCKER) | **Mutation proof** — reverting the `blend <= 0` early-return (`selectBotMove.ts:113-118`) makes V-01 FAIL | mutation | manual revert → run V-01 → confirm red → re-apply | ✅ (uses V-01) |
| V-03 | D-03 | `chessClock.ts:36-39` D-16 comment no longer falsely claims the deadline is enforced for all blends; `BotGameSettings.blend` (`useBotGame.ts:161-162`) documents the blend-0 exemption | source assertion | grep for corrected text | n/a (doc) |
| V-04 | PLAY-01 / D-16 / D-18 | `/bots` renders in desktop nav, mobile bottom bar, and mobile more-drawer; nav order is Library · Bots · Openings · Endgames | unit (RTL) | `npx vitest run App.test.tsx` | ❌ **Wave 0** |
| V-05 | PLAY-01 / **D-17** | `/bots` nav link is NEVER `aria-disabled`/dimmed — asserted across zero-game, guest, and fully-imported `navUnlocked` states | unit (RTL) | same file as V-04 | ❌ **Wave 0** |
| V-06 | PLAY-01 / D-18 | `isActive('/bots', pathname)` is true for `/bots` and `/bots/*`; `ROUTE_TITLES['/bots']` set | unit | same file as V-04 | ❌ **Wave 0** |
| V-07 | PLAY-02 / D-14 | Setup screen renders ELO / play-style / color / TC pickers; Start builds a correct `BotGameSettings`, incl. TC preset → `{baseSeconds, incrementSeconds}` | unit (RTL) | `npx vitest run SetupScreen.test.tsx` | ❌ **Wave 0** |
| V-08 | PLAY-02 / **D-12** | Random color resolves to a concrete White/Black **before** `useBotGame` mounts — settings and exported PGN never carry "random" | unit | same file as V-07 | ❌ **Wave 0** |
| V-09 | PLAY-02 / **D-01** | Play-style control: Human preset → `blend = 0`; Engine preset → `blend = 1`; slider spans 0.05–1.00 in 0.05 steps and **cannot reach 0** | unit | same file as V-07 | ❌ **Wave 0** |
| V-10 | PLAY-02 / D-10 | Last-used settings persist under an **owner-scoped key distinct from** `botGameSnapshot` and `botPendingStore`, and prefill on next setup mount | unit | `npx vitest run botSetupSettings.test.ts` | ❌ **Wave 0** |
| V-11 | PLAY-02 / D-11 / D-13 | "New game" returns to the **setup screen** prefilled (not an instant restart); ResumeGate **discard** falls through to setup, not a stub game | unit (RTL) | `npx vitest run Bots.test.tsx` | ❌ **Wave 0** (confirm existing file) |
| V-12 | **D-07** | `/users/me/profile` returns `lichess_blitz_equivalent_rating`: correct value with a blitz anchor; `null` with no anchor; `null` with only non-blitz anchors | unit (backend) | `uv run pytest tests/test_users_router.py -k lichess_blitz` | ❌ **Wave 0** |
| V-13 | D-07 / D-08 | Setup ELO default = the normalized rating (clamped to `MAIA_ELO_LADDER`), else 1500; `useMaiaEloDefault`'s **free-play branch** reads the same field | unit | `npx vitest run useMaiaEloDefault.test.ts` | ❌ **Wave 0** (confirm existing file) |
| V-14 | PLAY-10 / **D-21** | On `game.outcome` becoming non-null the store mutation **fires for the just-finished game** (not deferred to next mount) | unit | `npx vitest run Bots.test.tsx` | ❌ **Wave 0** |
| V-15 | PLAY-10 / **D-21** (regression risk) | **No double-POST** — finish → store succeeds → remount `/bots` → the pending-store drain does NOT re-POST the same game | unit | same file as V-14 | ❌ **Wave 0** |
| V-16 | PLAY-10 / D-20 / SC4 | "Saved to your Library" affordance renders **only** on store success; the guest not-auto-analyzed caveat renders only when `is_guest` | unit (RTL) | `npx vitest run GameResultDialog.test.tsx GameResultStrip.test.tsx` | ❌ **Wave 0** |
| V-17 | D-20 | "Analyze this game" keeps its current client-side `buildAnalysisLineUrl` behavior — **not** gated on the POST landing | unit | same file as V-16 | ❌ **Wave 0** |

*Status legend: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

New/extended test files that must exist before their behaviors can be verified:

- [ ] `frontend/src/App.test.tsx` — **does not exist today.** No test covers `NAV_ITEMS` / `BOTTOM_NAV_ITEMS` / the `NavHeader` lock rule at all. Covers V-04, V-05, V-06, and (as a byproduct) locks in the existing Library/Openings/Endgames lock behavior against silent regression.
- [ ] `frontend/src/components/bots/SetupScreen.test.tsx` — new. Covers V-07, V-08, V-09.
- [ ] `frontend/src/lib/botSetupSettings.test.ts` — new. Covers V-10. Mirror `botGameSnapshot.test.ts`'s shape (confirm it exists at plan time).
- [ ] `frontend/src/pages/Bots.test.tsx` — extend (or create). Covers V-11, V-14, V-15.
- [ ] `frontend/src/components/bots/GameResultDialog.test.tsx` / `GameResultStrip.test.tsx` — extend. Covers V-16, V-17.
- [ ] `tests/test_users_router.py` — extend with `TestProfileLichessBlitzEquivalentRating`, mirroring `TestProfileCurrentRating` (`:297-368`); seed anchors via `user_rating_anchors_repository.upsert_anchor` (pattern: `tests/services/test_store_bot_game_service.py:21-30`). Covers V-12.
- [ ] Framework install: **none** — Vitest + pytest already configured.

---

## Manual-Only Verifications (HUMAN-UAT)

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| A **guest** plays a full bot game end-to-end and it lands in their Library | PLAY-10 / SC3 | Spans a real guest JWT, localStorage, a real POST, and cross-page navigation — not faithfully reproducible in RTL | Home → `btn-guest` → `/bots` → setup → Start → play to mate/resign → confirm "Saved to your Library" appears **and** the guest caveat shows → follow the link → game is in the Library Games tab |
| A **logged-in** user's finished game appears in the Library Games tab | PLAY-10 / SC4 | Requires a real POST against the dev DB plus the Library's `flawchess` platform opt-in (167 D-03) | Log in → `/bots` → play a short game (3+0) to a finish → confirm the Library link → verify the row in `/library` Games tab |
| Human-mode (`blend = 0`) pacing does not feel robotic | D-02 | Subjective. D-02 says: if it feels wrong, **tune the `chessClock.ts` constant** — do NOT add a new pacing mechanism | Play a 3+0 game with the Human preset; judge the reveal tempo |
| The "30+0" preset's known bucket quirk is not surfacing as a bug | D-14 / Pitfall 4 | Known accepted quirk: `30+0` → `estimated = 1800` → buckets as **rapid**, not classical (`normalization.py:96-101`, frozen) | Play/store a 30+0 game; confirm it appears under a **rapid** Library filter. Expected, documented in a code comment — not a defect |
| Mobile: 4 bottom-nav items + More still fits and reads correctly | D-18 | Real-device layout | Load `/bots` on a phone viewport; check the bottom bar and the more-drawer |

---

## Validation Sign-Off

- [ ] All tasks have `<verify>` blocks or a declared Wave 0 dependency
- [ ] Sampling continuity: no 3 consecutive tasks without an automated verify
- [ ] Wave 0 covers every ❌ reference above
- [ ] No watch-mode flags (`vitest run`, never bare `vitest`)
- [ ] **V-02 mutation proof actually performed** — revert, confirm RED, re-apply. Grep / symbol-presence is NOT acceptable evidence (memory: `feedback_mutation_test_gap_closures`; SEED-100 says so explicitly; Phase 169 burned three rounds on this exact failure shape)
- [ ] **V-15 double-POST regression pinned** — this is the risk D-21 creates
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
