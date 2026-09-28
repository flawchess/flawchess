// chess.js hot-path microbench. node --import hook bench_js.mjs
import { resolveFrontendModule } from '/home/aimfeld/Projects/Python/flawchess/scripts/lib/node-engine-providers.mjs';
const { Chess } = await resolveFrontendModule('chess.js');
import { maskAndSoftmaxUci, POLICY_VOCAB_SIZE } from '@/lib/maiaEncoding';
import { expandChildPositions } from '@/lib/engine/treeCommon';

const FENS = [
  'r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4',
  'r2q1rk1/pp1nbppp/2p1bn2/3p4/3P1B2/2N1PN2/PPQ1BPPP/R4RK1 w - - 6 11',
  'r1bq1r1k/pp1nbppp/2p1p3/3pP3/3P4/2NB1N2/PPPQ1PPP/R3K2R w KQ - 2 11',
  '8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1',
];
function time(label, n, fn) {
  for (let i = 0; i < 200; i++) fn(i);
  const t0 = performance.now();
  for (let i = 0; i < n; i++) fn(i);
  console.log(label.padEnd(44), `${(((performance.now() - t0) / n) * 1000).toFixed(1)} us/call`);
}
const logits = new Float32Array(POLICY_VOCAB_SIZE).map(() => Math.random());
time('new Chess(fen)', 5000, (i) => new Chess(FENS[i % 4]));
time('new Chess(fen)+moves()', 5000, (i) => new Chess(FENS[i % 4]).moves());
time('new Chess(fen)+moves({verbose})', 5000, (i) => new Chess(FENS[i % 4]).moves({ verbose: true }));
time('maskAndSoftmaxUci (per policy result)', 5000, (i) => maskAndSoftmaxUci(logits, FENS[i % 4]));
const cands = FENS.map((f) => new Chess(f).moves({ verbose: true }).slice(0, 8).map((m) => m.from + m.to + (m.promotion ?? '')));
time('expandChildPositions (8 children)', 3000, (i) => expandChildPositions(FENS[i % 4], cands[i % 4], 'w'));
