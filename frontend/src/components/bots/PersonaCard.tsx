/**
 * PersonaCard — a single tappable persona tile on the Bots page grid (Phase
 * 183, PERS-01/AVAT-01/AVAT-02). Shows the persona's avatar, name, and the
 * calibrated, tilde-prefixed strength label (Phase 184 CAL-05,
 * `persona.calibratedLabel`) — never a raw unqualified number, and never
 * `~${persona.rung}` (the pre-calibration provisional value; see
 * `personaRegistry.ts`'s calibration-provenance header note).
 *
 * Backstop: the avatar renders `resolveAvatarSrc(persona)`'s future real-art
 * portrait (D-17) when present, otherwise the D-18 placeholder (species
 * emoji on the per-style tint) — a persona whose real-art `avatarSrc` is
 * absent/pending NEVER fails to render an avatar; the emoji fallback is
 * always present. Every persona omits `avatarSrc` today (183-01-SUMMARY.md),
 * so every card currently renders the emoji branch.
 */

import type { ReactElement } from 'react';
import type { Persona } from '@/lib/personas/personaRegistry';
import { placeholderAvatarFor, resolveAvatarSrc } from '@/lib/personas/personaAvatars';

export interface PersonaCardProps {
  persona: Persona;
  onSelect: (persona: Persona) => void;
}

/** Fixed avatar-circle size (px) — shared by the width/height so the avatar
 * always renders in a perfect circle regardless of Tailwind's responsive
 * grid-column width above it. */
const AVATAR_SIZE_PX = 48;

export function PersonaCard({ persona, onSelect }: PersonaCardProps): ReactElement {
  const avatar = placeholderAvatarFor(persona);
  const avatarSrc = resolveAvatarSrc(persona);

  return (
    <button
      type="button"
      data-testid={`bots-persona-card-${persona.id}`}
      aria-label={`${persona.name}, ${persona.calibratedLabel} ELO`}
      onClick={() => onSelect(persona)}
      className="flex flex-col items-center gap-1 rounded border border-border bg-card p-2 text-center transition-colors pointer-fine:hover:bg-inactive-bg-hover"
    >
      <span
        aria-hidden="true"
        className="flex shrink-0 items-center justify-center overflow-hidden rounded-full text-2xl"
        style={{
          backgroundColor: avatar.tint,
          width: AVATAR_SIZE_PX,
          height: AVATAR_SIZE_PX,
        }}
      >
        {avatarSrc !== undefined ? (
          <img src={avatarSrc} alt="" className="h-full w-full object-cover" />
        ) : (
          avatar.emoji
        )}
      </span>
      <span className="text-sm font-medium text-foreground">{persona.name}</span>
      <span className="text-sm text-muted-foreground">{persona.calibratedLabel}</span>
    </button>
  );
}
