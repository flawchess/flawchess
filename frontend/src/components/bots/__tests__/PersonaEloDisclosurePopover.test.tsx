// @vitest-environment jsdom
/**
 * PersonaEloDisclosurePopover.test.tsx (Phase 184).
 *
 * Covers BOTH calibration states of the D-08 disclosure. The provisional
 * state is what ships today (`--bootstrap` fit), and is also asserted through
 * the real surface in PersonaDetailSurface.test.tsx. The measured state is
 * exercised here by mocking `PERSONA_CALIBRATION_MEASURED` to true, so the
 * measured copy and the D-06 ~900 floor line are proven to appear the moment
 * a real sweep is fitted — rather than being discovered broken at that point.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
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

describe('PersonaEloDisclosurePopover — measured calibration', () => {
  it('claims the measurement once the calibration is real', async () => {
    measured.value = true;
    renderPopover(false);

    const content = await openDisclosure();
    expect(content.textContent).toContain('measured in bot-vs-engine games');
    expect(content.textContent).not.toContain('provisional');
  });

  it('appends the D-06 ~900 floor acknowledgment for a floor-rung persona', async () => {
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
