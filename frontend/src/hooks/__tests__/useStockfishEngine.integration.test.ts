// @vitest-environment node
/**
 * Real-WASM integration test: Stockfish 18 lite-single FEN → bestmove.
 *
 * Uses the stockfish package's Node.js entry point (`initEngine`) to boot the
 * real WASM binary in Node — no Worker URL resolution, no @vitest/web-worker
 * (avoided due to known WASM import bug vitest#6118).
 *
 * Confirmed before writing (open question 1 / assumption A2):
 *   node_modules/stockfish/bin/stockfish-18-lite-single.js contains:
 *     `f.print=function(e){f.listener?f.listener(e):console.log(e)}`
 *   → `engine.listener` is the correct output property name in v18.0.8.
 *   → Files live in `bin/` (not `src/` as RESEARCH.md suggested — v18.0.8
 *     changed the package structure; index.js checks `bin/` first, so no
 *     code changes were needed).
 *
 * The callback signature is `cb(err, engine)` (index.js line 48), but we
 * use the cleaner Promise form: `const engine = await initEngine('lite-single')`.
 */

import { describe, it, expect } from 'vitest';

/** Minimal typing for the stockfish Node.js engine object. */
interface StockfishEngine {
  sendCommand: (cmd: string) => void;
  listener: ((line: string) => void) | null;
}

describe('Stockfish WASM integration (node entry point)', () => {
  it(
    'returns bestmove h5f7 for the Scholar-attack mate-in-1 FEN',
    async () => {
      // Dynamic import avoids bundler touching the package (anti-pattern note).
      // The stockfish package exports `initEngine` as its default export.
      const { default: initEngine } = (await import('stockfish')) as {
        default: (path: string) => Promise<StockfishEngine>;
      };

      // Promise form: resolves only after uciok + readyok are processed
      // internally by index.js. The engine is fully ready when this awaits.
      const engine = await initEngine('lite-single');

      // Mate-in-1: after 1.e4 e5 2.Bc4 Nc6 3.Qh5 — Qxf7# (h5f7) is the only mate.
      // Deterministic regardless of eval_cp hardware variance (per project memory).
      const MATE_IN_1_FEN =
        'r1bqkb1r/pppp1ppp/2n2n2/4p2Q/2B1P3/8/PPPP1PPP/RNB1K1NR w KQkq - 4 4';

      const lines: string[] = [];
      let bestmoveLine = '';

      await new Promise<void>((resolve, reject) => {
        const timeout = setTimeout(
          () => reject(new Error('Stockfish WASM timed out after 8 s')),
          8000,
        );

        // Set listener BEFORE sending commands so no output is missed.
        // engine.listener is picked up by the Emscripten print function.
        engine.listener = (line: string) => {
          lines.push(line);
          if (line.startsWith('bestmove')) {
            bestmoveLine = line;
            clearTimeout(timeout);
            resolve();
          }
        };

        engine.sendCommand(`position fen ${MATE_IN_1_FEN}`);
        // 500ms search is more than sufficient for a mate-in-1.
        engine.sendCommand('go movetime 500');
      });

      // Release listener reference so the engine does not retain the callback.
      engine.listener = null;

      // Assert the winning queen capture is returned as bestmove.
      expect(bestmoveLine).toMatch(/^bestmove h5f7/);

      // Assert at least one info line carries both score and pv —
      // confirms eval + pv flow works end-to-end (not just bestmove).
      // For a mate-in-1 the engine reports `score mate 1`, not `score cp`,
      // so we accept either form.
      const evalLine = lines.find(
        (l) =>
          (l.includes('score cp') || l.includes('score mate')) &&
          l.includes(' pv '),
      );
      expect(evalLine).toBeDefined();
    },
    10_000, // 10s: WASM boot (~2–3 s) + 500ms search + 7s buffer
  );
});
