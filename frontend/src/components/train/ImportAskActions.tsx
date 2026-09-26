import type { ReactElement } from 'react';
import { Link } from 'react-router';
import { Button } from '@/components/ui/button';
import { TRAIN_BUTTON_CLASS } from '@/components/train/buttonStyles';
import { trackEvent } from '@/lib/analytics';

/**
 * ImportAskActions: quick task 260926-8p5. The "Import games" action rendered
 * into `TrainBotBubble`'s `actions` slot for a REGISTERED account with zero
 * imported games, on the Train landing bubble and the warm-up score bubble.
 *
 * Why it exists: every zero-game Train surface already SAID "Import your
 * games", but the only clickable import button lived in the `no_material`
 * empty state, which a zero-game account never reaches (sharp fillers always
 * compose a session). Prod 2026-09-25: ~2/3 of first-time Train users with no
 * games solved nothing, vs ~1/4 of users with games.
 *
 * Guests keep `SignupAskActions` instead: sign-up is their funnel lever.
 *
 * Attribution goes through `trackEvent` in onClick, never `data-umami-event`:
 * this is an internal react-router Link, and the attribute would downgrade
 * the click into a full page reload (frontend/CLAUDE.md).
 */

export type ImportAskSource = 'train-landing' | 'train-score';

export interface ImportAskActionsProps {
  source: ImportAskSource;
}

export function ImportAskActions({ source }: ImportAskActionsProps): ReactElement {
  return (
    <Button variant="default" asChild className={TRAIN_BUTTON_CLASS}>
      <Link
        to="/library/import"
        data-testid={`btn-import-games-${source}`}
        onClick={() => trackEvent('import-cta', { source })}
      >
        Import games
      </Link>
    </Button>
  );
}
