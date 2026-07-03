---
phase: quick-260703-suq
plan: 01
type: execute
wave: 1
depends_on: []
files_modified:
  - app/services/eval_drain.py
  - app/services/forcing_line_gate.py
  - tests/services/test_eval_drain.py
  - tests/services/test_full_eval_drain.py
  - tests/services/test_forcing_line_gate.py
autonomous: true
requirements: [SEED-079]
must_haves:
  truths:
    - "Tier-4 flaw-blob leases emit only even node_k (solver nodes); odd defender nodes are never leased or engine-evaluated."
    - "The assembler reconstructs a full-index blob from even-only worker results by filling odd indices with all-None placeholder PvNodes; a missing EVEN node is a gap, a missing odd node is a placeholder."
    - "The forcing-line gate produces identical credit decisions on a slim blob and its fat equivalent EXCEPT the odd-firing-depth forced-mate exemption, which conservatively degrades to non-exempt on slim blobs."
    - "The local drain (_build_flaw_multipv2_blobs) skips odd-k engine calls and stores the same placeholder scheme."
    - "Old atomic/tier-4 workers that still submit odd nodes have those odd submissions discarded at assembly (server authoritative)."
  artifacts:
    - app/services/eval_drain.py
    - app/services/forcing_line_gate.py
  key_links:
    - "_build_flaw_blob_lease_positions token emission ↔ _assemble_one_line_blob index reconstruction (must agree on even-only leasing + odd placeholders)."
    - "Placeholder defender PvNode (all-None, su='') ↔ forcing_line_gate read surface (gate must never read odd-node content except _is_forced_mate_firing at odd firing_depth)."
---

<objective>
Implement SEED-079 items 1–5 (server-side): stop paying MultiPV-2 Stockfish evals for defender (odd-index) continuation nodes in flaw-blob building, since the forcing-line gate reads only solver (even-index) nodes. This roughly halves the remaining tier-4 blob-backfill compute.

Purpose: defender-node blob content is confirmed dead weight (the 2026-07-03 defender-gate A/B rejected gating on defender nodes). Skipping their engine evals ~doubles tier-4 throughput while the backfill is still early (~14% coverage).

Output: even-only leasing, a placeholder-filling assembler, a slim-aware local drain, and a documented conservative decision on the one odd-firing-depth mate-exemption quirk. Mixed fat/slim blobs remain valid; existing 460k fat blobs are NOT rewritten.
</objective>

<execution_context>
@$HOME/.claude/gsd-core/workflows/execute-plan.md
</execution_context>

<context>
@.planning/seeds/SEED-079-slim-multipv-blobs-skip-defender-nodes.md
@app/services/eval_drain.py
@app/services/forcing_line_gate.py
@app/schemas/eval_remote.py
</context>

<constraints>
- `uv run ty check app/ tests/` must pass with zero errors.
- Run the backend suite with `uv run pytest -n auto`. Targeted: `uv run pytest -n auto tests/services/test_eval_drain.py tests/services/test_full_eval_drain.py tests/services/test_forcing_line_gate.py tests/test_eval_worker_endpoints.py`.
- No magic numbers — the even/odd node convention is `k % 2` (0 = solver, odd = defender); if a named helper reads clearer, add one, but a bare `% 2` with a clear comment is acceptable here as it is the blob's structural definition, not a tunable.
- Comment the non-obvious slim-blob invariants at each fix site (why odd nodes are skipped, why placeholders preserve gate indices).
- Do NOT change the gate's solver-node read surface (`is_solver_node_forced`, `_solver_nodes_through_firing_depth`, `_truncate_at_still_winning_floor`, `_strip_trailing_only_moves` logic). The gate must stay correct on BOTH fat and slim blobs.
- Do NOT rewrite existing fat blobs. Do NOT add a DB migration.
</constraints>

<shared_design>
Blob index convention (already load-bearing in forcing_line_gate.py): a PV line starts at a solver ply, so **even indices = solver nodes, odd indices = defender nodes**. The gate reads only even nodes (one exception: `_is_forced_mate_firing` reads `line[firing_depth]`, which can be odd).

Slim scheme: lease/evaluate only even node_k; reconstruct a full-length blob at assembly by inserting an all-None placeholder PvNode at each skipped odd index so the stored list keeps its original indices and length. A placeholder is `PvNode(b=None, bm=None, s=None, sm=None, su="")` (su must be str, never None — Pitfall 3).

Add ONE shared helper in eval_drain.py, e.g. `_placeholder_defender_node() -> PvNode`, and reuse it in both assembly paths (tier-4 `_assemble_one_line_blob` and local-drain `_build_line_blobs`).

Assembler gap semantics (both paths): walk even k = 0, 2, 4, …; for each present even node, first append the placeholder for the preceding odd index (only when k > 0), then append the real node; STOP at the first missing even node. Result therefore always ends on a real even solver node (never a trailing placeholder), preserving `_strip_trailing_only_moves`' "last solver node is real" assumption.
</shared_design>

<tasks>

<task type="auto" tdd="true">
  <name>Task 1: Even-only tier-4 leasing + placeholder-filling assembler (SEED-079 items 1, 2, 5)</name>
  <files>app/services/eval_drain.py, tests/services/test_eval_drain.py</files>
  <behavior>
    - _build_flaw_blob_lease_positions: for a walkable line (walk length >= 2), emits FlawBlobLeasePosition tokens ONLY for even node_k (0, 2, 4, …). A 3-board walk (indices 0,1,2) yields 2 lease positions (k=0, k=2), not 3. The `len(walk) < 2` sentinel behavior is unchanged.
    - _assemble_one_line_blob: given only even-k worker results for a line, returns a full-index blob: [node0, placeholder1, node2, placeholder3, node4, …] where placeholders are all-None PvNodes. A missing node0 still returns []. A present node0 with a missing node2 returns [node0] (one solver node). A missing odd node in node_results is NOT a gap.
    - Atomic/tier-4 storage-only guard (item 5): worker results at ODD tokens present in node_results are ignored (never read) — the assembler only reads even k and synthesizes odd placeholders, so old workers still sending odd nodes are discarded at assembly. Assert this with a node_results dict that includes an odd-k entry and verify the assembled odd index is the placeholder, not the worker value.
    - Resulting slim blob, passed through apply_forcing_line_filter, yields the SAME credit decision as the equivalent fat blob for a standard even-firing-depth tactic.
  </behavior>
  <action>
In app/services/eval_drain.py:

1. Add a module-level helper `_placeholder_defender_node() -> PvNode` returning `PvNode(b=None, bm=None, s=None, sm=None, su="")`, documented as the slim-blob odd-index placeholder that keeps solver-node indices aligned for the gate (SEED-079).

2. In `_build_flaw_blob_lease_positions`, change the token-emission loop (currently `for k, walk_board in enumerate(walk)`) to emit only even indices — iterate `range(0, len(walk), 2)` and index `walk[k]`. Keep the `len(walk) < 2` sentinel check and everything else. Add a comment: only solver (even) nodes are gate-read (D-10), so defender (odd) nodes are never leased — SEED-079 halves the tier-4 continuation-eval compute.

3. Rewrite `_assemble_one_line_blob`'s node walk to the slim placeholder scheme (see <shared_design>): keep the sentinel-line and missing-node0 early-returns; then walk even k in steps of 2, inserting `_placeholder_defender_node()` for the preceding odd index before each real node (except before node0), and BREAK on the first missing even node. Comment that odd node_results entries (if any old worker sent them) are intentionally never read — server-authoritative discard (SEED-079 item 5). This single change covers BOTH the tier-4 submit path and the atomic-submit path (both route through `_assemble_flaw_blobs_from_submit` → `_assemble_one_line_blob`).

Do NOT place fenced code in comments. Keep helper small.
  </action>
  <verify>
    <automated>uv run pytest -n auto tests/services/test_eval_drain.py -x</automated>
  </verify>
  <done>Leases emit even-only tokens; assembler reconstructs full-index blobs with all-None odd placeholders; missing even node = gap, missing/extra odd node = placeholder/discarded; slim blob gate decision matches fat for even-firing tactics. New/updated unit tests pass; ty clean.</done>
</task>

<task type="auto" tdd="true">
  <name>Task 2: Slim local drain — skip odd-k engine calls (SEED-079 item 4)</name>
  <files>app/services/eval_drain.py, tests/services/test_eval_drain.py, tests/services/test_full_eval_drain.py</files>
  <behavior>
    - _build_flaw_multipv2_blobs: for a flaw line whose PV walk has boards at indices 0..N, the continuation gather now includes ONLY even indices >= 2 (2, 4, …) — odd (defender) boards are never handed to engine_service.evaluate_nodes_multipv2. For a walk of length 5 (indices 0..4) the gather contributes 2 boards for that line (k=2, k=4), not 4.
    - _build_line_blobs: node 0 still comes from pos_eval + second_best_map; even continuation nodes (2, 4, …) come from node_eval; odd indices are filled with `_placeholder_defender_node()`; the list ends on a real even solver node; a missing even node_eval entry stops the walk.
    - A full local drain tick over a game with a clear blunder still produces allowed/missed blobs whose even (solver) nodes carry real evals and whose odd nodes are placeholders, and those blobs still gate identically to the pre-change (fat) result for an even-firing tactic.
  </behavior>
  <action>
In app/services/eval_drain.py:

1. In `_build_flaw_multipv2_blobs`, change BOTH continuation-gather loops (the "missed" loop around `for k, b in enumerate(missed_walk[1:], 1)` and the "allowed" loop) to enqueue only even indices >= 2: iterate `range(2, len(walk), 2)` and append `walk[k]` with `gather_keys.append((flaw_ply, line, k))`. Node 0 is not gathered (comes from pos_eval); odd defender nodes are skipped. Comment: SEED-079 — gate reads only solver (even) nodes, so defender continuation evals are dead weight.

2. Rewrite `_build_line_blobs`'s continuation loop (currently `for k in range(1, len(walk))` reading node_eval and breaking on None) to the slim scheme: keep the node0 assembly (pos_eval + second_best_map) unchanged; then walk even k from 2 in steps of 2 while k < len(walk), and for each present node_eval entry append `_placeholder_defender_node()` (the preceding odd index) then the real node; BREAK on the first missing even node_eval. Reuse the same `su_k`/None→"" handling for the real even nodes.

Ensure the placeholder helper from Task 1 is reused (no second definition).
  </action>
  <verify>
    <automated>uv run pytest -n auto tests/services/test_eval_drain.py tests/services/test_full_eval_drain.py -x</automated>
  </verify>
  <done>Local drain gathers only even continuation boards; _build_line_blobs emits placeholder odd nodes and real even nodes; drain-tick blobs gate identically to fat for even-firing tactics. Tests updated/added; ty clean.</done>
</task>

<task type="auto">
  <name>Task 3: Odd-firing-depth mate exemption — conservative acceptance + gate tests (SEED-079 item 3)</name>
  <files>app/services/forcing_line_gate.py, tests/services/test_forcing_line_gate.py</files>
  <behavior>
    - Decision (per seed: "prefer the minimal conservative option unless normalization is trivially safe"): ACCEPT CONSERVATIVELY. Normalizing an odd firing_depth to an adjacent even index would read a DIFFERENT node's mate value and would change credit decisions on the existing 460k fat blobs — that is not trivially safe and would touch the gate read surface (a non-goal). So NO gate logic change.
    - On a slim blob whose firing node lands at an odd index (placeholder defender node, bm=None), `_is_forced_mate_firing` returns False → the forced-mate exemption from D-08/D-10 is lost for that ~5% of gated tags (mainly DISCOVERED_ATTACK depth 1, WR-02 k-1 quirk). This is an accepted, conservative degradation, not a bug.
    - Fat blobs are UNAFFECTED: their odd nodes still carry real data, so `_is_forced_mate_firing` still works on them exactly as before.
    - A slim blob whose firing node is at an EVEN index (a real solver node delivering a forced mate) still gets the exemption (returns True).
    - Mixed fat/slim: the gate yields correct credit decisions on both blob shapes for standard even-firing tactics.
  </behavior>
  <action>
In app/services/forcing_line_gate.py, add a short comment block on `_is_forced_mate_firing` (docstring or inline) documenting the SEED-079 accepted degradation: with slim blobs (all-None placeholder defender nodes), an odd firing_depth reads a placeholder → bm is None → returns False, conservatively losing the forced-mate exemption for the WR-02 k-1 odd-depth motifs. Explain WHY we do NOT normalize (would read a different node and change fat-blob outcomes / touch the gate read surface — both non-goals). NO logic change.

In tests/services/test_forcing_line_gate.py, add tests covering:
  - `_is_forced_mate_firing` returns False for a slim blob where firing_depth is odd and line[odd] is a placeholder (all-None) node (accepted degradation).
  - `_is_forced_mate_firing` returns True for a slim blob where firing_depth is even and the even firing node is a solver forced mate.
  - `apply_forcing_line_filter` returns the SAME result for a fat blob and its slim equivalent (real even nodes, placeholder odd nodes) for a standard even-firing forced tactic (mixed fat/slim correctness).
  - Regression: a fat blob with a real defender firing node at an odd depth still gets its mate exemption (unchanged behavior).

Do NOT place fenced code in the docstring/comment.
  </action>
  <verify>
    <automated>uv run pytest -n auto tests/services/test_forcing_line_gate.py -x</automated>
  </verify>
  <done>forcing_line_gate.py documents the conservative odd-firing acceptance (no logic change); gate tests prove slim odd-firing degrades to non-exempt, slim even-firing stays exempt, fat blobs unchanged, and mixed fat/slim gate decisions match for even-firing tactics. ty clean.</done>
</task>

</tasks>

<verification>
Full targeted suite plus the pre-merge type gate:

```bash
uv run ty check app/ tests/
uv run pytest -n auto tests/services/test_eval_drain.py tests/services/test_full_eval_drain.py tests/services/test_forcing_line_gate.py tests/test_eval_worker_endpoints.py
```

Also confirm no endpoint test hard-codes a defender-inclusive node count (grep `test_eval_worker_endpoints.py` for lease-length asserts; existing ones use `len(positions) > 0`, which stays valid). Then run the whole backend suite once: `uv run pytest -n auto -x`.
</verification>

<success_criteria>
- Tier-4 leases and the local drain no longer emit or engine-evaluate odd (defender) continuation nodes.
- The assembler reconstructs full-index blobs with all-None odd placeholders; even-node gap semantics correct.
- Old workers' odd-node submissions are discarded at assembly (server-authoritative).
- The forcing-line gate is correct on BOTH fat and slim blobs for even-firing tactics; the odd-firing-depth mate exemption degrades conservatively (documented) and fat blobs are unaffected.
- `uv run ty check app/ tests/` passes; the full backend suite passes with `-n auto`.
- No DB migration; no rewrite of existing fat blobs.
</success_criteria>

<output>
Create `.planning/quick/260703-suq-slim-multipv-blobs-skip-defender-node-en/260703-suq-SUMMARY.md` when done.
</output>
