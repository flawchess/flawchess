// AUTO-GENERATED — do not edit by hand.
// Source: scripts/gen_bot_strength_curves.py, reports/data/bot-curves-internal-scale.json
// Regenerate with: uv run python scripts/gen_bot_strength_curves.py

export type BotStrengthPreset = "human" | "light" | "deep";

export const APPROX_ELO_DISCLAIMER = "This is an APPROXIMATE Lichess blitz ELO, derived from an internal calibration scale rather than measured against real players. It carries a per-preset uncertainty band and should be read as a rough guide, not a precise rating.";

export const BOT_STRENGTH_LOOKUP: Record<BotStrengthPreset, Record<number, number>> = {
  human: { 900: 1100, 1000: 1100, 1100: 1500, 1200: 1900, 1300: 1900, 1400: 1900 },
  light: { 1500: 1900, 1600: 1900 },
  deep: { 1600: 1500, 1700: 1500, 1800: 2300 },
} as const;

export const BOT_STRENGTH_RANGES: Record<
  BotStrengthPreset,
  { floor: number; ceiling: number }
> = {
  human: { floor: 900, ceiling: 1400 },
  light: { floor: 1500, ceiling: 1600 },
  deep: { floor: 1600, ceiling: 1800 },
} as const;

export const BOT_STRENGTH_BANDS: Record<BotStrengthPreset, number> = {
  human: 225,
  light: 200,
  deep: 250,
} as const;
