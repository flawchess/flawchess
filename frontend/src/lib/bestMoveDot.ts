/**
 * Gem/great eval-chart dot spec (Phase 175 Plan 06) — a pure function, extracted to
 * its own module (not EvalChart.tsx, which also exports the `EvalChart` React
 * component) to satisfy react-refresh's component-only-export rule. Mirrors
 * gemGlyph.ts/greatGlyph.ts's own "plain module, not the icon component file"
 * rationale.
 *
 * Living here also makes the color/tier binding, highlight emphasis, and dimming
 * unit-testable directly, without mounting recharts' custom `dot` render prop —
 * recharts 3 renders dots behind portal/zIndex layers that make jsdom
 * pixel-position assertions unreliable (see
 * EndgameClockDiffOverTimeChart.test.tsx's own note on this).
 */

import { isUserPly } from '@/lib/plyOwnership';
import { GREAT_ACCENT, MAIA_ACCENT } from '@/lib/theme';
import type { EvalPoint } from '@/types/library';

/**
 * Gem/great dot radius — same visual weight as EvalChart.tsx's own
 * FLAW_DOT_RADIUS (4.5). The two layers never coexist on the same ply (a
 * gem/great tier and a flaw marker are mutually exclusive: a gem/great is the
 * user's own best move, a flaw is a mistake), so color alone (violet/blue vs
 * severity) is the differentiator, not size.
 */
export const GEM_GREAT_DOT_RADIUS = 4.5;

/**
 * Radius multiplier for an emphasized (hover-highlighted) dot, and the opacity
 * for a non-matching dot while a highlight set is active. MUST match
 * EvalChart.tsx's own HIGHLIGHT_RADIUS_FACTOR / DIMMED_MARKER_OPACITY constants
 * (the flaw-dot layer) — both layers share the SAME highlightedPlies prop and
 * emphasis/dim convention by design (Task 1's "mirror the flaw layer's rule
 * exactly" requirement).
 */
const HIGHLIGHT_RADIUS_FACTOR = 1.25;
const DIMMED_OPACITY = 0.2;

export interface BestMoveDotSpec {
  color: string;
  radius: number;
  opacity: number;
}

/**
 * Dot spec for one EvalPoint's gem/great tier. Returns null when the ply has no
 * gem/great tier or no eval (es == null) — mirrors EvalChart's flaw-dot renderer's
 * invisible <g/> branch. An empty/null highlight set is a no-op (never dims
 * everything), matching the flaw layer's convention.
 *
 * Bug fix (Phase 175 Plan 06): `best_move_tier` is POSITION-scoped — the backend
 * stores it for BOTH players' best moves — so without a user filter the dot layer
 * painted the OPPONENT's gems/greats too. When `userColor` is provided, only the
 * user's own plies (mover parity) draw a dot; opponent best-moves are intentionally
 * excluded. `userColor` is optional so a call with no known color (should not happen
 * for an analyzed game) renders every tier as before rather than silently hiding
 * everything.
 */
export function bestMoveDotSpec(
  point: EvalPoint,
  highlightedPlies?: ReadonlySet<number> | null,
  userColor?: 'white' | 'black',
): BestMoveDotSpec | null {
  if (point.best_move_tier == null || point.es == null) return null;
  if (userColor != null && !isUserPly(point.ply, userColor)) return null;
  const highlightActive = highlightedPlies != null && highlightedPlies.size > 0;
  const matched = highlightActive && highlightedPlies!.has(point.ply);
  return {
    color: point.best_move_tier === 'gem' ? MAIA_ACCENT : GREAT_ACCENT,
    radius: matched ? GEM_GREAT_DOT_RADIUS * HIGHLIGHT_RADIUS_FACTOR : GEM_GREAT_DOT_RADIUS,
    opacity: !highlightActive || matched ? 1 : DIMMED_OPACITY,
  };
}
