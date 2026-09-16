// @vitest-environment jsdom
/**
 * useBotGameVoice unit tests (Phase 223, BOTVOICE-01/02/03).
 *
 * Behaviors verified:
 * 1. The game-start greeting fires once on a live, fresh (initialPly 0) game.
 * 2. It does NOT fire on a resumed game (initialPly > 0).
 * 3. `onMoveCommitted` clears the line when the mover is the user.
 * 4. `onMoveCommitted` leaves the line untouched when the mover is the bot.
 * 5. A graded swing FOR the bot (both establishing and reportable calls)
 *    produces the earned-tease key.
 * 5b. Phase 223 UAT, the regret latch: a swing AGAINST the bot stays silent
 *    on the bot's own move, then resolves as punished-mistake when the
 *    player captures, as got-away when the bot's next move recovers, and as
 *    nice-move when it does not.
 * 6. An adjacency violation (no prior baseline) produces nothing.
 * 7. Pacing suppresses a second non-terminal line fired too soon after the
 *    first.
 * 8. An outcome transition produces the terminal key with NO graded-score
 *    callback ever fired.
 * 9. A draw offer produces its key immediately, with no grade involved.
 *
 * The `'player-threat'` cases that used to sit at 7-8 were retired in Phase
 * 223 UAT along with the arm and its `lib/botThreat.ts` detector — see
 * `lib/botLineTrigger.ts`'s file header for why. The hook no longer reads the
 * board at all, which is why `onMoveCommitted` takes two arguments here.
 */
import { describe, it, expect } from 'vitest';
import { renderHook } from '@testing-library/react';
import { act } from 'react';
import type { Move } from 'chess.js';
import type { MoverColor } from '@/lib/liveFlaw';
import type { BotGameOutcome } from '@/lib/botGameEnd';
import { useBotGameVoice } from '../useBotGameVoice';

const USER_COLOR: MoverColor = 'white';
const BOT_COLOR: MoverColor = 'black';

/** A minimal chess.js `Move` fixture — only `.captured` is read by the hook. */
function move(captured?: 'p' | 'n' | 'b' | 'r' | 'q'): Move {
  return { captured } as unknown as Move;
}

describe('useBotGameVoice', () => {
  it('fires the game-start greeting once on a live, fresh game', () => {
    const { result } = renderHook(() =>
      useBotGameVoice({
        userColor: USER_COLOR,
        initialPly: 0,
        live: true,
        botDrawOffer: false,
        outcome: null,
      }),
    );
    expect(result.current.botLine).toBe('game-start');
  });

  it('does not greet a resumed game (initialPly > 0)', () => {
    const { result } = renderHook(() =>
      useBotGameVoice({
        userColor: USER_COLOR,
        initialPly: 12,
        live: true,
        botDrawOffer: false,
        outcome: null,
      }),
    );
    expect(result.current.botLine).toBeNull();
  });

  it('does not greet while not yet live, then greets once confirmLive/live flips true', () => {
    const { result, rerender } = renderHook(
      ({ live }: { live: boolean }) =>
        useBotGameVoice({
          userColor: USER_COLOR,
          initialPly: 0,
          live,
          botDrawOffer: false,
          outcome: null,
        }),
      { initialProps: { live: false } },
    );
    expect(result.current.botLine).toBeNull();

    rerender({ live: true });
    expect(result.current.botLine).toBe('game-start');
  });

  it("clears the line when the player's own move is committed", () => {
    const { result } = renderHook(() =>
      useBotGameVoice({
        userColor: USER_COLOR,
        initialPly: 0,
        live: true,
        botDrawOffer: false,
        outcome: null,
      }),
    );
    expect(result.current.botLine).toBe('game-start');

    act(() => {
      result.current.onMoveCommitted(move(), USER_COLOR);
    });
    expect(result.current.botLine).toBeNull();
  });

  it("survives the bot's own move commit — a bot move never clears a line it is about to set", () => {
    const { result } = renderHook(() =>
      useBotGameVoice({
        userColor: USER_COLOR,
        initialPly: 0,
        live: true,
        botDrawOffer: false,
        outcome: null,
      }),
    );
    expect(result.current.botLine).toBe('game-start');

    act(() => {
      result.current.onMoveCommitted(move(), BOT_COLOR);
    });
    expect(result.current.botLine).toBe('game-start');
  });

  it('a graded swing at or beyond the threshold produces the earned-tease key', () => {
    const { result } = renderHook(() =>
      useBotGameVoice({
        userColor: USER_COLOR,
        initialPly: 12,
        live: true,
        botDrawOffer: false,
        outcome: null,
      }),
    );
    expect(result.current.botLine).toBeNull();

    // Player then bot commit, neither capturing, so nothing but the swing
    // arm can fire.
    act(() => {
      result.current.onMoveCommitted(move(), USER_COLOR);
      result.current.onMoveCommitted(move(), BOT_COLOR);
    });

    // First grade establishes the baseline — no prior ply to compare
    // against, so no swing key yet.
    act(() => {
      result.current.onBotMoveGraded(0, 4);
    });
    expect(result.current.botLine).toBeNull();

    // Second grade, exactly one move pair later, with a large positive
    // delta — earned tease.
    act(() => {
      result.current.onBotMoveGraded(400, 6);
    });
    expect(result.current.botLine).toBe('earned-tease');
  });

  it('an adjacency violation (no established baseline) produces nothing', () => {
    const { result } = renderHook(() =>
      useBotGameVoice({
        userColor: USER_COLOR,
        initialPly: 12,
        live: true,
        botDrawOffer: false,
        outcome: null,
      }),
    );

    // A single graded call with no baseline ply recorded yet
    // (lastGradedPlyRef is still null) can never compute a reportable delta,
    // however large the score itself is.
    act(() => {
      result.current.onBotMoveGraded(900, 6);
    });
    expect(result.current.botLine).toBeNull();
  });

  describe('regret latch (Phase 223 UAT)', () => {
    /** Mounts a resumed (non-greeting) game and establishes a grade baseline
     * at ply 4, so the very next grade can produce a reportable pair delta. */
    function renderWithBaseline() {
      const view = renderHook(() =>
        useBotGameVoice({
          userColor: USER_COLOR,
          initialPly: 12,
          live: true,
          botDrawOffer: false,
          outcome: null,
        }),
      );
      act(() => {
        view.result.current.onMoveCommitted(move(), USER_COLOR);
        view.result.current.onMoveCommitted(move(), BOT_COLOR);
      });
      act(() => {
        view.result.current.onBotMoveGraded(0, 4);
      });
      return view;
    }

    it('stays SILENT on the bot\'s own blunder — no spoiler before the player has a move', () => {
      const { result } = renderWithBaseline();
      act(() => {
        result.current.onBotMoveGraded(-400, 6);
      });
      expect(result.current.botLine).toBeNull();
    });

    it('owns up the moment the player captures the hanging piece', () => {
      const { result } = renderWithBaseline();
      act(() => {
        result.current.onBotMoveGraded(-400, 6);
      });
      // The beat the UAT round is about: the reaction lands on the PLAYER's
      // capture, which the engine itself scores as a near-non-event.
      act(() => {
        result.current.onMoveCommitted(move('n'), USER_COLOR);
      });
      expect(result.current.botLine).toBe('punished-mistake');
    });

    it('says got-away when the player misses it and the bot then recovers', () => {
      const { result } = renderWithBaseline();
      act(() => {
        result.current.onBotMoveGraded(-400, 6);
      });
      // Player replies without capturing: the bubble clears, the latch holds.
      act(() => {
        result.current.onMoveCommitted(move(), USER_COLOR);
      });
      expect(result.current.botLine).toBeNull();
      act(() => {
        result.current.onMoveCommitted(move(), BOT_COLOR);
        result.current.onBotMoveGraded(-100, 8);
      });
      expect(result.current.botLine).toBe('got-away');
    });

    it('never claims got-away while the piece is STILL hanging', () => {
      const { result } = renderWithBaseline();
      act(() => {
        result.current.onBotMoveGraded(-400, 6);
      });
      act(() => {
        result.current.onMoveCommitted(move(), USER_COLOR);
      });
      // The bot shuffled something else; the position has not recovered.
      act(() => {
        result.current.onMoveCommitted(move(), BOT_COLOR);
        result.current.onBotMoveGraded(-390, 8);
      });
      expect(result.current.botLine).toBe('nice-move');
    });

    it('does not fire punished-mistake for a capture with no latch outstanding', () => {
      const { result } = renderWithBaseline();
      act(() => {
        result.current.onMoveCommitted(move('p'), USER_COLOR);
      });
      expect(result.current.botLine).toBeNull();
    });
  });

  it('pacing suppresses a second non-terminal line fired too soon after the first', () => {
    const { result } = renderHook(() =>
      useBotGameVoice({
        userColor: USER_COLOR,
        initialPly: 12,
        live: true,
        botDrawOffer: false,
        outcome: null,
      }),
    );

    act(() => {
      result.current.onMoveCommitted(move(), USER_COLOR);
      result.current.onMoveCommitted(move(), BOT_COLOR);
    });
    act(() => {
      result.current.onBotMoveGraded(0, 4); // baseline
    });
    act(() => {
      result.current.onBotMoveGraded(400, 6); // earned-tease, resets pacing to 0
    });
    expect(result.current.botLine).toBe('earned-tease');

    // Only ONE more bot commit (pacing count 1, below
    // BOT_LINE_SWING_SPACING_MOVES) before the next grade, with another
    // swing FOR the bot — must be suppressed.
    act(() => {
      result.current.onMoveCommitted(move(), BOT_COLOR);
    });
    act(() => {
      result.current.onBotMoveGraded(900, 8);
    });
    expect(result.current.botLine).toBe('earned-tease');
  });

  it('an outcome transition produces the terminal key with no graded-score callback ever fired', () => {
    const { result, rerender } = renderHook(
      ({ outcome }: { outcome: BotGameOutcome | null }) =>
        useBotGameVoice({
          userColor: USER_COLOR,
          initialPly: 12,
          live: true,
          botDrawOffer: false,
          outcome,
        }),
      { initialProps: { outcome: null } },
    );
    expect(result.current.botLine).toBeNull();

    rerender({ outcome: { reason: 'checkmate', winner: BOT_COLOR } });
    expect(result.current.botLine).toBe('bot-won');
  });

  it('a draw offer produces its key immediately, with no grade involved', () => {
    const { result, rerender } = renderHook(
      ({ botDrawOffer }: { botDrawOffer: boolean }) =>
        useBotGameVoice({
          userColor: USER_COLOR,
          initialPly: 12,
          live: true,
          botDrawOffer,
          outcome: null,
        }),
      { initialProps: { botDrawOffer: false } },
    );
    expect(result.current.botLine).toBeNull();

    rerender({ botDrawOffer: true });
    expect(result.current.botLine).toBe('draw-offer');
  });
});
