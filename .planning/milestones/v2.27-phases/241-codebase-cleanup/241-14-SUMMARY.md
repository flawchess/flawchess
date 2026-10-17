---
phase: 241-codebase-cleanup
plan: 14
subsystem: backend-services
tags: [cleanup, comments, tactic-detector, forcing-line-gate, flaws-service]

requires:
  - phase: 241-02
    provides: "cleanup.py scan/apply-edits/diff/ledger and source_scan_tests.sh"
  - phase: 241-03
    provides: "cleanup.py codemod"
provides:
  - "tactic_detector.py, forcing_line_gate.py, flaws_service.py, flaw_delta_zones.py and tactic_delta_zones.py free of planning tags and bug chronology, with an empty token diff against PHASE_BASE"
  - "ledgers/241-14.txt: all 27 INVENTORY section 6 rows of the scope are APPLIED"
affects: [241-56]

actuals:
  tokens: 90000
  tasks: 2
  commits: 2
plan_head_before: 297158250c71be5ad8a6dd1953ca3946d662ba21
plan_head_after: e8a8cb6b4b3b0365124e7bf9b7bfa15a213c40c9

key-files:
  created:
    - .planning/phases/241-codebase-cleanup/ledgers/241-14.txt
  modified:
    - app/services/tactic_detector.py
    - app/services/forcing_line_gate.py
    - app/services/flaws_service.py
    - app/services/flaw_delta_zones.py
    - app/services/tactic_delta_zones.py

key-decisions:
  - "Bug chronology (Bug A / Bug B, 'fixed in Phase 133', 'the prior port did X') became rules of the form 'Don't X: Y breaks' with the measured evidence kept (oracle_compare counts), the dated provenance dropped"
  - "The detect_sacrifice persistence-check essay keeps its three failed-rule bullets and the pointer to precision_floors.py but names fixture rows generically instead of by realgame_tags.csv row number"
  - "Comments that name an identifier use its current name: user_result / subject_result and _TACTIC_CHIP_CONFIDENCE_MIN stay until 241-56 and the rename plans"

status: complete
completed: 2026-10-16
---

# Phase 241 Plan 14: Tactic detector, forcing-line gate and flaw services Summary

**The tactic detector, forcing-line gate, flaw kernel and both delta-zone registries now state their predicates and gates as rules, with no planning tags and no bug chronology, and a zero-residue token diff against PHASE_BASE.**

## Accomplishments

- `tactic_detector.py`: 145 tagged lines gone. Dovetail, hook, arabian and boden/double-bishop docstrings restate the predicate the code implements (each read first), each with at most one "do not X: Y breaks" line. Stale facts fixed: `_GEOMETRIC_REGISTRY` ranks (discovered-check 4, discovered-attack 5, trapped-piece 6), the `_is_hanging` consumer note (only `detect_self_interference` uses it), the deflection `boards[k-1]` definition, the `EndgameClassInt` line number, the tier-3 floor list (no `clearance`), the x-ray "D-03 cutoff" paragraph, the "DO NOT EDIT interference regression lock" banner, and a pointer to a function that does not exist (`_dispatch_tier_candidates` is `_collect_non_mate_candidates`).
- `forcing_line_gate.py`: Phase 144 / VALID-02 / TAGFIX / D-NN provenance removed; `ALREADY_WINNING_CP_THRESHOLD` documented at its real value (800); `_is_forced_mate_firing` states that it reads the raw firing index.
- `flaws_service.py`: 48 tagged lines gone. `GameNotAnalyzed` wording, `miss/lucky` adjacency wording, the `flaw_pv_blobs` / `blobs_pending` / empty-list sentinel docs, `_classify_impact` and the both-movers comment rewritten as rules. Line-number pointers replaced by function names; `eval_drain._post_move_eval` corrected to `eval_apply._post_move_eval`.
- `flaw_delta_zones.py`, `tactic_delta_zones.py`: tags removed, `ZoneBand` docstring made unit-neutral, `ZONE_TC_FOR` documented with its single consumer.

## Ledger (ledgers/241-14.txt)

27 rows, all APPLIED, each re-verified against the current code first (D-10): INV-L748, L753, L763, L768, L769, L770, L771, L781, L782, L783, L784, L785, L786, L797, L798, L799, L804, L805, L811, L812, L815, L816, L831, L832, L833, L840, L841. No SKIPPED, LEFT or DEFERRED rows. No secondary-clause notes for rows owned by another plan.

## Codemod versus hand edits

| File | Codemod lines | Hand-edited lines (flagged by codemod or scan) | Pair edits applied |
|---|---|---|---|
| tactic_detector.py | 66 | 145 | about 125 |
| forcing_line_gate.py, flaws_service.py, flaw_delta_zones.py, tactic_delta_zones.py | 96 | 94 | about 110 |

`git diff -U0` was reviewed after each codemod run. One codemod artifact was fixed by hand (a lowercase `k` capitalized to `K is board index`); the `^\s*(#|//|\*)\s*[:;,]\s` grep found no punctuation-led comment.

## Non-inventoried fixes

- Dropped references to planning documents that were not tags: `132-RESEARCH.md`, `105-01-PLAN.md`, `CONTEXT.md §...`, `RESEARCH §Pattern 6`, `[ASSUMED]`.
- Dropped dev/prod row counts and TEST precision figures that were provenance (clearance review, pin fix, trapped-piece FP count, 33-of-302 recapture rows); kept the oracle_compare detection counts that justify a "do not reintroduce" rule.
- Re-wrapped three comments the rewrite had pushed over 100 columns; the one remaining over-long line in flaws_service.py (line 160) is pre-existing.

## Deviations from Plan

None - plan executed as written. The environmental notes below are not plan deviations.

## Gates (final tree)

| Command | Result |
|---|---|
| `cleanup.py scan --gate --scope scopes/241-14.txt` | exit 0 (5 files, 0 matches) |
| `cleanup.py diff --scope scopes/241-14.txt` | exit 0 (5 selected, 5 changed, no residue) |
| `cleanup.py ledger --scope scopes/241-14.txt --ledger ledgers/241-14.txt` | exit 0 |
| `ruff check app/services`, `ruff format --check app/services` | clean |
| `ty check app/ tests/ scripts/` | all checks passed (baseline was clean too) |
| `source_scan_tests.sh --fe` | 9 files, 131 tests passed |
| Python half of `source_scan_tests.sh`, run serially without `-n 4` | 95 + 5 passed |
| `pytest tests/services/test_tactic_detector.py test_flaws_service.py test_forcing_line_gate.py test_tactic_delta_zones.py test_flaw_delta_zones.py` | 395 passed, 7 skipped |

Environmental note: sibling executors share the dev Postgres, so pytest ran serially (no `-n`), as instructed. `uv sync --group maia-inference` and `npm --prefix frontend ci` were run in the fresh worktree (lockfile only, no new packages).

## Task Commits

1. **Task 1: app/services/tactic_detector.py** - `9b0115986` (`chore(comments): app/services/tactic_detector`)
2. **Task 2: forcing_line_gate, flaws_service, delta zones** - `e8a8cb6b4` (`chore(comments): app/services (forcing_line_gate, flaws, delta zones)`)

## Known Stubs

None.

## Threat Flags

None. T-241-27 mitigated: `cleanup.py diff` reports zero residue for all five files, and every predicate restatement was checked against the code before writing (no disagreement found, so no suspected bug to flag).

## Self-Check: PASSED

Files verified present: ledgers/241-14.txt, this SUMMARY, and the five modified services. Commits `9b0115986` and `e8a8cb6b4` are ancestors of HEAD.
