// @vitest-environment jsdom
/**
 * TrainVerdictDetails — the divider block below the verdict (Phase 264 D-08, D-14, AC-10):
 * the "Game move:" line, "Also fine", the return tail, and the look-closer line it replaces.
 */
import { afterEach, describe, expect, it, vi } from 'vitest';
import { cleanup, render, screen } from '@testing-library/react';
import { TrainVerdictDetails } from '@/components/train/TrainVerdictDetails';
import type { TrainVerdictDetailsProps } from '@/components/train/TrainVerdictDetails';
import { NO_GAME_MOVE_HEAD, gameBlunderParts } from '@/lib/gameBlunderSentence';
import type { GameMoveHead } from '@/lib/gameBlunderSentence';
import { verdictClauseParts, verdictCopy } from '@/lib/trainBotCopy';
import type { VerdictClauseInput } from '@/lib/trainBotCopy';
import type { SolveResponse } from '@/types/train';

const LOOK_CLOSER = 'Step through the lines to see why.';

const VERDICT: SolveResponse = {
  correct_guess: false,
  correct_move: false,
  move_quality: 'blunder',
  puzzle_type: 'sharp',
  source: 'sr_item',
  item_status: 'active',
  streak: 0,
  due_date: '2026-07-31',
  session_complete: false,
};

const CLAUSE_INPUT: VerdictClauseInput = {
  puzzleType: 'sharp',
  correctGuess: false,
  moveTier: 'blunder',
  isBest: false,
  fromOwnBlunder: true,
  fromForeignGame: false,
  disagreement: false,
  keySan: null,
};

const GAME_MOVE = gameBlunderParts({
  allowedTactic: { motif: 'fork', depth: 1 },
  missedTactic: { motif: 'pin', depth: 2 },
  typeLine: 'allowed_material',
  facepalmScore: 0.85,
});

/** A head with the given fields over an unscored, unbadged default. */
function head(overrides: Partial<GameMoveHead>): GameMoveHead {
  return { ...NO_GAME_MOVE_HEAD, ...overrides };
}

const SCORED = { facepalmScore: 0.85, facepalmType: 'allowed_loss' } as const;

function renderDetails(overrides: Partial<TrainVerdictDetailsProps> = {}): void {
  render(
    <TrainVerdictDetails
      verdict={VERDICT}
      opening={verdictCopy(0, () => 0)}
      clause={verdictClauseParts(CLAUSE_INPUT)}
      sessionDate="2026-07-27"
      expiresOn="2026-07-28"
      alsoFineSanList=""
      gameMove={[]}
      gameMoveHead={head({ san: 'Qc7', quality: 'blunder' })}
      gameMovePending={false}
      {...overrides}
    />,
  );
}

function extrasTestIds(): (string | null)[] {
  return Array.from(screen.getByTestId('train-verdict-extras').children).map((child) =>
    child.getAttribute('data-testid'),
  );
}

afterEach(cleanup);

describe('TrainVerdictDetails', () => {
  it('with a sentence the look-closer line is not shown, and the line leads the divider block', () => {
    renderDetails({ gameMove: GAME_MOVE, alsoFineSanList: 'Nf3, Qe2' });
    expect(screen.queryByTestId('train-bot-look-closer')).toBeNull();
    expect(screen.getByTestId('train-bot-verdict-line').textContent).not.toContain(LOOK_CLOSER);
    // The line starts with the move and its quality icon, then the parts.
    const line = screen.getByTestId('game-move-line');
    expect(line.firstElementChild?.contains(screen.getByTestId('game-move-san'))).toBe(true);
    expect(screen.getByTestId('game-move-san').textContent).toBe('Qc7');
    expect(screen.getByTestId('game-move-quality').getAttribute('data-quality')).toBe('blunder');
    expect(screen.getByTestId('game-move-quality').getAttribute('data-facepalm')).toBeNull();
    // D-25: the score sentence closes the line.
    expect(line.textContent?.endsWith(': missed pin in 3, allowed fork in 2, loses material. Easy to spot (facepalm score 85%).')).toBe(true);
    expect(line.textContent?.startsWith('Qc7')).toBe(true);
    expect(line.textContent).not.toContain('Game move');
    expect(extrasTestIds()).toEqual(['game-move-line', 'train-bot-return-tail']);
    // D-24: "Also fine" closes the verdict paragraph, above the divider, before any look-closer line.
    const alsoFine = screen.getByTestId('train-reveal-also-fine');
    expect(alsoFine.textContent).toBe('Also fine, e.g. Nf3, Qe2.');
    expect(screen.getByTestId('train-bot-verdict-line').contains(alsoFine)).toBe(true);
  });

  it('the tags keep the strip\'s two colours and the type part the text colour', () => {
    renderDetails({ gameMove: GAME_MOVE });
    const line = screen.getByTestId('game-move-line');
    const missed = line.querySelector<HTMLElement>('[data-part="missed"]');
    const allowed = line.querySelector<HTMLElement>('[data-part="allowed"]');
    const type = line.querySelector<HTMLElement>('[data-part="type"]');
    const score = line.querySelector<HTMLElement>('[data-part="score"]');
    expect(missed?.style.color).not.toBe('');
    expect(allowed?.style.color).not.toBe('');
    expect(missed?.style.color).not.toBe(allowed?.style.color);
    expect(type?.style.color).toBe('');
    expect(score?.style.color).toBe('');
  });

  it('a facepalm blunder gets the "???" glyph, and only a blunder does', () => {
    renderDetails({ gameMove: GAME_MOVE, gameMoveHead: head({ san: 'Ne7', quality: 'blunder', ...SCORED }) });
    expect(screen.getByTestId('game-move-quality').getAttribute('data-facepalm')).toBe('true');
    cleanup();
    renderDetails({ gameMove: GAME_MOVE, gameMoveHead: head({ san: 'Ne7', quality: 'mistake', ...SCORED }) });
    expect(screen.getByTestId('game-move-quality').getAttribute('data-facepalm')).toBeNull();
  });

  it('a scored blunder\'s icon opens the facepalm popover; without score or type it is plain (D-23)', () => {
    renderDetails({ gameMove: GAME_MOVE, gameMoveHead: head({ san: 'Ne7', quality: 'blunder', ...SCORED }) });
    const trigger = screen.getByTestId('train-game-move-facepalm-popover');
    expect(trigger.getAttribute('role')).toBe('button');
    expect(trigger.getAttribute('aria-label')).toBe('Facepalm blunder, facepalm score 85%, allowed loss, what the score means');
    expect(screen.getByTestId('game-move-quality').contains(trigger)).toBe(true);
    // The badge keeps the strip's alignment classes.
    expect(trigger.querySelector('svg')?.getAttribute('class')).toContain('-top-0.5');
    cleanup();
    for (const plain of [
      head({ san: 'Ne7', quality: 'blunder' }),
      head({ san: 'Ne7', quality: 'blunder', facepalmScore: 0.85 }),
      head({ san: 'Ne7', quality: 'blunder', facepalmType: 'allowed_loss' }),
      head({ san: 'Ne7', quality: 'mistake', ...SCORED }),
    ]) {
      renderDetails({ gameMove: GAME_MOVE, gameMoveHead: plain });
      expect(screen.queryByTestId('train-game-move-facepalm-popover')).toBeNull();
      expect(screen.getByTestId('game-move-quality').getAttribute('aria-hidden')).toBe('true');
      cleanup();
    }
  });

  it('a score-only line names the score after the popover badge (D-23)', () => {
    const scoreOnly = gameBlunderParts({ allowedTactic: null, missedTactic: null, typeLine: null, facepalmScore: 0.237 });
    renderDetails({ gameMove: scoreOnly, gameMoveHead: head({ san: 'Ne7', quality: 'blunder', facepalmScore: 0.237, facepalmType: 'missed_win' }) });
    // The badge's glyph reads "??" (23% is below the cut), then the score as the line's only part.
    expect(screen.getByTestId('game-move-line').textContent).toBe('Ne7??: hard to spot (facepalm score 23%).');
    expect(screen.getByTestId('game-move-line').querySelector<HTMLElement>('[data-part="score"]')?.style.color).toBe('');
    expect(screen.getByTestId('train-game-move-facepalm-popover')).toBeTruthy();
    expect(screen.queryByTestId('train-bot-look-closer')).toBeNull();
  });

  it('the icon slot is there, empty, while the move is not graded yet (no re-wrap when it lands)', () => {
    renderDetails({ gameMove: GAME_MOVE, gameMoveHead: head({ san: 'Ne7' }) });
    const slot = screen.getByTestId('game-move-quality');
    expect(slot.className).toContain('size-4');
    expect(slot.childElementCount).toBe(0);
  });

  it('without a SAN the line falls back to the neutral "Game move:" subject', () => {
    renderDetails({ gameMove: GAME_MOVE, gameMoveHead: NO_GAME_MOVE_HEAD });
    expect(screen.getByTestId('game-move-line').textContent).toBe(
      'Game move: missed pin in 3, allowed fork in 2, loses material. Easy to spot (facepalm score 85%).',
    );
    expect(screen.queryByTestId('game-move-quality')).toBeNull();
  });

  it.each<[0 | 1 | 2 | 3, boolean]>([
    [0, true],
    [1, true],
    [2, false],
    [3, false],
  ])('without a sentence the look-closer line shows as before: %i points -> %s', (points, shown) => {
    renderDetails({ opening: verdictCopy(points, () => 0) });
    const lookCloser = screen.queryByTestId('train-bot-look-closer');
    expect(lookCloser !== null).toBe(shown);
    if (shown) expect(lookCloser?.textContent).toBe(LOOK_CLOSER);
    expect(screen.queryByTestId('game-move-line')).toBeNull();
  });

  it('"Also fine" sits in the verdict paragraph before the look-closer line, never below the divider (D-24)', () => {
    renderDetails({ opening: verdictCopy(0, () => 0), alsoFineSanList: 'Nf3, Qe2' });
    const paragraph = screen.getByTestId('train-bot-verdict-line');
    const alsoFine = screen.getByTestId('train-reveal-also-fine');
    const lookCloser = screen.getByTestId('train-bot-look-closer');
    expect(paragraph.contains(alsoFine)).toBe(true);
    expect(alsoFine.compareDocumentPosition(lookCloser) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
    expect(paragraph.textContent?.endsWith('Also fine, e.g. Nf3, Qe2. Step through the lines to see why.')).toBe(true);
    expect(extrasTestIds()).toEqual(['train-bot-return-tail']);
  });

  it('the return tail renders inside the divider block, below the verdict, wording and test id unchanged', () => {
    renderDetails();
    const tail = screen.getByTestId('train-bot-return-tail');
    expect(tail.textContent).toBe('Back in 4 days.');
    expect(screen.getByTestId('train-verdict-extras').contains(tail)).toBe(true);
    expect(screen.getByTestId('train-bot-verdict-line').contains(tail)).toBe(false);
    expect(extrasTestIds()).toEqual(['train-bot-return-tail']);
  });

  it('a herring shows the divider with its tail alone', () => {
    renderDetails({
      verdict: { ...VERDICT, puzzle_type: 'herring', source: 'red_herring', item_status: null, due_date: null, streak: null },
    });
    expect(extrasTestIds()).toEqual(['train-bot-tail']);
    expect(screen.getByTestId('train-bot-tail').textContent).toBe("A red herring, so it won't come back.");
  });

  it('a mastered item keeps its non-promise tail test id', () => {
    renderDetails({ verdict: { ...VERDICT, item_status: 'mastered' } });
    expect(screen.getByTestId('train-bot-tail').textContent).toBe('Two in a row, so this one is retired.');
  });

  it('no source, no Also fine and no line: no divider block at all', () => {
    const legacy = { ...VERDICT } as Partial<SolveResponse>;
    delete legacy.source;
    renderDetails({ verdict: legacy as SolveResponse });
    expect(screen.queryByTestId('train-verdict-extras')).toBeNull();
  });

  it('while the reveal loads the line\'s slot is reserved and the look-closer line waits', () => {
    renderDetails({ gameMovePending: true });
    expect(extrasTestIds()).toEqual(['game-move-line-placeholder', 'train-bot-return-tail']);
    expect(screen.getByTestId('game-move-line-placeholder').className).toContain('invisible');
    // Not shown yet: the line may replace it, and showing it first would make it flash.
    expect(screen.queryByTestId('train-bot-look-closer')).toBeNull();
    expect(screen.getByTestId('train-bot-verdict-line').textContent).not.toContain(LOOK_CLOSER);
  });

  describe('the height latch (D-24/D-25 review fixes)', () => {
    let height = 0;
    const callbacks: ResizeObserverCallback[] = [];
    const fireResizeObservers = (): void => {
      for (const callback of callbacks) callback([], {} as ResizeObserver);
    };

    function latchRoot(): HTMLElement {
      // The body's root: the verdict paragraph sits in a flow-root div inside it.
      const root = screen.getByTestId('train-bot-verdict-line').parentElement?.parentElement;
      if (!root) throw new Error('no latch root');
      return root;
    }

    function installStubs(): void {
      callbacks.length = 0;
      vi.stubGlobal(
        'ResizeObserver',
        class {
          constructor(callback: ResizeObserverCallback) {
            callbacks.push(callback);
          }
          observe(): void {}
          disconnect(): void {}
        },
      );
      vi.spyOn(HTMLElement.prototype, 'offsetHeight', 'get').mockImplementation(() => height);
    }

    afterEach(() => {
      vi.unstubAllGlobals();
      vi.restoreAllMocks();
    });

    it('only grows during a verdict: a shorter body keeps the taller min-height', () => {
      installStubs();
      height = 171;
      renderDetails({ alsoFineSanList: 'Qe3' });
      fireResizeObservers();
      expect(latchRoot().style.minHeight).toBe('171px');
      // The live "Also fine" list crosses a line break, then drops back.
      height = 190;
      fireResizeObservers();
      expect(latchRoot().style.minHeight).toBe('190px');
      height = 171;
      fireResizeObservers();
      expect(latchRoot().style.minHeight).toBe('190px');
    });

    it('a window resize re-measures at the new width instead of leaving the body unlatched', () => {
      installStubs();
      height = 190;
      renderDetails();
      fireResizeObservers();
      height = 150;
      window.dispatchEvent(new Event('resize'));
      expect(latchRoot().style.minHeight).toBe('150px');
    });
  });
});
