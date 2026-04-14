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
import { ZONE_DANGER, ZONE_NEUTRAL, ZONE_SUCCESS } from '@/lib/theme';
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
                  Games are split by the material balance on entering the endgame:
                  <strong> Conversion</strong> (you lead by ≥ +1),
                  <strong> Even</strong> (roughly balanced), or
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
          How well do you convert a material advantage into a win and defend
          when you're down material?
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
              <th className="py-1 px-2 font-medium text-right"></th>
              <th className="py-1 px-2 font-medium">
                Your vs Opponents' Score
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
                  <td className="py-1.5 px-2 text-right text-xs tabular-nums text-muted-foreground whitespace-nowrap">
                    {hasOpponent ? (
                      <>
                        {row.score.toFixed(2)} −{' '}
                        {(row.opponent_score as number).toFixed(2)} ={' '}
                        <span style={{ color: diffColor }}>{diffLabel}</span>
                      </>
                    ) : (
                      row.score.toFixed(2)
                    )}
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
                <div className="text-xs text-muted-foreground mb-1 tabular-nums">
                  {opponentFormatted !== null ? (
                    <>
                      Your vs Opponents' Score: {row.score.toFixed(2)} -
                      {opponentFormatted} ={' '}
                      <span style={{ color: diffColor }}>{diffLabel}</span>
                    </>
                  ) : (
                    <>Your Score ({row.score.toFixed(2)})</>
                  )}
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
