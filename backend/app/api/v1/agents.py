from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.agent import Agent
from app.models.user import User
from app.schemas.common import AgentIn, AgentOut, AgentUpdate, HeartbeatQueued
from app.schemas.crm import SwarmQueued
from app.schemas.ops import ModelBroadcastIn, OrgPresetOut
from app.services.access import get_agent_in_brand, get_brand_for_user
from app.services.budget import spent_for_agent, spent_map_for_agents
from app.services.loop import ensure_launch_campaign
from app.services.seed import DEFAULT_ORG, ensure_default_org
from app.workers.heartbeat import run_agent_heartbeat

router = APIRouter(prefix="/brands/{brand_id}/agents", tags=["agents"])


def _out(db: Session, agent: Agent, spent=None) -> AgentOut:
    data = AgentOut.model_validate(agent)
    data.spent_usd = spent if spent is not None else spent_for_agent(db, agent.id)
    return data


def _many(db: Session, rows: list[Agent]) -> list[AgentOut]:
    spent = spent_map_for_agents(db, [a.id for a in rows])
    return [_out(db, a, spent.get(a.id)) for a in rows]


@router.get("", response_model=list[AgentOut])
def list_agents(
    brand_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[AgentOut]:
    get_brand_for_user(db, brand_id, user.id)
    rows = list(db.scalars(select(Agent).where(Agent.brand_id == brand_id)).all())
    return _many(db, rows)


@router.post("/expand", response_model=list[AgentOut])
def expand_org(
    brand_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[AgentOut]:
    brand = get_brand_for_user(db, brand_id, user.id)
    agents = ensure_default_org(db, brand)
    ensure_launch_campaign(db, brand)
    db.commit()
    return _many(db, agents)


@router.post("/wake-all", response_model=SwarmQueued)
def wake_all_agents(
    brand_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> SwarmQueued:
    brand = get_brand_for_user(db, brand_id, user.id)
    if brand.agents_paused:
        return SwarmQueued(queued=0, agent_ids=[], reason="Kill switch is on")
    ensure_launch_campaign(db, brand)
    db.commit()
    rows = db.scalars(select(Agent).where(Agent.brand_id == brand_id, Agent.status == "active")).all()
    for agent in rows:
        run_agent_heartbeat.delay(str(agent.id), "swarm")
    return SwarmQueued(queued=len(rows), agent_ids=[a.id for a in rows])


@router.post("/apply-presets", response_model=list[AgentOut])
def apply_presets(
    brand_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[AgentOut]:
    get_brand_for_user(db, brand_id, user.id)
    wanted = {spec["role"]: spec for spec in DEFAULT_ORG}
    rows = db.scalars(select(Agent).where(Agent.brand_id == brand_id)).all()
    for agent in rows:
        spec = wanted.get(agent.role)
        if not spec:
            continue
        agent.skill_slugs = list(spec["skills"])
        if spec.get("prompt"):
            agent.system_prompt = spec["prompt"]
    db.commit()
    return _many(db, rows)


@router.post("/broadcast-model", response_model=list[AgentOut])
def broadcast_model(
    brand_id: UUID,
    payload: ModelBroadcastIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[AgentOut]:
    get_brand_for_user(db, brand_id, user.id)
    model = payload.model.strip()
    rows = db.scalars(select(Agent).where(Agent.brand_id == brand_id)).all()
    if model:
        for agent in rows:
            agent.model = model
        db.commit()
    return _many(db, rows)


@router.get("/presets", response_model=list[OrgPresetOut])
def list_presets(
    brand_id: UUID, user: User = Depends(get_current_user)
) -> list[OrgPresetOut]:
    _ = brand_id
    _ = user
    return [
        OrgPresetOut(role=spec["role"], title=spec["title"], skills=spec["skills"], prompt=spec["prompt"])
        for spec in DEFAULT_ORG
    ]


@router.post("", response_model=AgentOut)
def create_agent(
    brand_id: UUID,
    payload: AgentIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AgentOut:
    get_brand_for_user(db, brand_id, user.id)
    agent = Agent(brand_id=brand_id, **payload.model_dump())
    db.add(agent)
    db.commit()
    db.refresh(agent)
    return _out(db, agent)


@router.get("/{agent_id}", response_model=AgentOut)
def get_agent(
    brand_id: UUID,
    agent_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AgentOut:
    get_brand_for_user(db, brand_id, user.id)
    return _out(db, get_agent_in_brand(db, brand_id, agent_id))


@router.patch("/{agent_id}", response_model=AgentOut)
def update_agent(
    brand_id: UUID,
    agent_id: UUID,
    payload: AgentUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AgentOut:
    get_brand_for_user(db, brand_id, user.id)
    agent = get_agent_in_brand(db, brand_id, agent_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(agent, key, value)
    db.commit()
    db.refresh(agent)
    return _out(db, agent)


@router.post("/{agent_id}/pause", response_model=AgentOut)
def pause_agent(
    brand_id: UUID,
    agent_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AgentOut:
    get_brand_for_user(db, brand_id, user.id)
    agent = get_agent_in_brand(db, brand_id, agent_id)
    agent.status = "paused"
    db.commit()
    db.refresh(agent)
    return _out(db, agent)


@router.post("/{agent_id}/resume", response_model=AgentOut)
def resume_agent(
    brand_id: UUID,
    agent_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AgentOut:
    get_brand_for_user(db, brand_id, user.id)
    agent = get_agent_in_brand(db, brand_id, agent_id)
    if agent.status != "terminated":
        agent.status = "active"
    db.commit()
    db.refresh(agent)
    return _out(db, agent)


@router.post("/{agent_id}/terminate", response_model=AgentOut)
def terminate_agent(
    brand_id: UUID,
    agent_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> AgentOut:
    get_brand_for_user(db, brand_id, user.id)
    agent = get_agent_in_brand(db, brand_id, agent_id)
    agent.status = "terminated"
    db.commit()
    db.refresh(agent)
    return _out(db, agent)


@router.post("/{agent_id}/heartbeat", response_model=HeartbeatQueued)
def queue_heartbeat(
    brand_id: UUID,
    agent_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> HeartbeatQueued:
    brand = get_brand_for_user(db, brand_id, user.id)
    agent = get_agent_in_brand(db, brand_id, agent_id)
    if brand.agents_paused:
        return HeartbeatQueued(queued=False, reason="Kill switch is on")
    run_agent_heartbeat.delay(str(agent.id), "manual")
    return HeartbeatQueued(queued=True, reason="Heartbeat queued")
