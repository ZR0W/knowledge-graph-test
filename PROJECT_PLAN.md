# Learning Graph Databases via a Movie Knowledge Graph + MCP Server

## Context

This repository (`knowledge-graph-test`) is currently completely empty — no code, no docs, no tooling. The goal is not to build a production system but to **learn graph database fundamentals hands-on**: how graphs model relationships, how graph querying/traversal works, how graph DBs compare to relational and vector databases, and — as the capstone — how to expose a graph database as an MCP server and connect an LLM to it so it can query and reason over the graph.

**Confirmed user decisions:**
- **Domain:** Movies/Actors/Genres/Users
- **Language:** Python
- **LLM integration:** Both Claude Desktop (interactive) and a scripted Anthropic API client (explicit tool-use loop)
- **Database: NO Docker, NO local install.** Primary database is Neo4j's free **public read-only demo server** (`neo4j+s://demo.neo4jlabs.com`, `recommendations` database — a pre-filled movie graph; credentials = database name for both username and password). This gives instant access to rich, real data with zero setup.
- **AuraDB Free upgrade path must be fully documented and executable on demand:** all write-oriented functionality (`add_entity`, `create_relationship`, seeding, agent memory) is designed and implemented in this project but only runnable once the user (or their agent, when prompted) provisions a free Neo4j AuraDB instance and flips the connection config. The repo docs must contain a complete, step-by-step `docs/auradb-upgrade.md` so an agent can execute the switch without further research.

Every choice below favors simplicity, strong documentation, and direct learning value over robustness or scale.

---

## 1. Learning Roadmap

| Phase | Focus | Why it matters |
|---|---|---|
| 0 — Environment | Python env, Neo4j driver, connect to the public demo server | Everything else depends on a working connection; zero infrastructure to install |
| 1 — Schema Discovery & Modeling | Explore the pre-filled `recommendations` graph; understand property-graph modeling by reverse-engineering a real schema | Graph modeling is a real mental shift from relational normalization; learning it from live data beats toy examples |
| 2 — Querying & Traversal | Cypher: pattern matching, variable-length paths, shortest path, aggregation | This is the heart of "how graph querying works" |
| 3 — Comparative Analysis | Same questions in SQL (local SQLite) + a naive vector-similarity example | Makes the graph DB's advantages concrete instead of theoretical |
| 4 — MCP Server Basics | MCP protocol, tool schemas, stdio transport | Learn MCP mechanics before layering an LLM on top |
| 5 — Full Tool Surface + Testing | Parameterized Cypher, injection safety, pytest against the live demo server | Real engineering practice around a graph-backed service |
| 6 — LLM Integration | Tool-calling loop, Claude Desktop + Anthropic SDK | The payoff: LLM reasoning over a graph |
| 7 — Demo Scenarios | End-to-end multi-hop Q&A | Consolidates and demonstrates everything learned |
| 8 — AuraDB Upgrade (on demand) + Stretch | Provision AuraDB Free, enable write tools, agent memory, hybrid vector search | Unlocks the write half of the project when desired |

---

## 2. Recommended Tech Stack

| Concern | Choice | Why |
|---|---|---|
| Language | **Python** | One language covers the Neo4j driver, the official MCP SDK, and the Anthropic SDK with minimal glue |
| Graph DB (primary) | **Neo4j public demo server** — `neo4j+s://demo.neo4jlabs.com`, database `recommendations` (user/pass both `recommendations`) | Zero install, zero Docker, pre-filled with a rich movie graph (movies, actors, directors, genres, real user ratings) — instant querying on day one |
| Graph DB (upgrade path) | **Neo4j AuraDB Free** (cloud, free, no credit card, ~200K nodes / 400K relationships) | Writeable; unlocks `add_entity`/`create_relationship`/seeding/agent-memory; same Cypher, same driver, only the URI/credentials change |
| Query language | **Cypher** | Most human-readable graph query language, most widely taught, native to Neo4j |
| MCP framework | **Official `mcp` Python SDK (FastMCP)** | Official, actively maintained, decorator-based tool definitions are the fastest path from function to LLM-callable tool |
| LLM integration | **Claude Desktop (interactive, config-only) + scripted Python client using the Anthropic SDK** | Desktop gives zero-code interactive exploration; the scripted client makes tool-calling mechanics explicit and produces repeatable demo transcripts |
| Backend framework | **None** | MCP server talks over stdio directly; an HTTP layer is unnecessary complexity |
| Dev tooling | **`uv`** (deps/venv) + **`ruff`** (lint/format) | Fast, minimal config, standard in current MCP quickstart docs |
| Docker | **Not used** | Avoided entirely per user constraint (Windows stability); the demo server / AuraDB are both remote |
| Testing | **`pytest`** with read-only integration tests against the live demo server; write-tool tests documented to run only against AuraDB | No container tooling needed; live read-only DB is stable and free to hit |
| Visualization | **Neo4j Browser / Workspace** (works against both demo server and AuraDB) + **neovis.js** (stretch) | Zero-setup built-in visualization |
| IDE | **VS Code** + Python/Neo4j-Cypher extensions | Free, first-class support for every layer of this stack |

---

## 3. Architecture

```
 ┌────────────────────┐        stdio (MCP/JSON-RPC)         ┌──────────────────────────┐
 │  Claude Desktop     │◄────────────────────────────────────►│   MCP Server (Python)   │
 │  (interactive)      │                                       │   FastMCP tool functions │
 └────────────────────┘                                       │   read tools: always on  │
                                                                │   write tools: enabled   │
 ┌────────────────────┐        stdio (MCP/JSON-RPC)           │   only if backend is     │
 │  Python demo client │◄────────────────────────────────────►│   writeable (AuraDB)     │
 │  (Anthropic SDK,    │                                       └────────────┬─────────────┘
 │  scripted tool loop)│                                                    │ neo4j+s://
 └────────────────────┘                                                    ▼
                                                     ┌───────────────────────────────────────┐
                                                     │  PRIMARY: demo.neo4jlabs.com          │
                                                     │  `recommendations` DB (read-only,     │
                                                     │  pre-filled movie graph)              │
                                                     ├───────────────────────────────────────┤
                                                     │  UPGRADE: Neo4j AuraDB Free           │
                                                     │  (writeable; swap URI + credentials   │
                                                     │  in .env — see docs/auradb-upgrade.md)│
                                                     └───────────────────────────────────────┘
```

Flow: **User → Claude → Claude picks an MCP tool → MCP Server → parameterized Cypher via the Neo4j Python driver → remote Neo4j → results → MCP Server → Claude → (may chain another tool call) → final answer.**

The database connection is configured entirely via `.env` (`NEO4J_URI`, `NEO4J_USERNAME`, `NEO4J_PASSWORD`, `NEO4J_DATABASE`). The MCP server detects at startup whether the backend is writeable and registers write tools only when it is — so the identical codebase serves both the demo server and AuraDB.

---

## 4. Domain: Movies (via the `recommendations` demo dataset)

The public `recommendations` database is a real, pre-filled movie graph containing movies, actors, directors, genres, and genuine user ratings — an almost exact match for the model this project would otherwise have hand-seeded. It supports all three target use cases: multi-hop traversal (actor↔movie↔genre↔actor), recommendations (content-based via shared genre/director, collaborative via shared user ratings), and shortest path ("degrees of separation" / Bacon number). Because it's the dataset Neo4j's own tutorials use, documentation and example queries are abundant.

---

## 5. Incremental Milestones

| # | Milestone | Goal / Features | Tech introduced | Learning outcome | Effort |
|---|---|---|---|---|---|
| M0 | Environment setup | `uv` project scaffold; `.env` config; verify connection to `neo4j+s://demo.neo4jlabs.com` (`recommendations`/`recommendations`) from a Python script; open the graph in Neo4j Browser | `uv`, `neo4j` driver, Bolt/TLS URIs | Driver basics, remote graph connectivity — with zero installs | 1–2 hrs |
| M1 | Schema discovery & modeling | Script that introspects labels, relationship types, properties, counts (`db.schema.visualization()`, `db.labels()`); write up the discovered model in `docs/graph-model.md`; design what a from-scratch seed script *would* look like (goes in the AuraDB upgrade path) | Cypher schema procedures | Property-graph modeling vs. relational normalization, learned from real data | Half day |
| M2 | Querying & traversal | Progressive Cypher (Section 7): lookup → traversal → shortest path → recommendations → aggregation, run in Browser and via driver; inspect plans with `EXPLAIN`/`PROFILE` | Cypher deep dive | How traversal and query planning work | Half day |
| M3 | Comparative analysis | Export a small slice of the graph to local SQLite; write equivalent multi-hop JOIN queries; small cosine-similarity example over movie-plot embeddings | SQLite, numpy/embeddings | Feel the "JOIN explosion" vs. traversal; see where vector search wins (semantic similarity) vs. graph (explicit relationships) | Half–1 day |
| M4 | MCP server skeleton | FastMCP server; implement `get_schema` and `search_nodes`; test with MCP Inspector | `mcp` Python SDK, FastMCP | MCP protocol basics, tool schema definition | Half day |
| M5 | Full MCP tool surface + tests | Implement `find_neighbors`, `shortest_path`, `recommend_similar`, `explain_graph`; implement `add_entity`/`create_relationship` **code-complete but gated on a writeable backend**; `pytest` read-only integration tests against the demo server | Parameterized Cypher, capability gating | Injection-safe dynamic queries, integration testing patterns | 1 day |
| M6 | LLM integration | Wire MCP server into Claude Desktop config; write an Anthropic SDK script with an explicit tool-use loop | Anthropic SDK, MCP client config | How an LLM selects and chains tool calls | Half day |
| M7 | Demo scenarios (capstone) | Run all 5 demo scenarios end to end; capture transcripts | — | Articulate the graph DB's value proposition with evidence | Half day |
| M8 | AuraDB upgrade (on demand) | Follow `docs/auradb-upgrade.md`: provision AuraDB Free, load the movie sample dataset (one click) or run the seed script, swap `.env`, confirm write tools activate, run write-tool tests | Neo4j AuraDB | Cloud provisioning, seeding with `MERGE`, constraints/indexes | Half day |
| M9+ | Stretch goals (pick 1–2) | See Section 10 | Varies | Varies | 1–3 days each |

Core path (M0–M7): roughly **4–5 focused days**. M8 runs whenever the user prompts their agent to execute it.

---

## 6. Graph Model (as found in the `recommendations` dataset)

**Nodes:** `Movie {title, released, plot, imdbRating, …}` · `Person`/`Actor`/`Director` `{name, born, …}` · `Genre {name}` · `User {name}`

**Relationships:**
- `(Actor)-[:ACTED_IN {role}]->(Movie)`
- `(Director)-[:DIRECTED]->(Movie)`
- `(Movie)-[:IN_GENRE]->(Genre)`
- `(User)-[:RATED {rating, timestamp}]->(Movie)`

M1 verifies the exact labels/properties via schema introspection and records them in `docs/graph-model.md` — tool implementations must use the *discovered* names, not assumptions.

**Reference seed model (for the AuraDB path)** — a hand-curated ~50-movie version of the same shape, created with idempotent `MERGE` statements plus uniqueness constraints, e.g.:
```cypher
MERGE (p:Person {name:"Christopher Nolan"}) SET p.born = 1970
MERGE (m:Movie {title:"Inception"}) SET m.released = 2010
MERGE (p)-[:DIRECTED]->(m)
```

---

## 7. Example Queries (progressive)

1. **Lookup:** `MATCH (m:Movie {title:'Inception'}) RETURN m`
2. **One-hop traversal:** `MATCH (m:Movie {title:'Inception'})<-[:ACTED_IN]-(p) RETURN p.name`
3. **Two-hop (co-actors):** `MATCH (p:Person {name:'Leonardo DiCaprio'})-[:ACTED_IN]->(:Movie)<-[:ACTED_IN]-(coActor) RETURN DISTINCT coActor.name`
4. **Shortest path:** `MATCH p = shortestPath((a:Person {name:'Kevin Bacon'})-[*..6]-(b:Person {name:'Keanu Reeves'})) RETURN length(p), p`
5. **Variable-length multi-hop:** `MATCH (a:Person {name:'Tom Hanks'})-[:ACTED_IN|DIRECTED*1..4]-(reachable) RETURN DISTINCT reachable LIMIT 50`
6. **Content-based recommendation:** `MATCH (m:Movie {title:'Inception'})-[:IN_GENRE]->(g)<-[:IN_GENRE]-(rec:Movie) WHERE rec<>m RETURN rec.title, count(g) AS shared ORDER BY shared DESC LIMIT 5`
7. **Collaborative-filtering recommendation:** `MATCH (u:User)-[:RATED]->(m:Movie {title:'Inception'}) MATCH (u)-[:RATED]->(rec) WHERE rec<>m RETURN rec.title, count(*) AS votes ORDER BY votes DESC LIMIT 5`
8. **Pattern matching:** `MATCH (a)-[:ACTED_IN]->(m:Movie)<-[:DIRECTED]-(a) RETURN a.name, m.title` (people who directed themselves)
9. **Aggregation:** `MATCH (p)-[:ACTED_IN]->(m:Movie) RETURN p.name, count(m) AS n ORDER BY n DESC LIMIT 10`
10. **Multi-hop aggregation:** `MATCH (d)-[:DIRECTED]->(m:Movie)<-[:ACTED_IN]-(p) RETURN d.name, count(DISTINCT p) AS uniqueActors ORDER BY uniqueActors DESC LIMIT 5`

(Exact label/relationship names to be confirmed against the live schema in M1.)

---

## 8. MCP Tool Surface

| Tool | Availability | Inputs | Output | Underlying Cypher |
|---|---|---|---|---|
| `get_schema` | always | none | labels, relationship types, property keys, counts | `db.schema.visualization()` / `db.labels()` |
| `search_nodes` | always | `label` (allowlisted), `property`, `value`, `limit` | matching node dicts | `MATCH (n:$label) WHERE n[$property] CONTAINS $value RETURN n LIMIT $limit` |
| `find_neighbors` | always | `name`, `rel_type` (optional), `direction`, `hops` (default 1) | neighbor nodes + relationships | `MATCH (n {name:$name})-[r*1..$hops]-(m) RETURN m, r` |
| `shortest_path` | always | `start_name`, `end_name`, `max_hops` (default 6) | path + length | `MATCH p=shortestPath((a{name:$start})-[*..$max_hops]-(b{name:$end})) RETURN p` |
| `recommend_similar` | always | `title`/`person_name`, `strategy` (`content`\|`collaborative`), `limit` | ranked recommendations | Queries 6/7 above, parameterized |
| `explain_graph` | always | optional `focus_node` | human-readable schema + stats summary | Combines `get_schema` with count aggregations |
| `add_entity` | **writeable backend only** (AuraDB) | `label`, `properties` | created/merged node | `MERGE (n:$label {name:$name}) SET n += $properties RETURN n` |
| `create_relationship` | **writeable backend only** (AuraDB) | `from_name`, `from_label`, `to_name`, `to_label`, `rel_type`, `properties` | created relationship | `MATCH (a),(b) … MERGE (a)-[r:$rel_type]->(b) SET r += $properties` |

**Write-tool gating:** at startup the server attempts a trivial write in a rolled-back transaction (or checks a `NEO4J_READONLY` env flag); on the demo server the write tools are either not registered or return a clear "read-only backend — see docs/auradb-upgrade.md" message. This is itself a good MCP lesson: advertising only tools that can actually succeed.

**Safety:** labels/relationship types/properties passed into tools must be validated against an allowlist derived from the live schema — never interpolated raw into Cypher. No raw-Cypher-execution tool in the core milestones; a constrained read-only Cypher tool is a reasonable stretch goal.

---

## 9. LLM Demo Scenarios

1. **"What's the shortest connection between Leonardo DiCaprio and Keanu Reeves?"** → `shortest_path(...)` → narrate the chain of movies/people.
2. **"Recommend me movies similar to Inception."** → `recommend_similar(title="Inception", strategy="content")` → explain via shared genres/directors.
3. **"I loved Inception and The Matrix — what should I watch next?"** → two `recommend_similar` calls, merged/ranked, cross-checked against `strategy="collaborative"` using the dataset's real user ratings.
4. **"Which director has worked with the widest range of actors?"** → `get_schema` first, then aggregation — demonstrates schema discovery before querying.
5. **"How exactly are Christopher Nolan and Kevin Bacon connected in this graph?"** → `shortest_path` then `find_neighbors` on intermediate nodes — demonstrates multi-tool composition.

Each is intentionally hard to answer without traversing relationships — the core "why graph" demonstration.

---

## 10. Stretch Goals (prioritized; most require the AuraDB upgrade first)

1. **AuraDB write unlock (M8)** — the gateway stretch goal; everything below that writes needs it.
2. **Agent memory in the graph** *(needs AuraDB)* — LLM autonomously uses `add_entity`/`create_relationship` to record and later recall facts from conversation.
3. **Hybrid vector + graph search** *(needs AuraDB)* — embeddings on `Movie.plot`, Neo4j native vector index, `semantic_search` tool combined with graph filters (GraphRAG pattern). Note: the `recommendations` demo dataset already ships plot embeddings, so a read-only variant is possible even before AuraDB.
4. **KG construction from documents** *(needs AuraDB)* — LLM extracts entities/relationships from raw text and populates the graph.
5. **Visualization** — neovis.js page rendering live query results (works read-only).
6. **Temporal graphs** *(needs AuraDB)* — valid-time properties on relationships with time-aware queries.
7. **Multi-agent workflows** — specialized agents with different MCP tool subsets over the shared graph. Most complex; do last.

---

## Verification Plan

- **M0:** Run the connectivity script; expect node/relationship counts printed from the live `recommendations` DB. Open Neo4j Browser/Workspace against the same URI and visually confirm the graph.
- **M1:** Schema introspection output matches `docs/graph-model.md`.
- **M2:** Run each Section 7 query in Browser and via the driver; confirm sensible results; `PROFILE` at least one traversal.
- **M3:** Same question answered in SQLite (JOINs) and Cypher side-by-side; compare readability/complexity.
- **M4–M5:** Exercise every tool via MCP Inspector (`npx @modelcontextprotocol/inspector`); `pytest` passes read-only integration tests against the demo server; confirm write tools are correctly gated off (clear error/absence, not a crash).
- **M6–M7:** Run all 5 demo scenarios in Claude Desktop and via the scripted Anthropic SDK client; capture transcripts into `docs/demo-transcripts.md`.
- **M8 (when triggered):** Follow `docs/auradb-upgrade.md` end-to-end; write tools register and succeed; write-tool tests pass against AuraDB.

---

## Final Recommendations Summary

| Item | Recommendation |
|---|---|
| Language | Python |
| Graph DB | Neo4j public demo server (`recommendations` DB) now; Neo4j AuraDB Free as the documented, on-demand upgrade |
| Query language | Cypher |
| MCP SDK | Official `mcp` Python SDK (FastMCP) |
| Visualization | Neo4j Browser/Workspace (core), neovis.js (stretch) |
| Containerization | None — deliberately avoided (Windows/Docker stability) |
| Local dev/deployment | `uv`-managed venv running the MCP server locally against the remote Neo4j |
| IDE | VS Code + Python/Cypher extensions |
| Key libraries | `neo4j`, `mcp` (FastMCP), `anthropic`, `pytest`, `ruff`, `python-dotenv` |

### Critical files to create during implementation
- `pyproject.toml` (uv project)
- `.env.example` (demo-server defaults + commented AuraDB placeholders)
- `src/graph/connection.py` (driver setup + writeability detection)
- `src/graph/schema_discovery.py` (M1)
- `src/graph/seed_data.py` (AuraDB-only seeding, used in M8)
- `src/mcp_server/server.py` (FastMCP tools, write tools gated)
- `src/llm/demo_client.py` (Anthropic SDK tool-use loop)
- `tests/test_mcp_tools.py` (read-only vs. write-gated test markers)
- `docs/graph-model.md`, `docs/auradb-upgrade.md`, `docs/comparisons.md`, `README.md`
