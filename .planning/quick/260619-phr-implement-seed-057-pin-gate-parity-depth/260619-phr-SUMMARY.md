---
quick_id: 260619-phr
title: Implement SEED-057 — pin gate parity + depth-index fix
status: complete
date: 2026-06-19
source_seed: .planning/seeds/SEED-057-pin-gate-parity-and-depth-index-bug.md
---

# Quick Task 260619-phr — SEED-057 pin gate parity + depth-index fix

## What changed

`app/services/tactic_detector.py`:
- **`_pin_wins_material` (WR-01 parity + gate reorder):** the direct-capture loop started
  at `pin_board_idx + 1`, which iterated the *opponent's* moves for even-`k` pins (the
  common case, incl. the start position) because pov's moves sit at even move indices.
  Fixed the start to `pin_board_idx + (pin_board_idx % 2)` (first pov move at/after the
  pin board). **Also reordered the gate** so the replacement-guard REJECT runs before the
  direct-capture ACCEPT.
- **`detect_pin` (IN-01 depth):** returned the board index `k` as `depth`; every other
  motif returns a move index. Now returns `max(0, k - 1)` (board `k` follows move `k-1`;
  clamp for `k==0` where the pin predates the PV window).

`tests/scripts/tagger/precision_floors.py`:
- Re-measured pin row in the docstring table; updated the SEED-057 note; re-set
  `PRECISION_FLOOR["pin"]` 0.35 → 0.40 to lock in the gain.

`CHANGELOG.md`: added a `Fixed` bullet under `[Unreleased]`.
`.planning/seeds/SEED-057-*.md`: marked `status: resolved` with the key finding.

## Key finding (deviation from the seed's literal fix sketch)

The seed predicted the parity fix would *prune* incidental pins and raise precision. That
premise was wrong: `_pin_wins_material` has **two accept paths** (Check 1 direct-capture,
and the default `return True`) and **one reject path** (the replacement guard). Check 1 is
therefore an accept-path, not a prune-path — fixing its parity made it `return True`
*earlier*, short-circuiting the only rejection. Measured: the parity fix **alone**
regressed pin precision 0.413 → 0.393 (FP 478 → 518).

The fix that achieves the seed's actual goal is parity fix **plus reordering** the gate so
the replacement-guard rejection runs first. Semantically sound too: a pov piece capturing
the "pinned" piece on the very next ply is a grab, not a constraining pin.

## Measured results (offline CC0 harness, `test_detector_precision.py`)

| metric        | baseline | parity-only | **parity + reorder (shipped)** |
|---------------|---------:|------------:|-------------------------------:|
| pin P (TRAIN) | 0.413    | 0.393       | **0.440**                      |
| pin P (TEST)  | 0.411    | 0.391       | **0.439**                      |
| pin FP (TRAIN)| 478      | 518         | **428**                        |
| pin TP (TRAIN)| 336      | 336         | **336**                        |
| pin recall    | 0.279    | 0.279       | **0.279** (unchanged)          |

train→test precision delta ~0.000 (no overfitting). All other motifs unchanged.

## Verification

- `uv run pytest tests/scripts/tagger/test_detector_precision.py -o addopts=""` — **passed** (floor gate green at the raised 0.40 floor).
- `uv run pytest tests/services/test_tactic_detector.py` — **51 passed, 5 skipped** (fast per-commit guards).
- `ruff format` / `ruff check` / `ty check` on the touched files — **clean**.

## Deferred (out of scope, flagged)

- **Dev re-backfill** (`scripts/backfill_flaws.py --db dev --full-evald-only`) to confirm
  the post-127 pin count (6,312) drops without collapsing: DB-heavy, multi-minute, needs
  the drain worker. The offline CC0 harness is the authoritative precision signal (D-09);
  the re-backfill is a population sanity check. Re-run on demand if pin count matters
  operationally. Note: the shipped fix is **net pin-count-neutral on the fixture** (TP/FN
  flat, FP −50), so a dramatic count drop is not expected — the gain is precision, not volume.
- WR-02 (Sentry capture nit in `flaws_service.py`) and IN-02 (dead-code guards): explicitly
  not part of SEED-057.
