import { useState, useCallback } from 'react';
import { Chess } from 'chess.js';
import { ChessBoard } from '@/components/board/ChessBoard';
import { PUZZLES, gradeMove, type Verdict, type AcceptableMove } from './puzzles';
import { QueueView } from './QueueView';
import { SolveView } from './SolveView';
import { FeedbackView } from './FeedbackView';
import { DoneView } from './DoneView';
import { EvalBar } from './EvalBar';

const STARTING_FEN = 'rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1';
const FIRST_FEN = PUZZLES[0]?.fen ?? STARTING_FEN;

type Mode = 'queue' | 'play' | 'done';

interface Attempt {
  verdict: Verdict;
  userSan: string;
  chosenMove: AcceptableMove | null;
}

const stripGlyphs = (san: string): string => san.replace(/[+#!?]/g, '');

function BrandHeader() {
  return (
    <header className="border-b border-border/40 bg-card/40">
      <div className="mx-auto flex w-full max-w-5xl items-center justify-between px-4 py-3 md:px-6">
        <span className="font-brand text-xl text-brand-brown-light">
          Flaw<span className="text-foreground">Chess</span>
        </span>
        <span className="rounded-full bg-brand-brown/15 px-3 py-1 text-sm font-semibold text-brand-brown-light">
          Train · prototype
        </span>
      </div>
    </header>
  );
}

export function TrainSketchPage() {
  const [mode, setMode] = useState<Mode>('queue');
  const [index, setIndex] = useState(0);
  const [position, setPosition] = useState(FIRST_FEN);
  const [lastMove, setLastMove] = useState<{ from: string; to: string } | null>(null);
  const [attempt, setAttempt] = useState<Attempt | null>(null);
  const [results, setResults] = useState<Verdict[]>([]);

  const puzzle = PUZZLES[index];
  const isLast = index === PUZZLES.length - 1;

  const loadPuzzle = useCallback((i: number) => {
    const p = PUZZLES[i];
    setPosition(p?.fen ?? STARTING_FEN);
    setLastMove(null);
    setAttempt(null);
  }, []);

  const startSession = useCallback(() => {
    setIndex(0);
    setResults([]);
    loadPuzzle(0);
    setMode('play');
  }, [loadPuzzle]);

  const onPieceDrop = useCallback(
    (from: string, to: string): boolean => {
      if (attempt !== null) return false; // already answered
      const p = PUZZLES[index];
      if (!p) return false;
      const chess = new Chess(p.fen);
      let move;
      try {
        move = chess.move({ from, to, promotion: 'q' });
      } catch {
        return false;
      }
      if (!move) return false;
      setPosition(chess.fen());
      setLastMove({ from, to });
      const result = gradeMove(p, move.san);
      setAttempt({ verdict: result.verdict, userSan: move.san, chosenMove: result.move });
      setResults((r) => [...r, result.verdict]);
      return true;
    },
    [attempt, index],
  );

  const onGiveUp = useCallback(() => {
    const p = PUZZLES[index];
    if (!p) return;
    const verdict: Verdict = p.kind === 'red_herring' ? 'herring_ok' : 'missed';
    // Play the best move onto the board so the answer is visible.
    if (p.bestSan) {
      const chess = new Chess(p.fen);
      const best = chess.moves({ verbose: true }).find((m) => stripGlyphs(m.san) === stripGlyphs(p.bestSan ?? ''));
      if (best) {
        chess.move(best);
        setPosition(chess.fen());
        setLastMove({ from: best.from, to: best.to });
      }
    }
    setAttempt({ verdict, userSan: '(gave up)', chosenMove: null });
    setResults((r) => [...r, verdict]);
  }, [index]);

  const onNext = useCallback(() => {
    if (isLast) {
      setMode('done');
      return;
    }
    const next = index + 1;
    setIndex(next);
    loadPuzzle(next);
  }, [index, isLast, loadPuzzle]);

  const onRestart = useCallback(() => {
    setIndex(0);
    setResults([]);
    loadPuzzle(0);
    setMode('queue');
  }, [loadPuzzle]);

  return (
    <div data-testid="train-sketch-page" className="flex min-h-screen flex-col bg-background">
      <BrandHeader />
      <main className="mx-auto w-full max-w-5xl flex-1 px-4 py-6 md:px-6">
        {mode === 'queue' ? <QueueView puzzles={PUZZLES} onStart={startSession} /> : null}
        {mode === 'done' ? <DoneView results={results} onRestart={onRestart} /> : null}
        {mode === 'play' && puzzle ? (
          <div className="flex flex-col gap-6 md:flex-row md:items-start md:gap-8">
            <div className="flex items-start gap-3">
              {attempt ? (
                <EvalBar
                  expectedScore={evalBarScore(puzzle, attempt)}
                  caption={evalBarCaption(puzzle, attempt)}
                />
              ) : null}
              <div className="w-full max-w-[400px] flex-1">
                <ChessBoard
                  position={position}
                  onPieceDrop={onPieceDrop}
                  flipped={puzzle.userColor === 'black'}
                  lastMove={lastMove}
                />
              </div>
            </div>
            <div className="flex-1">
              {attempt ? (
                <FeedbackView
                  puzzle={puzzle}
                  verdict={attempt.verdict}
                  userSan={attempt.userSan}
                  chosenMove={attempt.chosenMove}
                  onNext={onNext}
                  isLast={isLast}
                />
              ) : (
                <SolveView puzzle={puzzle} index={index} total={PUZZLES.length} onGiveUp={onGiveUp} />
              )}
            </div>
          </div>
        ) : null}
      </main>
    </div>
  );
}

function evalBarScore(puzzle: (typeof PUZZLES)[number], attempt: Attempt): number {
  if (attempt.verdict === 'solved' && attempt.chosenMove) return attempt.chosenMove.expectedScore;
  if (attempt.verdict === 'missed') return puzzle.acceptable[0]?.expectedScore ?? puzzle.preExpectedScore;
  return puzzle.preExpectedScore;
}

function evalBarCaption(puzzle: (typeof PUZZLES)[number], attempt: Attempt): string {
  if (attempt.verdict === 'solved') return `after ${attempt.userSan}`;
  if (attempt.verdict === 'missed') return puzzle.bestSan ? `best: ${puzzle.bestSan}` : 'missed';
  return 'balanced';
}
