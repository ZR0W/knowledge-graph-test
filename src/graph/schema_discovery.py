"""Schema discovery: introspect a live Neo4j graph's structure.

Learning notes (M1):

Unlike a relational database, Neo4j has no CREATE TABLE — the "schema" is
*emergent*: it is simply whatever labels, relationship types, and properties
the data actually uses. These built-in procedures let you reverse-engineer it:

- ``db.labels()`` / ``db.relationshipTypes()`` — every label/type in use
- ``db.schema.visualization()`` — a meta-graph of how labels connect
- ``keys(n)`` on sampled nodes — property keys actually present (two nodes
  with the same label may carry different properties!)

This "schema on read" flexibility is a defining trade-off vs. relational
databases: faster evolution, but the discipline of consistency moves from the
database into your code.
"""

from __future__ import annotations

from typing import Any

from graph.connection import GraphConnection

# How many nodes/relationships to sample per label/type when collecting
# property keys. Sampling keeps introspection fast on large graphs.
PROPERTY_SAMPLE_SIZE = 500


def get_labels(conn: GraphConnection) -> list[str]:
    return [row["label"] for row in conn.run("CALL db.labels() YIELD label RETURN label")]


def get_relationship_types(conn: GraphConnection) -> list[str]:
    return [
        row["relationshipType"]
        for row in conn.run(
            "CALL db.relationshipTypes() YIELD relationshipType RETURN relationshipType"
        )
    ]


def count_nodes_by_label(conn: GraphConnection) -> dict[str, int]:
    counts = {}
    for label in get_labels(conn):
        # Labels come from the database itself (not user input), so direct
        # interpolation is safe here; Cypher cannot parameterize labels.
        row = conn.run(f"MATCH (n:`{label}`) RETURN count(n) AS c")
        counts[label] = row[0]["c"]
    return counts


def count_relationships_by_type(conn: GraphConnection) -> dict[str, int]:
    counts = {}
    for rel_type in get_relationship_types(conn):
        row = conn.run(f"MATCH ()-[r:`{rel_type}`]->() RETURN count(r) AS c")
        counts[rel_type] = row[0]["c"]
    return counts


def get_node_properties(conn: GraphConnection, label: str) -> list[str]:
    """Property keys present on a sample of nodes with this label."""
    rows = conn.run(
        f"MATCH (n:`{label}`) WITH n LIMIT $sample "
        "UNWIND keys(n) AS key RETURN DISTINCT key ORDER BY key",
        sample=PROPERTY_SAMPLE_SIZE,
    )
    return [row["key"] for row in rows]


def get_relationship_properties(conn: GraphConnection, rel_type: str) -> list[str]:
    """Property keys present on a sample of relationships of this type."""
    rows = conn.run(
        f"MATCH ()-[r:`{rel_type}`]->() WITH r LIMIT $sample "
        "UNWIND keys(r) AS key RETURN DISTINCT key ORDER BY key",
        sample=PROPERTY_SAMPLE_SIZE,
    )
    return [row["key"] for row in rows]


def get_connection_patterns(conn: GraphConnection) -> list[dict[str, str]]:
    """Which label connects to which via what relationship type.

    Sampled from real relationships, this yields patterns like
    ``(Actor)-[:ACTED_IN]->(Movie)`` — the graph equivalent of foreign keys.
    """
    rows = conn.run(
        "MATCH (a)-[r]->(b) WITH labels(a) AS from, type(r) AS rel, labels(b) AS to, count(*) AS c "
        "RETURN from, rel, to, c ORDER BY c DESC LIMIT 50"
    )
    return [
        {
            "from": ":".join(row["from"]),
            "rel": row["rel"],
            "to": ":".join(row["to"]),
            "count": row["c"],
        }
        for row in rows
    ]


def discover(conn: GraphConnection) -> dict[str, Any]:
    """Full schema snapshot as one structured dict."""
    return {
        "node_counts": count_nodes_by_label(conn),
        "relationship_counts": count_relationships_by_type(conn),
        "node_properties": {
            label: get_node_properties(conn, label) for label in get_labels(conn)
        },
        "relationship_properties": {
            rel: get_relationship_properties(conn, rel) for rel in get_relationship_types(conn)
        },
        "patterns": get_connection_patterns(conn),
    }


def format_report(schema: dict[str, Any]) -> str:
    """Render a discover() snapshot as readable markdown."""
    lines = ["# Discovered Graph Schema", ""]

    lines.append("## Node labels")
    for label, count in sorted(schema["node_counts"].items(), key=lambda kv: -kv[1]):
        props = ", ".join(schema["node_properties"].get(label, []))
        lines.append(f"- **{label}** ({count:,} nodes) — properties: {props}")

    lines.append("")
    lines.append("## Relationship types")
    for rel, count in sorted(schema["relationship_counts"].items(), key=lambda kv: -kv[1]):
        props = ", ".join(schema["relationship_properties"].get(rel, [])) or "(none)"
        lines.append(f"- **{rel}** ({count:,} relationships) — properties: {props}")

    lines.append("")
    lines.append("## Connection patterns")
    for p in schema["patterns"]:
        lines.append(f"- `({p['from']})-[:{p['rel']}]->({p['to']})` × {p['count']:,}")

    return "\n".join(lines)
