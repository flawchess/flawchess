# Phase 236: Train Phone Grade Record & Instant Server Verdict - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-08
**Phase:** 236-train-phone-grade-instant-verdict
**Areas discussed:** none interactively (owner answered "you decide" to the area selection)

---

## Areas presented

| Area | Question | Claude's decision |
|------|----------|-------------------|
| Late phone reading write | Instant POST means the background reading lands after it: review route, new endpoint, or hold the POST? | Review route, write-once (D-12). Holding the POST rejected (verdict needs server-only correct_guess); new endpoint rejected (extra surface). |
| Reveal while search runs | Placeholder in "Your move" card, or hold the reveal? | Show reveal on SolveResponse, loading state in line cards, fill in place; no record and no error state on failure (D-14/D-15). |
| Record scope & contents | Played == key, re-check, legacy, device hint? | Always the 1.5 s reading (D-04); played == key gets a record with played = key fields (D-05); no record on legacy path (D-06); no device hint (D-07). |
| Instant verdict source | Payload tier (0 ms) or SolveResponse (RTT)? | SolveResponse (D-09); payload tier is the asserted move_quality fallback when live classification drifts (D-10). |

**User's choice:** "you decide"
**Notes:** Scouting found that soft vetted moves rated "inaccuracy" by the phone trigger a 6 s re-check the server then discards; locked as D-11 (exclude the whole server-graded set from the re-check).

## Claude's Discretion

All four areas, plus field names, write-once mechanism, loading visual, engine contention, stale-bundle handling.

## Deferred Ideas

- Engine/device hint on the record.
- Tuning the 1.5 s budget from the collected phone-vs-server data.
