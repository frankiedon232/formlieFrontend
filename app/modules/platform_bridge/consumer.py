r"""The `platform.published` consumer: the platform admin wrote global tables, Formalie drops its caches.

    fmly\Scripts\python.exe -m app.modules.platform_bridge.consumer

Binds the durable queue PLATFORM_PUBLISHED_QUEUE (dead-lettered to `formalie.dlx`) to EVENTS_EXCHANGE with the
routing key `platform.published` and calls `globals.on_published()` for every message ({table, ids, version} or
{tables: [...]}). Dropping a cache twice is harmless, so redeliveries need no bookkeeping. When the bus is down the
platform calls `/internal/admin/v1/cache/invalidate` instead, and every cached global answer expires on its own
after 10 minutes anyway.
"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from kombu import Connection, Queue
from kombu.mixins import ConsumerMixin

from app.core.config import get_settings
from app.core.events.bus import events_exchange
from app.workers.queues import DEAD_LETTER_EXCHANGE

log = logging.getLogger("formalie.platform.consumer")
ROUTING_KEY = "platform.published"


def published_queue() -> Queue:
    name = get_settings().platform_published_queue
    return Queue(name, exchange=events_exchange(), routing_key=ROUTING_KEY, durable=True,
                 queue_arguments={"x-dead-letter-exchange": DEAD_LETTER_EXCHANGE.name,
                                  "x-dead-letter-routing-key": f"{name}.dead"})


def handle(body: Any, loop: asyncio.AbstractEventLoop) -> list[str]:
    from app.modules.platform_bridge.globals import on_published

    event = json.loads(body) if isinstance(body, str | bytes) else body
    if not isinstance(event, dict):
        raise ValueError("platform.published: not an object")
    return loop.run_until_complete(on_published(event))


class PublishedConsumer(ConsumerMixin):
    def __init__(self, connection: Connection) -> None:
        self.connection = connection
        self.loop = asyncio.new_event_loop()

    def get_consumers(self, consumer_cls: Any, channel: Any) -> list[Any]:
        name = get_settings().platform_published_queue
        Queue(f"{name}.dead", exchange=DEAD_LETTER_EXCHANGE, routing_key=f"{name}.dead", durable=True)(channel).declare()
        return [consumer_cls(queues=[published_queue()], callbacks=[self.on_message], accept=["json"], prefetch_count=10)]

    def on_message(self, body: Any, message: Any) -> None:
        try:
            tables = handle(body, self.loop)
            log.info("platform.published handled", extra={"tables": tables})
            message.ack()
        except Exception:  # noqa: BLE001 (a malformed message goes to the dead letters, never loops)
            log.exception("platform.published could not be handled")
            message.reject(requeue=False)


def main() -> None:
    from app.core.logging.setup import configure_logging

    settings = get_settings()
    configure_logging(settings)
    with Connection(settings.rabbitmq_url.get_secret_value(), heartbeat=30) as connection:
        PublishedConsumer(connection).run()


if __name__ == "__main__":
    main()
