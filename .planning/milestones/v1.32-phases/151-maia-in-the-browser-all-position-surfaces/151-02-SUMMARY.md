---
phase: 151-maia-in-the-browser-all-position-surfaces
plan: 02
subsystem: legal
tags: [agpl, license, attribution, react, maia3, csslab]

# Dependency graph
requires: []
provides:
  - "Repo relicensed AGPL-3.0 (LICENSE + README)"
  - "Reusable MaiaAttribution component citing CSSLab/maia3, AGPL-3.0, model artifact path, and the Chessformer paper"
affects: [151-06]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Always-visible (non-hover-gated) attribution block for AGPL offer-source compliance, distinct from the codebase's usual hover/tap InfoPopover pattern"

key-files:
  created:
    - frontend/src/components/analysis/MaiaAttribution.tsx
    - frontend/src/components/analysis/__tests__/MaiaAttribution.test.tsx
  modified:
    - LICENSE
    - README.md

key-decisions:
  - "LICENSE: kept the exact FSF AGPL-3.0 boilerplate verbatim; only the 'How to Apply' appendix's <program name>/<year>/<author> placeholders were filled in with FlawChess / 2026 / Adrian Imfeld, matching GitHub's own AGPL-3.0 template convention"
  - "Also updated the Stockfish 'Engine Binaries (GPLv3 License Note)' section's one sentence about FlawChess's own license (was stale 'MIT licensed') to AGPL-3.0, since leaving it would contradict the relicense; the GPLv3 Stockfish-specific content is otherwise untouched"
  - "MaiaAttribution renders as an always-visible inline block (not a hover/tap Radix popover like InfoPopover/ScoreConfidencePopover elsewhere in the codebase) so the three offer-source links are present in the DOM without requiring interaction — matches AGPL's visibility expectation for a shipped model artifact better than a hover-gated tooltip"

requirements-completed: [LIC-01, LIC-02]

coverage:
  - id: D1
    description: "Repo LICENSE is the full AGPL-3.0 text (not MIT)"
    requirement: "LIC-01"
    verification:
      - kind: unit
        ref: "head -3 LICENSE | grep -qi AFFERO (plan verify command)"
        status: pass
    human_judgment: false
  - id: D2
    description: "README license badge, open-source bullet, Stockfish note, and License section all state AGPL-3.0; no residual license-MIT badge"
    requirement: "LIC-01"
    verification:
      - kind: unit
        ref: "grep -qi AGPL README.md && ! grep -q license-MIT README.md (plan verify command)"
        status: pass
    human_judgment: false
  - id: D3
    description: "MaiaAttribution component renders three citation links (CSSLab/maia3 source, AGPL-3.0 license text, Chessformer arXiv paper) plus the model artifact path"
    requirement: "LIC-02"
    verification:
      - kind: unit
        ref: "frontend/src/components/analysis/__tests__/MaiaAttribution.test.tsx (5 tests)"
        status: pass
    human_judgment: false

duration: 20min
completed: 2026-07-05
status: complete
---

# Phase 151 Plan 02: License Relicense + Maia Attribution Component Summary

**Repo relicensed MIT to AGPL-3.0 and a visible, always-rendered MaiaAttribution component citing CSSLab/maia3, the AGPL-3.0 text, and the Chessformer paper (arXiv:2605.19091), ready for Plan 06 to mount.**

## Performance

- **Duration:** ~20 min
- **Completed:** 2026-07-05
- **Tasks:** 2/2
- **Files modified:** 4 (2 modified, 2 created)

## Accomplishments

- `LICENSE` replaced with the full canonical GNU AGPL-3.0 text (sourced verbatim from the FSF's own text, not paraphrased), with the "How to Apply" appendix's placeholders filled in for FlawChess / 2026 / Adrian Imfeld
- `README.md` license badge, "Open source" bullet, Stockfish engine-binaries note, and the bottom License section all now state AGPL-3.0; added a one-line AGPL §13 network-service note to the License section
- New `MaiaAttribution` component: a compact, always-visible (non-hover-gated) block with three real anchors (`maia-attr-link-source` → github.com/CSSLab/maia3, `maia-attr-link-license` → gnu.org/licenses/agpl-3.0.html, `maia-attr-link-paper` → arxiv.org/abs/2605.19091) and the unmodified model artifact path in text
- 5 render tests covering the container testid, all three link hrefs, the paper citation text, and the artifact-path mention — all passing
- `npm run lint` and `npm run knip` both clean on the new component (no dead exports)

## Task Commits

Each task was committed atomically:

1. **Task 1: Relicense repo MIT -> AGPL-3.0 (LICENSE + README)** - `ad024604` (feat)
2. **Task 2: MaiaAttribution component — visible offer-source + citation notice** - `2c0b82d8` (feat)

_No TDD tasks in this plan; both tasks were single auto commits._

## Files Created/Modified

- `LICENSE` - Full canonical GNU AGPL-3.0 text, project name/copyright filled into the standard appendix
- `README.md` - License badge, open-source bullet, Stockfish note's FlawChess-license sentence, and License section all updated to AGPL-3.0
- `frontend/src/components/analysis/MaiaAttribution.tsx` - New visible attribution/offer-source component (not yet mounted; Plan 06 wires it in)
- `frontend/src/components/analysis/__tests__/MaiaAttribution.test.tsx` - 5 render tests for the three citation links + artifact path

## Decisions Made

- Sourced the AGPL-3.0 LICENSE text from the local `/usr/share/R/share/licenses/AGPL-3` file (the canonical FSF text bundled with R on this machine) rather than reconstructing it from memory, to guarantee byte-for-byte fidelity to the real license — only the "How to Apply" appendix's `<program name>`/`<year>`/`<name of author>` placeholders were substituted, matching the standard convention used by GitHub's own AGPL-3.0 license template.
- Updated one additional sentence in the README's existing Stockfish "Engine Binaries (GPLv3 License Note)" section — "All other FlawChess code is MIT licensed" — to AGPL-3.0. The plan's instruction to leave that section "intact" was read as preserving the Stockfish-specific GPL-3.0 content and structure; leaving FlawChess's own license mislabeled inside that section would directly contradict the relicense and the plan's must-have truth that all README license references state AGPL-3.0 (Rule 1 — bug/inconsistency fix).
- Built `MaiaAttribution` as an always-visible inline block rather than the codebase's usual hover/tap `InfoPopover` pattern (`ScoreConfidencePopover`, `WdlConfidenceTooltip`, etc.). AGPL offer-source/attribution notices are conventionally expected to be visible without requiring interaction (unlike the CLAUDE.md `text-xs` popover-body exception, which covers transient, opt-in asides) — hiding the notice behind a hover trigger would undercut the "visible" requirement in the plan's must-haves.

## Deviations from Plan

**1. [Rule 1 - Bug/inconsistency] Fixed stale "MIT licensed" reference inside the Stockfish engine-binaries README section**
- **Found during:** Task 1
- **Issue:** The plan's read_first/action only called out the badge, the "Open source" bullet, and the License section as things to update, but the Stockfish note's own prose ("All other FlawChess code is MIT licensed") would have been left contradicting the relicense if untouched.
- **Fix:** Changed that one sentence to "AGPL-3.0 licensed"; left the rest of the Stockfish/GPL-3.0-specific content unchanged.
- **Files modified:** README.md
- **Verification:** `grep -qi AGPL README.md && ! grep -q license-MIT README.md` passes; manual read confirms no residual MIT license claim about FlawChess's own code.
- **Committed in:** `ad024604` (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 bug/inconsistency)
**Impact on plan:** Necessary for correctness — the plan's own must-have truth ("README license references ... state AGPL-3.0") would otherwise fail. No scope creep; only the one sentence changed.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- `MaiaAttribution` is built, tested, and exported but **not mounted anywhere** — Plan 06 is expected to import it into the analysis layout once the human-move surfaces exist.
- LIC-01 (relicense) and the component half of LIC-02 are both complete. The remaining LIC-02 work (actually mounting the notice so it's visible in the running app) is explicitly deferred to Plan 06, per this plan's scope.
- No blockers for Plan 06 or the parallel ONNX-contract work in this wave.

---
*Phase: 151-maia-in-the-browser-all-position-surfaces*
*Completed: 2026-07-05*

## Self-Check: PASSED

- FOUND: LICENSE
- FOUND: frontend/src/components/analysis/MaiaAttribution.tsx
- FOUND: frontend/src/components/analysis/__tests__/MaiaAttribution.test.tsx
- FOUND: ad024604 (Task 1 commit)
- FOUND: 2c0b82d8 (Task 2 commit)
