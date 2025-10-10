"""
Structured logging setup for the trading system.
Supports both JSON and text formats with contextual information.
"""

import logging
import sys
from typing import Any, Dict
import structlog
from core.config.settings import settings


def setup_logging() -> None:
    """Configure structured logging for the application"""

    # Configure structlog processors
    processors = [
        structlog.contextvars.merge_contextvars,
        structlog.processors.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if settings.logging.format == "json":
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.extend(
            [
                structlog.dev.ConsoleRenderer(colors=True)
                if sys.stderr.isatty()
                else structlog.processors.JSONRenderer()
            ]
        )

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.logging.level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard logging
    logging.basicConfig(
        format="%(message)s",
        level=logging.getLevelName(settings.logging.level),
        stream=sys.stdout,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get a logger instance with the given name"""
    return structlog.get_logger(name)


class LoggerMixin:
    """Mixin class to add logging capability to any class"""

    @property
    def logger(self) -> structlog.BoundLogger:
        """Get logger bound to this class"""
        if not hasattr(self, "_logger"):
            self._logger = get_logger(self.__class__.__name__)
        return self._logger

    def log_event(
        self,
        event: str,
        level: str = "info",
        **kwargs: Any,
    ) -> None:
        """Log an event with context"""
        log_fn = getattr(self.logger, level.lower())
        log_fn(event, **kwargs)

    def log_trade(
        self,
        action: str,
        symbol: str,
        side: str,
        quantity: float,
        price: float,
        **kwargs: Any,
    ) -> None:
        """Log trading activity"""
        self.logger.info(
            "trade_event",
            action=action,
            symbol=symbol,
            side=side,
            quantity=quantity,
            price=price,
            **kwargs,
        )

    def log_signal(
        self,
        agent: str,
        symbol: str,
        signal: str,
        confidence: float,
        **kwargs: Any,
    ) -> None:
        """Log trading signals"""
        self.logger.info(
            "signal_event",
            agent=agent,
            symbol=symbol,
            signal=signal,
            confidence=confidence,
            **kwargs,
        )

    def log_error(
        self,
        error: Exception,
        context: Dict[str, Any] | None = None,
    ) -> None:
        """Log errors with context"""
        self.logger.error(
            "error_occurred",
            error=str(error),
            error_type=type(error).__name__,
            context=context or {},
            exc_info=True,
        )


# Initialize logging on module import
setup_logging()
