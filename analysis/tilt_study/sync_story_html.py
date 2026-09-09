"""Rebuild the data tables and JS data arrays in stories/tilt/index.html from the story CSVs.

The prose in the page is written by hand; the "View the data" tables and the chart data block
are generated, so a re-run of gen_story.py followed by this script keeps them exact.

Run: uv run --project analysis python analysis/tilt_study/sync_story_html.py
"""

import re
from pathlib import Path

import polars as pl

REPO = Path(__file__).resolve().parents[2]
STORY = REPO / "analysis" / "out" / "tilt" / "story"
HTML = REPO / "stories" / "tilt" / "index.html"
NEAR_ZERO = 0.05  # values that round to 0.0 get no sign


def load(name: str) -> pl.DataFrame:
    return pl.read_csv(STORY / f"{name}.csv")


def s1(v: float) -> str:
    """Signed one-decimal number with the page's minus entity."""
    if abs(v) < NEAR_ZERO:
        return "0.0"
    return ("+" if v > 0 else "&minus;") + f"{abs(v):.1f}"


def pc(v: float) -> str:
    return f"{v:.1f}%"


def n(v: int) -> str:
    return f"{v:,}"


def ci(v: float, lo: float, hi: float) -> str:
    return f"{s1(v)} ({s1(lo)} to {s1(hi)})"


def xlab(x: int) -> str:
    k = abs(x)
    word = ("loss" if k == 1 else "losses") if x < 0 else ("win" if k == 1 else "wins")
    return f"{k}{'+' if k == 6 else ''} {word}"


def replace_tbody(html: str, section_id: str, rows: list[str], which: int = 0) -> str:
    """Replace the `which`-th <tbody> inside the section with id=section_id."""
    start = html.index(f'<section class="card" id="{section_id}">')
    end = html.index("</section>", start)
    sec = html[start:end]
    bodies = list(re.finditer(r"<tbody>.*?</tbody>", sec, flags=re.S))
    m = bodies[which]
    new_body = "<tbody>\n" + "\n".join("        " + r for r in rows) + "\n      </tbody>"
    sec = sec[: m.start()] + new_body + sec[m.end() :]
    return html[:start] + sec + html[end:]


html = HTML.read_text()

# ---- section 1: control ladder ---------------------------------------------------------
lad = load("ladder6").filter(pl.col("x") != 0).sort("x")
rows = [
    f"<tr><td>{xlab(r['x'])}</td><td>{n(r['n_any'])}</td><td>{pc(r['any_opponent'])}</td><td>{pc(r['equal_footing'])}</td>"
    f"<td>{pc(r['controlled'])}</td><td>{pc(r['expected'])}</td><td>{s1(r['resid'])}</td></tr>"
    for r in lad.iter_rows(named=True)
]
html = replace_tbody(html, "raw-stats", rows)

# ---- section 2: controlled curve + P(loss) ---------------------------------------------------
sc = load("streak_curve").filter(pl.col("x") != 0).sort("x")
pl_ = {r["k"]: r["p_loss_pct"] for r in load("p_loss_after_k").iter_rows(named=True)}
rows = []
for r in sc.iter_rows(named=True):
    lose = pc(pl_[abs(r["x"])]) if r["x"] < 0 else ""
    rows.append(
        f"<tr><td>{xlab(r['x'])}</td><td>{n(r['n'])}</td><td>{pc(r['score'])}</td><td>{pc(r['expected'])}</td>"
        f"<td>{s1(r['resid'])}</td><td>{s1(r['resid_lo'])} to {s1(r['resid_hi'])}</td><td>{lose}</td></tr>"
    )
html = replace_tbody(html, "how-big", rows)

# ---- section 3: 3+ streaks by time control and rating ----------------------------------------
rows = []
for df, key, label in [
    (load("streak3_by_tc"), "tc", None),
    (load("streak3_by_rating"), "elo_bucket", None),
]:
    for r in df.iter_rows(named=True):
        name = str(r[key]).capitalize() if key == "tc" else str(r[key])
        if name == "Classical":
            name = "Classical*"
        rows.append(
            f"<tr><td>{name}</td><td>{n(r['cold_n'])}</td><td>{pc(r['cold_score'])}</td><td>{pc(r['cold_expected'])}</td>"
            f"<td>{ci(r['cold_resid'], r['cold_lo'], r['cold_hi'])}</td><td>{n(r['hot_n'])}</td><td>{pc(r['hot_score'])}</td>"
            f"<td>{pc(r['hot_expected'])}</td><td>{ci(r['hot_resid'], r['hot_lo'], r['hot_hi'])}</td></tr>"
        )
html = replace_tbody(html, "who-tilts", rows)

# ---- section 4: break test ----------------------------------------------------------------------
brk = load("break_test").filter(pl.col("break") != ">7 d")
BREAK_LABELS = {
    "<1 min": "Under 1 minute",
    "1-3 min": "1&ndash;3 minutes",
    "3-10 min": "3&ndash;10 minutes",
    "10-30 min": "10&ndash;30 minutes",
    "30-60 min": "30&ndash;60 minutes",
    "1-6 h": "1&ndash;6 hours",
    "6-24 h": "6&ndash;24 hours",
    "1-7 d": "1&ndash;7 days",
}
by = {(r["tc"], r["break"]): r for r in brk.iter_rows(named=True)}
rows = []
for b, lab in BREAK_LABELS.items():
    a, bu, ra = by[("all", b)], by[("bullet", b)], by[("rapid", b)]
    rows.append(
        f"<tr><td>{lab}</td><td>{s1(a['cold_resid'])} (n {n(a['cold_n'])})</td><td>{s1(a['hot_resid'])} (n {n(a['hot_n'])})</td>"
        f"<td>{s1(a['gap_hot_minus_cold'])}</td><td>{s1(bu['cold_resid'])}</td><td>{s1(bu['hot_resid'])}</td>"
        f"<td>{s1(ra['cold_resid'])}</td><td>{s1(ra['hot_resid'])}</td></tr>"
    )
html = replace_tbody(html, "breaks", rows)

# ---- section 5: loss anatomy --------------------------------------------------------------------
ANAT = [
    ("loss_by_termination", "checkmated", "by checkmate"),
    ("loss_by_termination", "resigned", "by resignation"),
    ("loss_by_termination", "on time", "on time"),
    ("loss_by_termination", "abandoned (disconnect)", "by disconnection"),
    ("loss_by_length", "short (<=20 plies)", "under 11 moves"),
    ("loss_by_length", "mid (21-60 plies)", "11 to 30 moves"),
    ("loss_by_length", "long (>60 plies)", "over 30 moves"),
    ("loss_by_endgame", "never reached an endgame", "never reached an endgame"),
    ("loss_by_endgame", "entered the endgame losing (<= -2)", "entered the endgame two pawns down"),
    ("loss_by_endgame", "entered the endgame balanced", "entered the endgame level"),
    (
        "loss_by_endgame",
        "blown: entered the endgame winning (>= +2)",
        "entered the endgame two pawns up (blown)",
    ),
]
rows = []
for f, cat, lab in ANAT:
    r = load(f).filter(pl.col("previous loss") == cat).row(0, named=True)
    rows.append(
        f"<tr><td>{lab}</td><td>{n(r['all_n'])}</td><td>{ci(r['all_resid'], r['all_lo'], r['all_hi'])}</td>"
        f"<td>{s1(r['bullet_resid'])}</td><td>{s1(r['blitz_resid'])}</td><td>{s1(r['rapid_resid'])}</td></tr>"
    )
html = replace_tbody(html, "which-loss", rows)

# ---- section 6: revenge + quit ------------------------------------------------------------------
rev = {r["tc"]: r for r in load("revenge").iter_rows(named=True)}
qt = {r["tc"]: r for r in load("quit_rush").iter_rows(named=True)}
rows = []
for tc in ["bullet", "blitz", "rapid", "classical", "all"]:
    r = rev[tc]
    q = qt.get(tc)
    quit_cells = (
        f"<td>{pc(q['quit_after_loss'])}</td><td>{pc(q['quit_after_win'])}</td>"
        f"<td>{q['next_within_60s_after_loss']:.0f}% / {q['next_within_60s_after_win']:.0f}%</td>"
        if q
        else "<td></td><td></td><td></td>"
    )
    rows.append(
        f"<tr><td>{tc.capitalize()}</td><td>{pc(r['rematch_rate_after_loss'])}</td><td>{pc(r['rematch_score_after_loss'])}</td>"
        f"<td>{pc(r['rematch_expected_after_loss'])}</td><td>{ci(r['rematch_resid_after_loss'], r['rematch_lo_after_loss'], r['rematch_hi_after_loss'])}</td>"
        f"<td>{s1(r['fresh_resid_after_loss'])}</td><td>{s1(r['rematch_resid_after_win'])}</td>{quit_cells}</tr>"
    )
html = replace_tbody(html, "behaviour", rows)


# ---- JS data block ------------------------------------------------------------------------------
def js(vals: list, d: int = 3) -> str:
    return "[" + ",".join((f"{v:.{d}f}" if isinstance(v, float) else str(v)) for v in vals) + "]"


def sub_arr(html: str, start: str, end: str, key: str, vals: list) -> str:
    i = html.index(start)
    j = html.index(end, i)
    blk, cnt = re.subn(
        r"(\b" + key + r":\s*)\[[^\]]*\]", lambda m: m.group(1) + js(vals), html[i:j], count=1
    )
    assert cnt == 1, key
    return html[:i] + blk + html[j:]


def sub_triples(html: str, start: str, end: str, triples: list[tuple[float, float, float]]) -> str:
    i = html.index(start)
    j = html.index(end, i)
    it = iter(triples)
    blk, cnt = re.subn(
        r"v:(-?[\d.]+),lo:(-?[\d.]+),hi:(-?[\d.]+)",
        lambda m: (lambda t: f"v:{t[0]:.3f},lo:{t[1]:.3f},hi:{t[2]:.3f}")(next(it)),
        html[i:j],
    )
    assert cnt == len(triples), (cnt, len(triples))
    return html[:i] + blk + html[j:]


for k, c in [
    ("raw", "any_opponent"),
    ("equal", "equal_footing"),
    ("ctrl", "controlled"),
    ("ctrlLo", "score_lo"),
    ("ctrlHi", "score_hi"),
    ("expected", "expected"),
    ("nRaw", "n_any"),
    ("nCtrl", "n_controlled"),
]:
    html = sub_arr(html, "const LADDER", "const TILT", k, lad[c].to_list())
for k, c in [("v", "resid"), ("lo", "resid_lo"), ("hi", "resid_hi")]:
    html = sub_arr(html, "const TILT", "const BY_TC", k, sc[c].to_list())
tc3 = load("streak3_by_tc").filter(pl.col("tc") != "classical")
el3 = load("streak3_by_rating")
for k, c in [
    ("cold", "cold_resid"),
    ("coldLo", "cold_lo"),
    ("coldHi", "cold_hi"),
    ("coldN", "cold_n"),
    ("hot", "hot_resid"),
    ("hotLo", "hot_lo"),
    ("hotHi", "hot_hi"),
    ("hotN", "hot_n"),
]:
    html = sub_arr(html, "const BY_TC", "const BY_RATING", k, tc3[c].to_list())
    html = sub_arr(html, "const BY_RATING", "const BREAKS", k, el3[c].to_list())
ball = brk.filter(pl.col("tc") == "all")
for k, c in [
    ("cold", "cold_resid"),
    ("coldLo", "cold_lo"),
    ("coldHi", "cold_hi"),
    ("coldN", "cold_n"),
    ("hot", "hot_resid"),
    ("hotLo", "hot_lo"),
    ("hotHi", "hot_hi"),
    ("hotN", "hot_n"),
]:
    html = sub_arr(html, "const BREAKS", "const ANATOMY", k, ball[c].to_list())
triples = []
for f, cat, _ in ANAT:
    r = load(f).filter(pl.col("previous loss") == cat).row(0, named=True)
    triples.append((r["all_resid"], r["all_lo"], r["all_hi"]))
html = sub_triples(html, "const ANATOMY", "const REVENGE", triples)
r = rev["all"]
html = sub_triples(
    html,
    "const REVENGE",
    "const QUIT",
    [
        (r["rematch_resid_after_loss"], r["rematch_lo_after_loss"], r["rematch_hi_after_loss"]),
        (r["fresh_resid_after_loss"], r["fresh_lo_after_loss"], r["fresh_hi_after_loss"]),
        (r["rematch_resid_after_win"], r["rematch_lo_after_win"], r["rematch_hi_after_win"]),
        (r["fresh_resid_after_win"], r["fresh_lo_after_win"], r["fresh_hi_after_win"]),
    ],
)
q = load("quit_rush")
html = sub_arr(html, "const QUIT", "/* ---------- helpers", "loss", q["quit_after_loss"].to_list())
html = sub_arr(html, "const QUIT", "/* ---------- helpers", "win", q["quit_after_win"].to_list())

HTML.write_text(html)
print(f"synced {HTML}")
