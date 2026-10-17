// @vitest-environment jsdom
/**
 * PersonaEloDisclosurePopover.test.tsx.
 *
 * Covers BOTH calibration states of the ELO disclosure by mocking
 * `PERSONA_CALIBRATION_MEASURED` (false by default, true per test). The
 * shipped (measured) state is also asserted through the real surface in
 * PersonaDetailSurface.test.tsx; here the provisional copy and the measured
 * copy with its ~900 floor line are each pinned independently of the
 * generated value.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';

import { PersonaEloDisclosurePopover } from '../PersonaEloDisclosurePopover';

const measured = vi.hoisted(() => ({ value: false }));

vi.mock('@/generated/personaCalibration', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/generated/personaCalibration')>();
  return {
    ...actual,
    get PERSONA_CALIBRATION_MEASURED() {
      return measured.value;
    },
  };
});

afterEach(() => {
  cleanup();
  measured.value = false;
});

/** Hovers the trigger and waits for the popover body to open. */
async function openDisclosure() {
  vi.useFakeTimers();
  try {
    fireEvent.mouseEnter(screen.getByTestId('persona-elo-disclosure'));
    act(() => {
      vi.advanceTimersByTime(200);
    });
  } finally {
    vi.useRealTimers();
  }
  return waitFor(() => screen.getByTestId('persona-elo-disclosure-content'));
}

function renderPopover(isFloorRung: boolean) {
  render(<PersonaEloDisclosurePopover isFloorRung={isFloorRung} ariaLabel="About this ELO" />);
}

describe('PersonaEloDisclosurePopover — provisional calibration', () => {
  it('says the ELO is provisional and never claims a measurement', async () => {
    renderPopover(false);

    const content = await openDisclosure();
    expect(content.textContent).toContain('provisional');
    expect(content.textContent).not.toContain('measured in bot-vs-engine games');
  });

  it('omits the ~900 floor line even for a floor-rung persona', async () => {
    renderPopover(true);

    const content = await openDisclosure();
    expect(content.textContent).not.toContain('900');
  });
});

describe('PersonaEloDisclosurePopover — popover-open tracking', () => {
  let track: ReturnType<typeof vi.fn>;

  beforeEach(() => {
    track = vi.fn();
    window.umami = { track, identify: vi.fn() };
    window.history.pushState({}, '', '/bots');
  });

  afterEach(() => {
    delete window.umami;
    window.history.pushState({}, '', '/');
  });

  it('sends nothing on render and one popover-open on first open', async () => {
    renderPopover(false);
    expect(track).not.toHaveBeenCalled();

    await openDisclosure();
    expect(track).toHaveBeenCalledTimes(1);
    expect(track).toHaveBeenCalledWith('popover-open', { page: 'bots', target: 'persona-elo-disclosure' });
  });
});

describe('PersonaEloDisclosurePopover — measured calibration', () => {
  it('claims the measurement once the calibration is real', async () => {
    measured.value = true;
    renderPopover(false);

    const content = await openDisclosure();
    expect(content.textContent).toContain('measured in bot-vs-engine games');
    expect(content.textContent).not.toContain('provisional');
  });

  it('appends the ~900 floor acknowledgment for a floor-rung persona', async () => {
    measured.value = true;
    renderPopover(true);

    const content = await openDisclosure();
    expect(content.textContent).toContain('900');
  });

  it('omits the floor acknowledgment for a non-floor persona', async () => {
    measured.value = true;
    renderPopover(false);

    const content = await openDisclosure();
    expect(content.textContent).not.toContain('900');
  });
});
