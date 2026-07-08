"""The M2 learning-query catalog: ten progressively harder Cypher queries.

Learning notes (M2):

Cypher is *declarative pattern matching*: you draw the shape you want in
ASCII-art — ``(a)-[:REL]->(b)`` — and the database finds every occurrence.
The progression below builds from single-node lookup to multi-hop
aggregation; each entry records the concept it teaches.

All queries are parameterized (``$name``-style). Parameters are sent
separately from the query text, which is both faster (plan caching) and the
Cypher analogue of SQL's defense against injection.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from graph.connection import GraphConnection


@dataclass(frozen=True)
class LearningQuery:
    number: int
    title: str
    concept: str
    cypher: str
    params: dict[str, Any] = field(default_factory=dict)


CATALOG: list[LearningQuery] = [
    LearningQuery(
        number=1,
        title="Basic node lookup",
        concept=(
            "MATCH with an inline property filter — the graph 'SELECT * WHERE'. "
            "Finds one node by exact property value."
        ),
        cypher="""
            MATCH (m:Movie {title: $title})
            RETURN m.title AS title, m.year AS year, m.imdbRating AS imdbRating, m.plot AS plot
        """,
        params={"title": "Inception"},
    ),
    LearningQuery(
        number=2,
        title="One-hop traversal: who acted in a movie",
        concept=(
            "Following a relationship. The arrow direction reads like the data: "
            "(Person)-[:ACTED_IN]->(Movie). No join table, no JOIN keyword."
        ),
        cypher="""
            MATCH (m:Movie {title: $title})<-[a:ACTED_IN]-(p:Person)
            RETURN p.name AS actor, a.role AS role
            ORDER BY actor
        """,
        params={"title": "Inception"},
    ),
    LearningQuery(
        number=3,
        title="Two-hop traversal: co-actors",
        concept=(
            "Chaining hops through an anonymous middle node (:Movie). In SQL this "
            "is already a three-table self-join; in Cypher it's one drawn path."
        ),
        cypher="""
            MATCH (p:Person {name: $name})-[:ACTED_IN]->(:Movie)<-[:ACTED_IN]-(co:Person)
            RETURN co.name AS coActor, count(*) AS sharedMovies
            ORDER BY sharedMovies DESC, coActor
            LIMIT 15
        """,
        params={"name": "Leonardo DiCaprio"},
    ),
    LearningQuery(
        number=4,
        title="Shortest path: degrees of separation (Bacon number)",
        concept=(
            "shortestPath() with a variable-length pattern [*..6] does a "
            "bidirectional breadth-first search — the classic query class that "
            "is painful in SQL (recursive CTEs) and native in a graph."
        ),
        cypher="""
            MATCH p = shortestPath(
                (a:Person {name: $from_name})-[:ACTED_IN*..6]-(b:Person {name: $to_name})
            )
            RETURN length(p) / 2 AS degreesOfSeparation,
                   [n IN nodes(p) | coalesce(n.title, n.name)] AS chain
        """,
        params={"from_name": "Kevin Bacon", "to_name": "Keanu Reeves"},
    ),
    LearningQuery(
        number=5,
        title="Variable-length traversal: collaboration network",
        concept=(
            "[*1..4] matches paths of ANY length 1-4 — 'everyone within N hops'. "
            "The frontier grows exponentially with depth; LIMIT keeps it sane."
        ),
        cypher="""
            MATCH (a:Person {name: $name})-[:ACTED_IN*1..4]-(other:Person)
            WHERE other <> a
            RETURN DISTINCT other.name AS person
            LIMIT 25
        """,
        params={"name": "Tom Hanks"},
    ),
    LearningQuery(
        number=6,
        title="Content-based recommendation: shared genres",
        concept=(
            "Similarity via shared attributes: hop OUT to genres, back IN to other "
            "movies, rank by overlap. A recommendation engine in five lines."
        ),
        cypher="""
            MATCH (m:Movie {title: $title})-[:IN_GENRE]->(g:Genre)<-[:IN_GENRE]-(rec:Movie)
            WHERE rec <> m AND rec.imdbRating IS NOT NULL
            RETURN rec.title AS recommendation, rec.imdbRating AS imdbRating,
                   collect(g.name) AS sharedGenres, count(g) AS overlap
            ORDER BY overlap DESC, imdbRating DESC
            LIMIT 10
        """,
        params={"title": "Inception"},
    ),
    LearningQuery(
        number=7,
        title="Collaborative filtering: users like you also liked",
        concept=(
            "Uses behavior (RATED relationships from real MovieLens users) instead "
            "of content: find users who liked this movie, surface what else they "
            "rated highly. Relationship properties (r.rating) drive the filter."
        ),
        cypher="""
            MATCH (m:Movie {title: $title})<-[r1:RATED]-(u:User)-[r2:RATED]->(rec:Movie)
            WHERE r1.rating >= 4 AND r2.rating >= 4 AND rec <> m
            RETURN rec.title AS recommendation,
                   count(u) AS fans,
                   round(avg(r2.rating), 2) AS avgRating
            ORDER BY fans DESC
            LIMIT 10
        """,
        params={"title": "Inception"},
    ),
    LearningQuery(
        number=8,
        title="Pattern matching: actors who directed themselves",
        concept=(
            "Structural search — the same node bound twice in one pattern "
            "(acted in AND directed the same movie). No WHERE gymnastics needed; "
            "the shape IS the filter."
        ),
        cypher="""
            MATCH (p:Person)-[:ACTED_IN]->(m:Movie)<-[:DIRECTED]-(p)
            RETURN p.name AS person, collect(m.title)[..5] AS examples,
                   count(m) AS selfDirected
            ORDER BY selfDirected DESC
            LIMIT 10
        """,
    ),
    LearningQuery(
        number=9,
        title="Aggregation: most prolific actors",
        concept=(
            "count()/collect() group implicitly by the non-aggregated columns — "
            "no GROUP BY clause exists in Cypher."
        ),
        cypher="""
            MATCH (p:Person)-[:ACTED_IN]->(m:Movie)
            RETURN p.name AS actor, count(m) AS movies
            ORDER BY movies DESC
            LIMIT 10
        """,
    ),
    LearningQuery(
        number=10,
        title="Multi-hop aggregation: directors with the widest actor network",
        concept=(
            "Traversal + aggregation combined: for each director, count DISTINCT "
            "actors across all their movies — a two-hop fan-out summarized in one "
            "pass. The graph analogue of a JOIN + GROUP BY + COUNT(DISTINCT)."
        ),
        cypher="""
            MATCH (d:Person)-[:DIRECTED]->(m:Movie)<-[:ACTED_IN]-(a:Person)
            RETURN d.name AS director,
                   count(DISTINCT a) AS uniqueActors,
                   count(DISTINCT m) AS movies
            ORDER BY uniqueActors DESC
            LIMIT 10
        """,
    ),
]


def get_query(number: int) -> LearningQuery:
    for q in CATALOG:
        if q.number == number:
            return q
    raise ValueError(f"No learning query #{number} (valid: 1-{len(CATALOG)})")


def run_query(conn: GraphConnection, query: LearningQuery) -> list[dict]:
    return conn.run(query.cypher, **query.params)


def profile_query(conn: GraphConnection, query: LearningQuery) -> str:
    """Return the PROFILE execution plan as printable text.

    PROFILE actually runs the query and annotates each plan operator with
    db hits and row counts — the tool for understanding HOW a traversal
    executes (index seek vs. scan, expand ordering, filtering position).
    """
    records, summary, _ = conn._driver.execute_query(
        "PROFILE " + query.cypher, query.params, database_=conn.database
    )

    def render(op, depth=0) -> list[str]:
        args = op.get("args", {})
        details = args.get("Details", "")
        hits = args.get("DbHits", "?")
        rows = args.get("Rows", "?")
        line = f"{'  ' * depth}{op['operatorType']}  [rows={rows}, dbHits={hits}]" + (
            f"  {details}" if details else ""
        )
        lines = [line]
        for child in op.get("children", []):
            lines.extend(render(child, depth + 1))
        return lines

    return "\n".join(render(summary.profile))
