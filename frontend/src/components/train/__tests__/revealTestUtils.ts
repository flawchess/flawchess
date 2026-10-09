/**
 * Shared helpers for the Train reveal tests (Phase 237).
 *
 * The reveal used to be found through its line-card testids and then the
 * Your-call card; both are gone (the card lives inside the verdict strip /
 * bubble, collapsed on phones). The root `train-reveal` testid is the one stable
 * sentinel for "the reveal is on screen".
 */
import { screen, waitFor } from '@testing-library/react';

/** Resolves once the reveal panel is mounted (the solve verdict landed). */
export async function waitForReveal(): Promise<HTMLElement> {
  return waitFor(() => screen.getByTestId('train-reveal'));
}
