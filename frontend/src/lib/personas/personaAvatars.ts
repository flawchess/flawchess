/**
 * personaAvatars — the D-18 placeholder-avatar look (species emoji on a
 * per-style background tint) plus the D-17 forward-compat seam for the
 * future real-art PR (Phase 183, AVAT-01 partial).
 *
 * RESEARCH.md Pitfall 6: this codebase has ZERO existing precedent for
 * `import.meta.glob`/Vite-bundled `@/assets/*` image imports — every
 * existing app image is a plain `/public/...` string path. Building that
 * import machinery now, before any real `.webp` files exist, risks either
 * dead code or a half-built pattern that doesn't actually satisfy D-17's
 * "build-time existence check" requirement. This module therefore ships
 * ONLY the placeholder path: `resolveAvatarSrc` is the single seam the
 * future real-art PR will need to touch (swap its body for a Vite import
 * lookup) — no glob, no static `.webp`/`.png` import statements here.
 */

import type { Persona } from './personaRegistry';
import type { Style } from '@/lib/engine/styleOpeningLines';
import {
  ATTACKER_ACCENT_BG,
  TRICKSTER_ACCENT_BG,
  GRINDER_ACCENT_BG,
  WALL_ACCENT_BG,
} from '@/lib/theme';

/** Per-style placeholder-avatar background tint (D-18), keyed by `Style` so
 * TypeScript enforces all 4 styles stay present — mirrors
 * `BOT_STYLE_BUNDLES`'s `Record<Style, ...>` exhaustiveness convention. */
export const PERSONA_STYLE_TINT: Record<Style, string> = {
  Attacker: ATTACKER_ACCENT_BG,
  Trickster: TRICKSTER_ACCENT_BG,
  Grinder: GRINDER_ACCENT_BG,
  Wall: WALL_ACCENT_BG,
};

/** The placeholder-avatar look for a persona: its species emoji rendered on
 * its style's background tint. */
export interface PlaceholderAvatar {
  emoji: string;
  tint: string;
}

/** Returns `persona`'s placeholder avatar (D-18) — the emoji + per-style
 * tint pairing every consumer (grid card, clock strip, result surfaces,
 * draw banner) renders until real art lands. */
export function placeholderAvatarFor(persona: Persona): PlaceholderAvatar {
  return { emoji: persona.avatarEmoji, tint: PERSONA_STYLE_TINT[persona.style] };
}

/**
 * Forward-compat seam (D-17): returns `persona.avatarSrc` if a future PR
 * ever populates it, `undefined` today (every current persona omits the
 * field). No bundling, no glob — the future real-art PR swaps ONLY this
 * function's body for a real Vite-imported lookup; every caller of this
 * function stays unchanged.
 */
export function resolveAvatarSrc(persona: Persona): string | undefined {
  return persona.avatarSrc ?? undefined;
}
