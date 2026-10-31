import type { ReactNode } from 'react';
import { Link } from 'react-router';
import { Cpu } from 'lucide-react';
import { Accordion, AccordionItem, AccordionTrigger, AccordionContent } from '@/components/ui/accordion';
import { Button } from '@/components/ui/button';
import { EmptyState } from '@/components/ui/empty-state';
import { LoadError } from '@/components/ui/load-error';
import { EndgameInsightsBlock } from '@/components/insights/EndgameInsightsBlock';
import { ShellyQuote } from '@/components/insights/ShellyQuote';
import { useEndgameRankedStats } from '@/hooks/useEndgames';
import type { EndgameClass } from '@/types/endgames';
import type { SectionId } from '@/types/insights';
import { MetricsSection } from './stats/MetricsSection';
import { OverallSection } from './stats/OverallSection';
import { TimePressureSection } from './stats/TimePressureSection';
import { TypeTable } from './stats/TypeTable';
import { EndgameStatsTcSwitch } from './stats/EndgameStatsTcSwitch';
import { StickyTcBar } from '@/components/stats/StickyTcBar';
import { useEndgameInsightsState } from './useEndgameInsightsState';
import type { SectionInsight } from './useEndgameInsightsState';

// ── Concepts accordion ───────────────────────────────────────────────────────

function EndgameConceptsAccordion() {
  return (
    <Accordion type="single" collapsible>
      <AccordionItem value="concepts" className="charcoal-texture rounded-md overflow-hidden" data-testid="endgame-concepts-trigger">
        <AccordionTrigger band>
          <span className="flex items-center gap-2 flex-1">
            <h3 className="text-base font-semibold text-foreground">Endgame Statistics Concepts</h3>
          </span>
        </AccordionTrigger>
        <AccordionContent className="text-muted-foreground space-y-2 p-4">
          <p>
            <strong>Percentile bars:</strong> every ranked metric has a bar per time control. The dot
            shows where you stand among players of similar rating in that time control: red below
            the 25th percentile, blue from the 25th to the 75th, green above the 75th. The lighter
            middle band is the typical half of similar-rated players, and the faint tick marks the
            median. Tap or hover the magnifier next to a metric for what it measures and how
            sure we are.
          </p>
          <p>
            <strong>Grey typical range:</strong> where there is no peer percentile (the Endgame Type
            Breakdown table, the Clock Gap timeline and the score-vs-clock curve), a grey band marks
            the typical range for similar players instead. In the two charts, dots are green above
            the range, red below it and blue inside it. In the type table a value turns red below
            the range and green above it.
          </p>
          <p>
            <strong>Your ranked games:</strong> the Stats tab uses your recent ranked games: rated
            games against human opponents within ±100 Elo of your rating, from the last 36 months,
            up to 1,000 games per time control. Every number, bar and chart on this tab comes from
            that same sample, so a value and its percentile always describe the same games. Filters
            only apply on the Games tab.
          </p>
          <p>
            <strong>FlawChess Benchmark:</strong> a stratified sample of Lichess players across rating
            and time control buckets, used to rank each metric. The latest run is published as the
            {' '}
            <a
              href="https://github.com/flawchess/flawchess/blob/main/reports/benchmark/benchmarks-latest.md"
              data-umami-event="outbound-report-benchmarks"
              className="text-primary underline-offset-4 hover:underline"
              target="_blank"
              rel="noopener noreferrer"
            >
              FlawChess Benchmark
            </a>
            {' '}report. Your percentile is computed in four steps, separately for each time control:
          </p>
          <ol className="list-decimal pl-6 space-y-1">
            <li>
              <strong>Anchor your rating.</strong> We take the median of your rating at game time
              across your ranked games in that time control. chess.com ratings are converted to
              Lichess-equivalent via the{' '}
              <a
                href="https://chessgoals.com/rating-comparison"
                data-umami-event="outbound-chessgoals"
                className="text-primary underline-offset-4 hover:underline"
                target="_blank"
                rel="noopener noreferrer"
              >
                ChessGoals rating conversion tables
              </a>
              {' '}so everyone is compared on the same scale.
            </li>
            <li>
              <strong>Pick the matching peer cohort.</strong> From the FlawChess Benchmark, we select
              all Lichess players within +/-200 Elo of your anchor in the same time control. A cell
              only qualifies if at least 100 benchmark users fall in that window, otherwise the bar
              shows that the metric is not ranked yet.
            </li>
            <li>
              <strong>Compute your metric value.</strong> The same metric (Endgame Score Gap,
              Conversion, Recovery, Eval Score Gap, etc.) is computed on your ranked games, the same
              way it is computed for each benchmark user.
            </li>
            <li>
              <strong>Look up your percentile.</strong> For each time control the benchmark cell
              stores 99 precomputed percentile breakpoints per metric; your value is interpolated
              against those breakpoints. Percentiles are never averaged across time controls.
            </li>
          </ol>
          <p>
            <strong>Endgame Phase:</strong> positions where the total count of major and minor pieces
            (queens, rooks, bishops, knights) across both sides is at most 6. Kings and pawns are not
            counted. This follows the Lichess definition. A game is only counted as having an Endgame
            Phase if it spans at least 3 full moves (6 half-moves) in the endgame. Shorter tactical transitions from middlegame into a checkmate are treated as no endgame.
          </p>
          <p>
            <strong>Endgame Types:</strong> Rook, Minor Piece (bishops/knights), Pawn (king and pawns only),
            Queen, and Mixed (two or more piece types).
          </p>
          <p>
            <strong>Endgame Sequence:</strong> a continuous stretch of at least 3 full moves (6 half-moves)
            spent in a single Endgame Type. A single game can produce multiple sequences. For example,
            a rook endgame where the rooks get traded becomes a pawn endgame, giving that game one rook
            sequence and one pawn sequence. Sequences drive the Endgame Type Breakdown, so a game can appear
            under more than one type.
          </p>
          <p>
            <strong>Score:</strong> your result as a percentage, counting each win as a
            full point and each draw as a half point (so 3 wins, 2 draws and 1 loss over
            6 games is 67%). 50% is an even result against equally matched opponents.
          </p>
          <p>
            <strong>Score Gap:</strong> the difference between two Scores. Positive means
            the first Score is the higher of the two, negative means it is lower.
          </p>
          <p>
            <Cpu className="inline h-4 w-4 -mt-0.5 mr-1" aria-hidden="true" />
            <strong>Eval:</strong> the Stockfish evaluation of a position, in pawns and from
            your perspective, where positive means you stand better (+1.0 is a one-pawn
            advantage). Metrics that are based on the engine are marked with this chip icon.
          </p>
          <p>
            <Cpu className="inline h-4 w-4 -mt-0.5 mr-1" aria-hidden="true" />
            <strong>Eval Score:</strong> an Eval converted into a Score with the{' '}
            <a
              href="https://lichess.org/page/accuracy"
              data-umami-event="outbound-lichess-accuracy"
              className="text-primary underline-offset-4 hover:underline"
              target="_blank"
              rel="noopener noreferrer"
            >
              Lichess expected-score formula
            </a>
            , so engine evaluations and actual results sit on the same scale. A +1.0 Eval
            is roughly a 60% Eval Score.
          </p>
          <p>
            <Cpu className="inline h-4 w-4 -mt-0.5 mr-1" aria-hidden="true" />
            <strong>Eval Score Gap:</strong> the gap between an Eval Score and another Score.
            Across your overall endgames it is your Endgame Score minus your Entry Eval Score
            (did you beat the engine's expectation for the positions you reached?); within an
            Endgame Sequence it is the change in Eval Score from start to end. Positive means
            you came out ahead of the engine's expectation, negative means you fell short.
          </p>
          <p>
            <strong>Conversion:</strong> percentage of games where you entered the endgame with a
            Stockfish evaluation of +1.0 or better (you ahead by at least one pawn of advantage)
            and went on to win. Measures how well you close out winning endgames.
          </p>
          <p>
            <strong>Parity:</strong> percentage of games where you entered the endgame with a
            Stockfish evaluation between -1.0 and +1.0 (roughly balanced). Score counts draws as
            half. Measures how well you handle balanced endgames.
          </p>
          <p>
            <strong>Recovery:</strong> percentage of games where you entered the endgame with a
            Stockfish evaluation of -1.0 or worse (you behind by at least one pawn of disadvantage)
            and drew or won. Measures how well you defend losing endgames.
          </p>
          <p>
            <Cpu className="inline h-4 w-4 -mt-0.5 mr-1" aria-hidden="true" />
            <strong>Entry Eval:</strong> the average Stockfish evaluation of
            the position where the endgame begins, measured in pawns from your perspective
            (positive means you have the better position). Mate scores are excluded.
          </p>
          <p>
            <Cpu className="inline h-4 w-4 -mt-0.5 mr-1" aria-hidden="true" />
            <strong>Entry Eval Score:</strong> your Entry Eval converted to a Score with the{' '}
            <a
              href="https://lichess.org/page/accuracy"
              data-umami-event="outbound-lichess-accuracy"
              className="text-primary underline-offset-4 hover:underline"
              target="_blank"
              rel="noopener noreferrer"
            >
              Lichess expected-score formula
            </a>
            , i.e. what a strong player would expect to score from your endgame-entry
            positions. The curve is fitted on 2300+ rapid games, so scoring a little below
            it from positive evals is normal at lower ratings. Compare it against your
            Endgame Score to see how well you convert the positions you reach.
          </p>
          <p>
            <strong>Endgame Score:</strong> your win rate (with draws counted as half)
            across all games that reach an endgame. 50% is the baseline against rating-matched
            opponents.
          </p>
          <p>
            <strong>Endgame Score Gap:</strong> the score difference between games that reach an endgame (Endgame Score) vs. games that end before (Non-Endgame Score). Positive means endgames are your strength; negative
            means you perform worse once games reach an endgame.
          </p>
          <p>
            <strong>Endgame ELO and Non-Endgame ELO:</strong> what your rating would be if your whole
            game played at the level of just your endgame games, or just your non-endgame games. Both
            sit symmetrically around your Actual ELO: we take your trailing-window score on each side
            (S_E for endgame games, S_N for non-endgame games), convert the score gap into an ELO
            spread via the Elo logistic, and split it across the two lines:
            {' '}
            <code>
              spread = 400 · log₁₀((S_E / (1 − S_E)) / (S_N / (1 − S_N)))
            </code>
            , {' '}
            <code>Endgame ELO = Actual ELO + spread / 2</code>, {' '}
            <code>Non-Endgame ELO = Actual ELO − spread / 2</code>. The midpoint
            equals your Actual ELO by construction. When Endgame ELO sits above Non-Endgame ELO your
            endgame play is lifting your rating (green band); when it sits below, your endgame is
            holding it back (red band).
          </p>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  );
}

// ── SectionInsightSlot ──────────────────────────────────────────────────────
// Renders a per-section insight (headline + 0-2 bullets) at the top of each H2
// group, under the section question, when the backend returned a matching
// section_id. Returns null when no matching data exists, e.g. pre-generate state,
// or any section the LLM chose to omit. The headline is Shelly's italic quote and
// the bullets start collapsed.
function SectionInsightSlot({
  sectionId,
  data,
}: {
  sectionId: SectionId;
  data: SectionInsight;
}) {
  if (!data) return null;

  // Header band content shared by both the plain (headline-only) and the
  // collapsible (headline + bullets) variants; only the latter gets the hint.
  const headline = (expandHint: boolean) => (
    <ShellyQuote
      text={data.headline}
      avatarClassName="size-10.5"
      className="text-sm font-semibold"
      expandHint={expandHint}
    />
  );

  // No bullets: nothing to fold, so render a plain header card without a
  // chevron rather than a collapsible with an empty body.
  if (data.bullets.length === 0) {
    return (
      <div
        data-testid={`insights-section-${sectionId}`}
        className="charcoal-texture rounded-md overflow-hidden"
      >
        <div className="w-full flex items-center gap-2 px-4 py-3 bg-card-band">
          {headline(false)}
        </div>
      </div>
    );
  }

  return (
    <Accordion type="single" collapsible>
      <AccordionItem
        value="insight"
        data-testid={`insights-section-${sectionId}`}
        className="charcoal-texture rounded-md overflow-hidden"
      >
        <AccordionTrigger
          data-testid={`insights-section-${sectionId}-trigger`}
          band
        >
          {headline(true)}
        </AccordionTrigger>
        <AccordionContent className="p-4">
          <ul className="list-disc list-outside pl-5 space-y-1 text-sm text-muted-foreground">
            {data.bullets.map((b, i) => (
              <li key={i}>{b}</li>
            ))}
          </ul>
        </AccordionContent>
      </AccordionItem>
    </Accordion>
  );
}

// ── Tab ──────────────────────────────────────────────────────────────────────

const LOADING_COPY = 'Loading endgame analytics...';

interface EndgameStatsTabProps {
  tier2: boolean;
  onCategorySelect: (category: EndgameClass) => void;
}

/**
 * The Endgame Stats tab: the Shelly block, the concepts accordion and
 * the four sections, all driven by the ranked-sample payload and the synced time
 * control switch. The tab takes no filter state: filters only apply on the Games tab.
 */
export function EndgameStatsTab({ tier2, onCategorySelect }: EndgameStatsTabProps) {
  const ranked = useEndgameRankedStats({ enabled: tier2 });
  const tcs = ranked.data?.tcs ?? [];
  // Auto-generate only once the ranked sample has games to narrate.
  const { generateState, insights, handleGenerateInsights, insightBySection } =
    useEndgameInsightsState({ autoGenerate: tcs.length > 0 });

  let body: ReactNode;
  if (ranked.isLoading) {
    body = (
      <div className="charcoal-texture rounded-md p-12 flex items-center justify-center">
        <p className="text-muted-foreground">{LOADING_COPY}</p>
      </div>
    );
  } else if (ranked.isError) {
    body = <LoadError variant="centered" resource="endgame stats" />;
  } else if (tcs.length === 0) {
    // No qualifying game in any TC. Name what counts and point to the Games tab.
    body = (
      <EmptyState
        layout="page"
        data-testid="endgame-stats-empty-state"
        title="No ranked games yet"
        subtitle="The Stats tab compares your rated games against human opponents within ±100 Elo of your rating, played in the last 36 months. None of your games qualify yet."
        action={
          <Button variant="brand-outline" asChild>
            <Link to="/endgames/games" data-testid="btn-empty-see-endgame-games">
              See all your endgame games
            </Link>
          </Button>
        }
      />
    );
  } else {
    body = (
      <>
        <EndgameConceptsAccordion />
        {/* One TC switch for every section, pinned while the sections scroll. */}
        <div>
          <StickyTcBar testId="endgame-stats-tc-bar">
            <EndgameStatsTcSwitch tcs={tcs} />
          </StickyTcBar>
          <div className="flex flex-col gap-4">
            <OverallSection tcs={tcs}>
              <SectionInsightSlot sectionId="overall" data={insightBySection.overall} />
            </OverallSection>
            <MetricsSection tcs={tcs}>
              <SectionInsightSlot sectionId="metrics_elo" data={insightBySection.metrics_elo} />
            </MetricsSection>
            <TimePressureSection tcs={tcs}>
              <SectionInsightSlot sectionId="time_pressure" data={insightBySection.time_pressure} />
            </TimePressureSection>
            <TypeTable tcs={tcs} onCategorySelect={onCategorySelect}>
              <SectionInsightSlot sectionId="type_breakdown" data={insightBySection.type_breakdown} />
            </TypeTable>
          </div>
        </div>
      </>
    );
  }

  return (
    <div className="flex flex-col gap-4" data-testid="endgame-stats-tab">
      <EndgameInsightsBlock
        insights={insights}
        generateState={generateState}
        onGenerate={handleGenerateInsights}
      />
      {body}
    </div>
  );
}
