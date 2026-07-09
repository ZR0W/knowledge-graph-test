"""Neo4j connection management.

Learning notes (M0):

- Neo4j speaks the *Bolt* binary protocol. The ``neo4j+s://`` URI scheme means
  "Bolt over TLS, with routing" — the same scheme works for the public demo
  server, AuraDB, and any self-hosted cluster, so switching backends is purely
  a configuration change (see ``.env.example``).
- A ``Driver`` is a thread-safe, long-lived connection pool. You create ONE per
  application and open cheap short-lived *sessions* off it per unit of work.
- Sessions target a specific *database* (one server can host many).
"""

from __future__ import annotations

import os
from functools import lru_cache

from dotenv import load_dotenv
from neo4j import Driver, GraphDatabase

load_dotenv()

DEFAULT_URI = "neo4j+s://demo.neo4jlabs.com"
DEFAULT_DATABASE = "recommendations"


class GraphConnection:
    """Small wrapper owning the driver plus the resolved database name."""

    def __init__(self, uri: str, username: str, password: str, database: str) -> None:
        self.uri = uri
        self.database = database
        self._driver: Driver = GraphDatabase.driver(uri, auth=(username, password))

    @classmethod
    def from_env(cls) -> GraphConnection:
        return cls(
            uri=os.getenv("NEO4J_URI", DEFAULT_URI),
            username=os.getenv("NEO4J_USERNAME", DEFAULT_DATABASE),
            password=os.getenv("NEO4J_PASSWORD", DEFAULT_DATABASE),
            database=os.getenv("NEO4J_DATABASE", DEFAULT_DATABASE),
        )

    def verify(self) -> None:
        """Fail fast (with a clear error) if the server is unreachable."""
        self._driver.verify_connectivity()

    def run(self, query: str, **params) -> list[dict]:
        """Run a single Cypher query and return records as plain dicts.

        ``execute_query`` handles session lifecycle and retries for us —
        ideal for the simple one-shot queries this project uses.
        """
        records, _, _ = self._driver.execute_query(query, params, database_=self.database)
        return [record.data() for record in records]

    def is_writeable(self) -> bool:
        """Detect whether the backend accepts writes.

        Honors an explicit ``NEO4J_READONLY`` env override; otherwise probes by
        creating a throwaway node inside a transaction that is always rolled
        back, so a writeable database is never actually modified.

        Later milestones use this to decide whether write-oriented MCP tools
        (``add_entity``, ``create_relationship``) should be exposed at all.
        """
        override = os.getenv("NEO4J_READONLY")
        if override is not None:
            return override.strip().lower() not in ("true", "1", "yes")

        try:
            with self._driver.session(database=self.database) as session:
                tx = session.begin_transaction()
                try:
                    tx.run("CREATE (probe:__WriteProbe__) RETURN probe")
                finally:
                    tx.rollback()
            return True
        except Exception:
            return False

    def close(self) -> None:
        self._driver.close()

    def __enter__(self) -> GraphConnection:
        return self

    def __exit__(self, *exc) -> None:
        self.close()


@lru_cache(maxsize=1)
def get_connection() -> GraphConnection:
    """Shared process-wide connection, configured from the environment."""
    return GraphConnection.from_env()
