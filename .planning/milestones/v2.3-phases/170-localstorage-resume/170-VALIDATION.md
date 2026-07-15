---
phase: 170
slug: localstorage-resume
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-07-13
---

# Phase 170 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Derived from `170-RESEARCH.md` § Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | Vitest (jsdom); `@testing-library/react` for hooks |
| **Config file** | `frontend/vite.config.ts` (no separate `vitest.config.*`) |
| **Quick run command** | `cd frontend && npm test -- <file> -t "<token>"` |
| **Full suite command** | `cd frontend && npm test` (`vitest run` — already non-watch) |
| **Type check (mandatory)** | `cd frontend && npx tsc -b` — lint/test do NOT type-check (esbuild strips types); this phase changes `useBotGame`'s exported state shape |
| **Estimated runtime** | ~30–60 seconds (full frontend suite) |

Mirror these existing files for conventions: `frontend/src/lib/__tests__/chessClock.test.ts`,
`frontend/src/lib/__tests__/botGamePgn.test.ts`, `frontend/src/hooks/__tests__/useBotGame.test.ts`
(`@vitest-environment jsdom` pragma, `vi.mock` of `selectBotMove` / `createDeadlineSearch` /
provider factories, `vi.useFakeTimers({ now: 0 })`, `renderHook` / `act`).

---

## Sampling Rate

- **After every task commit:** `npm test -- <touched test file> -t "<relevant token>"`
- **After every plan wave:** `npm test` (full frontend suite) + `npx tsc -b`
- **Before `/gsd-verify-work`:** full frontend suite green, `npm run lint` clean, `npx tsc -b` clean
- **Max feedback latency:** ~60 seconds

This phase makes no backend changes, so `uv run pytest` is not gated by its own work —
but the standing CLAUDE.md pre-merge gate still runs the full backend suite before the
squash-merge to `main`.

---

## Per-Requirement Verification Map

Task IDs are assigned by the planner; this map is the requirement-level contract every
plan must satisfy. **Every row is a revert-proof invariant**: per the project's
mutation-test discipline, each test MUST fail when its mechanism is reverted. A
grep / symbol-presence check is NOT acceptable proof.

| Requirement | Invariant | Test Type | Automated Command | File Exists |
|-------------|-----------|-----------|-------------------|-------------|
| RESUME-01 | Round-trip: `restore(snapshot(game)).pgn() === game.pgn()` for a game with moves by both colors (D-08 acceptance gate) | unit | `npm test -- src/lib/__tests__/botGameSnapshot.test.ts -t "round-trip"` | ❌ W0 |
| RESUME-01 | `hasLeftBook` / `hasFiredLowTime` / `movesSinceLastDecline` each survive a resume — revert each seed **individually** and confirm its specific test goes red | unit | `npm test -- src/hooks/__tests__/useBotGame.test.ts -t "resume-seed"` | ❌ W0 (extends) |
| RESUME-01 | D-01/D-02 clock-fold **asymmetry**: hide on the user's turn folds in-turn elapsed into the snapshot base; hide on the bot's turn does NOT (base == last-commit value) | unit | `npm test -- src/lib/__tests__/chessClock.test.ts -t "fold"` | ❌ W0 (extends) |
| RESUME-01 | D-03 `live` gate: a snapshot restored on the **bot's** turn triggers zero `selectBotMove` calls before `confirmLive()`, exactly one after | unit | `npm test -- src/hooks/__tests__/useBotGame.test.ts -t "prewarm-gate"` | ❌ W0 (extends) |
| RESUME-01 | No away-time billed: clock bases after restore equal the snapshot's bases regardless of wall-clock gap since `savedAt` | unit | `npm test -- src/hooks/__tests__/useBotGame.test.ts -t "no-away-time"` | ❌ W0 (extends) |
| RESUME-02 | An **unfinished** game's snapshot never reaches `flawchess_bot_pending_store` — only `finalizeGame` enqueues (SC2, structural) | unit | `npm test -- src/lib/__tests__/botPendingStore.test.ts -t "store-once"` | ❌ W0 |
| RESUME-02 | Drain semantics: 2xx (`created` true **or** false) removes the entry; 422 removes + captures to Sentry; 401 / 5xx **keeps** the entry | unit | `npm test -- src/hooks/__tests__/useStoreBotGame.test.ts -t "drain"` | ❌ W0 |
| RESUME-02 | `gameUuid` is minted once at game start and is **stable across a resume** — never re-minted (SC3; makes double-store structurally impossible via the server's `uq_games_user_platform_game_id`) | unit | `npm test -- src/hooks/__tests__/useBotGame.test.ts -t "stable-uuid"` | ❌ W0 |
| RESUME-02 | `tc_preset` sent to `POST /bots/games` is `toBackendTcStr(baseSeconds, incrementSeconds)` (base-seconds, e.g. `"300+3"`) and equals the PGN's `[TimeControl]` header — see amended CONTEXT.md D-14 | unit | `npm test -- src/hooks/__tests__/useStoreBotGame.test.ts -t "tc-preset"` | ❌ W0 |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `frontend/src/lib/botGameSnapshot.ts` + `frontend/src/lib/__tests__/botGameSnapshot.test.ts` — new module + test file
- [ ] `frontend/src/lib/botPendingStore.ts` + `frontend/src/lib/__tests__/botPendingStore.test.ts` — new module + test file
- [ ] `frontend/src/hooks/useStoreBotGame.ts` + `frontend/src/hooks/__tests__/useStoreBotGame.test.ts` — new hook + test file
- [ ] Extend `frontend/src/hooks/__tests__/useBotGame.test.ts` — `resume-seed`, `prewarm-gate`, `no-away-time`, `stable-uuid` groups
- [ ] Extend `frontend/src/lib/__tests__/chessClock.test.ts` — clock-fold helper tests

No framework install needed — Vitest + jsdom + Testing Library are already in place.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real `pagehide` / `visibilitychange` on a physical iOS/Android device (tab purge, app backgrounding, PWA install) | RESUME-01 | jsdom can dispatch the events but cannot reproduce a real mobile Safari tab purge or bfcache restore | Start a bot game on a phone, make a few moves, background the app for 2+ min, reopen `/bots` — the resume gate must appear with the correct move count and clocks, with no away-time billed |
| localStorage `QuotaExceededError` / Safari private mode | RESUME-01 | Browser-specific storage failure, not reproducible in jsdom without mocking away the thing under test | Open `/bots` in Safari private browsing — the game must play normally with resume silently disabled (no crash, no error toast), and the failure captured once to Sentry |
| Resume gate visual composition + mobile parity | RESUME-01 | Visual/layout judgement | Load `/bots` with a snapshot present on a narrow viewport — gate legible, buttons tappable, `brand-outline` secondary, `text-sm` floor honored |

---

## Validation Sign-Off

- [ ] All tasks have an `<automated>` verify or a Wave 0 dependency
- [ ] Sampling continuity: no 3 consecutive tasks without an automated verify
- [ ] Wave 0 covers all ❌ references above
- [ ] No watch-mode flags (`npm test` is already `vitest run`)
- [ ] Every invariant above proven by REVERTING its mechanism and observing a red test
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
