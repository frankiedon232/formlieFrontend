"""Publishing to the RabbitMQ topic exchange `formalie.events` (routing key = event type, `domain.action`).

Only the outbox relay calls this; services call `record_event()` so an event exists only if its change does.
Messages are persistent, carry the event id as message_id (consumers deduplicate) and use publisher confirms.
"""

from __future__ import annotations

from kombu import Connection, Exchange, Producer

from app.core.config import get_settings
from app.core.events.schemas import EventEnvelope


def events_exchange() -> Exchange:
    return Exchange(get_settings().events_exchange, type="topic", durable=True)


class EventBus:
    def __init__(self, url: str | None = None) -> None:
        self.url = url or get_settings().rabbitmq_url.get_secret_value()
        self.exchange = events_exchange()
        self._connection: Connection | None = None
        self._producer: Producer | None = None

    def _ensure(self) -> Producer:
        if self._producer is None:
            self._connection = Connection(self.url, transport_options={"confirm_publish": True}, connect_timeout=5)
            self._producer = Producer(self._connection.channel(), exchange=self.exchange, serializer="json")
            self.exchange(self._producer.channel).declare()
        return self._producer

    def publish(self, event: EventEnvelope) -> None:
        producer = self._ensure()
        producer.publish(
            event.wire(),  # PLATFORM-ADMIN-INTEGRATION §4: ids, counts, plans, timings; never personal data
            routing_key=event.type,
            delivery_mode=2,
            message_id=str(event.event_id),
            # No content_type here: with one, kombu skips its serializer and sends the dict as is.
            retry=True,
            retry_policy={"max_retries": 3, "interval_start": 0.2, "interval_step": 0.5},
        )

    def close(self) -> None:
        if self._connection is not None:
            self._connection.release()
        self._connection = None
        self._producer = None
