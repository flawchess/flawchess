/**
 * policyTemperature — Maia policy-temperature transform (Phase 159 D-06/D-07,
 * Thread A of SEED-085): reshapes an already-softmaxed move-probability
 * distribution as if the temperature had been applied before the softmax:
 * `p_i^(1/T)` renormalized. T>1 flattens the distribution (mass bleeds onto
 * the rarer moves); T<1 sharpens it toward the top move. The user-facing
 * polarity is the OPPOSITE of the naive reading, because Maia's peak is the
 * most *human* move, not the objectively best one: sharpening (T<1) is the
 * "Human" end (the engine leans on the single most human-likely move, and
 * findability demotes rare-but-strong moves harder), while flattening (T>1) is
 * the "Stockfish" end (rare-but-strong moves gain enough weight to clear
 * findability and surface in the ranking). Do NOT re-label T<1 as
 * "Stockfish-like" — that inverted assumption was the original bug. Valid
 * because Maia's
 * `policy()` output is itself a softmax over move logits (`maskAndSoftmax`,
 * `@/lib/maiaEncoding`) — `p_i^(1/T) / sum(p_j^(1/T))` is mathematically
 * equivalent to `softmax(logits/T)` for such inputs.
 *
 * This is a layered pure transform in the `select.ts` sense (module header,
 * "two DISTINCT functions layered in sequence, never conflated"): it sits
 * BEFORE `truncateAndRenormalize` (D-07) in the pipeline, never inside it —
 * `truncateAndRenormalize` stays general-purpose and untouched. Its output
 * becomes the input to truncation, whose output becomes `child.prior` — the
 * exact value `findability.ts`'s `rankScore` reads. No third "combiner"
 * function exists; the two threads compose because they are sequential pure
 * transforms over the same value (159-RESEARCH.md's central finding).
 *
 * Callers MUST short-circuit at `DEFAULT_POLICY_TEMPERATURE` (T=1) rather
 * than routing every call through this transform — `x ** 1` is
 * mathematically identity, but the renormalization division can still
 * introduce floating-point drift vs. skipping the transform entirely, which
 * would silently change today's default search output for every user who
 * never touches the slider (Pitfall 1, ENGINE-07 determinism).
 */

/**
 * T=1 is a true no-op (today's behavior) — callers MUST short-circuit at
 * this value rather than routing through `applyPolicyTemperature` (Pitfall 1,
 * ENGINE-07).
 */
export const DEFAULT_POLICY_TEMPERATURE = 1;

/**
 * Named hard cap on the number of root candidates surviving temperature +
 * truncation (Phase 159 D-07/Pitfall 6, T-159-05). `truncateAndRenormalize`'s
 * 0.9-mass cutoff has no candidate-count ceiling by design (correct at T=1,
 * where Maia's policy is normally peaked) — but at high T (up to 2.0) a
 * flattened distribution can require dozens of moves to reach 90% cumulative
 * mass, diluting the fixed `FLAWCHESS_ENGINE_MAX_NODES = 400` visit budget
 * across a much wider root branching factor. 15 is generous at T~1 (typical
 * root candidate counts are far below this) but bounded enough at T=2.0 to
 * protect the visit budget. Deliberately NOT `moveQuality.ts`'s
 * `CANDIDATE_HARD_CAP` — `select.ts`'s header forbids coupling those
 * independent tunables (search branching factor vs. chart display set).
 */
export const ROOT_CANDIDATE_HARD_CAP = 15;

/**
 * Reshapes `policy` via the standard softmax-temperature technique:
 * `p_i^(1/T)` renormalized to sum to 1. Guards `total <= 0` by returning 0
 * for every entry (degenerate empty/zero-mass input, mirrors `backup.ts`'s
 * `totalPrior===0` convention — never divides by zero or propagates `NaN`).
 */
export function applyPolicyTemperature(
  policy: Record<string, number>,
  temperature: number,
): Record<string, number> {
  const exponent = 1 / temperature;
  const reshaped = Object.entries(policy).map(([uci, p]) => [uci, p ** exponent] as const);
  const total = reshaped.reduce((sum, [, p]) => sum + p, 0);
  const result: Record<string, number> = {};
  for (const [uci, p] of reshaped) {
    result[uci] = total > 0 ? p / total : 0;
  }
  return result;
}
