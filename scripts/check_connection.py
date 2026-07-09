"""M0 verification: connect to the graph and print basic stats.

Usage:
    uv run python scripts/check_connection.py

Expected output (against the public `recommendations` demo database): the
server address, read-only status, and node/relationship counts in the
tens/hundreds of thousands.
"""

import sys

from graph.connection import get_connection


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    conn = get_connection()
    print(f"Connecting to {conn.uri} (database: {conn.database}) ...")
    try:
        conn.verify()
    except Exception as exc:
        print(f"\nCONNECTION FAILED: {exc}")
        print(
            "\nTroubleshooting:\n"
            "  - Check your .env (copy .env.example if missing).\n"
            "  - The demo server needs outbound TLS on port 7687; some corporate\n"
            "    or sandboxed networks block non-443 ports.\n"
            "  - Try opening https://demo.neo4jlabs.com:7473 in a browser to see\n"
            "    if the host is reachable at all."
        )
        return 1

    print("Connected.")
    writeable = conn.is_writeable()
    print(f"Backend writeable: {writeable}" + ("" if writeable else " (read-only, as expected)"))

    nodes = conn.run("MATCH (n) RETURN count(n) AS c")[0]["c"]
    rels = conn.run("MATCH ()-[r]->() RETURN count(r) AS c")[0]["c"]
    print(f"Nodes:         {nodes:,}")
    print(f"Relationships: {rels:,}")

    sample = conn.run(
        "MATCH (m:Movie) RETURN m.title AS title, m.year AS year ORDER BY m.year DESC LIMIT 5"
    )
    print("\nSample movies:")
    for row in sample:
        print(f"  - {row['title']} ({row['year']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
