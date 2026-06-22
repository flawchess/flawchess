---
id: SEED-061
status: dormant
planted: 2026-06-20
planted_during: v1.28 Tactic Tagging (Phase 129)
trigger_when: when next touching the Games-tab flaw/tactic filters, the Library query layer, or any tactic-filter accuracy work (fix together with SEED-060 on the same EXISTS)
scope: small
---

# SEED-061: Games-tab tactic filter omits the chip-confidence gate (matches below-threshold tactics)

## Why This Matters

The Flaws-tab tactic path (`build_flaw_filter_clauses`) ANDs
`tactic_confidence >= _TACTIC_CHIP_CONFIDENCE_MIN` (70) into each tactic branch, but the
Games-tab tactic-family EXISTS (`apply_game_filters`) deliberately omits it. The result is an
observable inconsistency: filtering the Games tab by e.g. `fork` can match a game whose only
fork motif has confidence below 70, yet that game's card shows **no fork chip** (chip display
is gated at 70). The user sees a game in a fork-filtered list with no visible fork, which reads
as a bug. The two filter surfaces should agree on what "has a tactic in family X" means
(the SEED-038 cross-tab-unification premise).

## When to Surface

**Trigger:** when next touching the Games-tab flaw/tactic filters, the Library query layer
(`query_utils.py` / `library_repository.py`), or any tactic-filter accuracy work. Best fixed in
the same pass as **SEED-060** (player_only_gate), since both gaps live on the same EXISTS predicate.

## Scope Estimate

**Small** — add one predicate (`_conf_col >= _TACTIC_CHIP_CONFIDENCE_MIN`) to the Games-tab tactic
branch plus a test. `_conf_col` is already unpacked (and currently discarded) in the loop, so the
value is in hand. Alternatively, if the asymmetry is intentional, document the rationale at the
call site instead of leaving it as a bare "Pitfall 3" reference.

## Breadcrumbs

- `app/repositories/query_utils.py` (~lines 236-255) — Games-tab tactic EXISTS; `_conf_col` is
  unpacked but not used in the branch predicate.
- `app/repositories/library_repository.py` (~lines 330-337) — Flaws-tab path that DOES gate on
  `conf_col >= _TACTIC_CHIP_CONFIDENCE_MIN`. Reference for the correct predicate.
- `_TACTIC_CHIP_CONFIDENCE_MIN` (= 70) — the shared chip-display threshold.
- Source: Phase 129 code review **WR-02** — see
  `.planning/phases/129-tactic-filter-ui/129-REVIEW.md`.

## Notes

Adjacent to SEED-060 (player_only_gate) on the same EXISTS — resolve together. Not a security
issue (still user-scoped); purely filter-display consistency. Add a test seeding a game whose only
family-X tactic is below 70 confidence and asserting it is NOT returned by the Games-tab filter
(matching chip-display semantics).
