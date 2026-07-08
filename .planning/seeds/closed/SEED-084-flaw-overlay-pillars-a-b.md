---
id: SEED-084
status: open
planted: 2026-07-05
planted_during: v1.32 Maia-3 Human-Move Enrichment milestone close — Phase 152 demoted from the roadmap
trigger_when: a future Maia-enrichment milestone revisits human-terms flaw interpretation on the analysis board
scope: medium (one browser-only phase extending the Phase 151/151.1 Maia + Stockfish surfaces; no DB/backend)
source: demoted from ROADMAP Phase 152 (Flaw Overlay, Pillars A + B) at v1.32 close — "not needed now"
related: SEED-081 (Maia-3 human-move enrichment milestone), SEED-083 (Stockfish-graded Maia moves, shipped as Phase 151.1), SEED-082 (human-playable-line engine)
---

# SEED-084: Flaw Overlay (Pillars A + B)

Demoted from **Phase 152** during the v1.32 milestone close — judged not needed for this
milestone. Captured verbatim so the design isn't lost; re-promote if a later Maia-enrichment
milestone picks the human-terms flaw interpretation back up.

## What it was

When the current move **is a flaw**, interpret it in human terms on top of the Phase 151 /
151.1 surfaces — a **salience × trainability** verdict banner plus a **Maia-WDL
practical-severity reframe** of how bad the flaw really is. Reuses the all-position "Moves by
Rating" chart + Maia WDL eval bar already shipped in Phase 151; browser-only, ephemeral, zero DB
writes (same posture as the rest of the v1.32 Maia surface).

## Requirements (were FLAW-01..04)

- **FLAW-01**: When the current move **is a flaw**, a **verdict banner** overlays the chart with
  the salience × trainability quadrant call ("Growth edge — drill this" / "Even masters fall for
  this" / "You rarely err here" / above-your-level).
- **FLAW-02**: The verdict derives **salience** = `P(blunder move | your ELO)` and
  **trainability** = `P(blunder | your ELO) − P(blunder | top ELO)` from the stored curve — an
  **endpoint** difference, robust to non-monotonic (hump/U) curve shapes, never a local slope.
- **FLAW-03**: The **Maia-WDL practical-severity reframe** is applied to the flaw — the human
  win% reframes how bad the flaw is relative to the objective Stockfish eval (Stockfish stays the
  objective source of truth; Maia adds the practical lens).
- **FLAW-04**: **Precision-first fallback** — where Maia's calibration is not trustworthy for the
  relevant ELO bucket, the verdict is **withheld** rather than shown wrong (consistent with the
  tactic-tag NULL-on-low-confidence stance).

## Success criteria (from the Phase 152 roadmap block)

1. When the current move is a flaw, a verdict banner overlays the chart with the salience ×
   trainability quadrant call (FLAW-01).
2. The verdict derives salience = `P(blunder move | your ELO)` and trainability =
   `P(blunder | your ELO) − P(blunder | top ELO)` as an endpoint difference from the stored
   curve — robust to non-monotonic (hump/U) curve shapes, never a local slope (FLAW-02).
3. The flaw carries a Maia-WDL practical-severity reframe alongside the objective Stockfish
   eval — the human win% reframes how bad the flaw is, with Stockfish staying the objective
   source of truth (FLAW-03).
4. Where Maia's calibration is not trustworthy for the relevant ELO bucket, the verdict is
   withheld rather than shown wrong (precision-first, consistent with the tactic-tag
   NULL-on-low-confidence stance) (FLAW-04).

## Recommendation

Re-promote to a **phase** when a future milestone returns to human-terms flaw coaching. Depends
on the Phase 151 / 151.1 surfaces (Moves-by-Rating chart + Maia WDL eval bar + Stockfish
grading), all now shipped. Scope is one browser-only phase — no backend, no DB, no schema change.
