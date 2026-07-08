"""M1 verification: introspect the live graph schema and print a report.

Usage:
    uv run python scripts/discover_schema.py            # print to stdout
    uv run python scripts/discover_schema.py --write    # also refresh the
                                                        # snapshot section in
                                                        # docs/graph-model.md
"""

import sys
from pathlib import Path

from graph.connection import get_connection
from graph.schema_discovery import discover, format_report

SNAPSHOT_MARKER = "<!-- LIVE-SCHEMA-SNAPSHOT -->"


def main() -> int:
    conn = get_connection()
    print(f"Introspecting {conn.uri} (database: {conn.database}) ...\n")
    try:
        conn.verify()
    except Exception as exc:
        print(f"CONNECTION FAILED: {exc}\nSee scripts/check_connection.py for troubleshooting.")
        return 1

    report = format_report(discover(conn))
    print(report)

    if "--write" in sys.argv:
        doc = Path(__file__).resolve().parent.parent / "docs" / "graph-model.md"
        text = doc.read_text()
        head, marker, _ = text.partition(SNAPSHOT_MARKER)
        if not marker:
            print(f"\nMarker {SNAPSHOT_MARKER} not found in {doc}; not writing.")
            return 1
        doc.write_text(head + marker + "\n\n" + report + "\n")
        print(f"\nSnapshot written to {doc}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
