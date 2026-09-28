// Stockfish lite-single wasm: nps + MultiPV cost. node bench_sf.mjs
import { spawnStockfish } from '/home/aimfeld/Projects/Python/flawchess/scripts/lib/node-engine-providers.mjs';
const e = await spawnStockfish();
const FEN = 'r2q1rk1/pp1nbppp/2p1bn2/3p4/3P1B2/2N1PN2/PPQ1BPPP/R4RK1 w - - 6 11';
const CANDS = ['a1c1', 'f1d1', 'a2a3', 'h2h3', 'f3e5', 'f1e1', 'c3b5', 'f4g5', 'e2d3', 'b2b4'];
e.send('setoption name Hash value 8');
async function go(multipv, cands, depth) {
  e.send('ucinewgame'); e.send('isready'); await e.waitFor((l) => l === 'readyok', 30000);
  e.send(`setoption name MultiPV value ${multipv}`);
  e.send(`position fen ${FEN}`);
  let last = '';
  const off = e.onLine((l) => { if (l.startsWith('info depth')) last = l; });
  const t0 = performance.now();
  e.send(`go depth ${depth}${cands ? ' searchmoves ' + cands.join(' ') : ''}`);
  await e.waitFor((l) => l.startsWith('bestmove'), 120000);
  const dt = performance.now() - t0; off();
  const nodes = Number(/ nodes (\d+)/.exec(last)?.[1]); const nps = Number(/ nps (\d+)/.exec(last)?.[1]);
  console.log(`depth ${depth} multipv ${multipv} ${cands ? cands.length + ' searchmoves' : 'all moves'}: ${dt.toFixed(0)} ms, nodes ${nodes}, nps ${nps}`);
}
for (const d of [10, 14]) {
  await go(1, null, d);
  await go(1, CANDS, d);
  await go(4, CANDS.slice(0, 4), d);
  await go(10, CANDS, d);
}
e.terminate();
process.exit(0);
