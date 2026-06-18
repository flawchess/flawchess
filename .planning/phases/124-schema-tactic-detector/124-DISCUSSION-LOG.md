# Phase 124: Schema + Tactic Detector - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-06-17
**Phase:** 124-schema-tactic-detector
**Areas discussed:** Detector scope, Priority order (Q-010), Validation + accuracy bar (Q-011), tactic_piece semantics (Q-012)

> Mid-session, the user revised `.planning/notes/tactic-tagging-architecture.md` with new
> locked decisions (full motif set, severity gate, the `tactic_confidence` column). That
> retired the originally-planned "MVP motif set" question (the set is now decided as
> "everything reliable") and re-framed the discussion around what Phase 124 actually
> implements/validates now.

---

## Detector scope

| Option | Description | Selected |
|--------|-------------|----------|
| Core 8 now, tier-3 enum-only | Implement + validate Core 8 only; reserve enum slots for tier-3 + named mates but don't implement them | |
| Everything now | Implement ALL detectors (core 8 + 8 tier-3 + named mates), each precision-first | ✓ |
| Core 8 + named mates, tier-3 deferred | Implement core 8 + named-mate subtypes; defer the 8 fuzzy tier-3 heuristics | |

**User's choice:** Everything now
**Notes:** Large phase by deliberate choice. Claude flagged that the tier-3 + named-mate
validation burden is front-loaded and Phase 125 backfill is gated on all detectors
clearing the Q-011 bar. User accepted (disagree-and-commit not needed — informed choice).

---

## Priority order (Q-010)

### Q1 — Does a forced mate always win the tiebreak?

| Option | Description | Selected |
|--------|-------------|----------|
| Mate always dominates | Forced-mate PV → mate type (named > back-rank > generic), regardless of co-firing geometric motif | ✓ |
| Geometric motif wins, mate as fallback | Prefer fork/skewer/pin/discovered label; use "mate" only when no geometric motif fires | |

**User's choice:** Mate always dominates

### Q2 — Where does hanging-piece sit?

| Option | Description | Selected |
|--------|-------------|----------|
| Lowest catch-all | hanging-piece wins only when no more specific motif fires | ✓ |
| Above tier-3 fuzzy | hanging-piece outranks fuzzy tier-3 but sits below reliable geometric | |

**User's choice:** Lowest catch-all
**Notes:** Final order — Mates (named > back-rank > generic) > [fork > skewer > pin >
discovered-attack > double-check] > [tier-3 fuzzy] > hanging-piece. Intra-tier order in
tiers 2/3 left provisional, tunable post-detector per Q-010 step 2.

---

## Validation + accuracy bar (Q-011)

### Q1 — Fixture sizing + precision bar

| Option | Description | Selected |
|--------|-------------|----------|
| Small-N, tiered bar | ~10–15 positives/motif from prod + hard-negatives; core ≥90%, tier-3 ≥95% precision; recall not gated; miss-bar → query-suppressed | ✓ |
| Uniform high bar | ~20–30/motif, single ≥95% across all 24 | |
| Core-strict, tier-3 lenient | Core ≥90% with fixtures; tier-3 spot-check only, no hard gate | |

**User's choice:** Small-N, tiered bar

### Q2 — Low-confidence handling

| Option | Description | Selected |
|--------|-------------|----------|
| Always write + query-time threshold | Store motif + tactic_confidence whenever a detector fires; suppress low-confidence at query time only; NULL = nothing fired | ✓ |
| Build-time floor + query-time threshold | Also drop tier-3 below ~50 confidence to NULL at detect time | |

**User's choice:** Always write + query-time threshold
**Notes:** Matches the architecture note's winner-confidence rationale (sweep thresholds
in SQL, no re-backfill). Accepted limitation: thresholds the winner only, can't re-rank.

---

## tactic_piece semantics (Q-012)

| Option | Description | Selected |
|--------|-------------|----------|
| Core + discovered-attack, rest NULL | Piece for core mapping + discovered-attack; double-check + all tier-3 NULL | |
| Clean-semantic everywhere possible | Also tier-3 where well-defined (sacrifice/capturing-defender/deflection/attraction); NULL only when genuinely ambiguous | ✓ |
| Core 5 only, everything else NULL | Only fork/hanging/pin/skewer/mate get a piece | |

**User's choice:** Clean-semantic everywhere possible
**Notes:** Piece is stored-but-unsurfaced in v1 (motif-level comparison only) and
re-backfillable. NULL reserved for double-check, x-ray, interference, clearance,
intermezzo, and multi-piece/ambiguous cases.

---

## Claude's Discretion

- Detector module layout; the PV-parsing helper that builds `(board, line, pov)` (pov =
  refuting side); fixture file format/location; exact int values per motif in the enum.
- The precise graded scoring function per tier-3 motif (constrained by the ≥95% bar).

## Deferred Ideas

- Piece-level you-vs-opponent UI (TACPIECE-01) — data captured now, UI later.
- Surfacing named-mate subtypes — v1 surfaces coarse "mate"; subtype surfacing is a
  Phase 126 decision.
- True standalone `missed-X` detection (TACMISS-01) — deferred.
