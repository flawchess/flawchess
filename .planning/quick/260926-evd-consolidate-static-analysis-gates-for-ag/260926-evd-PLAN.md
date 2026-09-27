---
quick_id: 260926-evd
slug: consolidate-static-analysis-gates-for-agentic-engineering
date: 2026-09-26
phase: quick-260926-evd
plan: 01
type: execute
wave: 1
depends_on: []
autonomous: true
requirements: [D-01, D-02, D-03]
files_modified:
  - pyproject.toml
  - scripts/check_function_size.py
  - tests/scripts/test_check_function_size.py
  - frontend/eslint.config.js
  - .github/workflows/ci.yml
  - CLAUDE.md
  - docs/dev-tooling.md
  - frontend/CLAUDE.md
  - app/repositories/library_repository.py
  - app/services/tactic_detector.py
  - frontend/src/pages/Analysis.tsx

estimate:
  tokens: 110000
  raw_tokens: 110000
  tasks: 3
  confidence: low

must_haves:
  truths:
    - "D-03: nesting depth <= 4 is the only hard complexity gate. `uv run python scripts/check_function_size.py app/ --fail-over-depth 4` exits 1 only on a depth breach; a flat 250-logic-line function exits 0 (the script still reports raw_loc/logic_loc in --json)."
    - "D-03: ruff's complexity-count rules (mccabe, too-many-branches, too-many-statements) are no longer enabled; `ruff check --show-settings` lists none of them and pyproject.toml carries no baseline block for them."
    - "D-03: `npm run lint` resolves `max-depth` 4 for every TS/TSX file and resolves neither `complexity` nor `max-statements` for any file; the Phase 215 per-file ratchet region is gone except the single max-depth entry for src/lib/__tests__/reminderSlotState.test.ts."
    - "D-02: `uv run ruff check .` exits 0 with select E4/E7/E9/F plus extend-select TID251, B, ASYNC, DTZ; `import requests` / `import berserk` is flagged (TID251) anywhere in the repo; naive `datetime.datetime.now()` in app/ is flagged (DTZ005); tz-aware `datetime.now(timezone.utc)` is NOT flagged; FastAPI `Query(...)`/`Depends(...)` defaults are NOT flagged (B008 cleared by extend-immutable-calls config, not by a baseline)."
    - "D-02: each category landed as its own commit (TID251, B, ASYNC, DTZ), with pre-existing app/ findings baselined per file with specific codes and non-app dirs scoped out by glob."
    - "D-01: the CLAUDE.md pre-merge gate type-checks the frontend (`npm run build` = `tsc -b && vite build`) and matches CI's gate steps (ruff, depth-only function-size gate, eslint, build, knip)."
    - "D-03: CLAUDE.md, docs/dev-tooling.md and frontend/CLAUDE.md state depth as the only hard rule and LOC + cognitive complexity as soft, report-only guidance, in less text than before."
  artifacts:
    - pyproject.toml
    - scripts/check_function_size.py
    - tests/scripts/test_check_function_size.py
    - frontend/eslint.config.js
    - .github/workflows/ci.yml
    - CLAUDE.md
    - docs/dev-tooling.md
    - frontend/CLAUDE.md
  key_links:
    - "CLAUDE.md pre-merge gate block <-> .github/workflows/ci.yml steps: same function-size invocation (depth flag only), same ruff/eslint commands, both run the frontend type check (`npm run build`) and knip."
    - "pyproject.toml [tool.ruff.lint] extend-select + per-file-ignores -> `uv run ruff check .` (CI Lint step and pre-merge gate); the `ruff check . --fix` gate step must never autofix the baselined B010 site (ignored rules are not fixed)."
    - "frontend/eslint.config.js base `**/*.{ts,tsx}` rules -> `npm run lint` (CI + gate) and eslint.config.sonarjs.mjs (spreads the base config for report-only `npm run lint:cognitive`)."
---

<objective>
Consolidate the static-analysis gates so agents get few, deterministic, file:line-precise errors instead of ~9 overlapping complexity measures with a large ratchet baseline.

Locked decisions (from the planning context, referenced as D-NN below):
- **D-01**: close the pre-merge gate gap. The gate runs `npm run lint && npm test -- --run`, neither of which type-checks. Add `npm run build` (chosen over bare `npx tsc -b`: measured 2026-09-26, `tsc -b` ~8 s warm vs `npm run build` ~16 s, so the extra ~8 s buys the exact CI step "Type check and build (tsc + vite)", which also catches Vite import-resolution/bundling failures that bare tsc misses). Also add `npm run knip` (~2 s, already a CI step) so the gate that "replaces pre-merge CI" covers every CI-only frontend check (planner's discretion, CI-parity constraint).
- **D-02**: mechanize prose rules via ruff: TID251 banned-api, then B, ASYNC, DTZ, one category per commit, config-fix what is trivially safe, baseline the rest, no large hand-fixes, keep the explicit-pin philosophy comment.
- **D-03**: nesting depth <= 4 is the only hard complexity gate (backend check_function_size, frontend eslint max-depth); one report-only cognitive measure per stack (complexipy, `npm run lint:cognitive`); drop ruff complexity-count rules, the LOC gate, eslint `complexity`/`max-statements` and their baselines; remove dead pragmas; shorten the docs.

Two planning-time findings that change the literal instructions (both verified 2026-09-26, the executor must re-check):
1. `scripts/check_function_size.py` defaults its LOC threshold to 200, so dropping the CLI flag from CI would NOT drop the LOC gate. The script itself must stop gating LOC (Task 1).
2. D-02 asked to ban `datetime.datetime.now` "after checking legitimate use". It has legitimate use: `datetime.now(timezone.utc)` is called in ~9 app/ sites outside endpoints-with-dev-clock (app/middleware/last_activity.py, app/repositories/import_job_repository.py x3, app/routers/eval_remote.py lease stamps x4, app/core/dev_clock.py itself). TID251 bans the name regardless of arguments, so it is NOT banned. The naive form is caught by DTZ005 once DTZ is enabled (already 0 findings), and the endpoint-only `dev_now_utc` rule is not expressible as an API ban.

Purpose: fewer, sharper gates; prose rules become lint errors; a frontend type error can no longer reach `main` through the local gate.
Output: updated ruff/eslint config, depth-only function-size script + tests, CI step, CLAUDE.md gate + condensed prose, docs/dev-tooling.md, frontend/CLAUDE.md.
</objective>

<execution_context>
@~/.claude/gsd-core/workflows/execute-plan.md
@~/.claude/gsd-core/templates/summary.md
</execution_context>

<context>
@CLAUDE.md
@frontend/CLAUDE.md
@docs/dev-tooling.md
@pyproject.toml
@frontend/eslint.config.js
@frontend/eslint.config.sonarjs.mjs
@scripts/check_function_size.py
@tests/scripts/test_check_function_size.py
@.github/workflows/ci.yml

Working rules for this plan:
- Work directly on `main`. Before EVERY commit run `git branch --show-current` and confirm it prints `main` (GSD's commit helper and concurrent agents have landed commits on a stray phase branch before). Commits are atomic per task, except Task 2 which is one commit per ruff category (D-02).
- Commit prefixes: `chore(quick-260926-evd): ...` for config/script, `docs(quick-260926-evd): ...` for prose. End every commit message with the attribution lines from the session system reminder.
- Frontend has no Prettier: never run prettier. ESLint only.
- If `uv run ty check` reports 3 unresolved imports in app/services/maia_engine.py, run `uv sync --group maia-inference` first (environment, not a code problem).
- No CHANGELOG.md entry (dev tooling, not user-facing).
- MUTABLE SCOPE: every finding count in this plan was measured at planning time (ruff 0.16.6). Re-measure before baselining; baseline what you measure, not what is written here.
</context>

<tasks>

<task type="tracer" tdd="true">
  <name>Task 1: Depth-only complexity gate end-to-end (ruff config, function-size script, eslint, CI, pre-merge gate)</name>
  <files>pyproject.toml, scripts/check_function_size.py, tests/scripts/test_check_function_size.py, frontend/eslint.config.js, .github/workflows/ci.yml, CLAUDE.md</files>
  <read_first>pyproject.toml ([tool.ruff*] sections), scripts/check_function_size.py, tests/scripts/test_check_function_size.py (lines 215-322), frontend/eslint.config.js, .github/workflows/ci.yml (Function-size gate step), CLAUDE.md "Pre-merge gate" block</read_first>
  <behavior>
    - A file containing one flat function with 250 logic lines and depth 0, scanned with only `--fail-over-depth 4`, exits 0 (RED today: the script's built-in LOC default of 200 makes it exit 1).
    - A depth-5 function still exits 1 with `--fail-over-depth 4`.
    - `--json` output still carries path, qualname, start_line, end_line, raw_loc, logic_loc, max_nesting_depth for every function.
  </behavior>
  <action>
    Per D-03, make nesting depth the only hard complexity gate across every layer in one slice.

    <!-- planner-discipline-allow: fail-over-loc -->
    <!-- planner-discipline-allow: allow-loc -->
    <!-- planner-discipline-allow: max-statements -->
    <!-- planner-discipline-allow: C901 -->
    <!-- planner-discipline-allow: PLR0912 -->
    <!-- planner-discipline-allow: PLR0915 -->

    1. RED first (tests/scripts/test_check_function_size.py): replace `test_cli_exits_one_when_loc_threshold_breached` with a test named along the lines of `test_cli_does_not_gate_logic_loc` that writes the same 250-assignment flat function and asserts exit code 0 when run with only `--fail-over-depth 4`. Drop the `--fail-over-loc 200` arguments from the other two CLI tests. Run `uv run pytest tests/scripts/test_check_function_size.py -q` and confirm the new test FAILS before touching the script (proves the test exercises the LOC default, per the mutation-test lesson). Do not add a test that references the removed flag by name.

    2. GREEN (scripts/check_function_size.py): remove LOC gating entirely: delete `_DEFAULT_MAX_LOGIC_LOC`, `_PRAGMA_PREFIX`, `_pragma_for_def`, the `allow_loc`/`allow_loc_reason` fields of `FunctionRecord` and their population in `_build_record`, the `--fail-over-loc` argparse option, and the LOC branch of `_breaches` (new signature takes only the record and the depth limit). Keep `raw_loc`, `logic_loc` and `logic_loc()` (reported via `--json`, informational). Rewrite the module docstring to: depth gate + LOC report; keep a one-sentence reason why this exists (ruff's only depth rule is preview-only and `--preview` would expand the rule set ~180x); drop the pragma and tie-breaker paragraphs; update the usage lines. Do not name the removed option, the pragma, or ruff's statement-count rule anywhere in the new docstring (Task 3's stale-reference sweep covers this file). Rationale for full removal over an opt-in flag: depth is the only gate, and an opt-in threshold plus a pragma with no in-repo caller is dead surface. In the test file, delete `test_pragma_exempts_loc_but_not_depth` and `test_function_without_pragma_is_not_exempt` (their section header too), drop `allow_loc`/`allow_loc_reason` from the JSON field list, and remove the pragma mention from the module docstring. The now-inert pragma comment in app/repositories/library_repository.py is cleaned up in Task 3.

    3. pyproject.toml: delete the `extend-select` line, the `[tool.ruff.lint.mccabe]` and `[tool.ruff.lint.pylint]` tables, and the whole Phase 214 baseline block in `[tool.ruff.lint.per-file-ignores]` (its comment lines and every entry listing only those three complexity codes). Keep the `app/models/*.py` F821 and `alembic/versions/*.py` F401 entries and the explicit-pin comment. Add one comment line under `select` saying ruff's complexity-count rules are deliberately not enabled because nesting depth (scripts/check_function_size.py) is the only hard complexity gate. Phrase it by concept; do not write the rule codes.

    4. frontend/eslint.config.js: in the `**/*.{ts,tsx}` rules remove `complexity` and `max-statements`, keep `'max-depth': ['error', 4]`, and replace the Phase 215 comment with one or two lines: nesting depth is the only hard complexity gate (mirrors scripts/check_function_size.py); cognitive complexity is report-only via `npm run lint:cognitive`. Do not name the removed rules in any new comment (Task 3's sweep covers this file). Delete the entire Phase 215 baseline region (header comment plus every override that sets only `complexity`/`max-statements`, including both reasoned-residual entries). Keep the `src/lib/__tests__/reminderSlotState.test.ts` `max-depth` 10 override with a one-line comment (only max-depth breach, a test file; delete once flattened; new breaches are fixed, not baselined). Leave the three react-refresh overrides untouched.

    5. .github/workflows/ci.yml "Function-size gate" step: run with only `--fail-over-depth 4`; reword the step comment to "AST nesting-depth gate: fails the build past the depth-4 hard limit in app/ (tests/ and scripts/ deliberately not gated)". No other CI change: `npm run build` and `npm run knip` are already CI steps.

    6. CLAUDE.md "Pre-merge gate" code block only (the prose section is Task 3): change the function-size line to `uv run python scripts/check_function_size.py app/ --fail-over-depth 4` with trailing comment `# nesting-depth gate (app/)`; change the frontend line to `( cd frontend && npm run lint && npm run build && npm test -- --run && npm run knip )` per D-01 (build = tsc -b type check + vite build, mirrors CI; knip mirrors CI).

    7. `uv run ruff format scripts/ tests/`, then commit: `chore(quick-260926-evd): make nesting depth the only hard complexity gate`.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess && uv run pytest tests/scripts/test_check_function_size.py -q && uv run python scripts/check_function_size.py app/ --fail-over-depth 4 && uv run ruff check . && uv run ruff format --check app/ tests/ scripts/ analysis/ && SETTINGS="$(uv run ruff check --show-settings app/main.py)" && ! printf '%s' "$SETTINGS" | grep -qE "\((C901|PLR0912|PLR0915)\)" && uv run ty check app/ tests/ scripts/ && cd frontend && npm run lint && npx eslint --print-config src/pages/Analysis.tsx | node -e "const r=JSON.parse(require('fs').readFileSync(0,'utf8')).rules; process.exit(r.complexity || r['max-statements'] || !r['max-depth'] || r['max-depth'][1] !== 4 ? 1 : 0)" && npx eslint --print-config src/lib/__tests__/reminderSlotState.test.ts | node -e "const r=JSON.parse(require('fs').readFileSync(0,'utf8')).rules; process.exit(r['max-depth'][1] === 10 && !r.complexity ? 0 : 1)" && npm run build && npm run knip</automated>
  </verify>
  <done>New CLI test was observed RED then GREEN; check_function_size gates depth only and still reports LOC in --json; ruff enables no complexity-count rule and has no baseline block for them; eslint resolves max-depth 4 (10 for the one test file) and neither complexity nor max-statements anywhere; CI and the CLAUDE.md gate invoke the depth-only gate, and the gate now runs `npm run build` and `npm run knip`; one commit on main.</done>
</task>

<task type="auto">
  <name>Task 2: Adopt ruff TID251, B, ASYNC, DTZ (one commit per category, config-fix + baseline)</name>
  <files>pyproject.toml</files>
  <read_first>pyproject.toml [tool.ruff.lint] after Task 1</read_first>
  <action>
    Per D-02, adopt four categories, each as its own commit, in this order. For each: add the code to `extend-select` (re-create the line; order TID251, B, ASYNC, DTZ), run `uv run ruff check . --statistics` and `uv run ruff check . --output-format concise` to re-measure, apply the config fix/scoping/baseline below, confirm `uv run ruff check .` exits 0, `git branch --show-current` prints main, commit. Do NOT run `ruff check --fix` while adopting (the one autofixable finding, B010, is deliberately baselined; see B). Do not hand-edit code to fix findings; behavior changes are out of scope.

    Scoping policy (write it once as a comment above the glob entries): B, ASYNC and DTZ target app/ code. `scripts/**`, `analysis/**` and `alembic/**` ignore all three (CLI/research/migration code: blocking file I/O and naive local dates are fine there, zip over known-equal sequences is noise). `tests/**` ignores ASYNC, DTZ and B905 (async tests do blocking fixture I/O by design; naive fixture datetimes; zip over fixture pairs), but bugbear stays on for tests because B017/B904/B007 catch real test bugs. TID251 applies everywhere. Grow each glob's code list commit by commit. TOML rejects duplicate keys: if a path needs codes from two categories, append to its existing entry.

    Baseline style: one block introduced by a dated comment, e.g. "Quick 260926-evd baseline (measured 2026-09-26, ruff 0.16.6): pre-existing findings in newly adopted categories. Delete an entry when its file is fixed; never add one for new code." Each entry lists only the specific codes measured for that file.

    Also extend the explicit-pin comment above `select` with one sentence: TID251, B, ASYNC and DTZ were adopted deliberately on 2026-09-26 (quick 260926-evd), scoped per the per-file-ignores comment. Keep the existing pin rationale intact.

    a) TID251 commit (`chore(quick-260926-evd): ban requests and berserk via ruff TID251`): add `[tool.ruff.lint.flake8-tidy-imports.banned-api]` with entries for `requests` (msg: blocks the event loop, use httpx.AsyncClient) and `berserk` (msg: use httpx.AsyncClient against the lichess API). Add a comment explaining why the datetime `now` API is NOT banned (legitimate tz-aware use in middleware, import-job and eval-lease code; naive form caught by DTZ005; the endpoint-only dev_now_utc rule is not an API ban). Expected findings: 0.

    b) B commit (`chore(quick-260926-evd): adopt ruff flake8-bugbear (B)`): add `[tool.ruff.lint.flake8-bugbear]` `extend-immutable-calls` listing `fastapi.Depends`, `fastapi.Query`, `fastapi.Path`, `fastapi.Body`, `fastapi.Header`, `fastapi.Cookie`, `fastapi.Security`, `fastapi.Form`, `fastapi.File` (clears all ~60 B008 findings, verified at planning time). Add the non-app globs with B, `tests/**` with B905. Baseline the remainder per file; expected: app/routers/auth.py B904, app/routers/imports.py B904, app/services/endgame_service.py B905, app/services/maia_encoding.py B905, tests/repositories/test_opening_insights_repository.py B007, tests/services/test_push_crypto.py B017, tests/test_eval_worker_endpoints.py B017, tests/test_main_lifespan.py B904, tests/test_alembic_autogen_filter.py B010. The B010 entry gets an inline reason: the setattr calls deliberately bypass ty (its autofix to plain attribute assignment was verified to produce a ty invalid-assignment error on the alembic.context proxy), so never autofix it.

    c) ASYNC commit (`chore(quick-260926-evd): adopt ruff flake8-async (ASYNC)`): add ASYNC to the non-app globs and `tests/**`. Expected app baseline: app/services/engine.py ASYNC109.

    d) DTZ commit (`chore(quick-260926-evd): adopt ruff flake8-datetimez (DTZ)`): add DTZ to the non-app globs and `tests/**`. Expected app baseline: app/services/insights_llm.py DTZ011, app/services/insights_service.py DTZ011, app/services/normalization.py DTZ007, app/services/user_benchmark_percentiles_service.py DTZ011.

    If re-measurement shows a category is mostly noise in app/ (not expected), you may ignore that single rule globally with a one-line reason instead of a long baseline; record it in the SUMMARY.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess && uv run ruff check . && printf 'import time\n\n\nasync def f() -> None:\n    time.sleep(1)\n' | uv run ruff check --stdin-filename app/_probe.py --output-format concise - | grep -q ASYNC251 && echo 'import requests' | uv run ruff check --stdin-filename scripts/_probe.py --output-format concise - | grep -q TID251 && echo 'import berserk' | uv run ruff check --stdin-filename app/_probe.py --output-format concise - | grep -q TID251 && printf 'import datetime\nx = datetime.datetime.now()\n' | uv run ruff check --stdin-filename app/_probe.py --output-format concise - | grep -q DTZ005 && printf 'from datetime import datetime, timezone\nx = datetime.now(timezone.utc)\n' | uv run ruff check --stdin-filename app/_probe.py - && printf 'import datetime\nx = datetime.datetime.now()\n' | uv run ruff check --stdin-filename scripts/_probe.py - && printf 'from fastapi import Depends, Query\n\n\ndef dep() -> int:\n    return 1\n\n\ndef f(x: int = Query(1), y: int = Depends(dep)) -> int:\n    return x + y\n' | uv run ruff check --stdin-filename app/_probe.py - && printf 'import pytest\n\n\ndef test_x() -> None:\n    with pytest.raises(Exception):\n        pass\n' | uv run ruff check --stdin-filename tests/_probe.py --output-format concise - | grep -q B017 && RECENT="$(git log --oneline -6)" && test "$(printf '%s\n' "$RECENT" | grep -c 'quick-260926-evd')" -ge 5 && uv run ty check app/ tests/ scripts/</automated>
  </verify>
  <done>`ruff check .` green with TID251/B/ASYNC/DTZ enabled; requests/berserk banned repo-wide; naive now flagged in app/, tz-aware now and FastAPI Query/Depends defaults not flagged; non-app dirs scoped out by documented globs; app/ and tests/ findings baselined per file with specific codes under a dated comment; four separate category commits on main; ty still clean.</done>
</task>

<task type="auto">
  <name>Task 3: Condense the complexity prose and clean stale gate references</name>
  <files>CLAUDE.md, docs/dev-tooling.md, frontend/CLAUDE.md, app/repositories/library_repository.py, app/services/tactic_detector.py, frontend/src/pages/Analysis.tsx</files>
  <read_first>CLAUDE.md ("Coding Guidelines": the "Keep functions small and shallow" and "Refactor bloated code on sight" bullets), docs/dev-tooling.md (## Scripts section), frontend/CLAUDE.md line 10, app/repositories/library_repository.py (comment block above fetch_flaw_comparison, ~line 2014), app/services/tactic_detector.py (~lines 2063 and 2176), frontend/src/pages/Analysis.tsx (~line 743)</read_first>
  <action>
    Per D-03, the point is less text for agents. Use em-dashes sparingly in new prose (commas, colons, parentheses instead). Phrase dropped rules by concept (e.g. "ruff's complexity-count rules", "eslint's cyclomatic and statement-count rules"), never by rule code or removed flag name, so the negative sweep in verify stays meaningful.

    <!-- planner-discipline-allow: fail-over-loc -->
    <!-- planner-discipline-allow: allow-loc -->
    <!-- planner-discipline-allow: max-statements -->
    <!-- planner-discipline-allow: C901 -->
    <!-- planner-discipline-allow: PLR0912 -->
    <!-- planner-discipline-allow: PLR0915 -->

    1. CLAUDE.md, replace the two bullets "Keep functions small and shallow" (with all sub-bullets) and "Refactor bloated code on sight" with a condensed version (keep the bold lead `**Keep functions small and shallow.**` so the section is findable), covering exactly:
       - Hard rule: nesting depth <= 4 inside any function body (aim for 3), gated by `scripts/check_function_size.py` (backend app/) and eslint `max-depth` (frontend). Fix a new breach, never baseline it.
       - Soft guidance, not gated, reviewed by humans and `/simplify`: about 100 logic lines per function (excluding a returned JSX tree, large literal config/lookup tables, docstrings) and cognitive complexity <= 15. Report-only tools: `uv run complexipy app/ --max-complexity-allowed 15 --failed` and `npm run lint:cognitive` (from frontend/).
       - Real seams when splitting (one line): pipeline stages (`_fetch`/`_classify`/`_rank`), a `useXyzData` hook for React data shaping, separate desktop/mobile renderers, thin routers with logic in services, early `continue`/`return` instead of nested loops.
       - Don't split to satisfy a metric (condensed): if the split needs a context object threading state between helpers that always run together, the original was cohesive.
       - Refactor-on-sight (condensed to one or two sentences): when editing a function clearly past this guidance, refactor it as part of the task; outside a GSD phase plan flag it instead, and for `/gsd-quick`/`/gsd-fast` work leave a follow-up note.
       Budget: the text from the "Keep functions small" bullet up to the "## Error Handling" heading must be <= 230 words (was 390).

    2. docs/dev-tooling.md "## Scripts": replace the five tooling bullets (check_function_size, ruff complexity rules, complexipy, frontend complexity rules, lint:cognitive) with:
       - `scripts/check_function_size.py`: AST nesting-depth gate (depth <= 4, app/ only, CI + pre-merge gate). Keep the one-clause reason ruff's preview-only depth rule was rejected. `--json` also reports raw/logic LOC per function for review; LOC is not gated.
       - Ruff rule set: explicit pin E4/E7/E9/F + TID251/B/ASYNC/DTZ (see the pyproject comment for why the set is pinned). B/ASYNC/DTZ target app/ (bugbear also tests/); scripts/, analysis/, alembic/ are scoped out. Banned APIs: requests, berserk. Pre-existing findings are baselined in per-file-ignores; an entry is deleted when its file is fixed, never added for new code.
       - Cognitive complexity, report-only on both stacks: `uv run complexipy app/ --max-complexity-allowed 15 --failed --sort desc` and `npm run lint:cognitive` (`sonarjs/cognitive-complexity` 15, own config `frontend/eslint.config.sonarjs.mjs`, not in CI).
       - Frontend: eslint `max-depth` 4 at `error` in `frontend/eslint.config.js` (TS/TSX only, because `eslint .` also walks the vendored engine bundles under `frontend/public/`) is the only complexity gate; one test file is baselined.
       Budget: the "## Scripts" section (heading up to "## Database access") must be <= 560 words (was 627).

    3. frontend/CLAUDE.md line 10: replace the complexity bullet with one sentence: `max-depth` 4 gates `npm run lint`; fix a new breach rather than baselining it; cognitive complexity is report-only via `npm run lint:cognitive` (soft guidance per root CLAUDE.md). While there, add one short clause or bullet that `npm run lint` and `npm test` do not type-check, so run `npm run build` (tsc -b) before integrating (D-01).

    4. Stale gate references in code comments (comment-only edits, no logic change):
       - app/repositories/library_repository.py: delete the 4-line explanatory comment and the pragma line directly above `async def fetch_flaw_comparison` (the script no longer reads the pragma).
       - app/services/tactic_detector.py: in the `_clearance_check_move_is_valid` docstring and the "Condition 7" comment inside detect_clearance, reword "to keep ... branch count under the project's ... gate" to say it was extracted to keep detect_clearance's branching readable. Keep the rest of the docstring (the cook rule and the prior-port bug note) intact.
       - frontend/src/pages/Analysis.tsx (~line 743): drop the clause claiming the component sits at its statement-count/complexity baseline; keep the rest of the comment.

    5. `uv run ruff format app/`, then commit: `docs(quick-260926-evd): condense complexity guidance to a depth-only hard rule`.
  </action>
  <verify>
    <automated>cd /home/aimfeld/Projects/Python/flawchess && test "$(awk '/^- \*\*Keep functions small and shallow/,/^## Error Handling/' CLAUDE.md | wc -w)" -le 230 && test "$(awk '/^## Scripts/,/^## Database access/' docs/dev-tooling.md | wc -w)" -le 560 && { git grep -n -e C901 -e PLR0912 -e PLR0915 -e fail-over-loc -e allow-loc -e max-statements -- pyproject.toml .github/workflows/ci.yml CLAUDE.md docs/dev-tooling.md frontend/CLAUDE.md frontend/eslint.config.js frontend/src scripts/check_function_size.py app; test $? -eq 1; } && grep -q "npm run build" CLAUDE.md && grep -q "complexipy" CLAUDE.md && grep -q "lint:cognitive" frontend/CLAUDE.md && uv run ruff check . && uv run ruff format --check app/ tests/ scripts/ analysis/ && uv run python scripts/check_function_size.py app/ --fail-over-depth 4 && cd frontend && npm run lint</automated>
  </verify>
  <done>CLAUDE.md complexity section <= 230 words with depth as the only hard rule and LOC/cognitive complexity as soft report-only guidance (don't-split-to-fit guidance kept); dev-tooling Scripts section <= 560 words and describes the new ruff rule set and scoping; frontend/CLAUDE.md matches; no stale reference to a dropped rule, flag or pragma remains in config, CI, docs, app/ or frontend/src; one docs commit on main.</done>
</task>

</tasks>

<threat_model>
## Trust Boundaries

| Boundary | Description |
|----------|-------------|
| local pre-merge gate / CI -> main | The gates decide what code reaches `main` and then `production`; this plan changes which checks run. |

## STRIDE Threat Register

| Threat ID | Category | Component | Severity | Disposition | Mitigation Plan |
|-----------|----------|-----------|----------|-------------|-----------------|
| T-evd-01 | Tampering | frontend/eslint.config.js, scripts/check_function_size.py | medium | mitigate | Task 1 verify asserts via `eslint --print-config` that max-depth 4 is still resolved and via the CLI test that a depth-5 function still exits 1, so consolidation cannot silently drop the one hard gate. |
| T-evd-02 | Denial of Service | backend HTTP clients (event loop) | medium | mitigate | TID251 bans `requests` and `berserk` repo-wide (blocking HTTP stalls the async event loop); Task 2 verify probes the ban in both app/ and scripts/. |
| T-evd-03 | Tampering | pyproject.toml per-file-ignores | low | mitigate | Directory globs only for scripts/, analysis/, alembic/ (and three named rules for tests/); app/ findings are baselined per file with specific codes, so new app/ code is fully linted. Task 2 verify probes app/ and tests/ scoping. |
| T-evd-04 | Tampering | CLAUDE.md pre-merge gate | low | mitigate | D-01 adds `npm run build` (tsc type check) and `npm run knip`, closing the CI-only gap through which a type error could reach `main` via local squash-merge. |
| T-evd-SC | Tampering | npm/pip installs | low | accept | No package is installed or added; complexipy and eslint-plugin-sonarjs are already dependencies. |
</threat_model>

<verification>
Final gate (run after Task 3, all must pass):
- `uv run ruff format --check app/ tests/ scripts/ analysis/`
- `uv run ruff check .`
- `uv run ty check app/ tests/ scripts/`
- `uv run --project analysis --with ty ty check analysis/`
- `uv run python scripts/check_function_size.py app/ --fail-over-depth 4`
- `uv run pytest tests/scripts/test_check_function_size.py -q`
- `( cd frontend && npm run lint && npm run build && npm run knip )`

The full backend suite (`uv run pytest -n auto -x`) and vitest are not required: the only Python logic change is scripts/check_function_size.py (covered by its own test file), app/ edits are comment-only, and the frontend change is lint config plus one comment. `git log --oneline -7` shows six `quick-260926-evd` commits on `main` (Task 1, four Task 2 category commits, Task 3).
</verification>

<success_criteria>
- Nesting depth <= 4 is the only hard complexity gate on both stacks; LOC and cognitive complexity are report-only (D-03).
- Ruff enforces TID251/B/ASYNC/DTZ with a documented scope and a small dated per-file baseline; no behavior-changing code edits (D-02).
- The pre-merge gate type-checks the frontend and matches CI (D-01).
- Complexity prose is shorter in CLAUDE.md and docs/dev-tooling.md, and consistent across CLAUDE.md, frontend/CLAUDE.md, docs/dev-tooling.md, pyproject.toml, eslint.config.js and ci.yml.
</success_criteria>

<output>
Create `.planning/quick/260926-evd-consolidate-static-analysis-gates-for-ag/260926-evd-SUMMARY.md` when done. Record: the re-measured finding counts per category, the final baseline entries, the two planning-time corrections (script LOC default; datetime now not banned), and any rule ignored globally with its reason.
</output>
