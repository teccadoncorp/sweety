import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String, Text, func
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.db import Base


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    brand_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("brands.id"), index=True)
    role: Mapped[str] = mapped_column(String(64), index=True)
    title: Mapped[str] = mapped_column(String(200))
    reports_to_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=True
    )
    adapter: Mapped[str] = mapped_column(String(32), default="openrouter")
    model: Mapped[str] = mapped_column(String(128), default="openai/gpt-4o-mini")
    system_prompt: Mapped[str] = mapped_column(Text, default="")
    skill_slugs: Mapped[list[str]] = mapped_column(ARRAY(String), default=list)
    monthly_budget_usd: Mapped[Decimal] = mapped_column(Numeric(12, 4), default=Decimal("15.00"))
    status: Mapped[str] = mapped_column(String(32), default="active")
    heartbeat_interval_minutes: Mapped[int] = mapped_column(Integer, default=10)
    last_heartbeat_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    brand = relationship("Brand", back_populates="agents")
    reports_to = relationship("Agent", remote_side="Agent.id")
