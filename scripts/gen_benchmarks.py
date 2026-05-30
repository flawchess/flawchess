"""Deterministic generator for the FlawChess benchmark report (SEED-029, Phase A).

Replaces the LLM-runs-~36-inline-SQL-blocks-and-hand-computes-stats flow in
`.claude/skills/benchmarks/SKILL.md`. That report (`reports/benchmark/benchmarks-latest.md`)
is the **source of truth** for shipped gauge-zone constants
(`app/services/endgame_zones.py` -> `frontend/src/generated/endgameZones.ts`), so the
hand-computation is a real transcription/arithmetic fragility. This script computes every
distribution / Cohen's d / IQR / correlation into a structured artifact (JSON + markdown
tables); the SKILL.md LLM then applies the fixed collapse-verdict thresholds and writes the
prose narration.

PHASE A MANDATE — FAITHFUL PORT FIRST (SEED-029 locked decision #1):
    Reproduce the *existing* methodology verbatim (max|d|, IQR bands, current conv/recov
    floors, sparse-cell exclusion, equal-footing opponent filter, game-time ELO bucketing).
    The acceptance gate is a numeric diff: this script's output must match the current
    `benchmarks-latest.md` within rounding for every metric, marginal, and d-value. Any
    mismatch is resolved or footnoted as a fixed prior transcription error. Do NOT layer in
    methodology changes (#4 metric-vs-ELO correlation, #6 conditional-opportunity floors)
    here — those are Phase B, as separate attributable commits against this baseline.

CODE/LLM SEAM (locked decision #2):
    Code emits numbers. The LLM applies verdicts + narrates. The port diff validates the
    numbers, not the verdicts (LLM-authored from a fixed threshold table).

DB target (read-only). Mirrors the --db guard in scripts/backfill_eval.py, but this script
only ever reads. `benchmark` is the canonical source; `dev` is allowed for smoke-testing the
harness against the dev DB.
    benchmark: localhost:5433  (bin/benchmark_db.sh start)
    dev:       localhost:5432  (docker compose -f docker-compose.dev.yml -p flawchess-dev up -d)

DB URL is derived from settings.DATABASE_URL by swapping the port. Override with
GEN_BENCHMARK_DB_URL / GEN_DEV_DB_URL (must use a localhost host).

Usage:
    bin/benchmark_db.sh start
    uv run python scripts/gen_benchmarks.py --db benchmark
    uv run python scripts/gen_benchmarks.py --db benchmark --out reports/benchmark
    uv run python scripts/gen_benchmarks.py --db dev --dry-run   # connectivity smoke

Status: SCAFFOLD. Chapter computations are stubbed (see CHAPTER_STUBS / _generate_chapters).
Each stub references the SKILL.md section it must port. Fill them in one section at a time,
diffing each against benchmarks-latest.md as you go.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import sys
from collections.abc import Awaitable, Callable
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Literal
from urllib.parse import urlparse, urlunparse

from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

# Bootstrap project root so `app.*` imports resolve when running as a script.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.config import settings  # noqa: E402
from scripts.benchmarks import (  # noqa: E402
    chapter1,
    chapter2,
    chapter3,
    chapter3_3,
    chapter3_4,
    chapter4,
)

DbTarget = Literal["benchmark", "dev"]

# Port map for --db targets (CLAUDE.md). prod is intentionally excluded: prod is not the
# benchmark source, and the generator must never read the live DB for zone calibration.
_TARGET_PORT: dict[str, int] = {
    "benchmark": 5433,
    "dev": 5432,
}

_LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}

# Default output directory for the artifact pair (JSON + markdown), relative to repo root.
_DEFAULT_OUT = "reports/benchmark"


def _log(msg: str = "") -> None:
    """Print a message prefixed with a UTC timestamp (second precision)."""
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")


def _db_url(target: str) -> str:
    """Build the asyncpg URL for the chosen --db target (read-only use).

    Derives from settings.DATABASE_URL by replacing host:port with
    localhost:<target-port>. For non-default credentials (the benchmark DB runs
    postgres:postgres, not the dev app user), an override URL wins. We accept
    GEN_{TARGET}_DB_URL first, then fall back to BACKFILL_{TARGET}_DB_URL — the
    same var backfill_eval.py already reads, so an existing local .env points
    this script at the benchmark DB with no extra setup. The override host must
    be localhost (benchmark/dev are reached via Docker on the workstation).
    """
    if target not in _TARGET_PORT:
        raise ValueError(f"Unknown --db target: {target!r}. Must be one of: {list(_TARGET_PORT)}")

    for var in (f"GEN_{target.upper()}_DB_URL", f"BACKFILL_{target.upper()}_DB_URL"):
        override = os.environ.get(var)
        if not override:
            continue
        host = urlparse(override).hostname
        if host not in _LOCAL_HOSTS:
            raise ValueError(
                f"{var} host is {host!r}, but this script reaches the database via "
                f"localhost. Use localhost:{_TARGET_PORT[target]} (keeping creds)."
            )
        return override

    parsed = urlparse(settings.DATABASE_URL)
    new_netloc = f"{parsed.username}:{parsed.password}@localhost:{_TARGET_PORT[target]}"
    return urlunparse(parsed._replace(netloc=new_netloc))


async def _enforce_read_only(session: AsyncSession) -> None:
    """Pin the session to a read-only transaction.

    The benchmark DB exposes a read-only role, but the app credentials in
    settings.DATABASE_URL are read-write. Setting the transaction read-only is a
    cheap guardrail so a stray write in a half-ported chapter aborts loudly
    instead of mutating the calibration source.
    """
    await session.execute(text("SET TRANSACTION READ ONLY"))


async def _sanity_check(session: AsyncSession) -> dict[str, Any]:
    """Prove connectivity + that we're pointed at a benchmark-shaped DB.

    Returns a small dict that lands in the artifact's `meta` block. Cheap counts
    only — the real cohort construction (§1 Stratified Sample) is a chapter stub.
    """
    selected_users = (
        await session.execute(text("SELECT COUNT(*) FROM benchmark_selected_users"))
    ).scalar_one()
    games = (await session.execute(text("SELECT COUNT(*) FROM games"))).scalar_one()
    return {"benchmark_selected_users": selected_users, "games": games}


# ---------------------------------------------------------------------------
# Chapter stubs — one entry per SKILL.md section that must be ported.
# Fill `_generate_chapters` in one section at a time; diff each against
# reports/benchmark/benchmarks-latest.md before moving to the next.
# ---------------------------------------------------------------------------

CHAPTER_STUBS: tuple[tuple[str, str], ...] = (
    ("1-stratified-sample", "SKILL.md §1 — cohort construction, game-time ELO + TC bucketing"),
    ("2.1-openings-middlegame-eval", "SKILL.md §2.1 — middlegame-entry eval distribution"),
    ("3.1-endgame-overall", "SKILL.md §3.1 — endgame overall performance (score-gap)"),
    ("3.2-endgame-metrics-elo", "SKILL.md §3.2 — Conversion/Parity/Recovery + composite vs ELO"),
    ("3.3-time-pressure", "SKILL.md §3.3 — time-pressure stats + per-pressure-bin curves"),
    ("3.4-endgame-type", "SKILL.md §3.4 — per-class (rook/minor/pawn/queen/mixed/pawnless)"),
    (
        "4-global-percentile-cdf",
        "SKILL.md §4 — already deterministic via gen_global_percentile_cdf.py",
    ),
)


# Registry of ported chapters. Keys match CHAPTER_STUBS; unported keys fall back
# to `_stub_chapter`. Shared building blocks (game-time ELO + TC bucketing,
# equal-footing filter, sparse-cell exclusion, Cohen's d, IQR) live in the
# `scripts.benchmarks` subpackage (importable + unit-tested via tests/scripts/).
_CHAPTER_BUILDERS: dict[str, Callable[[AsyncSession], Awaitable[dict[str, Any]]]] = {
    "1-stratified-sample": chapter1.build,
    "2.1-openings-middlegame-eval": chapter2.build,
    "3.1-endgame-overall": chapter3.build,
    "3.2-endgame-metrics-elo": chapter3.build_32,
    "3.3-time-pressure": chapter3_3.build,
    "3.4-endgame-type": chapter3_4.build,
    # §4 is a separate deliverable (its own generator + report + gates); the chapter is a
    # reference-only payload (markdown=None) that records cross-refs without a report body.
    "4-global-percentile-cdf": chapter4.build,
}


async def _generate_chapters(session: AsyncSession) -> dict[str, Any]:
    """Compute every benchmark chapter into a structured dict.

    Ported chapters (in `_CHAPTER_BUILDERS`) emit real numbers + rendered markdown,
    validated against benchmarks-latest.md within rounding. Unported chapters fall
    back to a TODO stub. Port one section at a time, diffing each before the next.
    """
    chapters: dict[str, Any] = {}
    for key, todo in CHAPTER_STUBS:
        builder = _CHAPTER_BUILDERS.get(key)
        chapters[key] = await builder(session) if builder is not None else _stub_chapter(key, todo)
    return chapters


def _stub_chapter(key: str, todo: str) -> dict[str, Any]:
    """Placeholder chapter payload. Marks the section as not-yet-ported."""
    return {"status": "TODO", "section": todo, "tables": [], "values": {}}


def _build_artifact(meta: dict[str, Any], chapters: dict[str, Any]) -> dict[str, Any]:
    """Assemble the full benchmark artifact (the JSON half of the output pair)."""
    return {"meta": meta, "chapters": chapters}


def _render_markdown(artifact: dict[str, Any]) -> str:
    """Render the artifact as markdown tables (the MD half of the output pair).

    SCAFFOLD: emits a skeleton mirroring the SKILL.md "Report file layout" so the
    SKILL.md narrator has a stable shape to fill. Real table rendering (display
    formatting rules, §"Display formatting") lands with the chapter ports.
    """
    meta = artifact["meta"]
    lines = [
        f"# FlawChess Benchmarks — {meta.get('generated_at', '<DATE>')}",
        "",
        "> SCAFFOLD output from scripts/gen_benchmarks.py. Chapters are stubs (SEED-029 Phase A).",
        "",
        f"- DB target: `{meta.get('db_target')}`",
        f"- benchmark_selected_users: {meta.get('sanity', {}).get('benchmark_selected_users', '?')}",
        f"- games: {meta.get('sanity', {}).get('games', '?')}",
        "",
    ]
    for key, chapter in artifact["chapters"].items():
        md = chapter.get("markdown")
        if md:
            lines.append(md)
        elif chapter.get("status") == "REFERENCE":
            # Separate deliverable (e.g. §4 percentile CDF) — cross-ref lives in the JSON
            # artifact, not the benchmark report body. Skip it here.
            continue
        else:
            lines.append(f"## {key}")
            lines.append(f"_{chapter['status']}: {chapter['section']}_")
        lines.append("")
    return "\n".join(lines)


def _write_outputs(out_dir: Path, artifact: dict[str, Any]) -> tuple[Path, Path]:
    """Write the JSON + markdown artifact pair. Returns their paths.

    NOTE: does not yet implement the SKILL.md date-based rotation rule (rotate a
    prior benchmarks-latest.md to a dated filename). That lands when the port is
    complete and this script owns report emission. For now writes scaffold files
    under a `gen-scaffold` prefix so it can't clobber the real latest report.
    """
    out_dir.mkdir(parents=True, exist_ok=True)
    json_path = out_dir / "gen-scaffold-benchmarks.json"
    md_path = out_dir / "gen-scaffold-benchmarks.md"
    json_path.write_text(json.dumps(artifact, indent=2, sort_keys=True, ensure_ascii=False))
    md_path.write_text(_render_markdown(artifact))
    return json_path, md_path


async def run_generate(*, db: DbTarget, out: str, dry_run: bool) -> dict[str, Any]:
    """Generate the benchmark artifact. Public callable for testability.

    dry_run: connect, run the sanity check, and exit without computing chapters
    or writing files — a connectivity smoke test.
    """
    url = _db_url(db)
    engine = create_async_engine(url, pool_pre_ping=True)
    session_maker = async_sessionmaker(engine, expire_on_commit=False)
    try:
        async with session_maker() as session:
            await _enforce_read_only(session)
            sanity = await _sanity_check(session)
            _log(f"Sanity: {sanity}")
            if dry_run:
                _log("--dry-run: connectivity OK; not computing chapters or writing files.")
                return {"meta": {"db_target": db, "sanity": sanity}, "chapters": {}}

            chapters = await _generate_chapters(session)

        meta = {
            "db_target": db,
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "sanity": sanity,
        }
        artifact = _build_artifact(meta, chapters)
        json_path, md_path = _write_outputs(Path(out), artifact)
        _log(f"Wrote artifact: {json_path}")
        _log(f"Wrote markdown: {md_path}")
        return artifact
    finally:
        await engine.dispose()


def parse_args() -> argparse.Namespace:
    """Parse and validate CLI arguments."""
    parser = argparse.ArgumentParser(
        description="Deterministic generator for the FlawChess benchmark report (SEED-029, Phase A)."
    )
    parser.add_argument(
        "--db",
        choices=list(_TARGET_PORT),
        required=True,
        help="Database target (read-only). benchmark=localhost:5433 (source), dev=localhost:5432 (smoke).",
    )
    parser.add_argument(
        "--out",
        default=_DEFAULT_OUT,
        metavar="DIR",
        help=f"Output directory for the JSON + markdown artifact pair (default: {_DEFAULT_OUT}).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dry_run",
        help="Connect and run the sanity check only; do not compute chapters or write files.",
    )
    return parser.parse_args()


def _load_dotenv() -> None:
    """Load the repo-root .env into os.environ (existing vars win).

    settings (pydantic-settings) reads .env into its own object, but _db_url's
    BACKFILL_{TARGET}_DB_URL override is read from os.environ. Loading .env here
    means `uv run python scripts/gen_benchmarks.py --db benchmark` resolves the
    benchmark credentials without a manual `export`. override=False keeps any
    var already set in the real environment authoritative.
    """
    from dotenv import load_dotenv

    load_dotenv(Path(__file__).resolve().parent.parent / ".env", override=False)


async def main() -> None:
    """Entry point: parse CLI args, run the generator."""
    _load_dotenv()
    args = parse_args()
    _log(f"Starting benchmark generation: db={args.db} out={args.out} dry_run={args.dry_run}")
    await run_generate(db=args.db, out=args.out, dry_run=args.dry_run)
    _log("Done.")


if __name__ == "__main__":
    asyncio.run(main())
