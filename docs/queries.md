# The Ten Learning Queries (M2)

Run with `uv run python scripts/run_queries.py` (all), `--query N` (one), or
`--query N --profile` (execution plan). The source of truth is
`src/graph/queries.py`; this file explains the progression.

Each query can also be pasted into the [Neo4j demo browser](https://demo.neo4jlabs.com:7473/browser/)
(user/pass `recommendations`) — replace `$param` placeholders with literals, or use
`:param title => 'Inception'` first.

| # | Query | What it teaches |
|---|---|---|
| 1 | Basic node lookup | `MATCH` + inline property filter — the graph's `SELECT … WHERE`. One node, no traversal yet. |
| 2 | One-hop traversal | Following `(Person)-[:ACTED_IN]->(Movie)` backwards to list a cast. The arrow *is* the join; the `role` property lives on the relationship, not in a join table. |
| 3 | Two-hop: co-actors | Chaining through an anonymous middle node `(:Movie)`. Equivalent SQL is a three-way self-join; Cypher just draws the path. |
| 4 | Shortest path (Bacon number) | `shortestPath()` + variable-length `[*..6]` — bidirectional BFS built into the database. The classic "hard in SQL (recursive CTE), one line in a graph" query. |
| 5 | Variable-length traversal | `[*1..4]` matches paths of *any* length 1–4: "everyone within N hops". Demonstrates exponential frontier growth and why you bound depth and `LIMIT`. |
| 6 | Content-based recommendation | Similarity via shared attributes: out to `Genre`, back in to other movies, rank by overlap. A recommender in five lines. |
| 7 | Collaborative filtering | Similarity via *behavior*: real MovieLens users who rated this movie ≥4 — what else did they love? Relationship properties (`r.rating`) drive the logic. |
| 8 | Pattern matching | The same node bound twice in one pattern (`(p)-[:ACTED_IN]->(m)<-[:DIRECTED]-(p)`) finds actors who directed themselves. The *shape* is the filter. |
| 9 | Aggregation | `count()` groups implicitly by the non-aggregated return columns — Cypher has no `GROUP BY`. |
| 10 | Multi-hop aggregation | Two-hop fan-out (director → movies → actors) summarized with `count(DISTINCT …)` — traversal and analytics in a single pass. |

## Reading a PROFILE plan

`--profile` prints the operator tree with `rows` and `dbHits` per operator
(a *db hit* ≈ one unit of storage work). Things to look for:

- **NodeIndexSeek vs. NodeByLabelScan** — did the anchor node come from an
  index lookup (fast) or a full label scan (slow)? Try profiling query 1.
- **Expand(All)** — the traversal step itself; its row count shows the
  frontier size at each hop. Compare query 3 against query 5 to watch the
  frontier explode as path length grows.
- **Filter position** — predicates applied *during* expansion prune the
  search early; predicates applied at the end mean wasted traversal.

The big comparison, coming in M3: the equivalent SQL for queries 3–7 needs
one JOIN *per hop* (with intermediate result sets growing at each step),
while the graph plan's cost tracks only the neighborhoods it actually visits
— that difference is index-free adjacency made visible.
