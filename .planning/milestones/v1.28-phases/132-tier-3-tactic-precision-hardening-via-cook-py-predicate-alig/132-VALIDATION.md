---
phase: 132
slug: tier-3-tactic-precision-hardening-via-cook-py-predicate-alig
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-06-23
---

# Phase 132 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]` — `tests/scripts/tagger/` is default-excluded per Phase 127 D-14) |
| **Quick run command** | `uv run pytest tests/scripts/tagger/ -v` (the slow tagger fixture suite — opt-in by explicit path) |
| **Full suite command** | `uv run pytest -n auto` (default suite, tagger dir excluded) + the precision gate below |
| **Estimated runtime** | tagger fixture suite ~minutes; precision gate ~minutes (CC0 fixture scoring) |

**Authoritative precision signal:** the CC0 lichess puzzle fixture TEST split, scored post-dispatch via `scripts/tactic_tagger_report.py --check-goals --eval-set test`. A motif ships only if it clears >0.9 precision on the held-out TEST split (recall ungated). The dev re-backfill (`scripts/backfill_tactic_tags.py --db dev`) is a supplementary real-data validation, NOT the ship gate.

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/scripts/tagger/ -v` (detector behavior) + `uv run ty check app/`
- **After every plan wave:** Run `uv run python scripts/tactic_tagger_report.py --check-goals --eval-set test` to read post-dispatch per-motif precision and confirm no regression on `interference` (≥0.99 floor) or Tier-1/Tier-2 motifs.
- **Before `/gsd-verify-work`:** Full default suite green (`uv run pytest -n auto`), tagger fixture suite green, and TEST-split precision gate evaluated for every in-scope motif (shipped ≥0.9 or explicitly suppressed).
- **Max feedback latency:** tagger fixture suite minutes; precision report minutes.

---

## Per-Task Verification Map

> Requirement column is `none mapped` (traceability is via CONTEXT.md decisions D-01..D-05). Threat Ref `—` (security_enforcement off; pure-CPU detector, no external attack surface). Plan/Wave IDs are filled by the planner; the rows below are the validation skeleton each detector-rewrite task must satisfy.

| Task ID | Plan | Wave | Decision Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|--------------|-----------------|-----------|-------------------|-------------|--------|
| 132-deflection | TBD | TBD | D-01 (full port), D-05 (post-dispatch gate) | N/A | unit + fixture | `uv run pytest tests/scripts/tagger/ -v -k deflection` then `tactic_tagger_report.py --check-goals --eval-set test` | ✅ existing fixtures | ⬜ pending |
| 132-clearance | TBD | TBD | D-01 | N/A | unit + fixture | `tactic_tagger_report.py --check-goals --eval-set test` (clearance) | ✅ | ⬜ pending |
| 132-capturing-defender | TBD | TBD | D-01 | N/A | unit + fixture | `tactic_tagger_report.py --check-goals --eval-set test` (capturing-defender) | ✅ | ⬜ pending |
| 132-attraction | TBD | TBD | D-01 | N/A | unit + fixture | `tactic_tagger_report.py --check-goals --eval-set test` (attraction) | ✅ | ⬜ pending |
| 132-intermezzo | TBD | TBD | D-01 | N/A | unit + fixture | `tactic_tagger_report.py --check-goals --eval-set test` (intermezzo) | ✅ | ⬜ pending |
| 132-x-ray | TBD | TBD | D-01, D-03 (PV-divergence cutoff) | N/A | unit + fixture | `tactic_tagger_report.py --check-goals --eval-set test` (x-ray) | ✅ | ⬜ pending |
| 132-sacrifice | TBD | TBD | D-02 (port-then-suppress sweep) | N/A | unit + fixture | `tactic_tagger_report.py --check-goals --eval-set test` (sacrifice) | ✅ | ⬜ pending |
| 132-interference-lock | TBD | TBD | D-05 carry-forward (regression lock) | N/A | fixture regression | `tactic_tagger_report.py --eval-set test` asserts interference ≥0.99 | ✅ | ⬜ pending |
| 132-dev-backfill | TBD | TBD | D-04 (dev re-backfill) | N/A | manual real-data | `uv run python scripts/backfill_tactic_tags.py --db dev` + before/after count spot-check | ✅ existing script | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- CC0 lichess puzzle fixtures already committed for every in-scope motif (n(test): deflection 501, attraction 677, intermezzo 324, x-ray 274, clearance 334, capturing-defender 285, interference 257, sacrifice 1377). No new fixture authoring.
- `scripts/tactic_tagger_report.py` `--check-goals` GOALS dict needs 6 new entries raised to precision 0.9 — this is an in-task edit, not a Wave 0 install.
- No new test framework, no new fixtures, no dev DB reset.

*Existing infrastructure covers all phase validation requirements.*

---

## Manual-Only Verifications

| Behavior | Decision | Why Manual | Test Instructions |
|----------|----------|------------|-------------------|
| Dev re-backfill correctness | D-04 | Operates on the live dev DB (localhost:5432), refreshes the 8 tactic columns via `_detect_tactic_for_flaw`; correctness = parity with the live drain + a sane changed-row count | Bring dev DB up (`docker compose -f docker-compose.dev.yml -p flawchess-dev up -d`), run `scripts/backfill_tactic_tags.py --db dev`, compare per-motif tag counts before/after, spot-check a handful of changed rows against the puzzle-fixture expectation |
| Suppress-vs-ship call per motif | D-01 | The decision is driven by the TEST number at full port; no pre-judgment, so a human reads the final per-motif precision table | Read `tactic_tagger_report.py --check-goals --eval-set test` output; ship if ≥0.9, otherwise suppress via `SUPPRESSED_MOTIFS` |

---

## Validation Sign-Off

- [ ] Every in-scope motif has an automated TEST-split precision check (`tactic_tagger_report.py --eval-set test`)
- [ ] `interference` regression floor (≥0.99) asserted; no detector edits to it
- [ ] Sampling continuity: precision gate run after every wave; no 3 consecutive detector-rewrite tasks without a fixture/precision check
- [ ] No watch-mode flags
- [ ] Dev re-backfill (D-04) verified against the existing dev DB (no reset)
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
