// @vitest-environment jsdom
/**
 * TrainBotBubble.test.tsx — Phase 222 Plan 01 Task 2 (D-07).
 *
 * The presentational contract: avatar (real-art vs emoji fallback), name,
 * actions slot, testids, and `data-state`/`data-nudge`. Asserts the nudge
 * through the copy swap and the `data-nudge` attribute, never through the
 * animation class (RESEARCH Finding G / Pitfall 5) — an animation-class
 * assertion would be environment-dependent on whether `window.matchMedia`
 * is stubbed, which this isolated component test deliberately does not do.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, fireEvent, render, screen } from '@testing-library/react';
import { TrainBotBubble } from '@/components/train/TrainBotBubble';
import { TrainBotStepper } from '@/components/train/TrainBotStepper';
import { PERSONA_REGISTRY } from '@/lib/personas/personaRegistry';

afterEach(() => {
  cleanup();
});

const PERSONA = PERSONA_REGISTRY['wall-1800']; // Hilda — has curated art

describe('TrainBotBubble', () => {
  it('renders the persona name and avatar, and the copy children', () => {
    render(
      <TrainBotBubble persona={PERSONA} state="prompt">
        Is there only one good move, or several?
      </TrainBotBubble>,
    );

    expect(screen.getByTestId('train-bot-name').textContent).toBe(PERSONA.name);
    expect(screen.getByTestId('train-bot-copy').textContent).toBe(
      'Is there only one good move, or several?',
    );
    expect(screen.getByTestId('train-bot-avatar')).not.toBeNull();
  });

  it('renders the real-art <img> when resolveAvatarSrc resolves', () => {
    render(
      <TrainBotBubble persona={PERSONA} state="prompt">
        copy
      </TrainBotBubble>,
    );

    const avatar = screen.getByTestId('train-bot-avatar');
    const img = avatar.querySelector('img');
    expect(img).not.toBeNull();
    expect(img?.getAttribute('alt')).toBe('');
    expect(img?.getAttribute('loading')).toBe('lazy');
  });

  it('renders the emoji fallback when no real art resolves', () => {
    // Mirrors PersonaCard.test.tsx's backstop: an id the assets glob cannot
    // match forces resolveAvatarSrc to undefined.
    const personaNoArt = { ...PERSONA, id: 'no-such-persona' as typeof PERSONA.id, avatarSrc: undefined };
    render(
      <TrainBotBubble persona={personaNoArt} state="prompt">
        copy
      </TrainBotBubble>,
    );

    const avatar = screen.getByTestId('train-bot-avatar');
    expect(avatar.querySelector('img')).toBeNull();
    expect(avatar.textContent).toContain(PERSONA.avatarEmoji);
  });

  it('renders the actions slot inside the bubble, below the copy', () => {
    render(
      <TrainBotBubble persona={PERSONA} state="prompt" actions={<button type="button">Only one</button>}>
        copy
      </TrainBotBubble>,
    );

    expect(screen.getByRole('button', { name: 'Only one' })).not.toBeNull();
  });

  it('omits the actions row entirely when no actions are given', () => {
    const { container } = render(
      <TrainBotBubble persona={PERSONA} state="move">
        copy
      </TrainBotBubble>,
    );

    expect(container.querySelectorAll('button')).toHaveLength(0);
  });

  // Plan 06 UAT (SC1 during the intro): `resolveBubbleState` ranks `intro`
  // above `drop-nudge`, so a drop while Hilda's guess step is up keeps the
  // intro copy — the bubble must still pulse (plan 04: "nudges the bubble
  // without destroying the current intro step"). No matchMedia stub in this
  // file, so `prefersReducedMotion()` is false and the class is observable.
  it('pulses on an intro-state nudge without the nudge border or data-nudge', () => {
    const { container } = render(
      <TrainBotBubble persona={PERSONA} state="intro" nudgeNonce={1}>
        intro copy
      </TrainBotBubble>,
    );

    const box = container.querySelector('.animate-train-bubble-nudge');
    expect(box).not.toBeNull();
    expect(screen.getByTestId('train-bot-bubble').getAttribute('data-nudge')).toBeNull();
    expect(screen.getByTestId('train-bot-copy').textContent).toBe('intro copy');
  });

  it('does not pulse on the intro before any drop (nudgeNonce 0)', () => {
    const { container } = render(
      <TrainBotBubble persona={PERSONA} state="intro" nudgeNonce={0}>
        intro copy
      </TrainBotBubble>,
    );

    expect(container.querySelector('.animate-train-bubble-nudge')).toBeNull();
  });

  it('carries data-state matching the state prop', () => {
    render(
      <TrainBotBubble persona={PERSONA} state="grading">
        copy
      </TrainBotBubble>,
    );

    expect(screen.getByTestId('train-bot-bubble').getAttribute('data-state')).toBe('grading');
  });

  it('carries data-nudge="true" only in the drop-nudge state', () => {
    render(
      <TrainBotBubble persona={PERSONA} state="drop-nudge">
        Decide first, then move.
      </TrainBotBubble>,
    );

    expect(screen.getByTestId('train-bot-bubble').getAttribute('data-nudge')).toBe('true');
  });

  it('omits data-nudge in every other state', () => {
    render(
      <TrainBotBubble persona={PERSONA} state="prompt">
        copy
      </TrainBotBubble>,
    );

    expect(screen.getByTestId('train-bot-bubble').getAttribute('data-nudge')).toBeNull();
  });

  it('re-keys on nudgeNonce so a repeated nudge remounts the bubble element (RESEARCH Pitfall 3)', () => {
    const { rerender } = render(
      <TrainBotBubble persona={PERSONA} state="drop-nudge" nudgeNonce={1}>
        Decide first, then move.
      </TrainBotBubble>,
    );
    const firstNode = screen.getByTestId('train-bot-copy').parentElement;

    rerender(
      <TrainBotBubble persona={PERSONA} state="drop-nudge" nudgeNonce={2}>
        Decide first, then move.
      </TrainBotBubble>,
    );
    const secondNode = screen.getByTestId('train-bot-copy').parentElement;

    // A bumped `key` forces React to unmount+remount rather than patch in
    // place, so the two DOM nodes are NOT the same reference — this is what
    // lets a repeated nudge replay its pulse animation.
    expect(secondNode).not.toBe(firstNode);
  });
});

// ─── TrainBotStepper (Phase 222 Plan 01 Task 3) ────────────────────────────

describe('TrainBotStepper', () => {
  it('renders a Next button on every step except the last, calling onNext when clicked', () => {
    const onNext = vi.fn();
    render(
      <TrainBotStepper stepCount={3} step={0} onNext={onNext} lastControl={<span>done</span>}>
        step 0 copy
      </TrainBotStepper>,
    );

    expect(screen.getByText('step 0 copy')).not.toBeNull();
    const next = screen.getByTestId('btn-train-bot-step-next');
    expect(screen.queryByText('done')).toBeNull();
    fireEvent.click(next);
    expect(onNext).toHaveBeenCalledTimes(1);
  });

  it('renders lastControl instead of Next on the final step', () => {
    render(
      <TrainBotStepper stepCount={3} step={2} onNext={vi.fn()} lastControl={<span>done</span>}>
        step 2 copy
      </TrainBotStepper>,
    );

    expect(screen.getByText('step 2 copy')).not.toBeNull();
    expect(screen.getByText('done')).not.toBeNull();
    expect(screen.queryByTestId('btn-train-bot-step-next')).toBeNull();
  });

  it('never renders the TrainLineStepper testids', () => {
    render(
      <TrainBotStepper stepCount={2} step={0} onNext={vi.fn()} lastControl={<span>done</span>}>
        copy
      </TrainBotStepper>,
    );

    expect(screen.queryByTestId('btn-train-step-prev')).toBeNull();
    expect(screen.queryByTestId('btn-train-step-next')).toBeNull();
  });
});
