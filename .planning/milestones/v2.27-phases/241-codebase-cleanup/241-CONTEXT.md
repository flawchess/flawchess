# Phase 241: Codebase Cleanup (naming + comments) - Context

**Gathered:** 2026-10-16
**Status:** Ready for planning

<domain>
## Phase Boundary

A hygiene pass with no architecture refactoring and no behavior change: strip planning-artifact tags from
comments, fix comments that contradict the code or name things that no longer exist, and apply the approved
renames. The full pre-merge gate passes with **no test assertion changed**. Any diff line that is neither a
comment, a docstring, a rename, nor a test title/name rewrite (D-13) needs a written justification.

Out of scope (fixed by ROADMAP): suspected bugs (INVENTORY §7.2), seed candidates (list only), all §1
contracts (DB/API/worker-protocol/Umami/Sentry/storage/testid/URL/env/LLM prompt text), `alembic/`,
`analysis/`, `stories/`, `scripts/archive/`, large-file splits, helper consolidation (D-04).

</domain>

<decisions>
## Implementation Decisions

### Glossary (STYLE-GUIDE §3.3)
- **D-01:** A canonical term binds **prose and new code only**: comments, docstrings, test titles, and code
  written from now on. Existing identifiers change only when they are in the inventory (§3 + §5), are
  covered by D-05, or fall under D-16. A comment that names a specific identifier uses that identifier's
  actual name.
- **D-02:** §3.3 is filled by adopting INVENTORY §2's "Suggested canonical" column for all 79 rows as
  printed, with the overrides below. Contract names stay whatever a row says. The first plan writes the
  resulting table into `241-STYLE-GUIDE.md` §3.3 (the row text can be condensed; the canonical choice can't
  change).
- **D-03:** Row #2 (user side of a you-vs-opponent comparison): internal canonical is **`player`**, paired
  with `opp`. `you_*` and `player_*` wire fields stay. Row #16 (a Train exercise): **"puzzle"** in prose and
  new code. `drill_*` tables and models stay, and `item` is used only for the SR bookkeeping row.
- **D-04:** Rows #43 (EVAL_CLIP_MAX_CP vs EVAL_OUTLIER_TRIM_CP), #59 (five eval formatters), #60 (three
  fen→ply helpers) and #79 (two iPad detectors whose thresholds may not be equivalent) are **seed candidates
  only**. The glossary records the canonical name, but no merge happens in this phase (a merge is a code
  change, and #79 risks a behavior change). Renames already in the inventory that touch these rows (for
  example `formatScore` → `formatEval` in EngineLines.tsx) still ship.
- **D-05:** Row #21 exception to D-01: **`walkthrough` → `tour` is one extra cross-layer rename** across
  the frontend (about 22 files: `useTrainWalkthrough` → `useTrainTour`, `WALKTHROUGH_*`,
  `WalkthroughTarget`/`Context`/`Input`/`Result`/`StepCopy`, `walkthroughTarget`/`Active`/`HideRef`,
  trainBotCopy constants, test files, `vi.mock` paths). It lands as a single commit:
  `refactor(naming): walkthrough → tour`. **Contracts stay:** `review_walkthrough` (telemetry wire field in
  `app/schemas/train.py:434`, and in the DB if persisted), testids `train-bot-walkthrough` /
  `btn-train-bot-walkthrough-next`, and any persisted or wire key in `frontend/src/lib/trainTelemetry.ts`
  (`ReviewCounters.walkthrough` is mapped to `review_walkthrough` and validated by `isAbsentOrBoolean`, so
  check whether it is stored in session/localStorage before renaming the field). Rename the internal
  identifiers only.
  — **Reversibility:** costly — about 22 files and tests; undoing it means a second sweep.

### Rename pruning
- **D-06:** **All 86 inventoried renames ship** (INVENTORY §3 X1–X9 and every row in §5), plus D-05 and
  any D-16 renames.
- **D-07:** For the 19 rows with an `M` verdict, **the verifier's name wins**: the "Old → new" column as
  printed. The auditor's original in the notes is ignored.
- **D-08:** Follow-ons in the rename notes: items worded "should follow", "follow" or "same commit" are
  **included**. Items worded "optional", "optionally" or "may follow" are **skipped** (e.g.
  `trans_counts` → `transposition_counts`, aligning `RenderedState.response`, and the TrainLeaderboardCard
  locals at :315/:416 are skipped; the Bots.tsx `celebrationHold` local is included).
- **D-09:** The multi-file groups the inventory says land together (G1 `_apply_*_filter` ×5;
  `onHoverPlyChange` + LibraryGameCard `hoverPly`; `matchingInsights` + `rendered` + `sectionBySection` +
  `mutation`; `BulletConfidencePopover` + `WdlConfidenceTooltip`; `totalGames` in LibraryPage + App.tsx;
  X8 + X9; `_override_for_key_move` + the trainPhoneGrade.ts JSDoc) each go in **one commit**.

### Comment fixes
- **D-10:** Apply **all A and M comment fixes** from INVENTORY §6 (the 3 `B` rows stay untouched). Each fix
  is **re-verified against the current code first**: the inventory predates three quick-task fixes
  (164754ce9, 07dd60fb4, 38baedf8b) and the renames shift line numbers. A fix whose target moved is applied
  at its new location. A fix whose target is gone or already correct is skipped and logged in the plan
  SUMMARY, never forced.
- **D-11:** Bare tags not in the inventory are handled by the STYLE-GUIDE §2.1 table (drop the tag and keep
  the why; delete a tag-only or provenance-only comment; replace "per D-04" with the decision). The tag
  pattern means planning IDs only: `Phase NNN` (2–3 digit numbers referring to GSD phases), `D-NN`,
  `SEED-NNN`, `CR-NN`, `WR-NN`, `FE-IN-NN`, `SC2`, `RESEARCH Pitfall N`, quick-task IDs (`261016-fwd`),
  REQ-IDs. **Not tags:** algorithm step labels like `Phase 1/2/3` in `compute_clock_diff_timeline`
  (INVENTORY seed #21), the chess "game phase" concept, and similar domain words.
- **D-12:** Open-seed pointers **stay as `(see SEED-NNN)`** (style call 1 approved). Open means the file is
  in `.planning/seeds/` (19 today), not `.planning/seeds/closed/` (184). Closed-seed references get the
  §2.1 treatment.

### Reach
- **D-13:** The tag strip and comment pass cover **`app/` + `frontend/src/` + `tests/`** (frontend tests
  under `frontend/src` included). `scripts/` (about 1,343 tagged lines), `docs/` and `bin/` are not touched
  in this phase.
- **D-14:** In tests, tags are also stripped from **non-comment test text**: describe/it/test titles (about
  603 frontend lines) and Python test function names carrying a tag (about 83, e.g. `def test_phase238_...`).
  Rewrite each one to say what it tests. No assertion changes. There are no snapshot files, so no snapshot
  can be orphaned. pytest `-k` selectors and test IDs that `pyproject.toml`/CI config may reference by name
  need a grep check before renaming.
- **D-15:** **Runtime strings are left alone** in `app/` and `frontend/src` (logger messages, exception
  text, dev-only labels), even when they carry a tag. The only changes are to comments, docstrings, test
  titles/names, and identifiers that are being renamed.
- **D-16:** A **production identifier carrying a planning tag that the inventory missed** (the kind of
  `_phase80_item_from_metrics` row) is renamed when its blast radius is local or module and it is not a
  §1 contract. A cross-layer one is listed in the SUMMARY for the owner instead of being renamed.
- **D-17:** Style call 2: internal names that mirror a wire field are **never renamed in this phase**: no
  `serialization_alias` additions and no explicit-mapping workarounds. (None of the 86 renames needs one.)
  — **Reversibility:** reversible — a later phase can still rename with an alias.

### Claude's Discretion
- Plan granularity and wave layout, within the ROADMAP plan shape: (1) comment cleanup per area as one
  parallel wave over disjoint files; (2) local and module renames per area; (3) cross-layer renames (X1–X9,
  D-05, the D-09 groups that cross layers) in sequence, one commit each. Keep plans small: about 11,000
  tagged lines in scope means splitting areas further (e.g. by directory) rather than running a few huge
  executors.
- The mechanical diff check (the diff outside comments, docstrings, renames and test titles is empty):
  tool and method are up to the planner (e.g. AST/token comparison after stripping comments and applying
  the rename map, plus `git diff --word-diff` review).
- Commit message shape follows STYLE-GUIDE §4.5: `chore(comments): <area>`, and
  `refactor(naming): old → new` for cross-layer renames.

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Phase inputs (research already done: skip the research step)
- `.planning/phases/241-codebase-cleanup/241-STYLE-GUIDE.md`: comment policy (§2), naming conventions
  (§3), off-limits contracts (§1), rename mechanics (§4: grep old names as strings, `npm run build`, mock
  paths). §3.3 gets filled per D-02.
- `.planning/phases/241-codebase-cleanup/241-INVENTORY.md`: §2 glossary (79 rows, D-02), §3 cross-layer
  renames X1–X9, §4 contract names to leave alone, §5 local/module renames by area, §6 comment fixes by
  area and category (772), §7 seed candidates and suspected bugs (out of scope, list only).
- `.planning/phases/241-codebase-cleanup/241-audit-workflow.js`: how the inventory was produced (area
  definitions and path splits, reusable for the per-area plan split).

### Project rules
- `CLAUDE.md`: pre-merge gate, ty compliance, "comment bug fixes" rule (bug-fix comments keep the what and
  why with the tag dropped), em-dash guidance.
- `frontend/CLAUDE.md`: references `WdlConfidenceTooltip` by name (update with the
  `ScoreConfidenceTooltip` rename) and lists testid rules.
- `.planning/ROADMAP.md` § Phase 241: goal, plan shape, out-of-scope list, run-alone rule.
- `.planning/seeds/` vs `.planning/seeds/closed/`: open/closed test for D-12.

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `scripts/check_function_size.py`: the nesting gate in the pre-merge gate. Renames can't affect it, but it
  runs anyway.
- Inventory area keys (backend-surface, backend-repositories, services-eval-engine,
  services-insights-stats, services-import-train-tactics, fe-components-train-analysis-bots,
  fe-components-data-views, fe-components-rest-and-root, fe-hooks, fe-pages-api-types-lib) already give a
  disjoint file split for the parallel comment wave. `tests/` needs its own areas (it was not part of the
  audit: only bare tags and test titles/names apply there).

### Established Patterns
- ty does not see `getattr`, `text()` SQL, Pydantic aliases, JSONB keys, `mock.patch("module.name")`
  strings or log `extra=` keys. esbuild strips types, so `npm run build` (tsc) is required, and untyped
  `vi.mock` factory keys (e.g. `isPending` in about 10 test files) are invisible to tsc. Grep old names as
  strings after every rename (STYLE-GUIDE §4.2–4.3).
- No frontend Prettier: never run `prettier --write`. ESLint only.
- Serial CI and `-n auto` locally can diverge. Run the full serial suite before the final merge if test
  names or fixtures moved.

### Integration Points
- Cross-layer renames touch `app/` ↔ `frontend/src` constants (X2 `PRESET_THRESHOLD`), `tests/` monkeypatch
  strings (X3), `scripts/` imports (X4 touches `scripts/tactic_tagger_report.py` and
  `scripts/benchmarks/chapter5.py`). A rename follows into `scripts/` even though D-13 keeps scripts out of
  the comment pass.
- Run alone: no other phase or quick task in this checkout while it runs (repo-wide diff, shared-checkout
  HEAD race).

</code_context>

<specifics>
## Specific Ideas

- The owner chose to bound the phase: glossary terms don't spawn renames, apart from the one deliberate
  exception (walkthrough → tour).
- Every inventory row is pre-approved, so executors don't need to come back to the owner for individual
  renames or comment fixes. Escalation is reserved for contract doubts and cross-layer D-16 finds.

</specifics>

<deferred>
## Deferred Ideas

- Helper and constant consolidation from glossary rows #43, #59, #60, #79 → seed candidates (D-04).
- Glossary-driven renames beyond the inventory (sf → stockfish prefix, hasError → hasFailed,
  live → isLive, boardMarkers → squareMarkers, the `_pct`/`_frac` rule applied to existing identifiers,
  uncelebrated, playedAs, etc.) → a possible later cleanup phase. The glossary only governs new code for
  now.
- Tag strip and comment pass for `scripts/` (non-archive), `docs/`, `bin/` → a later pass.
- Wire-field renames with explicit aliases → never in this phase (D-17).
- INVENTORY §7.1 seed candidates (50) and §7.2 suspected bugs: owner decides separately.

### Reviewed Todos (not folded)
- `2026-05-18-wr01-pt33-invalid-tailwind-score-axis-label.md`: a behavior fix (invalid class), not
  naming/comment hygiene.
- `2026-03-11-bitboard-storage-for-partial-position-queries.md`: a feature idea. Keyword-match noise.
- `172-deferred-review-findings.md`: a Phase 172 review leftover. Keyword-match noise.

</deferred>

---

*Phase: 241-codebase-cleanup*
*Context gathered: 2026-10-16*
