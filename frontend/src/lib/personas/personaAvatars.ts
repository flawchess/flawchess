/**
 * personaAvatars — the placeholder-avatar look (species emoji on a
 * per-style background tint) plus the real-art seam: a Vite
 * `import.meta.glob` lookup over `frontend/src/assets/personas/*.webp`.
 *
 * `resolveAvatarSrc` globs the assets directory once at module load (`eager:
 * true`), keyed by each file's basename (the persona id, e.g.
 * `attacker-800`). A persona with no matching webp resolves to `undefined`,
 * so `PersonaCard` falls back to the emoji placeholder — the
 * generate-curate-swap loop (`scripts/gen_persona_avatars.py`,
 * `frontend/src/data/personaAvatarPrompts.md`) works by deleting a webp and
 * rerunning the script; no code change is ever needed here. The glob
 * matching zero files (before any webp exists) is valid — Vite's glob
 * returns `{}` — so the build stays green with or without curated art.
 */

import type { Persona } from './personaRegistry';
import type { Style } from '@/lib/engine/styleOpeningLines';
import {
  ATTACKER_ACCENT,
  ATTACKER_ACCENT_BG,
  TRICKSTER_ACCENT,
  TRICKSTER_ACCENT_BG,
  GRINDER_ACCENT,
  GRINDER_ACCENT_BG,
  WALL_ACCENT,
  WALL_ACCENT_BG,
} from '@/lib/theme';

/** Full-strength per-style accent — the `PersonaCard` border + glow color.
 * Same hue as `PERSONA_STYLE_TINT`, minus the 14% wash. */
export const PERSONA_STYLE_ACCENT: Record<Style, string> = {
  Attacker: ATTACKER_ACCENT,
  Trickster: TRICKSTER_ACCENT,
  Grinder: GRINDER_ACCENT,
  Wall: WALL_ACCENT,
};

/** Per-style placeholder-avatar background tint, keyed by `Style` so
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

/** Returns `persona`'s placeholder avatar: the emoji + per-style tint every
 * avatar consumer renders when no real art resolves. */
export function placeholderAvatarFor(persona: Persona): PlaceholderAvatar {
  return { emoji: persona.avatarEmoji, tint: PERSONA_STYLE_TINT[persona.style] };
}

/**
 * Glob every persona webp at module load, keyed by the filename stem (the
 * persona id). `query: '?url'` + `import: 'default'` yields a plain URL
 * string per matched file, matching `<img src>`'s expected type — no raw
 * asset objects leak out of this module.
 *
 * The glob is `eager: true` deliberately, rather
 * than a lazy per-persona `import()`. At `BUNDLE_AVATAR_SIZE_PX`
 * (128px, see `scripts/gen_persona_avatars.py`) the 24 variants are roughly
 * 5-8 KB each — about 150 KB of URL-only string imports, no longer the
 * payload problem the 512px masters were. A lazy glob would force
 * `resolveAvatarSrc` to become async and ripple through every caller for no
 * measurable win. `frontend/src/assets/personas-source/` holds the 512x512 masters and
 * is deliberately outside this glob pattern — the delete-a-master-and-rerun
 * curation loop (`scripts/gen_persona_avatars.py`) keys off that directory,
 * not this one.
 */
const AVATAR_MODULES = import.meta.glob('../../assets/personas/*.webp', {
  eager: true,
  query: '?url',
  import: 'default',
}) as Record<string, string>;

/** `AVATAR_MODULES`'s glob-path keys reduced to `{persona-id: url}` — computed
 * once at module load, not per render. */
const AVATAR_SRC_BY_ID: Record<string, string> = Object.fromEntries(
  Object.entries(AVATAR_MODULES).map(([path, url]) => {
    const stem = path.split('/').pop()?.replace(/\.webp$/, '') ?? path;
    return [stem, url];
  }),
);

/**
 * Real-art avatar resolution: `persona.avatarSrc` wins if a persona
 * ever sets it explicitly (the field's documented override purpose), else
 * the glob-backed lookup by persona id, else `undefined` (no webp curated
 * yet — every caller falls back to the emoji placeholder).
 */
export function resolveAvatarSrc(persona: Persona): string | undefined {
  return persona.avatarSrc ?? AVATAR_SRC_BY_ID[persona.id];
}
