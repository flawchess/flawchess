# SEED-032: Frontend major dependency upgrades (clustered, sequential)

**Status:** Open
**Created:** 2026-05-31
**Source:** Follow-up to quick task 260531-jga (updated all deps to *latest within current majors*). After that refresh, 11 frontend deps still have a newer **major** available that we deliberately did not adopt. Backend has **zero** outstanding major bumps. This seed captures the cluster list + ordering + compat risk so the work can be planned later.
**Related:** quick task 260531-jga (the in-major refresh that preceded this); `frontend/package.json`; `frontend/eslint.config.js`; CLAUDE.md "Pre-PR checklist / full local gate", "Frontend" rules, GitLab-Flow merge rules.

---

## One-liner

Eleven frontend dependencies are one or more **majors** behind. They are coupled into a few clusters that must be bumped together (peer-compat), and they carry real breakage risk (recharts 3 is user-facing; typescript 6 is a compiler major; eslint 10 + typescript-eslint compat is the likely blocker). Do them **one cluster at a time**, each atomically committed and gated, ordered low-risk → high-risk so the gate signal sharpens as you go. Backend needs nothing.

---

## Structure recommendation (NOT YET CREATED — captured per user request)

- **Not a milestone.** Milestones here map to *releases* (versioned CHANGELOG sections, git tags, `main → production`). This is maintenance — fold it into the current cycle, don't cut a release for tooling upgrades.
- **One phase, one plan per cluster, executed sequentially.** A single coherent goal ("frontend on latest majors, all gates green") gets one discuss→plan→verify pass, one CHANGELOG bullet, one cleanup — instead of paying that ceremony 7×.
- **Sequential, not parallel.** GSD runs plans *within a wave in parallel*; for dep bumps that is wrong. Put each cluster in its own sequential wave (or one plan with strictly-ordered tasks) so a gate failure points at exactly one cluster (bisectability).
- **Run a short research pass up front** (or `--research` on the lint/TS plans) to resolve the peer-compat question below before planning the bumps.

---

## The clusters & ordering (low-risk → high-risk)

Versions are a snapshot as of 2026-05-31 (current = locked after 260531-jga; latest = npm `Latest`). Re-check `npm outdated` at planning time — these will drift.

1. **lucide-react 0.577.0 → 1.17.0** (prod) — icon lib hit 1.0. Usually low-risk (icon-name surface); good confidence-builder to go first.
2. **Vite stack** — `vite` 7.3.3 → 8.0.14 + `@vitejs/plugin-react` 5.2.0 → 6.0.2 (both dev). Coupled; bump together. Verify `npm run build` + `vite-plugin-pwa` + `vite-prerender-plugin` still work.
3. **Test env** — `jsdom` 25.0.1 → 29.1.1 (four majors behind!) + `@types/node` 24.12.4 → 25.9.1 (both dev). **Pin `@types/node` to the runtime Node line, not blindly to 25** — its major tracks Node.js. Verify the full Vitest suite under jsdom 29.
4. **Lint stack** — `eslint` 9.39.4 → 10.4.1 + `@eslint/js` 9.39.4 → 10.0.1 + `globals` 16.5.0 → 17.6.0 + `eslint-plugin-react-refresh` 0.4.26 → 0.5.2 (all dev). Bump together; recheck every eslint plugin's eslint-10 compat.
5. **typescript 5.9.3 → 6.0.3** (dev) — compiler major. Re-run `tsc -b` (build) and `ty`; expect new type errors to fix. Note `noUncheckedIndexedAccess` is on, so TS 6 stricter inference may surface more.
6. **recharts 2.15.4 → 3.8.1** (prod) — **biggest functional risk.** v3 had API/render changes; used heavily across endgame + openings charts (MiniBulletChart, WDLChartRow, ScoreChart, ScoreGapByTimePressureChart, gauges, custom tooltips/gradients). This cluster earns **visual UAT** (desktop + mobile), not just green tests.

Non-major straggler worth folding in opportunistically: **shadcn** is at 4.8.3 but 4.9.0 is available within-major (npm "Wanted" = 4.9.0); the in-major refresh didn't pull it (lockfile resolution quirk). Trivial.

---

## Key risk to research before planning

**Peer-compat coupling between the lint stack and typescript 6.** `typescript-eslint` (currently `^8.48.0`) must support **both** TS 6 and eslint 10, and the eslint plugins (`eslint-plugin-react-hooks` ^7.1.1, `eslint-plugin-react-refresh`, `typescript-eslint`) must all support eslint 10. If `typescript-eslint` doesn't yet support TS 6 or eslint 10, clusters 4 and 5 are blocked until it does — that's the single most likely thing to stall this work. Resolve this first; it may reorder or defer those two clusters.

Secondary: `eslint-plugin-react-hooks` 7.1.1 introduced `react-hooks/set-state-in-effect`, which 260531-jga disabled globally (pre-existing intentional derive-from-server / filter-sync patterns). If the lint-stack bump changes that rule's behavior or default, revisit that decision rather than carrying the blanket `off`.

---

## Backend: nothing to do

For the record — at 2026-05-31, every declared backend dep (prod + dev) is already on its latest major; locked == PyPI latest for all 21. The two deliberate caps (`pydantic-ai-slim<2.0`, `genai-prices<0.1.0`) aren't binding right now (no 2.0 / 0.1 published yet). Revisit only when those upper bounds start blocking a release.

---

## Definition of done (per cluster, when this is eventually planned)

Each cluster's plan must end with the **full local gate green** before its squash-merge to `main` (per CLAUDE.md): `ruff format/check` + `ty` (backend untouched but cheap to confirm), `pytest -x`, and `( cd frontend && npm run lint && npm test -- --run && npm run build && npm run knip )`. recharts additionally gets a visual UAT checklist. If a single package in a cluster can't be made green, pin it back and note it (same escape hatch 260531-jga used).
