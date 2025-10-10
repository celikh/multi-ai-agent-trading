"""
FastAPI Backend for Trading Dashboard
Provides real-time system status, trades, and metrics
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
from zoneinfo import ZoneInfo
import os
from dotenv import load_dotenv
import psutil
import subprocess
import psycopg2
from psycopg2.extras import RealDictCursor
from contextlib import contextmanager
import ccxt

load_dotenv()

app = FastAPI(title="Trading System API", version="1.0.0")

# CORS configuration for Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://192.168.1.150:3000", "http://192.168.1.150:3001"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection configuration
DB_CONFIG = {
    'host': os.getenv("POSTGRES_HOST", "localhost"),
    'port': int(os.getenv("POSTGRES_PORT", "5434")),
    'database': os.getenv("POSTGRES_DB", "trading_system"),
    'user': os.getenv("POSTGRES_USER", "trading"),
    'password': os.getenv("POSTGRES_PASSWORD", "trading123")
}

# Binance exchange initialization
exchange = ccxt.binance({
    'apiKey': os.getenv('BINANCE_API_KEY'),
    'secret': os.getenv('BINANCE_SECRET_KEY'),
    'enableRateLimit': True,
    'options': {
        'defaultType': 'spot',  # 'spot' or 'future'
    }
})


# Response Models
class AgentStatus(BaseModel):
    name: str
    status: str  # 'running' | 'stopped' | 'error'
    uptime: int  # seconds
    lastUpdate: str  # ISO timestamp


class Trade(BaseModel):
    id: str
    symbol: str
    side: str
    quantity: float
    price: float
    timestamp: str
    status: str
    pnl: Optional[float] = None


class SystemMetrics(BaseModel):
    cpu: float
    memory: float
    activeConnections: int
    totalTrades: int
    totalSignals: int


class BalanceInfo(BaseModel):
    asset: str
    free: float
    locked: float
    total: float
    usdValue: float


class AccountBalance(BaseModel):
    totalBalanceUSD: float
    balances: List[BalanceInfo]
    accountType: str  # 'spot' or 'futures'


class ActivePosition(BaseModel):
    symbol: str
    side: str
    size: float
    entryPrice: float
    currentPrice: float
    unrealizedPnl: float
    marketType: str  # 'spot' or 'futures'


@contextmanager
def get_db_connection():
    """Context manager for database connections"""
    conn = None
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        yield conn
        conn.commit()
    except Exception as e:
        if conn:
            conn.rollback()
        raise e
    finally:
        if conn:
            conn.close()


# Helper functions
async def get_agent_process_status(agent_name: str) -> Dict[str, Any]:
    """Check if agent process is running via ps command"""
    try:
        result = subprocess.run(
            ["ps", "aux"],
            capture_output=True,
            text=True
        )

        # Look for agent process with module format: -m agents.data_collection.agent
        agent_module = f"agents.{agent_name.lower().replace(' ', '_')}.agent"
        for line in result.stdout.split('\n'):
            if agent_module in line and 'python' in line:
                # Process is running - extract uptime info
                parts = line.split()
                return {
                    "running": True,
                    "pid": parts[1],
                    "cpu": float(parts[2]),
                    "mem": float(parts[3])
                }

        return {"running": False}
    except Exception as e:
        print(f"Error checking agent {agent_name}: {e}")
        return {"running": False, "error": str(e)}


async def get_rabbitmq_stats() -> Dict[str, Any]:
    """Get RabbitMQ statistics via rabbitmqctl"""
    try:
        result = subprocess.run(
            ["docker", "exec", "trading_rabbitmq", "rabbitmqctl", "list_connections"],
            capture_output=True,
            text=True
        )

        # Count connections (subtract header line)
        connections = len([l for l in result.stdout.split('\n') if l.strip()]) - 1

        return {
            "connections": max(0, connections),
            "healthy": connections > 0
        }
    except Exception as e:
        print(f"Error getting RabbitMQ stats: {e}")
        return {"connections": 0, "healthy": False}


# API Endpoints
@app.get("/")
async def root():
    return {
        "service": "Trading System API",
        "status": "running",
        "version": "1.0.0"
    }


@app.get("/api/agents/status", response_model=List[AgentStatus])
async def get_agents_status():
    """Get status of all trading agents"""
    agent_names = [
        "Data Collection",
        "Technical Analysis",
        "Strategy",
        "Risk Manager",
        "Execution"
    ]

    statuses = []

    for agent_name in agent_names:
        process_info = await get_agent_process_status(agent_name)

        status = AgentStatus(
            name=agent_name,
            status="running" if process_info.get("running") else "stopped",
            uptime=3600,  # TODO: Calculate actual uptime from process start time
            lastUpdate=datetime.now(ZoneInfo("Europe/Istanbul")).isoformat()
        )
        statuses.append(status)

    return statuses


@app.get("/api/trades", response_model=List[Trade])
def get_trades(limit: int = 50):
    """Get recent trades from database"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Check if trades table exists
                cur.execute(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'trades')"
                )
                table_exists = cur.fetchone()['exists']

                if not table_exists:
                    return []

                cur.execute(
                    """
                    SELECT
                        id::text,
                        symbol,
                        side,
                        quantity,
                        price,
                        created_at as timestamp,
                        status
                    FROM trades
                    ORDER BY created_at DESC
                    LIMIT %s
                    """,
                    (limit,)
                )

                trades = []
                for row in cur.fetchall():
                    trade = Trade(
                        id=row['id'],
                        symbol=row['symbol'],
                        side=row['side'],
                        quantity=float(row['quantity']),
                        price=float(row['price']),
                        timestamp=row['timestamp'].isoformat(),
                        status=row['status'],
                        pnl=None  # PnL calculated separately
                    )
                    trades.append(trade)

                return trades

    except Exception as e:
        print(f"Error fetching trades: {e}")
        return []


@app.get("/api/signals")
def get_signals(limit: int = 50):
    """Get recent trading signals from database"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Check if signals table exists
                cur.execute(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'signals')"
                )
                table_exists = cur.fetchone()['exists']

                if not table_exists:
                    return []

                cur.execute(
                    """
                    SELECT
                        id::text,
                        symbol,
                        signal_type,
                        strength,
                        timestamp,
                        metadata
                    FROM signals
                    ORDER BY timestamp DESC
                    LIMIT %s
                    """,
                    (limit,)
                )

                return [dict(row) for row in cur.fetchall()]

    except Exception as e:
        print(f"Error fetching signals: {e}")
        return []


@app.get("/api/metrics", response_model=SystemMetrics)
async def get_system_metrics():
    """Get system metrics (CPU, memory, connections, trades count)"""

    # Get system CPU and memory
    cpu_percent = psutil.cpu_percent(interval=1)
    memory_percent = psutil.virtual_memory().percent

    # Get RabbitMQ connections
    rabbitmq_stats = await get_rabbitmq_stats()
    active_connections = rabbitmq_stats.get("connections", 0)

    # Get total trades count from database
    total_trades = 0
    total_signals = 0

    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Count trades
                cur.execute(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'trades')"
                )
                if cur.fetchone()[0]:
                    cur.execute("SELECT COUNT(*) FROM trades")
                    total_trades = cur.fetchone()[0]

                # Count signals
                cur.execute(
                    "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'signals')"
                )
                if cur.fetchone()[0]:
                    cur.execute("SELECT COUNT(*) FROM signals")
                    total_signals = cur.fetchone()[0]

    except Exception as e:
        print(f"Error fetching metrics: {e}")

    return SystemMetrics(
        cpu=cpu_percent,
        memory=memory_percent,
        activeConnections=active_connections,
        totalTrades=total_trades or 0,
        totalSignals=total_signals or 0
    )


@app.get("/api/health")
async def health_check():
    """Health check endpoint"""
    db_healthy = False
    try:
        with get_db_connection() as conn:
            db_healthy = True
    except:
        pass

    rabbitmq_stats = await get_rabbitmq_stats()

    return {
        "status": "healthy" if db_healthy else "degraded",
        "database": "connected" if db_healthy else "disconnected",
        "rabbitmq": "connected" if rabbitmq_stats.get("healthy") else "disconnected",
        "timestamp": datetime.now(ZoneInfo("Europe/Istanbul")).isoformat()
    }


@app.get("/api/balance", response_model=AccountBalance)
async def get_balance():
    """Get Binance account balance"""
    try:
        # Fetch balance from Binance
        balance_data = exchange.fetch_balance()

        # Get current prices for USD value calculation
        tickers = exchange.fetch_tickers()

        balances = []
        total_usd = 0.0

        for asset, amounts in balance_data['total'].items():
            if amounts > 0:  # Only show assets with balance
                free = balance_data['free'].get(asset, 0)
                locked = balance_data['used'].get(asset, 0)
                total = amounts

                # Calculate USD value
                usd_value = 0.0
                if asset == 'USDT' or asset == 'USD':
                    usd_value = total
                else:
                    # Try to get price from USDT pair
                    symbol = f"{asset}/USDT"
                    if symbol in tickers:
                        usd_value = total * tickers[symbol]['last']

                total_usd += usd_value

                balances.append(BalanceInfo(
                    asset=asset,
                    free=float(free),
                    locked=float(locked),
                    total=float(total),
                    usdValue=float(usd_value)
                ))

        # Sort by USD value descending
        balances.sort(key=lambda x: x.usdValue, reverse=True)

        return AccountBalance(
            totalBalanceUSD=float(total_usd),
            balances=balances,
            accountType=exchange.options.get('defaultType', 'spot')
        )

    except Exception as e:
        print(f"Error fetching balance: {e}")
        return AccountBalance(
            totalBalanceUSD=0.0,
            balances=[],
            accountType='spot'
        )


@app.get("/api/positions", response_model=List[ActivePosition])
async def get_positions():
    """Get active trading positions"""
    positions = []

    try:
        # Check if using futures
        if exchange.options.get('defaultType') == 'future':
            # Fetch futures positions
            positions_data = exchange.fetch_positions()

            for pos in positions_data:
                if float(pos.get('contracts', 0)) > 0:
                    positions.append(ActivePosition(
                        symbol=pos['symbol'],
                        side=pos['side'],
                        size=float(pos['contracts']),
                        entryPrice=float(pos['entryPrice']),
                        currentPrice=float(pos['markPrice']),
                        unrealizedPnl=float(pos['unrealizedPnl']),
                        marketType='futures'
                    ))
        else:
            # For spot, get positions from database
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        "SELECT EXISTS (SELECT FROM information_schema.tables WHERE table_name = 'positions')"
                    )
                    if cur.fetchone()['exists']:
                        cur.execute(
                            """
                            SELECT
                                symbol,
                                side,
                                quantity as size,
                                entry_price,
                                current_price,
                                unrealized_pnl
                            FROM positions
                            WHERE quantity > 0
                            """
                        )

                        for row in cur.fetchall():
                            positions.append(ActivePosition(
                                symbol=row['symbol'],
                                side=row['side'],
                                size=float(row['size']),
                                entryPrice=float(row['entry_price']),
                                currentPrice=float(row['current_price']),
                                unrealizedPnl=float(row['unrealized_pnl']),
                                marketType='spot'
                            ))

        return positions

    except Exception as e:
        print(f"Error fetching positions: {e}")
        return []


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
