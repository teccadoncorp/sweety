from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.brand import Brand
from app.models.usage import UsageEvent


def month_start() -> datetime:
    now = datetime.now(UTC)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def spent_for_brand(db: Session, brand_id: UUID) -> Decimal:
    value = db.scalar(
        select(func.coalesce(func.sum(UsageEvent.cost_usd), 0)).where(
            UsageEvent.brand_id == brand_id,
            UsageEvent.created_at >= month_start(),
        )
    )
    return Decimal(value or 0)


def spent_for_agent(db: Session, agent_id: UUID) -> Decimal:
    value = db.scalar(
        select(func.coalesce(func.sum(UsageEvent.cost_usd), 0)).where(
            UsageEvent.agent_id == agent_id,
            UsageEvent.created_at >= month_start(),
        )
    )
    return Decimal(value or 0)


def spent_for_campaign(db: Session, campaign_id: UUID) -> Decimal:
    value = db.scalar(
        select(func.coalesce(func.sum(UsageEvent.cost_usd), 0)).where(
            UsageEvent.campaign_id == campaign_id,
            UsageEvent.created_at >= month_start(),
        )
    )
    return Decimal(value or 0)


def budget_block_reason(db: Session, brand: Brand, agent: Agent) -> str | None:
    brand_spent = spent_for_brand(db, brand.id)
    if brand_spent >= Decimal(brand.monthly_budget_usd):
        return f"Brand monthly budget exhausted ({brand_spent} / {brand.monthly_budget_usd} USD)"
    agent_spent = spent_for_agent(db, agent.id)
    if agent_spent >= Decimal(agent.monthly_budget_usd):
        return f"Agent monthly budget exhausted ({agent_spent} / {agent.monthly_budget_usd} USD)"
    return None
