from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.agent import Agent
from app.models.campaign import Campaign
from app.models.task import Task
from app.models.user import User
from app.schemas.common import CampaignIn, CampaignOut, CampaignUpdate
from app.schemas.crm import SwarmQueued
from app.services.access import get_brand_for_user, get_campaign_in_brand
from app.services.budget import spent_for_campaign, spent_map_for_campaigns
from app.services.loop import queue_launch_heartbeats, spawn_launch_campaign
from app.workers.heartbeat import run_agent_heartbeat

router = APIRouter(prefix="/brands/{brand_id}/campaigns", tags=["campaigns"])


def _out(db: Session, campaign: Campaign, spent=None) -> CampaignOut:
    data = CampaignOut.model_validate(campaign)
    data.spent_usd = spent if spent is not None else spent_for_campaign(db, campaign.id)
    return data


@router.get("", response_model=list[CampaignOut])
def list_campaigns(
    brand_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[CampaignOut]:
    get_brand_for_user(db, brand_id, user.id)
    rows = list(
        db.scalars(
            select(Campaign).where(Campaign.brand_id == brand_id).order_by(Campaign.created_at.desc())
        ).all()
    )
    spent = spent_map_for_campaigns(db, [c.id for c in rows])
    return [_out(db, c, spent.get(c.id)) for c in rows]


@router.post("", response_model=CampaignOut)
def create_campaign(
    brand_id: UUID,
    payload: CampaignIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CampaignOut:
    brand = get_brand_for_user(db, brand_id, user.id)
    campaign, wake_ids = spawn_launch_campaign(
        db,
        brand,
        name=payload.name,
        goal=payload.goal,
        budget_cap_usd=payload.budget_cap_usd,
    )
    if payload.brief:
        campaign.brief = payload.brief
    db.commit()
    db.refresh(campaign)
    if wake_ids and not brand.agents_paused:
        queue_launch_heartbeats(wake_ids, "campaign")
    return _out(db, campaign)


@router.get("/{campaign_id}", response_model=CampaignOut)
def get_campaign(
    brand_id: UUID,
    campaign_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CampaignOut:
    get_brand_for_user(db, brand_id, user.id)
    return _out(db, get_campaign_in_brand(db, brand_id, campaign_id))


@router.patch("/{campaign_id}", response_model=CampaignOut)
def update_campaign(
    brand_id: UUID,
    campaign_id: UUID,
    payload: CampaignUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CampaignOut:
    get_brand_for_user(db, brand_id, user.id)
    campaign = get_campaign_in_brand(db, brand_id, campaign_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(campaign, key, value)
    db.commit()
    db.refresh(campaign)
    return _out(db, campaign)


@router.post("/{campaign_id}/approve", response_model=CampaignOut)
def approve_campaign(
    brand_id: UUID,
    campaign_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CampaignOut:
    get_brand_for_user(db, brand_id, user.id)
    campaign = get_campaign_in_brand(db, brand_id, campaign_id)
    campaign.status = "active"
    db.commit()
    db.refresh(campaign)
    return _out(db, campaign)


@router.post("/{campaign_id}/pause", response_model=CampaignOut)
def pause_campaign(
    brand_id: UUID,
    campaign_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CampaignOut:
    get_brand_for_user(db, brand_id, user.id)
    campaign = get_campaign_in_brand(db, brand_id, campaign_id)
    campaign.status = "paused"
    db.commit()
    db.refresh(campaign)
    return _out(db, campaign)


@router.post("/{campaign_id}/run-team", response_model=SwarmQueued)
def run_campaign_team(
    brand_id: UUID,
    campaign_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> SwarmQueued:
    brand = get_brand_for_user(db, brand_id, user.id)
    if brand.agents_paused:
        return SwarmQueued(queued=0, agent_ids=[], reason="Kill switch is on")
    get_campaign_in_brand(db, brand_id, campaign_id)
    tasks = db.scalars(
        select(Task).where(
            Task.campaign_id == campaign_id,
            Task.status.in_(["ready", "checked_out", "blocked", "review", "backlog"]),
        )
    ).all()
    ids = {t.assignee_agent_id for t in tasks if t.assignee_agent_id}
    if not ids:
        cmo = db.scalar(select(Agent).where(Agent.brand_id == brand_id, Agent.role == "cmo"))
        if cmo:
            ids.add(cmo.id)
    queued = []
    for agent_id in ids:
        agent = db.get(Agent, agent_id)
        if agent is None or agent.status != "active":
            continue
        run_agent_heartbeat.delay(str(agent.id), "campaign")
        queued.append(agent.id)
    return SwarmQueued(queued=len(queued), agent_ids=queued, reason="Campaign team queued")
