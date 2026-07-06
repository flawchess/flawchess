# The FlawChess Engine: MCTS-Based Expectimax, Explained

**Date:** 2026-07-06
**Scope:** the pure search core in `frontend/src/lib/engine/` delivered by Phase 153 (requirements ENGINE-01..07).
**Audience:** a developer who knows chess and TypeScript but has not built a game-tree search before. Complicated ideas (expectimax, MCTS, PUCT, the sigmoid) are explained from scratch.
**Purpose:** a durable reference for *what this engine does and why it's built the way it is*. This is an explanatory document, not a defect review.

Files covered: `types.ts`, `guardrail.ts`, `leafScore.ts`, `backup.ts`, `select.ts`, `mctsSearch.ts`, `fallbackExpectimax.ts`.

---

## 1. What problem this engine solves

Ordinary chess engines (Stockfish, Leela) answer one question: **what is the objectively best move, assuming both sides play perfectly from here on?** That is exactly the wrong question for a human improvement tool. A 1400-rated player is not going to find the only-move that holds a position, and their opponent is not going to defend like a 3500-rated engine.

The FlawChess Engine answers a different question:

> **What is the best move *you can actually pull off*, against an opponent who defends the way real players at their level actually defend?**

Two examples of where this diverges from Stockfish:

- A line that is objectively winning but requires a sequence of quiet only-moves that almost nobody at your level finds. Stockfish loves it. This engine discounts it, because *you* probably won't execute it.
- A move that is objectively second-best, but sets a trap the opponent walks into 60% of the time. Stockfish ignores it. This engine can rank it **above** the "best" move, because in expectation it scores more points for you. This trap/swindle finding is the engine's signature feature.

The output is a single number per candidate move: an **expected practical score** between 0 and 1 (think "expected fraction of a point" — 1 = you win, 0.5 = draw, 0 = you lose), from your point of view. The UI can later show both numbers side by side: "objectively +3.0, but practically +0.9 for you."

This is a client-side TypeScript engine — no server round-trip, no Web Workers *in this phase*. Phase 153 built and unit-tested the pure search logic in isolation; real Stockfish/Maia providers and the UI arrive in later phases.

---

## 2. The two "brains" the engine borrows

The engine does not evaluate positions itself. It orchestrates two existing models, each doing what it is good at. In the code these are the two methods of the `EngineProviders` interface (`types.ts:26`):

**Stockfish — the quality axis (`grade`).** Given a position and a list of candidate moves, Stockfish returns a shallow evaluation of each ("this move leaves you +1.2 pawns", "this one is dead lost"). This is the *objective* truth about the position. In this phase `grade` is a fake provider in tests; in Phase 154 it becomes a pool of Stockfish workers.

**Maia — the probability axis (`policy`).** Maia is a neural network trained on millions of human games *at specific rating levels*. Given a position and a rating, it returns a **probability distribution over moves**: "at 1400, players play Nf3 here 45% of the time, Bc4 25%, ..." This is the *human behavior* model. It is what lets the engine reason about what a real player would actually do.

The crucial design move: the engine queries Maia **asymmetrically**. When it is *your* turn deep in a line, it asks Maia "what would a player at *your* rating do?" When it is the *opponent's* turn, it asks "what would a player at *their* rating do?" This is why the budget carries two ratings, not one — `elo: { w: number; b: number }` (`types.ts:38`). Modeling *your own future self honestly* is what prices in "can I actually follow this line, or will I go wrong at move 3?"

---

## 3. The core idea in one sentence

> **Expectimax semantics living inside MCTS budget allocation. The root is a `max` node; every other node is a Maia-probability-weighted average.**

That sentence contains two separate ideas. Let's unpack each, because they are the whole design.

### 3a. Expectimax: max where you choose, average where you can't be sure

A normal chess engine uses **minimax**: I pick my best move, then I assume my opponent picks *their* best move (worst for me), and so on. Both sides are treated as perfect maximizers.

**Expectimax** replaces "the opponent plays their best move" with "the opponent plays a *probability distribution* of moves, so the value of this position is the *weighted average* over what they might do." It is the standard technique for games against a non-perfect, probabilistic opponent.

This engine applies expectimax to **both** sides below the root:

- **Opponent to move:** value = the average of the resulting positions, weighted by how likely the opponent is to play each move (their Maia distribution). If a move loses for them but they only find it 10% of the time, it only drags the average down by 10% of its badness.
- **You to move (below the root):** *also* a weighted average, under *your* Maia distribution. This is the subtle, honest part. Below the root you don't get to assume you'll find the best move — you model yourself as the fallible human you are. A brilliant continuation you'd find 8% of the time contributes 8% of its brilliance plus 92% of whatever you'd more likely play instead.
- **The root — and only the root — is a `max`.** This is the one place you *are* choosing deliberately, right now, with the engine's help. So here the engine takes the best candidate rather than averaging. "The tree has exactly one max node: the root."

This asymmetry (root = max, everything else = expectation) is unusual and is the genuinely novel piece. It is isolated into one tiny file, `backup.ts`, on purpose (see §5).

### 3b. MCTS: spend your limited evaluations where they matter

Why not just build the full tree to depth 8 and average everything up? **Cost.** Each Stockfish evaluation takes 50–300ms. A few seconds of budget buys only a few hundred evaluations total. A uniform depth-8 tree would blow the entire budget on lines that were already dead at move 2.

**Monte Carlo Tree Search (MCTS)** is a budgeting strategy. Instead of expanding everything uniformly, it grows the tree *adaptively*: it repeatedly walks from the root down to a promising leaf, expands that one leaf, and propagates the result back up. Promising lines get explored 10+ moves deep; junk gets abandoned after one look. Same budget, far better use of it.

Each "walk down, expand one leaf, propagate back up" is one iteration. The engine calls one expansion **one node** (`maxNodes` in the budget counts these), because one expansion = exactly one `policy()` call plus one batched `grade()` call, which is the real cost driver.

So the design is: **use MCTS's smart budget allocation, but replace its usual averaging rule with our custom expectimax rule.** That swap is the whole trick.

---

## 4. The pieces, and how they fit together

The core is seven small files. Read them in this order:

| File | Role | Analogy |
|---|---|---|
| `types.ts` | The frozen data contract (inputs, outputs, provider interface) | The shape of every message |
| `guardrail.ts` | The one function signature both runners implement | The wall socket both plugs fit |
| `leafScore.ts` | Turns a Stockfish eval into an expected score (0–1) | The unit converter |
| `backup.ts` | The novel rule: max at root, weighted average elsewhere | The engine's "physics" |
| `select.ts` | Decides which branch to walk down next | The steering wheel |
| `mctsSearch.ts` | The main loop that ties it all together | The driver |
| `fallbackExpectimax.ts` | A simpler backup engine behind the same signature | The spare tyre |

The philosophy is **small, single-purpose files** so the two genuinely tricky ideas (the backup rule and the rating routing) can each be proven correct with hand-computed test fixtures *before* any real Stockfish or Maia exists. The tests feed the search fake providers with known numbers and check the arithmetic by hand.

### The frozen contract (`guardrail.ts`, `types.ts`)

Everything the search does is expressed through one function signature, `SearchRunner` (`guardrail.ts:13`):

```
(rootFen, budget, providers, onSnapshot, signal) => Promise<EngineSnapshot>
```

- `rootFen` — the position to analyze.
- `budget` — how hard to search: `maxNodes` (how many expansions), `maxPlies` (how deep, locked to a 6–10 half-move band), `elo: {w, b}` (the two ratings), `concurrency` (how many evaluations in flight at once), and optional `extraRootMoves` (see below).
- `providers` — the Stockfish (`grade`) and Maia (`policy`) hooks.
- `onSnapshot` — a callback fired after **every** completed expansion, so the UI can update live ("anytime" refinement). The search emits a full ranked result each tick; throttling to ~10Hz is the caller's job, not the engine's.
- `signal` — an `AbortSignal` to cancel mid-search (e.g. the user moved on).
- Returns an `EngineSnapshot`: the ranked candidate moves, how many nodes were evaluated, and whether the budget ran out.

This signature is **frozen**. Two completely different engines implement it identically (§7), and all downstream phases build against it unchanged. That is the "guardrail" the filename refers to: if MCTS tuning ever becomes a rabbit hole, the simpler fallback engine can be swapped in behind the exact same socket with zero changes elsewhere.

One notable field: `extraRootMoves`. Maia might assign a strong Stockfish move a near-zero human probability, which would normally get it dropped before it's ever looked at. `extraRootMoves` lets the caller force specific moves (e.g. Stockfish's top lines) into the root candidate set so they're always evaluated, even if humans rarely play them. Phase 155 will feed the live Stockfish engine's best moves in here.

### The unit converter (`leafScore.ts`)

At the bottom of the tree (a "leaf"), the engine stops searching and needs a number. Stockfish gives a pawn evaluation ("+1.5") or a mate score ("mate in 3"). The engine needs an **expected score** in 0–1.

`leafExpectedScore` (`leafScore.ts:26`) does this conversion using the well-established **lichess win-probability sigmoid** — the same S-shaped curve that maps "+1.5 pawns" to "≈70% expected score" everywhere else in FlawChess (`evalToExpectedScore` in `liveFlaw.ts`). No new math was invented here; it reuses the existing formula verbatim.

This file also carries the single **subtlest correctness detail in the whole phase**, explained fully in §6.

### The novel rule (`backup.ts`)

This is the smallest file and the most important. "Backing up" means: after expanding a node, recompute its value from its children's values, then push that up to its parent, and so on to the root. `backup.ts` defines *how* a node combines its children:

- `backupExpectation` (`backup.ts:43`) — **non-root nodes.** The Maia-probability-weighted average of the children's values: `Σ (prior_i × value_i)`. Each `prior` is the child's Maia probability; each `value` is either the child's own backed-up value (if it's been expanded) or its leaf estimate (if not). No probability mass is ever dropped — expanded and unexpanded children are mixed in the same average.
- `backupRootMax` (`backup.ts:54`) — **the root only.** The plain maximum of the children's values. The root picks the best; it never averages.

The file is deliberately tiny and pure (just arithmetic over arrays, no I/O). The reason is a documented trap: it would be very easy for this custom expectimax rule to *silently* degenerate back into textbook MCTS, which weights children by **visit count** instead of by Maia probability. To make that mistake impossible to hide, the `BackupChild` type has an explicit `prior` field supplied independently, and the word `visits` appears **nowhere** in the file. A reviewer can confirm at a glance that the weighting can never come from visit counts. That structural guarantee is the whole point of isolating this into its own file.

### The steering wheel (`select.ts`)

Every MCTS iteration has to answer: *from the root, which branch do I walk down to find the next leaf worth expanding?* You want to balance:

- **Exploitation** — go where results already look good.
- **Exploration** — try branches you haven't looked at much yet, in case they're better.

The standard formula for this balance is **PUCT** (Predictor + Upper Confidence bound for Trees). Intuitively, each child gets a score = *how good it looks so far* + *a bonus for being under-explored*, where the bonus is bigger for children with a high prior probability and fewer visits. `selectChild` (`select.ts:109`) implements this with the engine's deliberate twist:

- **At the root:** the full formula, `Q(child) + c_puct · P(child) · √N / (1 + n(child))`. `Q` is how good the child looks, the rest is the exploration bonus. `c_puct` (set to 1.4) tunes how adventurous the search is.
- **At every other node:** the `Q` term is **dropped** — selection is driven purely by the prior-weighted exploration term. Why? Because below the root, the node's *value* is a fixed expectation, not something you're choosing to maximize. There's no "best child to commit to" down there; you just want to keep refining whichever move *dominates the expectation* (highest probability × uncertainty). Descent naturally deepens the most-likely line.

Two more subtleties live here:

- **Truncation (`truncateAndRenormalize`, `select.ts:44`).** Maia returns a probability for *every* legal move, but the long tail of near-zero moves isn't worth searching. The engine keeps the top moves until their cumulative probability reaches 90% (`POLICY_MASS_THRESHOLD`), drops the rest, and rescales the survivors to sum to 1. This keeps the branching factor at a manageable 3–5 moves per node. This threshold is deliberately *separate* from the 95% used for chart display elsewhere — search breadth and display are different concerns.
- **The root exploration floor (`rootExplorationPriors`, `select.ts:65`).** Recall `extraRootMoves` can inject a strong-but-rare Stockfish move. If that move has ~0 Maia probability, PUCT would never give it any exploration visits, so its score would stay a single shallow guess. The fix: at the root *only*, and for the *exploration term only*, floor every prior at 0.10 before use. This guarantees injected moves get looked at. Critically, this floored prior is used **only** to decide where to spend visits — it never touches the actual value math in `backup.ts`, which always uses the true Maia probabilities. So visit allocation is nudged, but scores are never distorted.

---

## 5. The main loop, step by step (`mctsSearch.ts`)

`mctsSearch` is the primary engine. Its loop (`mctsSearch.ts:349`) repeats until the node budget runs out or the search is aborted. Each iteration:

1. **Select** (`selectPath`, `mctsSearch.ts:182`). Walk from the root down through the tree, using `selectChild` at each level, until you reach a leaf that hasn't been expanded yet. This is the "promising path."
2. **Terminal check.** If the leaf is checkmate, stalemate, or a draw, it gets a fixed value (see §6) and is never expanded — it's a dead end. Same if it hit the depth ceiling (`maxPlies`). Dead ends cost no provider calls; they just get a visit bump. (This is why `nodesEvaluated` only counts *real* expansions.)
3. **Expand** (`dispatchExpansion`, `mctsSearch.ts:324`). For a genuine leaf: call Maia (`policy`) to get the candidate moves, truncate to the top ~90%, (at the root) union in any `extraRootMoves`, then make **one batched Stockfish call** (`grade`) over all those candidates. Create a child node for each candidate, its initial value being its leaf estimate.
4. **Backup** (`applyExpansion` → `recomputeValue`, `mctsSearch.ts:225`). Recompute the leaf's value from its new children using `backup.ts`'s rule, then walk back up the path recomputing every ancestor. The root's value is now a slightly better estimate than before.
5. **Snapshot.** Emit the current ranked candidates via `onSnapshot`, so the UI refreshes live.

When the loop ends, `buildRankedLines` (`mctsSearch.ts:293`) produces the final output: each root candidate move, its practical score, its objective Stockfish eval, its **modal path** (the most-likely continuation — your probable moves plus the opponent's most probable replies, for display as "the line"), and its visit count. Results are sorted by practical score, with ties broken by alphabetical UCI move string so the output is perfectly reproducible.

### Concurrency, done carefully

Real Stockfish evaluation is slow, so Phase 154 will run 2–4 workers in parallel. The loop is already built for that: it can select up to `concurrency` leaves in one round and dispatch their expansions together. This introduces a classic hazard — if two evaluations finish in a different order than they started, the tree could end up in a different state on different runs, breaking reproducibility. Two mechanisms prevent that:

- **Pending markers.** When a leaf is selected for expansion this round, it's flagged `isPending`, and `selectPath` skips pending nodes. That stops a second selection in the same round from re-picking the same leaf.
- **Apply in dispatch order, not arrival order.** Results are collected with `Promise.all` (which preserves input order regardless of which finishes first) and applied to the tree strictly in the order they were dispatched. Visit counts are also incremented at *apply* time, not *dispatch* time, so intermediate snapshots don't depend on how many expansions happened to be batched together.

The payoff (ENGINE-07): the entire *sequence* of snapshots is bit-for-bit identical across runs, and identical whether you run at concurrency 1 or concurrency 2 (given ordered providers). The determinism test asserts not just the final answer but every intermediate tick.

---

## 6. The two traps that get the most attention

Two correctness bugs would be *silent* — the engine would still produce plausible-looking numbers, just wrong ones. Both are structurally prevented, and each has its own dedicated fixture test.

### Trap 1: the sign-flip (the "root-relative frame")

Textbook chess search (negamax) flips the sign of the evaluation at every ply, because "good for White" is "bad for Black" and the side to move alternates. This engine's backup formula (`backup.ts`) has **no sign-flip term** — it's a plain weighted average of numbers that are all supposed to already be in the *same* reference frame: **the root player's point of view**, held fixed for the entire search.

That means every leaf value must be converted to *the root player's* expected score, using the root player's color — **never the leaf's own side to move.** `rootMover` is computed exactly once from the root position (`sideToMoveFromFen(rootFen)`) and threaded as a constant into every `leafExpectedScore` call. If someone "helpfully" recomputed the mover per node, the sign would flip every ply and quietly corrupt the whole search. `leafScore.ts`'s header calls this out as "the single subtlest correctness detail in the phase," and there is a fixture test that pins it.

Terminal positions follow the same frame: `terminalValue` (`mctsSearch.ts:92`) returns 1.0 when the *root player* delivered checkmate, 0.0 when the root player got mated, 0.5 for any draw — all from the root player's perspective, never the leaf's.

### Trap 2: rating inversion (asymmetric ELO routing)

Recall the engine must query Maia at *your* rating on your moves and the *opponent's* rating on theirs. The obvious-but-wrong way to decide "whose move is this" would be depth parity — "even plies are me, odd plies are the opponent." That breaks the instant the analyzed position has Black to move, or off-by-one bugs creep in.

The engine instead reads the side to move **directly from each node's own FEN** (`fenSide`, `mctsSearch.ts:82`) and looks up the rating by color: `budget.elo[node.side]`. Because color comes straight from the position and the budget is keyed by color (`{w, b}`), the routing is *structural* — there's no arithmetic to get wrong. The mapping from "your rating / opponent's rating" to "white / black" is resolved once, later, in the Phase 155 hook where the user's color is known. The ENGINE-04 test asserts the exact `(position, rating)` pairs for both root colors.

---

## 7. The spare tyre (`fallbackExpectimax.ts`)

`fallbackExpectimax` is a **second, completely separate engine** that implements the identical `SearchRunner` signature. It is not MCTS at all — it is a plain depth-limited expectimax: it expands *every* candidate of *every* node down to `maxPlies`, with no PUCT, no visit counts, no budget-directed selection, no concurrency. Simpler, more predictable, but it wastes evaluations on doomed lines.

Its reason to exist is twofold:

1. **Insurance.** SEED-082 explicitly flagged that MCTS tuning could become a time sink. If it does, this simpler engine is a proven, drop-in replacement behind the same socket — "recoverable in a day."
2. **A living proof that the interface is real.** Because both engines reuse the *same* correctness-critical primitives — `backup.ts` (the max/expectation rule), `leafScore.ts` (the root-relative conversion), `truncateAndRenormalize` (the same 90% Maia cut) — their `practicalScore` semantics **cannot silently drift apart**. The phase includes a "swap-in" test proving one can replace the other. That shared-primitive discipline is what makes the frozen interface trustworthy rather than aspirational.

Because it's purely sequential (no parallel dispatch), the fallback is trivially reproducible with no ordering concerns at all.

---

## 8. What is deliberately *not* here

Scope discipline is part of the design. The following were consciously left out of this phase (some deferred to later phases, some indefinitely):

- **No real Stockfish or Maia.** This phase is pure logic tested against fabricated providers. Real WASM Stockfish workers arrive in Phase 154; the UI in Phase 155.
- **No transposition/Zobrist caching.** Positions diverge too fast in a shallow practical-play tree for a cache to pay off; Stockfish's own internal table gives partial reuse for free.
- **No per-rating leaf sigmoid.** For now every leaf converts via the one global lichess curve, so *beyond* the search horizon everyone is modeled as an average lichess player. Within the horizon, realism comes from the explicit Maia modeling. Per-rating calibrated sigmoids are a documented future upgrade.
- **No time-pressure conditioning.** Modeling bullet scrambles (query Maia at a reduced effective rating, flatten the distribution) is designed but deferred.
- **No "best move" framing.** Output is always "best *practical* move for you," never unqualified "best move." Disagreement with Stockfish is intentional and the UI must make it read as intentional.

A known, accepted limitation worth stating plainly: **Maia's move predictions get less reliable the deeper you search.** Every Maia probability has estimation error, and multiplying those probabilities along a deep line compounds the error — while simultaneously, deep positions look less and less like the real human games Maia was trained on. This is precisely why the search is deliberately kept shallow (6–10 half-moves) and the leaf sigmoid is trusted to absorb everything beyond the horizon. Don't trust an impressive-looking depth-16 "practical" line; the design intentionally won't produce one.

---

## 9. One-paragraph summary

The FlawChess Engine is a client-side search that ranks chess moves by **expected practical score** — how well a move actually does for *you*, given that you and your opponent both play like real humans at your respective ratings, not like perfect engines. It borrows Stockfish for objective position quality and Maia for human move-probability, and combines them with **expectimax** (the root is a `max` where you choose deliberately; every deeper node is a Maia-probability-weighted average that honestly prices in fallibility on both sides) run inside an **MCTS** budget allocator (which spends its scarce, expensive evaluations on the promising lines instead of uniformly). The novel, highest-risk rule lives in one tiny arithmetic file (`backup.ts`) so it can't silently drift into textbook MCTS; two subtle correctness traps (a per-ply sign flip and rating-by-parity inversion) are prevented *structurally* rather than by convention and each has a dedicated fixture test; and a simpler depth-limited fallback engine sits behind the identical frozen interface as both insurance and living proof that the contract is real. The result: a search that can rank an objectively second-best move first when it sets a trap the opponent walks into — the feature no conventional engine gives you.
