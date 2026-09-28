import { createStockfishPool } from '/home/aimfeld/Projects/Python/flawchess/scripts/lib/stockfish-pool.mjs';
const pool = await createStockfishPool({ size: 4, hashMb: 8 });
const POS = [
 ['r2q1rk1/pp1nbppp/2p1bn2/3p4/3P1B2/2N1PN2/PPQ1BPPP/R4RK1 w - - 6 11', ['a1c1','f1d1','a2a3','h2h3','f3e5','f1e1','c3b5','f4g5','e2d3','b2b4','a1b1','c2d2']],
 ['r1bqkb1r/pppp1ppp/2n2n2/4p3/2B1P3/5N2/PPPP1PPP/RNBQK2R w KQkq - 4 4', ['e1g1','d2d3','b1c3','f3g5','d2d4','c2c3','h2h3','a2a4']],
];
for (const [fen, c] of POS) {
  let t0 = performance.now(); const whole = await pool.grade(fen, c, undefined, 14); const tw = performance.now() - t0;
  const chunks = [[],[],[],[]]; c.forEach((u, i) => chunks[i % 4].push(u));
  t0 = performance.now(); const parts = await Promise.all(chunks.map((ch) => pool.grade(fen, ch, undefined, 14))); const ts = performance.now() - t0;
  const split = new Map(parts.flatMap((m) => [...m]));
  const diffs = c.map((u) => `${u}:${whole.get(u)?.evalCp}/${split.get(u)?.evalCp}`).join(' ');
  console.log(`${c.length} cands d14: single-worker MultiPV ${tw.toFixed(0)}ms vs 4-way split ${ts.toFixed(0)}ms (${(tw/ts).toFixed(1)}x)\n  cp whole/split: ${diffs}`);
}
pool.quitAll(); process.exit(0);
