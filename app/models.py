from datetime import datetime, timezone
from sqlalchemy import String, Integer, Float, DateTime, JSON, Text, Index
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base

class RequestAudit(Base):
    __tablename__ = 'request_audit'
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    request_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    trace_id: Mapped[str] = mapped_column(String(64), index=True)
    provider: Mapped[str | None] = mapped_column(String(16), nullable=True)
    status: Mapped[str] = mapped_column(String(24), index=True)
    http_status: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration_ms: Mapped[float | None] = mapped_column(Float, nullable=True)
    request_payload: Mapped[dict] = mapped_column(JSON)
    response_payload: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True)

Index('ix_request_audit_created_provider', RequestAudit.created_at, RequestAudit.provider)
