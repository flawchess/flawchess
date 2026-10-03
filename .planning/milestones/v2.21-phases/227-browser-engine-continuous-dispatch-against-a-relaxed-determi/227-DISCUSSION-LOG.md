# Phase 227: Browser Engine Continuous Dispatch Against a Relaxed Determinism Target - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-10-02
**Phase:** 227-browser-engine-continuous-dispatch-against-a-relaxed-determi
**Areas discussed:** WebGPU (keep or drop); the other four areas were left to Claude ("no preference")

---

## Pre-question: should WebGPU Maia be dropped altogether?

The owner asked whether there is a case for dropping WebGPU and what would be lost.

Claude's analysis:
- **Lost by dropping:** an unmeasured Maia speedup for desktop Chrome/Edge with `shader-f16` and for Android Chrome. Maia is 27% of bot wall and 55% of analysis wall on wasm. The ~15 ms WebGPU figure is an assumption, and batch-1 GPU inference may gain little. Also lost: CPU headroom for Stockfish, since wasm Maia's 4 threads compete with the SF pool and continuous dispatch makes them run at the same time.
- **Gained by dropping:** one Maia cost profile (L-6 and the other-machine prerequisite go away), no 24.3 MB asyncify runtime, no adapter probe or respawn path, and no untestable failure class. Sentry shows Android inference ×5, Android page-killed ×1 and Windows ×1 in 30 days after the iOS fix. It also likely makes policy content uniform across devices (fp16 GPU kernels; unverified).
- No success telemetry exists, so the share of WebGPU users is unknown.

| Option | Description | Selected |
|--------|-------------|----------|
| Measure, then decide (recommended) | 227's prerequisite becomes a WebGPU-vs-wasm comparison; keep or drop follows from it | |
| Drop WebGPU now | Separate quick task before 227; size on wasm only | |
| Keep it, proceed as planned | WebGPU stays; D-02 prerequisite sizes the desktop win | ✓ |

**User's choice:** Keep it, proceed as planned.

---

## Gray-area selection

| Option | Description | Selected |
|--------|-------------|----------|
| Tolerance & ship bar | D-06 floor measured 0; replacement anchor and "substantial" gain | |
| WebGPU measurement | Who and how; gate vs size; CPU contention | |
| In-flight work semantics | Cancel vs drain on stop; pending exclusion vs virtual loss; overshoot; cache race | |
| Rollout & calibration | Callers, flag default, harness parity, refit budget | |

**User's choice:** "[No preference]". Claude decided all four areas with recommended defaults (CONTEXT.md D-01..D-04, D-06..D-16).

---

## Claude's Discretion

- **Tolerance anchor:** the 0.0168 content-instrument floor with k = 1.5 (about 0.0252, matching 226's warm CONTENT_MAX). It replaces the degenerate zero round-mode floor.
- **Ship bar:** ≥ 15% CPU-normalized wall on the bot or analysis path, no regression > 3% on the other, pool-2 no regression, interleaved arms.
- **WebGPU:** a dev-only browser tool, run by the owner on a WebGPU machine. It sizes and reports; it is blocking only on "continuous not slower than round on WebGPU".
- **In-flight:** hard pending exclusion, arrival-order apply, cancel in-flight on stop/abort (zero applied), no maxNodes overshoot, c = 4, c = 1 byte-identity tripwire.
- **Review:** disposition all X-/Y- findings from Phase 198, then two independent-context reviewers.
- **Rollout:** both callers, flag defaults to continuous in the app, harness parity, ship plus one refit on a powered shift.

## Deferred Ideas

- Dropping WebGPU (rejected; revisit if the measurement shows no clear win)
- Concurrency above 4
- Maia success telemetry

---

## Follow-up: guiding principle

**User:** "For this phase, again, we don't want to treat the current flawchess engine as gospel. We'll rather make the decisions thinking from first principles, and based on what the tests show."

**Effect on CONTEXT.md:**
- Added D-00.
- D-01 changed from "picked-move es within ±tolerance of round mode" to **one-sided non-inferiority on absolute d20 quality**. Divergence is report-only.
- D-03 now counts move-quality regressions in **both directions** (net count).
- D-08 justifies pending exclusion on its merits, and adds a virtual-loss arm if the data shows exclusion hurting.
- D-10 keeps c = 4 for scope reasons only.
- Pre-registration is kept: it protects the evidence, not the old engine.
