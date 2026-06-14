"""Re-arm already-stamped engine games with non-terminal eval holes (Phase 119 SEED-045).

Finds engine games (lichess_evals_at IS NULL) whose full_evals_completed_at is set
but that still carry at least one non-terminal hole (eval_cp IS NULL AND eval_mate IS NULL
on a ply that is not the terminal game-over ply). Clears their completion markers
(full_evals_completed_at, full_pv_completed_at) and resets full_eval_attempts to 0
so the bounded-retry drain re-picks them with a fresh MAX_EVAL_ATTEMPTS budget.

Usage:
    uv run python scripts/resweep_holed_games.py --dry-run        # count only
    uv run python scripts/resweep_holed_games.py                  # sweep all
    uv run python scripts/resweep_holed_games.py --limit 100      # sweep first 100
"""

import argparse
import asyncio
import sys

# Ensure the project root is on the path when run from the repo root.
sys.path.insert(0, "")


async def _main(dry_run: bool, limit: int | None) -> int:
    from app.services.eval_drain import resweep_holed_games

    count = await resweep_holed_games(limit=limit, dry_run=dry_run)
    action = "Would sweep" if dry_run else "Swept"
    print(f"{action} {count} game(s) with non-terminal eval holes.")
    return count


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Re-arm engine games with non-terminal eval holes for the bounded-retry drain."
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        default=False,
        help="Count candidates without updating (default: False).",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Cap the scan at N games (default: all).",
    )
    args = parser.parse_args()
    asyncio.run(_main(dry_run=args.dry_run, limit=args.limit))


if __name__ == "__main__":
    main()
