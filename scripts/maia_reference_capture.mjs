#!/usr/bin/env node
/**
 * maia_reference_capture.mjs — capture client-side (onnxruntime-web) Maia-3
 * `maia_prob` values for a set of positions, to seed the backend parity corpus
 * (tests/fixtures/maia_parity/corpus.json).
 *
 * This is the INDEPENDENT client-equivalent reference for Phase 174's D-01/D-02
 * parity gate: it runs the SAME vendored maia3_simplified.onnx model through
 * onnxruntime-web's WASM execution provider (the exact runtime the browser worker
 * ships) AND the LIVE frontend encoding (frontend/src/lib/maiaEncoding.ts:
 * encodeBoard + maskAndSoftmax) — NOT the Python port under test. So comparing the
 * Python port (app/services/maia_encoding.py + onnxruntime CPU) against these values
 * is genuinely non-circular: it measures encoding-port fidelity + CPU-vs-WASM float
 * drift, exactly what D-01 requires.
 *
 * Usage: node --import ./scripts/lib/frontend-alias-hook.mjs \
 *          scripts/maia_reference_capture.mjs <candidates.json>
 * where candidates.json is [{ "fen": ..., "pinned_elo": ..., "played_uci": ... }, ...]
 * Prints an enriched array with the captured expected_maia_prob + the top few
 * policy moves (for tier sanity) to stdout as JSON.
 */
import fs from 'node:fs';
import { createMaiaSession, resolveFrontendModule } from './lib/node-engine-providers.mjs';
import { encodeBoard, maskAndSoftmax } from '@/lib/maiaEncoding';

// chess.js is a bare specifier vendored in frontend/node_modules; scripts/*.mjs is
// not under frontend/src so Node's node_modules walk can't find it — resolve it
// from the frontend package the same way node-engine-providers.mjs resolves ort.
const { Chess } = await resolveFrontendModule('chess.js');

const NUM_SQUARES = 64;
const PLANES_PER_SQUARE = 12;

function uciToSan(fen, uci) {
  const chess = new Chess(fen);
  const move = chess.move({
    from: uci.slice(0, 2),
    to: uci.slice(2, 4),
    promotion: uci.length > 4 ? uci.slice(4) : undefined,
  });
  if (!move) throw new Error(`illegal played_uci ${uci} for fen ${fen}`);
  return move.san;
}

async function main() {
  const candidatesPath = process.argv[2];
  if (!candidatesPath) throw new Error('usage: maia_reference_capture.mjs <candidates.json>');
  const candidates = JSON.parse(fs.readFileSync(candidatesPath, 'utf8'));

  const { ort, session } = await createMaiaSession();

  const results = [];
  for (const cand of candidates) {
    const { fen, pinned_elo, played_uci } = cand;
    const tokens = encodeBoard(fen);
    const feeds = {
      tokens: new ort.Tensor('float32', tokens, [1, NUM_SQUARES, PLANES_PER_SQUARE]),
      elo_self: new ort.Tensor('float32', Float32Array.from([pinned_elo]), [1]),
      elo_oppo: new ort.Tensor('float32', Float32Array.from([pinned_elo]), [1]),
    };
    const out = await session.run(feeds);
    const policy = out.logits_move.data;
    const probsBySan = maskAndSoftmax(policy, fen);

    const san = uciToSan(fen, played_uci);
    const expected = probsBySan[san];
    const top = Object.entries(probsBySan)
      .sort((a, b) => b[1] - a[1])
      .slice(0, 5)
      .map(([m, p]) => `${m}:${p.toFixed(4)}`);
    results.push({
      fen,
      pinned_elo,
      played_uci,
      played_san: san,
      expected_maia_prob: Number(expected.toFixed(6)),
      top5: top,
    });
  }
  process.stdout.write(JSON.stringify(results, null, 2) + '\n');
}

main().catch((err) => {
  console.error(err);
  process.exit(1);
});
