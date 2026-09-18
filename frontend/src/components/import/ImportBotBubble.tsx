import { useMemo, type ReactElement } from 'react';
import { Link } from 'react-router';
import { pickBot } from '@/lib/trainBotCopy';
import { TrainBotBubble } from '@/components/train/TrainBotBubble';
import { SignupAskActions } from '@/components/train/SignupAskActions';
import {
  PARTS_BY_VARIANT,
  type BubblePart,
  type ImportBotBubbleVariant,
} from '@/components/import/importBotBubbleCopy';

/**
 * ImportBotBubble: Phase 224 (S-6, D-06; GUESTACT-07). Replaces the Import
 * page's old `Alert`-based guest sign-up prompt with a friendly-bot bubble.
 * Composed exactly like `BotGameDesktopLayout` composes its bubble: the
 * parent (this component) supplies persona, copy and actions;
 * `SignupAskActions` (the actions component) carries no logic of its own.
 *
 * Three variants (224 UAT rounds 1-2: the sign-up CTA on a fresh account was
 * "too early", and registered accounts should get the same tour):
 *
 * - `welcome`: shown to guests AND registered users before their first
 *   completed import. A plain welcome that points at the import cards and,
 *   as a side door, at the bots page. No sign-up ask.
 * - `explore`: shown to registered accounts once a first import has
 *   completed. Points at the tabs that now have data (Games, Train, Bots,
 *   Openings, Endgames). No sign-up ask, no actions.
 * - `signup-ask`: the guest counterpart of `explore`: the same sentence plus
 *   the import-specific payoff (D-06: background analysis of all imported
 *   games) and the sign-up action pair. Shares no sentence with the
 *   score-screen ask (`GUEST_SIGNUP_ASK_SCORE`).
 *
 * This is the FIRST persona appearance outside a game/puzzle context
 * (accepted, S-6). The component reads no profile: the caller (`ImportPage`)
 * picks the variant and decides whether to mount it at all.
 */

function renderParts(parts: readonly BubblePart[]): ReactElement[] {
  return parts.map((part, index) =>
    typeof part === 'string' ? (
      <span key={index}>{part}</span>
    ) : (
      // Internal routes: no data-umami-event here (frontend/CLAUDE.md, the
      // tracker would downgrade the click to a full page reload).
      <Link
        key={index}
        to={part.to}
        className="underline underline-offset-4 hover:text-brand-brown-highlight"
        data-testid={`import-bot-bubble-link-${part.slug}`}
      >
        {part.text}
      </Link>
    ),
  );
}

export interface ImportBotBubbleProps {
  variant: ImportBotBubbleVariant;
}

export function ImportBotBubble({ variant }: ImportBotBubbleProps): ReactElement {
  // ImportPage re-renders on every import-job poll tick (mirrors
  // TrainScoreScreen's identical rationale for pickBot('smart')): without
  // this memo the persona would recast mid-read on every poll.
  const bot = useMemo(() => pickBot('friendly'), []);

  return (
    <div data-testid="import-bot-bubble" data-variant={variant}>
      {/* `state="prompt"` is the neutral, non-pulsing kind (DISCRETION);
          `verdict` is the score screen's own state and carries the wrong
          connotation on an import page. */}
      <TrainBotBubble
        persona={bot}
        state="prompt"
        actions={variant === 'signup-ask' ? <SignupAskActions source="import-promo" /> : undefined}
      >
        {renderParts(PARTS_BY_VARIANT[variant])}
      </TrainBotBubble>
    </div>
  );
}
