-- Create orders table for tracking orders and SL/TP
-- Required for DEV-76: SL/TP order monitoring

CREATE TABLE IF NOT EXISTS orders (
    order_id VARCHAR(100) PRIMARY KEY,
    symbol VARCHAR(20) NOT NULL,
    side VARCHAR(10) NOT NULL,  -- buy, sell
    order_type VARCHAR(20) NOT NULL,  -- market, limit, stop_loss, take_profit
    quantity DECIMAL(18, 8) NOT NULL,
    price DECIMAL(18, 8),  -- Limit/stop price (NULL for market orders)
    status VARCHAR(20) NOT NULL,  -- pending, open, filled, cancelled, rejected
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    filled_at TIMESTAMP,
    filled_price DECIMAL(18, 8),
    filled_quantity DECIMAL(18, 8),
    metadata JSONB,  -- Additional order info (position_id, stop_loss_for, take_profit_for, etc.)
    exchange_order_id VARCHAR(100),  -- Exchange's order ID
    error_message TEXT,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for efficient queries
CREATE INDEX IF NOT EXISTS idx_orders_symbol ON orders(symbol);
CREATE INDEX IF NOT EXISTS idx_orders_status ON orders(status);
CREATE INDEX IF NOT EXISTS idx_orders_type ON orders(order_type);
CREATE INDEX IF NOT EXISTS idx_orders_created_at ON orders(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_orders_position_id ON orders((metadata->>'position_id')) WHERE metadata->>'position_id' IS NOT NULL;

-- Comments
COMMENT ON TABLE orders IS 'Order tracking table for all order types including SL/TP';
COMMENT ON COLUMN orders.order_id IS 'Unique order identifier (UUID)';
COMMENT ON COLUMN orders.metadata IS 'JSON metadata including position_id for SL/TP orders';
COMMENT ON COLUMN orders.exchange_order_id IS 'Exchange-assigned order ID after placement';
