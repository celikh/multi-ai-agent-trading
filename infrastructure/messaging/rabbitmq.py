"""
RabbitMQ message broker for inter-agent communication.
"""

from typing import Any, Callable, Dict, Optional
import json
import asyncio
import aio_pika
from aio_pika import Message, ExchangeType, DeliveryMode
from aio_pika.abc import AbstractRobustConnection, AbstractRobustChannel
from core.config.settings import settings
from core.logging.logger import get_logger

logger = get_logger(__name__)


class RabbitMQBroker:
    """RabbitMQ message broker with async support"""

    # Topic routing keys
    TOPICS = {
        "ticks.raw": "market.ticks.raw",
        "signals.tech": "signals.technical",
        "signals.fund": "signals.fundamental",
        "signals.sent": "signals.sentiment",
        "signals.strategy": "signals.strategy",
        "trade.intent": "trading.intent",
        "trade.order": "trading.order",
        "trade.execution": "trading.execution",
        "risk.assessment": "risk.assessment",
        "portfolio.update": "portfolio.update",
    }

    def __init__(self) -> None:
        self._connection: Optional[AbstractRobustConnection] = None
        self._channel: Optional[AbstractRobustChannel] = None
        self._exchange = None

    async def connect(self) -> None:
        """Connect to RabbitMQ"""
        try:
            self._connection = await aio_pika.connect_robust(
                settings.messaging.rabbitmq_url,
                client_properties={"connection_name": "trading-system"},
            )

            self._channel = await self._connection.channel()
            await self._channel.set_qos(prefetch_count=10)

            # Declare topic exchange
            self._exchange = await self._channel.declare_exchange(
                "trading",
                ExchangeType.TOPIC,
                durable=True,
            )

            logger.info(
                "rabbitmq_connected",
                host=settings.messaging.rabbitmq_host,
                port=settings.messaging.rabbitmq_port,
            )
        except Exception as e:
            logger.error("rabbitmq_connection_failed", error=str(e))
            raise

    async def disconnect(self) -> None:
        """Disconnect from RabbitMQ"""
        if self._connection:
            await self._connection.close()
            logger.info("rabbitmq_disconnected")

    async def publish(
        self,
        topic: str,
        message: Dict[str, Any],
        priority: int = 5,
    ) -> None:
        """Publish a message to a topic"""
        if not self._exchange:
            raise RuntimeError("Not connected to RabbitMQ")

        routing_key = self.TOPICS.get(topic, topic)

        # Add metadata
        message["_meta"] = {
            "topic": topic,
            "routing_key": routing_key,
            "version": "1.0",
        }

        msg = Message(
            body=json.dumps(message).encode(),
            delivery_mode=DeliveryMode.PERSISTENT,
            priority=priority,
            content_type="application/json",
        )

        await self._exchange.publish(
            msg,
            routing_key=routing_key,
        )

        logger.debug(
            "message_published",
            topic=topic,
            routing_key=routing_key,
            size=len(msg.body),
        )

    async def subscribe(
        self,
        topic: str,
        callback: Callable,
        queue_name: Optional[str] = None,
    ) -> None:
        """Subscribe to a topic"""
        if not self._channel or not self._exchange:
            raise RuntimeError("Not connected to RabbitMQ")

        routing_key = self.TOPICS.get(topic, topic)
        queue_name = queue_name or f"queue.{topic}"

        # Declare queue
        queue = await self._channel.declare_queue(
            queue_name,
            durable=True,
            arguments={
                "x-message-ttl": 3600000,  # 1 hour TTL
                "x-max-length": 10000,  # Max 10k messages
            },
        )

        # Bind queue to exchange
        await queue.bind(self._exchange, routing_key=routing_key)

        # Start consuming
        async def process_message(message: aio_pika.IncomingMessage):
            async with message.process():
                try:
                    data = json.loads(message.body.decode())
                    await callback(data)
                    logger.debug(
                        "message_processed",
                        topic=topic,
                        routing_key=routing_key,
                    )
                except Exception as e:
                    logger.error(
                        "message_processing_failed",
                        topic=topic,
                        error=str(e),
                        exc_info=True,
                    )

        await queue.consume(process_message)

        logger.info(
            "subscribed_to_topic",
            topic=topic,
            routing_key=routing_key,
            queue=queue_name,
        )

    async def publish_signal(
        self,
        agent_type: str,
        signal_data: Dict[str, Any],
    ) -> None:
        """Publish a trading signal"""
        topic = f"signals.{agent_type.lower()}"
        await self.publish(topic, signal_data, priority=7)

    async def publish_trade_intent(
        self,
        trade_data: Dict[str, Any],
    ) -> None:
        """Publish a trade intent"""
        await self.publish("trade.intent", trade_data, priority=8)

    async def publish_order(
        self,
        order_data: Dict[str, Any],
    ) -> None:
        """Publish an order for execution"""
        await self.publish("trade.order", order_data, priority=9)

    async def publish_market_data(
        self,
        market_data: Dict[str, Any],
    ) -> None:
        """Publish market data"""
        await self.publish("ticks.raw", market_data, priority=5)


# Global broker instance
broker = RabbitMQBroker()


async def get_broker() -> RabbitMQBroker:
    """Get message broker instance"""
    if not broker._connection:
        await broker.connect()
    return broker
