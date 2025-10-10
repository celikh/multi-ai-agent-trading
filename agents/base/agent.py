"""
Base agent class providing common functionality for all trading agents.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Callable
import asyncio
from datetime import datetime
from core.logging.logger import LoggerMixin
from core.config.settings import settings
from infrastructure.messaging.rabbitmq import get_broker, RabbitMQBroker
from infrastructure.database.postgresql import get_db, PostgreSQLDatabase
from agents.base.protocol import (
    BaseMessage,
    MessageType,
    serialize_message,
    deserialize_message,
)


class BaseAgent(LoggerMixin, ABC):
    """
    Base class for all trading agents.

    Provides:
    - Message publishing/subscribing
    - Database access
    - Logging
    - State management
    - Error handling
    """

    def __init__(
        self,
        name: str,
        agent_type: str,
        description: str = "",
    ):
        self.name = name
        self.agent_type = agent_type
        self.description = description
        self._running = False
        self._tasks: List[asyncio.Task] = []
        self._broker: Optional[RabbitMQBroker] = None
        self._db: Optional[PostgreSQLDatabase] = None
        self._subscriptions: Dict[str, Callable] = {}

    async def initialize(self) -> None:
        """Initialize agent resources"""
        try:
            # Connect to message broker
            self._broker = await get_broker()

            # Connect to database
            self._db = await get_db()

            # Load agent configuration
            await self._load_config()

            # Call agent-specific initialization
            await self.setup()

            self.log_event(
                "agent_initialized",
                agent=self.name,
                type=self.agent_type,
            )

        except Exception as e:
            self.log_error(e, {"agent": self.name, "phase": "initialization"})
            raise

    async def shutdown(self) -> None:
        """Shutdown agent gracefully"""
        self._running = False

        # Cancel all tasks
        for task in self._tasks:
            task.cancel()

        await asyncio.gather(*self._tasks, return_exceptions=True)

        # Call agent-specific cleanup
        await self.cleanup()

        self.log_event("agent_shutdown", agent=self.name)

    async def start(self) -> None:
        """Start agent operation"""
        self._running = True

        try:
            # Subscribe to topics
            await self._setup_subscriptions()

            # Run agent logic
            await self.run()

        except Exception as e:
            self.log_error(e, {"agent": self.name, "phase": "runtime"})
            raise
        finally:
            await self.shutdown()

    async def publish_message(
        self,
        topic: str,
        message: BaseMessage,
        priority: int = 5,
    ) -> None:
        """Publish a message to a topic"""
        if not self._broker:
            raise RuntimeError("Agent not initialized")

        message.source_agent = self.name
        data = serialize_message(message)

        await self._broker.publish(topic, data, priority=priority)

        self.logger.debug(
            "message_published",
            agent=self.name,
            topic=topic,
            message_type=message.type,
        )

    async def subscribe_topic(
        self,
        topic: str,
        handler: Callable[[BaseMessage], Any],
    ) -> None:
        """Subscribe to a topic with a handler"""
        if not self._broker:
            raise RuntimeError("Agent not initialized")

        async def wrapped_handler(data: Dict[str, Any]) -> None:
            try:
                message = deserialize_message(data)
                await handler(message)
            except Exception as e:
                self.log_error(e, {
                    "agent": self.name,
                    "topic": topic,
                    "handler": handler.__name__,
                })

        self._subscriptions[topic] = wrapped_handler
        await self._broker.subscribe(topic, wrapped_handler, queue_name=f"{self.name}.{topic}")

        self.logger.info(
            "subscribed_to_topic",
            agent=self.name,
            topic=topic,
        )

    async def save_state(self, state: Dict[str, Any]) -> None:
        """Save agent state to database"""
        if not self._db:
            raise RuntimeError("Agent not initialized")

        await self._db.execute(
            """
            INSERT INTO agent_configs (agent_name, agent_type, config, enabled)
            VALUES ($1, $2, $3, $4)
            ON CONFLICT (agent_name)
            DO UPDATE SET config = $3, updated_at = NOW()
            """,
            self.name,
            self.agent_type,
            state,
            True,
        )

        self.logger.debug("state_saved", agent=self.name)

    async def load_state(self) -> Optional[Dict[str, Any]]:
        """Load agent state from database"""
        if not self._db:
            raise RuntimeError("Agent not initialized")

        result = await self._db.fetch_one(
            "SELECT config FROM agent_configs WHERE agent_name = $1",
            self.name,
        )

        if result:
            self.logger.debug("state_loaded", agent=self.name)
            return result.get("config")

        return None

    async def _load_config(self) -> None:
        """Load agent configuration"""
        state = await self.load_state()
        if state:
            await self.configure(state)

    async def _setup_subscriptions(self) -> None:
        """Setup message subscriptions"""
        topics = self.get_subscribed_topics()
        for topic in topics:
            handler = getattr(self, f"handle_{topic.replace('.', '_')}", None)
            if handler:
                await self.subscribe_topic(topic, handler)

    def create_task(self, coro) -> asyncio.Task:
        """Create a managed task"""
        task = asyncio.create_task(coro)
        self._tasks.append(task)
        return task

    # Abstract methods to be implemented by subclasses
    @abstractmethod
    async def setup(self) -> None:
        """Agent-specific setup logic"""
        pass

    @abstractmethod
    async def run(self) -> None:
        """Main agent logic"""
        pass

    @abstractmethod
    async def cleanup(self) -> None:
        """Agent-specific cleanup logic"""
        pass

    @abstractmethod
    def get_subscribed_topics(self) -> List[str]:
        """Return list of topics this agent subscribes to"""
        pass

    async def configure(self, config: Dict[str, Any]) -> None:
        """Configure agent with settings (optional override)"""
        pass


class PeriodicAgent(BaseAgent):
    """Agent that runs periodic tasks"""

    def __init__(
        self,
        name: str,
        agent_type: str,
        interval_seconds: int = 60,
        description: str = "",
    ):
        super().__init__(name, agent_type, description)
        self.interval = interval_seconds

    async def run(self) -> None:
        """Run periodic task"""
        while self._running:
            try:
                await self.execute()
                await asyncio.sleep(self.interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self.log_error(e, {"agent": self.name, "phase": "periodic_execution"})
                await asyncio.sleep(self.interval)

    @abstractmethod
    async def execute(self) -> None:
        """Execute periodic task (implement in subclass)"""
        pass
