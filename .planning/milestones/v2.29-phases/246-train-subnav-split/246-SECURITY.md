---
phase: "246"
slug: "train-subnav-split"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-11-07"
---

# Phase 246 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| browser -> API | `list`, `limit` and `offset` on `GET /train/archive` are untrusted; the user identity comes only from the token | Query params |
| API -> browser | Archive items and the viewer's own leaderboard rank | The viewer's game details and positions, opponent usernames (other users' self-typed strings) |
| URL -> client state | The pathname and `?page=` decide which tab and page render | User-controlled strings |
| sessionStorage -> client state | The cached reveal read at mount, validated against the session id | The player's own session state |
| client state -> feedback-ask API and local snapshot | One-shot effects write a view count and a localStorage snapshot on mount | Counters, streak snapshot |
| agent -> dev DB | Seeding and cleanup for the browser walk | Dev rows only, never prod |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-246-01 | Elevation of privilege | `get_train_archive` user scoping | high | mitigate | No user parameter exists. `app/routers/train.py:379` takes the user from `current_active_user`, passed keyword-only at `:393`. `test_archive_other_user_items_absent`, `test_archive_excludes_active_and_other_users_items`, `test_archive_requires_auth` | closed |
| T-246-02 | Information disclosure | `last_solve` subquery | medium | mitigate | `DrillSolve.user_id == user_id` and `DrillItem.user_id == user_id` in `_archive_page_stmt` (`app/repositories/train_repository.py:634`, `:659`). `test_archive_ignores_herring_filler_and_other_user_solves` | closed |
| T-246-03 | Denial of service | `offset` overflow into a 500 | low | mitigate | `Query(ge=0, le=_ARCHIVE_OFFSET_MAX)` at `app/routers/train.py:382`. `test_archive_rejects_bad_params` (`?offset=-1`, `?offset=2147483648`) | closed |
| T-246-04 | Denial of service | PGN replay per row | low | mitigate | `limit` capped by `ARCHIVE_PAGE_SIZE_MAX = 50` (`app/routers/train.py:78`, `:381`); sort and page run before `games` is joined (`app/repositories/train_repository.py:646`) | closed |
| T-246-05 | Tampering (business logic) | Listing ACTIVE puzzles via a crafted `list` | medium | mitigate | `ArchiveList = Literal["mastered", "parked"]` (`app/schemas/train.py:843`). `?list=active` returns 422 in `test_archive_rejects_bad_params` | closed |
| T-246-06 | Information disclosure (spoiler) | Response shape | low | mitigate | No move, motif or severity on the wire; `set(item.keys()) == _ARCHIVE_ITEM_KEYS` at `tests/routers/test_train.py:4489` | closed |
| T-246-07 | Information disclosure | Analyze opening a stranger's game | medium | accept | `drill_items` come only from the user's own flaws. Prod check P5 (`games.user_id <> drill_items.user_id`) ran 2026-11-06 and returned 0 (`246-RESEARCH.md:800`) | closed |
| T-246-08 | Denial of service | Repeated Stockfish spawns on iOS | medium | mitigate | `todayVisited` latch at `frontend/src/hooks/useTrainLoop.ts:116`, engine `enabled: canTrain && todayVisited` at `:120`. Counting `WorkerCtor` in `Train.subnav.test.tsx` | closed |
| T-246-09 | Tampering (data integrity) | Spurious session rows from browsing | medium | mitigate | No session POST on a visit that never touched Today (same latch); `requestSessionReread` defers a late save's re-read. Deep-link test in `Train.subnav.test.tsx` | closed |
| T-246-10 | Tampering | Crafted `/train/*` pathname | low | mitigate | `parseTrainRoute` (`frontend/src/lib/trainRoute.ts:36`) matches exact paths; pinned by `trainRoute.test.ts` | closed |
| T-246-11 | Spoofing (stale view) | Restored reveal from another session | low | accept | Existing session id guard moved unchanged; `isToday` stops it showing on another tab | closed |
| T-246-12 | Information disclosure | Rank line for hidden and guest viewers | low | accept | The rank is the viewer's own and renders only on their device (D-11) | closed |
| T-246-13 | Tampering (analytics integrity) | `nav-click` value | low | mitigate | `train-rank-line` is a registered literal in `NAV_SOURCES` (`frontend/src/lib/analytics.ts:418`) | closed |
| T-246-14 | Tampering | Usernames on `TrainPuzzleCard` | low | mitigate | React text children only (`TrainPuzzleCard.tsx:99`); no `dangerouslySetInnerHTML` or `href` in the file | closed |
| T-246-15 | Tampering | Crafted `?page=` value | low | mitigate | `parseArchivePage` falls back to 1 and caps at `ARCHIVE_PAGE_MAX` (`frontend/src/lib/trainRoute.ts:55-62`); pinned by `trainRoute.test.ts` | closed |
| T-246-16 | Information disclosure (spoiler) | Card contents | low | mitigate | No spoiler field on the wire (T-246-06); `TrainPuzzleCard.test.tsx` asserts no arrows and no SAN token | closed |
| T-246-17 | Tampering | Analyze link | low | mitigate | `buildTrainPuzzleAnalysisUrl(gameId: number, ply: number)` (`frontend/src/lib/analysisUrl.ts:121`); no free text enters the URL | closed |
| T-246-18 | Tampering | UAT seeding in the dev DB | low | mitigate | Dev only; `temp/246-uat/results.md` records `seeded=25 deleted=25 remaining=0`. The walk's dev session 296 and guest users stayed in dev (`246-06-SUMMARY.md:46`) | closed |
| T-246-19 | Information disclosure | Minted dev JWT | low | mitigate | Written under `temp/246-uat/`, confirmed gitignored; signed with the dev secret | closed |
| T-246-20 | Tampering (data integrity) | Feedback-ask view and streak snapshot from a hidden landing | medium | mitigate | `isVisible` gate at `frontend/src/components/train/TrainStartScreen.tsx:361`; hidden-landing tests in `Train.subnav.test.tsx` | closed |
| T-246-SC | Tampering | npm/pip/cargo installs | low | accept | No plan in this phase installs packages | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-246-01 | T-246-07 | Archive items are the user's own flaws. Prod returned 0 foreign rows, so Analyze cannot open a stranger's game today. The route does not enforce this per request. | Plan 246-01 disposition | 2026-11-06 |
| AR-246-02 | T-246-11 | Existing guard kept unchanged. | Plan 246-02 disposition | 2026-11-06 |
| AR-246-03 | T-246-12 | The viewer already sees their own rank on the board view. | Plan 246-03 disposition | 2026-11-06 |
| AR-246-04 | T-246-SC | No packages installed. | Plan dispositions | 2026-11-06 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-11-07 | 21 | 21 | 0 | /gsd-secure-phase orchestrator, L1 short-circuit (register authored at plan time, no auditor subagent). Evidence: grep of the code above, 19 backend archive tests and 71 frontend tests in `trainRoute`, `TrainPuzzleCard` and `Train.subnav` pass. |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-11-07
