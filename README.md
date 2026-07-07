# knowledge-graph-test

A hands-on learning project for exploring **graph databases** by building a movie knowledge graph, exposing it through an **MCP (Model Context Protocol) server**, and connecting an **LLM** so it can query and reason over the graph.

> **Status: planning complete — implementation not yet started.**
> The full approved plan lives in [`PROJECT_PLAN.md`](./PROJECT_PLAN.md). Implementation proceeds milestone-by-milestone (M0–M8) as described there.

## The Short Version

| | |
|---|---|
| **Goal** | Learn graph DB fundamentals (modeling, Cypher, traversal), compare graphs vs. relational vs. vector DBs, then build an MCP server + LLM integration on top |
| **Language** | Python (`uv` + `ruff`) |
| **Database** | Neo4j **public read-only demo server** — `neo4j+s://demo.neo4jlabs.com`, database `recommendations` (username & password are both `recommendations`). Zero install, zero Docker, pre-filled movie graph |
| **Write path** | Neo4j **AuraDB Free** upgrade, documented in `docs/auradb-upgrade.md` (created during implementation) — flips `.env` config to unlock `add_entity` / `create_relationship` / agent-memory features |
| **Query language** | Cypher |
| **MCP** | Official `mcp` Python SDK (FastMCP), stdio transport |
| **LLM** | Claude Desktop (interactive) + scripted Anthropic SDK client (explicit tool-use loop) |
| **Testing** | `pytest` read-only integration tests against the live demo server |

## Key Constraint

**No Docker, no local database install.** Everything runs against remote Neo4j instances (public demo server now, free AuraDB later), keeping the setup Windows-friendly and trivial to reproduce.

## Milestones at a Glance

- **M0** — Environment setup + connect to the demo server (1–2 hrs)
- **M1** — Schema discovery & graph modeling from live data (½ day)
- **M2** — Cypher querying & traversal deep dive (½ day)
- **M3** — Comparative analysis: same questions in SQLite JOINs + naive vector similarity (½–1 day)
- **M4** — MCP server skeleton (`get_schema`, `search_nodes`) (½ day)
- **M5** — Full MCP tool surface + tests; write tools built but gated (1 day)
- **M6** — LLM integration: Claude Desktop + scripted tool-use loop (½ day)
- **M7** — Capstone demo scenarios with captured transcripts (½ day)
- **M8** — On-demand AuraDB Free upgrade to unlock writes (½ day)
- **M9+** — Stretch goals: agent memory, hybrid vector+graph search, KG construction, visualization, temporal graphs, multi-agent

See [`PROJECT_PLAN.md`](./PROJECT_PLAN.md) for the full roadmap, architecture diagram, sample graph model, example queries, MCP tool definitions, and demo scenarios.
