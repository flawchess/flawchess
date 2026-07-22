// @vitest-environment jsdom
/**
 * PersonaDetailSurface.test.tsx (Phase 183 Plan 04).
 *
 * @sentry/react is mocked (its ESM module namespace is not configurable) —
 * `botPersonaSetupSettings.ts` calls `Sentry.captureException` on corrupt
 * localStorage, which none of these tests exercise, but the import must
 * resolve. jsdom supplies a real `localStorage`.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { act, cleanup, fireEvent, render, screen, waitFor } from '@testing-library/react';

import { PersonaDetailSurface } from '../PersonaDetailSurface';
import { PERSONA_REGISTRY } from '@/lib/personas/personaRegistry';
import { PERSONA_CALIBRATION_MEASURED } from '@/generated/personaCalibration';
import { BOT_STYLE_BUNDLES } from '@/lib/engine/botStyleBundles';
import {
  writePersonaSetupSettings,
  BOT_PERSONA_SETUP_SETTINGS_KEY_PREFIX,
} from '@/lib/personas/botPersonaSetupSettings';
import type { BotGameSettings } from '@/hooks/useBotGame';

vi.mock('@sentry/react', () => ({ captureException: vi.fn() }));

beforeEach(() => {
  localStorage.clear();
});

afterEach(() => {
  cleanup();
});

const PERSONA = PERSONA_REGISTRY['grinder-1200'];
const OWNER_KEY = 'user@example.com';

function renderSurface(
  overrides: Partial<Parameters<typeof PersonaDetailSurface>[0]> = {},
) {
  const onOpenChange = vi.fn();
  const onStart = vi.fn();
  render(
    <PersonaDetailSurface
      persona={PERSONA}
      ownerKey={OWNER_KEY}
      open={true}
      onOpenChange={onOpenChange}
      onStart={onStart}
      {...overrides}
    />,
  );
  return { onOpenChange, onStart };
}

describe('PersonaDetailSurface — rendering', () => {
  it('shows the bio, color chips, TC chips, and a single Play button', () => {
    renderSurface();

    expect(screen.getByTestId('persona-detail-bio').textContent).toBe(PERSONA.bio);
    expect(screen.getByTestId('persona-color-white')).toBeTruthy();
    expect(screen.getByTestId('persona-color-black')).toBeTruthy();
    expect(screen.getByTestId('persona-color-random')).toBeTruthy();
    expect(screen.getByTestId('persona-tc-10-0')).toBeTruthy();
    expect(screen.getByTestId('btn-persona-play')).toBeTruthy();
  });

  it('renders no ELO/strength picker — display-only calibrated ELO + style text only', () => {
    renderSurface();

    expect(screen.getByTestId('persona-detail-meta').textContent).toBe(
      `${PERSONA.style} · ${PERSONA.calibratedLabel}`,
    );
    expect(screen.queryByTestId('setup-elo')).toBeNull();
    expect(screen.queryByRole('slider')).toBeNull();
  });

  it('mounts the D-08 ELO disclosure popover trigger for every persona', () => {
    renderSurface();

    expect(screen.getByTestId('persona-elo-disclosure')).toBeTruthy();
  });

  it('returns null (renders nothing) when persona is null', () => {
    const { container } = render(
      <PersonaDetailSurface
        persona={null}
        ownerKey={OWNER_KEY}
        open={true}
        onOpenChange={vi.fn()}
        onStart={vi.fn()}
      />,
    );
    expect(container.innerHTML).toBe('');
  });

  it('defaults color/TC to DEFAULT_PERSONA_SETUP_SETTINGS when nothing is persisted', () => {
    renderSurface();

    expect(screen.getByTestId('persona-color-random').getAttribute('aria-pressed')).toBe('true');
    expect(screen.getByTestId('persona-tc-10-0').getAttribute('aria-pressed')).toBe('true');
  });

  it('defaults color/TC to the persisted last-used values when present', () => {
    writePersonaSetupSettings(OWNER_KEY, { colorPreference: 'black', tcLabel: '5+3' });

    renderSurface();

    expect(screen.getByTestId('persona-color-black').getAttribute('aria-pressed')).toBe('true');
    expect(screen.getByTestId('persona-tc-5-3').getAttribute('aria-pressed')).toBe('true');
  });
});

describe('PersonaDetailSurface — Play builds the pinned BotGameSettings (PERS-02)', () => {
  it('builds settings with the pinned botElo/blend/personaId, the by-reference style, and calls onStart exactly once', () => {
    const { onStart, onOpenChange } = renderSurface();

    fireEvent.click(screen.getByTestId('persona-color-white'));
    fireEvent.click(screen.getByTestId('persona-tc-5-3'));
    fireEvent.click(screen.getByTestId('btn-persona-play'));

    expect(onStart).toHaveBeenCalledTimes(1);
    const settings = onStart.mock.calls[0]?.[0] as BotGameSettings;
    expect(settings.botElo).toBe(PERSONA.botElo);
    expect(settings.blend).toBe(PERSONA.blend);
    expect(settings.personaId).toBe(PERSONA.id);
    // Reference identity, not a clone (Pitfall 4).
    expect(settings.style).toBe(BOT_STYLE_BUNDLES[PERSONA.style]);
    expect(settings.userColor).toBe('white');
    expect(settings.baseSeconds).toBe(300);
    expect(settings.incrementSeconds).toBe(3);
    expect(onOpenChange).toHaveBeenCalledWith(false);
  });

  it('resolves an unresolved Random color preference to a concrete color before Play fires (D-12)', () => {
    const { onStart } = renderSurface();
    // Random is the default color preference — do not touch the color chips.
    fireEvent.click(screen.getByTestId('btn-persona-play'));

    const settings = onStart.mock.calls[0]?.[0] as BotGameSettings;
    expect(settings.userColor === 'white' || settings.userColor === 'black').toBe(true);
  });

  it('persists the chosen color/TC preference under the persona settings key on Play', () => {
    renderSurface();

    fireEvent.click(screen.getByTestId('persona-color-black'));
    fireEvent.click(screen.getByTestId('persona-tc-5-3'));
    fireEvent.click(screen.getByTestId('btn-persona-play'));

    const raw = localStorage.getItem(`${BOT_PERSONA_SETUP_SETTINGS_KEY_PREFIX}${OWNER_KEY}`);
    expect(raw).not.toBeNull();
    expect(JSON.parse(raw as string)).toEqual({ colorPreference: 'black', tcLabel: '5+3' });
  });
});

describe('PersonaDetailSurface — D-08/D-06 ELO disclosure popover copy', () => {
  /** Hovers the ELO disclosure trigger and waits for the popover body to open. */
  async function openEloDisclosure() {
    vi.useFakeTimers();
    try {
      const trigger = screen.getByTestId('persona-elo-disclosure');
      fireEvent.mouseEnter(trigger);
      act(() => {
        vi.advanceTimersByTime(200);
      });
    } finally {
      vi.useRealTimers();
    }
    return waitFor(() => screen.getByTestId('persona-elo-disclosure-content'));
  }

  it('a non-floor-rung persona popover does NOT include the floor acknowledgment', async () => {
    renderSurface(); // PERSONA = grinder-1200

    const content = await openEloDisclosure();
    expect(content.textContent).not.toContain('900');
  });

  // The committed calibration is still the `--bootstrap` fit (approx_blitz =
  // rung, ratings NaN), so PERSONA_CALIBRATION_MEASURED is false. These two
  // assertions are the honesty contract: until a real sweep is fitted the
  // popover must not claim a measurement, and must not print the ~900 floor
  // line (which would contradict the visible "~800" label). Both flip to the
  // measured copy automatically when the refit lands — see
  // PersonaEloDisclosurePopover.test.tsx for the measured-state coverage.
  it('withholds the measured claim while the calibration is provisional', async () => {
    renderSurface();

    const content = await openEloDisclosure();
    expect(PERSONA_CALIBRATION_MEASURED).toBe(false);
    expect(content.textContent).toContain('provisional');
    expect(content.textContent).not.toContain('measured in bot-vs-engine games');
  });

  it('withholds the ~900 floor line for a bottom-rung persona while provisional', async () => {
    const floorPersona = PERSONA_REGISTRY['grinder-800'];
    render(
      <PersonaDetailSurface
        persona={floorPersona}
        ownerKey={OWNER_KEY}
        open={true}
        onOpenChange={vi.fn()}
        onStart={vi.fn()}
      />,
    );

    const content = await openEloDisclosure();
    expect(content.textContent).not.toContain('900');
  });
});
