-- Add dashboard-specific columns to trades table
-- Migration: 001_add_dashboard_columns.sql

-- Add pnl column to trades
ALTER TABLE trades
ADD COLUMN IF NOT EXISTS pnl DECIMAL(20, 8);

-- Add strategy tag for trade classification
ALTER TABLE trades
ADD COLUMN IF NOT EXISTS strategy_tag VARCHAR(20)
CHECK (strategy_tag IN ('swing', 'scalp', 'position'));

-- Add index for strategy filtering
CREATE INDEX IF NOT EXISTS idx_trades_strategy_tag
ON trades(strategy_tag) WHERE strategy_tag IS NOT NULL;

-- Add StonkJournal enhancement columns to positions
ALTER TABLE positions
ADD COLUMN IF NOT EXISTS strategy_tag VARCHAR(20)
CHECK (strategy_tag IN ('swing', 'scalp', 'position'));

ALTER TABLE positions
ADD COLUMN IF NOT EXISTS reasoning TEXT;

ALTER TABLE positions
ADD COLUMN IF NOT EXISTS execution_quality DECIMAL(5, 2)
CHECK (execution_quality >= 0 AND execution_quality <= 100);

-- Add index for position strategy filtering
CREATE INDEX IF NOT EXISTS idx_positions_strategy_tag
ON positions(strategy_tag) WHERE strategy_tag IS NOT NULL;

COMMENT ON COLUMN trades.pnl IS 'Profit/Loss for the trade in base currency';
COMMENT ON COLUMN trades.strategy_tag IS 'Trading strategy used: swing, scalp, or position';
COMMENT ON COLUMN positions.strategy_tag IS 'Trading strategy used for this position';
COMMENT ON COLUMN positions.reasoning IS 'Trade reasoning and setup notes';
COMMENT ON COLUMN positions.execution_quality IS 'Trade execution quality score (0-100)';
