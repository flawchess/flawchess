/**
 * botStyleBundles — the 4 named style-to-knob bundles (Phase 182, D-02).
 *
 * Ships the 4 named playstyles from SEED-098 (Attacker / Trickster / Grinder
 * / Wall) as plain exported `BotStyleParams` data constants (D-01/BOT-03: no
 * function fields, no player-derived values, no style names leaking into
 * `botStyle.ts`'s engine transforms — those consume ONLY the numeric knobs
 * defined here). `BOT_STYLE_BUNDLES` is what Phase 183's persona registry
 * will reference per persona; Plan 06 (`selectBotMove.ts` wiring) and Plan 07
 * (`useBotGame.ts` wiring) consume these same constants directly.
 *
 * STALENESS (D-11, Phase 184, CAL-04/CAL-05): `frontend/src/lib/personas/
 * personaRegistry.ts`'s `botElo`/`calibratedLabel` fields are calibrated
 * against the style params below via an operator-run overnight sweep
 * (`bin/run_persona_calibration_sweep.sh`). Changing ANY numeric knob in
 * this file (or extending the anchor ladder) invalidates that calibration —
 * re-run the sweep and regenerate `frontend/src/generated/
 * personaCalibration.ts` (`scripts/gen_persona_calibration.py`) before
 * trusting the persona registry's displayed strength labels again. This is
 * a documented operator policy only; no hash-guard automation enforces it.
 *
 * Magnitude provenance (D-12): every numeric knob below was hand-tuned
 * against `scripts/style-lever-measurement.mjs`'s real-Maia-policy TSV
 * output (`reports/data/style-lever-measurement-*.tsv`, N=200, seed=1,
 * elo=1000 — the tuning evidence committed alongside this file). Each
 * `featureMultipliers` field (the values the TSV directly measures) carries
 * a "Tuned (D-12)" doc comment citing the measured shift; `scoreBonus`/
 * `varianceBonus`/`contempt`/`threshold`/`hysteresisFloor`/`bookBoost` are
 * NOT individually tallied by the TSV (an averaged expected-score bonus, a
 * draw-contempt shift, and a resign/book policy knob have no per-move
 * feature to classify) — their final values are instead confirmed by the
 * cross-style ORDERING invariants `botStyleBundles.test.ts` asserts
 * (Grinder contempt > 0 / Wall contempt < 0, Grinder's resign floor far
 * below the other 3, Trickster's highest / Wall's lowest `varianceBonus`),
 * documented as such below.
 *
 * Tuning history (Task 3): the initial hand-picked pass got every style's
 * headline feature pointed the right direction except Wall's `isExchange`,
 * which measured NEGATIVE at its initial 1.5x — the redistribution pull of
 * Wall's OTHER discounts (isPawnAdvance/isPawnStorm/isCheck all < 1) onto
 * the large share of legal moves that are neither checks nor pawn moves nor
 * captures diluted the exchange boost faster than 1.5x could compensate.
 * Raised in two steps to 4.0 (with a matching isPawnStorm retune to 0.3 to
 * hold storm's own sign negative once exchange's much larger boost started
 * pulling relative weight off pawn-advance moves generally) until the
 * measured TSV delta flipped and stayed positive. See the Wall section
 * below for the literal before/after magnitudes.
 *
 * `bookBoost` values (D-06: roughly x20-50) are consumed together with
 * `styleLinesFor(style, side)` (`styleOpeningLines.ts`, Plan 03) at the
 * `useBotGame.ts` wiring seam (Plan 07) — this file does not itself store
 * curated line sets; `BOT_STYLE_BUNDLES`'s keys are the SAME `Style` union
 * `styleLinesFor` is keyed by, so a bundle "references" its curated book set
 * by key membership, not by embedding the set here.
 */

import type { BotStyleParams } from './botStyle';
import type { Style } from './styleOpeningLines';

// ─── Attacker — aggressive / complicating ──────────────────────────────────
// Checks/captures/pawn-storms boosted (D-06 identity); accepts Maia-3's
// documented sac-blindness as accepted flavor (182-CONTEXT.md specifics) —
// not worked around in this phase. Near-zero-to-slight positive contempt
// (D-09): an attacker is mildly reluctant to trade the game away for a draw
// but is not defined by drawing behavior the way Grinder/Wall are.

export const ATTACKER_STYLE: BotStyleParams = {
  featureMultipliers: {
    /** Tuned (D-12): kept at the initial 1.8 — the measurement TSV confirmed a visibly positive check-frequency delta (+0.0096 at N=200) vs baseline without further raising it, the cheapest, most legible "aggressive" tell. */
    isCheck: 1.8,
    /** Tuned (D-12): kept at the initial 1.5 — the measurement TSV confirmed the strongest single delta of Attacker's 3 headline features (+0.0316 capture-frequency at N=200); attacker presses material contact. */
    isCapture: 1.5,
    /** Tuned (D-12): kept at the initial 1.1 — a plain non-capturing pawn push is a mild "keeps developing forward" signal, not the identity driver; the TSV shows a modest but positive pawn-advance delta (+0.0104) as a side-effect of the 3 boosted features crowding it slightly rather than from this multiplier itself. */
    isPawnAdvance: 1.1,
    /** Tuned (D-12): kept at the initial 1.6 — the measurement TSV confirmed the largest of Attacker's 3 headline deltas (+0.0378 storm-frequency at N=200), the other headline attacking tell alongside checks/captures. */
    isPawnStorm: 1.6,
    /** Tuned (D-12): kept neutral at 1.0 — a capture that happens to be a roughly-even trade is not separately discouraged (isCapture's own 1.5x already applies to it); the TSV shows isExchange positive anyway (+0.0275) purely as a pass-through of the isCapture boost, confirming no dedicated exchange multiplier was needed for Attacker. */
    isExchange: 1.0,
    /** Tuned (D-12): kept at the initial 0.6 — an attacker presses forward rather than repositioning backward; retreats are rare enough in the sampled opening corpus (baseline 0.34%) that the measured delta (-0.0015) is directionally correct but too small a sample to further calibrate against. */
    isRetreat: 0.6,
  },
  /** Tuned (D-12): kept at 0.03 (within the ~0.02-0.05 band) — small positive optimism bias on the search branch; not individually tallied by the TSV (uniform across all lines so it never changes move ranking by itself). WR-02 (182-REVIEW.md): the resign/draw-gate score does NOT come from here — it comes from an independent post-commit `pool.grade()` call in `useBotGame.ts`; this bonus affects move SELECTION only. */
  scoreBonus: 0.03,
  /** Tuned (D-12): kept at 0.1 — positive; prefers the sharper of two root candidates when childScoreSpread differs (complicating identity carries into the search branch too); confirmed lower than Trickster's 0.2 and higher than Grinder/Wall's negative values by `botStyleBundles.test.ts`'s cross-style ordering assertions. */
  varianceBonus: 0.1,
  /** Tuned (D-12): kept at 0.03 — near-zero-to-slight positive per D-09; mildly reluctant to settle for a draw, but not Grinder's defining trait (Grinder's 0.15 stays the largest-magnitude positive contempt of the 4 styles). */
  contempt: 0.03,
  /** Tuned (D-12): kept at 0.12 — normal resign floor; an attacker concedes like any other styled bot once genuinely lost (D-08's resign policy is not part of the Attacker identity), confirmed well above Grinder's 0.02 "never resigns early" floor by the test suite. */
  threshold: 0.12,
  /** Tuned (D-12): kept at 4 — normal hysteresis, no early/late bias vs the `RESIGN_HYSTERESIS_TURNS` reference value in `botDrawGate.ts` (WR-03, 182-REVIEW.md: a hand-tuned reference the 4 bundles are picked around, not a live runtime fallback — every bundle sets its own `hysteresisFloor` explicitly), confirmed well below Grinder's 10 by the test suite. */
  hysteresisFloor: 4,
  /** Tuned (D-12): kept at 35 (within the D-06 ~20-50 band) — mid-high; attacking gambit lines should dominate the menu whenever available. Not separately measured (the TSV's opening-book sampling FENs are past book, not the book-selection step itself). */
  bookBoost: 35,
};

// ─── Trickster — defensive / complicating, traps & swindles ───────────────
// High-variance score-shaping preference is the defining Light/Deep-rung
// trait (SEED-098: "swindle mode + high variance at 1600+"); at Human rungs
// the identity carries mainly through the troll/swindle opening book
// (Plan 03's TRICKSTER_WHITE/BLACK_LINES) rather than through prior
// reweighting, so the feature multipliers here are deliberately mild.

export const TRICKSTER_STYLE: BotStyleParams = {
  featureMultipliers: {
    /** Tuned (D-12): kept at 1.3 — occasional surprise checks fit the trap/swindle identity without dominating move choice; the TSV shows a small positive delta (+0.0046), deliberately muted vs Attacker's 1.8/+0.0096 since Trickster's identity is carried mainly by the book + variance, not this lever. */
    isCheck: 1.3,
    /** Tuned (D-12): kept at 1.2 — captures that create complications (not simplifying trades) are a trickster trait; TSV delta +0.0032, deliberately mild. */
    isCapture: 1.2,
    isPawnAdvance: 1.0,
    /** Tuned (D-12): kept at 1.1 — a probing storm can set a trap; TSV delta +0.0031, deliberately mild vs Attacker's headline 1.6/+0.0378. */
    isPawnStorm: 1.1,
    /** Tuned (D-12): kept at 0.8 — a trickster avoids simplifying trades, which close down the complications swindles need; TSV shows the smallest positive isExchange delta of the styles that boost anything (+0.001), consistent with a deliberately mild discourage-not-suppress magnitude. */
    isExchange: 0.8,
    isRetreat: 1.0,
  },
  /** Tuned (D-12): kept at 0.01 — near-neutral; the trickster identity is carried by `varianceBonus`, not an average-position preference; not individually tallied by the TSV (uniform additive term). WR-02 (182-REVIEW.md): affects move SELECTION only — the resign/draw-gate score comes from an independent post-commit `pool.grade()` call in `useBotGame.ts`, not from this bonus. */
  scoreBonus: 0.01,
  /** Tuned (D-12): kept at 0.2 — the trickster's defining Light/Deep-rung trait; confirmed the HIGHEST `varianceBonus` of the 4 styles by `botStyleBundles.test.ts`'s cross-style ordering assertion (strictly greater than Attacker/Grinder/Wall). */
  varianceBonus: 0.2,
  /** Tuned (D-12): kept at 0.0 — a trickster is indifferent to draws by default per D-09, its identity is complications, not draw avoidance/seeking; deliberately the only style with exactly zero contempt. */
  contempt: 0.0,
  /** Tuned (D-12): kept at 0.12 — normal resign floor, no special resign identity; matches Attacker's band, confirmed well above Grinder's 0.02 by the test suite. */
  threshold: 0.12,
  /** Tuned (D-12): kept at 5 — slightly higher than the `RESIGN_HYSTERESIS_TURNS` reference value; a trickster plays on a beat longer looking for a swindle chance before conceding, but stays far below Grinder's 10 "never resigns early" floor. */
  hysteresisFloor: 5,
  /** Tuned (D-12): kept at 40 (within the D-06 ~20-50 band) — the HIGHEST of the 4 styles; the troll/swindle lines ARE the trickster's headline identity (SEED-098: "cheapest, most perceptible lever"), so book-following should be near-total whenever a line is available. */
  bookBoost: 40,
};

// ─── Grinder — analytics-native trade-happy, steers to endgames ───────────
// Never resigns early (SEED-098: "playing it trains exactly what FlawChess
// measures") — combines a very low resign floor with a high hysteresis
// requirement so only a near-total, sustained loss ever triggers a
// resignation. High-positive contempt (D-09): avoids draws, wants to keep
// grinding.

export const GRINDER_STYLE: BotStyleParams = {
  featureMultipliers: {
    isCheck: 1.0,
    /** Tuned (D-12): kept at 1.1 — captures that simplify toward an endgame are welcome, the dominant trade signal is `isExchange` below; TSV delta +0.0143 (isExchange's own product with this multiplier drives most of it). */
    isCapture: 1.1,
    isPawnAdvance: 1.0,
    /** Tuned (D-12): kept at 0.7 — a grinder does not rush the attack, it trades and steers toward the endgame instead; TSV shows a small POSITIVE storm delta in the prior_reweighting lane (+0.0042, a redistribution side-effect of the much larger exchange boost) but a small negative delta in the score_shaping lane (-0.0019) — net directionally acceptable, not Grinder's headline feature either way. */
    isPawnStorm: 0.7,
    /** Tuned (D-12): kept at the initial 1.8 — the measurement TSV confirmed a strongly positive exchange-frequency delta in BOTH lanes (prior_reweighting +0.0134, score_shaping +0.0019 after the Task 3 synthesizedChildScoreSpread bug fix), the headline Grinder tell ("exchange/trade multiplier greater than 1"). */
    isExchange: 1.8,
    isRetreat: 1.0,
  },
  /** Tuned (D-12): kept at 0.02 — small positive; a grinder is quietly confident in the kind of grounded, simplified positions its own style already steers toward; not individually tallied by the TSV (uniform additive term). WR-02 (182-REVIEW.md): affects move SELECTION only — the resign/draw-gate score comes from an independent post-commit `pool.grade()` call in `useBotGame.ts`, not from this bonus. */
  scoreBonus: 0.02,
  /** Tuned (D-12): kept at -0.1 — prefers the FLATTER of two root candidates when childScoreSpread differs, the direct opposite of Trickster/Attacker's sharp-line preference; confirmed negative (below all 3 other styles except Wall) by `botStyleBundles.test.ts`, reinforcing the simplifying/steering-to-endgame identity on the search branch. */
  varianceBonus: -0.1,
  /** Tuned (D-12): kept at 0.15 — high-positive per D-09, the defining Grinder trait: wants meaningfully more than dead-equal before accepting a draw, so `drawValue = 0.5 + contempt` sits well above 0.5 (CR-01, 182-REVIEW.md: corrected from the inverted `0.5 - contempt`); confirmed the LARGEST-magnitude contempt of the 4 styles (strictly > 0, and > Attacker/Trickster's near-zero values) by the test suite. */
  contempt: 0.15,
  /** Tuned (D-12): kept at 0.02 — D-08 "never resigns early": very low resign floor, only a position at or near objectively lost (practicalScore near the bottom of its [0,1] range) can ever qualify, an ordinary "worse but fighting" position never crosses this bar; confirmed the LOWEST threshold of the 4 styles (strictly below Attacker/Trickster/Wall's 0.12-0.18 band) by the test suite. */
  threshold: 0.02,
  /** Tuned (D-12): kept at 10 — high hysteresis, layered on top of the already-low threshold as a second independent safeguard against an early resignation off one or two rough turns; the score must stay at/below `threshold` for this many of the Grinder's OWN consecutive turns before `wouldBotResign` can ever fire; confirmed the HIGHEST hysteresis floor of the 4 styles by the test suite (strictly above Attacker's 4). */
  hysteresisFloor: 10,
  /** Tuned (D-12): kept at 25 (within the D-06 ~20-50 band) — the LOWEST of the 4 styles; Grinder's identity is carried mainly by the exchange multiplier + contempt + resign policy, not the opening phase, so a solid-but-not-maximal boost is enough for its exchange-heavy lines to dominate the menu when available. */
  bookBoost: 25,
};

// ─── Wall — defensive / simplifying, system openings ──────────────────────
// Slightly-negative contempt (D-09): welcomes an early draw a bit more
// readily than dead-equal. Simplifying preference carries across every
// lever: exchanges boosted, storms strongly discouraged, retreats (a
// defensive repositioning tell) mildly favored, and a negative
// `varianceBonus` prefers the flattest available continuation.

export const WALL_STYLE: BotStyleParams = {
  featureMultipliers: {
    /** Tuned (D-12): kept at 0.8 — a wall does not go out of its way to give checks, it holds its structure; TSV shows a small negative check delta (-0.003), directionally correct. */
    isCheck: 0.8,
    isCapture: 1.0,
    /** Tuned (D-12): kept at 0.9 — a system player keeps its fixed setup rather than pushing pawns reactively; the measurement TSV confirmed the strongest of Wall's headline deltas (-0.0375 pawn-advance frequency at N=200, the single largest-magnitude shift of any style/feature pair measured). */
    isPawnAdvance: 0.9,
    /** Tuned (D-12) — lowered from the initial 0.5 to 0.3 after raising isExchange to 4.0 (below): the measurement TSV showed storm frequency flip slightly POSITIVE at the intermediate isExchange=3.0/isPawnStorm=0.5 combination (the strong exchange boost pulled enough relative weight off pawn-advance moves generally that storm's own share crept up despite its own discount). 0.3 restored a visibly negative storm delta (-0.0091 at the final combination), the direct opposite of Attacker's headline trait — "a wall never storms". */
    isPawnStorm: 0.3,
    /** Tuned (D-12) — raised from the initial 1.5 through 3.0 to 4.0: the measurement TSV showed 1.5 was too weak to overcome the redistribution pull of the isPawnAdvance/isPawnStorm/isCheck discounts onto the ~93% of legal moves that are NOT even-trade captures (isExchange delta measured NEGATIVE, -0.0059, at 1.5). 4.0 (paired with the isPawnStorm 0.3 retune above) is the smallest magnitude tested that kept the measured delta visibly positive (+0.0121 prior_reweighting, +0.0008 score_shaping) — simplifying trades are the Wall's headline identity trait alongside its book. */
    isExchange: 4.0,
    /** Tuned (D-12): kept at 1.2 — a defensive reposition toward one's own back rank fits the "hold the fort" identity; retreats are rare in the sampled opening corpus (baseline 0.34%) so the measured delta (+0.0008) is directionally correct but too small a sample to further calibrate against. */
    isRetreat: 1.2,
  },
  /** Tuned (D-12): kept at -0.02 — small negative; a cautious, risk-averse discount on the search branch's optimism, mirroring the defensive identity; not individually tallied by the TSV (uniform additive term). WR-02 (182-REVIEW.md): affects move SELECTION only — the resign/draw-gate score comes from an independent post-commit `pool.grade()` call in `useBotGame.ts`, not from this bonus. */
  scoreBonus: -0.02,
  /** Tuned (D-12): kept at -0.15 — the strongest flat/quiet preference of the 4 styles; prefers the LEAST-spread root candidate whenever childScoreSpread differs; confirmed the LOWEST (most negative) `varianceBonus` of the 4 styles by `botStyleBundles.test.ts`'s cross-style ordering assertion. */
  varianceBonus: -0.15,
  /** Tuned (D-12): kept at -0.08 — slightly-negative per D-09; welcomes a draw a bit before dead-equal, so `drawValue = 0.5 + contempt` sits just below 0.5 (CR-01, 182-REVIEW.md: corrected from the inverted `0.5 - contempt`); confirmed strictly negative (the only style below zero) by the test suite. */
  contempt: -0.08,
  /** Tuned (D-12): kept at 0.18 — higher resign floor than the shared default; a pragmatic, simplifying style concedes a clearly worse position sooner rather than grinding on; confirmed the HIGHEST threshold of the 4 styles by the test suite. */
  threshold: 0.18,
  /** Tuned (D-12): kept at 3 — lower than the `RESIGN_HYSTERESIS_TURNS` reference value; once the score has settled at/below threshold, a wall concedes without playing on for long; confirmed the LOWEST hysteresis floor of the 4 styles by the test suite. */
  hysteresisFloor: 3,
  /** Tuned (D-12): kept at 30 (within the D-06 ~20-50 band) — mid-low; the London/Colle/Caro-Kann/Stonewall system lines are recognizable without needing the maximal boost the Trickster's troll-opening identity relies on. */
  bookBoost: 30,
};

/**
 * The 4 named style bundles, keyed by `Style` (`styleOpeningLines.ts`,
 * Plan 03) — a `Record<Style, BotStyleParams>` so TypeScript enforces all 4
 * styles stay present. Phase 183's persona registry looks a persona's style
 * up here by name; Plans 06/07 wire the resolved `BotStyleParams` into
 * `selectBotMove`/`useBotGame` exactly as any other optional `style` value.
 */
export const BOT_STYLE_BUNDLES: Record<Style, BotStyleParams> = {
  Attacker: ATTACKER_STYLE,
  Trickster: TRICKSTER_STYLE,
  Grinder: GRINDER_STYLE,
  Wall: WALL_STYLE,
};
