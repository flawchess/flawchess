/**
 * PersonaGrid — the Bots page's default setup view (Phase 183, PERS-01/
 * PERS-04). Renders all 24 personas as a transposed grid (Phase 185): one
 * header row of the 4 style names (`STYLE_SECTION_ORDER`) in their accent
 * colors, then 6 rung rows ascending 800 (top) -> 1800 (bottom)
 * (`RUNGS`/`personasForRung`), 4 `PersonaCard`s per row in style order, no
 * row labels — plus one clearly-visible Custom entry that routes to the
 * unchanged `SetupScreen` (D-01) rather than duplicating any of its
 * controls here.
 */

import type { ReactElement } from 'react';
import { format } from 'date-fns';
import { PersonaCard } from '@/components/bots/PersonaCard';
import { TrainBotBubble } from '@/components/train/TrainBotBubble';
import { Button } from '@/components/ui/button';
import { InfoPopover } from '@/components/ui/info-popover';
import { rosterHost, ROSTER_HUMAN_LIKE_LINE } from '@/lib/botGameCopy';
import { devClockNow, readDevClockOffsetMinutes } from '@/lib/devClock';
import {
  STYLE_SECTION_ORDER,
  RUNGS,
  personasForRung,
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
  /** Phase 185: per-persona-id raw win counts, fetched ONCE by `Bots.tsx`
   * (`useBotPersonaWins`) and prop-drilled here — this component never calls
   * `useQuery` itself (Pattern 3, single-fetch-then-prop-drill), which would
   * break its existing no-`QueryClientProvider` render tests. `undefined`
   * while loading/erroring; each card degrades to its own all-outline
   * zero-state rather than blocking this whole grid. */
  winsByPersona?: Record<string, number>;
}

/**
 * BotWelcomeCard — the roster page's per-persona welcome (D-13,
 * 223-CONTEXT). Replaces the retired `HumanLikeOpponentsCard`'s prose
 * paragraph with the SAME rotating `TrainBotBubble` the /train landing page
 * uses (`TrainStartScreen.tsx`'s `landingHost` call site is the register
 * this bubble matches) — `rosterHost` (`botGameCopy.ts`) shares its epoch
 * and id order with `landingHost`, so the two pages agree on today's host
 * structurally. Phase 223 UAT: no card around it any more — the bubble sits
 * directly on the page like the Train landing's.
 *
 * The bubble renders unconditionally, guests included — they are exactly who
 * needs the explanation most. Phase 223 UAT also retired the player's
 * estimated-rating line that used to sit beneath it: a bot's calibrated ELO
 * is measured against engines, not humans, so putting a human number next to
 * it invited a comparison the two scales do not support.
 *
 * Copy accuracy constraint: 16 of the 24 personas run at `HUMAN_BLEND` (rungs
 * 800-1400), where `selectBotMove` makes exactly ONE Maia policy call and never
 * searches. So the greeting this bubble hosts (and every table in
 * `botGameCopy.ts`) must never claim the bots "calculate" or "think" — it
 * describes human move PREDICTION, which is what all 24 have in common. The
 * style sentence in the popover body stays directional for the same reason:
 * `varianceBonus` and `contempt` only bite on the Light/Deep rungs, while the
 * prior reweighting and opening books tilt every rung.
 */
function BotWelcomeCard(): ReactElement {
  // Rotation day is computed HERE, in the component, from the dev clock —
  // `rosterHost` is a pure module and never reads a clock itself.
  const today = format(devClockNow(readDevClockOffsetMinutes()), 'yyyy-MM-dd');
  const host = rosterHost({ today });

  return (
    <section data-testid="bots-intro" className="space-y-3 text-sm text-muted-foreground">
      <div data-testid="bots-welcome-bubble">
        <TrainBotBubble persona={host.persona} state="prompt" avatarSize="large">
          {/* The info trigger sits inline at the END of the greeting it
              expands (Train landing pattern). `align-middle` keeps the 16px
              glyph on the text baseline when the sentence wraps. */}
          <p>
            {host.copy} {ROSTER_HUMAN_LIKE_LINE}{' '}
            <span className="inline-flex align-middle">
              <InfoPopover ariaLabel="About the bot opponents" testId="bots-intro-info">
                <div className="max-w-xs space-y-2">
                  {/* Non-technical engine explainer, kept in the register
                      of Analysis.tsx's FlawChessInfoTooltip: no "Maia", no
                      "MCTS", no "expectimax". It describes what the engine
                      KNOWS (how players at a rating move), never that the
                      bot calculates — 16 of the 24 personas run no search
                      at all. */}
                  <p>
                    These bots are driven by the FlawChess Engine and play like human players, not
                    like weakened engines. Beyond which move is objectively best, it models how real
                    players at a given rating actually move: which moves they find, and which they
                    miss.
                  </p>
                  <p>
                    So a bot never plays perfectly and then throws in a random blunder, the way a
                    dialed-down engine does. Its mistakes look like the ones you meet online.
                  </p>
                  <p>
                    Each style tilts that further: Attackers press, Tricksters play for
                    complications, Grinders trade down and never resign, Walls keep it quiet.
                  </p>
                </div>
              </InfoPopover>
            </span>
          </p>
        </TrainBotBubble>
      </div>
    </section>
  );
}

export function PersonaGrid({
  onSelectPersona,
  onSelectCustom,
  winsByPersona,
}: PersonaGridProps): ReactElement {
  return (
    // Bottom-nav clearance (mirrors SetupScreen.tsx's root pb-20 sm:pb-4
    // pattern — this is now the Bots page's default setup-phase root).
    <div
      data-testid="bots-persona-grid"
      className="mx-auto flex max-w-2xl flex-col gap-6 p-4 pb-20 sm:pb-4"
    >
      <BotWelcomeCard />

      {/* Single grid-cols-4 container for the header row + all 6 rung body
          rows, so columns align exactly and row/column gaps stay uniform
          (8px, per UI-SPEC) — separate from the outer flex column's gap-6.
          Header cells auto-flow into row 1; RUNGS.flatMap(personasForRung)
          fills the remaining rows rung-major (800 top -> 1800 bottom), no
          row labels (locked decision). */}
      <div className="grid grid-cols-4 gap-2">
        {STYLE_SECTION_ORDER.map((style) => (
          <div
            key={style}
            data-testid={`bots-persona-header-${style.toLowerCase()}`}
            className="text-center text-sm font-semibold tracking-wide"
            style={{ color: STYLE_ACCENT[style] }}
          >
            {style}
          </div>
        ))}
        {RUNGS.flatMap((rung) => personasForRung(rung)).map((persona) => (
          <PersonaCard
            key={persona.id}
            persona={persona}
            onSelect={onSelectPersona}
            winsForPersona={winsByPersona?.[persona.id]}
          />
        ))}
      </div>

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
