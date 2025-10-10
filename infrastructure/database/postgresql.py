"""
PostgreSQL database connection and operations.
"""

from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager
import asyncpg
from asyncpg.pool import Pool
from core.config.settings import settings
from core.logging.logger import get_logger

logger = get_logger(__name__)


class PostgreSQLDatabase:
    """PostgreSQL database manager with connection pooling"""

    def __init__(self) -> None:
        self._pool: Optional[Pool] = None

    async def connect(self) -> None:
        """Initialize database connection pool"""
        try:
            self._pool = await asyncpg.create_pool(
                host=settings.database.host,
                port=settings.database.port,
                database=settings.database.database,
                user=settings.database.user,
                password=settings.database.password,
                min_size=5,
                max_size=20,
                command_timeout=60,
            )
            logger.info(
                "postgres_connected",
                host=settings.database.host,
                database=settings.database.database,
            )
        except Exception as e:
            logger.error("postgres_connection_failed", error=str(e))
            raise

    async def disconnect(self) -> None:
        """Close database connection pool"""
        if self._pool:
            await self._pool.close()
            logger.info("postgres_disconnected")

    @asynccontextmanager
    async def acquire(self):
        """Acquire a connection from the pool"""
        if not self._pool:
            raise RuntimeError("Database not connected")

        async with self._pool.acquire() as connection:
            yield connection

    async def execute(
        self,
        query: str,
        *args: Any,
        timeout: float = 30.0,
    ) -> str:
        """Execute a query without returning results"""
        async with self.acquire() as conn:
            result = await conn.execute(query, *args, timeout=timeout)
            logger.debug("query_executed", query=query[:100], result=result)
            return result

    async def fetch_one(
        self,
        query: str,
        *args: Any,
        timeout: float = 30.0,
    ) -> Optional[Dict[str, Any]]:
        """Fetch a single row"""
        async with self.acquire() as conn:
            row = await conn.fetchrow(query, *args, timeout=timeout)
            return dict(row) if row else None

    async def fetch_all(
        self,
        query: str,
        *args: Any,
        timeout: float = 30.0,
    ) -> List[Dict[str, Any]]:
        """Fetch all rows"""
        async with self.acquire() as conn:
            rows = await conn.fetch(query, *args, timeout=timeout)
            return [dict(row) for row in rows]

    async def insert_trade(
        self,
        exchange: str,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: float,
        **kwargs: Any,
    ) -> str:
        """Insert a new trade record"""
        query = """
            INSERT INTO trades (
                exchange, symbol, side, order_type, quantity, price,
                fee, fee_currency, status, order_id, execution_time, metadata
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12)
            RETURNING id
        """
        result = await self.fetch_one(
            query,
            exchange,
            symbol,
            side,
            order_type,
            quantity,
            price,
            kwargs.get("fee"),
            kwargs.get("fee_currency"),
            kwargs.get("status", "PENDING"),
            kwargs.get("order_id"),
            kwargs.get("execution_time"),
            kwargs.get("metadata", {}),
        )
        return str(result["id"]) if result else None

    async def insert_signal(
        self,
        agent_type: str,
        agent_name: str,
        symbol: str,
        signal_type: str,
        confidence: float,
        **kwargs: Any,
    ) -> str:
        """Insert a new trading signal"""
        import json

        query = """
            INSERT INTO signals (
                agent_type, agent_name, symbol, signal_type, confidence,
                price_target, stop_loss, take_profit, reasoning, indicators, metadata
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11)
            RETURNING id
        """
        result = await self.fetch_one(
            query,
            agent_type,
            agent_name,
            symbol,
            signal_type,
            confidence,
            kwargs.get("price_target"),
            kwargs.get("stop_loss"),
            kwargs.get("take_profit"),
            kwargs.get("reasoning"),
            json.dumps(kwargs.get("indicators", {})),
            json.dumps(kwargs.get("metadata", {})),
        )
        return str(result["id"]) if result else None

    async def get_active_positions(self) -> List[Dict[str, Any]]:
        """Get all active positions"""
        query = "SELECT * FROM active_positions"
        return await self.fetch_all(query)

    async def get_portfolio_snapshot(self) -> Optional[Dict[str, Any]]:
        """Get latest portfolio snapshot"""
        query = """
            SELECT * FROM portfolio_snapshots
            ORDER BY snapshot_time DESC
            LIMIT 1
        """
        return await self.fetch_one(query)

    async def get_recent_signals(
        self,
        symbol: Optional[str] = None,
        hours: int = 24,
    ) -> List[Dict[str, Any]]:
        """Get recent trading signals"""
        if symbol:
            query = """
                SELECT * FROM recent_signals
                WHERE symbol = $1
                ORDER BY created_at DESC
            """
            return await self.fetch_all(query, symbol)
        else:
            query = """
                SELECT * FROM recent_signals
                ORDER BY created_at DESC
                LIMIT 100
            """
            return await self.fetch_all(query)


# Global database instance
db = PostgreSQLDatabase()


async def get_db() -> PostgreSQLDatabase:
    """Get database instance"""
    if not db._pool:
        await db.connect()
    return db
