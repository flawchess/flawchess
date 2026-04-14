/**
 * Endgame Score Gap & Material Breakdown section:
 * - Signed score difference (endgame score vs non-endgame score), green >= 0, red < 0
 * - Material-stratified WDL table: Conversion / Even / Recovery, with a mini
 *   bullet chart comparing each bucket's score to the opponent's score in the
 *   mirror bucket (self-calibrating peer baseline — Phase 60).
 *   Conversion/Recovery require the material imbalance to persist 4 plies into
 *   the endgame to filter out transient trade noise — games that don't persist
 *   fall into the Even bucket.
 */

import { InfoPopover } from '@/components/ui/info-popover';
import { MiniWDLBar } from '@/components/stats/MiniWDLBar';
import { MiniBulletChart } from '@/components/charts/MiniBulletChart';
import type { MaterialBucket, ScoreGapMaterialResponse } from '@/types/endgames';

// Phase 60: opponent baseline — single symmetric neutral zone for all
// buckets. Equally-rated players should score equally in mirrored
// situations, so the expected diff is zero everywhere. ±0.03 (3pp)
// reads as "essentially matched" — widen to ±0.05 if the bullet band
// is visually too tight; do NOT revert to per-bucket asymmetric zones.
const NEUTRAL_ZONE_MIN = -0.03;
const NEUTRAL_ZONE_MAX = 0.03;

// Narrow bullet domain for opponent-calibrated diffs. Equally-rated
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
  even: 'Even',
  recovery: 'Recovery',
};

interface EndgameScoreGapSectionProps {
  data: ScoreGapMaterialResponse;
}

export function EndgameScoreGapSection({ data }: EndgameScoreGapSectionProps) {
  const totalMaterialGames = data.material_rows.reduce((sum, r) => sum + r.games, 0);

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
                  When you enter an endgame with a material advantage (Conversion),
                  your baseline is your opponents' score when they have the advantage
                  against you — the mirror situation. Because opponents are rating-matched
                  by the platform, this baseline is self-calibrating: it adapts as you climb.
                </p>
                <p>
                  Bars near the neutral zone mean you're performing about the same as
                  equally-rated players in the same situation; to the right, you outperform
                  them; to the left, you underperform. Baselines are hidden when the
                  opponent sample is smaller than 10 games.
                </p>
                <p>
                  For an even tighter comparison, set the Opponent Strength filter to
                  "Similar" — this restricts the baseline to opponents within ±50 ELO
                  of your rating.
                </p>
              </div>
            </InfoPopover>
          </span>
        </h3>
        <p className="text-sm text-muted-foreground mt-1">
          Your vs. your opponents' performance <em>against you</em> when
          entering the endgame with a material advantage (Conversion, ≥ +1),
          roughly even (Even), or a deficit (Recovery, ≤ −1).
        </p>
      </div>

      {/* Desktop: table layout */}
      <div className="hidden lg:block overflow-x-auto">
        <table
          className="w-full min-w-[720px] text-sm sm:text-base table-fixed"
          data-testid="material-table"
        >
          <colgroup>
            <col style={{ width: '140px' }} />
            <col style={{ width: '130px' }} />
            <col style={{ width: '160px' }} />
            <col style={{ width: '110px' }} />
            <col style={{ width: '180px' }} />
          </colgroup>
          <thead>
            <tr className="text-left text-xs text-muted-foreground border-b border-border">
              <th className="py-1 pr-3 font-medium" aria-label="Material bucket" />
              <th className="py-1 px-2 font-medium text-right">Games</th>
              <th className="py-1 px-2 font-medium">Win / Draw / Loss</th>
              <th className="py-1 px-2 font-medium text-right">
                Score (Diff)
              </th>
              <th className="py-1 px-2 font-medium">
                Score vs Opponent
              </th>
            </tr>
          </thead>
          <tbody>
            {data.material_rows.map((row) => {
              const hasOpponent =
                row.opponent_score !== null &&
                row.opponent_games >= MIN_OPPONENT_BASELINE_GAMES;
              const diff = hasOpponent ? row.score - (row.opponent_score as number) : 0;
              const diffLabel = (diff >= 0 ? '+' : '') + diff.toFixed(2);
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
                  <td className="py-1.5 px-2 text-right text-xs tabular-nums text-muted-foreground whitespace-nowrap">
                    {hasOpponent
                      ? `${row.score.toFixed(2)} vs ${(row.opponent_score as number).toFixed(2)} (${diffLabel})`
                      : row.score.toFixed(2)}
                  </td>
                  <td className="py-1.5 px-2">
                    {hasOpponent ? (
                      <MiniBulletChart
                        value={diff}
                        neutralMin={NEUTRAL_ZONE_MIN}
                        neutralMax={NEUTRAL_ZONE_MAX}
                        domain={BULLET_DOMAIN}
                        ariaLabel={`${BUCKET_DISPLAY_LABELS[row.bucket]}: ${diffLabel} vs opponent`}
                      />
                    ) : (
                      <span
                        className="text-xs text-muted-foreground"
                        data-testid={`material-row-${row.bucket}-muted`}
                      >
                        n &lt; {MIN_OPPONENT_BASELINE_GAMES} — baseline unavailable
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
          const hasOpponent =
            row.opponent_score !== null &&
            row.opponent_games >= MIN_OPPONENT_BASELINE_GAMES;
          const diff = hasOpponent ? row.score - (row.opponent_score as number) : 0;
          const diffLabel = (diff >= 0 ? '+' : '') + diff.toFixed(2);
          const opponentFormatted = hasOpponent
            ? (row.opponent_score as number).toFixed(2)
            : null;
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
                <div className="flex items-baseline justify-between text-xs mb-1">
                  <span className="text-muted-foreground">
                    {opponentFormatted !== null
                      ? `Score vs Opponent (${opponentFormatted})`
                      : 'Score vs Opponent'}
                  </span>
                  <span className="tabular-nums text-muted-foreground">
                    {hasOpponent
                      ? `${row.score.toFixed(2)} (${diffLabel})`
                      : row.score.toFixed(2)}
                  </span>
                </div>
                {hasOpponent ? (
                  <MiniBulletChart
                    value={diff}
                    neutralMin={NEUTRAL_ZONE_MIN}
                    neutralMax={NEUTRAL_ZONE_MAX}
                    ariaLabel={`${BUCKET_DISPLAY_LABELS[row.bucket]}: ${diffLabel} vs opponent`}
                  />
                ) : (
                  <span
                    className="text-xs text-muted-foreground block"
                    data-testid={`material-card-${row.bucket}-muted`}
                  >
                    n &lt; {MIN_OPPONENT_BASELINE_GAMES} — baseline unavailable
                  </span>
                )}
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
