---
title: Distributed user compute (users-as-Stockfish-workers) — rejected
date: 2026-06-18
context: /gsd-explore session on scaling analysis compute as the user base grows
---

# Distributed user compute — rejected

## The idea (explored, not pursued)

As more users join, self-hosted worker compute might become insufficient. Proposal:
turn **users into analysis workers**. Each user's browser runs Stockfish-WASM to analyze
games for the network; they earn **1 credit per game analyzed** and **spend credit when the
network analyzes their own games**. New users get `x` free starting credits. A
**contribution leaderboard** provides a social incentive.

## Why it was rejected

1. **Trust / verification is expensive.** Client-returned `eval_cp` / `best_move` / flaw
   tags flow straight into other users' WDL stats, flaw zones, and LLM feedback. A buggy or
   malicious client silently poisons analysis. Eval is not bit-reproducible across machines
   (see [[project_eval_nondeterminism]]), so you can't verify by exact re-run. The usual
   fixes (N-way redundancy, server-side spot-checks) claw back the very compute you set out
   to save.

2. **WASM is 3–5x slower (and needs cross-origin isolation).** Native baseline is
   ~1 position/sec/core ≈ ~60 sec/game at the 1M-node budget (Phase 116). Stockfish-WASM is
   ~1/3–1/2 native on desktop *with* SIMD+threads (~2–3 min/game), and threads require
   COOP/COEP headers site-wide (can break OAuth popups / embeds). Without them you fall back
   to ~1/5–1/10 native.

3. **Consumption/contribution asymmetry — the killer.** Consumption is bursty and huge (a
   new import = ~1,000 games demanded up front, fast). Contribution is a slow trickle
   (~1–3 games per focused browsing session). Plus free starting credits. For the median
   user the credit account is a faucet with no drain, so load still lands on servers + a
   tiny minority of "whale" contributors. The leaderboard is really just a recruitment tool
   for that minority, not a self-balancing mechanism.

4. **Unreliable SLA.** Farming a user's import to random browsers makes their results slow
   and unpredictable to materialize, versus the current predictable worker throughput.

Device mix was **not** a blocker (55% laptop / 8% desktop / 36% mobile — 64% capable,
contribution would simply be gated to capable devices).

## What we'll do instead

Scale **server-side**. The existing `eval_jobs` queue + tier-priority drain worker is
already built for horizontal scaling — the path is "more instances of the worker we already
run" on cheap CPU (Stockfish is pure CPU-bound, the cheapest thing to rent), not a new
crowd-compute system. Predictable, verifiable, SLA-able, and almost certainly cheaper than
the engineering a trust/verification layer would cost. Current state: workers run only on
Adrian's + girlfriend's personal machines; no cloud worker nodes yet.

## Worth keeping (decoupled)

The **community/leaderboard instinct was good — just attached to the wrong mechanism.** A
social layer around what users *actually* do (games analyzed, improvement streaks, biggest
flaw fixed, openings mastered) could be a real retention feature on its own, independent of
compute contribution.
