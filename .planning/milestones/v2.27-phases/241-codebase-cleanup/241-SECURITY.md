---
phase: "241"
slug: "codebase-cleanup"
status: verified
# threats_open = count of OPEN threats at or above workflow.security_block_on severity (the blocking gate)
threats_open: 0
asvs_level: 1
created: "2026-10-16"
---

# Phase 241 — Security

> Per-phase security contract: threat register, accepted risks, and audit trail. Built from the 70 plan-time STRIDE registers (State B, ASVS L1 short-circuit: threats_open 0, register authored at plan time).

---

## Trust Boundaries

| Boundary | Description | Data Crossing |
|----------|-------------|---------------|
| Source edits → runtime behavior | Comment, docstring, test-title and identifier edits must not change any executable token (strings, numbers, wire field names, SQL, markup, testids, Umami attributes, directives) | Source code only; no user data, no network, no new dependencies |
| Internal names → wire/persisted contracts | Renames stop at API fields, Literal values, storage keys, snapshot fields and generated files (D-17) | Field names in JSON payloads, sessionStorage/localStorage keys, generated TS |

---

## Threat Register

Mitigation evidence for every `mitigate` row: the phase-wide token diff (`cleanup.py diff --all-allow`, 1311 files, exit 0, 13 residue lines all allow-listed with reasons), `cleanup.py absent` (128 rename rows, 0 hits), zero generator drift, and the full pre-merge gate green on the phase head (241-70-SUMMARY.md), plus each plan's own scoped diff and targeted tests (per-plan SUMMARY.md).

| Threat ID | Category | Component | Severity | Disposition | Mitigation | Status |
|-----------|----------|-----------|----------|-------------|------------|--------|
| 241-01 T-241-01 | Tampering | §3.3 canonical choices | low | mitigate | Verify counts 79 rows and checks the seven override rows; any change to a printed canonical choice is visible in the row-by-row diff against INVENTORY §2 | closed |
| 241-01 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs in this plan | closed |
| 241-02 T-241-02 | Tampering | cleanup.py diff (a vacuous gate would certify code changes as comment-only) | high | mitigate | Selftest cases for string/number/name/directive changes, the live mutation check in Task 1, and the ancestor check on PHASE_BASE | closed |
| 241-02 T-241-03 | Tampering | app/core runtime strings (Sentry messages, exception text) edited during the pass | medium | mitigate | Scan never reports string tokens (D-15) and diff reports any changed string literal as residue | closed |
| 241-02 T-241-04 | Elevation of Privilege | apply-edits writing outside the cleanup scope | low | mitigate | apply-edits refuses out-of-scope paths and validates every `old` before any write | closed |
| 241-02 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs; stdlib-only Python | closed |
| 241-03 T-241-05 | Tampering | codemod editing code or string tokens | high | mitigate | Rewrites only prose-region text by column; selftest case for a tagged string literal; every plan's `diff` gate rejects any code-token change | closed |
| 241-03 T-241-06 | Repudiation | codemod changes nobody reviewed | medium | mitigate | Codemod prints every before/after pair; plans require a `git diff -U0` review and record counts in the SUMMARY | closed |
| 241-03 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-04 T-241-07 | Tampering | JSX comment deletion leaving or removing markup | high | mitigate | tokens mode drops only expression-less JSX containers and whitespace-only JSX text; any other markup token change is residue; mutation checks in Task 1 | closed |
| 241-04 T-241-08 | Tampering | testids / Umami event names edited as if prose | medium | mitigate | Only comments and test titles are prose; diff reports every string-literal change outside test titles | closed |
| 241-04 T-241-09 | Tampering | removed eslint-disable or @ts-expect-error hiding a real error | medium | mitigate | directive_heads multiset compared per file; lint and tsc build run in Task 2 | closed |
| 241-04 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No new packages; `npm --prefix frontend ci` only reinstalls the lockfile in a fresh worktree | closed |
| 241-05 T-241-10 | Tampering | app/models code tokens edited alongside comments | high | mitigate | `cleanup.py diff` over the scope must report zero residue against PHASE_BASE; ty and ruff run on the result | closed |
| 241-05 T-241-11 | Tampering | §1 contract names (columns, CHECK values) rewritten inside comments | low | accept | Comments do not bind the schema; the names stay exact by rule and the code tokens are unchanged | closed |
| 241-05 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-06 T-241-12 | Tampering | wire field names / Literal values changed during comment edits | high | mitigate | `cleanup.py diff` must report zero residue (every name and string token compared); ty runs on the result | closed |
| 241-06 T-241-13 | Information Disclosure | OpenAPI descriptions edited | low | accept | Field(description=...) strings are runtime strings and are not edited (D-15); diff would report any change | closed |
| 241-06 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-07 T-241-14 | Tampering | route paths / remote-worker JSON fields changed during comment edits | high | mitigate | `cleanup.py diff` zero residue over the scope (decorator path strings are tokens); ty on the result | closed |
| 241-07 T-241-15 | Repudiation | Sentry messages or tags reworded, breaking issue grouping | medium | mitigate | Only prose is edited; diff reports any string-literal change (D-15) | closed |
| 241-07 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-08 T-241-16 | Tampering | train_repository.py query code edited with its comments | high | mitigate | `cleanup.py diff` zero residue (every SQLAlchemy and text() token compared); ty on the result | closed |
| 241-08 T-241-17 | Information Disclosure | comments rewritten to include user data | low | accept | Only existing prose is rewritten; no data is read | closed |
| 241-08 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-09 T-241-18 | Tampering | filter predicates edited alongside their comments | high | mitigate | `cleanup.py diff` zero residue over the scope; ty on the result | closed |
| 241-09 T-241-19 | Denial of Service | a source-counting test silently broken by a deleted comment mention | low | mitigate | The family-count test runs in Task 1 and in the source-scan runner | closed |
| 241-09 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-10 T-241-20 | Tampering | query code edited with its comments | high | mitigate | `cleanup.py diff` zero residue over the scope; ty on the result | closed |
| 241-10 T-241-21 | Tampering | dead code removed under the cover of a comment fix | medium | mitigate | INV-L490 recorded LEFT; diff would report any removed code token | closed |
| 241-10 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-11 T-241-22 | Tampering | eval write code edited with its comments | high | mitigate | `cleanup.py diff` zero residue; ty on the result | closed |
| 241-11 T-241-23 | Tampering | a rewritten comment asserting a wrong invariant (single ply convention, delete-then-insert) that invites a later bug | medium | mitigate | Invariants listed in planner_assumptions; acceptance grep for the stale phrase; INVENTORY M rows applied as the verifier wrote them | closed |
| 241-11 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-12 T-241-24 | Tampering | drain code or re-export imports changed with comments | high | mitigate | `cleanup.py diff` zero residue and unchanged noqa directive heads; ty on the result | closed |
| 241-12 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-13 T-241-25 | Tampering | claim SQL or tier constants edited with comments | high | mitigate | `cleanup.py diff` zero residue over the scope; ty on the result | closed |
| 241-13 T-241-26 | Denial of Service | source-scanning invariant test broken by a docstring rewrite | low | mitigate | source_scan_tests.sh runs test_eval_utils and test_sharp_filler | closed |
| 241-13 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-14 T-241-27 | Tampering | detector predicates edited while rewriting their comments | high | mitigate | `cleanup.py diff` zero residue; a predicate restatement that disagrees with the code is a suspected bug and is left untouched (STYLE-GUIDE §2.2) | closed |
| 241-14 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-15 T-241-28 | Tampering | request, retry or normalization code edited with comments | high | mitigate | `cleanup.py diff` zero residue over the scope; ty on the result | closed |
| 241-15 T-241-29 | Information Disclosure | push_send prune capture rewritten to carry the endpoint path | medium | mitigate | INV-L826 keeps the "host only, never the path" rule as written; code tokens unchanged by diff | closed |
| 241-15 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-16 T-241-30 | Tampering | scheduler / scoring constants edited with their comments | high | mitigate | `cleanup.py diff` zero residue; the train score and leaderboard parity tests run via source_scan_tests.sh | closed |
| 241-16 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-17 T-241-31 | Tampering | LLM prompt strings edited as if they were comments | high | mitigate | Scan and codemod touch prose only; diff reports any string-token change; the golden user-prompt test runs in Task 1 | closed |
| 241-17 T-241-32 | Denial of Service | module-source invariant test broken by a comment mentioning a banned phrase | low | mitigate | Named in planner_assumptions; source_scan_tests.sh runs the module_source tests | closed |
| 241-17 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-18 T-241-33 | Tampering | zone values edited with their comments | high | mitigate | `cleanup.py diff` zero residue; the codegen run must leave frontend/src/generated unchanged | closed |
| 241-18 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-19 T-241-34 | Tampering | SQL builders or anonymization code edited with comments | high | mitigate | `cleanup.py diff` zero residue; ty on the result | closed |
| 241-19 T-241-35 | Information Disclosure | INV-L635 docstring misstates what leaves the database | low | mitigate | The row text states the dense-index rule; verify it against the query before writing | closed |
| 241-19 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-20 T-241-36 | Tampering | an assertion weakened or a test dropped during the edit | high | mitigate | `cleanup.py diff` compares every test-body token; equal collection counts before/after; the tests run | closed |
| 241-20 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-21 T-241-37 | Tampering | an assertion or golden scenario value changed during the edit | high | mitigate | `cleanup.py diff` compares every test-body token; equal collection counts; the tests run | closed |
| 241-21 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-22 T-241-38 | Tampering | an expected prompt string or assertion changed during the edit | high | mitigate | `cleanup.py diff` compares every string token; golden file untouched; the tests run | closed |
| 241-22 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-23 T-241-39 | Tampering | an assertion or monkeypatch target changed during the edit | high | mitigate | `cleanup.py diff` compares every test-body token incl. strings; equal collection counts; the tests run | closed |
| 241-23 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-24 T-241-40 | Tampering | conftest fixture or an assertion changed during the edit | high | mitigate | `cleanup.py diff` compares every token of conftest.py and the tests; equal collection counts; the tests run | closed |
| 241-24 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-25 T-241-41 | Tampering | a revision id string or assertion changed during the edit | high | mitigate | `cleanup.py diff` compares every string token; equal collection counts; the tests run | closed |
| 241-25 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-26 T-241-42 | Tampering | a precision floor, suppression entry or verdict threshold changed during the edit | high | mitigate | `cleanup.py diff` compares every token; the tagger gate and verdict tests run | closed |
| 241-26 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-27 T-241-43 | Tampering | an expected payload or assertion changed during the edit | high | mitigate | `cleanup.py diff` compares every string and token; equal collection counts; the tests run | closed |
| 241-27 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-28 T-241-44 | Tampering | hook code or a directive changed with its comments | high | mitigate | `cleanup.py diff` zero residue and equal directive heads; lint runs | closed |
| 241-28 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-29 T-241-45 | Tampering | hook code, worker paths or directives changed with comments | high | mitigate | `cleanup.py diff` zero residue and equal directive heads; lint runs | closed |
| 241-29 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-30 T-241-46 | Tampering | storage keys or telemetry field names changed with comments | high | mitigate | `cleanup.py diff` compares every string and identifier token; lint runs | closed |
| 241-30 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-31 T-241-47 | Tampering | a query key, param or directive changed with comments | high | mitigate | `cleanup.py diff` compares every string and identifier token plus directive heads; lint runs | closed |
| 241-31 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-32 T-241-48 | Tampering | a search constant changed with its comment, shifting bot strength | high | mitigate | `cleanup.py diff` zero residue (numeric literals are tokens); lint runs | closed |
| 241-32 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-33 T-241-49 | Tampering | asset paths, cache version or byte constants changed with comments | high | mitigate | `cleanup.py diff` zero residue; INV-L1307 LEFT; source-scan tests read these sources | closed |
| 241-33 T-241-50 | Repudiation | a rewritten comment claims edge-cache invalidation that does not happen, leading to a skipped purge after an asset bump | medium | mitigate | INV-L1370 edge claim written only after grepping that the URLs carry the version query | closed |
| 241-33 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-34 T-241-51 | Tampering | copy strings or telemetry caps changed with comments | high | mitigate | `cleanup.py diff` compares every string and numeric token; the parity tests run in Task 1 | closed |
| 241-34 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-35 T-241-52 | Tampering | a theme/zone value changed with its comment | high | mitigate | `cleanup.py diff` compares every string and numeric token; lint and source-scan tests run | closed |
| 241-35 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-36 T-241-53 | Tampering | JSX markup, testids or Umami attributes changed while deleting JSX comments | high | mitigate | `cleanup.py diff` drops only expression-less JSX containers; every other markup and string token is compared; lint runs | closed |
| 241-36 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-37 T-241-54 | Tampering | markup, testids or the reminder-intent write order changed with comments | high | mitigate | `cleanup.py diff` compares every markup and string token; lint runs | closed |
| 241-37 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-38 T-241-55 | Tampering | markup, testids or eval formatting changed with comments | high | mitigate | `cleanup.py diff` compares every markup, string and numeric token; lint runs | closed |
| 241-38 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-39 T-241-56 | Tampering | Sentry capture strings or markup changed with comments | high | mitigate | `cleanup.py diff` compares every string and markup token; lint runs | closed |
| 241-39 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-40 T-241-57 | Tampering | URL param handling or markup changed while deleting tombstones | high | mitigate | `cleanup.py diff` compares every token; lint runs | closed |
| 241-40 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-41 T-241-58 | Tampering | a wire field, API path or auth-redirect condition changed with comments | high | mitigate | `cleanup.py diff` compares every identifier and string token; lint runs | closed |
| 241-41 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-42 T-241-59 | Tampering | testid templates or markup changed while deleting JSX comments | high | mitigate | `cleanup.py diff` compares every markup and template token; lint runs | closed |
| 241-42 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-43 T-241-60 | Tampering | chart JSX structure changed while deleting JSX comments | high | mitigate | `cleanup.py diff` compares every JSX token except comment-only containers; lint runs | closed |
| 241-43 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-44 T-241-61 | Elevation of Privilege | nav/route gating code changed with comments (a locked route becomes reachable) | high | mitigate | `cleanup.py diff` compares every token of App.tsx; lint and source-scan tests run | closed |
| 241-44 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-45 T-241-62 | Elevation of Privilege | admin component gating changed with comments | high | mitigate | `cleanup.py diff` compares every token; lint runs | closed |
| 241-45 T-241-63 | Tampering | a tooling directive removed and hiding dead code | low | mitigate | Only the inventoried @knipignore goes, allow-listed with its reason; knip runs | closed |
| 241-45 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-46 T-241-64 | Tampering | an assertion or mock changed while rewriting a title | high | mitigate | `cleanup.py diff` normalizes only title literals and compares every other token; equal vitest counts; tests run | closed |
| 241-46 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-47 T-241-65 | Tampering | an assertion, testid query or mock changed while rewriting a title | high | mitigate | `cleanup.py diff` normalizes only title literals; equal vitest counts; tests run | closed |
| 241-47 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-48 T-241-66 | Tampering | an assertion, option key or mock changed while rewriting a title | high | mitigate | `cleanup.py diff` normalizes only title literals; equal vitest counts; tests run | closed |
| 241-48 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-49 T-241-67 | Tampering | an expected copy string or assertion changed while rewriting a title | high | mitigate | `cleanup.py diff` normalizes only title literals; equal vitest counts; tests run | closed |
| 241-49 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-50 T-241-68 | Tampering | a source-text expectation or assertion changed while rewriting a title | high | mitigate | `cleanup.py diff` normalizes only title literals; equal vitest counts; tests run | closed |
| 241-50 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-51 T-241-69 | Tampering | a testid query, mock or assertion changed while rewriting a title | high | mitigate | `cleanup.py diff` normalizes only title literals; equal vitest counts; tests run | closed |
| 241-51 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-52 T-241-70 | Tampering | a scoped rename (`full_hash` label) spilling into the DB column name | high | mitigate | canon_paths-scoped row, before/after occurrence count, ty and the stats tests | closed |
| 241-52 T-241-71 | Tampering | a remote-worker JSON field renamed with a local | high | mitigate | Only handler locals are renamed; diff over eval_remote.py reports any string-token change | closed |
| 241-52 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-53 T-241-72 | Tampering | tuple values or the upsert filter changed with the rename | high | mitigate | diff reports any string-token change; write-path golden and eval_apply tests run | closed |
| 241-53 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-54 T-241-73 | Tampering | prompt output changed by a rename touching a string | high | mitigate | Only identifiers and docstrings change; diff reports string-token changes; the golden user-prompt test runs in Tasks 2 and 3 | closed |
| 241-54 T-241-74 | Tampering | the TcBucket swap changing the accepted Literal values | medium | mitigate | TimeControlBucket is the same four-value Literal; ty checks every use; endgame/insights tests run | closed |
| 241-54 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-55 T-241-75 | Tampering | a generic name (`gc`) rename spilling into unrelated code | medium | mitigate | canon_paths-scoped row; diff and the openings tests | closed |
| 241-55 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-56 T-241-76 | Tampering | a wire field (`bot_elo`, `user_result`) renamed along with its internal mirror | high | mitigate | canon_paths-scoped rows; per-file before/after occurrence counts; bots router and schema tests run (D-17) | closed |
| 241-56 T-241-77 | Tampering | `game_dict` → `game` shadowing an outer `game` binding | medium | mitigate | Scope check before renaming; SKIPPED with reason if a shadow exists; import tests run | closed |
| 241-56 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-57 T-241-78 | Tampering | a stale vi.mock path after the file rename makes a test exercise the real module | medium | mitigate | absent over frontend/src for the old stem; TrainScoreScreen tests run; knip flags orphaned modules | closed |
| 241-57 T-241-79 | Tampering | a testid or Umami string renamed with an identifier | medium | mitigate | diff reports any string-token change outside the file-stem canonicalization | closed |
| 241-57 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-58 T-241-80 | Tampering | botDrawOffer being a persisted snapshot key | high | mitigate | Explicit snapshot grep before renaming; stop and flag if persisted; bot tests run | closed |
| 241-58 T-241-81 | Tampering | stale vi.mock path / factory key leaving a test unmocked | medium | mitigate | absent over the old names incl. strings; Bots tests run; knip checks orphaned modules | closed |
| 241-58 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-59 T-241-82 | Tampering | renaming board PlayerBar or OverallSection's formatScore by mistake | medium | mitigate | canon_paths-scoped rows; unchanged occurrence counts in the excluded files; tsc build and tests | closed |
| 241-59 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-60 T-241-83 | Tampering | the arrow color value or equality changed with the rename | medium | mitigate | diff shows identical value tokens; board and arrowColor tests plus the Python arrow-consistency test run | closed |
| 241-60 T-241-84 | Tampering | a shadowed `live` renamed, changing which value a callback reads | medium | mitigate | Only the outer binding renamed; canon_paths-scoped row; reveal-tree tests run | closed |
| 241-60 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-61 T-241-85 | Tampering | a stale mock path or factory key turns a test into a different test | medium | mitigate | absent for the popover names; per-file isPending counts; the affected tests run | closed |
| 241-61 T-241-86 | Tampering | an unrelated `isPending` (mutation state) renamed | medium | mitigate | Only useEvalCoverage factory keys change; counts recorded; tests run | closed |
| 241-61 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-62 T-241-87 | Tampering | a global `window` reference renamed with the prop | medium | mitigate | canon_paths-scoped row; per-token check; tsc catches an undefined `windowSize`; chart tests run | closed |
| 241-62 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-63 T-241-88 | Elevation of Privilege | nav gating expression changed while renaming the count | medium | mitigate | diff proves the expression tokens are identical after canonicalization; App tests run | closed |
| 241-63 T-241-89 | Tampering | the board MiniBoard renamed instead of the bookmark one | medium | mitigate | canon_paths limited to position-bookmarks/; board tests run; tsc build | closed |
| 241-63 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-64 T-241-90 | Tampering | an API param key renamed with its local | medium | mitigate | Only locals renamed; diff reports any object-key/string change; hook tests run | closed |
| 241-64 T-241-91 | Tampering | a testid containing 'sidebar' changed with the drawer state | medium | mitigate | testids are strings outside canonicalization; Openings render tests query them | closed |
| 241-64 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-65 T-241-92 | Tampering | a testid template value changed with the prop rename | medium | mitigate | diff compares template literal tokens; chip tests query the testids | closed |
| 241-65 T-241-93 | Tampering | EvalChart's real-hover state renamed with LibraryGameCard's scrub ply | medium | mitigate | canon_paths-scoped row; unchanged occurrence count in EvalChart.tsx; chart tests run | closed |
| 241-65 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-66 T-241-94 | Tampering | a monkeypatch string left on the old name silently patches nothing (raising=True default makes it fail loudly) | medium | mitigate | absent check covers tests/; the four strings are counted; the Stage B tests run | closed |
| 241-66 T-241-95 | Information disclosure | SolveTotals fields leaking into a response model under a new key | low | mitigate | confirm no schema builds from SolveTotals by field name before renaming; tests/routers/test_train.py runs | closed |
| 241-66 T-241-96 | Tampering | a D-16 rename that hits a §1 contract (DB column, API field, Sentry tag) | high | mitigate | contract check before each D-16 rename; cross-layer finds are reported, not renamed | closed |
| 241-66 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-67 T-241-97 | Tampering | chip confidence floor value or SQL predicate changed while consolidating names | high | mitigate | diff compares number tokens (70 must be unchanged); test_chapter5_sql asserts the predicate text and benchmark/app parity; library repository tests run | closed |
| 241-67 T-241-98 | Repudiation | attempt-cap reporting silently dropped if the renamed keyword is not passed | medium | mitigate | ty flags unknown or missing keyword arguments; eval_apply and remote-worker tests run; log text unchanged | closed |
| 241-67 T-241-99 | Tampering | X7 rename leaking into unrelated eg_*/ne_* endgame locals | low | mitigate | canon_paths scoped to two files; absent_paths scoped to the function's module | closed |
| 241-67 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-68 T-241-100 | Tampering | entry-lane and full-lane writers swapped while renaming (the +1 shift difference corrupts evals) | high | mitigate | only the unqualified names change; `_apply_full_eval_results` / `_FullPlyEvalTarget` are untouched; diff canonicalizes old → new and reports any other name change; the entry-submit and drain tests run | closed |
| 241-68 T-241-101 | Tampering | Similar preset bound value or the gap parameters changed | medium | mitigate | diff compares number tokens; the frontend build and filter tests run | closed |
| 241-68 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-69 T-241-102 | Tampering | persisted `walkthrough` snapshot field renamed, so a reload drops the stored flag (isAbsentOrBoolean accepts absence silently) | high | mitigate | the field and its accesses are excluded from the rename by name; the residual-spelling gate allows walkthrough only in the three telemetry files and the acceptance grep proves only the field remains there; trainRevealCache and telemetry tests run | closed |
| 241-69 T-241-103 | Tampering | a testid or `review_walkthrough` changed by a whole-word replace (hyphen and underscore boundaries) | high | mitigate | compound-only scripted replaces; the bare-word row is scoped to TrainSolveScreen.tsx; contract-token count compared against HEAD~1 | closed |
| 241-69 T-241-104 | Tampering | a D-16 rename hitting a frontend contract (Umami event, storage key, URL key) | medium | mitigate | contract check before each rename; cross-layer finds reported, not renamed | closed |
| 241-69 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |
| 241-70 T-241-105 | Tampering | a behavior change hidden among comment edits across plans | high | mitigate | phase-wide token diff against PHASE_BASE with every rename map; every allowed residue justified; full and serial test suites | closed |
| 241-70 T-241-106 | Tampering | allow lists widened to make the final gate pass | medium | mitigate | every allowed item is printed with its reason and copied into the SUMMARY; a residue without a reason stops the plan | closed |
| 241-70 T-241-107 | Repudiation | an inventory row silently dropped | low | mitigate | set equality between INVENTORY §6 row ids and ledger final statuses; DEFERRED lines checked against their target ledgers | closed |
| 241-70 T-241-SC | Tampering | npm/pip/cargo installs | low | accept | No package installs | closed |

*Status: open · closed · open — below high threshold (non-blocking)*
*Severity: critical > high > medium > low — only open threats at or above workflow.security_block_on count toward threats_open*
*Disposition: mitigate (implementation required) · accept (documented risk) · transfer (third-party)*

---

## Accepted Risks Log

| Risk ID | Threat Ref | Rationale | Accepted By | Date |
|---------|------------|-----------|-------------|------|
| AR-241-001 | 241-01 T-241-SC | No package installs in this plan | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-002 | 241-02 T-241-SC | No package installs; stdlib-only Python | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-003 | 241-03 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-004 | 241-04 T-241-SC | No new packages; `npm --prefix frontend ci` only reinstalls the lockfile in a fresh worktree | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-005 | 241-05 T-241-11 | Comments do not bind the schema; the names stay exact by rule and the code tokens are unchanged | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-006 | 241-05 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-007 | 241-06 T-241-13 | Field(description=...) strings are runtime strings and are not edited (D-15); diff would report any change | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-008 | 241-06 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-009 | 241-07 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-010 | 241-08 T-241-17 | Only existing prose is rewritten; no data is read | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-011 | 241-08 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-012 | 241-09 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-013 | 241-10 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-014 | 241-11 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-015 | 241-12 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-016 | 241-13 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-017 | 241-14 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-018 | 241-15 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-019 | 241-16 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-020 | 241-17 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-021 | 241-18 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-022 | 241-19 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-023 | 241-20 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-024 | 241-21 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-025 | 241-22 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-026 | 241-23 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-027 | 241-24 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-028 | 241-25 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-029 | 241-26 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-030 | 241-27 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-031 | 241-28 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-032 | 241-29 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-033 | 241-30 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-034 | 241-31 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-035 | 241-32 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-036 | 241-33 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-037 | 241-34 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-038 | 241-35 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-039 | 241-36 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-040 | 241-37 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-041 | 241-38 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-042 | 241-39 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-043 | 241-40 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-044 | 241-41 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-045 | 241-42 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-046 | 241-43 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-047 | 241-44 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-048 | 241-45 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-049 | 241-46 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-050 | 241-47 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-051 | 241-48 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-052 | 241-49 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-053 | 241-50 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-054 | 241-51 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-055 | 241-52 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-056 | 241-53 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-057 | 241-54 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-058 | 241-55 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-059 | 241-56 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-060 | 241-57 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-061 | 241-58 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-062 | 241-59 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-063 | 241-60 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-064 | 241-61 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-065 | 241-62 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-066 | 241-63 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-067 | 241-64 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-068 | 241-65 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-069 | 241-66 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-070 | 241-67 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-071 | 241-68 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-072 | 241-69 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |
| AR-241-073 | 241-70 T-241-SC | No package installs | plan-time register (owner-approved plan) | 2026-10-16 |

*Accepted risks do not resurface in future audit runs.*

---

## Security Audit Trail

| Audit Date | Threats Total | Closed | Open | Run By |
|------------|---------------|--------|------|--------|
| 2026-10-16 | 177 | 177 | 0 | execute-phase orchestrator (secure-phase, L1 short-circuit) |

---

## Sign-Off

- [x] All threats have a disposition (mitigate / accept / transfer)
- [x] Accepted risks documented in Accepted Risks Log
- [x] `threats_open: 0` confirmed
- [x] `status: verified` set in frontmatter

**Approval:** verified 2026-10-16
