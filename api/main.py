"""
FastAPI Backend for Trading Dashboard
Provides real-time system status, trades, and metrics
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
import numpy as np
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
    allow_origins=[
        "http://localhost:3000",
        "http://localhost:3001",
        "http://192.168.1.150:3000",
        "http://192.168.1.150:3001"
    ],
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
    position_id: str
    symbol: str
    side: str
    size: float
    entryPrice: float
    currentPrice: float
    unrealizedPnl: float
    unrealizedPnlPercent: float
    marketType: str  # 'spot' or 'futures'
    # StonkJournal enhancements
    stopLoss: Optional[float] = None
    takeProfit: Optional[float] = None
    strategyTag: Optional[str] = None  # 'swing' | 'scalp' | 'position'
    openedAt: str = ""
    holdDuration: Optional[str] = None
    reasoning: Optional[str] = None
    executionQuality: Optional[float] = None


class DashboardMetrics(BaseModel):
    totalEquity: float
    totalPnl: float
    totalPnlPercent: float
    winRate: float
    totalTrades: int
    winningTrades: int
    losingTrades: int
    openPositions: int
    sharpeRatio: Optional[float] = None
    maxDrawdown: Optional[float] = None
    profitFactor: Optional[float] = None
    averageWin: Optional[float] = None
    averageLoss: Optional[float] = None


class EquityDataPoint(BaseModel):
    timestamp: str
    equity: float
    drawdown: float
    displayTime: str


class StrategyStats(BaseModel):
    strategy: str
    totalTrades: int
    winRate: float
    totalPnl: float
    avgWin: float
    avgLoss: float
    sharpeRatio: float
    maxDrawdown: float
    profitFactor: float


class BenchmarkDataPoint(BaseModel):
    timestamp: str
    portfolioReturn: float
    btcReturn: float
    ethReturn: float
    displayTime: str


class BenchmarkMetrics(BaseModel):
    data: List[BenchmarkDataPoint]
    portfolioAlpha: float
    portfolioBeta: float
    correlation: Dict[str, float]


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

        # Look for agent process with module format
        # -m agents.data_collection.agent
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
            [
                "docker", "exec", "trading_rabbitmq",
                "rabbitmqctl", "list_connections"
            ],
            capture_output=True,
            text=True
        )

        # Count connections (subtract header line)
        lines = [line for line in result.stdout.split('\n') if line.strip()]
        connections = len(lines) - 1

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
        with get_db_connection():
            db_healthy = True
    except Exception:
        pass

    rabbitmq_stats = await get_rabbitmq_stats()

    return {
        "status": "healthy" if db_healthy else "degraded",
        "database": "connected" if db_healthy else "disconnected",
        "rabbitmq": (
            "connected" if rabbitmq_stats.get("healthy")
            else "disconnected"
        ),
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
                    entry = float(pos['entryPrice'])
                    current = float(pos['markPrice'])
                    pnl_pct = ((current - entry) / entry * 100)

                    positions.append(ActivePosition(
                        position_id=str(pos.get('id', pos['symbol'])),
                        symbol=pos['symbol'],
                        side=pos['side'],
                        size=float(pos['contracts']),
                        entryPrice=entry,
                        currentPrice=current,
                        unrealizedPnl=float(pos['unrealizedPnl']),
                        unrealizedPnlPercent=pnl_pct,
                        marketType='futures',
                        openedAt=pos.get('timestamp', ''),
                    ))
        else:
            # For spot, get positions from database
            with get_db_connection() as conn:
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute(
                        """SELECT EXISTS (
                            SELECT FROM information_schema.tables
                            WHERE table_name = 'positions'
                        )"""
                    )
                    if cur.fetchone()['exists']:
                        cur.execute(
                            """
                            SELECT
                                id::text as position_id,
                                symbol,
                                side,
                                quantity as size,
                                entry_price,
                                current_price,
                                unrealized_pnl,
                                stop_loss,
                                take_profit,
                                strategy_tag,
                                opened_at,
                                reasoning,
                                execution_quality
                            FROM positions
                            WHERE quantity > 0
                            """
                        )

                        for row in cur.fetchall():
                            entry = float(row['entry_price'])
                            current = float(row['current_price'])
                            pnl_pct = ((current - entry) / entry * 100)

                            # Calculate hold duration
                            hold_dur = None
                            if row.get('opened_at'):
                                delta = (
                                    datetime.now(ZoneInfo("Europe/Istanbul")) -
                                    row['opened_at']
                                )
                                days = delta.days
                                hours = delta.seconds // 3600
                                if days > 0:
                                    hold_dur = f"{days}d {hours}h"
                                else:
                                    hold_dur = f"{hours}h"

                            positions.append(ActivePosition(
                                position_id=row['position_id'],
                                symbol=row['symbol'],
                                side=row['side'],
                                size=float(row['size']),
                                entryPrice=entry,
                                currentPrice=current,
                                unrealizedPnl=float(row['unrealized_pnl']),
                                unrealizedPnlPercent=pnl_pct,
                                marketType='spot',
                                stopLoss=row.get('stop_loss'),
                                takeProfit=row.get('take_profit'),
                                strategyTag=row.get('strategy_tag'),
                                openedAt=(
                                    row['opened_at'].isoformat()
                                    if row.get('opened_at') else ""
                                ),
                                holdDuration=hold_dur,
                                reasoning=row.get('reasoning'),
                                executionQuality=row.get('execution_quality')
                            ))

        return positions

    except Exception as e:
        print(f"Error fetching positions: {e}")
        return []


@app.get("/api/dashboard/metrics", response_model=DashboardMetrics)
async def get_dashboard_metrics(period: str = 'today'):
    """Get comprehensive dashboard metrics"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Check tables exist
                cur.execute(
                    """SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = 'trades'
                    )"""
                )
                if not cur.fetchone()['exists']:
                    return DashboardMetrics(
                        totalEquity=10000.0,
                        totalPnl=0,
                        totalPnlPercent=0,
                        winRate=0,
                        totalTrades=0,
                        winningTrades=0,
                        losingTrades=0,
                        openPositions=0
                    )

                # Calculate time filter
                now = datetime.now(ZoneInfo("Europe/Istanbul"))
                if period == 'today':
                    start_time = now.replace(
                        hour=0, minute=0, second=0, microsecond=0
                    )
                elif period == 'week':
                    start_time = now - timedelta(days=7)
                elif period == 'month':
                    start_time = now - timedelta(days=30)
                else:  # all
                    start_time = datetime(2020, 1, 1, tzinfo=ZoneInfo(
                        "Europe/Istanbul"
                    ))

                # Get trades stats
                cur.execute(
                    """
                    SELECT
                        COUNT(*) as total_trades,
                        SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END) as wins,
                        SUM(CASE WHEN pnl < 0 THEN 1 ELSE 0 END) as losses,
                        SUM(pnl) as total_pnl,
                        AVG(CASE WHEN pnl > 0 THEN pnl END) as avg_win,
                        AVG(CASE WHEN pnl < 0 THEN pnl END) as avg_loss
                    FROM trades
                    WHERE created_at >= %s AND status = 'FILLED'
                    """,
                    (start_time,)
                )

                stats = cur.fetchone()
                total_trades = stats['total_trades'] or 0
                wins = stats['wins'] or 0
                losses = stats['losses'] or 0
                total_pnl = float(stats['total_pnl'] or 0)
                avg_win = float(stats['avg_win'] or 0)
                avg_loss = float(stats['avg_loss'] or 0)

                # Get open positions count
                cur.execute(
                    """SELECT COUNT(*) FROM positions
                       WHERE quantity > 0"""
                )
                open_positions = cur.fetchone()[0] or 0

                # Calculate metrics
                win_rate = (wins / total_trades * 100) if total_trades else 0
                total_equity = 10000.0 + total_pnl
                pnl_percent = (total_pnl / 10000.0 * 100)

                profit_factor = None
                if avg_loss != 0:
                    profit_factor = abs(avg_win / avg_loss)

                return DashboardMetrics(
                    totalEquity=total_equity,
                    totalPnl=total_pnl,
                    totalPnlPercent=pnl_percent,
                    winRate=win_rate,
                    totalTrades=total_trades,
                    winningTrades=wins,
                    losingTrades=losses,
                    openPositions=open_positions,
                    profitFactor=profit_factor,
                    averageWin=avg_win,
                    averageLoss=avg_loss
                )

    except Exception as e:
        print(f"Error fetching dashboard metrics: {e}")
        return DashboardMetrics(
            totalEquity=10000.0,
            totalPnl=0,
            totalPnlPercent=0,
            winRate=0,
            totalTrades=0,
            winningTrades=0,
            losingTrades=0,
            openPositions=0
        )


@app.get("/api/dashboard/equity-curve")
async def get_equity_curve(period: str = 'today'):
    """Get equity curve data"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = 'trades'
                    )"""
                )
                if not cur.fetchone()['exists']:
                    return []

                # Calculate time filter
                now = datetime.now(ZoneInfo("Europe/Istanbul"))
                if period == 'today':
                    start_time = now.replace(
                        hour=0, minute=0, second=0, microsecond=0
                    )
                elif period == 'week':
                    start_time = now - timedelta(days=7)
                elif period == 'month':
                    start_time = now - timedelta(days=30)
                else:
                    start_time = datetime(2020, 1, 1, tzinfo=ZoneInfo(
                        "Europe/Istanbul"
                    ))

                cur.execute(
                    """
                    SELECT
                        created_at as timestamp,
                        SUM(pnl) OVER (
                            ORDER BY created_at
                        ) as cumulative_pnl
                    FROM trades
                    WHERE created_at >= %s AND status = 'FILLED'
                    ORDER BY created_at
                    """,
                    (start_time,)
                )

                equity_data = []
                max_equity = 10000.0

                for row in cur.fetchall():
                    equity = 10000.0 + float(row['cumulative_pnl'])
                    max_equity = max(max_equity, equity)
                    drawdown = ((max_equity - equity) / max_equity * 100)

                    equity_data.append({
                        "timestamp": row['timestamp'].isoformat(),
                        "equity": equity,
                        "drawdown": drawdown,
                        "displayTime": row['timestamp'].strftime("%H:%M")
                    })

                return equity_data

    except Exception as e:
        print(f"Error fetching equity curve: {e}")
        return []


@app.get("/api/dashboard/strategy-comparison")
async def get_strategy_comparison(period: str = 'all'):
    """Get strategy comparison stats"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                cur.execute(
                    """SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = 'trades'
                    )"""
                )
                if not cur.fetchone()['exists']:
                    return []

                cur.execute(
                    """
                    SELECT
                        strategy_tag as strategy,
                        COUNT(*) as total_trades,
                        SUM(CASE WHEN pnl > 0 THEN 1 ELSE 0 END)::float /
                            COUNT(*)::float * 100 as win_rate,
                        SUM(pnl) as total_pnl,
                        AVG(CASE WHEN pnl > 0 THEN pnl END) as avg_win,
                        AVG(CASE WHEN pnl < 0 THEN pnl END) as avg_loss
                    FROM trades
                    WHERE strategy_tag IS NOT NULL AND status = 'FILLED'
                    GROUP BY strategy_tag
                    """
                )

                strategies = []
                for row in cur.fetchall():
                    avg_win = float(row['avg_win'] or 0)
                    avg_loss = float(row['avg_loss'] or 0)
                    profit_factor = (
                        abs(avg_win / avg_loss) if avg_loss != 0 else 1.0
                    )

                    strategies.append({
                        "strategy": row['strategy'],
                        "totalTrades": row['total_trades'],
                        "winRate": float(row['win_rate'] or 0),
                        "totalPnl": float(row['total_pnl'] or 0),
                        "avgWin": avg_win,
                        "avgLoss": avg_loss,
                        "sharpeRatio": 1.5,  # TODO: Calculate from returns
                        "maxDrawdown": 5.0,  # TODO: Calculate actual
                        "profitFactor": profit_factor
                    })

                return strategies

    except Exception as e:
        print(f"Error fetching strategy comparison: {e}")
        return []


@app.get("/api/dashboard/benchmark-comparison")
async def get_benchmark_comparison(period: str = 'week'):
    """Get benchmark comparison data"""
    # TODO: Implement with InfluxDB historical price data
    # For now, return mock data structure
    return {
        "data": [],
        "portfolioAlpha": 0.0,
        "portfolioBeta": 1.0,
        "correlation": {"btc": 0.0, "eth": 0.0}
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
