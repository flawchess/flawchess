# Tilt study: methods review and recommendations

Reviewed 2026-09-16. This document records the review of the article, technical report,
analysis code, and cached results, and recommends work before publication. It does not
implement corrections or present corrected estimates.

The new `study/tilt` branch starts from `ec2eda978` on `main`, which incorporates the
previous branch's article and chart edits. The numerical diagnostics below were run
during the preceding review against the existing cached extracts. The underlying
analysis code and technical report were unchanged by those article edits. The database
extraction and complete analysis pipeline were not rerun for this review.

## Assessment of the contribution

The study is worthwhile. Its strongest contribution is demonstrating how much of the
dramatic raw association between streaks and subsequent results disappears after
accounting for opponents and playing context. Reproducing that pattern and then
examining its sources is a useful challenge to popular interpretations of chess data.

Two claims need to remain distinct:

- **Raw streak statistics exaggerate the evidence for psychological tilt.** The
  analysis provides substantial support for this interpretation, subject to correcting
  the timing and checking robustness to the filters.
- **Psychological tilt itself is small or overrated.** This is a plausible hypothesis,
  but the current analysis cannot establish it generally.

A small average association among people who keep playing can coexist with severe
but uncommon tilt, large effects in some individuals, players successfully stopping
when tilted, or other players responding to losses with greater concentration.
The study measures neither emotional state nor the outcomes of unplayed games.

The residual is not automatically an upper bound on tilt. Omitted influences can
inflate it or offset it. For example, rating updates after losses can leave a
constant-strength player temporarily under-rated. Small net underperformance does
not establish that every underlying mechanism is small.

A defensible central message is:

> Losing streaks are weaker evidence of tilt than they look. Much of the dramatic
> next-game pattern disappears after accounting for opponents and playing context.
> Among players who continue, the remaining association is small on average; these
> data do not establish how much is emotional tilt or whether stopping improves results.

## What the study already does well

The review considered these existing controls; they are not missing work:

- Full histories are retained for sequence features while scored outcomes use the
  equal-footing filter.
- The expectation accounts for time-control bucket, rating band, rating difference,
  and colour, rather than assuming perfect Elo calibration.
- The principal streak analysis separates fresh opponents from rematches.
- Confidence intervals resample users, recognizing dependence between a user's games.
- The technical report includes trailing-form and player-demeaning checks.
- The report discusses selection into computer analysis and limitations of the
  separately engine-analysed sample.
- Observational selection and cohort limitations are acknowledged in the report.

The article is often more categorical than that report. Its latest calendar paragraph
appropriately acknowledges that a bad mood can last across days and explains the
narrower within-session question. The raw-result introduction also now explicitly
describes this dataset. Neither change resolves the concerns below.

## Findings requiring correction

### 1. Game-end reconstruction uses minimum clocks instead of final clocks

In [`extract_clocks.py`](../../analysis/tilt_study/extract_clocks.py), the SQL uses
`min(clock_seconds)` for each side and names the results `w_last_clk` and `b_last_clk`.
With increments, a clock can rise after reaching its minimum. The minimum therefore
does not necessarily represent the last recorded clock.

[`story_data.py`](../../analysis/tilt_study/story_data.py) subtracts those values in
its duration calculation. Relative to using the actual last readings, this can
overestimate duration and shorten the estimated break. Session assignments, streak
eligibility, break groups, and quit/rush measures depend on these times.

Diagnostics from the cached feature frame:

| Diagnostic | Result |
|---|---:|
| Negative gaps in the break-analysis frame | 7,060 |
| Games in that frame | 450,070 |
| Negative-gap share of rapid's under-one-minute break group | 7.8% |
| Negative-gap share of classical's under-one-minute break group | 75.3% |

Negative gaps are currently admitted to the under-one-minute category. These figures
do not establish that every negative gap comes from the minimum-clock bug; they show
that timing validity needs attention before interpreting the results.

**Recommendation:** extract the last non-null clock by move order for each side.
Validate clock coverage and the increment convention. Distinguish the last recorded
move from actual game termination: resignation, flagging, and disconnection can occur
later. Prefer validated end timestamps where available, and document approximation
error otherwise. Investigate negative gaps rather than simply clamping them to zero.

Rebuild all dependent features and tables after correction. The generator currently
reuses `features.parquet` whenever it exists, so running it again alone is insufficient.
Add cache invalidation or explicit rebuild instructions.

### 2. The stop-loss calculation is not a stopping-policy estimate

In [`gen_story.py`](../../analysis/tilt_study/gen_story.py), the stop-rule calculation is
the share of scored games following two or more same-session losses against fresh
opponents multiplied by their mean residual. The magnitude is approximately 0.07
score points per 100 games.

This is the aggregate observed shortfall in a subset, not the benefit of stopping.
Interpreting it as a saving assumes those games would be replaced by comparable games
with zero residual. The calculation does not model recovery, replacement games, or
all subsequent games removed by ending a session. It also excludes rematches despite
the article describing a rule for everyone.

**Recommendation:** present this only as an aggregate scale comparison, with its
denominator and assumptions explicit. Remove “would have saved,” “forget the stop-loss
rule,” and “if anything, keep playing” unless a separate intervention analysis can
support them. The limitation applies even to observed continuers: their outcome under
stopping is still unobserved.

The latest introduction says “stop after three losses,” while the calculation and
takeaway concern two. Align these definitions.

### 3. First-rematch classification shifts an already-filtered sequence

The generator computes `prev_rematch` after restricting the data to eligible scored,
in-session games. Consequently, the shifted flag can describe the previous retained
game rather than the actual preceding game.

Computing that shift on the full ordered history changes the flag for 4,468 of
108,308 rematches in the cached comparison.

**Recommendation:** compute the preceding-rematch flag on the full user/time-control
sequence, then apply the scoring filters. Regenerate the first-versus-later-rematch
comparison. This diagnostic does not itself quantify the change in its score estimates.

### 4. Some article numbers have missing denominators or are stale

- The rapid rush rates of 53% after losses and 43% after wins are conditional on
  continuing within the session. Across all eligible rapid losses and wins, the cached
  rates are 32.9% and 27.9%. Name the conditional denominator. Rapid players also quit
  more often after losses, so “do the opposite” is misleading.
- The footer reports reliability 0.19 and approximately 80% noise. The current report
  and generated output give reliability 0.113, corresponding under the reliability
  calculation to approximately 89% noise variance. Avoid implying that this percentage
  describes the error of every individual's estimate.
- A deficit in expected score is not uniquely an increase in loss probability, because
  draws can change too. Prefer “one fewer score point per 180 games” to “one extra loss,”
  or explicitly label a win-to-loss conversion as an illustrative equivalence.

## Interpretation concerns

### Residual underperformance is not a direct measurement of tilt

The hero, prose, and revised chart label the controlled residual as psychological
tilt. Possible remaining explanations include persistent distraction, fatigue,
changing strength, exact time-control mix, and selection into continued play.

The report's own player-demeaning check materially weakens the headline:

| Previous losses | Main residual, pp | Player-demeaned residual, pp | Demeaned 95% interval |
|---|---:|---:|---|
| Exactly three | -0.564 | -0.152 | -0.654 to +0.337 |
| Six or more | -2.147 | -1.423 | -2.845 to +0.143 |

This is not proof of no tilt. It does show that “tilt is real” is too categorical,
and that the three-loss headline is more sensitive than the statement that the tails
shrink by a third suggests. Demeaning the outcome alone is also not equivalent to a
joint fixed-effects regression containing the streak predictors.

**Recommendation:** call the quantity “score relative to the benchmark” or
“post-streak residual.” Put the player-adjusted sensitivity near the headline. Label
chart regions descriptively rather than presenting a causal partition into “Tilt”
and “Not tilt.” The filter ladder changes the population as well as the estimate;
it is not a clean decomposition of causal contributions.

### Break-group convergence does not identify recovery

People pausing after wins and losses can differ even at the same break length.
Comparing their residuals does not automatically remove selection.

At 30–60 minutes, the post-win and post-loss residuals are approximately -1.8 and
-2.0 pp. Their convergence largely reflects the post-win group's decline, not the
post-loss group's return to the benchmark. The difference's interval also includes
meaningful positive and negative values.

The analysis observes the next game after different gaps. It does not track the
evolution of a state over elapsed time among people who continue playing, so it cannot
establish that a streak effect fades “whether you pause or not.”

**Recommendation:** after correcting timing, describe a smaller association at longer
gaps without claiming a recovery time or a causal benefit or cost of taking a break.

### Rematch asymmetry cannot be assigned to mood

The claim that approximately one point of the rematch penalty is mood assumes that
matchup selection after wins and losses is symmetric and that other sources of
asymmetry are absent. Both players select into rematches; their decisions may depend
on how the previous game unfolded. The post-win comparison does not identify a
numerical decomposition into matchup and emotion.

**Recommendation:** retain the descriptive comparison, after fixing series position,
but remove “the rest ... is the mood” and causal language about the cost of choosing
a rematch.

### Secondary mechanisms are plausible interpretations, not established findings

- **Time control and rating:** larger estimated shortfalls in rapid and the lowest
  rating band do not establish that longer games cause stronger emotional carryover
  or that tilt is mainly a beginner's problem. Compare groups directly and standardize
  relevant composition before making strong group claims.
- **Move quality:** the engine-analysed subset is selected, and opponents' blunder
  rates also rise. Preserve the report's uncertainty between game composition and
  behavioural explanations. “Tilt shows up on the board after three” is too strong.
- **Endgames:** an evaluation of +2 at endgame entry is not necessarily a material
  lead of two pawns, nor evidence that the position remained winning when a player
  flagged. “No detectable average shortfall among continuers” is more accurate than
  “leaves no mark.”
- **Short losses and disconnects:** persistent technical problems or distraction
  are alternatives to psychological tilt. Their association with another poor result
  does not establish a player's emotional state.

## Prioritized additional analysis

### Priority 1: repair and check stability

1. Correct and validate timing, fix rematch sequence position, and rebuild dependent
   caches, report tables, chart data, and prose figures.
2. Show sensitivity to reasonable session boundaries and the account-history filters.
   In particular, examine the long-run rating-deviation filter: streaks move ratings,
   and the long-run median uses future as well as past information.
3. Keep the equal-footing analysis primary, in accordance with the study's rules.
   Make sample changes and exclusions visible in all sensitivity comparisons.

### Priority 2: strengthen the within-player evidence

Fit a joint model with player effects, streak predictors, rating difference, colour,
exact clock setting, and session depth or elapsed playing time. Choose and document
the estimand before adding controls: some variables may be consequences of earlier
losses rather than baseline confounders.

Report standardized differences in score percentage points with uncertainty clustered
by player. Compare these with the existing pooled and demeaned estimates. This asks
whether the same player performs differently after losses at comparable moments; it
still does not identify an emotional mechanism.

The present bootstrap operates on already-computed residuals. Consider refitting the
estimated expectation within resamples, or an appropriate joint-model procedure, so
uncertainty in the benchmark is represented. Do not assume in advance which direction
this will move the intervals.

### Priority 3: test the pipeline under explicit no-tilt models

Simulate sequences with player-strength differences and rating updates but no
psychological carryover, and apply the same feature construction and filters. Extend
the diagnostic to slowly changing strength or session-level form without an effect
of losing itself.

Determine whether these mechanisms alone can create a residual streak curve. Specify
how opponents, continuation, and session boundaries are generated or conditioned on;
results depend on those assumptions. Simple outcome shuffling destroys much of this
structure and is not sufficient. These are model checks, not causal proof.

### Priority 4: expose continuation selection

Plot the probability of continuing after each loss-streak length beside the performance
estimate, and describe differences between continuers and stoppers. Handle the final
observed game in a history as potentially censored rather than automatically treating
it as a voluntary stopping decision.

This cannot recover the outcomes of unplayed games. It clarifies how far the evidence
can support claims about all players, and whether apparent small effects coexist with
people successfully choosing to stop.

## Publication recommendation

The timing correction and factual fixes are necessary before publication. A focused
robustness and within-player analysis would substantially strengthen the main story.
No-tilt simulations and continuation analysis would make the broader challenge to
conventional wisdom more convincing. Elaborate causal break or rematch analyses are
not prerequisites if those sections remain explicitly descriptive.

The strongest article challenges the usual evidence for a large tilt effect while
remaining clear about what the study measures. It need not prove that tilt is absent
to make a valuable and potentially controversial contribution.
