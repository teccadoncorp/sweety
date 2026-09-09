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


def spent_map_for_brands(db: Session, brand_ids: list[UUID]) -> dict[UUID, Decimal]:
    if not brand_ids:
        return {}
    rows = db.execute(
        select(UsageEvent.brand_id, func.coalesce(func.sum(UsageEvent.cost_usd), 0))
        .where(UsageEvent.brand_id.in_(brand_ids), UsageEvent.created_at >= month_start())
        .group_by(UsageEvent.brand_id)
    ).all()
    out = {bid: Decimal("0") for bid in brand_ids}
    for bid, value in rows:
        if bid is not None:
            out[bid] = Decimal(value or 0)
    return out


def spent_map_for_agents(db: Session, agent_ids: list[UUID]) -> dict[UUID, Decimal]:
    if not agent_ids:
        return {}
    rows = db.execute(
        select(UsageEvent.agent_id, func.coalesce(func.sum(UsageEvent.cost_usd), 0))
        .where(UsageEvent.agent_id.in_(agent_ids), UsageEvent.created_at >= month_start())
        .group_by(UsageEvent.agent_id)
    ).all()
    out = {aid: Decimal("0") for aid in agent_ids}
    for aid, value in rows:
        if aid is not None:
            out[aid] = Decimal(value or 0)
    return out


def spent_map_for_campaigns(db: Session, campaign_ids: list[UUID]) -> dict[UUID, Decimal]:
    if not campaign_ids:
        return {}
    rows = db.execute(
        select(UsageEvent.campaign_id, func.coalesce(func.sum(UsageEvent.cost_usd), 0))
        .where(UsageEvent.campaign_id.in_(campaign_ids), UsageEvent.created_at >= month_start())
        .group_by(UsageEvent.campaign_id)
    ).all()
    out = {cid: Decimal("0") for cid in campaign_ids}
    for cid, value in rows:
        if cid is not None:
            out[cid] = Decimal(value or 0)
    return out


def budget_block_reason(db: Session, brand: Brand, agent: Agent) -> str | None:
    brand_spent = spent_for_brand(db, brand.id)
    if brand_spent >= Decimal(brand.monthly_budget_usd):
        return f"Brand monthly budget exhausted ({brand_spent} / {brand.monthly_budget_usd} USD)"
    agent_spent = spent_for_agent(db, agent.id)
    if agent_spent >= Decimal(agent.monthly_budget_usd):
        return f"Agent monthly budget exhausted ({agent_spent} / {agent.monthly_budget_usd} USD)"
    return None
