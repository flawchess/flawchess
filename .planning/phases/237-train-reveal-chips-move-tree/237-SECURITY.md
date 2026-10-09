---
phase: "237"
slug: "train-reveal-chips-move-tree"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-09"
---

# Phase 237 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.
> Register authored at plan time (11 PLAN `<threat_model>` blocks); verified at ASVS L1 (grep depth) against the implementation on `gsd/phase-237-train-reveal-chips-move-tree`. SUMMARY Threat Flags: none raised.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| client -> `POST /train/.../review` | review telemetry flush (v1 and v2 bodies) | counts and booleans only, user-owned row |
| sessionStorage -> reveal | `train_reveal_cache.revealTree` restore (Analyze -> Back) | self-only UCI paths, never trusted for grading |
| client -> Umami | feature events (chip, fork, strip, rewind) | enumerated literal targets, no SAN/FEN |
| dev environment | browser UAT edits | dev DB `reveal_walkthrough_seen_at` of the dev user only |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-237-01 | Tampering | ReviewTelemetry v2 fields | medium | mitigate | `extra="forbid"`, StrictBool, clamped counts, `_keys_match_version` (app/schemas/train.py:440-447), schema tests | closed |
| T-237-02 | Repudiation | mixed v1/v2 rows in analysis | low | mitigate | docstring on row-level `v` = last patch merged (app/schemas/train.py:384-400); validator forbids mixed bodies | closed |
| T-237-03 | Elevation of privilege | review route, foreign row | low | mitigate | ownership check unchanged; `test_review_flush_rejects_other_users_row` (tests/routers/test_train.py:3661) green | closed |
| T-237-04 | Information disclosure | tree seeding before the solve lands | medium | mitigate | seeding/restore effects return while `!active` (useTrainRevealTree.ts:323,335); hook test asserts zero nodes while inactive | closed |
| T-237-05 | Denial of service (self) | oversized restore snapshot | low | mitigate | `REVEAL_TREE_SNAPSHOT_MAX_PATHS`/`_MAX_PLIES` (trainRevealLines.ts:417-440), chess.js-guarded replay | closed |
| T-237-06 | Information disclosure | dimmed Also-fine arrows on the pristine board | low | mitigate | `buildTrainRevealOverlay` returns empty while `!verdictLanded` (trainArrows.ts:382) | closed |
| T-237-07 | Information disclosure | chips memo / tree active before verdict | medium | mitigate | `chips` empty while `verdict === null` (TrainSolveScreen.tsx:846-848), tree `active` = verdict landed | closed |
| T-237-08 | Information disclosure | chip/tree testids | low | mitigate | testids keyed on role `train-chip-${chip.key}` (TrainLineChips.tsx:64), no SAN interpolation | closed |
| T-237-09 | Tampering | post-verdict drop (SOLV-02 scoring integrity) | high | mitigate | `if (verdict === null) return false; return revealTree.playMove(...)` after unchanged guards (TrainSolveScreen.tsx:1356-1357); SOLV-02 FakeWorker test proves one `solvePuzzle`, no extra grading search | closed |
| T-237-10 | Information disclosure | first-fork Umami event | low | mitigate | literal `train-sideline-fork` in `ACTION_TARGETS` (analytics.ts:391), fired from the drop handler | closed |
| T-237-11 | Denial of service | reveal engine vs Phase 236 background grade | low | mitigate | `engineEnabled: instantGrade?.status !== 'pending'` (TrainSolveScreen.tsx:921) | closed |
| T-237-12 | Spoofing (UI integrity) | stale published bar payload | low | mitigate | `usePublishMobileBoardControls` clears on unmount (mobileBoardControls.ts:125); tests assert null before the verdict | closed |
| T-237-13 | Information disclosure | Analyze link analytics | low | mitigate | internal `Link` with analytics in the click handler, no `data-umami-event` (TrainRevealActionBar.tsx) | closed |
| T-237-14 | Spoofing (UI integrity) | strip total / clause | low | mitigate | points from `scorePuzzle(verdict.correct_guess, verdict.move_quality)` (TrainReveal.tsx:405); `isBest` wording only | closed |
| T-237-15 | Information disclosure | strip expand Umami | low | mitigate | literal `train-verdict-strip` in `PANEL_TARGETS` (analytics.ts:372), click handler only | closed |
| T-237-16 | Tampering | `train_reveal_cache.revealTree` | low | mitigate | `isRevealTreeSnapshot` shape + cap check drops a malformed field (trainRevealCache.ts:93,151); never feeds grading | closed |
| T-237-17 | Tampering | client-built v2 telemetry | low | transfer | server boundary is the authority (T-237-01) | closed |
| T-237-18 | Information disclosure | telemetry content | low | mitigate | wire sends `chipKeys.size` only (trainTelemetry.ts:142); the key list stays in the client snapshot | closed |
| T-237-19 | Repudiation | reveal_walkthrough stamp | low | accept | stamp only from user actions on the last step; first-write-wins guard unchanged | closed |
| T-237-20 | Tampering | dev DB edits for the tour UAT | low | mitigate | only user 28's `reveal_walkthrough_seen_at` on the dev DB was reset (237-11-SUMMARY); `bin/reset_db.sh` never run | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

T-237-SC (supply chain, every plan): accept, no packages installed this phase.

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-237-01 | T-237-19 | an abandoned tour replays by design (D-12); the stamp is user-initiated and idempotent server-side | plan 10 threat model | 2026-10-09 |
| AR-237-02 | T-237-SC | no new npm/pip dependencies in this phase | plan threat models | 2026-10-09 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-09 | 20 | 20 | 0 | orchestrator (L1 grep evidence; register authored at plan time, auditor short-circuited per workflow) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
