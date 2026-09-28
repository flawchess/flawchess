// Maia batch/threads/backend microbench. node --import hook bench_maia.mjs [modelPath]
import fs from 'node:fs';
import { createRequire } from 'node:module';
import { resolveFrontendModule } from '/home/aimfeld/Projects/Python/flawchess/scripts/lib/node-engine-providers.mjs';
import { encodeBoard, eloToInput, NUM_SQUARES, PLANES_PER_SQUARE } from '@/lib/maiaEncoding';

const MODEL = process.argv[2] ?? '/home/aimfeld/Projects/Python/flawchess/frontend/public/maia/maia3_simplified.onnx';
const FENS = [
  'r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4',
  'r2q1rk1/pp1nbppp/2p1bn2/3p4/3P1B2/2N1PN2/PPQ1BPPP/R4RK1 w - - 6 11',
  'r1bq1r1k/pp1nbppp/2p1p3/3pP3/3P4/2NB1N2/PPPQ1PPP/R3K2R w KQ - 2 11',
  '8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1',
];
const BATCHES = [1, 2, 4, 8, 16];
const REPS = 7;

function feedsFor(ort, b) {
  const tok = new Float32Array(b * NUM_SQUARES * PLANES_PER_SQUARE);
  for (let i = 0; i < b; i++) tok.set(encodeBoard(FENS[i % FENS.length]), i * NUM_SQUARES * PLANES_PER_SQUARE);
  const elo = new Float32Array(b).fill(eloToInput(1500));
  return {
    tokens: new ort.Tensor('float32', tok, [b, NUM_SQUARES, PLANES_PER_SQUARE]),
    elo_self: new ort.Tensor('float32', elo, [b]),
    elo_oppo: new ort.Tensor('float32', elo, [b]),
  };
}
const median = (a) => [...a].sort((x, y) => x - y)[Math.floor(a.length / 2)];

async function bench(label, ort, session) {
  const row = [];
  for (const b of BATCHES) {
    const times = [];
    for (let r = 0; r < REPS + 1; r++) {
      const f = feedsFor(ort, b);
      const t0 = performance.now();
      const out = await session.run(f);
      const dt = performance.now() - t0;
      for (const t of Object.values(out)) t.dispose?.();
      if (r > 0) times.push(dt);
    }
    const m = median(times);
    row.push(`b${b}=${m.toFixed(1)}ms(${(m / b).toFixed(1)}/pos)`);
  }
  console.log(label.padEnd(24), row.join('  '));
}

const bytes = fs.readFileSync(MODEL);
const mode = process.argv[3] ?? 'web';
if (mode === 'web') {
  const threads = Number(process.argv[4] ?? 1);
  const ort = (await resolveFrontendModule('onnxruntime-web')).default;
  ort.env.wasm.numThreads = threads;
  const s = await ort.InferenceSession.create(bytes, { executionProviders: ['wasm'] });
  await bench(`ort-web wasm t=${threads}`, ort, s);
} else {
  const threads = Number(process.argv[4] ?? 1);
  const ort = createRequire('/home/aimfeld/Projects/Python/flawchess/scripts/package.json')('onnxruntime-node');
  const s = await ort.InferenceSession.create(MODEL, { executionProviders: ['cpu'], intraOpNumThreads: threads, interOpNumThreads: 1 });
  await bench(`ort-node native t=${threads}`, ort, s);
}
// encode cost
const t0 = performance.now();
for (let i = 0; i < 20000; i++) encodeBoard(FENS[i % 4]);
console.log(`encodeBoard: ${((performance.now() - t0) / 20000 * 1000).toFixed(1)} us/call`);
process.exit(0);
