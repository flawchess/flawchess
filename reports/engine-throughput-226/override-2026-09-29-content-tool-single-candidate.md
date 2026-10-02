# Accept-rule override: root-split content tool, single-candidate roots

**Date:** 2026-09-29
**Decided by:** Orchestrator-authored under the owner's autonomy instruction (Plan 226-12, gate
run); **pending owner ratification.**
**Scope:** `reports/engine-throughput-226/accept-rule.md` §3 "Root-split content and determinism",
the two `engine-root-split-content.mjs --split-source pool` commands at arm A21S, and §1's
"no arm changes tooling" content assertion as it applies to that one tool at that one arm.
**Rule file:** NOT edited.
**Revert target:** treat this override as void, discard `gate/a21s/content/`, and re-open the
content criterion for the owner if the reasoning below is rejected.

---

## What happened

The first gate run of `engine-root-split-content.mjs --split-source pool --hash clear` at A21S
(`f6c1f7a54`) aborted on the fixture row HEzVd (`6k1/p1r4p/1p4p1/4pq2/7Q/P7/1P6/K6R w - - 4 36`):

```
FAILURE: pool.rootSplitStats().splits did not rise by one for 6k1/p1r4p/... (before=29 after=29)
```

HEzVd has exactly one root candidate (step-0 prototype row: `n=1 k=1`). The pool's
`splitAcrossFreeEngines` (`scripts/lib/stockfish-pool.mjs`, Plan 226-01) deliberately takes the
single-grade path when `k <= 1` or the candidate list has one entry, matching the app's
`WorkerPool.gradeRoot` (`k <= 1` delegates to `grade`). The content tool (Plan 226-06) asserted
`splits + 1` unconditionally. It could not be exercised in pool mode before A21S existed, since it
exits 3 there by design, so this path was first reached in the gate itself.

## Why this is a tool defect, not an engine finding

- The engine behaviour is the specified one (L-3: `k` clamped to `[1, n]`; a one-candidate root
  cannot be split).
- The tool's own `k` snapshot, `min(freeCount, n)`, was already computed. It was simply not used
  in the assertion.
- The fix changes only the expectation, from `+1` to `+(k > 1 ? 1 : 0)`. It changes nothing in
  what is measured, how rows are built, or the grades compared.

## What was changed, and how the gate step was run

- Fix commit: `fix(226-12): content tool expects no split for k<=1 roots` (this override's
  sibling commit), `scripts/engine-root-split-content.mjs` only.
- The two pool-mode content commands at A21S ran from the `../flawchess-226-a21s` worktree
  (engine code byte-identical to `f6c1f7a54`) with that single tool file replaced by the fixed
  version. No other arm runs this tool, so cross-arm tooling identity for every criterion that
  compares arms is unaffected.
- Every other gate step (throughput, stop rule, determinism, warm arm, MQ, calibration) ran with
  tooling byte-identical to the arm SHAs, as §1 requires.
- One-candidate rows are kept. Their split-vs-single `|Δes|` is 0 by construction (same single
  grade), exactly as the step-0 prototype run recorded them (`n=1 k=1 mean|de_s|=0`). The Clear-Hash
  and warm content means therefore stay comparable to the step-0 design inputs.
