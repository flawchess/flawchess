/**
 * Endgame Score Gap & Material Breakdown section:
 * - Signed score difference (endgame score vs non-endgame score), green >= 0, red < 0
 * - Material-stratified WDL table: Conversion / Parity / Recovery, with a mini
 *   bullet chart comparing each bucket's score to the opponent's score in the
 *   mirror bucket (self-calibrating peer baseline — Phase 60).
 *   Conversion/Recovery require the material imbalance to persist 4 plies into
 *   the endgame to filter out transient trade noise — games that don't persist
 *   fall into the Parity bucket.
 */

import { InfoPopover } from '@/components/ui/info-popover';
import { MiniWDLBar } from '@/components/stats/MiniWDLBar';
import { EndgameGauge } from '@/components/charts/EndgameGauge';
import {
  ZONE_DANGER,
  ZONE_NEUTRAL,
  ZONE_SUCCESS,
  GAUGE_DANGER,
  GAUGE_PEER,
  GAUGE_SUCCESS,
  DEFAULT_GAUGE_ZONES,
  type GaugeZone,
} from '@/lib/theme';
import type {
  MaterialBucket,
  MaterialRow,
  ScoreGapMaterialResponse,
} from '@/types/endgames';

// Phase 60: opponent baseline — single symmetric neutral zone for all
// buckets. Equally-rated players should score equally in mirrored
// situations, so the expected diff is zero everywhere. ±0.03 (3pp)
// reads as "essentially matched" — kept for the table Diff color thresholds.
const NEUTRAL_ZONE_MIN = -0.05;
const NEUTRAL_ZONE_MAX = 0.05;

// Peer-calibrated gauge tolerance — width of the blue peer-match band
// on either side of the opponent's rate. Same 5pp value as the Diff
// neutral zone, keeping the two visualisations conceptually aligned.
const PEER_ZONE_TOLERANCE = 0.05;

// Hide the bullet bar when the opponent's mirror-bucket sample is too
// small. Mirrors backend `_MIN_OPPONENT_SAMPLE = 10` and the WDL-bar
// mute threshold used in the Opening Explorer moves list.
const MIN_OPPONENT_BASELINE_GAMES = 10;

// Short display names — the material indicator ("≥ +1", "≤ −1") lives in the
// section description, freeing column/card space (especially on mobile).
const BUCKET_DISPLAY_LABELS: Record<MaterialBucket, string> = {
  conversion: 'Conversion',
  parity: 'Parity',
  recovery: 'Recovery',
};

/** Format a 0.0-1.0 rate as an integer percent string, e.g. 0.684 -> "68%". */
function formatScorePct(score: number): string {
  return `${Math.round(score * 100)}%`;
}

/** Format a signed diff (in 0.0-1.0 rate units) as an integer percent
 * with an explicit sign, e.g. -0.08 -> "-8%", 0.03 -> "+3%", 0 -> "+0%". */
function formatDiffPct(diff: number): string {
  const pct = Math.round(diff * 100);
  return `${pct >= 0 ? '+' : ''}${pct}%`;
}

// Mirror-bucket map: used to derive opponent rate from the user's WDL in
// the mirror bucket (same-game symmetry: opponent wins = user losses,
// opponent draws = user draws).
const MIRROR_BUCKET: Record<MaterialBucket, MaterialBucket> = {
  conversion: 'recovery',
  parity: 'parity',
  recovery: 'conversion',
};

/** User's rate for this bucket using the bucket's headline definition:
 * - Conversion: win rate (W/G) — only wins count as a successful conversion
 * - Recovery: save rate ((W+D)/G) — draws also count as a successful defense
 * - Parity: chess score ((W+D/2)/G) — neutral midpoint at material balance
 *
 * win_pct/draw_pct/loss_pct are stored as 0-100 on the row; we scale to 0-1
 * to match `row.score` and the bullet-chart domain. */
function userRate(row: MaterialRow): number {
  if (row.bucket === 'conversion') return row.win_pct / 100;
  if (row.bucket === 'recovery') return (row.win_pct + row.draw_pct) / 100;
  return row.score;
}

/** Opponent's rate in the mirror bucket under the same definition.
 * By same-game symmetry, an opponent's win/draw/loss within the mirror
 * bucket = user's loss/draw/win in the mirror bucket.
 * - Conversion opp = opp wins in user's recovery bucket = user losses there
 * - Recovery opp  = opp wins+draws in user's conversion bucket = user losses+draws there
 * - Parity opp    = 1 − user parity score (chess-score symmetry)
 *
 * Returns null if mirror bucket is missing from response (defensive). */
function opponentRate(row: MaterialRow, mirror: MaterialRow | undefined): number | null {
  if (!mirror) return null;
  if (row.bucket === 'conversion') return mirror.loss_pct / 100;
  if (row.bucket === 'recovery') return (mirror.loss_pct + mirror.draw_pct) / 100;
  return 1 - row.score;
}

/** Build peer-calibrated gauge zones around the opponent's rate.
 * Returns red below [peerRate − tol], blue inside [peerRate ± tol], green above.
 * Edge zones are dropped if they would be empty (peerRate at 0 or 1). */
function peerCalibratedZones(peerRate: number, tolerance = PEER_ZONE_TOLERANCE): GaugeZone[] {
  const lo = Math.max(0, peerRate - tolerance);
  const hi = Math.min(1, peerRate + tolerance);
  const zones: GaugeZone[] = [];
  if (lo > 0) zones.push({ from: 0, to: lo, color: GAUGE_DANGER });
  if (hi > lo) zones.push({ from: lo, to: hi, color: GAUGE_PEER });
  if (hi < 1) zones.push({ from: hi, to: 1, color: GAUGE_SUCCESS });
  return zones;
}

interface EndgameScoreGapSectionProps {
  data: ScoreGapMaterialResponse;
}

export function EndgameScoreGapSection({ data }: EndgameScoreGapSectionProps) {
  const totalMaterialGames = data.material_rows.reduce((sum, r) => sum + r.games, 0);
  const rowByBucket: Partial<Record<MaterialBucket, MaterialRow>> = {};
  for (const r of data.material_rows) rowByBucket[r.bucket] = r;

  return (
    <div className="space-y-4" data-testid="score-gap-section">
      {/* Section header */}
      <div>
        <h3 className="text-base font-semibold">
          <span className="inline-flex items-center gap-1">
            Endgame Conversion & Recovery
            <InfoPopover
              ariaLabel="Conversion & Recovery info"
              testId="material-breakdown-section-info"
              side="top"
            >
              <div className="space-y-2">
                <p>
                  Games are split by the material balance on entering the endgame:
                  <strong> Conversion</strong> (you lead by ≥ +1),
                  <strong> Parity</strong> (roughly balanced), or
                  <strong> Recovery</strong> (you trail by ≤ −1). The imbalance must
                  persist 4 half-moves into the endgame, so transient trades don't
                  distort the split.
                </p>
                <p>
                  Your baseline is how your opponents performed in the mirror
                  bucket <em>against you</em> — e.g. your Conversion score is
                  compared to your opponents' Conversion score when playing you
                  (your Recovery games, flipped). Because the platform rating-matches
                  you, this baseline self-calibrates as you improve.
                </p>
                <p>
                  Bars near the neutral zone mean you perform like an equally-rated
                  player in the same situation; to the right you outperform, to the
                  left you underperform. Baselines are hidden when the opponent
                  sample is smaller than 10 games.
                </p>
                <p>
                  Tip: set the Opponent Strength filter to "Similar" to restrict
                  the baseline to opponents within ±50 ELO of your rating.
                </p>
              </div>
            </InfoPopover>
          </span>
        </h3>
        <p className="text-sm text-muted-foreground mt-1">
          How well do you convert a material advantage into a win and recovery
          when you're down material?
        </p>
      </div>

      {/* Peer-calibrated gauge strip — Conversion / Parity / Recovery */}
      <div
        className="grid grid-cols-1 sm:grid-cols-3 gap-3"
        data-testid="endgame-gauge-strip"
      >
        {(['conversion', 'parity', 'recovery'] as const).map((bucket) => {
          const row = rowByBucket[bucket];
          if (!row) return null;
          const mirror = rowByBucket[MIRROR_BUCKET[bucket]];
          const userR = userRate(row);
          const oppR = opponentRate(row, mirror);
          const hasPeer =
            oppR !== null && row.opponent_games >= MIN_OPPONENT_BASELINE_GAMES;
          const zones = hasPeer
            ? peerCalibratedZones(oppR as number)
            : DEFAULT_GAUGE_ZONES;
          return (
            <div
              key={bucket}
              className="flex flex-col items-center"
              data-testid={`endgame-gauge-${bucket}`}
            >
              <div className="text-xs text-muted-foreground mb-1">
                {BUCKET_DISPLAY_LABELS[bucket]}
              </div>
              <EndgameGauge
                value={userR * 100}
                label={BUCKET_DISPLAY_LABELS[bucket]}
                zones={zones}
              />
              <div className="text-xs text-muted-foreground tabular-nums">
                {hasPeer ? `Peer: ${formatScorePct(oppR as number)}` : '—'}
              </div>
            </div>
          );
        })}
      </div>

      {/* Desktop: table layout */}
      <div className="hidden lg:block overflow-x-auto">
        <table
          className="w-full min-w-[600px] text-sm sm:text-base table-fixed"
          data-testid="material-table"
        >
          <colgroup>
            <col style={{ width: '120px' }} />
            <col style={{ width: '130px' }} />
            <col style={{ width: '160px' }} />
            <col style={{ width: '110px' }} />
            <col style={{ width: '110px' }} />
            <col style={{ width: '70px' }} />
          </colgroup>
          <thead>
            <tr className="text-left text-xs text-muted-foreground border-b border-border">
              <th className="py-1 pr-3 font-medium" aria-label="Material bucket" />
              <th className="py-1 px-2 font-medium text-right">Games</th>
              <th className="py-1 px-2 font-medium">Win / Draw / Loss</th>
              <th className="py-1 px-2 font-medium text-right">You vs Peers</th>
              <th className="py-1 px-2 font-medium text-right">Peers vs You</th>
              <th className="py-1 px-2 font-medium text-right">Diff</th>
            </tr>
          </thead>
          <tbody>
            {data.material_rows.map((row) => {
              const mirror = rowByBucket[MIRROR_BUCKET[row.bucket]];
              const userR = userRate(row);
              const oppR = opponentRate(row, mirror);
              const hasOpponent =
                oppR !== null && row.opponent_games >= MIN_OPPONENT_BASELINE_GAMES;
              const diff = hasOpponent ? userR - (oppR as number) : 0;
              const diffColor =
                diff >= NEUTRAL_ZONE_MAX
                  ? ZONE_SUCCESS
                  : diff >= NEUTRAL_ZONE_MIN
                    ? ZONE_NEUTRAL
                    : ZONE_DANGER;
              const pct =
                totalMaterialGames > 0
                  ? ((row.games / totalMaterialGames) * 100).toFixed(1)
                  : '0.0';
              return (
                <tr
                  key={row.bucket}
                  className={row.games === 0 ? 'opacity-50' : undefined}
                  data-testid={`material-row-${row.bucket}`}
                >
                  <td className="py-1.5 pr-3 text-sm">
                    {BUCKET_DISPLAY_LABELS[row.bucket]}
                  </td>
                  <td className="py-1.5 px-2 text-right text-sm tabular-nums whitespace-nowrap">
                    {pct}% ({row.games.toLocaleString()})
                  </td>
                  <td className="py-1.5 px-2">
                    <MiniWDLBar
                      win_pct={row.win_pct}
                      draw_pct={row.draw_pct}
                      loss_pct={row.loss_pct}
                    />
                  </td>
                  <td
                    className="py-1.5 px-2 text-right text-xs tabular-nums whitespace-nowrap"
                    data-testid={`material-row-${row.bucket}-you`}
                  >
                    {formatScorePct(userR)}
                  </td>
                  <td
                    className="py-1.5 px-2 text-right text-xs tabular-nums text-muted-foreground whitespace-nowrap"
                    data-testid={`material-row-${row.bucket}-opp`}
                  >
                    {hasOpponent ? formatScorePct(oppR as number) : ''}
                  </td>
                  <td
                    className="py-1.5 px-2 text-right text-xs tabular-nums whitespace-nowrap"
                    data-testid={`material-row-${row.bucket}-diff`}
                  >
                    {hasOpponent ? (
                      <span style={{ color: diffColor }}>{formatDiffPct(diff)}</span>
                    ) : (
                      ''
                    )}
                  </td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>

      {/* Mobile: stacked cards */}
      <div className="lg:hidden space-y-3" data-testid="material-cards">
        {data.material_rows.map((row) => {
          const mirror = rowByBucket[MIRROR_BUCKET[row.bucket]];
          const userR = userRate(row);
          const oppR = opponentRate(row, mirror);
          const hasOpponent =
            oppR !== null && row.opponent_games >= MIN_OPPONENT_BASELINE_GAMES;
          const diff = hasOpponent ? userR - (oppR as number) : 0;
          const diffColor =
            diff >= NEUTRAL_ZONE_MAX
              ? ZONE_SUCCESS
              : diff >= NEUTRAL_ZONE_MIN
                ? ZONE_NEUTRAL
                : ZONE_DANGER;
          const pct =
            totalMaterialGames > 0
              ? ((row.games / totalMaterialGames) * 100).toFixed(1)
              : '0.0';
          return (
            <div
              key={row.bucket}
              className={
                'rounded border border-border p-3 space-y-2' +
                (row.games === 0 ? ' opacity-50' : '')
              }
              data-testid={`material-card-${row.bucket}`}
            >
              <div className="flex items-baseline justify-between">
                <div className="text-sm font-medium">
                  {BUCKET_DISPLAY_LABELS[row.bucket]}
                </div>
                <div className="text-xs tabular-nums text-muted-foreground">
                  {pct}% ({row.games.toLocaleString()} games)
                </div>
              </div>
              <div>
                <div className="text-xs text-muted-foreground mb-1">
                  Win / Draw / Loss
                </div>
                <MiniWDLBar
                  win_pct={row.win_pct}
                  draw_pct={row.draw_pct}
                  loss_pct={row.loss_pct}
                />
              </div>
              <div>
                <div className="flex gap-4 text-xs tabular-nums mb-1">
                  <div>
                    <div className="text-muted-foreground">You vs Peers</div>
                    <div
                      className="font-medium"
                      data-testid={`material-card-${row.bucket}-you`}
                    >
                      {formatScorePct(userR)}
                    </div>
                  </div>
                  {hasOpponent && (
                    <>
                      <div>
                        <div className="text-muted-foreground">Peers vs You</div>
                        <div
                          className="font-medium"
                          data-testid={`material-card-${row.bucket}-opp`}
                        >
                          {formatScorePct(oppR as number)}
                        </div>
                      </div>
                      <div>
                        <div className="text-muted-foreground">Diff</div>
                        <div
                          className="font-medium"
                          style={{ color: diffColor }}
                          data-testid={`material-card-${row.bucket}-diff`}
                        >
                          {formatDiffPct(diff)}
                        </div>
                      </div>
                    </>
                  )}
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
