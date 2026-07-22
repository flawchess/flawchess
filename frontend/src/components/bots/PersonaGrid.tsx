/**
 * PersonaGrid — the Bots page's default setup view (Phase 183, PERS-01/
 * PERS-04). Renders all 24 personas grouped into 4 style sections
 * (`STYLE_SECTION_ORDER`), each ascending by rung 800->1800
 * (`personasForSection`), plus one clearly-visible Custom entry that routes
 * to the unchanged `SetupScreen` (D-01) rather than duplicating any of its
 * controls here.
 */

import type { ReactElement } from 'react';
import { PersonaCard } from '@/components/bots/PersonaCard';
import { Button } from '@/components/ui/button';
import {
  STYLE_SECTION_ORDER,
  personasForSection,
  type Persona,
} from '@/lib/personas/personaRegistry';
import type { Style } from '@/lib/engine/styleOpeningLines';
import { ATTACKER_ACCENT, TRICKSTER_ACCENT, GRINDER_ACCENT, WALL_ACCENT } from '@/lib/theme';

/** Per-style section-heading accent (D-14: the heading text is the style's
 * own display name — "Wall", never "Solid Wall"/"Great Wall"). Mirrors
 * `personaAvatars.ts`'s `PERSONA_STYLE_TINT` exhaustiveness convention. */
const STYLE_ACCENT: Record<Style, string> = {
  Attacker: ATTACKER_ACCENT,
  Trickster: TRICKSTER_ACCENT,
  Grinder: GRINDER_ACCENT,
  Wall: WALL_ACCENT,
};

export interface PersonaGridProps {
  onSelectPersona: (persona: Persona) => void;
  onSelectCustom: () => void;
}

export function PersonaGrid({ onSelectPersona, onSelectCustom }: PersonaGridProps): ReactElement {
  return (
    // Bottom-nav clearance (mirrors SetupScreen.tsx's root pb-20 sm:pb-4
    // pattern — this is now the Bots page's default setup-phase root).
    <div
      data-testid="bots-persona-grid"
      className="mx-auto flex max-w-2xl flex-col gap-6 p-4 pb-20 sm:pb-4"
    >
      {STYLE_SECTION_ORDER.map((style) => (
        <section key={style} data-testid={`bots-persona-section-${style.toLowerCase()}`}>
          <h2
            className="mb-2 text-sm font-semibold tracking-wide"
            style={{ color: STYLE_ACCENT[style] }}
          >
            {style}
          </h2>
          <div className="grid grid-cols-3 gap-2 sm:grid-cols-6">
            {personasForSection(style).map((persona) => (
              <PersonaCard key={persona.id} persona={persona} onSelect={onSelectPersona} />
            ))}
          </div>
        </section>
      ))}

      <Button
        variant="brand-outline"
        data-testid="bots-persona-custom"
        onClick={onSelectCustom}
        className="h-12 w-full"
      >
        Custom
      </Button>
    </div>
  );
}
