"""Assemble the tilt technical report (stories/tilt/tilt-report.md) from the story tables.

Prose lives here; every table is rendered from analysis/out/tilt/story/*.csv, which
gen_story.py and robustness.py write, so the report can never drift from the numbers.
The headline figures quoted in the prose are read from the same tables.

Run: uv run --project analysis python analysis/tilt_study/gen_story.py
     uv run --project analysis python analysis/tilt_study/robustness.py
     uv run --project analysis python analysis/tilt_study/gen_report.py
"""

import json
from pathlib import Path

import polars as pl

REPO = Path(__file__).resolve().parents[2]
STORY = REPO / "analysis" / "out" / "tilt" / "story"
REPORT = REPO / "stories" / "tilt" / "tilt-report.md"
REVISED = "2026-09-16"
GAMES_PER_POINT = 100  # 1 pp of score = 1 point per 100 games


def load(name: str) -> pl.DataFrame:
    return pl.read_csv(STORY / f"{name}.csv")


def fmt_cell(v: object) -> str:
    if v is None:
        return ""
    if isinstance(v, float):
        return f"{v:.1f}" if abs(v) < 1000 else f"{v:,.0f}"
    if isinstance(v, int):
        return f"{v:,}"
    return str(v)


def table(df: pl.DataFrame, cols: list[tuple[str, str]] | None = None) -> str:
    """Markdown table; cols = [(source column, header)] to select and rename."""
    if cols:
        df = df.select([pl.col(c).alias(h) for c, h in cols])
    head = "| " + " | ".join(df.columns) + " |\n|" + "---|" * len(df.columns)
    body = "\n".join("| " + " | ".join(fmt_cell(v) for v in row) + " |" for row in df.iter_rows())
    return head + "\n" + body


def ci(df: pl.DataFrame, mean: str, lo: str, hi: str, name: str) -> pl.DataFrame:
    return df.with_columns(
        (
            pl.col(mean).map_elements(lambda v: f"{v:+.1f}", return_dtype=pl.Utf8)
            + " ["
            + pl.col(lo).map_elements(lambda v: f"{v:+.1f}", return_dtype=pl.Utf8)
            + ", "
            + pl.col(hi).map_elements(lambda v: f"{v:+.1f}", return_dtype=pl.Utf8)
            + "]"
        ).alias(name)
    )


def xlab(x: int) -> str:
    k = abs(x)
    if x == 0:
        return "draw"
    return f"{k}{'+' if k == 6 else ''} {'loss' if x < 0 else 'win'}{'es' if (k > 1 and x < 0) else ('s' if k > 1 else '')}"


def pick(df: pl.DataFrame, col: str, **where: object) -> float:
    """The single value of `col` in the row where every `where` column equals its value."""
    d = df
    for k, v in where.items():
        d = d.filter(pl.col(k) == v)
    if d.height != 1:
        raise ValueError(f"{where} matched {d.height} rows")
    return float(d[col][0])


def games_per_loss(pp: float) -> int:
    """Illustrative equivalence: |pp| points per 100 games = one win turned into a loss every N games."""
    return round(GAMES_PER_POINT / abs(pp))


pop = json.loads((STORY / "population.json").read_text())
trait = json.loads((STORY / "trait.json").read_text())
design = json.loads((STORY / "within_player_design.json").read_text())

lad = (
    load("ladder6")
    .filter(pl.col("x") != 0)
    .with_columns(pl.col("x").map_elements(xlab, return_dtype=pl.Utf8).alias("streak"))
)
lad = ci(lad, "resid", "resid_lo", "resid_hi", "residual")
sc = load("streak_curve")
curve_tc = load("streak_curve_tc").filter(pl.col("x") != 0)
curve_elo = load("streak_curve_elo").filter(pl.col("x") != 0)
colour = load("streak_curve_colour_check").filter(pl.col("x") != 0)
form = load("form_control")
fe = load("streak_curve_player_fe").filter(pl.col("x") != 0)
s3tc = ci(
    ci(load("streak3_by_tc"), "cold_resid", "cold_lo", "cold_hi", "after 3+ losses"),
    "hot_resid",
    "hot_lo",
    "hot_hi",
    "after 3+ wins",
)
s3elo = ci(
    ci(load("streak3_by_rating"), "cold_resid", "cold_lo", "cold_hi", "after 3+ losses"),
    "hot_resid",
    "hot_lo",
    "hot_hi",
    "after 3+ wins",
)
s3cell = ci(
    ci(load("streak3_by_cell"), "cold_resid", "cold_lo", "cold_hi", "after 3+ losses"),
    "hot_resid",
    "hot_lo",
    "hot_hi",
    "after 3+ wins",
)
brk = ci(
    ci(load("break_test"), "cold_resid", "cold_lo", "cold_hi", "after 2+ losses"),
    "hot_resid",
    "hot_lo",
    "hot_hi",
    "after 2+ wins",
)
brk = ci(brk, "gap_hot_minus_cold", "gap_lo", "gap_hi", "gap (hot minus cold)")
brk_all = load("break_test").filter(pl.col("tc") == "all")
shares = load("break_shares").filter(pl.col("gap_bucket") == "<1 min")
stop = load("stop_rule")
fatigue = load("fatigue")
ploss = load("p_loss_after_k")
quit_ = load("quit_rush")
rev = load("revenge")
rev_elo = load("revenge_by_rating")
rev_series = load("revenge_series")
speed = load("speed")
blunders = load("blunders")
shape = load("next_loss_shape")
timing = load("timing_diagnostics")
sens = load("sensitivity")
within = load("within_player")
swings = load("within_player_swings")
cont = load("continuation")
analysed = ci(
    ci(
        load("analysed_by_streak").with_columns(
            pl.col("x").map_elements(xlab, return_dtype=pl.Utf8).alias("streak")
        ),
        "analysed_pct",
        "analysed_lo",
        "analysed_hi",
        "analysed % [95% CI]",
    ),
    "demeaned_pp",
    "demeaned_lo",
    "demeaned_hi",
    "vs player's own rate, pp [95% CI]",
).with_columns(pl.col("analysed % [95% CI]").str.replace_all(r"\+", ""))  # rates are unsigned
analysed = ci(analysed, "deep_pp", "deep_lo", "deep_hi", "same, session games 6–15 only [95% CI]")
an_raw = load("analysed_by_streak")


def anat(name: str) -> str:
    d = load(name)
    cols = [("previous loss", "previous loss")]
    for tc in ["all", "bullet", "blitz", "rapid", "classical"]:
        d = ci(d, f"{tc}_resid", f"{tc}_lo", f"{tc}_hi", tc)
        cols.append((tc, tc))
    cols.insert(1, ("all_n", "games"))
    return table(d, cols)


def anat_val(name: str, cat: str, col: str = "all_resid") -> float:
    return pick(load(name), col, **{"previous loss": cat})


def pivot_curve(df: pl.DataFrame, key: str, col: str) -> str:
    p = df.pivot(on="x", index=key, values=col)
    p = p.rename({c: xlab(int(c)) for c in p.columns if c != key})
    return table(p)


def within_table() -> str:
    """Streak contrasts (vs exactly one loss) side by side for the three model variants."""
    out = None
    for model in within["model"].unique(maintain_order=True).to_list():
        d = ci(within.filter(pl.col("model") == model), "contrast_pp", "lo", "hi", model).select(
            "streak", "n", model
        )
        out = d if out is None else out.join(d.drop("n"), on="streak")
    assert out is not None
    return table(
        out.sort("streak").with_columns(
            pl.col("streak").map_elements(xlab, return_dtype=pl.Utf8).alias("streak")
        )
    )


def swing_table() -> str:
    d = ci(swings, "hot_minus_cold_pp", "lo", "hi", "hot minus cold, pp [95% CI]")
    return table(
        d.with_columns(
            pl.col("streak").map_elements(
                lambda k: f"{k}{'+' if k == 6 else ''} wins vs {k}{'+' if k == 6 else ''} losses",
                return_dtype=pl.Utf8,
            )
        ),
        [
            ("model", "model"),
            ("streak", "contrast"),
            ("hot minus cold, pp [95% CI]", "hot minus cold, pp [95% CI]"),
        ],
    )


def sensitivity_table() -> str:
    d = ci(sens, "residual_pp", "lo", "hi", "v")
    p = d.pivot(on="streak", index="specification", values="v")
    return table(p.rename({c: xlab(int(c)) for c in p.columns if c != "specification"}))


def continuation_tables() -> tuple[str, str]:
    d = ci(cont, "continue_pct", "lo", "hi", "keeps playing % [95% CI]").with_columns(
        pl.col("keeps playing % [95% CI]").str.replace_all(r"\+", ""),
        pl.col("streak").map_elements(xlab, return_dtype=pl.Utf8).alias("streak just completed"),
    )
    pooled = table(
        d.filter(pl.col("tc") == "all"),
        [
            ("streak just completed", "streak just completed"),
            ("n", "games"),
            ("censored_or_unknown_timing", "censored / unknown timing"),
            ("keeps playing % [95% CI]", "next game within the hour % [95% CI]"),
            ("continuer_rating", "rating, continuers"),
            ("stopper_rating", "rating, stoppers"),
            ("continuer_session_idx", "game no. in session, continuers"),
            ("stopper_session_idx", "game no. in session, stoppers"),
        ],
    )
    p = cont.filter(pl.col("tc") != "all").pivot(on="streak", index="tc", values="continue_pct")
    by_tc = table(p.rename({c: xlab(int(c)) for c in p.columns if c != "tc"}))
    return pooled, by_tc


def sv(x: int, col: str = "resid") -> float:
    return pick(sc, col, x=x)


def wv(k: int, model: str = "player + ratings + clock", col: str = "contrast_pp") -> float:
    return pick(within, col, model=model, streak=k)


def sw(k: int, col: str = "hot_minus_cold_pp", model: str = "player + ratings + clock") -> float:
    return pick(swings, col, model=model, streak=k)


def s3(df: pl.DataFrame, key: str, val: object, col: str) -> float:
    return pick(df, col, **{key: val})


def q(tc: str, col: str) -> float:
    return pick(quit_, col, tc=tc)


def rv(tc: str, col: str) -> float:
    return pick(rev, col, tc=tc)


def rs(after: str, position: str, col: str = "rematch_minus_fresh") -> float:
    return pick(rev_series, col, after=after, position=position)


def bt(brk_label: str, col: str) -> float:
    return pick(brk_all, col, **{"break": brk_label})


def cv(streak: int, col: str = "continue_pct", tc: str = "all") -> float:
    return pick(cont, col, tc=tc, streak=streak)


def av(x: int, col: str) -> float:
    return pick(an_raw, col, x=x)


def tv(tc: str, col: str) -> float:
    return pick(timing, col, tc=tc)


def sens_v(spec: str, streak: int) -> float:
    return pick(sens, "residual_pp", specification=spec, streak=streak)


con_pooled, con_by_tc = continuation_tables()
first_clock_ok = (
    100
    - sum(
        tv(tc, "first_clock_mismatch_pct") * tv(tc, "games")
        for tc in ["bullet", "blitz", "rapid", "classical"]
    )
    / pop["games_total"]
)
neg_gaps = int(timing["negative_gaps"].sum())
resid_illustration = f"{sv(-3):+.1f}"
loss_share_LL = pick(stop, "share_of_games", tc="all")
shortfall_LL = pick(stop, "aggregate_shortfall_per_100_games", tc="all")
sens_specs = [
    s
    for s in sens["specification"].unique(maintain_order=True).to_list()
    if s not in ("primary", "zero increment only")
]
sens_range_6 = (min(sens_v(s, -6) for s in sens_specs), max(sens_v(s, -6) for s in sens_specs))
sens_range_p6 = (min(sens_v(s, 6) for s in sens_specs), max(sens_v(s, 6) for s in sens_specs))

md = f"""# The game after a losing streak. Technical report

Companion to the data story [You've lost three in a row. Should you stop?](https://stories.flawchess.com/tilt/).
Revised {REVISED} after a methods review (`analysis/tilt_study/methods-review.md`); the revision fixes a
game-end timing bug, a rematch-sequence bug, replaces the stop-rule and rematch attributions with
descriptive statements, and adds a within-player model, a sensitivity ladder and a continuation table.
Every number in the story comes from the tables below, generated by `analysis/tilt_study/gen_story.py`
and `analysis/tilt_study/robustness.py` from the cached extracts of the FlawChess benchmark database;
this document is assembled by `analysis/tilt_study/gen_report.py`. The exploratory analysis that
preceded the story, including a review of the published literature, is in `analysis/tilt_study/FINDINGS.md`.

## What this report measures, and what it does not

Every "tilt" number below is a **residual**: the score in the game after a streak minus the score
that players of the same rating, time control, colour and rating gap achieve in comparable games.
Among players who keep playing within the hour, it says how far the next game falls short of (or
exceeds) that benchmark. It does not measure emotional state, and it does not observe the players who
stopped. Fatigue, distraction, a bad connection, slowly changing strength and selection into
continuing are all consistent with a non-zero residual; the controls in §2c–§2e narrow the list but
do not identify a mechanism. "Tilt" is used below as the everyday name of the phenomenon a losing
streak is supposed to cause, not as a claim to have isolated it.

## TL;DR

1. **In raw game history the streak effect looks enormous**: the game after 6+ straight losses scores
   {pick(lad, "any_opponent", x=-6):.1f}%, after 6+ straight wins {pick(lad, "any_opponent", x=6):.1f}% (a
   {pick(lad, "any_opponent", x=6) - pick(lad, "any_opponent", x=-6):.0f}-point swing). Almost all of it is opponent
   selection (long streaks happen against weaker opponents: arenas, fresh accounts, the thin top of the pool; the
   pairing system itself moves the rating only ≈30 points over six wins), streaks that span more than one
   sitting, rematch series against the same opponent, and account artefacts (rating drift, second accounts).
   Holding those fixed leaves {pick(lad, "controlled", x=-6):.1f}% vs {pick(lad, "controlled", x=6):.1f}%, against a
   rating-based expectation of {sv(-6, "expected"):.1f}% / {sv(6, "expected"):.1f}%: a residual of
   **{sv(-6):+.1f} / {sv(6):+.1f} points** (§1). Each filter changes the population as well as the estimate,
   so the ladder is a bound on how much the raw pattern overstates the evidence, not a decomposition.
2. **After the controls a small residual remains, and it grows with the streak.** After 1, 2, 3, 4, 5, 6+
   losses: {sv(-1):+.1f}, {sv(-2):+.1f}, {sv(-3):+.1f}, {sv(-4):+.1f}, {sv(-5):+.1f}, {sv(-6):+.1f} points of
   score; after wins {sv(1):+.1f}, {sv(2):+.1f}, {sv(3):+.1f}, {sv(4):+.1f}, {sv(5):+.1f}, {sv(6):+.1f}. A
   joint within-player model (player × time-control intercepts, rating gap, own rating, colour, exact clock)
   gives the same picture: for the same player, the game after 6+ losses runs {wv(-6):+.1f} pp
   [{wv(-6, col="lo"):+.1f}, {wv(-6, col="hi"):+.1f}] relative to the game after one loss, and the
   hot-minus-cold swing is {sw(3):+.1f} pp at three and {sw(6):+.1f} pp at 6+ (§2d). Session length,
   hygiene filters and player-by-quarter intercepts move the tails by a few tenths of a point (§2e). The
   raw probability of losing the next game stays under 50% at every streak length
   ({pick(ploss, "p_loss_pct", k=6):.1f}% after 6+ losses) (§2).
3. **The post-loss residual is largest in rapid and at 800.** After 3+ losses: bullet
   {s3(s3tc, "tc", "bullet", "cold_resid"):+.1f}, blitz {s3(s3tc, "tc", "blitz", "cold_resid"):+.1f}, rapid
   {s3(s3tc, "tc", "rapid", "cold_resid"):+.1f}; 800-rated players {s3(s3elo, "elo_bucket", 800, "cold_resid"):+.1f},
   everyone from 1200 up between {min(s3(s3elo, "elo_bucket", e, "cold_resid") for e in (1200, 1600, 2000, 2400)):+.1f}
   and {max(s3(s3elo, "elo_bucket", e, "cold_resid") for e in (1200, 1600, 2000, 2400)):+.1f}. The post-win
   residual is +0.7 to +1.5 everywhere (§3). Group intervals overlap at the edges and the groups differ in
   composition; these are descriptive comparisons, not claims that game length or inexperience cause
   stronger carry-over.
4. **Longer breaks are followed by a smaller hot-minus-cold gap; this is not a recovery time.** The gap after a
   2+ streak is {bt("<1 min", "gap_hot_minus_cold"):+.1f} to {bt("10-30 min", "gap_hot_minus_cold"):+.1f} points for
   breaks under 30 minutes and ≈0 from 30–60 minutes on. Who pauses is self-selected at every break length,
   and the convergence comes as much from the post-win group falling as from the post-loss group recovering,
   so the data do not say what a break does to a given player. Games after 2+ same-session losses are
   {loss_share_LL:.1f}% of scored games with a mean residual of {pick(stop, "resid_pp", tc="all"):+.1f} pp: an
   aggregate shortfall of {shortfall_LL:.2f} points per 100 games. That is a scale comparison, not the saving a
   "stop after two losses" rule would produce, which needs the outcomes of games that were never played (§4).
   At every streak length {cv(-1):.0f}–{cv(-6):.0f}% of players play on within the hour; the share *rises* with
   the streak because long same-session streaks happen deep in long sessions (§4a).
5. **No detectable average shortfall after a blown endgame among continuers; short losses and disconnects are
   followed by the worst games.** Next-game residual after a loss that entered the endgame at ≥ +2:
   {anat_val("loss_by_endgame", "blown: entered the endgame winning (>= +2)"):+.1f} (two thirds are flags; blown
   by resignation {anat_val("loss_blown_by_termination", "resigned"):+.1f} with a wide interval); after a loss in
   ≤ 20 plies: {anat_val("loss_by_length", "short (<=20 plies)"):+.1f}; after an abandoned game:
   {anat_val("loss_by_termination", "abandoned (disconnect)"):+.1f}. Games thrown away before the endgame are not
   separable from other short losses in this cut, and a disconnect or a ten-move loss may mark a distracted
   player or a bad connection rather than an emotional state (§5).
6. **After a loss, behaviour changes more than the score.** Players move 2–4% faster, end the session more
   often (bullet: {q("bullet", "quit_after_loss"):.1f}% vs {q("bullet", "quit_after_win"):.1f}%), and, among those
   who continue within the hour, start the next game within a minute more often (rapid:
   {q("rapid", "next_within_60s_after_loss"):.0f}% vs {q("rapid", "next_within_60s_after_win"):.0f}%; of *all* rapid
   losses and wins, {q("rapid", "next_within_60s_unconditional_loss"):.0f}% vs
   {q("rapid", "next_within_60s_unconditional_win"):.0f}%). The revenge rematch scores {rv("all", "rematch_resid_after_loss"):+.1f}
   against {rv("all", "fresh_resid_after_loss"):+.1f} for a fresh opponent; the post-win mirror shows a symmetric
   rematch bonus for the first rematch, so opponent selection explains part of the penalty, and the split between
   matchup and state is not identified. Blunder rates in games with an engine evaluation are essentially unchanged after one loss
   and ≈0.6 per 100 moves higher after three, with the opponents' rate rising about half as much (§6).
7. **The post-loss-minus-post-win difference varies between players, but weakly**: split-half
   r = {trait["split_half_r"]:.2f}, so an individual's own number from ~300 games is mostly noise (§7).

## Data and method

- **Population**: {pop["games_total"]:,} rated games against humans with both ratings known, played by
  {pop["users"]:,} Lichess users in the FlawChess benchmark database (≈200 users per rating × time-control
  cell, ≈300 games each, {pop["first_game_at"][:10]} to {pop["last_game_at"][:10]}). Games with a usable
  clock record for end-time reconstruction: {pop["share_with_clock_duration"]:.1f}% (§2f).
- **Unit**: consecutive games of one user in one time-control bucket (bullet / blitz / rapid / classical),
  ordered by start time. A user's games in other buckets are a separate stream.
- **Game end** (approximate): start + the clock time used by both sides, reconstructed from the first and
  last `%clk` of each side (`first clocks + inc·(plies − 2) − last clocks`; the first move of each side
  carries the base time without increment, which holds for {first_clock_ok:.1f}% of games), plus the loser's
  remaining clock for losses on time. The data carry no game-end timestamp, so the delay between the last
  recorded move and a resignation or disconnect is unmeasured; §2e shows the streak curve with 30 s added to
  every game. Games with an incomplete or non-standard clock record get no end time (no median fallback):
  the gaps on either side of such a game are unknown, which starts a new session and excludes them from
  break rates. A negative gap (next game starting before the reconstructed end of the previous one,
  {neg_gaps:,} games) is treated as unknown timing, not as a zero-length break. Breaks and sessions are
  measured from the end of the previous game; a gap of ≥ 60 minutes starts a new session. *Bug fixed
  {REVISED}*: the first version used the minimum clock of each side as its last clock, which with an
  increment overstated the time used in {max(tv(tc, "last_clock_above_minimum_pct") for tc in ["blitz", "rapid", "classical"]):.0f}%
  of classical games and put thousands of negative gaps into the under-a-minute break cells.
- **Streak**: run of same-result games ending at the previous game. Draws break streaks and are shown
  as their own cell where relevant.
- **Equal footing** (stories/CLAUDE.md rule): only games in which the two players are within 100 rating
  points are *scored* ({pop["games_scored_equal_footing"]:,} games,
  {100 * pop["games_scored_equal_footing"] / pop["games_total"]:.1f}%). Sequence features (streaks, breaks,
  sessions, rematches) use the full history. Behaviour rates (quit, rush, rematch, analysis requests) also
  apply it to the game whose result they condition on.
- **Expected score**: empirical mean score in the same (time control, 400-point rating bucket at game
  time, 25-point rating-gap bin, colour), fitted on the frame the story scores: equal-footing, hygiene-clean
  games that are not the first game of a session (so the residual averages zero on that frame, by time
  control and by rating). Fitting on all equal-footing games instead put the zero point on a population
  that includes the cold-start first games of a session, which shifted every in-session cell by a
  time-control-specific offset (bullet +0.4, rapid −0.3, classical −1.7 pp) and made the bullet-vs-rapid
  contrast in §3 largely a warm-up artefact. Lichess ratings are not quite Elo-calibrated (a 100–149-point
  favourite scores 63%, not the 67% the Elo formula gives; the logistic scale is ≈520 in blitz, not 400),
  so the Elo formula would fake a hot hand for favourites. **Residual = score − expected**, in percentage
  points (pp) of score. One point of score per 100 games can be one win turned into a loss, two wins turned
  into draws, or two draws turned into losses; the story's "one extra loss per N games" is that first
  reading, used as an illustration.
- **Story hygiene** (applied to every scored number in the story unless stated): drop each user's first
  100 imported games in the time control and games played more than 150 points from the user's long-run
  median rating in that time control (second accounts, resets, rating drift). The import is the most recent
  1,000 games in a 36-month window, so the first 100 are mostly the oldest games of an established account
  rather than provisional ones; what they carry is rating drift (mean |rating − median| 62 vs 36 later,
  residual +0.5 pp), plus the odd new account. The rating-deviation filter conditions on the outcome (a long
  streak moves the rating, and the long-run median uses future games); it drops only 2–4% of games, and §2e
  shows the curve without it. {pop["games_scored_story_hygiene"]:,} games remain. Streak statistics also
  require the streak to lie within one session, the next game to start within the hour, and a **fresh
  opponent** (see below): {pop["games_after_same_session_streak"]:,} games (bullet {pop["after_streak_bullet"]:,},
  blitz {pop["after_streak_blitz"]:,}, rapid {pop["after_streak_rapid"]:,}, classical {pop["after_streak_classical"]:,}).
- **Fresh opponent** (every streak-conditioned number in §1–§5 and §7): the next opponent did not
  appear in any game of the streak that just ended (the opponent's last appearance in the whole history
  precedes the streak). A rematch series is not an independent draw from the pool: the same opponent
  carries an opponent-specific mismatch the rating-gap calibration cannot see, and their state is
  correlated with yours (they just lost to you k times). Within a rematch the streak effect is about twice
  the fresh-opponent effect (−5.3 / +4.6 pp after 6+ in the exploratory probes, vs {sv(-6):+.1f} / {sv(6):+.1f}),
  which is why the rematch is treated as a decision of its own in §6 rather than folded into the streak
  curve. Rematches are 7–14% of the same-session streak frame, so the control moves the 6+ cells by about
  half a point. The rematch-position flag (first rematch vs later in a series) is computed on the full
  history before any filter; *bug fixed {REVISED}*: it was previously shifted on the already-filtered
  frame, which mislabelled 4% of rematches.
- **Intervals**: 95% bootstrap over users (a user's games are correlated), 1,000 resamples for the
  headline curve, 300–500 elsewhere. The headline curve's resamples also refit the expectation table, so
  uncertainty in the benchmark is included; other tables treat the benchmark as fixed. Differences between
  groups (break test gap, rematch minus fresh) resample users jointly. Model-based intervals in §2d are
  cluster-robust by player.
- **Streak-selection bias** (Miller–Sanjurjo) does not apply: statistics are pooled over games, not
  averaged per session.

## 1. The control ladder

Next-game score (%) by the streak that just ended. Columns left to right add one control each:
any opponent and any gap (raw history) → equal-footing next game → streak within one session and next
game within the hour → fresh opponent (no rematch of anyone from the streak) → account hygiene.
"Expected" is the calibrated expectation for the controlled games; the residual carries its 95%
interval. Each step changes the set of games, so the columns show how much of the raw pattern
survives each condition, not how much each mechanism contributes.

{table(lad, [("streak", "streak"), ("n_any", "games (raw)"), ("any_opponent", "raw history"), ("equal_footing", "+ equal footing"), ("same_session", "+ one session"), ("fresh_opponent", "+ fresh opponent"), ("controlled", "+ hygiene (controlled)"), ("n_controlled", "games (controlled)"), ("expected", "expected"), ("residual", "residual [95% CI]")])}

Why the raw curve is steep (all games, by streak; the 6+ cells are pooled from the 7+ axis in
`ladder_diagnostics.csv`): after 6+ wins the next opponent is on average 175 points weaker, after 6+
losses 61 points stronger. This is selection, not matchmaking: the user's rating sits only 8–10 points
above its long-run median at that point and six wins move it by ≈30 points, while the opponents *during*
the streak were on average even weaker than the next one (111 points for exactly six wins, 253 for 7+).
Streaks are produced by lopsided pairings and the next opponent comes from the same context. The mean is
a fat tail rather than a shift (median gap +28 after exactly six wins, +105 after 7+; 38% of post-7+ games
are against an opponent more than 200 points weaker): split 6+ win streaks by whether the streak's own
opponents averaged >100 points weaker and the half that did face a next opponent 365 points weaker, the
other half +16, the population baseline. Dropping rematch series changes little here (+163 after 6+
wins), so the drivers are arenas, fresh or under-rated accounts and the thin top of the pool. Only
27–30% of 6+ streaks lie within one session (41% span more than a day); 16–20% of the games after a 6+
streak fall in the user's first 100 games (baseline 15%); 3.5–4.2% are played more than 150 points off
the user's median rating (baseline 2%).

{table(load("ladder_diagnostics"), [("x", "streak (−7 = 7+ losses)"), ("n", "games"), ("mean_rating_gap_next_game", "mean rating gap, next game"), ("median_rating_gap_next_game", "median gap"), ("share_equal_footing", "share equal footing"), ("share_streak_in_one_session", "share streak in one session"), ("share_rematch_series", "share rematch series"), ("share_in_first_100_games", "share in first 100 games"), ("rating_minus_long_run_median", "rating − long-run median")])}

## 2. The controlled streak curve

Same games as the last column of §1. Raw next-game score, expectation and residual by exact streak
length, ±6 pooled (6 or more). Intervals resample users and refit the expectation table.

{table(sc.filter(pl.col("x") != 0).with_columns(pl.col("x").map_elements(xlab, return_dtype=pl.Utf8).alias("streak")).pipe(ci, "resid", "resid_lo", "resid_hi", "residual"), [("streak", "streak"), ("n", "games"), ("score", "next-game score"), ("score_lo", "score lo"), ("score_hi", "score hi"), ("expected", "expected"), ("residual", "residual [95% CI]")])}

Raw probability of losing the next game after k straight losses (same games):

{table(ploss, [("k", "k losses in a row"), ("n", "games"), ("p_loss_pct", "P(lose next) %"), ("p_win_pct", "P(win next) %"), ("score_pct", "score %"), ("expected_pct", "expected %")])}

### 2a. By time control (residual, pp)

{pivot_curve(curve_tc, "tc", "resid")}

Cell sizes (games):

{pivot_curve(curve_tc, "tc", "n")}

Classical has 10–60 games per tail cell after the same-session requirement (its regular players play
one or two games per sitting) and is reported here only; the story charts bullet, blitz and rapid.

### 2b. By rating (residual, pp)

{pivot_curve(curve_elo, "elo_bucket", "resid")}

{pivot_curve(curve_elo, "elo_bucket", "n")}

### 2c. Robustness checks on the residual

**Colour.** The expectation is fitted per colour. Refitting it without colour changes no cell by more
than 0.1 pp:

{table(colour, [("x", "streak"), ("resid", "residual (colour-aware)"), ("resid_nocolour", "residual (colour-blind)")])}

**Trailing form.** Form = mean residual over the 20 scored games ending four games before the current
one (never overlapping the 3-game streak window), split into terciles. The streak effect has the same
size inside every tercile, so it is not a 20-game form window in disguise:

{table(form, [("form_tercile", "form tercile"), ("mean_form_pp", "mean form (pp)"), ("LLL+", "after LLL+"), ("L", "after L"), ("W", "after W"), ("WWW+", "after WWW+")])}

**Player demeaning (kept for reference; superseded by §2d).** Subtracting each user × time-control mean
residual (over all their scored games) from the residual shrinks both tails by about a third and puts
zero inside the cold 3+ intervals. This check is itself biased towards zero: players who chronically
score below their rating produce more losing streaks, so their mean residual carries part of the streak
effect and demeaning removes it along with the rating-lag component it is meant to remove. The joint
model below estimates the player intercepts and the streak contrasts together, which is the correct
version of this check:

{table(fe, [("x", "streak"), ("n", "games"), ("resid", "residual"), ("resid_player_fe", "residual, player-demeaned"), ("lo", "lo"), ("hi", "hi"), ("mean_player_fe", "mean player effect")])}

### 2d. Within-player model

Linear probability model of the next-game score on the controlled frame ({design["n"]:,} games,
{design["users"]:,} players, {design["streams"]:,} player × time-control streams), fitted by absorbing
group intercepts (Frisch–Waugh–Lovell), with standard errors clustered by player. Regressors: one dummy
per streak length (−6 … +6, reference = exactly one loss, draws as their own cell), the rating gap and
its square, own rating, colour, and the exact clock setting (levels with fewer than 500 games pooled).
Variant two adds session depth (game number in the session) and elapsed session time as categories;
these are partly consequences of earlier results, so the first variant is the primary estimate. Variant
three replaces the player × time-control intercepts with player × time-control × quarter intercepts
({design["stream_quarters"]:,} groups), which absorbs strength that drifts over months. Contrasts in pp
of score relative to the game after exactly one loss, so the pooled residual of {sv(-1):+.1f} at one loss
is the implicit baseline:

{within_table()}

Hot-minus-cold swing (the difference between the +k and −k contrasts, with its covariance):

{swing_table()}

The joint model reproduces the pooled curve rather than shrinking it: within the same player, the game
after 6+ losses runs {wv(-6):+.1f} pp relative to the game after one loss (pooled residual difference
{sv(-6) - sv(-1):+.1f}), the game after 6+ wins {wv(6):+.1f} pp, and the swing at three is
{sw(3):+.1f} pp [{sw(3, "lo"):+.1f}, {sw(3, "hi"):+.1f}]. Player-by-quarter intercepts change the
contrasts by at most {max(abs(wv(k, "player x quarter intercepts") - wv(k)) for k in range(-6, 7) if k != -1):.1f} pp,
so slowly drifting strength does not produce the curve. The model asks whether the same player scores
differently after a streak at a comparable moment; it still does not identify why.

### 2e. Sensitivity to the session and hygiene rules

The primary residual (users resampled, benchmark fixed) under alternative rules. "Zero increment only"
restricts to clock settings without increment, whose clocks are monotone (a check on the timing
reconstruction; the composition shifts towards bullet and blitz), with the expectation refitted on that
subset. "Game end +30 s" adds 30 seconds to every reconstructed game end (a resignation or disconnect
delay), which shortens every break.

{sensitivity_table()}

Across the session boundary (30, 60, 120 minutes) and the two history filters, the 6+ loss cell stays
between {sens_range_6[0]:+.1f} and {sens_range_6[1]:+.1f} and the 6+ win cell between
{sens_range_p6[0]:+.1f} and {sens_range_p6[1]:+.1f}. Dropping both hygiene filters makes both tails a
little larger, in line with the rating-drift games they remove. The zero-increment subset shows a
smaller loss tail ({sens_v("zero increment only", -6):+.1f}) with an interval that includes zero, which
matches the bullet/blitz composition of that subset (§2a) rather than pointing at a timing artefact.

### 2f. Timing validity

Per time control: share of games with a usable clock record (complete, first clock equal to the base
time), share whose last clock sits above the minimum (the cells the fixed bug had mis-timed), negative
gaps under the corrected reconstruction, share of games with a valid gap to the previous game, and
right-censored games (last game of a history):

{table(timing, [("tc", "time control"), ("games", "games"), ("usable_clock_pct", "usable clock %"), ("first_clock_mismatch_pct", "first clock ≠ base %"), ("last_clock_above_minimum_pct", "last clock > minimum %"), ("negative_gaps", "negative gaps"), ("valid_gap_pct", "valid gap to previous game %"), ("right_censored", "right-censored")])}

## 3. By rating and time control

Residual after 3+ straight losses (cold) and 3+ straight wins (hot), same-session streaks, hygiene.
The groups differ in composition (rating mix within a time control, clock settings within a rating
band), so the comparison is descriptive.

{table(s3tc, [("tc", "time control"), ("cold_n", "games after 3+ L"), ("cold_score", "score after L"), ("cold_expected", "expected after L"), ("after 3+ losses", "residual after 3+ L [95% CI]"), ("hot_n", "games after 3+ W"), ("hot_score", "score after W"), ("hot_expected", "expected after W"), ("after 3+ wins", "residual after 3+ W [95% CI]")])}

{table(s3elo, [("elo_bucket", "rating"), ("cold_n", "games after 3+ L"), ("cold_score", "score after L"), ("cold_expected", "expected after L"), ("after 3+ losses", "residual after 3+ L [95% CI]"), ("hot_n", "games after 3+ W"), ("hot_score", "score after W"), ("hot_expected", "expected after W"), ("after 3+ wins", "residual after 3+ W [95% CI]")])}

Rating × time control (cells under 1,000 games are noise-level; classical 2400 has no same-session
3+ streaks after the equal-footing filter):

{table(s3cell, [("cellk", "cell"), ("cold_n", "games after 3+ L"), ("after 3+ losses", "residual after 3+ L [95% CI]"), ("hot_n", "games after 3+ W"), ("after 3+ wins", "residual after 3+ W [95% CI]")])}

## 4. Breaks, continuation, the aggregate shortfall, warm-up and fatigue

Streak of 2+ within one session; next game bucketed by the break between the end of the last streak
game and its start. Residual after 2+ losses (cold) and 2+ wins (hot), and the hot-minus-cold gap with a
joint user bootstrap. Levels are self-selected (who pauses after two losses is not random), and so is
the gap: people who pause after wins and people who pause after losses need not be alike at the same
break length. The table describes the next game observed after different gaps; it does not follow a
state over elapsed time, so it cannot measure how long a streak's effect lasts or what a break does.

{table(brk, [("tc", "time control"), ("break", "break"), ("cold_n", "games (cold)"), ("after 2+ losses", "after 2+ losses [CI]"), ("hot_n", "games (hot)"), ("after 2+ wins", "after 2+ wins [CI]"), ("gap (hot minus cold)", "gap [CI]")])}

Pooled, the gap is {bt("<1 min", "gap_hot_minus_cold"):+.1f} within a minute, {bt("3-10 min", "gap_hot_minus_cold"):+.1f}
at 3–10 minutes, {bt("10-30 min", "gap_hot_minus_cold"):+.1f} at 10–30 minutes and {bt("30-60 min", "gap_hot_minus_cold"):+.1f}
[{bt("30-60 min", "gap_lo"):+.1f}, {bt("30-60 min", "gap_hi"):+.1f}] at 30–60 minutes. At 30–60 minutes both
groups sit below the benchmark ({bt("30-60 min", "cold_resid"):+.1f} and {bt("30-60 min", "hot_resid"):+.1f}): the
convergence is mostly the post-win group coming down, and the 30–60 minute interval admits gaps from
{bt("30-60 min", "gap_lo"):+.1f} to {bt("30-60 min", "gap_hi"):+.1f}.

Who takes which break (share of next games, %; `break_shares.csv`): after 2+ losses,
{pick(shares, "share", tc="bullet", streak_dir=-1):.0f}% of bullet and {pick(shares, "share", tc="rapid", streak_dir=-1):.0f}%
of rapid next games start within a minute; after 2+ wins {pick(shares, "share", tc="bullet", streak_dir=1):.0f}% and
{pick(shares, "share", tc="rapid", streak_dir=1):.0f}%. Rapid players re-queue faster after losses than after wins;
bullet players the other way round.

### 4a. Who keeps playing

Share of streak games followed by another game within the hour, by the streak the game completes (the
row "3 losses" is the third straight loss itself). The game must pass equal footing and hygiene and its
run must lie in one session; no condition is placed on the next game. The last game of a history and
games with unknown timing are censored, not counted as stops. Continuers and stoppers are compared on
rating and on how deep into the session the game sits:

{con_pooled}

By time control (next game within the hour, %):

{con_by_tc}

Continuation *rises* with streak length, from {cv(-1):.0f}% after one loss to {cv(-6):.0f}% after 6+, and
symmetrically after wins ({cv(1):.0f}% → {cv(6):.0f}%). This is mostly composition: a k-game same-session
streak sits at least k games into a session, and long sessions belong to players who keep playing
(stoppers sit {cv(-6, "continuer_session_idx") - cv(-6, "stopper_session_idx"):.0f} games earlier in the session
after 6+ losses and are ≈{cv(-6, "continuer_rating") - cv(-6, "stopper_rating"):.0f} rating points lower).
The table does not show that players ignore the "stop after three" advice, only that the streak cells
above describe the {cv(-3):.0f}–{cv(-6):.0f}% who continued, whose next game is observed, and not the
rest, whose counterfactual game is not.

### 4b. The aggregate post-loss shortfall

Share of scored games that follow 2+ same-session losses (fresh opponent, next game within the hour),
their mean residual, and the product, in points of score per 100 games:

{table(stop.with_columns(pl.col("aggregate_shortfall_per_100_games").map_elements(lambda v: f"{v:.2f}", return_dtype=pl.Utf8).alias("shortfall")), [("tc", "time control"), ("games_after_LL_in_session", "games after LL"), ("share_of_games", "share of games %"), ("resid_pp", "residual"), ("lo", "lo"), ("hi", "hi"), ("shortfall", "aggregate shortfall / 100 games")])}

This is how much of a player's total score, per 100 games, is accounted for by the post-2+-loss cells
running below the benchmark: {shortfall_LL:.2f} points pooled. It is a scale comparison. It is not what a
"stop after two losses" rule would recover, because that depends on the replacement games (played later,
in another state) and on all the later games of the session the rule would remove, none of which are
observed; and it excludes rematches, which the rule would not.

### 4c. Warm-up and fatigue

Residual for the first game of a session and by minutes since the session started (games after the
first):

{table(fatigue, [("tc", "time control"), ("first_game_n", "first games"), ("first_game_resid", "first game of session"), ("first_lo", "lo"), ("first_hi", "hi"), ("0-30 min", "0–30 min"), ("30-60 min", "30–60 min"), ("60-120 min", "60–120 min"), ("2-4 h", "2–4 h"), (">4 h", "> 4 h")])}

The first game of a bullet session runs {pick(fatigue, "first_game_resid", tc="bullet"):+.1f} and bullet shows no
drift over 4+ hours; rapid and classical drift down by 0.5–1 pp after one to four hours. (Residuals here
are relative to in-session games, which is why the first-game cells are negative and the in-session
cells sit near zero.)

## 5. The game after a loss, by what the loss looked like

Next-game residual after a loss (previous game lost, next game within the hour against a fresh opponent,
equal footing, hygiene), by how the loss ended, how long it lasted, and the Stockfish evaluation when it
entered the endgame (Lichess phase rule; ≥ +2.0 for the player = "blown", an evaluation lead, not
necessarily two pawns of material, and not necessarily still winning when the game ended; no endgame = the
game ended in the opening or middlegame). "all" pools the four time controls. All cells describe
continuers; a disconnect or a ten-move loss may indicate a distracted player or a technical problem as
readily as an emotional state.

By termination:

{anat("loss_by_termination")}

By length:

{anat("loss_by_length")}

By endgame state:

{anat("loss_by_endgame")}

Blown wins by how the blown game ended. Two thirds are flags in a won endgame; the blown win by
resignation, the folklore case, is 10k games with an interval that excludes anything large but not a
small effect. A game thrown away before the endgame (a hung piece in the middlegame) has no endgame entry
and lands in the "never reached an endgame" cell, so this cut cannot separate it from other short losses:

{anat("loss_blown_by_termination")}

Endgame state inside long losses only (> 60 plies), so the endgame cut is not length in disguise:

{anat("loss_by_endgame_long")}

Single losses only (streak length exactly 1), to show the cut is not streak length in disguise:

{anat("loss_by_length_single")}

{anat("loss_by_endgame_single")}

Mirror: the game after a **win**, by endgame state and length:

{anat("win_by_endgame")}

{anat("win_by_length")}

Shape of the next loss after a streak (conditional on losing the next game): after a losing streak the
loss is shorter, more often abandoned and more often resigned:

{table(shape, [("tc", "time control"), ("grp", "after"), ("n", "losses"), ("short_loss_pct", "≤ 20 plies %"), ("abandoned_pct", "abandoned %"), ("resigned_pct", "resigned %"), ("flagged_pct", "flagged %"), ("mean_plies", "mean plies")])}

## 6. Behaviour: quitting, rushing, revenge, speed, blunders

**Quit and rush** (equal-footing games with hygiene; a session ends when the next game starts ≥ 60 min
after this one ends). The quit rate excludes the last observed game of each history and games with
unknown timing (censored). The "next game < 60 s" rate is conditional on continuing within the hour; the
unconditional columns divide by all losses / wins, quits included:

{table(quit_, [("tc", "time control"), ("quit_after_loss", "P(session ends) after a loss %"), ("quit_after_win", "P(session ends) after a win %"), ("next_within_60s_after_loss", "next < 60 s after a loss, of continuers %"), ("next_within_60s_after_win", "next < 60 s after a win, of continuers %"), ("next_within_60s_unconditional_loss", "next < 60 s after a loss, of all losses %"), ("next_within_60s_unconditional_win", "next < 60 s after a win, of all wins %"), ("median_gap_after_loss_s", "median gap after a loss (s)"), ("median_gap_after_win_s", "after a win (s)"), ("sessions_ending_on_loss_pct", "sessions ending on a loss %"), ("base_loss_rate_pct", "base loss rate %")])}

**Revenge rematch**: next game, within the hour, against the same opponent. The streak curve in §1–§5
requires a fresh opponent, so this is where the rematch comes back in. Residual for the rematch vs a
fresh opponent, after a loss and after a win (equal footing, hygiene). The rematch-minus-fresh
difference is {rs("after loss", "first rematch"):+.1f} pp for the first rematch of a pairing and
{rs("after loss", "later in a series"):+.1f} later in a series. Opponent selection (the player who just beat
you is, on that evidence, a little better than their rating) predicts a symmetric bonus after wins, and the
first post-win rematch shows one ({rs("after win", "first rematch"):+.1f} over a fresh opponent). That is
consistent with part of the post-loss penalty being matchup. It does not give a decomposition: both
players choose the rematch, their reasons can differ after a win and after a loss, and the post-win
comparison assumes a symmetry that cannot be checked. The table describes the cost of the observed
choice; it does not attribute a share of it to mood.

{table(rev, [("tc", "time control"), ("rematch_rate_after_loss", "rematch rate after L %"), ("rematch_n_after_loss", "rematches"), ("rematch_score_after_loss", "score"), ("rematch_expected_after_loss", "expected"), ("rematch_resid_after_loss", "rematch residual"), ("rematch_lo_after_loss", "lo"), ("rematch_hi_after_loss", "hi"), ("fresh_resid_after_loss", "fresh-opponent residual"), ("rematch_rate_after_win", "rematch rate after W %"), ("rematch_resid_after_win", "rematch residual after W"), ("fresh_resid_after_win", "fresh residual after W")])}

{table(rev_elo, [("elo_bucket", "rating"), ("rematch_rate_after_loss", "rematch rate after L %"), ("rematch_n_after_loss", "rematches"), ("rematch_resid_after_loss", "revenge residual"), ("lo_after_loss", "lo"), ("hi_after_loss", "hi"), ("rematch_rate_after_win", "rematch rate after W %"), ("rematch_resid_after_win", "rematch residual after W")])}

First rematch of a pairing vs later games in a series against the same opponent (position computed on
the full history), with the rematch-minus-fresh difference and its joint user bootstrap:

{table(ci(rev_series, "rematch_minus_fresh", "diff_lo", "diff_hi", "rematch − fresh [95% CI]"), [("after", "after"), ("position", "position"), ("n", "rematches"), ("rematch_resid", "rematch residual"), ("lo", "lo"), ("hi", "hi"), ("fresh_resid", "fresh residual"), ("rematch − fresh [95% CI]", "rematch − fresh [95% CI]")])}

**Speed**: mean seconds per move over moves 3–20 (own moves with a clock delta, ≥ 10 such moves) and the
share of those moves played in ≤ 1 s, by the streak just ended; plus the paired per-user relative change
in seconds per move after a loss vs after a win (users with ≥ 20 games in each cell):

{table(speed, [("tc", "time control"), ("think_s_LLL+", "s/move after LLL+"), ("think_s_L", "after L"), ("think_s_W", "after W"), ("think_s_WWW+", "after WWW+"), ("fast_moves_pct_L", "≤ 1 s moves after L %"), ("fast_moves_pct_W", "≤ 1 s moves after W %"), ("paired_users", "paired users"), ("paired_rel_change_pct", "paired change after L vs W %"), ("share_users_faster_after_loss", "share of users faster after L %")])}

**Move quality**: blunders per 100 own moves in every game with a full engine evaluation (a Lichess
computer analysis requested by either player, or a Stockfish evaluation run by the FlawChess benchmark
pipeline; rapid and classical, ≥ 20 plies), own and opponent's, by streak. After a single
loss the rate is essentially unchanged ({pick(blunders, "blunders_per_100_L", tc="all"):.1f} vs {pick(blunders, "blunders_per_100_W", tc="all"):.1f}
after a win, where the score effect is also ≈ 0). After 3+ losses it is higher by
≈{pick(blunders, "blunders_per_100_LLL+", tc="rapid") - pick(blunders, "blunders_per_100_W", tc="rapid"):.1f} per
100 moves (rapid {pick(blunders, "blunders_per_100_LLL+", tc="rapid"):.1f} [{pick(blunders, "lo_LLL+", tc="rapid"):.1f}, {pick(blunders, "hi_LLL+", tc="rapid"):.1f}]
vs {pick(blunders, "blunders_per_100_W", tc="rapid"):.1f} [{pick(blunders, "lo_W", tc="rapid"):.1f}, {pick(blunders, "hi_W", tc="rapid"):.1f}]).
The opponent's rate rises in the same games, by about half as much, which fits a game-mix effect
(sharper, faster games) as well as a change in the player; the data cannot separate the two. Whether a
game has an evaluation at all is not independent of the streak (§6a: the analysis rate is a few points
lower after long losing streaks, and Lichess-analysed games carry fewer blunders per move than the
benchmark-evaluated ones), but the analysed share moves by about 6 points between LLL+ and WWW+ against a
level gap of about 1.4 per 100 moves, so the mix can account for at most ≈0.1 of the difference below:

{table(blunders, [("tc", "time control"), ("blunders_per_100_LLL+", "own, after LLL+"), ("opp_blunders_LLL+", "opponent, after LLL+"), ("blunders_per_100_L", "own, after L"), ("opp_blunders_L", "opponent, after L"), ("blunders_per_100_W", "own, after W"), ("opp_blunders_W", "opponent, after W"), ("blunders_per_100_WWW+", "own, after WWW+"), ("opp_blunders_WWW+", "opponent, after WWW+"), ("n_L", "games after L")])}

### 6a. Analysis requests: does a player on a losing streak still look at the game?

Share of games with a Lichess computer analysis (`lichess_evals_at` set; either player can request
it), by the streak the game *completes*: the row "3 losses" is the third straight loss itself, not the
game after it. Equal-footing games with hygiene, the run within one session, ±6 pooled, intervals from
the user bootstrap. Two controls: "vs player's own rate" subtracts each user × time-control mean analysis
rate from the game's flag, which removes who reaches long streaks; "session games 6–15 only" additionally
compares streak lengths at the same session depth, because a k-game streak sits at least k games into
its session, the per-game analysis rate falls with session length whatever the result, and the game a
player stops on is analysed more often while a streak game is by construction less often the stopping
game. The last two columns are the rapid raw rate and the rapid depth-controlled rate:

{table(analysed, [("streak", "streak completed"), ("n", "games"), ("analysed % [95% CI]", "analysed % [95% CI]"), ("vs player's own rate, pp [95% CI]", "vs player's own rate, pp [95% CI]"), ("same, session games 6–15 only [95% CI]", "same, session games 6–15 only [95% CI]"), ("bullet_analysed_pct", "bullet %"), ("blitz_analysed_pct", "blitz %"), ("rapid_analysed_pct", "rapid %"), ("rapid_deep_pp", "rapid, controlled pp")])}

The raw column falls from {av(-1, "analysed_pct"):.1f}% after a single loss to {av(-6, "analysed_pct"):.1f}% after
6+ straight losses (rapid: {av(-1, "rapid_analysed_pct"):.1f}% → {av(-6, "rapid_analysed_pct"):.1f}%), but most of
that is not a decision to look away. Three mechanical things drive it: who reaches long same-session
streaks (bullet players at 7% whatever the streak, high-volume accounts, lower-rated players who analyse
less), session depth, and the stop-and-analyse selection above. Game shape is not one of them: length
(62–68 plies) and abandonment rate are flat across the loss cells, and dropping rematches changes
nothing. Demeaning by user removes most of the drop; holding session depth fixed removes more. What
survives is small and consistent in sign: at equal depth, within a player, a single loss is analysed
{av(-1, "deep_pp"):+.1f} pp more often than that player's average game, 6+ losses {av(-6, "deep_pp"):+.1f} pp (rapid:
{av(-1, "rapid_deep_pp"):+.1f} → {av(-6, "rapid_deep_pp"):+.1f}), while wins sit {av(1, "deep_pp"):+.1f} to
{av(5, "deep_pp"):+.1f} pp below the player's mean (rapid: {av(1, "rapid_deep_pp"):+.1f} to {av(6, "rapid_deep_pp"):+.1f}).
The loss-specific part of the decline is under 1 pp pooled and ≈1.5 pp in rapid, on bases of 20% and
30%; the trend is monotonic from 1 to 4 losses, but the 6+ cell alone has an interval of ± 1 pp
pooled and ± 3 pp in rapid, so this is suggestive rather than established. The rising raw rate after
long winning streaks is the mirror artefact (win streaks in rapid come from higher-rated players who
analyse more; within player the win rate is flat). Draws are the most analysed result in raw terms
({av(0, "analysed_pct"):.1f}%) but {av(0, "deep_pp"):+.1f} pp within player: draw-heavy players are the rapid and
classical crowd. Analysis requests are mildly streak-dependent, mostly through composition and session depth rather
than mood; §6 bounds the mix effect this has on the blunder comparison.

## 7. Does the post-loss dip vary between players?

Per user × time control: Δ = mean residual after a loss − mean residual after a win, computed
separately on odd- and even-numbered sessions (≥ 25 scored games per side per half). The SD and the
correlation are taken over the same streams (both halves qualifying).

| statistic | value |
|---|---|
| user × time-control streams | {trait["streams_user_x_tc"]:,} (users: {trait["users"]:,}) |
| mean Δ (pp) | {trait["mean_delta_pp"]:+.2f} |
| observed SD of Δ across users (pp) | {trait["sd_delta_pp"]:.1f} |
| split-half correlation r | {trait["split_half_r"]:.3f} |
| Spearman–Brown reliability of a full ~300-game Δ | {trait["spearman_brown_reliability"]:.2f} |
| implied true SD of the trait (pp) | {trait["implied_true_sd_pp"]:.1f} |

The difference varies between players, but weakly: a player one SD above the mean scores
≈ {trait["implied_true_sd_pp"]:.1f} pp lower after losses than after wins, relative to the average
player. The reliability of a single player's ~300-game Δ is {trait["spearman_brown_reliability"]:.2f}, so
≈ {100 - 100 * trait["spearman_brown_reliability"]:.0f}% of the variance of individual estimates is noise
(this describes the population of estimates, not the error of any one of them); a per-user "tilt score"
would mislead most users, and the story reports population averages.

## 8. Relation to published work

Summarised from the literature review in `analysis/tilt_study/FINDINGS.md` §8.

- **Gee, Seese, Curley & Ward (2025)**, arXiv:2503.21713, hierarchical Bayesian logit on Lichess bullet
  games of 141 players from 1700 up, controlling for rating difference, colour and player: the global
  winner/loser effect is centred on zero, individual effects within ±3 pp. Our single-game residual
  ({sv(-1):+.1f} / {sv(1):+.1f}) is below their detection floor; our 3+ and 6+ cells sit inside their credible range.
- **Rosenthal (2025)**, Harvard Data Science Review 7(2), 293k chess.com games of seven top players:
  autocorrelation of excess score ≈ 0 at every lag, raw-score autocorrelation ≈ 0.1 attributed to rating
  updates. Our 2000–2400 cells ({s3(s3elo, "elo_bucket", 2000, "cold_resid"):+.1f} and
  {s3(s3elo, "elo_bucket", 2400, "cold_resid"):+.1f} after 3+ losses, CIs including zero) agree, and his
  raw-vs-excess gap is our §1 ladder.
- **Chowdhary, Iacopini & Battiston (2023)**, Sci. Rep. 13:2113, 123M Lichess blitz games: real streaks
  are longer than shuffled ones, cold streaks longer than hot, beginners streakier than experts. Same
  direction as ours; a shuffle test cannot separate state from rating drift, which is why their effect
  looks larger.
- **Popular analyses** do not control for opponent rating, session or account state; §1 reproduces a
  swing of that size on our raw data and shows where it goes. Two examples:
  [chessanalysis.co (2026)](https://chessanalysis.co/research/chess-improvement-rating-trajectories),
  ~840k Lichess games from ~80k players: 39.1% next-game win rate after five losses vs 58.1% after five
  wins at 1200–1400; [Devine, "Tilt and Hype in Online Chess"](http://seandevine.org/blog/chessBlog.html),
  ~1M Lichess games from 2014, mixed-effects logit with a player intercept but no opponent-rating term:
  the previous result shifts the log-odds of winning by 0.25, with results up to seven games back still
  predictive. Neither excludes rematches against the same opponent.
- Break length, loss anatomy, revenge rematches and quit-on-loss have no quantitative chess precedent
  that we found. The closest analogue is Jack J (2020) on League of Legends, where re-queuing immediately
  after two losses is worst for mid-rank players and best for top-rank players.

## 9. Limits

- **The residual is not a measurement of emotional tilt.** Persistent distraction, fatigue, a bad
  connection, changing strength, the exact clock mix and selection into continued play are all
  compatible with it. §2c–§2e rule out colour, 20-game form, time-invariant and quarter-level player
  effects, session depth and the session and hygiene rules as the source; they do not identify what is
  left. A small average residual among continuers is also compatible with severe but rare tilt, with
  large effects in some players, and with players who stop when they feel tilted; the study measures
  neither emotional state nor the unplayed games of those who stopped.
- Observational throughout. Who continues, pauses, rematches or requests analysis is self-selected;
  the report leans on differences between groups facing similar selection (hot vs cold at the same break
  length; rematch vs fresh opponent after the same result) rather than on single cells, but similar is
  not identical, and none of these differences is a causal effect of pausing or of rematching.
- **Rating lag.** The expectation is calibrated on the pooled population; user-level rating lag remains.
  For a constant-strength player it works *against* the observed pattern: after k losses the rating sits
  below strength (six Glicko-2 updates of roughly 6–10 points each), the player is under-rated by ≈40–60
  points and should score ≈2–3 pp *above* the benchmark against an equal-rated opponent. An improving
  player is under-rated after wins, which inflates the post-win residual. The joint model's own-rating
  term, the player × quarter intercepts (§2d) and the form terciles (§2c) bound the drifting-strength
  version of this; a no-tilt simulation of the pipeline was not run.
- The game end is reconstructed from clocks. There is no end timestamp; resignation and disconnect
  delays after the last recorded move are unmeasured (§2e adds 30 s), and 3% of games have no usable
  clock record and break the session at both ends.
- The hot-minus-cold gap in §4 is flat from 30–60 minutes on, but that cell's interval admits gaps from
  {bt("30-60 min", "gap_lo"):+.1f} to {bt("30-60 min", "gap_hi"):+.1f}, and the comparison observes different
  people at different gaps rather than one state over time; it does not give a recovery time.
- The aggregate shortfall in §4b is not a policy estimate (see there).
- Time of day is UTC only (no user time zone) and not analysed.
- The benchmark cohort is regular players (~300 games per time control over three years), not a uniform
  sample of Lichess. Classical is thin once streaks must lie within one session.
- The equal-footing filter removes 22% of games, disproportionately at 2400 and in classical.
- Berserk in arena games, sub-time-control mix (1+0 vs 2+1; the joint model controls for the exact
  clock, the pooled tables do not) and casual games after a loss were not modelled. 944 of the 4,487
  users have games in a second time control; play in the other control inside a break gap is under 0.5%
  of break-test cells, so switching controls does not contaminate §4, but casual games in a gap are invisible.

## Reproduction

```bash
bin/benchmark_db.sh start
uv run --project analysis python analysis/tilt_study/extract_clocks.py           # clock_ends.parquet
uv run --project analysis python analysis/tilt_study/probes/extract_acc.py       # acc.parquet (colour)
uv run --project analysis python analysis/tilt_study/probes/extract_moves.py     # move_feats.parquet
uv run --project analysis python analysis/tilt_study/probes/extract_flaws.py     # flaws.parquet
uv run --project analysis python analysis/tilt_study/extract_endgame_entry.py    # endgame_entry.parquet
uv run --project analysis python analysis/tilt_study/gen_story.py                # analysis/out/tilt/story/*.csv
uv run --project analysis python analysis/tilt_study/robustness.py               # sensitivity, model, continuation
uv run --project analysis python analysis/tilt_study/gen_report.py               # this file
```

`games.parquet` is written by the first run of the marimo notebook `analysis/tilt_study/tilt_study.py`.
The feature cache (`features.parquet`) is rebuilt automatically when `story_data.py` or any source
extract changes.
"""

REPORT.write_text(md)
print(f"wrote {REPORT} ({len(md):,} chars)")
