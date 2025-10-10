"""
Dashboard API
Provides trading dashboard metrics and analytics endpoints
"""

from fastapi import FastAPI, Query, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from decimal import Decimal
import asyncpg
from pydantic import BaseModel
from core.config.settings import settings

app = FastAPI(title="Trading Dashboard API", version="1.0.0")

# CORS middleware for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database connection pool
db_pool: Optional[asyncpg.Pool] = None


# =====================================================
# Pydantic Models
# =====================================================

class DashboardMetrics(BaseModel):
    """Dashboard summary metrics"""
    balance: Dict[str, Any]
    trades: Dict[str, Any]
    pnl: Dict[str, Any]
    risk: Dict[str, Any]


class PositionDetail(BaseModel):
    """Position details for dashboard table"""
    id: str
    symbol: str
    side: str
    status: str
    quantity: Decimal
    entry_price: Decimal
    current_price: Optional[Decimal]
    stop_loss: Optional[Decimal]
    take_profit: Optional[Decimal]
    pnl: Decimal
    pnl_pct: Decimal
    hold_duration: str
    opened_at: datetime
    closed_at: Optional[datetime]
    strategy_tag: Optional[str]
    execution_quality: Optional[Decimal]


class PerformanceSnapshot(BaseModel):
    """Performance snapshot data"""
    timestamp: datetime
    total_balance: Decimal
    total_pnl: Decimal
    total_pnl_pct: Decimal
    win_rate: Decimal
    open_positions: int


# =====================================================
# Database Utilities
# =====================================================

@app.on_event("startup")
async def startup():
    """Initialize database connection pool"""
    global db_pool
    db_pool = await asyncpg.create_pool(
        host=settings.postgres.host,
        port=settings.postgres.port,
        database=settings.postgres.database,
        user=settings.postgres.user,
        password=settings.postgres.password,
        min_size=5,
        max_size=20,
    )
    print("✅ Database connection pool initialized")


@app.on_event("shutdown")
async def shutdown():
    """Close database connection pool"""
    global db_pool
    if db_pool:
        await db_pool.close()
    print("❌ Database connection pool closed")


# =====================================================
# API Endpoints
# =====================================================

@app.get("/")
async def root():
    """API info"""
    return {
        "name": "Trading Dashboard API",
        "version": "1.0.0",
        "status": "operational",
    }


@app.get("/api/dashboard/metrics", response_model=DashboardMetrics)
async def get_dashboard_metrics(
    period: str = Query("today", regex="^(today|week|month|year|all)$"),
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None,
):
    """
    Get dashboard summary metrics

    Parameters:
    - period: Time period (today, week, month, year, all)
    - start_date: Custom start date (optional)
    - end_date: Custom end date (optional)
    """
    # Calculate date range
    end_dt = end_date or datetime.now()
    if period == "today":
        start_dt = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == "week":
        start_dt = end_dt - timedelta(days=7)
    elif period == "month":
        start_dt = end_dt - timedelta(days=30)
    elif period == "year":
        start_dt = end_dt - timedelta(days=365)
    else:  # all
        start_dt = datetime(2020, 1, 1)

    if start_date:
        start_dt = start_date

    # Query database
    async with db_pool.acquire() as conn:
        # Portfolio status
        portfolio = await conn.fetchrow("""
            SELECT
                open_positions,
                total_unrealized_pnl,
                total_realized_pnl,
                total_pnl,
                avg_execution_quality,
                total_fees,
                total_positions
            FROM v_portfolio_status
        """)

        # Win/Loss stats
        stats = await conn.fetchrow("""
            SELECT wins, losses, win_rate, avg_win, avg_loss, best_trade, worst_trade
            FROM v_win_loss_stats
        """)

        # Get previous balance for change calculation (mock for now)
        current_balance = 10000.00 + float(portfolio['total_pnl'] or 0)
        previous_balance = current_balance - 100  # Mock previous

        return DashboardMetrics(
            balance={
                "current": round(current_balance, 2),
                "previous": round(previous_balance, 2),
                "change": round(current_balance - previous_balance, 2),
                "change_pct": round(100 * (current_balance - previous_balance) / previous_balance, 2),
            },
            trades={
                "wins": stats['wins'] or 0,
                "losses": stats['losses'] or 0,
                "win_rate": float(stats['win_rate'] or 0),
                "open": portfolio['open_positions'] or 0,
                "total": portfolio['total_positions'] or 0,
            },
            pnl={
                "total": float(portfolio['total_pnl'] or 0),
                "total_pct": round(100 * float(portfolio['total_pnl'] or 0) / 10000, 4),
                "realized": float(portfolio['total_realized_pnl'] or 0),
                "unrealized": float(portfolio['total_unrealized_pnl'] or 0),
                "avg_win": float(stats['avg_win'] or 0),
                "avg_loss": float(stats['avg_loss'] or 0),
                "best_trade": float(stats['best_trade'] or 0),
                "worst_trade": float(stats['worst_trade'] or 0),
            },
            risk={
                "sharpe_ratio": 0.0,  # TODO: Calculate
                "max_drawdown": 0.0,  # TODO: Calculate
                "avg_rr_ratio": 0.0,  # TODO: Calculate
                "avg_execution_quality": float(portfolio['avg_execution_quality'] or 0),
                "total_fees": float(portfolio['total_fees'] or 0),
            }
        )


@app.get("/api/positions", response_model=List[PositionDetail])
async def get_positions(
    status: str = Query("all", regex="^(all|open|closed)$"),
    symbol: Optional[str] = None,
    limit: int = Query(50, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    """
    Get position list with filtering

    Parameters:
    - status: Position status filter (all, open, closed)
    - symbol: Symbol filter (e.g., BTC/USDT)
    - limit: Number of results
    - offset: Pagination offset
    """
    query = """
        SELECT
            id, symbol, side, status, quantity,
            entry_price, current_price, stop_loss, take_profit,
            pnl, pnl_pct,
            EXTRACT(EPOCH FROM hold_duration)::int as hold_seconds,
            opened_at, closed_at, strategy_tag, execution_quality
        FROM v_position_dashboard
        WHERE 1=1
    """

    params = []
    param_count = 1

    if status != "all":
        query += f" AND status = ${param_count}"
        params.append(status.upper())
        param_count += 1

    if symbol:
        query += f" AND symbol = ${param_count}"
        params.append(symbol)
        param_count += 1

    query += f" ORDER BY opened_at DESC LIMIT ${param_count} OFFSET ${param_count + 1}"
    params.extend([limit, offset])

    async with db_pool.acquire() as conn:
        rows = await conn.fetch(query, *params)

        positions = []
        for row in rows:
            # Format hold duration
            seconds = row['hold_seconds']
            hours = seconds // 3600
            minutes = (seconds % 3600) // 60
            hold_str = f"{hours}h {minutes}m"

            positions.append(PositionDetail(
                id=str(row['id']),
                symbol=row['symbol'],
                side=row['side'],
                status=row['status'],
                quantity=row['quantity'],
                entry_price=row['entry_price'],
                current_price=row['current_price'],
                stop_loss=row['stop_loss'],
                take_profit=row['take_profit'],
                pnl=row['pnl'],
                pnl_pct=row['pnl_pct'],
                hold_duration=hold_str,
                opened_at=row['opened_at'],
                closed_at=row['closed_at'],
                strategy_tag=row['strategy_tag'],
                execution_quality=row['execution_quality'],
            ))

        return positions


@app.get("/api/analytics/equity-curve", response_model=List[Dict[str, Any]])
async def get_equity_curve(
    period: str = Query("month", regex="^(week|month|year|all)$"),
):
    """
    Get equity curve data points for charting

    Returns list of {timestamp, balance, pnl} points
    """
    # TODO: Implement using performance_snapshots table
    # For now, return mock data
    return []


@app.post("/api/performance/snapshot")
async def create_performance_snapshot():
    """
    Create a new performance snapshot

    Useful for periodic snapshots and equity curve tracking
    """
    async with db_pool.acquire() as conn:
        snapshot_id = await conn.fetchval("""
            SELECT create_performance_snapshot()
        """)

        return {
            "success": True,
            "snapshot_id": str(snapshot_id),
            "timestamp": datetime.now().isoformat(),
        }


@app.get("/api/analytics/trade-distribution")
async def get_trade_distribution(
    group_by: str = Query("symbol", regex="^(symbol|strategy|side|status)$"),
):
    """
    Get trade distribution grouped by specified field

    Parameters:
    - group_by: Field to group by (symbol, strategy, side, status)
    """
    async with db_pool.acquire() as conn:
        query = f"""
            SELECT
                {group_by},
                COUNT(*) as count,
                SUM(CASE WHEN status = 'OPEN' THEN unrealized_pnl ELSE realized_pnl END) as total_pnl,
                AVG(CASE WHEN status = 'OPEN' THEN unrealized_pnl ELSE realized_pnl END) as avg_pnl
            FROM positions
            GROUP BY {group_by}
            ORDER BY count DESC
        """

        rows = await conn.fetch(query)

        return [
            {
                group_by: row[group_by],
                "count": row['count'],
                "total_pnl": float(row['total_pnl'] or 0),
                "avg_pnl": float(row['avg_pnl'] or 0),
            }
            for row in rows
        ]


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        async with db_pool.acquire() as conn:
            await conn.fetchval("SELECT 1")
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        return {"status": "unhealthy", "error": str(e)}


# =====================================================
# Run with: uvicorn api.dashboard:app --reload --port 8000
# =====================================================

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
