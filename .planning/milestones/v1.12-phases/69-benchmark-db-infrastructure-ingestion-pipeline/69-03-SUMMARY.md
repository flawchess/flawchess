---
phase: 69-benchmark-db-infrastructure-ingestion-pipeline
plan: 03
subsystem: infra
tags: [mcp, postgres, claude-code, documentation, benchmark-db]

# Dependency graph
requires:
  - phase: 69-benchmark-db-infrastructure-ingestion-pipeline
    provides: "docker-compose.benchmark.yml stack on port 5433, deploy/init-benchmark-db.sql with flawchess_benchmark_ro role (Plan 01), bin/benchmark_db.sh start/stop/reset wrapper (Plan 02)"
provides:
  - "CLAUDE.md §Database Access (MCP) documents flawchess-benchmark-db as the third MCP server alongside flawchess-db and flawchess-prod-db"
  - "Convention recorded: read-only MCP role + locally-set password (never committed) — same pattern as flawchess-prod-db"
  - "Manual checkpoint instructions for the user to register the MCP entry in ~/.claude.json (Claude Code does not write user-level config)"
affects: [69-04, 69-05, 69-06, 70, 71, 72, 73]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Documenting per-environment MCP DB servers in CLAUDE.md §Database Access (MCP) so future contributors discover the connection routing"
    - "Read-only MCP servers carry the RO password in ~/.claude.json (user-level) only; the committed init SQL keeps a <PASSWORD> placeholder"

key-files:
  created:
    - .planning/phases/69-benchmark-db-infrastructure-ingestion-pipeline/69-03-SUMMARY.md
  modified:
    - CLAUDE.md

key-decisions:
  - "Updated the section opener from 'Two PostgreSQL MCP servers' to 'Three' to keep the count consistent with the bullet list (Rule 1 documentation bug fix). The plan did not call this out but leaving 'Two' would have been factually wrong."
  - "Used the longer plan-specified bullet text (with bin/benchmark_db.sh references and the explanatory 'All three are...' replacement sentence) rather than the shorter PATTERNS.md variant. The PLAN.md text takes precedence over PATTERNS.md."
  - "Did NOT execute the ~/.claude.json edit or any `claude mcp add` command. That step is autonomous=false and was returned as a human-action checkpoint per the plan's explicit Task 03-02 framing."

patterns-established:
  - "Three-server MCP doc layout in CLAUDE.md (dev, prod-RO, benchmark-RO) — future read-only MCP additions should follow the same bullet shape and be added after the prod entry."
  - "Plan-level guard against writing user-level config: when a step requires editing files outside the project sandbox (`~/.claude.json`), surface it as a checkpoint:human-action rather than attempting the write."

requirements-completed: [INFRA-03]

# Metrics
duration: ~3min
completed: 2026-04-26
---

# Phase 69 Plan 03: MCP Server Registration & Doc Update Summary

**CLAUDE.md §Database Access (MCP) now documents the third MCP server `flawchess-benchmark-db` (RO role on port 5433); the matching `~/.claude.json` registration is returned to the user as a human-action checkpoint.**

## Performance

- **Duration:** ~3 min
- **Started:** 2026-04-26T07:45:00Z (approx)
- **Completed:** 2026-04-26T07:48:00Z
- **Tasks:** 1 of 2 completed; 1 returned as checkpoint:human-action (per plan)
- **Files modified:** 1 (CLAUDE.md)

## Accomplishments

- Added a third bullet to CLAUDE.md §Database Access (MCP) describing `flawchess-benchmark-db`: Docker on `localhost:5433`, started via `bin/benchmark_db.sh start`, RO role `flawchess_benchmark_ro`, password set locally and not committed.
- Replaced the "Both are read-only query tools …" sentence with an "All three are …" variant naming `mcp__flawchess-benchmark-db__query` and clarifying that `flawchess-db` is RW at the SQL level (app user) while the other two use dedicated RO DB roles.
- Updated the section opener from "Two PostgreSQL MCP servers" to "Three" (Rule 1 doc bug — the count had to match the bullet list).
- Captured the ~/.claude.json registration step as a structured human-action checkpoint with two execution paths (recommended `claude mcp add` CLI vs manual JSON edit), the password handling protocol, and the verification steps (MCP query + write-rejection check).

## Task Commits

1. **Task 03-01: Update CLAUDE.md §Database Access (MCP)** — `1243225` (docs)

**Plan metadata:** SUMMARY commit follows below (separate `docs(69-03): complete plan 03 summary` commit; STATE.md/ROADMAP.md updates handled by orchestrator, not this executor).

## Files Created/Modified

- `CLAUDE.md` — §Database Access (MCP) updated: opener "Two" → "Three", new third bullet for `flawchess-benchmark-db`, "Both are…" → "All three are…" sentence with `mcp__flawchess-benchmark-db__query` named.
- `.planning/phases/69-benchmark-db-infrastructure-ingestion-pipeline/69-03-SUMMARY.md` — this file.

## Decisions Made

- **Followed PLAN.md bullet text, not PATTERNS.md.** The plan's bullet text references `bin/benchmark_db.sh start/stop` and includes the explicit `<PASSWORD>` placeholder convention; the PATTERNS.md variant was shorter. PLAN.md takes precedence.
- **Updated the "Two" → "Three" opener proactively** even though the plan did not explicitly list it. Leaving "Two" while the bullet list shows three servers would be a factual contradiction inside CLAUDE.md, which is itself a hard-constraints document. Treated as Rule 1 (bug fix) deviation.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated section opener from "Two" to "Three" PostgreSQL MCP servers**
- **Found during:** Task 03-01 (CLAUDE.md edit)
- **Issue:** The plan instructed adding a third bullet and replacing the "Both are…" sentence, but did not address the opening sentence "Two PostgreSQL MCP servers are configured for direct database queries:" — leaving it as "Two" with three bullets below would be self-contradictory.
- **Fix:** Changed opener to "Three PostgreSQL MCP servers are configured for direct database queries:" inside the same edit.
- **Files modified:** CLAUDE.md
- **Verification:** Plan's automated verify command passed (`grep -q 'flawchess-benchmark-db' && grep -q 'localhost:5433' && grep -q 'mcp__flawchess-benchmark-db__query' && ! grep -q 'Both are read-only query tools'`).
- **Committed in:** `1243225` (Task 03-01 commit)

---

**Total deviations:** 1 auto-fixed (1 doc bug)
**Impact on plan:** Doc-only correction, fully consistent with plan intent. No scope creep.

## Issues Encountered

None during the executed task. Task 03-02 is intentionally pending as a human-action checkpoint (autonomous=false plan).

## Checkpoint Returned (Task 03-02)

Task 03-02 (`checkpoint:human-action`) was returned to the orchestrator without execution:

- **Why not auto-executed:** The step modifies `~/.claude.json` (user-level config outside the project sandbox) and requires a Claude Code restart. Both are explicit human actions per the plan. Auto mode does not auto-approve `checkpoint:human-action` per the executor protocol.
- **What the user must do:**
  1. Pick a RO password locally (e.g. `openssl rand -hex 16`).
  2. Replace the `<PASSWORD>` placeholder locally in `deploy/init-benchmark-db.sql` (do NOT `git add` it; or use `git update-index --assume-unchanged`). If the benchmark Docker volume already exists, run `bin/benchmark_db.sh reset` so the new password is applied (initdb only runs on first volume init).
  3. Register the MCP entry in `~/.claude.json` under `projects["/home/aimfeld/Projects/Python/flawchess"].mcpServers` as `flawchess-benchmark-db` with args `["-y", "@modelcontextprotocol/server-postgres", "postgresql://flawchess_benchmark_ro:<RO_PASSWORD>@localhost:5433/flawchess_benchmark"]`. Either edit the JSON manually (the plan's chosen method) or use the `claude mcp add` CLI as an equivalent shortcut.
  4. Restart Claude Code.
  5. From a fresh session, run `mcp__flawchess-benchmark-db__query` with `SELECT count(*) FROM games;` (expect a number, likely 0), and verify an `INSERT INTO games (id) VALUES (1);` is rejected with a permission error.
- **Acceptance gate (blocking):** plan resume signal is "approved" once the MCP query succeeds and the write-rejection is observed.

## User Setup Required

Yes — see Task 03-02 checkpoint above. Specifically: choose a RO password, edit `deploy/init-benchmark-db.sql` locally, register the MCP server in `~/.claude.json`, restart Claude Code, and verify with an MCP query and an INSERT-rejection test.

## Next Plan Readiness

- CLAUDE.md doc surface now documents `flawchess-benchmark-db` so all future plans (69-04 through 69-06, plus Phases 70-73) can reference the MCP server by name without ambiguity.
- The MCP server itself is **not yet usable** until the user completes Task 03-02. Plans 69-04/05/06 do not depend on the MCP server (they ingest via SQLAlchemy directly using `BENCHMARK_DATABASE_URL`), so they are unblocked. Phase 70+ analytics that want to query the benchmark DB through the MCP path will need Task 03-02 completed.

## Threat Flags

None — no new security-relevant surface introduced. The threat model in PLAN.md (T-69-02 EoP, T-69-03 password disclosure) is still satisfied: the RO role privileges were enforced in Plan 01, and the password convention (locally-set, never committed) is now documented in CLAUDE.md.

## Self-Check

- File `CLAUDE.md` exists and contains `flawchess-benchmark-db`, `localhost:5433`, `mcp__flawchess-benchmark-db__query` strings; no longer contains `Both are read-only query tools`. PASS.
- Commit `1243225` exists in `git log --oneline`. PASS.
- File `.planning/phases/69-benchmark-db-infrastructure-ingestion-pipeline/69-03-SUMMARY.md` exists. PASS (created in this commit).

## Self-Check: PASSED

---
*Phase: 69-benchmark-db-infrastructure-ingestion-pipeline*
*Plan: 03*
*Completed: 2026-04-26*
