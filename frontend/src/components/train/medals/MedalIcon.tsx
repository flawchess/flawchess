/**
 * MedalIcon — a gold, silver or bronze medal drawn after the 🥇 emoji
 * (Phase 231 UAT): two ribbon straps forming a V above a filled disc with a
 * darker rim and the place number. Shared by the row tally, the "Last week:"
 * podium and the medal dialog. The colours live in theme.ts; this component
 * never carries a colour literal. Inline SVG rather than the emoji character,
 * so it renders the same on every platform.
 */
import type { ReactElement } from 'react';
import { MEDAL_PALETTES, MEDAL_RIBBON_LEFT, MEDAL_RIBBON_RIGHT } from '@/lib/theme';
import { cn } from '@/lib/utils';
import type { MedalKind } from '@/types/train';

const MEDAL_PLACE: Record<MedalKind, number> = { gold: 1, silver: 2, bronze: 3 };

// Geometry in a 100x100 viewBox. The straps end behind the disc.
const LEFT_STRAP_POINTS = '16,0 38,0 62,48 40,54';
const RIGHT_STRAP_POINTS = '62,0 84,0 60,54 38,48';
const DISC_CX = 50;
const DISC_CY = 66;
const RIM_RADIUS = 33;
const FACE_RADIUS = 25;
const NUMBER_FONT_SIZE = 34;

export function MedalIcon({ kind, className }: { kind: MedalKind; className?: string }): ReactElement {
  const palette = MEDAL_PALETTES[kind];
  return (
    <svg viewBox="0 0 100 100" aria-hidden="true" className={cn('size-4 shrink-0', className)}>
      <polygon points={LEFT_STRAP_POINTS} fill={MEDAL_RIBBON_LEFT} />
      <polygon points={RIGHT_STRAP_POINTS} fill={MEDAL_RIBBON_RIGHT} />
      <circle cx={DISC_CX} cy={DISC_CY} r={RIM_RADIUS} fill={palette.rim} />
      <circle cx={DISC_CX} cy={DISC_CY} r={FACE_RADIUS} fill={palette.face} />
      <text
        x={DISC_CX}
        y={DISC_CY}
        textAnchor="middle"
        dominantBaseline="central"
        fontSize={NUMBER_FONT_SIZE}
        fontWeight={700}
        fill={palette.number}
      >
        {MEDAL_PLACE[kind]}
      </text>
    </svg>
  );
}
