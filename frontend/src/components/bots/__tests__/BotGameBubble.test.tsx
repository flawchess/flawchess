// @vitest-environment jsdom
/**
 * BotGameBubble.test.tsx — Phase 223 Plan 01 Task 2 (BOTVOICE-01/02,
 * Wave 0). Renders with a real persona from `PERSONA_REGISTRY` (not a
 * fabricated object) so the avatar idiom is exercised for real; the copy
 * assertion compares against `botLineCopy`'s own return, never a
 * hard-coded string, so re-authored copy can never break this file.
 */
import { afterEach, describe, expect, it } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import type { PersonaId } from '@/lib/personas/personaRegistry';
import { PERSONA_REGISTRY } from '@/lib/personas/personaRegistry';
import { botLineCopy, BOT_LINE_MAX_CHARS } from '@/lib/botGameCopy';
import { BotGameBubble } from '../BotGameBubble';

const PERSONA = PERSONA_REGISTRY['attacker-800'];

/** Every real registry persona has curated webp art (see
 * `frontend/src/assets/personas/*.webp`), so the emoji-fallback branch needs
 * a persona whose id resolves to no art — a fabricated id, cast the same
 * way a stale/removed id would arrive at runtime. */
const PERSONA_WITH_NO_ART = { ...PERSONA, id: 'attacker-9999' as unknown as PersonaId };

afterEach(() => {
  cleanup();
});

describe('BotGameBubble — null persona', () => {
  it('renders nothing at all for a null persona', () => {
    const { container } = render(<BotGameBubble persona={null} line={null} />);
    expect(container.firstChild).toBeNull();
  });
});

describe('BotGameBubble — avatar', () => {
  it('renders the real-art <img> when art resolves', () => {
    render(<BotGameBubble persona={PERSONA} line={null} />);
    const avatar = screen.getByTestId('bot-game-avatar');
    expect(avatar.querySelector('img')).toBeTruthy();
  });

  it('renders the species emoji fallback when no art resolves', () => {
    render(<BotGameBubble persona={PERSONA_WITH_NO_ART} line={null} />);
    const avatar = screen.getByTestId('bot-game-avatar');
    expect(avatar.querySelector('img')).toBeNull();
    expect(avatar.textContent).toBe(PERSONA.avatarEmoji);
  });
});

describe('BotGameBubble — copy', () => {
  it("renders the authored copy for the supplied key and persona, byte-identical to botLineCopy's return", () => {
    render(<BotGameBubble persona={PERSONA} line="game-start" />);
    expect(screen.getByTestId('bot-game-bubble-copy').textContent).toBe(
      botLineCopy('game-start', PERSONA.id),
    );
  });

  it("keeps this persona's game-start line within the phone copy budget (BOT_LINE_MAX_CHARS)", () => {
    // The exhaustive-over-every-persona budget test is Wave 0's
    // `botGameCopy.test.ts` (a later plan); this is the single-persona
    // sanity check that also gives `BOT_LINE_MAX_CHARS` a real consumer in
    // this plan (knip flags an export with zero readers).
    expect(botLineCopy('game-start', PERSONA.id).length).toBeLessThanOrEqual(BOT_LINE_MAX_CHARS);
  });

  it('keeps the copy node mounted with the SAME height classes when the line is null (no collapsing slot)', () => {
    const { unmount } = render(<BotGameBubble persona={PERSONA} line="game-start" />);
    const withLineClassName = screen.getByTestId('bot-game-bubble-copy').className;
    unmount();

    render(<BotGameBubble persona={PERSONA} line={null} />);
    const withoutLineNode = screen.getByTestId('bot-game-bubble-copy');
    expect(withoutLineNode.textContent).toBe('');
    expect(withoutLineNode.className).toBe(withLineClassName);
  });
});

describe('BotGameBubble — silent state (Phase 223 UAT)', () => {
  it('hides the bubble box (invisible, still laid out) when there is no line and no actions', () => {
    render(<BotGameBubble persona={PERSONA} line={null} />);
    expect(screen.getByTestId('bot-game-bubble-box').className).toContain('invisible');
    // The avatar stays visible as the bot's presence beside the board.
    expect(screen.getByTestId('bot-game-avatar')).toBeTruthy();
  });

  it('shows the box when a line is live', () => {
    render(<BotGameBubble persona={PERSONA} line="game-start" />);
    expect(screen.getByTestId('bot-game-bubble-box').className).not.toContain('invisible');
  });

  it('shows the box for actions alone (a live draw offer with no line)', () => {
    render(<BotGameBubble persona={PERSONA} line={null} actions={<button>Accept</button>} />);
    expect(screen.getByTestId('bot-game-bubble-box').className).not.toContain('invisible');
  });
});

describe('BotGameBubble — actions slot', () => {
  it('renders the actions slot inside the bubble when supplied', () => {
    render(
      <BotGameBubble persona={PERSONA} line={null} actions={<button>Accept</button>} />,
    );
    expect(screen.getByRole('button', { name: 'Accept' })).toBeTruthy();
  });

  it('omits the actions row entirely when not supplied', () => {
    render(<BotGameBubble persona={PERSONA} line={null} />);
    expect(screen.queryByRole('button')).toBeNull();
  });
});

describe('BotGameBubble — type-size floor', () => {
  it('never uses sub-text-sm font-size utilities anywhere in the bubble', () => {
    render(<BotGameBubble persona={PERSONA} line="game-start" />);
    expect(screen.getByTestId('bot-game-bubble').innerHTML).not.toContain('text-xs');
  });
});
