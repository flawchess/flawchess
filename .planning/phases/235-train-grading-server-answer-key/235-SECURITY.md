---
phase: "235"
slug: "train-grading-server-answer-key"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-07"
---

# Phase 235 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail.

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| client -> POST /api/train/sessions | authenticated request; user id only from current_active_user | session request (no user-supplied ids) |
| server -> pre-attempt payload | the answer key crosses to the client before the attempt (D-05) | key UCI, puzzle type, sharp runner-up (low sensitivity) |
| server TrainPuzzle -> client grading engine | the key is only the move to search after; the grade is the phone's own two-search comparison | key UCI |
| client -> UI before the attempt | key and type must not render pre-attempt (D-05) | none rendered |
| client -> POST /api/train/sessions/{id}/solve | untrusted body: played move, client tier, optional re-check claim that can earn a guess point | client claim (integrity-relevant) |
| request -> drill_solves.recheck | validated payload persisted as JSONB | bounded floats/ints, two Literals |
| server verdict -> reveal copy | the D-15 line renders only from the server's `disagreement` flag | boolean |

---

## Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| T-235-01 | Information disclosure | TrainPuzzle.key_move_uci / puzzle_type / runner_up_uci | low | accept | Owner decision D-05; see Accepted Risks Log | closed |
| T-235-02 | Elevation of privilege (IDOR) | `_answer_keys_by_position` | medium | mitigate | `app/repositories/train_repository.py:2244-2292`: WHERE `DrillSolve.user_id == user_id` plus the server-composed `session_id`; SR joins match `GameFlaw.user_id == DrillSolve.user_id` / `GamePosition.user_id == DrillSolve.user_id` | closed |
| T-235-03 | Denial of service | `answer_key_for` / `legal_answer_key` | low | mitigate | `app/services/train_pool.py:306-415`: isinstance guard clauses, `ValueError` caught in `_legal_in`, illegal/absent key degrades to null (D-07) | closed |
| T-235-04 | Information disclosure | TrainSolveScreen pre-attempt render | low | mitigate | D-05 gate A: only `TrainSolveScreen.tsx`, `TrainReveal.tsx`, `types/train.ts` name the fields in production code; gate B: `TrainSolveScreen.tsx` reads them only as dotted `puzzle.` accesses feeding `startGrading` (1089, 1202) and `shouldRecheck` (1105-1107) | closed |
| T-235-05 | Tampering (grade integrity) | `gradeMoveInner` on terminal after-move positions | medium | mitigate | `terminalSearchResult` (`frontend/src/hooks/trainGradingSupport.ts:201`) scores checkmate/stalemate directly | closed |
| T-235-06 | Tampering | illegal or malformed key from a stale payload | low | mitigate | `useTrainGradingEngine.ts:608-615`: `fenAfterUciMove` returns null -> `legacyAnchorFrom` root-search fallback, never throws | closed |
| T-235-07 | Tampering | forged "confirmed" recheck to earn the guess point | medium | mitigate | `_disagreement_accepted` (`train_repository.py:2794`): confirmed outcome, both ES pairs good, LIVE type sharp, server key present, played != key and != su, client tier good; every claim stored with `accepted`. Residual accepted by owner (D-05) | closed |
| T-235-08 | Tampering / DoS | malformed or oversized recheck JSON | low | mitigate | `SolveRecheck` (`app/schemas/train.py:~275`): `extra="forbid"`, `Literal[1]` v, `Literal` outcome, bounded `RecheckExpectedScore` / clamped `RecheckDepth`; wrap validator drops a bad object to None | closed |
| T-235-09 | Tampering (integrity) | JSON null in drill_solves.recheck | low | mitigate | `app/models/drill_solve.py:205-206` `JSONB(none_as_null=True)`; column written only when a recheck arrived. UAT: 57 solved rows SQL NULL, 0 JSON null | closed |
| T-235-10 | Elevation of privilege (IDOR) | `record_solve` | medium | mitigate | row lookup and claim UPDATE scoped by `DrillSolve.user_id == user_id` (`train_repository.py:3310`, `3367`, `3423`); foreign session/position 404s first | closed |
| T-235-11 | Repudiation | disputed guess credit | low | mitigate | stored record (both ES pairs, four depths, outcome, accepted) per solve; verified live in 235-UAT.md test 4 | closed |
| T-235-12 | Tampering | recheck payload built on the client | low | transfer | transferred to the server check T-235-07; the client never decides credit and the D-15 copy reads only `verdict.disagreement` | closed |
| T-235-13 | Denial of service (UX) | wedged Worker during the 6 s re-check | low | mitigate | `recheckMove` (`useTrainGradingEngine.ts:807-812`) races `TRAIN_RECHECK_TIMEOUT_MS` and never rejects; WR-01 `signal.aborted` guard stops the second search. UAT overrun: 12.5 s fallback, no record | closed |
| T-235-14 | Information disclosure | key SAN in the guess card | low | accept | rendered only post-attempt from the verdict; see Accepted Risks Log | closed |
| T-235-15 | Information disclosure | TrainSolveScreen trigger reads | low | mitigate | same D-05 gates A and B as T-235-04 | closed |
| T-235-16 | Denial of service (UX) | "Taking a closer look…" outliving the re-check | low | mitigate | `TrainSolveScreen.tsx:1114-1118` sets `isRechecking` immediately before the single await and clears it in `finally`; per-puzzle reset at 1058; bounded by T-235-13 | closed |
| T-235-SC | Tampering | npm/pip/cargo installs | low | accept | no packages installed by any plan | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-235-01 | T-235-01 | The key crosses to the client pre-attempt; anyone can run Stockfish in another tab, and off-key move_quality was already client-asserted. The UI never renders it pre-attempt (T-235-04/15) | owner (D-05) | 2026-10-07 |
| AR-235-02 | T-235-07 (residual) | A crafted solve body passing every sanity check can earn one guess point; cheating is not a concern for Train (D-05) and every claim is auditable via `accepted` | owner (D-05) | 2026-10-07 |
| AR-235-03 | T-235-14 | Key SAN shown in the post-attempt guess card only | owner (D-05) | 2026-10-07 |
| AR-235-04 | T-235-SC | No dependency installs in this phase | plan authors | 2026-10-07 |

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-07 | 17 | 17 | 0 | /gsd-secure-phase (orchestrator, ASVS L1 grep-depth; auditor skipped per short-circuit: register authored at plan time, threats_open 0) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-07
