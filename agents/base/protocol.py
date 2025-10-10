"""
Inter-agent communication protocol.
Defines message formats and data structures for agent communication.
"""

from typing import Any, Dict, List, Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field
from enum import Enum


class MessageType(str, Enum):
    """Message types for inter-agent communication"""

    MARKET_DATA = "market.data"
    SIGNAL = "signal"
    TRADE_INTENT = "trade.intent"
    ORDER = "order"
    EXECUTION_REPORT = "execution.report"
    RISK_ASSESSMENT = "risk.assessment"
    PORTFOLIO_UPDATE = "portfolio.update"
    POSITION_UPDATE = "position.update"


class SignalType(str, Enum):
    """Trading signal types"""

    BUY = "BUY"
    SELL = "SELL"
    HOLD = "HOLD"


class OrderSide(str, Enum):
    """Order side"""

    BUY = "BUY"
    SELL = "SELL"


class OrderType(str, Enum):
    """Order types"""

    MARKET = "MARKET"
    LIMIT = "LIMIT"
    STOP_LOSS = "STOP_LOSS"
    TAKE_PROFIT = "TAKE_PROFIT"


class OrderStatus(str, Enum):
    """Order status"""

    PENDING = "PENDING"
    FILLED = "FILLED"
    PARTIAL = "PARTIAL"
    CANCELLED = "CANCELLED"
    FAILED = "FAILED"


class BaseMessage(BaseModel):
    """Base message structure"""

    version: str = "1.0"
    type: MessageType
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    source_agent: str
    correlation_id: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


class MarketDataMessage(BaseMessage):
    """Market data message"""

    type: Literal[MessageType.MARKET_DATA] = MessageType.MARKET_DATA
    exchange: str
    symbol: str
    data: Dict[str, Any]


class TradingSignal(BaseMessage):
    """Trading signal from analysis agents"""

    type: Literal[MessageType.SIGNAL] = MessageType.SIGNAL
    agent_type: str
    symbol: str
    signal: SignalType
    confidence: float = Field(ge=0.0, le=1.0)
    price_target: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    reasoning: Optional[str] = None
    indicators: Dict[str, float] = Field(default_factory=dict)


class TradeIntent(BaseMessage):
    """Trade intent from strategy agent"""

    type: Literal[MessageType.TRADE_INTENT] = MessageType.TRADE_INTENT
    symbol: str
    side: OrderSide
    quantity: float
    expected_price: float
    signals: List[TradingSignal] = Field(default_factory=list)
    strategy_name: str
    confidence: float = Field(ge=0.0, le=1.0)


class Order(BaseMessage):
    """Order from risk manager"""

    type: Literal[MessageType.ORDER] = MessageType.ORDER
    exchange: str
    symbol: str
    order_type: OrderType
    side: OrderSide
    quantity: float
    price: Optional[float] = None
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    leverage: float = 1.0
    risk_approved: bool
    risk_params: Dict[str, Any] = Field(default_factory=dict)


class ExecutionReport(BaseMessage):
    """Execution report from execution agent"""

    type: Literal[MessageType.EXECUTION_REPORT] = MessageType.EXECUTION_REPORT
    order_id: str
    exchange: str
    symbol: str
    side: OrderSide
    status: OrderStatus
    filled_quantity: float
    average_price: float
    total_value: float
    fee: float
    fee_currency: str
    execution_time: datetime


class RiskAssessment(BaseMessage):
    """Risk assessment from risk manager"""

    type: Literal[MessageType.RISK_ASSESSMENT] = MessageType.RISK_ASSESSMENT
    trade_intent_id: str
    symbol: str
    approved: bool
    risk_score: float = Field(ge=0.0, le=1.0)
    position_size: float
    var_estimate: float
    max_loss: float
    rejection_reason: Optional[str] = None
    risk_metrics: Dict[str, Any] = Field(default_factory=dict)


class PortfolioUpdate(BaseMessage):
    """Portfolio state update"""

    type: Literal[MessageType.PORTFOLIO_UPDATE] = MessageType.PORTFOLIO_UPDATE
    total_value: float
    cash_balance: float
    positions_value: float
    unrealized_pnl: float
    realized_pnl: float
    daily_pnl: float
    positions: List[Dict[str, Any]] = Field(default_factory=list)


class PositionUpdate(BaseMessage):
    """Individual position update"""

    type: Literal[MessageType.POSITION_UPDATE] = MessageType.POSITION_UPDATE
    symbol: str
    side: str
    quantity: float
    entry_price: float
    current_price: float
    unrealized_pnl: float
    realized_pnl: float
    metadata: Dict[str, Any] = Field(default_factory=dict)


# Message serialization helpers
def serialize_message(message: BaseMessage) -> Dict[str, Any]:
    """Serialize a message to dict"""
    return message.model_dump(mode="json")


def deserialize_message(data: Dict[str, Any]) -> BaseMessage:
    """Deserialize a message from dict"""
    message_type = data.get("type")

    type_map = {
        MessageType.MARKET_DATA: MarketDataMessage,
        MessageType.SIGNAL: TradingSignal,
        MessageType.TRADE_INTENT: TradeIntent,
        MessageType.ORDER: Order,
        MessageType.EXECUTION_REPORT: ExecutionReport,
        MessageType.RISK_ASSESSMENT: RiskAssessment,
        MessageType.PORTFOLIO_UPDATE: PortfolioUpdate,
        MessageType.POSITION_UPDATE: PositionUpdate,
    }

    message_class = type_map.get(message_type, BaseMessage)
    return message_class(**data)
