/**
 * Endgame Score Gap & Material Breakdown section:
 * - Gauge strip (Conversion / Parity / Recovery) showing the absolute rate
 *   against a fixed per-bucket blue target band (skill-cohort expectation).
 *   The targets are intentionally stable — they do NOT shift with filters
 *   or opponent pool, unlike the opponent-relative Diff column.
 * - Material-stratified WDL table: Conversion / Parity / Recovery with
 *   You / Opp / Diff columns and a bullet chart visualizing the signed
 *   diff against a self-calibrating opponent baseline (the user's opponents
 *   in the mirror bucket). Conversion/Recovery require the material
 *   imbalance to persist 4 plies into the endgame to filter out transient
 *   trade noise — games that don't persist fall into the Parity bucket.
 *
 * The two signals (gauge color vs Diff color) can disagree when the
 * opponent pool is unusual — that disagreement is informative.
 */

import { InfoPopover } from '@/components/ui/info-popover';
import { MiniWDLBar } from '@/components/stats/MiniWDLBar';
import { MiniBulletChart } from '@/components/charts/MiniBulletChart';
import { EndgameGauge } from '@/components/charts/EndgameGauge';
import {
  ZONE_DANGER,
  ZONE_NEUTRAL,
  ZONE_SUCCESS,
  GAUGE_DANGER,
  GAUGE_NEUTRAL,
  GAUGE_SUCCESS,
  type GaugeZone,
} from '@/lib/theme';
import type {
  MaterialBucket,
  MaterialRow,
  ScoreGapMaterialResponse,
} from '@/types/endgames';

// Opponent baseline: single symmetric neutral zone for all buckets.
// Equally-rated players should score equally in mirrored situations,
// so the expected diff is zero everywhere. ±0.05 (5pp) reads as
// "essentially matched" for the Diff color and bullet-chart neutral band.
const NEUTRAL_ZONE_MIN = -0.05;
const NEUTRAL_ZONE_MAX = 0.05;

// Bullet domain half-width for opponent-calibrated diffs. Equally-rated
// players cluster near zero, so ±0.20 covers realistic diffs without
// making typical values look tiny.
const BULLET_DOMAIN = 0.20;

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

// User-facing labels that also name the per-bucket metric, so readers can
// tell the percent column isn't the generic Score % used elsewhere on the
// page. Used in the gauge strip, desktop table, and mobile cards; aria
// labels and gauge testIds keep the short form above.
const BUCKET_DISPLAY_LABELS_WITH_METRIC: Record<MaterialBucket, string> = {
  conversion: 'Conversion (Win %)',
  parity: 'Parity (Score %)',
  recovery: 'Recovery (Save %)',
};

// Fixed per-bucket gauge zones. The blue band marks the typical
// skill-cohort range for each bucket; red below, green above. Boundaries
// are deliberately stable across users, filters, and opponent pools —
// this is the "fixed target" the opponent-calibrated design couldn't offer.
// Bands calibrated from FlawChess prod data (users ±50 ELO vs opponents,
// 0-2499 ELO brackets): conversion and recovery stay within ~4pp across
// rating ranges, so a single rating-agnostic band is used for each bucket.
const FIXED_GAUGE_ZONES: Record<MaterialBucket, GaugeZone[]> = {
  conversion: [
    { from: 0, to: 0.65, color: GAUGE_DANGER },
    { from: 0.65, to: 0.75, color: GAUGE_NEUTRAL },
    { from: 0.75, to: 1.0, color: GAUGE_SUCCESS },
  ],
  parity: [
    { from: 0, to: 0.45, color: GAUGE_DANGER },
    { from: 0.45, to: 0.55, color: GAUGE_NEUTRAL },
    { from: 0.55, to: 1.0, color: GAUGE_SUCCESS },
  ],
  recovery: [
    { from: 0, to: 0.25, color: GAUGE_DANGER },
    { from: 0.25, to: 0.35, color: GAUGE_NEUTRAL },
    { from: 0.35, to: 1.0, color: GAUGE_SUCCESS },
  ],
};

// Zones for the composite Endgame Skill gauge. The blue band mirrors the
// Parity gauge (45–55%) so the color story stays consistent with the
// per-bucket gauges users are already reading. Typical value lands around
// 52% on FlawChess data, sitting in the middle of the blue band.
const ENDGAME_SKILL_ZONES: GaugeZone[] = [
  { from: 0, to: 0.45, color: GAUGE_DANGER },
  { from: 0.45, to: 0.55, color: GAUGE_NEUTRAL },
  { from: 0.55, to: 1.0, color: GAUGE_SUCCESS },
];

/** Format a 0.0-1.0 rate as an integer percent string, e.g. 0.684 -> "68%". */
function formatScorePct(score: number): string {
  return `${Math.round(score * 100)}%`;
}

/** Format the visible diff as an integer percent with explicit sign, e.g. "-2%".
 *
 * Computed from the already-rounded You/Opp percentages so the Diff always
 * equals (displayed You) − (displayed Opp). Rounding the raw rate diff
 * independently can disagree with the displayed values by 1pp (e.g. You 69% /
 * Opp 71% showing Diff −1% instead of −2%). */
function formatDiffPct(userR: number, oppR: number): string {
  const pct = Math.round(userR * 100) - Math.round(oppR * 100);
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

/** Composite "Endgame Skill" rate: simple arithmetic mean of the per-bucket
 * rates from `userRate()`, computed over buckets with games > 0. Returns null
 * when no bucket has games (callers render a disabled gauge).
 *
 * This is intentionally an aggregate of three different rate definitions
 * (Win %, Score %, Save %), so the result is a one-number summary rather
 * than a true chess score. */
function endgameSkill(rows: MaterialRow[]): number | null {
  const active = rows.filter((r) => r.games > 0);
  if (active.length === 0) return null;
  let sum = 0;
  for (const row of active) {
    if (row.bucket === 'conversion') sum += row.win_pct / 100;
    else if (row.bucket === 'recovery') sum += (row.win_pct + row.draw_pct) / 100;
    else sum += row.score; // parity
  }
  return sum / active.length;
}

interface EndgameScoreGapSectionProps {
  data: ScoreGapMaterialResponse;
}

export function EndgameScoreGapSection({ data }: EndgameScoreGapSectionProps) {
  const totalMaterialGames = data.material_rows.reduce((sum, r) => sum + r.games, 0);
  const rowByBucket: Partial<Record<MaterialBucket, MaterialRow>> = {};
  for (const r of data.material_rows) rowByBucket[r.bucket] = r;
  const skill = endgameSkill(data.material_rows);

  return (
    <div className="space-y-4" data-testid="score-gap-section">
      {/* Section header */}
      <div>
        <h3 className="text-base font-semibold">
          <span className="inline-flex items-center gap-1">
            Endgame Metrics
            <InfoPopover
              ariaLabel="Endgame Metrics info"
              testId="material-breakdown-section-info"
              side="top"
            >
              <div className="space-y-2">
                <p>
                  Games are split by the material balance on entering the endgame:
                  <strong> Conversion</strong> (you lead by ≥ +1),
                  <strong> Parity</strong> (balanced), or
                  <strong> Recovery</strong> (you trail by ≤ −1). The imbalance
                  must persist 4 half-moves into the endgame, so transient trades
                  don't distort the split.
                </p>
                <p>
                  Each bucket uses its own rate, shown in the gauge and the
                  You / Opp / Diff columns, and named on the bucket label:
                </p>
                <ul className="list-disc pl-5 space-y-1">
                  <li>
                    <strong>Conversion (Win %)</strong>: only wins count
                  </li>
                  <li>
                    <strong>Parity (Score %)</strong>: draws count as half
                  </li>
                  <li>
                    <strong>Recovery (Save %)</strong>: draws count as a save
                  </li>
                  <li>
                    <strong>Endgame Skill</strong>: averages the three rates above
                  </li>
                </ul>
                <p>
                  These rates are not the same as the generic Score % used
                  elsewhere on the page.
                </p>
                <p>
                  The <strong>gauges</strong> plot that rate against a fixed
                  skill-cohort target band (blue = typical, red = below,
                  green = above). Bands are calibrated from FlawChess data and
                  don't shift with filters, giving you a stable target you can chase as
                  you improve.
                </p>
                <p>
                  The <strong>table</strong> compares your rate to your actual
                  opponents' rate in the mirror bucket (e.g. your Conversion vs
                  their Conversion when playing you, which is your Recovery games,
                  flipped). This baseline is self-calibrating and shifts with
                  filters like Opponent Strength. Hidden when the opponent sample
                  is smaller than 10 games.
                </p>
              </div>
            </InfoPopover>
          </span>
        </h3>
        <p className="text-sm text-muted-foreground mt-1">
          How well do you convert a material advantage into a win, and recover
          when you're down material?
        </p>
      </div>

      {/* Gauge strip — Conversion / Parity / Recovery with fixed
          per-bucket blue target bands. The Diff column below carries
          the opponent-relative verdict against the user's actual opponents. */}
      <div
        className="hidden lg:grid grid-cols-4 gap-3"
        data-testid="endgame-gauge-strip"
      >
        {(['conversion', 'parity', 'recovery'] as const).map((bucket) => {
          const row = rowByBucket[bucket];
          if (!row) return null;
          const userR = userRate(row);
          return (
            <div
              key={bucket}
              className="flex flex-col items-center"
              data-testid={`endgame-gauge-${bucket}`}
            >
              <div className="text-sm mb-1">
                {BUCKET_DISPLAY_LABELS_WITH_METRIC[bucket]}
              </div>
              <EndgameGauge
                value={userR * 100}
                label={BUCKET_DISPLAY_LABELS[bucket]}
                zones={FIXED_GAUGE_ZONES[bucket]}
              />
            </div>
          );
        })}
        {/* Composite Endgame Skill gauge — appears after Recovery so the
            per-bucket gauges keep their existing order and Skill reads as
            a summary on the right. */}
        <div
          key="skill"
          className={
            'flex flex-col items-center' + (skill === null ? ' opacity-50' : '')
          }
          data-testid="endgame-gauge-skill"
        >
          <div className="text-sm mb-1">Endgame Skill</div>
          <EndgameGauge
            value={(skill ?? 0) * 100}
            label="Endgame Skill"
            zones={ENDGAME_SKILL_ZONES}
          />
        </div>
      </div>

      {/* Desktop: table layout */}
      <div className="hidden lg:block overflow-x-auto">
        <table
          className="w-full min-w-[640px] text-sm sm:text-base table-fixed"
          data-testid="material-table"
        >
          <colgroup>
            <col style={{ width: '150px' }} />
            <col style={{ width: '120px' }} />
            <col style={{ width: '150px' }} />
            <col style={{ width: '90px' }} />
            <col style={{ width: '100px' }} />
            <col style={{ width: '70px' }} />
            <col style={{ width: '160px' }} />
          </colgroup>
          <thead>
            <tr className="text-left text-xs text-muted-foreground border-b border-border">
              <th className="py-1 pr-3 font-medium" aria-label="Material bucket" />
              <th className="py-1 px-2 font-medium text-right">Games</th>
              <th className="py-1 px-2 font-medium">Win / Draw / Loss</th>
              <th className="py-1 px-2 font-medium text-right">You</th>
              <th className="py-1 px-2 font-medium text-right">Opp</th>
              <th className="py-1 px-2 font-medium text-right">Diff</th>
              <th className="py-1 px-2 font-medium">You − Opp</th>
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
                  <td className="py-1.5 pr-3 text-sm whitespace-nowrap">
                    {BUCKET_DISPLAY_LABELS_WITH_METRIC[row.bucket]}
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
                    className="py-1.5 px-2 text-right text-sm tabular-nums whitespace-nowrap"
                    data-testid={`material-row-${row.bucket}-you`}
                  >
                    {formatScorePct(userR)}
                  </td>
                  <td
                    className="py-1.5 px-2 text-right text-sm tabular-nums text-muted-foreground whitespace-nowrap"
                    data-testid={`material-row-${row.bucket}-opp`}
                  >
                    {hasOpponent ? formatScorePct(oppR as number) : ''}
                  </td>
                  <td
                    className="py-1.5 px-2 text-right text-sm tabular-nums whitespace-nowrap"
                    data-testid={`material-row-${row.bucket}-diff`}
                  >
                    {hasOpponent ? (
                      <span className="font-semibold" style={{ color: diffColor }}>{formatDiffPct(userR, oppR as number)}</span>
                    ) : (
                      ''
                    )}
                  </td>
                  <td className="py-1.5 px-2">
                    {hasOpponent ? (
                      <MiniBulletChart
                        value={diff}
                        neutralMin={NEUTRAL_ZONE_MIN}
                        neutralMax={NEUTRAL_ZONE_MAX}
                        domain={BULLET_DOMAIN}
                        ariaLabel={`${BUCKET_DISPLAY_LABELS[row.bucket]}: ${formatDiffPct(userR, oppR as number)} vs opponents`}
                      />
                    ) : (
                      <span
                        className="text-xs text-muted-foreground"
                        data-testid={`material-row-${row.bucket}-muted`}
                      >
                        n &lt; {MIN_OPPONENT_BASELINE_GAMES}, baseline unavailable
                      </span>
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
                  {BUCKET_DISPLAY_LABELS_WITH_METRIC[row.bucket]}
                </div>
                <div className="text-xs tabular-nums text-muted-foreground">
                  {pct}% ({row.games.toLocaleString()} games)
                </div>
              </div>
              <div className="flex justify-center">
                <EndgameGauge
                  value={userR * 100}
                  label={BUCKET_DISPLAY_LABELS[row.bucket]}
                  zones={FIXED_GAUGE_ZONES[row.bucket]}
                />
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
                <div className="flex flex-wrap gap-x-4 gap-y-1 text-sm tabular-nums mb-1">
                  <div>
                    <span className="text-muted-foreground">You: </span>
                    <span
                      className="font-medium"
                      data-testid={`material-card-${row.bucket}-you`}
                    >
                      {formatScorePct(userR)}
                    </span>
                  </div>
                  {hasOpponent && (
                    <>
                      <div>
                        <span className="text-muted-foreground">Opp: </span>
                        <span
                          className="font-medium"
                          data-testid={`material-card-${row.bucket}-opp`}
                        >
                          {formatScorePct(oppR as number)}
                        </span>
                      </div>
                      <div>
                        <span className="text-muted-foreground">Diff: </span>
                        <span
                          className="font-semibold"
                          style={{ color: diffColor }}
                          data-testid={`material-card-${row.bucket}-diff`}
                        >
                          {formatDiffPct(userR, oppR as number)}
                        </span>
                      </div>
                    </>
                  )}
                </div>
                {hasOpponent ? (
                  <MiniBulletChart
                    value={diff}
                    neutralMin={NEUTRAL_ZONE_MIN}
                    neutralMax={NEUTRAL_ZONE_MAX}
                    domain={BULLET_DOMAIN}
                    ariaLabel={`${BUCKET_DISPLAY_LABELS[row.bucket]}: ${formatDiffPct(userR, oppR as number)} vs opponents`}
                  />
                ) : (
                  <span
                    className="text-xs text-muted-foreground block"
                    data-testid={`material-card-${row.bucket}-muted`}
                  >
                    n &lt; {MIN_OPPONENT_BASELINE_GAMES}, baseline unavailable
                  </span>
                )}
              </div>
            </div>
          );
        })}
        {/* Composite Endgame Skill card — gauge-only summary mirroring the
            desktop strip's 4th gauge. No WDL / You / Opp / Diff rows. */}
        <div
          className={
            'rounded border border-border p-3 space-y-2' +
            (skill === null ? ' opacity-50' : '')
          }
          data-testid="endgame-skill-card"
        >
          <div className="flex items-baseline justify-between">
            <div className="text-sm font-medium">Endgame Skill</div>
          </div>
          <div className="flex justify-center">
            <EndgameGauge
              value={(skill ?? 0) * 100}
              label="Endgame Skill"
              zones={ENDGAME_SKILL_ZONES}
            />
          </div>
        </div>
      </div>
    </div>
  );
}
