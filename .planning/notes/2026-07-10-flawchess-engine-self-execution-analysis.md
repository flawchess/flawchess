---
date: "2026-07-10 16:10"
promoted: false
---

# FlawChess Engine: why it prefers Rxd1 over the only-equalizing Qxh2+ perpetual

**Case**: game 687537, ply 46 (`/analysis?game_id=687537&ply=46`), FEN
`3r2k1/1pb2ppp/p2r3q/8/1PB5/2P2Q2/PB3PPP/3R1RK1 b - - 3 24`, engine at 2600/2600 ELO,
Stockfish playstyle (T=2.0). Objective truth (Stockfish depth 20): Qxh2+ = 0.00 (queen-sac
perpetual: Qxh2+ Kxh2 Rh6+ Kg1 Bh2+ Kh1 Bg3+ Kg1 …), Rxd1 = −3.9 for black. The engine
suggests Rxd1.

**Verdict: this is the engine working as designed (a feature), not a bug.** The sign frame,
truncation, findability ranking, and backup rule were all verified correct. The behavior
follows from the milestone's deliberate self-execution-probability modeling (SEED-082 hook):
the engine maximizes practical expected score *given that you, too, are a fallible Maia-2600
after the root move*.

## Verification method

- Reproduced Maia-3 inference headlessly: Python + `onnxruntime==1.20.1` (1.22+ segfaults on
  the vendored model), encoding replicated from `public/maia/maia-worker.js` +
  `maiaEncoding.ts` (mirror-on-black, 12-plane, vocab 4352, raw ELO floats). Root
  distribution matched the UI to 0.01% (Qxh2+ 45.24%, Rxd1 41.84%) — encoding validated.
- Leaf grades from the vendored WASM Stockfish (`public/engine/stockfish-18-lite-single.js`
  in Node) at the engine's real grading depth (`GRADING_TARGET_DEPTH = 14`, MultiPV
  searchmoves, white-POV keying) — depth 14 sees the perpetual (0.00) at every node in the
  line, so repetition-blindness of `terminalValue` (FEN-only, no history) is NOT the cause.
- Hand-rolled the exact pipeline: `applyPolicyTemperature` → `truncateAndRenormalize` (0.9
  mass) → `backupExpectation` (prior-weighted), leaf = lichess sigmoid of white-POV cp.

## Mechanism (quantified)

At 2600 both root moves saturate the findability factor (pRef = 0.005), so ranking is purely
by practical score V.

**V(Qxh2+) ≈ 0.24.** After Qxh2+ Kxh2 (only legal reply, prior 1), Maia-2600 — asked cold,
with no move history — gives the required follow-up Rh6+ only **28% raw / 31% post-truncation**,
vs **56% for the losing Rxd1+** (down a queen, +5.35 white-POV → leaf 0.12). The simplified
Maia-3 export has n=0 history planes, so it cannot condition on "you just sacked the queen
intending this exact perpetual"; it models a random 2600 teleported into the position.
V = 0.31·0.5 + 0.69·~0.12 ≈ 0.24. Deeper perpetual nodes are near-forced (Bh2+ 98.9%; the
final node's candidates are all drawing discovered checks) — the discount happens at this
single node. Break-even follow-up probability for the sac to outrank Rxd1: **~49%**.

**V(Rxd1) ≈ 0.31 — and it is NOT swindle value.** After 24...Rxd1, Maia-2600 white plays the
refutation Qxf7+ with 72% prior (Bxf7+ 11%, g3 9%); the losing recapture Rxd1?? gets 7% and
is **truncated out of the tree entirely** by the 0.9-mass cut. V = 0.78·0.21 + 0.12·0.65 +
0.10·0.64 ≈ 0.31. So Rxd1 wins as "probably refuted but survivable" vs "probably unexecuted
forced draw" — consistent with the homepage claim (opponent modeling, not swindles).

## Why the playstyle slider can't express "assume I execute"

Temperature reshapes the root player's policy at ALL self nodes (`sideMatchesMover` in
`dispatchExpansion`), not just the root:

| Playstyle | P(Rh6+) after pipeline | V(Qxh2+) |
|---|---|---|
| T=1 (center) | 0.31 (3 candidates kept) | 0.238 |
| T=2.0 (full Stockfish) | 0.23 (16 candidates kept — junk dilution) | 0.213 |
| T=0.5 (full Human) | 0.20 (sharpens onto wrong modal move Rxd1+) | 0.199 |

Both slider ends make the sac look *worse* than the default. The knob was designed for
root-surfacing (flatten → rare strong moves clear truncation), and Qxh2+ does surface — it
just loses the V ranking.

## If this ever becomes a product priority

The fix would live in self-node execution modeling, not temperature: e.g. blend self-node
priors toward the best-*graded* move as playstyle → Stockfish, or switch self nodes from
expectation to max-backup at the Stockfish end. The principled cure (conditioning Maia on
preceding moves) requires a history-aware model (Maia-2 style dual-skill attention); the
vendored simplified Maia-3 cannot do it. For now: accepted design behavior — the engine
distrusts your hands, not banks on your opponent's blunders. A UI hint could someday explain
low practical scores on objectively-best sac lines ("requires follow-up precision Maia rates
at 28%").

Related memory: `project_engine_self_execution_sac_blindness` (auto-memory dir).
