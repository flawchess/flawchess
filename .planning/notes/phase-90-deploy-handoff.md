# Phase 90 deployment handoff — 2026-05-20

In-flight session handoff. Phase 90 (import-pipeline OOM fix + resilience) is **done coding and UAT-verified**; only the deploy chain remains. Drop this into a fresh session via the resume prompt at the bottom.

## Where we are

| | |
|---|---|
| Branch | `gsd/phase-90-import-pipeline-memory-leak-fix-resilience` (30 commits ahead of origin/main) |
| PR | **#128** — https://github.com/flawchess/flawchess/pull/128 |
| PR base / head | `main` ← `gsd/phase-90-...` |
| Last commit | `f9a06645` — `style(90): ruff format import_service after retry-classifier edits` |
| CI state at handoff | Re-running after `f9a06645`. Two CI failures already triaged and fixed: (1) pip-audit on vendor-disputed `PYSEC-2025-183` (pyjwt) — suppressed in `72c38767`; (2) `ruff format --check` on `app/services/import_service.py` — formatted in `f9a06645`. Local `pip-audit`, `ruff format --check`, `ruff check`, `ty check`, `pytest` all pass. **Verify the new CI run is green before merging.** |

## What's already done

1. **All 3 plans executed and merged** to the phase branch:
   - 90-01 Stage 5 `_flush_batch` rewrite (bindparam executemany against `Game.__table__`)
   - 90-02 per-batch AsyncSession scoping
   - 90-03 periodic reaper + bounded retry helper + lifespan wiring
2. **Code review** (`/gsd:code-review`): 1 critical + 7 warnings → **all 8 fixed** in atomic follow-up commits (`dddd66f5` … `554ada5b`). `90-REVIEW.md` has the Fixes Applied table.
3. **Phase verification** (`gsd-verifier`): 9/9 must-haves verified. `90-VERIFICATION.md` produced.
4. **Local UAT (2026-05-20):**
   - UAT-1 RSS-flat: 🟢 PASS — plateau at 577 MB across +1044 games post-warmup, ~88% reduction vs pre-fix 0.48 MB/game
   - UAT-2 Signal A (retry helper): 🟢 PASS after fix `ac2e2381` — first attempt caught a real classifier bug (only matched OperationalError); broadened to a `_RETRIABLE_DB_OUTAGE_ERRORS` tuple + `engine.dispose()` pool invalidation
   - UAT-2 Signal B (reaper): 🟢 PASS — 4h-backdated job reaped within next tick; live (<3h) jobs untouched
   - UAT-3 (Sentry FLAWCHESS-56/3Q): ⏳ pending — needs production deploy + 48h watch
   - Full results recorded in `90-HUMAN-UAT.md`
5. **UAT-detected bugs fixed during UAT** (both have real-DB regression coverage now):
   - `c56ab052` — Stage 5 ORM bulk-update fragility: `update(Game).where(...)` raised under real DB sessions because original tests used AsyncMock. Switched to `update(Game.__table__)`. New `TestFlushBatchStage5RealDb`.
   - `ac2e2381` — retry classifier too narrow + pool invalidation missing. New `TestRecordFailureWithRetryDbOutage` (6 tests).
6. **CHANGELOG.md** — Phase 90 entries added under `[Unreleased]` (`59d6032a`).
7. **CI fix** (`72c38767`) — suppressed vendor-disputed pyjwt CVE PYSEC-2025-183 with the same rationale as the existing pip CVE suppression. **Local pip-audit passes.**

## Next steps (resume order)

Task IDs from the previous session were:

| # | Task | Status at handoff |
|---|------|---|
| 11 | Wait for CI on PR #128 | in_progress (background poll `b8qvgpj2v` was active) |
| 12 | Squash-merge PR #128 to main | pending |
| 13 | Open main → production release PR | pending |
| 14 | Merge release PR + run `bin/deploy.sh` | pending |
| 15 | Verify production deploy health | pending |
| 16 | Mark phase 90 complete in STATE/ROADMAP | pending |

(The background polls won't survive `/clear` — re-arm them or just check CI manually.)

### Step-by-step

1. **Verify CI is green** on PR #128 (the `72c38767` re-run):
   ```bash
   gh pr checks 128
   ```
   Expected: `test` pass, `Analyze (python)` pass, `Analyze (javascript-typescript)` pass, `deploy` skipping. If anything's still failing, diagnose with `gh run view <run-id> --log-failed`.

2. **Squash-merge PR #128** to main:
   ```bash
   gh pr merge 128 --squash --delete-branch \
     --subject "Phase 90: import-pipeline memory leak fix + resilience" \
     --body "$(cat <<'EOF'
   Closes the 2026-05-16 production OOM (FLAWCHESS-56 / FLAWCHESS-3Q).
   
   - Plan 90-01: Stage 5 _flush_batch rewritten with bindparam executemany against Game.__table__ — invariant SQL text across batches eliminates the per-batch unique-SQL leak.
   - Plan 90-02: run_import restructured into three AsyncSession scopes (bootstrap / per-batch / completion).
   - Plan 90-03: periodic orphan-job reaper (5-min tick, 3h age threshold) + bounded retry helper with broadened DB-outage classifier and engine.dispose() pool invalidation.
   - Real-DB regression tests added (TestFlushBatchStage5RealDb, TestRecordFailureWithRetryDbOutage).
   - Local UAT passed: RSS plateau, retry helper, reaper. UAT-3 (production Sentry monitoring) is the 48h post-deploy watch.
   
   See PR #128 for full detail, .planning/phases/90-import-pipeline-memory-leak-fix-resilience/90-HUMAN-UAT.md for UAT results.
   EOF
   )"
   ```

3. **Switch local to main and pull**:
   ```bash
   git checkout main && git pull origin main
   ```

4. **Open the main → production release PR** (per GitLab Flow):
   ```bash
   gh pr create --base production --head main \
     --title "Release: Phase 90 — import-pipeline OOM fix + resilience" \
     --body "$(cat <<'EOF'
   Promotes Phase 90 to production. Closes the 2026-05-16 OOM (FLAWCHESS-56 / FLAWCHESS-3Q).
   
   - Stage 5 _flush_batch executemany rewrite (memory-leak root cause)
   - Per-batch AsyncSession scoping (defense-in-depth)
   - Periodic orphan-job reaper + bounded failure-state retry helper
   - Real-DB regression tests for both
   
   Local UAT verified the leak fix (RSS plateau), retry helper, and reaper. Sentry FLAWCHESS-56/3Q watch starts post-deploy.
   
   🤖 Generated with [Claude Code](https://claude.com/claude-code)
   EOF
   )"
   ```
   Merge it (squash) once any production-PR checks settle:
   ```bash
   gh pr merge --base production --squash --delete-branch=false
   ```
   (Don't delete `main` here — `--delete-branch=false` is essential.)

5. **Deploy to production**:
   ```bash
   bin/deploy.sh
   ```
   This triggers the GitHub Actions deploy workflow against the `production` branch. Watch the run; the script also tails it.

6. **Verify production health** (after deploy completes):
   ```bash
   ssh flawchess "cd /opt/flawchess && docker compose ps"
   ssh flawchess "cd /opt/flawchess && docker compose logs --tail=80 backend | grep -iE 'reaper|error|critical|ImportJob|FLAWCHESS-56'"
   ```
   Expectations:
   - Backend container is `Up (healthy)`
   - Backend log shows lifespan startup completing and the reaper task spawned (no crash)
   - No new errors. Tail Sentry dashboard for FLAWCHESS-56 / FLAWCHESS-3Q quiet over the next 48h.

7. **Mark phase complete in STATE/ROADMAP**:
   - STATE.md frontmatter `status: awaiting_uat` → `status: idle` (or `complete`)
   - "Current Position" block: rewrite from "AWAITING HUMAN UAT" to "Phase 90 shipped to production YYYY-MM-DD"
   - Phase 90 is not entered in the main `.planning/ROADMAP.md` Phases section (it's a post-v1.17 carryover, known split-roadmap issue per the project memory). Either add a one-line entry under the v1.17 milestone summary, or leave as-is and rely on the phase directory + CHANGELOG.
   ```bash
   git add .planning/STATE.md .planning/ROADMAP.md
   git commit -m "docs(phase-90): mark phase complete after production deploy

   Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>"
   git push
   ```

8. **48h Sentry watch** (manual, separate session). If FLAWCHESS-56 / FLAWCHESS-3Q stay quiet, edit `90-HUMAN-UAT.md` UAT-3 result → `passed YYYY-MM-DD` and bump frontmatter `status` from `partial` to `passed`. If they recur, gap-close.

## Useful pointers

- Phase artifacts: `.planning/phases/90-import-pipeline-memory-leak-fix-resilience/`
- PR: https://github.com/flawchess/flawchess/pull/128
- Sentry: https://flawchess.sentry.io (issues FLAWCHESS-56, FLAWCHESS-3Q)
- Deploy script: `bin/deploy.sh`
- Production SSH: `ssh flawchess`
- Server app path: `/opt/flawchess`
- CLAUDE.md "Version Control" section has the full GitLab Flow + hotfix recipes.

## Cleanup nicety (optional)

The dev DB still has the stranded `68da025c-ca22-43a0-8719-1b3d928e9827` from UAT-2 Signal A's first round (retry exhaustion test). Not harmful but tidy:
```sql
UPDATE import_jobs SET status='failed',
  error_message='Stranded by UAT-2 Signal A retry exhaustion; cleaned manually',
  completed_at=NOW()
WHERE id = '68da025c-ca22-43a0-8719-1b3d928e9827';
```
