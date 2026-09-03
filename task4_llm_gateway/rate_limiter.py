import sqlite3
import threading
import time
from pathlib import Path


TOKEN_LIMIT_PER_MINUTE = 50_000
WINDOW_SECONDS = 60


class TokenRateLimiter:
    """
    Persistent sliding-window token rate limiter.

    Each tenant API key may consume up to 50,000 tokens
    during the preceding 60 seconds.
    """

    def __init__(
        self,
        db_path: str = "rate_limits.db",
        limit: int = TOKEN_LIMIT_PER_MINUTE,
        window_seconds: int = WINDOW_SECONDS,
    ):
        self.db_path = Path(db_path)
        self.limit = limit
        self.window_seconds = window_seconds
        self._lock = threading.Lock()

        self._initialize_database()

    def _connect(self):
        connection = sqlite3.connect(
            self.db_path,
            timeout=5,
        )

        connection.execute(
            "PRAGMA journal_mode=WAL"
        )

        return connection

    def _initialize_database(self):
        with self._connect() as connection:
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS token_usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tenant_key TEXT NOT NULL,
                    tokens INTEGER NOT NULL,
                    timestamp REAL NOT NULL
                )
                """
            )

            connection.execute(
                """
                CREATE INDEX IF NOT EXISTS
                idx_token_usage_tenant_timestamp
                ON token_usage (
                    tenant_key,
                    timestamp
                )
                """
            )

    def _cleanup_old_entries(
        self,
        connection,
        now: float,
    ):
        cutoff = now - self.window_seconds

        connection.execute(
            """
            DELETE FROM token_usage
            WHERE timestamp < ?
            """,
            (cutoff,),
        )

    def get_usage(
        self,
        tenant_key: str,
        now: float | None = None,
    ) -> int:
        now = now if now is not None else time.time()
        cutoff = now - self.window_seconds

        with self._connect() as connection:
            row = connection.execute(
                """
                SELECT COALESCE(SUM(tokens), 0)
                FROM token_usage
                WHERE tenant_key = ?
                  AND timestamp >= ?
                """,
                (
                    tenant_key,
                    cutoff,
                ),
            ).fetchone()

        return int(row[0])

    def consume(
        self,
        tenant_key: str,
        tokens: int,
        now: float | None = None,
    ) -> tuple[bool, int]:
        if not tenant_key:
            raise ValueError(
                "tenant_key is required"
            )

        if tokens <= 0:
            raise ValueError(
                "tokens must be greater than zero"
            )

        now = now if now is not None else time.time()
        cutoff = now - self.window_seconds

        with self._lock:
            with self._connect() as connection:
                connection.execute("BEGIN IMMEDIATE")

                self._cleanup_old_entries(
                    connection,
                    now,
                )

                row = connection.execute(
                    """
                    SELECT COALESCE(SUM(tokens), 0)
                    FROM token_usage
                    WHERE tenant_key = ?
                      AND timestamp >= ?
                    """,
                    (
                        tenant_key,
                        cutoff,
                    ),
                ).fetchone()

                current_usage = int(row[0])
                new_usage = current_usage + tokens

                if new_usage > self.limit:
                    connection.rollback()

                    remaining = max(
                        self.limit - current_usage,
                        0,
                    )

                    return False, remaining

                connection.execute(
                    """
                    INSERT INTO token_usage (
                        tenant_key,
                        tokens,
                        timestamp
                    )
                    VALUES (?, ?, ?)
                    """,
                    (
                        tenant_key,
                        tokens,
                        now,
                    ),
                )

                connection.commit()

                remaining = self.limit - new_usage

                return True, remaining