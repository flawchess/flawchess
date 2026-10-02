// Instrumented mctsSearch profile: Maia inference vs Stockfish grade vs JS glue.
// D-17 (Phase 226): also records grade ms by (root vs non-root, grading depth,
// candidate-count bucket) and prints the share of grade ms spent on non-root
// grades with more than 8 candidates — the signal that decides whether the
// non-root candidate-cap arm is worth building.
// Run: node --import /home/aimfeld/Projects/Python/flawchess/scripts/lib/frontend-alias-hook.mjs profile_search.mjs [nodes] [conc] [maiaThreads] [stopRule 0/1] [outJson]
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
const OUT_JSON = process.argv[6] ?? null;
const ELO = 1500;

/** D-17 candidate-count buckets: `<=4` / `5-8` / `9-12` / `13+`. */
function candBucket(n) {
  if (n <= 4) return '<=4';
  if (n <= 8) return '5-8';
  if (n <= 12) return '9-12';
  return '13+';
}

/** Accumulates one grade call's calls/ms into `hist`, keyed by (isRoot, depth, candBucket(n)). */
function accumulateHistogram(hist, isRoot, depth, n, ms) {
  const bucket = candBucket(n);
  const key = `${isRoot}|${depth}|${bucket}`;
  const entry = (hist[key] ??= { isRoot, depth, bucket, calls: 0, ms: 0 });
  entry.calls += 1;
  entry.ms += ms;
}

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

const agg = { wall: 0, maiaCalls: 0, maiaMs: 0, maiaCacheHits: 0, gradeCalls: 0, gradeMs: 0, gradeCacheHits: 0, gradeByDepth: {}, glue: 0, nodes: 0, cands: 0, histogram: {} };
const positionStats = [];
for (const { label, fen } of POSITIONS) {
  const logitCache = new Map();
  const gradeCache = new Map();
  const st = { maiaCalls: 0, maiaMs: 0, maiaHits: 0, gradeCalls: 0, gradeMs: 0, gradeHits: 0, byDepth: {}, cands: 0, histogram: {} };
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
      // D-17: is_root x grading_depth x candidate-count bucket histogram, per
      // position and in aggregate. Cache hits are NOT counted (mirrors gradeMs
      // above — a cache hit does no grading work).
      const isRoot = f === fen;
      accumulateHistogram(st.histogram, isRoot, depth, cands.length, dt);
      accumulateHistogram(agg.histogram, isRoot, depth, cands.length, dt);
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
  positionStats.push({
    label, nodes: snap.nodesEvaluated, wallMs: wall,
    maiaCalls: st.maiaCalls, maiaMs: st.maiaMs, gradeCalls: st.gradeCalls, gradeMs: st.gradeMs,
    histogram: Object.values(st.histogram).map((e) => ({ is_root: e.isRoot, grading_depth: e.depth, cand_bucket: e.bucket, calls: e.calls, ms: e.ms })),
  });
}
console.log(`TOTAL nodes=${NODES} conc=${CONC} maiaThreads=${MAIA_THREADS} stop=${USE_STOP}: wall ${agg.wall.toFixed(0)}ms; maia serialized ${agg.maiaMs.toFixed(0)}ms (${((agg.maiaMs / agg.wall) * 100).toFixed(0)}% of wall); SF busy ${agg.gradeMs.toFixed(0)}ms across ${CONC} procs (${((agg.gradeMs / CONC / agg.wall) * 100).toFixed(0)}% pool utilisation); glue ${agg.glue.toFixed(0)}ms (${((agg.glue / agg.wall) * 100).toFixed(1)}%)`);

// D-17: aggregate is_root x grading_depth x candidate-count-bucket histogram,
// printed as aligned rows, then the single decision line the accept rule
// reads: share of total grade ms spent on non-root grades with MORE THAN 8
// candidates (i.e. bucket '9-12' or '13+') over total grade ms.
const BUCKET_ORDER = ['<=4', '5-8', '9-12', '13+'];
const histogramRows = Object.values(agg.histogram).sort((a, b) => {
  if (a.isRoot !== b.isRoot) return a.isRoot ? -1 : 1;
  if (a.depth !== b.depth) return a.depth - b.depth;
  return BUCKET_ORDER.indexOf(a.bucket) - BUCKET_ORDER.indexOf(b.bucket);
});
console.log('\nis_root  depth  bucket  calls  ms');
for (const row of histogramRows) {
  console.log(`${String(row.isRoot).padEnd(9)}${String(row.depth).padEnd(7)}${row.bucket.padEnd(8)}${String(row.calls).padEnd(7)}${row.ms.toFixed(0)}`);
}
let nonRootGt8Ms = 0;
for (const row of histogramRows) {
  if (!row.isRoot && (row.bucket === '9-12' || row.bucket === '13+')) nonRootGt8Ms += row.ms;
}
const nonRootGt8Share = agg.gradeMs > 0 ? nonRootGt8Ms / agg.gradeMs : 0;
console.log(`D17 non_root_gt8_share=${nonRootGt8Share.toFixed(3)} non_root_gt8_ms=${nonRootGt8Ms.toFixed(0)} grade_ms=${agg.gradeMs.toFixed(0)}`);

if (OUT_JSON !== null) {
  const payload = {
    nodes: NODES, conc: CONC, maiaThreads: MAIA_THREADS, stop: USE_STOP,
    positions: positionStats,
    histogram: histogramRows.map((e) => ({ is_root: e.isRoot, grading_depth: e.depth, cand_bucket: e.bucket, calls: e.calls, ms: e.ms })),
    totals: {
      wallMs: agg.wall, maiaMs: agg.maiaMs, gradeMs: agg.gradeMs,
      nonRootGt8Ms, nonRootGt8Share,
    },
  };
  fs.writeFileSync(OUT_JSON, JSON.stringify(payload, null, 2));
  console.log(`\nWrote ${OUT_JSON}`);
}

pool.quitAll();
process.exit(0);
