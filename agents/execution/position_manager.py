"""
Position Manager Module
Track and manage trading positions, P&L calculation.
"""

from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from decimal import Decimal


class PositionSide(str, Enum):
    """Position side types"""

    LONG = "long"
    SHORT = "short"


class PositionStatus(str, Enum):
    """Position status"""

    OPEN = "open"
    CLOSED = "closed"
    PARTIALLY_CLOSED = "partially_closed"


@dataclass
class Position:
    """Trading position"""

    position_id: str
    symbol: str
    side: PositionSide
    entry_price: float
    current_price: float
    quantity: float
    initial_quantity: float
    unrealized_pnl: float
    unrealized_pnl_pct: float
    realized_pnl: float
    total_pnl: float
    stop_loss: Optional[float]
    take_profit: Optional[float]
    entry_time: datetime
    status: PositionStatus
    metadata: Dict


@dataclass
class PositionUpdate:
    """Position update event"""

    position_id: str
    symbol: str
    action: str  # "open", "increase", "decrease", "close"
    quantity: float
    price: float
    pnl: float
    timestamp: datetime
    metadata: Dict


class PositionManager:
    """
    Manage trading positions and P&L
    """

    def __init__(self):
        self.positions: Dict[str, Position] = {}
        self.closed_positions: List[Position] = []
        self.position_updates: List[PositionUpdate] = []

    def open_position(
        self,
        symbol: str,
        side: str,
        quantity: float,
        entry_price: float,
        stop_loss: Optional[float] = None,
        take_profit: Optional[float] = None,
        metadata: Optional[Dict] = None,
    ) -> Position:
        """
        Open a new position

        Args:
            symbol: Trading pair
            side: "long" or "short"
            quantity: Position size
            entry_price: Entry price
            stop_loss: Stop loss price
            take_profit: Take profit price
            metadata: Additional information

        Returns:
            Position object
        """
        position_id = f"{symbol}_{side}_{datetime.utcnow().timestamp()}"

        position = Position(
            position_id=position_id,
            symbol=symbol,
            side=PositionSide(side.lower()),
            entry_price=entry_price,
            current_price=entry_price,
            quantity=quantity,
            initial_quantity=quantity,
            unrealized_pnl=0.0,
            unrealized_pnl_pct=0.0,
            realized_pnl=0.0,
            total_pnl=0.0,
            stop_loss=stop_loss,
            take_profit=take_profit,
            entry_time=datetime.utcnow(),
            status=PositionStatus.OPEN,
            metadata=metadata or {},
        )

        self.positions[position_id] = position

        # Record update
        self._record_update(
            position_id=position_id,
            symbol=symbol,
            action="open",
            quantity=quantity,
            price=entry_price,
            pnl=0.0,
            metadata=metadata or {},
        )

        return position

    def update_position_price(
        self, position_id: str, current_price: float
    ) -> Optional[Position]:
        """
        Update position with current market price and recalculate P&L

        Args:
            position_id: Position ID
            current_price: Current market price

        Returns:
            Updated Position or None
        """
        if position_id not in self.positions:
            return None

        position = self.positions[position_id]
        position.current_price = current_price

        # Calculate unrealized P&L
        if position.side == PositionSide.LONG:
            pnl_per_unit = current_price - position.entry_price
        else:  # SHORT
            pnl_per_unit = position.entry_price - current_price

        position.unrealized_pnl = pnl_per_unit * position.quantity
        position.unrealized_pnl_pct = (
            (pnl_per_unit / position.entry_price) * 100
        )

        # Total P&L
        position.total_pnl = position.unrealized_pnl + position.realized_pnl

        return position

    def increase_position(
        self,
        position_id: str,
        additional_quantity: float,
        price: float,
    ) -> Optional[Position]:
        """
        Increase position size (add to position)

        Args:
            position_id: Position ID
            additional_quantity: Quantity to add
            price: Fill price

        Returns:
            Updated Position or None
        """
        if position_id not in self.positions:
            return None

        position = self.positions[position_id]

        # Calculate new average entry price
        total_cost = (position.quantity * position.entry_price) + (
            additional_quantity * price
        )
        new_quantity = position.quantity + additional_quantity
        new_avg_price = total_cost / new_quantity

        # Update position
        position.entry_price = new_avg_price
        position.quantity = new_quantity
        position.current_price = price

        # Recalculate P&L
        self.update_position_price(position_id, price)

        # Record update
        self._record_update(
            position_id=position_id,
            symbol=position.symbol,
            action="increase",
            quantity=additional_quantity,
            price=price,
            pnl=0.0,
            metadata={"new_avg_price": new_avg_price},
        )

        return position

    def decrease_position(
        self,
        position_id: str,
        reduce_quantity: float,
        price: float,
    ) -> Optional[Position]:
        """
        Decrease position size (partial close)

        Args:
            position_id: Position ID
            reduce_quantity: Quantity to reduce
            price: Exit price

        Returns:
            Updated Position or None
        """
        if position_id not in self.positions:
            return None

        position = self.positions[position_id]

        if reduce_quantity >= position.quantity:
            # Full close
            return self.close_position(position_id, price)

        # Calculate P&L for closed portion
        if position.side == PositionSide.LONG:
            pnl_per_unit = price - position.entry_price
        else:
            pnl_per_unit = position.entry_price - price

        partial_pnl = pnl_per_unit * reduce_quantity

        # Update position
        position.quantity -= reduce_quantity
        position.realized_pnl += partial_pnl
        position.current_price = price
        position.status = PositionStatus.PARTIALLY_CLOSED

        # Recalculate unrealized P&L for remaining quantity
        self.update_position_price(position_id, price)

        # Record update
        self._record_update(
            position_id=position_id,
            symbol=position.symbol,
            action="decrease",
            quantity=reduce_quantity,
            price=price,
            pnl=partial_pnl,
            metadata={"remaining_quantity": position.quantity},
        )

        return position

    def close_position(
        self, position_id: str, exit_price: float
    ) -> Optional[Position]:
        """
        Close position completely

        Args:
            position_id: Position ID
            exit_price: Exit price

        Returns:
            Closed Position or None
        """
        if position_id not in self.positions:
            return None

        position = self.positions[position_id]

        # Calculate final P&L
        if position.side == PositionSide.LONG:
            pnl_per_unit = exit_price - position.entry_price
        else:
            pnl_per_unit = position.entry_price - exit_price

        final_pnl = pnl_per_unit * position.quantity

        # Update position
        position.current_price = exit_price
        position.unrealized_pnl = 0.0
        position.unrealized_pnl_pct = 0.0
        position.realized_pnl += final_pnl
        position.total_pnl = position.realized_pnl
        position.status = PositionStatus.CLOSED
        position.quantity = 0.0

        # Move to closed positions
        self.closed_positions.append(position)
        del self.positions[position_id]

        # Record update
        self._record_update(
            position_id=position_id,
            symbol=position.symbol,
            action="close",
            quantity=position.initial_quantity,
            price=exit_price,
            pnl=final_pnl,
            metadata={"final_pnl": final_pnl},
        )

        return position

    def get_position(self, position_id: str) -> Optional[Position]:
        """Get position by ID"""
        return self.positions.get(position_id)

    def get_positions_by_symbol(self, symbol: str) -> List[Position]:
        """Get all open positions for a symbol"""
        return [p for p in self.positions.values() if p.symbol == symbol]

    def get_all_positions(self) -> List[Position]:
        """Get all open positions"""
        return list(self.positions.values())

    def get_total_pnl(self) -> float:
        """Get total P&L across all positions"""
        open_pnl = sum(p.total_pnl for p in self.positions.values())
        closed_pnl = sum(p.realized_pnl for p in self.closed_positions)
        return open_pnl + closed_pnl

    def get_unrealized_pnl(self) -> float:
        """Get total unrealized P&L"""
        return sum(p.unrealized_pnl for p in self.positions.values())

    def get_realized_pnl(self) -> float:
        """Get total realized P&L"""
        open_realized = sum(p.realized_pnl for p in self.positions.values())
        closed_realized = sum(p.realized_pnl for p in self.closed_positions)
        return open_realized + closed_realized

    def get_portfolio_value(self, account_balance: float) -> float:
        """
        Calculate total portfolio value

        Args:
            account_balance: Cash balance

        Returns:
            Total portfolio value (cash + positions)
        """
        positions_value = sum(
            p.quantity * p.current_price for p in self.positions.values()
        )
        return account_balance + positions_value

    def get_exposure(self) -> Dict[str, float]:
        """
        Get exposure by symbol

        Returns:
            Dict of symbol -> total position value
        """
        exposure = {}
        for position in self.positions.values():
            value = position.quantity * position.current_price
            if position.symbol in exposure:
                exposure[position.symbol] += value
            else:
                exposure[position.symbol] = value
        return exposure

    def check_stop_loss(
        self, position_id: str
    ) -> Tuple[bool, Optional[float]]:
        """
        Check if position hit stop loss

        Returns:
            (hit_stop_loss, stop_loss_price)
        """
        if position_id not in self.positions:
            return False, None

        position = self.positions[position_id]

        if not position.stop_loss:
            return False, None

        if position.side == PositionSide.LONG:
            # Long: stop loss is below entry
            hit = position.current_price <= position.stop_loss
        else:
            # Short: stop loss is above entry
            hit = position.current_price >= position.stop_loss

        return hit, position.stop_loss

    def check_take_profit(
        self, position_id: str
    ) -> Tuple[bool, Optional[float]]:
        """
        Check if position hit take profit

        Returns:
            (hit_take_profit, take_profit_price)
        """
        if position_id not in self.positions:
            return False, None

        position = self.positions[position_id]

        if not position.take_profit:
            return False, None

        if position.side == PositionSide.LONG:
            # Long: take profit is above entry
            hit = position.current_price >= position.take_profit
        else:
            # Short: take profit is below entry
            hit = position.current_price <= position.take_profit

        return hit, position.take_profit

    def _record_update(
        self,
        position_id: str,
        symbol: str,
        action: str,
        quantity: float,
        price: float,
        pnl: float,
        metadata: Dict,
    ):
        """Record position update for audit trail"""
        update = PositionUpdate(
            position_id=position_id,
            symbol=symbol,
            action=action,
            quantity=quantity,
            price=price,
            pnl=pnl,
            timestamp=datetime.utcnow(),
            metadata=metadata,
        )
        self.position_updates.append(update)

    def get_position_history(
        self, position_id: str
    ) -> List[PositionUpdate]:
        """Get all updates for a position"""
        return [
            u for u in self.position_updates if u.position_id == position_id
        ]

    def get_performance_stats(self) -> Dict:
        """Get overall performance statistics"""
        all_closed = self.closed_positions

        if not all_closed:
            return {
                "total_trades": 0,
                "winning_trades": 0,
                "losing_trades": 0,
                "win_rate": 0.0,
                "average_win": 0.0,
                "average_loss": 0.0,
                "profit_factor": 0.0,
                "total_pnl": 0.0,
            }

        winning = [p for p in all_closed if p.realized_pnl > 0]
        losing = [p for p in all_closed if p.realized_pnl < 0]

        avg_win = (
            sum(p.realized_pnl for p in winning) / len(winning)
            if winning
            else 0.0
        )
        avg_loss = (
            sum(p.realized_pnl for p in losing) / len(losing)
            if losing
            else 0.0
        )

        total_wins = sum(p.realized_pnl for p in winning)
        total_losses = abs(sum(p.realized_pnl for p in losing))

        profit_factor = (
            total_wins / total_losses if total_losses > 0 else 0.0
        )

        return {
            "total_trades": len(all_closed),
            "winning_trades": len(winning),
            "losing_trades": len(losing),
            "win_rate": (len(winning) / len(all_closed)) * 100
            if all_closed
            else 0.0,
            "average_win": avg_win,
            "average_loss": avg_loss,
            "profit_factor": profit_factor,
            "total_pnl": sum(p.realized_pnl for p in all_closed),
        }
