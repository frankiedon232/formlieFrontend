"""`formaly.request_logs`: every request in full (BACKEND-SPEC §8.1), partitioned by month.

Written in batches by the API (`database` sink) or the `logs` Celery queue (`celery` sink); never updated.
RLS is forced: a workspace may later read only its own rows; the writers insert any row (the record is built by
our middleware, not by the caller). `platform_reader` reads every column except the bodies.
"""

from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from sqlalchemy import BigInteger, Boolean, DateTime, Float, Index, Integer, PrimaryKeyConstraint, SmallInteger, String, Text, Uuid
from sqlalchemy.dialects.postgresql import ARRAY, INET, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db.base import Base
from app.core.ids import uuid7


class RequestLog(Base):
    __tablename__ = "request_logs"
    __table_args__ = (
        PrimaryKeyConstraint("id", "occurred_at"),
        Index("ix_request_logs_occurred_at", "occurred_at"),
        Index("ix_request_logs_tenant_occurred", "tenant_id", "occurred_at"),
        Index("ix_request_logs_client_ip", "client_ip", "occurred_at"),
        Index("ix_request_logs_trace_id", "trace_id"),
        {"postgresql_partition_by": "RANGE (occurred_at)"},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid, default=uuid7)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    trace_id: Mapped[str] = mapped_column(String(36), nullable=False)

    # Who
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    organisation_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    session_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)

    # What
    scheme: Mapped[str | None] = mapped_column(String(8))
    http_version: Mapped[str | None] = mapped_column(String(8))
    method: Mapped[str] = mapped_column(String(10), nullable=False)
    host: Mapped[str | None] = mapped_column(String(255))
    host_kind: Mapped[str | None] = mapped_column(String(10))
    subdomain: Mapped[str | None] = mapped_column(String(63))
    path: Mapped[str] = mapped_column(Text, nullable=False)
    route: Mapped[str | None] = mapped_column(Text)
    query: Mapped[dict[str, Any] | None] = mapped_column(JSONB)

    # Outcome
    status: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    duration_ms: Mapped[float | None] = mapped_column(Float)
    request_bytes: Mapped[int | None] = mapped_column(BigInteger)
    response_bytes: Mapped[int | None] = mapped_column(BigInteger)
    error_code: Mapped[str | None] = mapped_column(String(20))
    rate_limited: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    flags: Mapped[list[str] | None] = mapped_column(ARRAY(Text))

    # Where from
    client_ip: Mapped[str | None] = mapped_column(INET)
    peer_ip: Mapped[str | None] = mapped_column(INET)
    forwarded_for: Mapped[str | None] = mapped_column(Text)
    proxy_trusted: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")
    geo_source: Mapped[str | None] = mapped_column(String(12))  # maxmind, cloudflare, private, none
    continent: Mapped[str | None] = mapped_column(String(2))
    country: Mapped[str | None] = mapped_column(String(2))
    country_name: Mapped[str | None] = mapped_column(String(100))
    region: Mapped[str | None] = mapped_column(String(100))
    region_code: Mapped[str | None] = mapped_column(String(10))
    city: Mapped[str | None] = mapped_column(String(100))
    postal_code: Mapped[str | None] = mapped_column(String(20))
    timezone: Mapped[str | None] = mapped_column(String(64))
    latitude: Mapped[float | None] = mapped_column(Float)
    longitude: Mapped[float | None] = mapped_column(Float)
    accuracy_km: Mapped[int | None] = mapped_column(Integer)
    asn: Mapped[int | None] = mapped_column(BigInteger)
    as_org: Mapped[str | None] = mapped_column(String(255))

    # Client
    user_agent: Mapped[str | None] = mapped_column(Text)
    device_type: Mapped[str | None] = mapped_column(String(10))  # desktop, mobile, tablet, bot, other
    device_brand: Mapped[str | None] = mapped_column(String(100))
    device_model: Mapped[str | None] = mapped_column(String(100))
    os: Mapped[str | None] = mapped_column(String(100))
    os_version: Mapped[str | None] = mapped_column(String(50))
    browser: Mapped[str | None] = mapped_column(String(100))
    browser_version: Mapped[str | None] = mapped_column(String(50))
    is_bot: Mapped[bool | None] = mapped_column(Boolean)
    referer: Mapped[str | None] = mapped_column(Text)
    origin: Mapped[str | None] = mapped_column(Text)
    client_app: Mapped[str | None] = mapped_column(String(100))
    client_version: Mapped[str | None] = mapped_column(String(50))

    # Request in full (secrets masked)
    request_headers: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    request_content_type: Mapped[str | None] = mapped_column(String(255))
    request_body: Mapped[Any] = mapped_column(JSONB, nullable=True)
    request_body_text: Mapped[str | None] = mapped_column(Text)
    request_body_sha256: Mapped[str | None] = mapped_column(String(64))
    request_body_keys: Mapped[list[str] | None] = mapped_column(ARRAY(Text))
    request_body_fields: Mapped[int | None] = mapped_column(Integer)
    request_body_truncated: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")

    # Response
    response_headers: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    response_content_type: Mapped[str | None] = mapped_column(String(255))
    response_body: Mapped[Any] = mapped_column(JSONB, nullable=True)


COLUMNS = frozenset(c.name for c in RequestLog.__table__.columns)
BODY_COLUMNS = ("request_body", "request_body_text", "response_body")


class ErrorLog(Base):
    """`formaly.error_logs` (BACKEND-SPEC §8.3): every WARNING, ERROR and CRITICAL line of every process, loaded from
    the dated level files by `logs.ingest_error_files`, so they can be searched (platform admin). Insert-only, monthly
    partitions; the id comes from the file and line position, so loading a file twice adds nothing."""

    __tablename__ = "error_logs"
    __table_args__ = (
        PrimaryKeyConstraint("id", "occurred_at"),
        Index("ix_error_logs_level_occurred", "level", "occurred_at"),
        Index("ix_error_logs_tenant_occurred", "tenant_id", "occurred_at"),
        Index("ix_error_logs_trace_id", "trace_id"),
        Index("ix_error_logs_code", "error_code", "occurred_at"),
        {"postgresql_partition_by": "RANGE (occurred_at)"},
    )

    id: Mapped[uuid.UUID] = mapped_column(Uuid)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    level: Mapped[str] = mapped_column(String(10), nullable=False)
    logger: Mapped[str | None] = mapped_column(String(120))
    message: Mapped[str] = mapped_column(Text, nullable=False)
    error_code: Mapped[str | None] = mapped_column(String(20))
    security_event: Mapped[str | None] = mapped_column(String(60))
    trace_id: Mapped[str | None] = mapped_column(String(36))
    tenant_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    organisation_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    user_id: Mapped[uuid.UUID | None] = mapped_column(Uuid)
    method: Mapped[str | None] = mapped_column(String(10))
    path: Mapped[str | None] = mapped_column(String(500))
    stack: Mapped[str | None] = mapped_column(Text)  # server side only, never in an answer
    context: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)  # every other field of the line (masked)
    environment: Mapped[str | None] = mapped_column(String(20))
    release: Mapped[str | None] = mapped_column(String(40))
    source: Mapped[str] = mapped_column(String(200), nullable=False)  # level/day file and byte position


class LogIngestOffset(Base):
    """How far `logs.ingest_error_files` has read each level file."""

    __tablename__ = "log_ingest_offsets"

    file: Mapped[str] = mapped_column(String(200), primary_key=True)
    offset: Mapped[int] = mapped_column(BigInteger, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
