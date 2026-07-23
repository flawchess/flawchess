// AUTO-GENERATED — do not edit by hand.
// Source: scripts/gen_persona_calibration.py, reports/data/persona-calibration-cells.tsv
// Regenerate with: uv run python scripts/gen_persona_calibration.py

// STALENESS (D-11): changing botStyleBundles.ts style params or the anchor
// ladder invalidates this calibration — re-run the persona sweep
// (bin/run_persona_calibration_sweep.sh) before regenerating. No hash-guard
// automation enforces this — it is a documented operator policy only.

import type { PersonaId } from '@/lib/personas/personaRegistry';

// False while the labels are provisional (`--bootstrap` fit: approx_blitz =
// rung, ratings NaN). The ELO disclosure popover reads this so it never
// claims a measurement that has not happened; it flips to true on the first
// real sweep refit.
export const PERSONA_CALIBRATION_MEASURED = true;

export const PERSONA_CALIBRATION: Record<PersonaId, { botElo: number; label: string }> = {
  'attacker-800': { botElo: 700, label: '~800' },
  'attacker-1000': { botElo: 1100, label: '~1000' },
  'attacker-1200': { botElo: 1500, label: '~1300' },
  'attacker-1400': { botElo: 1900, label: '~1400' },
  'attacker-1600': { botElo: 1900, label: '~1650' },
  'attacker-1800': { botElo: 2300, label: '~1800' },
  'trickster-800': { botElo: 700, label: '~750' },
  'trickster-1000': { botElo: 1100, label: '~1050' },
  'trickster-1200': { botElo: 1500, label: '~1150' },
  'trickster-1400': { botElo: 1900, label: '~1300' },
  'trickster-1600': { botElo: 1500, label: '~1600' },
  'trickster-1800': { botElo: 2300, label: '~1800' },
  'grinder-800': { botElo: 700, label: '~900' },
  'grinder-1000': { botElo: 1100, label: '~1000' },
  'grinder-1200': { botElo: 1500, label: '~1250' },
  'grinder-1400': { botElo: 1900, label: '~1450' },
  'grinder-1600': { botElo: 1500, label: '~1500' },
  'grinder-1800': { botElo: 2300, label: '~1800' },
  'wall-800': { botElo: 700, label: '~850' },
  'wall-1000': { botElo: 1100, label: '~1050' },
  'wall-1200': { botElo: 1500, label: '~1200' },
  'wall-1400': { botElo: 1900, label: '~1250' },
  'wall-1600': { botElo: 1900, label: '~1550' },
  'wall-1800': { botElo: 2300, label: '~1800' },
} as const;
