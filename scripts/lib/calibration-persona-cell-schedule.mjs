#!/usr/bin/env node
/**
 * calibration-persona-cell-schedule.mjs — PersonaId-keyed persona-cell
 * schedule (Phase 184, Plan 01, Task 2). Reuses (imports, never forks) the
 * Phase-180 bot-cell scheduler's pure anchor-selection primitives
 * (`internalRatingFor`, `pickLocateAnchors`, `locateEstimate`,
 * `selectMeasureBracket`, `bracketBeyondLadder`) verbatim — the anchor math
 * is UNCHANGED; only the outer grouping key changes from `(botElo, blend)`
 * to `PersonaId` (the load-bearing Pitfall-1 fix, T-184-01-02).
 *
 * WHY A NEW MODULE, NOT A VERBATIM REUSE OF THE BOT-CELL SCHEDULE:
 * after Phase-181 retargeting (D-01), multiple DISTINCT personas collide on
 * an identical `(botElo, blend)` pair — e.g. every rung-1800 persona (all 4
 * styles) retargets to `(botElo=2300, blend=DEEP_BLEND)`, and rung-800/1000
 * personas collide on `(botElo=1100, blend=HUMAN_BLEND)` within every
 * style — yet each must be measured and ledgered INDEPENDENTLY to capture
 * its own style-induced strength delta (CAL-04's entire point). Keying by
 * `(botElo, blend)` (`calibration-harness.mjs`'s `cellKey`, the pattern to
 * AVOID here) would silently merge them into one accumulator.
 * `personaCellKey` below fixes this by keying strictly on `PersonaId`.
 *
 * No engines, no I/O — every export here is a deterministic transform over
 * `PERSONA_REGISTRY` + the Phase-181 `BOT_STRENGTH_LOOKUP`, unit-testable
 * independent of any real engine run (see
 * `calibration-persona-cell-schedule.check.mjs`).
 */
import {
  internalRatingFor,
  pickLocateAnchors,
  locateEstimate,
  selectMeasureBracket,
  bracketBeyondLadder,
  LOCATE_PASS_GAMES,
  DEFAULT_BRACKET_SIZE,
  MIN_BRACKET_PER_FAMILY,
} from './calibration-bot-cell-schedule.mjs';
import { PERSONA_REGISTRY } from '@/lib/personas/personaRegistry';
import { BOT_STYLE_BUNDLES } from '@/lib/engine/botStyleBundles';
import { BOT_STRENGTH_LOOKUP } from '@/generated/botStrengthCurves';
import { deriveActivePlayStylePreset } from '@/lib/playStyle';

// Re-export the imported anchor-selection primitives verbatim (Task 2:
// "import, don't fork") so a future persona-sweep orchestration script can
// pull the full anchor-selection surface from this ONE module.
export {
  internalRatingFor,
  pickLocateAnchors,
  locateEstimate,
  selectMeasureBracket,
  bracketBeyondLadder,
  LOCATE_PASS_GAMES,
  DEFAULT_BRACKET_SIZE,
  MIN_BRACKET_PER_FAMILY,
};

/**
 * Maps a persona's raw `blend` value to the Phase-181 preset name
 * `BOT_STRENGTH_LOOKUP` is keyed by ("human" | "light" | "deep"). Reuses
 * `playStyle.ts`'s `deriveActivePlayStylePreset` — the SAME exact-equality
 * 3-way mapping the app itself uses for HUMAN_BLEND(0)/LIGHT_BLEND(0.05)/
 * DEEP_BLEND(0.5) — rather than re-deriving those literals here. Throws
 * fail-loud (never coerces to a default) on any other blend value: a
 * persona-cell schedule has no legitimate "unknown preset" case (mirrors
 * `internalRatingFor`'s fail-loud discipline, WR-02).
 */
export function presetNameForBlend(blend) {
  const preset = deriveActivePlayStylePreset(blend);
  if (preset === null) {
    throw new Error(
      `presetNameForBlend: blend=${blend} does not match any of the 3 named presets ` +
        '(human=0 / light=0.05 / deep=0.5)',
    );
  }
  return preset;
}

/**
 * Retargeted `botElo` for a persona (D-01): looks up
 * `BOT_STRENGTH_LOOKUP[presetNameForBlend(persona.blend)][String(persona.rung)]`
 * — the Phase-181 100-step blitz->bot_elo inversion for the persona's own
 * preset, so the underlying search strength actually TARGETS the rung
 * (e.g. a Human rung-1200 persona retargets to `botElo=1900`, not 1200).
 *
 * The 800 rung sits BELOW every preset's measured floor — no `"800"` key
 * exists in ANY preset's lookup (every preset's lowest key is >= 900 in
 * `bot-strength-lookup.json`). Rather than throwing on that expected gap,
 * this clamps to the LOWEST available key for the persona's preset
 * (CONTEXT.md D-01/discretion: "the 800 rung clamps to the lookup's lowest
 * available bot_elo"). Still fails loud (never silently defaults to some
 * arbitrary number) if the preset/rung combo is unusable even after the
 * floor clamp — that would be a genuine data-integrity bug in
 * `bot-strength-lookup.json`, not a legitimate edge case to swallow.
 */
export function retargetedBotEloFor(persona) {
  const preset = presetNameForBlend(persona.blend);
  const lookup = BOT_STRENGTH_LOOKUP[preset];
  if (lookup === undefined) {
    throw new Error(`retargetedBotEloFor: no BOT_STRENGTH_LOOKUP entry for preset "${preset}"`);
  }

  const directHit = lookup[String(persona.rung)];
  if (directHit !== undefined) return directHit;

  // 800-rung floor clamp: fall back to the preset's lowest available key.
  const lowestKey = Math.min(...Object.keys(lookup).map(Number));
  const floorHit = lookup[String(lowestKey)];
  if (floorHit === undefined) {
    throw new Error(
      `retargetedBotEloFor: preset "${preset}" has no usable lookup entry for rung=${persona.rung} ` +
        `even after clamping to its lowest key (${lowestKey}) — check bot-strength-lookup.json`,
    );
  }
  return floorHit;
}

/**
 * Persona-cell key (fixes Pitfall 1 — the load-bearing correctness
 * safeguard of this phase, T-184-01-02): keyed strictly by `PersonaId`,
 * NEVER by `(botElo, blend)`. Mirrors `calibration-harness.mjs`'s
 * `cellKey(botElo, botBlend, anchorLabel)` shape but substitutes the key —
 * verified real collisions exist post-retargeting (rung 1800 all 4 styles
 * share `(botElo=2300, blend=DEEP_BLEND)`; rung 800/1000 share
 * `(botElo=1100, blend=HUMAN_BLEND)` within every style), so
 * `(botElo, blend)` is NOT a unique cell identity for a persona.
 */
export function personaCellKey(personaId, anchorLabel) {
  return `${personaId}|${anchorLabel}`;
}

/**
 * The 24 PersonaId-keyed cell records — one per `PERSONA_REGISTRY` slot.
 * Each holds the persona's identity (`personaId`/`style`/`rung`/`blend`),
 * its D-01 retargeted `botElo`, and the resolved `BotStyleParams` bundle a
 * persona-cell sweep threads into `playGame({ ..., style: styleParams })`.
 *
 * Built once at module load (pure data, no engine/network access). Every
 * entry is independently keyed by `personaId` — colliding-`(botElo, blend)`
 * personas (Pitfall 1) still produce 24 DISTINCT rows here, never merged
 * into one accumulator.
 */
export const ALL_PERSONA_CELLS = Object.values(PERSONA_REGISTRY).map((persona) => ({
  personaId: persona.id,
  style: persona.style,
  rung: persona.rung,
  blend: persona.blend,
  botElo: retargetedBotEloFor(persona),
  styleParams: BOT_STYLE_BUNDLES[persona.style],
}));
