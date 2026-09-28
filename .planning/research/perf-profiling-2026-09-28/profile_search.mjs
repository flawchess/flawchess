// Instrumented mctsSearch profile: Maia inference vs Stockfish grade vs JS glue.
// Run: node --import /home/aimfeld/Projects/Python/flawchess/scripts/lib/frontend-alias-hook.mjs profile_search.mjs [nodes] [conc] [maiaThreads] [stopRule 0/1]
import { createStockfishPool } from '/home/aimfeld/Projects/Python/flawchess/scripts/lib/stockfish-pool.mjs';
import { resolveFrontendModule } from '/home/aimfeld/Projects/Python/flawchess/scripts/lib/node-engine-providers.mjs';
import fs from 'node:fs';
import { mctsSearch } from '@/lib/engine/mctsSearch';
import { FLAWCHESS_BOT_STOP_RULE } from '@/lib/engine/botBudget';
import { maskAndSoftmaxUci, encodeBoard, eloToInput, NUM_SQUARES, PLANES_PER_SQUARE, POLICY_VOCAB_SIZE } from '@/lib/maiaEncoding';

const NODES = Number(process.argv[2] ?? 50);
const CONC = Number(process.argv[3] ?? 4);
const MAIA_THREADS = Number(process.argv[4] ?? 4);
const USE_STOP = (process.argv[5] ?? '1') === '1';
const ELO = 1500;

const POSITIONS = [
  { label: 'italian', fen: 'r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4' },
  { label: 'middlegame', fen: 'r2q1rk1/pp1nbppp/2p1bn2/3p4/3P1B2/2N1PN2/PPQ1BPPP/R4RK1 w - - 6 11' },
  { label: 'sharp', fen: 'r1bq1r1k/pp1nbppp/2p1p3/3pP3/3P4/2NB1N2/PPPQ1PPP/R3K2R w KQ - 2 11' },
  { label: 'endgame', fen: '8/2p5/3p4/KP5r/1R3p1k/8/4P1P1/8 w - - 0 1' },
];

const ort = (await resolveFrontendModule('onnxruntime-web')).default;
ort.env.wasm.numThreads = MAIA_THREADS;
const session = await ort.InferenceSession.create(
  fs.readFileSync('/home/aimfeld/Projects/Python/flawchess/frontend/public/maia/maia3_simplified.onnx'),
  { executionProviders: ['wasm'] },
);
const pool = await createStockfishPool({ size: CONC, hashMb: 8 });

let maiaChain = Promise.resolve();
function serialized(fn) {
  const p = maiaChain.then(fn, fn);
  maiaChain = p.catch(() => {});
  return p;
}

async function rawLogits(fen, elo) {
  const eloInput = Float32Array.of(eloToInput(elo));
  const feeds = {
    tokens: new ort.Tensor('float32', encodeBoard(fen), [1, NUM_SQUARES, PLANES_PER_SQUARE]),
    elo_self: new ort.Tensor('float32', eloInput, [1]),
    elo_oppo: new ort.Tensor('float32', eloInput, [1]),
  };
  let out;
  try {
    out = await session.run(feeds);
    return out.logits_move.data.slice(0, POLICY_VOCAB_SIZE);
  } finally {
    for (const t of Object.values(feeds)) t.dispose?.();
    if (out) for (const t of Object.values(out)) t.dispose?.();
  }
}
// warm
await rawLogits(POSITIONS[0].fen, ELO);

const agg = { wall: 0, maiaCalls: 0, maiaMs: 0, maiaCacheHits: 0, gradeCalls: 0, gradeMs: 0, gradeCacheHits: 0, gradeByDepth: {}, glue: 0, nodes: 0, cands: 0 };
for (const { label, fen } of POSITIONS) {
  const logitCache = new Map();
  const gradeCache = new Map();
  const st = { maiaCalls: 0, maiaMs: 0, maiaHits: 0, gradeCalls: 0, gradeMs: 0, gradeHits: 0, byDepth: {}, cands: 0 };
  const providers = {
    policy: async (f, elo) => {
      const key = `${f}|${elo}`;
      if (logitCache.has(key)) { st.maiaHits++; return maskAndSoftmaxUci(logitCache.get(key), f); }
      const logits = await serialized(async () => {
        const t0 = performance.now();
        const r = await rawLogits(f, elo);
        st.maiaMs += performance.now() - t0; st.maiaCalls++;
        return r;
      });
      logitCache.set(key, logits);
      return maskAndSoftmaxUci(logits, f);
    },
    grade: async (f, cands, signal, depth) => {
      const key = `${f}|${depth}`;
      const c = gradeCache.get(key);
      if (c && cands.every((u) => c.has(u))) { st.gradeHits++; return c; }
      const t0 = performance.now();
      const g = await pool.grade(f, cands, signal, depth);
      const dt = performance.now() - t0;
      st.gradeMs += dt; st.gradeCalls++; st.cands += cands.length;
      const d = (st.byDepth[depth] ??= { n: 0, ms: 0, cands: 0 });
      d.n++; d.ms += dt; d.cands += cands.length;
      gradeCache.set(key, new Map([...(c ?? []), ...g]));
      return g;
    },
  };
  const budget = { maxNodes: NODES, maxPlies: 8, concurrency: CONC, elo: { w: ELO, b: ELO }, ...(USE_STOP ? { stopRule: FLAWCHESS_BOT_STOP_RULE } : {}) };
  const sig = new AbortController().signal;
  const t0 = performance.now();
  const snap = await mctsSearch(fen, budget, providers, () => {}, sig);
  const wall = performance.now() - t0;
  // replay for glue cost (zero-latency providers, real maskAndSoftmaxUci)
  const replay = {
    policy: async (f, elo) => maskAndSoftmaxUci(logitCache.get(`${f}|${elo}`) ?? new Float32Array(POLICY_VOCAB_SIZE), f),
    grade: async (f, cands, s, depth) => gradeCache.get(`${f}|${depth}`) ?? new Map(),
  };
  await mctsSearch(fen, budget, replay, () => {}, sig);
  const r0 = performance.now();
  for (let i = 0; i < 3; i++) await mctsSearch(fen, budget, replay, () => {}, sig);
  const glue = (performance.now() - r0) / 3;
  console.log(`${label.padEnd(11)} nodes=${snap.nodesEvaluated} wall=${wall.toFixed(0)}ms | maia ${st.maiaCalls} calls ${st.maiaMs.toFixed(0)}ms (${(st.maiaMs / st.maiaCalls).toFixed(1)}/call, ${st.maiaHits} cache hits) | grade ${st.gradeCalls} calls busy ${st.gradeMs.toFixed(0)}ms (${(st.gradeMs / st.gradeCalls).toFixed(0)}/call, avg ${(st.cands / st.gradeCalls).toFixed(1)} cands, ${st.gradeHits} hits) ${JSON.stringify(Object.fromEntries(Object.entries(st.byDepth).map(([k, v]) => [k, `${v.n}x ${(v.ms / v.n).toFixed(0)}ms ${(v.cands / v.n).toFixed(1)}c`])))} | JS glue replay ${glue.toFixed(0)}ms`);
  agg.wall += wall; agg.maiaCalls += st.maiaCalls; agg.maiaMs += st.maiaMs; agg.gradeCalls += st.gradeCalls; agg.gradeMs += st.gradeMs; agg.glue += glue; agg.nodes += snap.nodesEvaluated;
}
console.log(`TOTAL nodes=${NODES} conc=${CONC} maiaThreads=${MAIA_THREADS} stop=${USE_STOP}: wall ${agg.wall.toFixed(0)}ms; maia serialized ${agg.maiaMs.toFixed(0)}ms (${((agg.maiaMs / agg.wall) * 100).toFixed(0)}% of wall); SF busy ${agg.gradeMs.toFixed(0)}ms across ${CONC} procs (${((agg.gradeMs / CONC / agg.wall) * 100).toFixed(0)}% pool utilisation); glue ${agg.glue.toFixed(0)}ms (${((agg.glue / agg.wall) * 100).toFixed(1)}%)`);
pool.quitAll();
process.exit(0);
