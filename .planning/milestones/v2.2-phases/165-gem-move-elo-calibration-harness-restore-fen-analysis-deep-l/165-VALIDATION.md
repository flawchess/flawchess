---
phase: 165
slug: gem-move-elo-calibration-harness-restore-fen-analysis-deep-l
status: approved
nyquist_compliant: true
wave_0_complete: false
created: 2026-07-11
---

# Phase 165 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | vitest (frontend), node (harness smoke run) |
| **Config file** | `frontend/vitest.config.ts` (existing) |
| **Quick run command** | `cd frontend && npm test -- --run src/lib/analysisUrl` |
| **Full suite command** | `cd frontend && npm run lint && npm test -- --run && npx tsc -b` |
| **Estimated runtime** | ~30–60 seconds (frontend); harness smoke `--n 5` ~ minutes |

---

## Sampling Rate

- **After every task commit:** Run the relevant quick command (frontend unit test or harness `--n 5` smoke)
- **After every plan wave:** Run `cd frontend && npm run lint && npm test -- --run`
- **Before `/gsd-verify-work`:** Frontend full suite green + a successful harness `--n 5` smoke run producing a valid TSV
- **Max feedback latency:** ~60 seconds (frontend); harness smoke run out-of-band

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 165-01-* | 01 | 1 | SEED-094 | — | N/A | node smoke | `node scripts/<harness>.mjs --n 5` produces a TSV in reports/data/ | ❌ W0 | ⬜ pending |
| 165-01-* | 01 | 1 | SEED-094 | — | N/A | fixture | harness gem boolean for a fixed FEN matches frontend `classifyGem` | ❌ W0 | ⬜ pending |
| 165-02-* | 02 | 1 | SEED-094 | — | N/A | unit | `cd frontend && npm test -- --run src/lib/analysisUrl` exits 0 | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `frontend/src/lib/analysisUrl.test.ts` — extend with `?fen=` build/parse round-trip cases (mirror existing `?line=` tests)
- [ ] Harness `--n` smoke path (`--n 5`) — end-to-end sanity without a 3000-position soak

*Node harness has no committed unit test framework; validation is the `--n 5` smoke run + the gem-logic fixture parity check.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| `?fen=<fen>` deep-link loads an arbitrary mid-game position as free-play root in the browser | SEED-094 | Requires real `/analysis` render + board seeding | Open `/analysis?fen=<url-encoded FEN from a TSV row>`; board shows that position, free-play navigable |
| Full 3000-position calibration run + drop-off curve is sensible | SEED-094 | Long soak (~2.5h), interpretive | Run harness at default `--n`; inspect TSV + summary block for the predicted fall-with-ELO gem rate |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 60s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-07-11
