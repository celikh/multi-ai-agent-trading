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


# Trade Journal Models
class TradeJournalCreate(BaseModel):
    position_id: Optional[str] = None
    symbol: str
    side: str
    strategy_tag: str
    entry_price: float
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    setup_type: str
    timeframe: str
    reasoning: str
    technical_indicators: Optional[List[str]] = None
    market_condition: Optional[str] = None
    confidence_level: int
    chart_screenshot: Optional[str] = None


class TradeJournalUpdate(BaseModel):
    setup_type: Optional[str] = None
    reasoning: Optional[str] = None
    confidence_level: Optional[int] = None
    execution_quality: Optional[int] = None
    slippage: Optional[float] = None
    entry_timing: Optional[str] = None
    status: Optional[str] = None


class TradeReview(BaseModel):
    exit_reason: str
    execution_quality: int
    entry_timing: str
    emotional_state: List[str]
    rule_following: int
    what_went_well: str
    what_went_wrong: str
    lessons_learned: str
    tags: List[str]


class TradeJournal(BaseModel):
    id: str
    position_id: Optional[str]
    symbol: str
    side: str
    strategy_tag: str
    entry_price: float
    current_price: Optional[float] = None
    unrealized_pnl: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    setup_type: str
    timeframe: str
    reasoning: str
    technical_indicators: Optional[Dict] = None
    market_condition: Optional[str] = None
    confidence_level: int
    risk_reward_ratio: Optional[float] = None
    execution_quality: Optional[int] = None
    slippage: Optional[float] = None
    entry_timing: Optional[str] = None
    exit_reason: Optional[str] = None
    emotional_state: Optional[List[str]] = None
    rule_following: Optional[int] = None
    what_went_well: Optional[str] = None
    what_went_wrong: Optional[str] = None
    lessons_learned: Optional[str] = None
    tags: Optional[List[str]] = None
    status: str
    created_at: str
    updated_at: str
    review_completed_at: Optional[str] = None


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


# ============================================================================
# TRADE JOURNAL ENDPOINTS
# ============================================================================

@app.post("/api/journal/trades", response_model=Dict[str, Any])
async def create_journal_entry(entry: TradeJournalCreate):
    """Create new trade journal entry"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Calculate risk-reward ratio
                rr_ratio = None
                if entry.stop_loss and entry.take_profit:
                    risk = abs(entry.entry_price - entry.stop_loss)
                    reward = abs(entry.take_profit - entry.entry_price)
                    if risk > 0:
                        rr_ratio = reward / risk

                # Convert technical_indicators to JSONB
                tech_indicators = None
                if entry.technical_indicators:
                    tech_indicators = {
                        "indicators": entry.technical_indicators
                    }

                cur.execute(
                    """
                    INSERT INTO trade_journal (
                        position_id, setup_type, timeframe, reasoning,
                        technical_indicators, market_condition,
                        confidence_level, chart_screenshot,
                        risk_reward_ratio, status
                    ) VALUES (
                        %s, %s, %s, %s, %s, %s, %s, %s, %s, 'planned'
                    )
                    RETURNING id, created_at
                    """,
                    (
                        entry.position_id,
                        entry.setup_type,
                        entry.timeframe,
                        entry.reasoning,
                        tech_indicators,
                        entry.market_condition,
                        entry.confidence_level,
                        entry.chart_screenshot,
                        rr_ratio
                    )
                )

                result = cur.fetchone()
                return {
                    "id": str(result['id']),
                    "created_at": result['created_at'].isoformat(),
                    "risk_reward_ratio": float(rr_ratio) if rr_ratio else None
                }

    except Exception as e:
        print(f"Error creating journal entry: {e}")
        raise


@app.get("/api/journal/trades", response_model=List[TradeJournal])
async def get_journal_entries(
    status: Optional[str] = None,
    strategy: Optional[str] = None,
    limit: int = 50
):
    """Get trade journal entries with optional filtering"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Check if table exists
                cur.execute(
                    """SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = 'trade_journal'
                    )"""
                )
                if not cur.fetchone()['exists']:
                    return []

                # Build query with filters
                query = """
                    SELECT
                        tj.id::text,
                        tj.position_id::text,
                        p.symbol,
                        p.side,
                        p.strategy_tag,
                        p.entry_price,
                        p.current_price,
                        p.unrealized_pnl,
                        p.stop_loss,
                        p.take_profit,
                        tj.setup_type,
                        tj.timeframe,
                        tj.reasoning,
                        tj.technical_indicators,
                        tj.market_condition,
                        tj.confidence_level,
                        tj.risk_reward_ratio,
                        tj.execution_quality,
                        tj.slippage,
                        tj.entry_timing,
                        tj.exit_reason,
                        tj.emotional_state,
                        tj.rule_following,
                        tj.what_went_well,
                        tj.what_went_wrong,
                        tj.lessons_learned,
                        tj.tags,
                        tj.status,
                        tj.created_at,
                        tj.updated_at,
                        tj.review_completed_at
                    FROM trade_journal tj
                    LEFT JOIN positions p ON tj.position_id = p.id
                    WHERE 1=1
                """

                params = []
                if status:
                    query += " AND tj.status = %s"
                    params.append(status)

                if strategy:
                    query += " AND p.strategy_tag = %s"
                    params.append(strategy)

                query += " ORDER BY tj.created_at DESC LIMIT %s"
                params.append(limit)

                cur.execute(query, params)

                entries = []
                for row in cur.fetchall():
                    # Extract technical indicators
                    tech_ind = row.get('technical_indicators')
                    if tech_ind:
                        tech_ind = tech_ind

                    entries.append(TradeJournal(
                        id=row['id'],
                        position_id=row['position_id'],
                        symbol=row['symbol'] or '',
                        side=row['side'] or '',
                        strategy_tag=row['strategy_tag'] or '',
                        entry_price=float(row['entry_price'] or 0),
                        current_price=(
                            float(row['current_price'])
                            if row.get('current_price') else None
                        ),
                        unrealized_pnl=(
                            float(row['unrealized_pnl'])
                            if row.get('unrealized_pnl') else None
                        ),
                        stop_loss=(
                            float(row['stop_loss'])
                            if row.get('stop_loss') else None
                        ),
                        take_profit=(
                            float(row['take_profit'])
                            if row.get('take_profit') else None
                        ),
                        setup_type=row['setup_type'],
                        timeframe=row['timeframe'],
                        reasoning=row['reasoning'],
                        technical_indicators=tech_ind,
                        market_condition=row.get('market_condition'),
                        confidence_level=row['confidence_level'],
                        risk_reward_ratio=(
                            float(row['risk_reward_ratio'])
                            if row.get('risk_reward_ratio') else None
                        ),
                        execution_quality=row.get('execution_quality'),
                        slippage=(
                            float(row['slippage'])
                            if row.get('slippage') else None
                        ),
                        entry_timing=row.get('entry_timing'),
                        exit_reason=row.get('exit_reason'),
                        emotional_state=row.get('emotional_state'),
                        rule_following=row.get('rule_following'),
                        what_went_well=row.get('what_went_well'),
                        what_went_wrong=row.get('what_went_wrong'),
                        lessons_learned=row.get('lessons_learned'),
                        tags=row.get('tags'),
                        status=row['status'],
                        created_at=row['created_at'].isoformat(),
                        updated_at=row['updated_at'].isoformat(),
                        review_completed_at=(
                            row['review_completed_at'].isoformat()
                            if row.get('review_completed_at') else None
                        )
                    ))

                return entries

    except Exception as e:
        print(f"Error fetching journal entries: {e}")
        return []


@app.patch("/api/journal/trades/{journal_id}")
async def update_journal_entry(
    journal_id: str,
    update: TradeJournalUpdate
):
    """Update trade journal entry"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                # Build update query dynamically
                update_fields = []
                params = []

                if update.setup_type is not None:
                    update_fields.append("setup_type = %s")
                    params.append(update.setup_type)

                if update.reasoning is not None:
                    update_fields.append("reasoning = %s")
                    params.append(update.reasoning)

                if update.confidence_level is not None:
                    update_fields.append("confidence_level = %s")
                    params.append(update.confidence_level)

                if update.execution_quality is not None:
                    update_fields.append("execution_quality = %s")
                    params.append(update.execution_quality)

                if update.slippage is not None:
                    update_fields.append("slippage = %s")
                    params.append(update.slippage)

                if update.entry_timing is not None:
                    update_fields.append("entry_timing = %s")
                    params.append(update.entry_timing)

                if update.status is not None:
                    update_fields.append("status = %s")
                    params.append(update.status)

                if not update_fields:
                    return {"success": True, "message": "No fields to update"}

                params.append(journal_id)
                query = f"""
                    UPDATE trade_journal
                    SET {', '.join(update_fields)}
                    WHERE id = %s
                """

                cur.execute(query, params)
                return {"success": True, "updated": cur.rowcount}

    except Exception as e:
        print(f"Error updating journal entry: {e}")
        raise


@app.post("/api/journal/trades/{journal_id}/review")
async def add_trade_review(journal_id: str, review: TradeReview):
    """Add post-trade review to journal entry"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    UPDATE trade_journal
                    SET
                        exit_reason = %s,
                        execution_quality = %s,
                        entry_timing = %s,
                        emotional_state = %s,
                        rule_following = %s,
                        what_went_well = %s,
                        what_went_wrong = %s,
                        lessons_learned = %s,
                        tags = %s,
                        review_completed_at = NOW(),
                        status = 'closed'
                    WHERE id = %s
                    RETURNING review_completed_at
                    """,
                    (
                        review.exit_reason,
                        review.execution_quality,
                        review.entry_timing,
                        review.emotional_state,
                        review.rule_following,
                        review.what_went_well,
                        review.what_went_wrong,
                        review.lessons_learned,
                        review.tags,
                        journal_id
                    )
                )

                result = cur.fetchone()
                if result:
                    return {
                        "success": True,
                        "review_completed_at": result[0].isoformat()
                    }
                else:
                    return {"success": False, "error": "Entry not found"}

    except Exception as e:
        print(f"Error adding trade review: {e}")
        raise


@app.get("/api/journal/statistics")
async def get_journal_statistics(period: str = 'month'):
    """Get journal statistics and insights"""
    try:
        with get_db_connection() as conn:
            with conn.cursor(cursor_factory=RealDictCursor) as cur:
                # Check if table exists
                cur.execute(
                    """SELECT EXISTS (
                        SELECT FROM information_schema.tables
                        WHERE table_name = 'trade_journal'
                    )"""
                )
                if not cur.fetchone()['exists']:
                    return {
                        "setupWinRates": {},
                        "emotionImpact": {},
                        "executionQuality": {"avg": 0, "trend": 0},
                        "commonMistakes": [],
                        "bestSetups": []
                    }

                # Calculate time filter
                now = datetime.now(ZoneInfo("Europe/Istanbul"))
                if period == 'week':
                    start_time = now - timedelta(days=7)
                elif period == 'month':
                    start_time = now - timedelta(days=30)
                else:  # all
                    start_time = datetime(2020, 1, 1, tzinfo=ZoneInfo(
                        "Europe/Istanbul"
                    ))

                # Setup win rates
                cur.execute(
                    """
                    SELECT
                        setup_type,
                        COUNT(*) as total,
                        AVG(execution_quality) as avg_quality
                    FROM trade_journal
                    WHERE created_at >= %s
                        AND setup_type IS NOT NULL
                    GROUP BY setup_type
                    """,
                    (start_time,)
                )

                setup_stats = {}
                for row in cur.fetchall():
                    setup_stats[row['setup_type']] = {
                        "total": row['total'],
                        "avgQuality": float(row['avg_quality'] or 0)
                    }

                # Execution quality trend
                cur.execute(
                    """
                    SELECT AVG(execution_quality) as avg_quality
                    FROM trade_journal
                    WHERE created_at >= %s
                        AND execution_quality IS NOT NULL
                    """,
                    (start_time,)
                )

                avg_quality = cur.fetchone()
                exec_quality_avg = float(avg_quality['avg_quality'] or 0)

                # Common tags (mistakes/wins)
                cur.execute(
                    """
                    SELECT unnest(tags) as tag, COUNT(*) as count
                    FROM trade_journal
                    WHERE created_at >= %s AND tags IS NOT NULL
                    GROUP BY tag
                    ORDER BY count DESC
                    LIMIT 10
                    """,
                    (start_time,)
                )

                common_tags = [
                    row['tag'] for row in cur.fetchall()
                ]

                return {
                    "setupWinRates": setup_stats,
                    "emotionImpact": {},  # TODO: Correlation analysis
                    "executionQuality": {
                        "avg": exec_quality_avg,
                        "trend": 0  # TODO: Calculate trend
                    },
                    "commonMistakes": [
                        t for t in common_tags if 'mistake' in t.lower()
                    ],
                    "bestSetups": list(setup_stats.keys())[:3]
                }

    except Exception as e:
        print(f"Error fetching journal statistics: {e}")
        return {
            "setupWinRates": {},
            "emotionImpact": {},
            "executionQuality": {"avg": 0, "trend": 0},
            "commonMistakes": [],
            "bestSetups": []
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
