"""M2 verification: run the ten progressive learning queries.

Usage:
    uv run python scripts/run_queries.py                # run all ten
    uv run python scripts/run_queries.py --query 4      # run one
    uv run python scripts/run_queries.py --query 4 --profile   # show its plan
"""

import argparse
import sys
import textwrap

from graph.connection import get_connection
from graph.queries import CATALOG, get_query, profile_query, run_query

MAX_ROWS_SHOWN = 10


def print_result(rows: list[dict]) -> None:
    if not rows:
        print("  (no rows)")
        return
    for row in rows[:MAX_ROWS_SHOWN]:
        cells = ", ".join(f"{k}={v!r}" for k, v in row.items())
        print(textwrap.shorten(f"  {cells}", width=120, placeholder=" …"))
    if len(rows) > MAX_ROWS_SHOWN:
        print(f"  … {len(rows) - MAX_ROWS_SHOWN} more rows")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--query", type=int, help="run a single query by number (1-10)")
    parser.add_argument("--profile", action="store_true", help="show the PROFILE plan instead")
    args = parser.parse_args()

    conn = get_connection()
    try:
        conn.verify()
    except Exception as exc:
        print(f"CONNECTION FAILED: {exc}\nSee scripts/check_connection.py for troubleshooting.")
        return 1

    queries = [get_query(args.query)] if args.query else CATALOG
    for q in queries:
        print(f"\n{'=' * 70}\n#{q.number} — {q.title}")
        print(textwrap.fill(q.concept, width=70, initial_indent="   ", subsequent_indent="   "))
        if args.profile:
            print("\n" + profile_query(conn, q))
        else:
            print_result(run_query(conn, q))
    return 0


if __name__ == "__main__":
    sys.exit(main())
