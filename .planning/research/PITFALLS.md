# Pitfalls Research

**Domain:** Client-side MCTS practical-play chess engine (Maia + Stockfish.wasm) in a mobile-first PWA
**Researched:** 2026-07-05
**Confidence:** MEDIUM overall (HIGH on protocol/determinism facts already proven in Phase 151/151.1; MEDIUM on browser-memory facts, cross-checked across independent sources but not FlawChess-device-measured; LOW-to-MEDIUM on Maia-drift extrapolation — the underlying papers are real and cross-checked, but no paper tests our exact "static prior, never re-searched" configuration, so treat "may not transfer" as a hypothesis to validate, not a settled fact)

This research assumes the SEED-082 design is locked (expectimax-inside-MCTS, asymmetric self/opponent ELO, static Maia prior, client-side pool of 2-4 single-threaded stockfish.wasm workers, no SAB). Pitfalls below are scoped to what's specific to *this* engine, not generic MCTS/chess-engine advice — see `.planning/seeds/SEED-082-human-playable-line-engine.md` for the algorithm this assumes.

## Critical Pitfalls

### Pitfall 1: Stockfish worker pool + onnxruntime-web Maia model exceed mobile Safari's memory ceiling

**What goes wrong:**
Each stockfish.wasm worker instance loads its own NNUE net into its own WASM linear memory (no sharing across workers without SharedArrayBuffer, which this design deliberately forgoes). A pool of 2-4 workers plus one onnxruntime-web Maia session plus the existing live-eval `useStockfishEngine` instance (already running on `/analysis`) means the page can be holding 3-6 independent WASM heaps concurrently. Mobile Safari has an observed hard ceiling around ~100MB (iPhone) / ~200MB (iPad) for a web page — far below the 4GB theoretical WASM limit — and multiple WebKit bugs confirm memory growth is not released within a page's lifetime, so repeated re-analysis across positions in a review session accumulates toward that ceiling rather than plateauing. The failure mode is a silent tab reload/crash, not a catchable JS exception — the worst possible UX (user loses their analysis state with no error message, on the platform where the PWA is a first-class install target).

**Why it happens:**
Desktop Chrome development masks this completely — Chrome's WASM memory limits are effectively unbounded for this workload, so a design/implementation that "works great" in local dev testing can silently fail for the iOS Safari / installed-PWA segment of the user base only, discovered late (or not at all, if the team primarily dev-tests on desktop Chrome, per this project's own dev workflow bias).

**How to avoid:**
- Budget memory explicitly per platform, not just per feature: measure actual per-worker RSS (Chrome `performance.memory` / task manager, and Safari Web Inspector on a real iOS device) for one stockfish.wasm instance + one onnxruntime-web session *before* committing to a pool size, not after.
- Cap the pool size adaptively: use `navigator.hardwareConcurrency` and a coarse mobile/desktop heuristic (viewport width or `navigator.userAgentData`/UA sniffing as fallback) to run 2 workers on mobile, up to 4 on desktop — never a fixed "2-4" the SEED phrases it as a range.
- Never run the FlawChess Engine MCTS pool and the existing free-standing `useStockfishEngine` eval bar concurrently on the same position — they must share one Stockfish "budget," either by disabling the primary eval bar while the Engine searches or by having the Engine reuse the primary worker's output at the root (avoid double-loading a NNUE net for the same position).
- Explicit teardown on navigation away from `/analysis` and on tab-hide (already the pattern in `useStockfishEngine.ts`/`useStockfishGradingEngine.ts` — extend the same `worker.terminate()` discipline to every pool member, not just the first).
- On iOS Safari specifically, prefer the plain (non-JSEP) WASM execution provider for onnxruntime-web over WebGPU/JSEP — Safari 26 JSEP mode shows documented severe CPU/memory blowup post-inference in unrelated onnxruntime-web issues; the non-JSEP WASM backend is the one reported stable.
- Add a graceful-degradation floor: if pool creation or first-inference fails (catch onnxruntime-web/Worker errors), fall back to pool size 1 or disable the FlawChess Engine layer entirely with a clear "not available on this device" message rather than crashing the page.

**Warning signs:**
- Any manual test on a real iOS device (not simulator) that leaves multiple positions analyzed in one session without a page reload.
- Chrome DevTools memory profile showing linear, non-decreasing WASM heap growth across repeated `go`/`analyze` cycles instead of a plateau.
- Sentry frontend errors spiking specifically from iOS Safari user agents with no clear JS stack (page-reload crashes often don't produce a catchable exception at all — look for session/pageview drop-off in Umami analytics filtered to iOS, not Sentry).

**Phase to address:**
Architecture/spike phase, before the pool is wired into the search (test the concurrency budget in isolation first); re-verified as an explicit UAT gate in whichever phase ships the worker pool to production, on a real low/mid-tier Android and an iPhone, not just desktop Chrome.

---

### Pitfall 2: Main-thread jank from synchronous work around the workers, not the workers themselves

**What goes wrong:**
Workers correctly keep Stockfish/Maia computation off the main thread, but the *orchestration* code that's easy to leave on the main thread — MCTS tree bookkeeping (node creation, backup, priority-queue reordering across the "current-best-line" favoring scheme the SEED calls for), SAN/UCI translation via `chess.js` for every candidate at every node, and any per-node Maia-distribution renormalization — is pure synchronous JS. At a "few hundred node evaluations" budget (the SEED's own arithmetic), this bookkeeping runs hundreds of times per search, and if it's non-trivial (e.g. re-instantiating a `chess.js` `Chess` object per node, which existing code already does per grading call), it can itself become the jank source even though "the engine is in a worker."

**Why it happens:**
"Put the heavy engine in a worker" is the obvious optimization and gets done; the orchestration layer around it looks cheap in isolation (a `Chess()` construction here, a sort there) and only compounds when multiplied by the search's node count, which nobody profiles until the UI visibly stutters on real hardware.

**How to avoid:**
- Keep the MCTS tree/backup logic itself off the main thread too — run the tree orchestration in a dedicated worker (or the same worker that owns the priority queue feeding the Stockfish pool), with only the anytime "current top-n lines" summary posted back to the main thread for rendering.
- Profile node-processing cost (not just engine eval cost) early with a synthetic budget (e.g. 500 simulated nodes with a stub evaluator) to catch orchestration-side slowness before real engine latency masks it.
- Batch the anytime UI updates (e.g. requestAnimationFrame-throttled, not "post a message on every single node backup") — this project already has a `RAPID_STEP_DEBOUNCE_MS` pattern in the existing hooks; reuse a similar coalescing discipline for MCTS's inherently high-frequency updates rather than introducing a new one from scratch.

**Warning signs:**
- Chrome Performance panel showing long main-thread tasks (>50ms) during an active search, with the flame graph attributing them to tree/JS logic rather than `Worker` message handling.
- Visible input lag (board clicks / slider drags feel delayed) specifically *while* the Engine search is running, on lower-end devices.

**Phase to address:**
The MCTS orchestration-layer implementation phase (MVP1 per SEED phasing) — add a profiling checkpoint to that phase's plan before declaring it done, not deferred to a later "performance polish" phase.

---

### Pitfall 3: The custom Maia-weighted backup rule silently degenerates into plain expectimax or plain MCTS

**What goes wrong:**
The design's one genuinely novel piece — non-root nodes back up the **Maia-prior-weighted expectation** over expanded children (not a UCT/PUCT visit-count-weighted average, not a pure max) — is easy to get subtly wrong in a way that still produces plausible-looking output, because MCTS's usual backup (average of child values weighted by visit count) is a very close-looking piece of code. If the backup accidentally uses visit-count weighting instead of (or blended with) the fixed Maia probability, the search silently converges toward "whichever child got explored most" rather than "what a human at opponent's ELO would actually play" — the entire practical-value semantics is gone, but nothing throws an error and the UI still shows a ranked line with a score.

**Why it happens:**
Every standard MCTS reference implementation (AlphaZero-style PUCT, textbook UCT) backs up via visit-count-weighted averages by construction; this design intentionally diverges from that textbook shape (Maia-prior weights fixed at expansion time, not re-derived from visit counts), and it is exactly the kind of "this looks like MCTS so it should behave like MCTS" trap where copy-adapting a reference implementation reintroduces the standard backup rule as a bug, not a design choice.

**How to avoid:**
- Write the backup rule as an isolated, directly unit-testable pure function: `backup(childValues: number[], maiaProbabilities: number[]) -> number`, deliberately taking `maiaProbabilities` as an explicit parameter that is *never* derived from `childValues`, `visitCounts`, or anything search-produced — so there is no code path by which visit counts can leak into the weighting even by accident.
- Golden-value unit tests: hand-construct a 2-3 child scenario with known Maia probabilities and known child values, assert the exact expected weighted sum, and assert the result does NOT equal the naive average or the visit-count-weighted average (a negative assertion that specifically catches the "reverted to textbook MCTS" bug).
- Separately unit test the root-is-max vs non-root-is-expectation branch — the single line of code distinguishing root from non-root backup is the whole "expectimax inside MCTS" thesis; a boundary bug here (e.g. off-by-one on "is this the root" during recursive backup) silently converts the top-level ranking to an expectation instead of a max, which changes *which move is recommended*, not just a score.
- Code review checklist item, not just tests: any PR touching the backup function must explicitly show the reviewer where the Maia weights come from and confirm they are frozen at node-expansion time.

**Warning signs:**
- Root move ranking that never disagrees with Stockfish's top move even in positions handpicked to have an objectively-second-best swindle line (SEED-082's own "killer feature" — if it never fires on curated test positions, the backup rule is suspect).
- A search whose top line changes meaningfully between two runs with a fixed node budget and no randomness (see Pitfall 5) — often traceable to a visit-count-order dependency that shouldn't exist in a probability-weighted backup.

**Phase to address:**
The core MCTS backup implementation phase (the phase after Phase 151's per-node primitive lands) — this is the single highest-value unit-test investment in the whole engine; do not let it ship behind only integration/UI tests.

---

### Pitfall 4: Asymmetric self/opponent ELO gets crossed at the node level

**What goes wrong:**
The design's structural claim — opponent-ELO Maia distribution at opponent-to-move nodes, self-ELO Maia distribution at your-future-move nodes — requires every node in the tree to correctly track "whose ELO applies here," which flips every ply. A tree built with a naive `depth % 2` parity check is exactly one off-by-one (whether root is "your move" or ply 0 is counted from White regardless of whose turn it actually is) away from silently querying the *wrong* ELO at every node — meaning the entire tree reflects "what would I play at the opponent's rating" and vice versa. This produces a coherent-looking, fully-functional search with completely inverted semantics: it would rank lines by how well the *opponent* executes moves you're claimed to make, an error invisible without a targeted test.

**Why it happens:**
Side-to-move parity bugs are the single most common chess-tree bug class in general (this project's own codebase already had to fix a POV-sign bug in the grading worker, see `useStockfishGradingEngine.ts`'s white-POV normalization), and here the stakes are higher because getting parity wrong doesn't just flip a sign on a score — it swaps which ELO's move-distribution shapes half the tree.

**How to avoid:**
- Derive "whose ELO" from the actual side-to-move color extracted from the position (already how `useStockfishGradingEngine.ts` does it: `fenToGrade.split(' ')[1] === 'b'`), tagged against the analyzed player's known color at the root — never from tree depth parity or move-count parity alone. Root color is a first-class input to the search (the player being analyzed), not inferred.
- Unit test with an explicit "who moves here" oracle: build a small fixed tree (3-4 plies) and assert, per node, which ELO was queried, using a mock Maia function that records its ELO argument — verifiable independent of the rest of the search.
- Test both starting colors (root = White to move, root = Black to move) — a parity bug that only manifests when the player is Black is exactly the kind of bug that survives a White-only dev-testing habit.

**Warning signs:**
- The FlawChess Engine's practical score for a very strong player analyzing a weak-opponent's win consistently looks *worse* than expected (or vice versa) — a symptom of the ELOs being swapped so "your" execution is modeled as the weaker side.
- Any manual review where the Engine's top line, when replayed, has *your* moves looking suspiciously "textbook engine" and the *opponent's* replies looking suspiciously "beginner blunder-prone" regardless of the actual rating gap configured — a tell that the wrong distribution is being sampled at the wrong nodes.

**Phase to address:**
The core MCTS implementation phase, same phase as Pitfall 3 (it's the same node-construction code) — cover both in the same unit-test suite so a reviewer sees "backup rule" and "ELO-at-node" tested together as the two load-bearing pieces of the custom algorithm.

---

### Pitfall 5: Non-determinism creeps in from MCTS internals despite "no Dirichlet noise, fixed node budget"

**What goes wrong:**
The SEED locks reproducibility as a design requirement ("no Dirichlet noise, deterministic tie-breaking, fixed node budgets in tests"), but MCTS implementations have several *other* common non-determinism sources beyond the obvious exploration-noise one: (1) `Map`/object iteration order when expanding children isn't guaranteed stable if keyed by something derived from a `Set` or hash rather than an explicit sort; (2) worker-pool result *arrival order* is inherently non-deterministic (whichever leaf's Stockfish eval finishes first gets backed up first), and if the tie-break for "next node to expand" or "which of two equal-value lines to display first" depends on arrival order rather than a canonical sort, the displayed top-2 lines can flicker between equivalent runs; (3) floating-point summation order for the Maia-weighted expectation is technically non-associative, so summing children in a different order can produce a bit-different (usually irrelevant, but test-breaking) float.

**Why it happens:**
"No randomness in my RNG calls" is necessary but not sufficient for determinism in a concurrent, worker-pool-fed system — the *scheduling* of async work (which leaf comes back from which worker first) is a second, easy-to-overlook non-determinism source that has nothing to do with Dirichlet noise or tie-break logic as usually understood.

**How to avoid:**
- Explicit canonical ordering for every "pick among equals" decision: sort candidate moves by a fixed key (e.g. UCI string) before any tie-break, never by insertion order or `Map` iteration order.
- Decouple "when a leaf eval arrives" from "how it affects final output": buffer worker results and apply them to the tree in a canonical (e.g. node-ID) order at each synchronization point, rather than applying backups in raw arrival order — this both fixes the flicker and makes results reproducible independent of which worker happened to be free first.
- For the deterministic-test requirement specifically: run the full pipeline (not just the backup math) against a stubbed/deterministic Stockfish response (fixed eval per FEN) in CI, and assert bit-identical output across repeated runs — this is the only way to catch scheduling-order non-determinism, since a live Stockfish response is inherently variably-timed.
- Treat any observed non-determinism in "no Dirichlet, fixed budget" testing as a real bug immediately — don't rationalize small differences as "engine variance," since actual live-Stockfish nondeterminism (documented elsewhere in this project's `project_eval_nondeterminism.md` memory: `eval_cp` isn't reproducible across machines) is a *different, accepted* source that must not be confused with an MCTS orchestration bug.

**Warning signs:**
- A CI determinism test that passes locally but flakes only under `pytest -n auto`-style parallel execution or under different machine load — a hallmark of arrival-order-dependent non-determinism.
- The displayed top-2 FlawChess Engine arrows changing between two page loads of the identical position with an identical node budget and no new game data.

**Phase to address:**
The MCTS orchestration/worker-pool integration phase — add a "deterministic replay" test harness (stub engine, fixed responses) as an explicit deliverable of that phase, not an afterthought bolted on when a flake is reported later.

---

### Pitfall 6: `multipv` index reused as a move identity anywhere new is added (repeat of the already-fixed Phase 151.1 bug)

**What goes wrong:**
Phase 151.1 already found and fixed this exact bug in `useStockfishGradingEngine.ts` — the UCI `multipv` field is an **eval rank** that reorders as search depth increases (line 2 at depth 10 can become line 1 at depth 14), not a stable move identifier. The fix keys grades by `pv[0]` (the actual move) instead. The risk for v2.0 is that this same landmine gets re-triggered in *new* code the MCTS layer introduces: any code path that grades multiple Stockfish leaves via a single MultiPV search (e.g. root-level multi-PV grading feeding the union-of-candidates step the SEED describes) is a fresh opportunity to key by `multipv` index again, because the bug is not structurally prevented by a type system — it's a convention that has to be remembered and re-applied at every new call site.

**Why it happens:**
The bug is easy to reintroduce because `info depth N multipv K pv <move> ...` naturally reads like "K identifies which line," and only a spike-level real-binary test (as Phase 151.1's did) surfaces that `multipv` reorders mid-search; a developer writing new grading code without re-reading the 151.1 postmortem has no structural signal warning them off the natural-looking `multipv`-as-key approach.

**How to avoid:**
- Extract the "parse a UCI info line, key by `pv[0]`" logic Phase 151.1 already wrote (`parseInfoLine` / the `sanFromUci` pattern in `useStockfishGradingEngine.ts`) into one shared, reused utility rather than letting every new grading call site reimplement info-line parsing from scratch — a shared function is a structural guardrail that a comment alone is not.
- Add an explicit code-review checklist line for any PR touching Stockfish UCI parsing: "does this key results by `pv[0]`/move, not by `multipv`?"
- A cheap regression test: assert that a synthetic sequence of `info` lines where `multipv` values for two lines swap between two depths still produces grades keyed correctly by move, not by rank.

**Warning signs:**
- Grades that "jump" between two different moves mid-search in a way that looks like the wrong move got a wrong score — a subtle UI symptom, not a crash.
- Any new file with its own `parseInfoLine`-shaped function that isn't importing the one Phase 151.1 already built.

**Phase to address:**
Any phase adding a new Stockfish MultiPV consumption path (root-level candidate grading, leaf-batch grading for the MCTS pool) — verification step: grep for `multipv` usage across the new code and confirm every read site keys by `pv[0]`, not the `multipv` field.

---

### Pitfall 7: Deep MCTS lines look impressively "sharp" but are Maia-out-of-distribution garbage

**What goes wrong:**
Cross-checked across three independent papers (Maia's own KDD 2020 ablation, the 2026 Maia-2+MCTS follow-on, and ALLIE/ICLR 2025's need for *time-adaptive*, not full, search), search specifically degrades a human-move model's calibration. The SEED's mitigating nuance — FlawChess uses Maia's *static* policy as fixed expectimax weights and never re-searches to sharpen Maia's own output — is a real and load-bearing distinction, but it does not fully neutralize the underlying mechanism: Maia is trained on real human games, and a 6-10-ply engine-guided tree explores move sequences (both "your" engine-suggested candidates and the opponent's Maia-sampled replies compounding together) that increasingly diverge from realistic human game continuations the deeper the tree goes — engine-preferred lines are systematically different from what humans actually play into. Every Maia probability queried at an out-of-distribution position carries larger, unknown estimation error, and those errors compound multiplicatively through the recursive expectation. A depth-10 line can display a confident-looking practical score built on several out-of-distribution Maia queries whose true error is unbounded.

**Why it happens:**
Nothing in the code path *fails* when Maia is queried on a weird, engine-shaped position — the model has no confidence/out-of-distribution signal, it will confidently output a probability distribution for any legal position it's given, including ones drawn from a completely different distribution than its lichess training data. The failure is silent and only shows up as "this recommendation feels wrong" in manual review, potentially long after ship.

**How to avoid:**
- Honor the SEED's own depth cap strictly (6-10 explicit plies) — treat this as a hard ceiling enforced in code (a constant, reviewed like any other magic number per this project's coding guidelines), not a soft target that creeps upward when someone wants "just a bit more lookahead" for a demo position.
- Build a small curated validation set of hand-picked positions (10-20, spanning opening/middlegame/tactical/quiet) specifically to eyeball whether the depth-6-10 practical lines look like plausible human continuations, not engine-only-computer sequences — this is a manual/qualitative gate, not a metric, and should run before the MCTS layer ships, then again whenever the leaf sigmoid or candidate-selection logic changes.
- Consider (as a cheap diagnostic, not a shipped feature) logging the mean Maia top-move probability mass at each depth of a sample of searches — a mass that collapses toward uniform/low-confidence deep in the tree is a measurable proxy for "drifting out of distribution," useful for internal tuning even if never surfaced to users.
- Do not let this pitfall block MVP1 — the SEED explicitly treats "beyond the horizon everyone converts like an average lichess player" (the leaf sigmoid) as a known, accepted MVP limitation; the actionable prevention here is bounding *explicit search depth*, not eliminating the underlying drift (which requires per-ELO leaf calibration, explicitly deferred).

**Warning signs:**
- Any depth-10 "practical" line in manual review that a domain expert (or the project owner, a strong club player) immediately recognizes as "no human would ever reach this exact position by playing naturally" — the intended qualitative check.
- A validation-set line whose practical score materially disagrees with a quick sanity gut-check from a strong player, especially at the deep end of the tree.

**Phase to address:**
The MCTS core-search phase should hard-code the depth cap; a lightweight "sanity validation set" pass belongs in that same phase's UAT/verification step (per this project's Nyquist-validation conventions), not deferred to a later polish phase.

---

### Pitfall 8: Presenting an objectively-inferior "best practical" move without it looking broken

**What goes wrong:**
The engine's headline feature — ranking an objectively second-best move above Stockfish's top choice because the opponent is statistically likely to blunder against it — is functionally identical, from a naive user's perspective, to a buggy engine recommendation. Users (especially ones coming from Stockfish-only tools where "best move" always means "objectively best") will see a move that Stockfish's own arrow layer (kept visible per the SEED's four-arrow-layer design) disagrees with, and the default reaction to two engines disagreeing is "one of them is wrong," not "one of them understands human opponents better." Trust erodes fast if the disagreement isn't explained inline, every time it happens — not just discoverable via a tooltip a user has to go looking for.

**Why it happens:**
The team building the feature deeply understands *why* the disagreement is the point (it's the whole SEED thesis); a first-time user has none of that context and will apply "engine disagreement = one of them is broken" priors formed by every other chess tool they've used.

**How to avoid:**
- Never show the FlawChess Engine's top move without the paired objective-vs-practical score simultaneously visible (the SEED already locks this: "objectively +3.0, practically +0.9 for you") — the score pair *is* the explanation, and it must never be one click/hover away from the arrow itself.
- Copy discipline (already locked in the SEED and CLAUDE.md communication style): never "best move" unqualified, always "best **practical** move for you" — audit every UI string that touches this feature, not just the primary label, for accidental unqualified "best move" phrasing (button labels, empty states, tooltips, exported/shared text).
- When the FlawChess Engine and Stockfish top-2 arrows actually disagree at the root, that specific moment is the single highest-value place for a one-line inline explanation ("opponents at this level miss the refutation Xd7! 70% of the time") — not a generic disclaimer shown regardless of whether disagreement occurred.
- Ship the Maia-top-2 arrow layer alongside (already in the SEED's four-layer design) so a curious user can trace *why*: hovering shows the opponent's actual reply-probability distribution, turning "the engine looks wrong" into "oh, I see, that's what opponents actually play."

**Warning signs:**
- Any UAT session (even informal) where a tester's first reaction to seeing the FlawChess Engine arrow disagree with Stockfish's is confusion or "is this broken?" rather than curiosity — that's the copy/explanation failing, not the algorithm.
- Support/feedback messages (this project has an in-app feedback modal) reporting "wrong best move" specifically on positions where a swindle line was surfaced.

**Phase to address:**
The UI/display phase (modal-path line display + score pair, per SEED MVP1) — this is a `/gsd-ui-phase` / `/gsd-ui-review` candidate, not just a functional-completeness check; explicitly UAT the disagreement-explanation flow with a fresh (non-team) reviewer if possible.

---

### Pitfall 9: Anytime refinement flicker makes the "top line" feel unstable / untrustworthy

**What goes wrong:**
MCTS's anytime nature means the top-ranked root line can genuinely change as the search deepens (a line that looked best at 50 nodes gets overtaken at 300 nodes) — this is correct behavior, but naively re-rendering the board arrows and line text on every update produces visible flicker: an arrow jumping between two squares, move text changing mid-read. Combined with Pitfall 5's determinism concerns, unstable-looking output (even when each intermediate state is "correct for its budget so far") reads as buggy rather than "still thinking."

**Why it happens:**
"Anytime" is treated as a purely backend/algorithmic requirement (SEED: "quick top-n lines immediately, refined live as the search deepens") without an explicit UI-side damping strategy — the natural implementation posts every intermediate ranking straight to the DOM.

**How to avoid:**
- Explicit UI-side hysteresis: only promote a new candidate to the "displayed top line" position if it beats the current displayed line by a minimum margin (not just "is currently ranked #1 by any amount"), and/or require it to hold the #1 rank for N consecutive updates before the arrow moves — this project already has a debounce precedent (`RAPID_STEP_DEBOUNCE_MS`) worth extending conceptually here, though the mechanism differs (rank-stability threshold, not just time-based debounce, since the search itself is continuously running).
- Distinguish "searching, refining" from "settled" in the UI explicitly (e.g. a subtle depth/node-count indicator or a brief "still refining" state) so users don't read early flicker as final output — similar in spirit to this project's existing Stockfish eval bar's depth indicator.
- Cap the update-render frequency independent of node-arrival frequency (batch to e.g. every N nodes or every Xms of wall clock, whichever is coarser) — this both solves Pitfall 2's main-thread cost and this pitfall's visual flicker with one mechanism.

**Warning signs:**
- Any manual test scrubbing through a position where the top-line arrow visibly jumps back and forth more than once or twice during a single search.
- User-facing complaints (or internal dogfooding reactions) describing the recommendation as "flaky" or "keeps changing its mind."

**Phase to address:**
The anytime-refinement / live-update UI phase (MVP1, alongside Pitfall 8's display work) — pair this with the orchestration-layer batching from Pitfall 2 so it's solved once, not twice.

---

### Pitfall 10: Testing a probabilistic engine devolves into "no automated tests, trust me" or brittle exact-output snapshots

**What goes wrong:**
Two failure modes at opposite extremes are both common for this class of system: (a) the team concludes "it's inherently non-deterministic / depends on live engines, so we can't really unit test it" and ships with only manual eyeballing, leaving regressions (a backup-rule bug, an ELO-parity bug) to be caught by users, not CI; or (b) the team snapshot-tests exact output against a live Stockfish/Maia run, which is brittle for reasons that have nothing to do with real regressions — Stockfish version bumps, WASM build changes, or even machine-to-machine `eval_cp` non-determinism (already an accepted, documented fact in this project's own `project_eval_nondeterminism` memory) will break the snapshot and train the team to ignore red CI.

**Why it happens:**
"Probabilistic" and "non-deterministic" get conflated — the *search orchestration* (backup math, ELO routing, tie-breaks) is fully deterministic and testable in isolation (Pitfalls 3-5 already established this); it's only the *live engine outputs* (actual Stockfish eval numbers, actual Maia probabilities from the real ONNX model) that are appropriately variable. Teams that don't draw this line either over-mock (testing nothing real) or under-mock (testing against live nondeterminism).

**How to avoid:**
- **Layer the test strategy** to match where determinism actually lives, per the SEED's own guardrail (search behind a small interface, `position + budget -> ranked root lines`):
  1. **Pure backup/orchestration unit tests** (Pitfalls 3-5): stub both Stockfish and Maia with fixed, hand-authored responses; assert exact numeric output. Fully deterministic, fast, run on every commit — this is the bulk of the test investment and the highest-value one, since it catches the algorithm bugs that matter most (Pitfalls 3, 4, 5, 6).
  2. **Golden-position integration tests** against the *real* engines but asserting only *qualitative/structural* properties, not exact scores: "the top-2 lines are legal," "the practical score is between the min and max Stockfish child eval" (a sanity bound the backup math should satisfy), "a known swindle position (curated, e.g. from the validation set in Pitfall 7) ranks the trap move above Stockfish's top move" — properties robust to Stockfish-version/`eval_cp` drift, similar in spirit to this project's existing `test_centipawn_convention_signed_from_white`-style invariant tests rather than exact-value assertions.
  3. **Determinism regression test** (Pitfall 5): fixed stub engine, assert bit-identical output across repeated runs — this is the one place exact-match assertions are appropriate, precisely because the engines are stubbed.
- Never snapshot-test exact centipawn/probability values against a *live* Stockfish or Maia call in CI — this project already has hard-won experience (`project_eval_nondeterminism.md`) that `eval_cp` differs across machines even for the backend's own server-side Stockfish; the browser-side engine will be at least as variable, plus browser/OS/WASM-runtime variance on top.
- Build the curated golden-position set (Pitfall 7's validation set can double as this) once, check it into the repo (e.g. as FEN + expected-property assertions, mirroring this project's existing `fixtures/tagger/*.csv` pattern for the tactic detector), and treat it as a precision/recall-style regression gate the way `tactic-tagger-report` already works for a different probabilistic detector in this codebase — same pattern, new domain.

**Warning signs:**
- A test suite for this feature with zero unit tests on the backup function itself, only end-to-end tests that spin up real Worker/WASM instances.
- Any CI flake on this feature that gets silenced with `--rerun` or a skip rather than root-caused — a strong signal the test is asserting something inherently non-deterministic (live engine values) that should have been a structural/bounds assertion instead.

**Phase to address:**
Test strategy should be designed alongside the core MCTS phase (Pitfalls 3-5's unit tests) and the golden-position set alongside Pitfall 7's validation work — do not defer "how do we test this" to a separate later `/gsd-add-tests` pass; for a system this algorithm-sensitive, tests-after risks locking in an already-subtly-wrong backup rule that "passes" only because nothing checks its actual math.

---

## Technical Debt Patterns

| Shortcut | Immediate Benefit | Long-term Cost | When Acceptable |
|----------|-------------------|-----------------|------------------|
| Fixed pool size (e.g. always 4 workers) instead of device-adaptive sizing | Simpler code, faster to ship MVP1 | Mobile OOM crashes discovered late, in production, on devices the team doesn't dev-test on | Never past the spike/architecture phase — must be adaptive before shipping to `/analysis` (mobile-first PWA) |
| Reusing `useStockfishEngine`'s eval bar and the new MCTS pool simultaneously without coordinating a shared budget | Avoids refactoring the existing hook | Doubles peak memory/CPU exactly when the user is most engaged (actively analyzing) | Only acceptable behind a feature flag during internal development; must be resolved before public ship |
| Skipping the pure-function extraction for backup rule / ELO routing (inlining it in the MCTS loop) | Faster initial implementation | Untestable in isolation — Pitfalls 3 & 4 become unfindable except by full-integration debugging | Never — extract as pure functions from the first implementation, not as a later refactor |
| Snapshot-testing exact live-engine output "just to get some coverage" | Quick CI green checkmark | Brittle, flaky, trains the team to ignore red CI (this project has already learned this lesson elsewhere re: `eval_cp` nondeterminism) | Never for this feature; use bounded/structural assertions instead (Pitfall 10) |
| Letting explicit search depth creep past 10 plies "just for this one demo position" | Looks impressively deep in a demo | Reintroduces Pitfall 7's Maia-drift risk with no corresponding validation | Never in shipped code; fine as a one-off local experiment, gated behind a dev-only constant override, never the shipped default |

## Integration Gotchas

| Integration | Common Mistake | Correct Approach |
|--------------|------------------|--------------------|
| stockfish.wasm UCI `searchmoves` | Passing any candidate move (including one derived from a bad SAN→UCI conversion) straight into `searchmoves`, trusting the engine to reject bad entries loudly | Filter to only legal, correctly-converted UCI moves before building the `searchmoves` string — illegal entries are silently dropped, under-counting MultiPV lines with no error (already known from Phase 151.1; re-verify at every new grading call site, per Pitfall 6) |
| onnxruntime-web execution provider selection | Letting the library auto-pick WebGPU/JSEP on iOS Safari | Explicitly configure/prefer the plain (non-JSEP) WASM backend on iOS, given documented Safari 26 JSEP memory/CPU blowup issues; test the actual selected backend on real iOS hardware, not just that "it loads" |
| Stockfish `multipv` field | Keying any result map by the `multipv` rank | Key by `pv[0]` (the move) always — `multipv` reorders as depth increases (confirmed on FlawChess's own real binary in Phase 151.1) |
| Worker pool result routing | Applying leaf-eval results to the tree in raw arrival order | Buffer and apply in a canonical order at synchronization points (Pitfall 5) so output doesn't depend on which worker happened to finish first |
| Maia (onnxruntime-web) + Stockfish (wasm) memory coexistence | Treating each engine's memory footprint as independent, testing them in isolation only | Test the *combined* concurrent footprint (both engines + the pool, running together, on the actual page) — isolated per-engine testing misses the additive/peak effect that causes mobile crashes |

## Performance Traps

| Trap | Symptoms | Prevention | When It Breaks |
|------|----------|------------|-----------------|
| Uniform-depth expectimax instead of MCTS's adaptive allocation | Most of the seconds-scale node budget spent evaluating lines already dead by ply 2 | This is exactly why the SEED chose MCTS over depth-limited expectimax for MVP — keep the depth-limited version only as the documented recoverable fallback behind the same interface, never as the shipped default | Any position with a node budget under a few thousand evals (i.e. always, given the ~50-300ms per-eval cost the SEED itself computes) |
| Re-instantiating `chess.js` `Chess()` objects per node for SAN/UCI conversion | Main-thread orchestration cost scales with node count and becomes visible jank at higher budgets, masking as "engine is slow" when it's actually JS orchestration | Profile orchestration cost separately from engine-call cost (Pitfall 2); consider caching parsed board state per node rather than reconstructing from FEN repeatedly | Once node budgets exceed roughly a few hundred (i.e. essentially immediately, per the SEED's own budget arithmetic) |
| Un-batched anytime UI updates (post every node backup to React state) | Main thread churns re-rendering on every single node instead of at a sane cadence; compounds with mobile's weaker CPUs | Batch/throttle emission (Pitfall 2 and Pitfall 9 share this fix) | Any budget above a trivial handful of nodes; worse on mobile |
| Running the FlawChess Engine pool concurrently with the pre-existing live eval bar's own Stockfish worker | CPU contention on the same device makes both features slower than either alone; on mobile this can also trip thermal throttling | Coordinate: pause/share the primary eval bar's worker while the Engine search runs, or explicitly budget CPU between them | Any device with fewer effective cores than `1 (primary eval) + 2-4 (pool)` — i.e. most phones |

## Security Mistakes

| Mistake | Risk | Prevention |
|---------|------|------------|
| Assuming a future SAB/COOP/COEP upgrade path is risk-free | Retrofitting `COOP: same-origin` later (for multi-threaded Stockfish) breaks `window.opener` and silently breaks Google OAuth popup sign-in (already flagged as a blocker in the SEED) | Treat SAB/multithreading as a deployment-level decision requiring explicit auth-flow regression testing (e.g. scoping COOP headers to only the `/analysis` route, or `COEP: credentialless`) — not an incremental "just enable it" change; keep it deferred exactly as the SEED does until this is planned |
| Loading vendored Maia weights / stockfish.wasm binaries without integrity verification | A compromised CDN/build step could silently swap in a malicious WASM binary served to every user's browser (supply-chain risk, elevated because this project already does SHA-256 verification for its *server-side* Stockfish per CLAUDE.md) | Extend the same supply-chain discipline (checksum/pin) already used for the backend Stockfish binary to the client-vendored WASM/ONNX assets, not just the server one |

## UX Pitfalls

| Pitfall | User Impact | Better Approach |
|---------|-------------|-------------------|
| Showing the "best practical" move without the objective-vs-practical score pair every time | Users read engine disagreement as a bug (Pitfall 8) | Always pair the two scores; never show one arrow layer's recommendation as if it were unqualified "best move" |
| Flickering/unstable anytime top line | Erodes trust in the recommendation ("it keeps changing its mind") | Rank-stability threshold / hysteresis before promoting a new top line, decoupled from raw node-arrival frequency (Pitfall 9) |
| No "still searching" affordance | Users mistake an early, unrefined intermediate ranking for the final answer | Explicit depth/node/refining indicator, consistent with the existing Stockfish eval bar's depth display pattern |
| Silent mobile crash/page reload when memory is exhausted | User loses their entire analysis session with zero explanation, on the exact platform (installed PWA) this project is mobile-first for | Graceful capability-detection fallback (disable the Engine layer with a clear message) rather than letting the OS kill the tab (Pitfall 1) |

## "Looks Done But Isn't" Checklist

- [ ] **Backup rule correctness**: Often "looks done" once it produces *a* ranked line with *a* score — verify with the negative unit-test assertion (Pitfall 3) that it isn't secretly equivalent to plain visit-count-weighted MCTS or plain max.
- [ ] **Asymmetric ELO routing**: Often "looks done" once both a self-ELO and opponent-ELO parameter exist somewhere in the code — verify with a node-level oracle test (Pitfall 4) that each is actually applied at the *correct* nodes, not just that both values are threaded through the function signatures.
- [ ] **Determinism**: Often "looks done" once "no Dirichlet noise" is removed — verify with a repeated-run bit-identical test against a *stubbed* engine (Pitfall 5), since live-engine variance can mask real scheduling-order non-determinism as "expected engine variance."
- [ ] **Mobile viability**: Often "looks done" once it works on desktop Chrome during development — verify on a real, mid-tier Android device and a real iPhone (not just a browser devtools mobile emulation, which does not reproduce Safari's actual WASM memory ceiling) before considering the feature shippable.
- [ ] **Depth-cap enforcement**: Often "looks done" once a depth constant exists — verify it's actually a hard ceiling enforced in the search loop, not a soft default that a later change (e.g. "just extend the horizon a bit for this position type") can silently exceed.
- [ ] **`searchmoves`/`multipv` hygiene in new code**: Often "looks done" once a new grading/search call site works on the happy-path test position — verify (grep + review) it reuses the existing legal-move-filtering and `pv[0]`-keying utilities rather than reimplementing UCI parsing from scratch (Pitfall 6).

## Recovery Strategies

| Pitfall | Recovery Cost | Recovery Steps |
|---------|----------------|------------------|
| Backup rule shipped with a silent bug (Pitfall 3) | MEDIUM | Add the negative golden-value unit tests retroactively; if they fail, the fix is usually localized to the single backup function (isolated by design) — low blast radius if the interface boundary (SEED's `position + budget -> ranked lines`) was actually respected |
| Mobile memory crashes discovered post-ship (Pitfall 1) | MEDIUM-HIGH | Ship a capability-gated fallback (disable pool on low-memory devices via a feature flag) as a fast mitigation; follow with the proper adaptive-sizing fix; requires real-device testing to validate, which can't be rushed |
| ELO parity bug discovered post-ship (Pitfall 4) | LOW-MEDIUM | Isolated to the node-construction code path if the interface boundary held; add the oracle test, fix, and — because there's no persistence (client-side only, no server state per the SEED) — there's no backfill/migration needed, just a client redeploy |
| Anytime flicker reported as "buggy" by users (Pitfall 9) | LOW | UI-only fix (hysteresis threshold), no data/algorithm changes required; fast to ship independently of the search engine itself |
| Test suite discovered to only cover live-engine snapshot tests (Pitfall 10) | MEDIUM | Retrofit the pure-function unit test layer against the same production backup/routing code (no refactor needed if it was already extracted as a pure function per the "avoid" guidance); the *expensive* recovery case is if the logic was never extracted as a testable pure function to begin with, which requires an actual refactor first |

## Pitfall-to-Phase Mapping

| Pitfall | Prevention Phase | Verification |
|---------|-------------------|----------------|
| 1. Mobile/browser memory ceiling | Architecture/spike phase (pool sizing), re-verified at pool-shipping phase | Real-device (iPhone + mid-tier Android) memory profile under a realistic multi-position review session; no page reload/crash |
| 2. Main-thread jank from orchestration | MCTS orchestration implementation phase | Chrome Performance panel: no >50ms main-thread tasks attributable to tree/JS logic during an active search |
| 3. Backup rule degenerates to textbook MCTS | Core MCTS backup implementation phase | Negative unit-test assertions (backup output ≠ naive average, ≠ visit-count-weighted average) pass; root-vs-non-root branch explicitly tested |
| 4. Asymmetric ELO crossed at nodes | Same phase as #3 | Node-level oracle unit test recording which ELO was queried at each node, for both root colors (White and Black) |
| 5. Non-determinism from scheduling/float order | MCTS orchestration/worker-pool integration phase | Stubbed-engine, repeated-run bit-identical test in CI |
| 6. `multipv`-as-identity landmine reintroduced | Every phase adding a new Stockfish MultiPV consumption path | Grep audit: all new `multipv`-line readers key by `pv[0]`; reuses the shared parsing utility |
| 7. Maia distributional drift at depth | Core MCTS search phase (depth-cap enforcement) + validation-set pass in the same phase | Depth cap is a hard-coded ceiling in the search loop; curated 10-20 position validation set reviewed qualitatively before ship |
| 8. Objectively-inferior move looks broken | UI/display phase (modal-path + score pair, MVP1) | UAT/`/gsd-ui-review` with a fresh reviewer specifically probing reaction to Engine-vs-Stockfish disagreement |
| 9. Anytime flicker | Anytime-refinement UI phase (paired with #2's batching) | Manual scrub test: top-line arrow does not visibly jump more than once or twice per search |
| 10. Untestable/brittle probabilistic-engine tests | Designed alongside the core MCTS phase (#3-5) and the validation-set work (#7) | Test suite has (a) pure-function unit tests with exact assertions, (b) golden-position structural/bounds assertions, (c) a stubbed-engine determinism test — all three layers present, not just one |

## Sources

- SEED-082 (`.planning/seeds/SEED-082-human-playable-line-engine.md`) — locked design, prior-art survey, and the critical-pitfall/open-questions sections this research extends
- `.planning/PROJECT.md` — v2.0 milestone scope and locked context
- Existing codebase precedent (read directly, HIGH confidence — these are FlawChess's own already-fixed bugs and existing patterns): `frontend/src/hooks/useStockfishGradingEngine.ts` (Phase 151.1's `multipv`-vs-`pv[0]` fix, `searchmoves` illegal-move-drop mitigation, debounce/stale-guard patterns), `frontend/src/hooks/useMaiaEngine.ts` (onnxruntime-web worker lifecycle, cache, tab-hide pause)
- [Maia KDD 2020 paper — "Aligning Superhuman AI with Human Behavior: Chess as a Model System"](https://www.cs.toronto.edu/~ashton/pubs/maia-kdd2020.pdf) — MEDIUM confidence, cross-checked against 2 independent follow-on papers
- [Human-Aligned Chess With a Bit of Search (ALLIE, ICLR 2025)](https://arxiv.org/abs/2410.03893) — MEDIUM confidence, corroborates the search-vs-human-calibration tradeoff independently
- [Maia-2: A Unified Model for Human-AI Alignment in Chess (NeurIPS 2024)](https://arxiv.org/pdf/2409.20553) — MEDIUM confidence, background on skill-aware conditioning
- [lichess-org/stockfish.wasm](https://github.com/lichess-org/stockfish.wasm) and [official Stockfish UCI docs](https://official-stockfish.github.io/docs/stockfish-wiki/UCI-&-Commands.html) — MEDIUM confidence on `searchmoves`/illegal-move behavior, cross-checked against FlawChess's own Phase 151.1 real-binary spike (HIGH confidence on that specific finding)
- [onnxruntime GitHub issues #22086, #22776, #26827](https://github.com/microsoft/onnxruntime/issues/22086) — MEDIUM confidence, iOS-Safari-specific WASM/JSEP memory issues (community-reported, not officially documented limits)
- [Mobile Safari web pages are severely limited by memory (lapcatsoftware.com, 2026)](https://lapcatsoftware.com/articles/2026/1/7.html) and related [emscripten](https://github.com/emscripten-core/emscripten/issues/19374)/[WebKit](https://bugs.webkit.org/show_bug.cgi?id=221530) bug reports — MEDIUM confidence, independent third-party measurement + multiple corroborating engine bug reports, not FlawChess-device-verified
- User memory: `project_flawchess_engine_prior_art.md`, `project_headless_stockfish_wasm_verification.md`, `project_eval_nondeterminism.md`, `project_frontend_beta_gating_source.md` — HIGH confidence, direct project history

---
*Pitfalls research for: client-side MCTS practical-play chess engine (FlawChess Engine, v2.0 milestone)*
*Researched: 2026-07-05*
