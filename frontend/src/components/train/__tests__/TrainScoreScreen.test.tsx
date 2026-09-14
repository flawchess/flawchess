// @vitest-environment jsdom
/**
 * TrainScoreScreen.test.tsx — Phase 191 Plan 03 Task 1 coverage (PROG-02,
 * D-15, UI-SPEC E8): the fire-once-on-mount green-band confetti burst and its
 * `prefersReducedMotion` guard. No test file existed for this component
 * before this plan (Wave 0 gap) — this is a new file, not an extension.
 *
 * Extended with the per-band result sound, the smaller yellow-band burst, and
 * the badge's reduced-motion animation opt-out.
 *
 * Phase 222 (D-25, SC4): extended again with the score bubble — mocks
 * `useTrainSettings`/`useTrainOnboarding` directly (this suite deliberately
 * stays free of a `QueryClientProvider`, mirroring the existing
 * `useTrainReminderSlot` mock immediately below) rather than reaching for
 * TrainSolveScreen.test.tsx's `trainApi.getSettings` + real-provider pattern.
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import type { ReactElement } from 'react';
import { TrainScoreScreen } from '@/components/train/TrainScoreScreen';
import type { TrainScoreScreenProps } from '@/components/train/TrainScoreScreen';
import type { SolvedResult, TrainSettingsResponse } from '@/types/train';
import type { TrainSessionScore } from '@/lib/trainScore';

// Phase 202 (Task 1 harness fix, Task 3 mutable extension): the reminder slot
// depends on a QueryClientProvider (usePushCapability/useTrainSettings both
// call useQuery), which this suite deliberately stays free of — mocked so
// individual tests can switch between "renders null" (the hidden-slot shape)
// and "renders a stub btn-train-remind-me" (the both-slots shape) without
// re-mocking per test.
//
// Phase 203 Plan 04 UAT round 1: `TrainScoreScreen` now calls
// `useTrainReminderSlot()` directly (not `<TrainReminderButton />`) so it can
// place `control` (the row cell) and `belowRow` (overflow content — error
// copy, iOS instructions, the Android offer, the QR block) in two different
// rows. Both mocks are independently controllable per test.
const reminderSlotMock = vi.fn<() => ReactElement | null>(() => null);
const reminderBelowRowMock = vi.fn<() => ReactElement | null>(() => null);
vi.mock('@/components/train/TrainReminderButton', () => ({
  useTrainReminderSlot: () => ({ control: reminderSlotMock(), belowRow: reminderBelowRowMock() }),
}));

const fireWinConfetti = vi.fn();
const firePartialConfetti = vi.fn();
const prefersReducedMotion = vi.fn<() => boolean>();
const playSound = vi.fn();

vi.mock('@/lib/confetti', () => ({
  fireWinConfetti: (...args: unknown[]) => fireWinConfetti(...args),
  firePartialConfetti: (...args: unknown[]) => firePartialConfetti(...args),
  prefersReducedMotion: () => prefersReducedMotion(),
}));

vi.mock('@/lib/sounds', () => ({
  playSound: (...args: unknown[]) => playSound(...args),
}));

// Phase 222: "already seen" by default (a past timestamp on all three
// onboarding columns) so every PRE-EXISTING test in this file keeps seeing
// the one-liner variant, exactly as it did before the bubble landed — mirrors
// TrainSolveScreen.test.tsx's identical default-fixture rationale (plan 04).
const PAST_TIMESTAMP = '2026-01-01T00:00:00Z';
const SETTINGS_FIXTURE: TrainSettingsResponse = {
  timezone: 'Europe/Zurich',
  weekday_mask: 127,
  puzzles_per_session: 10,
  reminder_enabled: false,
  reminder_hour: 18,
  reminder_intent_at: null,
  intro_seen_at: PAST_TIMESTAMP,
  reveal_walkthrough_seen_at: PAST_TIMESTAMP,
  sr_explained_at: PAST_TIMESTAMP,
  has_mobile_subscription: false,
};
const getSettingsMock = vi.fn<() => { data: TrainSettingsResponse | undefined }>(() => ({
  data: SETTINGS_FIXTURE,
}));
vi.mock('@/hooks/useTrainSettings', () => ({
  useTrainSettings: () => getSettingsMock(),
}));

const stampMock = vi.fn();
vi.mock('@/hooks/useTrainOnboarding', () => ({
  useTrainOnboarding: () => ({ stamp: stampMock, isPending: false }),
}));

const NEXT_SESSION_DATE = '2026-08-01';
const SESSION_DATE = '2026-07-25';

const onDone = vi.fn();

function makeSolvedResult(overrides: Partial<SolvedResult> = {}): SolvedResult {
  return {
    correct_guess: true,
    move_quality: 'good',
    source: 'sr_item',
    item_status: 'active',
    due_date: '2026-07-28',
    ...overrides,
  };
}

function renderScoreScreen(
  score: TrainSessionScore,
  overrides: Partial<TrainScoreScreenProps> = {},
) {
  return render(
    <TrainScoreScreen
      score={score}
      nextSessionDate={NEXT_SESSION_DATE}
      onDone={onDone}
      solvedOutcomes={[]}
      sessionDate={SESSION_DATE}
      expiresOn={NEXT_SESSION_DATE}
      isWarmup={false}
      {...overrides}
    />,
  );
}

describe('TrainScoreScreen', () => {
  beforeEach(() => {
    fireWinConfetti.mockReset();
    firePartialConfetti.mockReset();
    playSound.mockReset();
    prefersReducedMotion.mockReset();
    prefersReducedMotion.mockReturnValue(false);
    onDone.mockReset();
    reminderSlotMock.mockReturnValue(null);
    reminderBelowRowMock.mockReturnValue(null);
    getSettingsMock.mockReset();
    getSettingsMock.mockReturnValue({ data: SETTINGS_FIXTURE });
    stampMock.mockReset();
  });

  afterEach(() => {
    cleanup();
  });

  it('a green-band score fires fireWinConfetti exactly once on mount', () => {
    renderScoreScreen({ total: 20, max: 20 });
    expect(fireWinConfetti).toHaveBeenCalledTimes(1);
  });

  it('a green-band score with prefersReducedMotion true does not fire confetti, and the total/percentage still render', () => {
    prefersReducedMotion.mockReturnValue(true);
    renderScoreScreen({ total: 20, max: 20 });
    expect(fireWinConfetti).not.toHaveBeenCalled();
    expect(screen.getByTestId('train-score-total')).not.toBeNull();
    expect(screen.getByTestId('train-score-percentage')).not.toBeNull();
  });

  // SEED-122: the permanently-disabled "Train again" CTA was removed — it could
  // never enable (no same-day resume path), so it read as broken rather than as
  // a completed session. A pressable "Done" back to the landing replaced it.
  it('renders no Train-again CTA', () => {
    renderScoreScreen({ total: 20, max: 20 });
    expect(screen.queryByTestId('btn-train-again')).toBeNull();
  });

  it('the Done button is enabled and calls onDone once when pressed', () => {
    renderScoreScreen({ total: 20, max: 20 });
    const done = screen.getByTestId('btn-train-done');
    expect((done as HTMLButtonElement).disabled).toBe(false);
    fireEvent.click(done);
    expect(onDone).toHaveBeenCalledTimes(1);
  });

  it('a yellow-band score fires only the smaller partial burst', () => {
    renderScoreScreen({ total: 12, max: 20 });
    expect(fireWinConfetti).not.toHaveBeenCalled();
    expect(firePartialConfetti).toHaveBeenCalledTimes(1);
  });

  it('a red-band score does not fire confetti', () => {
    renderScoreScreen({ total: 4, max: 20 });
    expect(fireWinConfetti).not.toHaveBeenCalled();
    expect(firePartialConfetti).not.toHaveBeenCalled();
  });

  it('a null-band score (max: 0) does not fire confetti and renders no percentage line', () => {
    renderScoreScreen({ total: 0, max: 0 });
    expect(fireWinConfetti).not.toHaveBeenCalled();
    expect(firePartialConfetti).not.toHaveBeenCalled();
    expect(screen.queryByTestId('train-score-percentage')).toBeNull();
    expect(screen.queryByTestId('train-score-badge')).toBeNull();
  });

  it('a re-render with the same props does not fire a second burst', () => {
    const { rerender } = renderScoreScreen({ total: 20, max: 20 });
    expect(fireWinConfetti).toHaveBeenCalledTimes(1);
    rerender(
      <TrainScoreScreen
        score={{ total: 20, max: 20 }}
        nextSessionDate={NEXT_SESSION_DATE}
        onDone={onDone}
        solvedOutcomes={[]}
        sessionDate={SESSION_DATE}
        expiresOn={NEXT_SESSION_DATE}
        isWarmup={false}
      />,
    );
    expect(fireWinConfetti).toHaveBeenCalledTimes(1);
  });

  it.each([
    ['green', { total: 20, max: 20 }, 'game-win'],
    ['yellow', { total: 12, max: 20 }, 'score-partial'],
    ['red', { total: 4, max: 20 }, 'game-loss'],
  ] as const)('a %s-band score plays its result sound exactly once', (_band, score, event) => {
    renderScoreScreen(score);
    expect(playSound).toHaveBeenCalledTimes(1);
    expect(playSound).toHaveBeenCalledWith(event);
  });

  it('a null-band score (max: 0) plays no result sound', () => {
    renderScoreScreen({ total: 0, max: 0 });
    expect(playSound).not.toHaveBeenCalled();
  });

  it('reduced motion suppresses confetti but still plays the result sound', () => {
    prefersReducedMotion.mockReturnValue(true);
    renderScoreScreen({ total: 12, max: 20 });
    expect(firePartialConfetti).not.toHaveBeenCalled();
    expect(playSound).toHaveBeenCalledWith('score-partial');
  });

  it('the badge animates by default and drops the animation class under reduced motion', () => {
    renderScoreScreen({ total: 12, max: 20 });
    expect(screen.getByTestId('train-score-badge').className).toContain(
      'animate-train-score-badge-pop',
    );
    cleanup();

    prefersReducedMotion.mockReturnValue(true);
    renderScoreScreen({ total: 12, max: 20 });
    expect(screen.getByTestId('train-score-badge').className).not.toContain(
      'animate-train-score-badge-pop',
    );
  });

  // Phase 202 Task 3 (D-04, UI-SPEC E2): row hierarchy and ordering.
  describe('the score-screen button row', () => {
    it('with the slot hidden, the row has exactly one element child and it is Done, with flex-1', () => {
      renderScoreScreen({ total: 20, max: 20 });
      const row = screen.getByTestId('train-score-button-row');
      expect(row.children).toHaveLength(1);
      expect(row.children[0]).toBe(screen.getByTestId('btn-train-done'));
      expect(screen.getByTestId('btn-train-done').className).toContain('flex-1');
    });

    it('with the slot present, the row is Remind me first then Done, in that DOM order', () => {
      reminderSlotMock.mockReturnValue(<div data-testid="btn-train-remind-me" />);
      renderScoreScreen({ total: 20, max: 20 });
      const row = screen.getByTestId('train-score-button-row');
      expect(row.children).toHaveLength(2);
      expect(row.children[0]?.getAttribute('data-testid')).toBe('btn-train-remind-me');
      expect(row.children[1]?.getAttribute('data-testid')).toBe('btn-train-done');
    });

    it('Done renders variant="default" (the brand-brown solid fill, per D-04)', () => {
      renderScoreScreen({ total: 20, max: 20 });
      // Asserted via a stable fragment of button.tsx's own "default" variant
      // class string, not by re-implementing the variant map.
      expect(screen.getByTestId('btn-train-done').className).toContain('bg-brand-brown');
    });
  });

  // Phase 203 Plan 04 UAT round 1: overflow content (error copy, iOS
  // instructions, the Android offer, the QR block) never crowds into the
  // cramped two-cell row — it renders on its own full-width line below it.
  describe('below-row overflow content (Plan 04 UAT round 1)', () => {
    it('with no below-row content, only the row itself renders — no extra empty line', () => {
      reminderSlotMock.mockReturnValue(<div data-testid="btn-train-remind-me" />);
      renderScoreScreen({ total: 20, max: 20 });
      expect(screen.queryByTestId('train-reminder-error-line')).toBeNull();
      expect(screen.queryByTestId('train-ios-reminder-instructions')).toBeNull();
    });

    it('the row keeps its two-cell shape (control + Done) even when below-row content is present', () => {
      reminderSlotMock.mockReturnValue(<div data-testid="btn-train-remind-me" />);
      reminderBelowRowMock.mockReturnValue(
        <p data-testid="train-reminder-error-line">Couldn&apos;t turn on reminders. Try again.</p>,
      );
      renderScoreScreen({ total: 20, max: 20 });

      const row = screen.getByTestId('train-score-button-row');
      expect(row.children).toHaveLength(2);
      expect(row.children[0]?.getAttribute('data-testid')).toBe('btn-train-remind-me');
      expect(row.children[1]?.getAttribute('data-testid')).toBe('btn-train-done');
      // The below-row content must NOT be a child of the row itself.
      expect(screen.getByTestId('train-reminder-error-line').closest('[data-testid="train-score-button-row"]')).toBeNull();
    });

    it('below-row content renders after (below) the button row in DOM order', () => {
      reminderSlotMock.mockReturnValue(<div data-testid="btn-train-remind-me" />);
      reminderBelowRowMock.mockReturnValue(
        <p data-testid="train-reminder-error-line">Couldn&apos;t turn on reminders. Try again.</p>,
      );
      renderScoreScreen({ total: 20, max: 20 });

      const row = screen.getByTestId('train-score-button-row');
      const errorLine = screen.getByTestId('train-reminder-error-line');
      expect(row.compareDocumentPosition(errorLine) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    });
  });

  // Phase 203 Plan 04 UAT round 3: the confirmed "Reminders on…" line is
  // non-interactive, so it moves below the row too — `control` is `null`
  // once subscribed, exactly like the hidden-slot shape from this screen's
  // point of view.
  describe('confirmed-state placement — control null, Done alone spans full width (Plan 04 UAT round 3)', () => {
    it('with control null and below-row content present (the confirmed shape), the row has exactly one child — Done — with flex-1, and no dead space beside it', () => {
      reminderSlotMock.mockReturnValue(null);
      reminderBelowRowMock.mockReturnValue(
        <span data-testid="train-reminder-confirmed">Reminders on — 16:00 on your training days</span>,
      );
      renderScoreScreen({ total: 20, max: 20 });

      const row = screen.getByTestId('train-score-button-row');
      expect(row.children).toHaveLength(1);
      expect(row.children[0]).toBe(screen.getByTestId('btn-train-done'));
      expect(screen.getByTestId('btn-train-done').className).toContain('flex-1');
      // The confirmed line itself is outside the row, below it.
      expect(
        screen.getByTestId('train-reminder-confirmed').closest('[data-testid="train-score-button-row"]'),
      ).toBeNull();
    });

    it('the confirmed line renders after (below) the button row in DOM order', () => {
      reminderSlotMock.mockReturnValue(null);
      reminderBelowRowMock.mockReturnValue(
        <span data-testid="train-reminder-confirmed">Reminders on — 16:00 on your training days</span>,
      );
      renderScoreScreen({ total: 20, max: 20 });

      const row = screen.getByTestId('train-score-button-row');
      const confirmedLine = screen.getByTestId('train-reminder-confirmed');
      expect(row.compareDocumentPosition(confirmedLine) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    });
  });

  // Phase 222 (D-04/D-12/D-15/D-16/D-18/D-25, SC4): the score bubble that
  // states what returns and when, before the reminder ask.
  describe('the score bubble (D-25)', () => {
    it('renders BEFORE the button row in the JSX return', () => {
      renderScoreScreen({ total: 20, max: 20 });
      const bubble = screen.getByTestId('train-score-bubble');
      const row = screen.getByTestId('train-score-button-row');
      expect(bubble.compareDocumentPosition(row) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    });

    it('renders no bubble copy while settings is still loading (data === undefined)', () => {
      getSettingsMock.mockReturnValue({ data: undefined });
      renderScoreScreen({ total: 20, max: 20 }, { solvedOutcomes: [makeSolvedResult()] });
      expect(screen.queryByTestId('train-score-bubble-returns')).toBeNull();
      // The bubble chrome (persona/avatar row) still renders — no layout jump.
      expect(screen.getByTestId('train-score-bubble')).not.toBeNull();
    });

    it('sr_explained_at === null with at least one missed SR item renders the full first-completed-session explanation and stamps exactly once', () => {
      getSettingsMock.mockReturnValue({
        data: { ...SETTINGS_FIXTURE, sr_explained_at: null },
      });
      renderScoreScreen(
        { total: 12, max: 20 },
        {
          solvedOutcomes: [
            makeSolvedResult({ correct_guess: false, move_quality: 'wrong', due_date: '2026-07-26' }),
          ],
        },
      );
      const text = screen.getByTestId('train-score-bubble-returns').textContent ?? '';
      expect(text).toContain('Reminders build the habit that makes Train work.');
      expect(stampMock).toHaveBeenCalledTimes(1);
      expect(stampMock).toHaveBeenCalledWith('sr_explained');
    });

    it('BUG FIX (UAT round 5): the full explanation survives the stamp writing sr_explained_at back into the settings cache', () => {
      getSettingsMock.mockReturnValue({
        data: { ...SETTINGS_FIXTURE, sr_explained_at: null },
      });
      const { rerender } = renderScoreScreen(
        { total: 12, max: 20 },
        {
          solvedOutcomes: [
            makeSolvedResult({ correct_guess: false, move_quality: 'wrong', due_date: '2026-07-26' }),
          ],
        },
      );
      expect(stampMock).toHaveBeenCalledTimes(1);
      // The stamp's onSuccess setQueryData: the same hook now reports a stamped row.
      getSettingsMock.mockReturnValue({ data: SETTINGS_FIXTURE });
      rerender(
        <TrainScoreScreen
          score={{ total: 12, max: 20 }}
          nextSessionDate={NEXT_SESSION_DATE}
          onDone={onDone}
          solvedOutcomes={[
            makeSolvedResult({ correct_guess: false, move_quality: 'wrong', due_date: '2026-07-26' }),
          ]}
          sessionDate={SESSION_DATE}
          expiresOn={NEXT_SESSION_DATE}
          isWarmup={false}
        />,
      );
      const text = screen.getByTestId('train-score-bubble-returns').textContent ?? '';
      expect(text).toContain('Reminders build the habit that makes Train work.');
      expect(stampMock).toHaveBeenCalledTimes(1);
    });

    it('sr_explained_at non-null renders the one-liner and never stamps', () => {
      renderScoreScreen(
        { total: 12, max: 20 },
        {
          solvedOutcomes: [
            makeSolvedResult({ correct_guess: false, move_quality: 'wrong', due_date: '2026-07-26' }),
          ],
        },
      );
      const text = screen.getByTestId('train-score-bubble-returns').textContent ?? '';
      expect(text).not.toContain('ordinary puzzles');
      expect(stampMock).not.toHaveBeenCalled();
    });

    it('a warm-up session (is_warmup, no SR items) renders the warm-up variant regardless of sr_explained_at, and stamps nothing', () => {
      getSettingsMock.mockReturnValue({
        data: { ...SETTINGS_FIXTURE, sr_explained_at: null },
      });
      renderScoreScreen(
        { total: 0, max: 0 },
        { isWarmup: true, solvedOutcomes: [] },
      );
      const text = screen.getByTestId('train-score-bubble-returns').textContent ?? '';
      expect(text).toContain('warm-ups');
      expect(text).not.toContain('come back');
      expect(stampMock).not.toHaveBeenCalled();
    });

    it('a session where nothing was missed renders the nothing-missed variant, even on the first completed session', () => {
      getSettingsMock.mockReturnValue({
        data: { ...SETTINGS_FIXTURE, sr_explained_at: null },
      });
      renderScoreScreen(
        { total: 20, max: 20 },
        { solvedOutcomes: [makeSolvedResult({ due_date: '2026-07-26' })] },
      );
      const text = screen.getByTestId('train-score-bubble-returns').textContent ?? '';
      expect(text).toContain('Nothing got away today.');
      // D-12: the full explanation never actually rendered here (the
      // nothing-missed variant won the precedence), so it must not stamp.
      expect(stampMock).not.toHaveBeenCalled();
    });

    it('a mastered outcome is excluded from the "comes back" counts', () => {
      renderScoreScreen(
        { total: 12, max: 20 },
        {
          solvedOutcomes: [
            makeSolvedResult({ item_status: 'mastered', due_date: '2026-06-01' }),
            makeSolvedResult({ due_date: '2026-07-26' }),
          ],
        },
      );
      const text = screen.getByTestId('train-score-bubble-returns').textContent ?? '';
      // Only the one genuinely-active item is counted — the mastered entry
      // never inflates the "comes back" total (D-16).
      expect(text).toContain('1 comes back next session');
    });

    it('renders no position number, game id or ply anywhere in the bubble text', () => {
      renderScoreScreen(
        { total: 12, max: 20 },
        {
          solvedOutcomes: [
            makeSolvedResult({ correct_guess: false, move_quality: 'wrong', due_date: '2026-07-26' }),
          ],
        },
      );
      const text = screen.getByTestId('train-score-bubble-returns').textContent ?? '';
      // The fixture's own would-be identifiers (position/game_id/ply) never
      // appear anywhere in SolvedResult (D-17) or the rendered text (D-18).
      expect(text).not.toMatch(/\bposition\s*\d/i);
      expect(text).not.toMatch(/\bgame\s*(id)?\s*\d/i);
      expect(text).not.toMatch(/\bply\s*\d/i);
    });
  });
});
