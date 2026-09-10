from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.adapters import get_adapter
from app.adapters.base import RunContext, all_adapters
from app.core.config import get_settings
from app.models.agent import Agent
from app.models.brand import Brand
from app.models.campaign import Campaign
from app.models.heartbeat_run import HeartbeatRun
from app.models.task import Task
from app.models.usage import UsageEvent
from app.services.budget import budget_block_reason
from app.services.loop import brand_memory_block, ensure_launch_campaign
from app.services.sanitize import sanitize_json, strip_nuls
from app.services.skills import render_skill_block
from app.tools.agent_tools import TOOL_SPECS, ToolExecutor


def due_agents(db: Session) -> list[Agent]:
    now = datetime.now(UTC)
    agents = db.scalars(
        select(Agent)
        .join(Brand, Agent.brand_id == Brand.id)
        .where(Agent.status == "active", Brand.agents_paused.is_(False))
    ).all()
    due: list[Agent] = []
    for agent in agents:
        if agent.last_heartbeat_at is None:
            due.append(agent)
            continue
        interval = timedelta(minutes=max(1, agent.heartbeat_interval_minutes))
        if now - agent.last_heartbeat_at >= interval:
            due.append(agent)
    return due


def build_user_prompt(db: Session, brand: Brand, agent: Agent) -> str:
    campaigns = db.scalars(
        select(Campaign).where(
            Campaign.brand_id == brand.id,
            Campaign.status.in_(["draft", "awaiting_approval", "active"]),
        )
    ).all()
    inbox = db.scalars(
        select(Task).where(
            Task.brand_id == brand.id,
            Task.assignee_agent_id == agent.id,
            Task.status.in_(["ready", "checked_out", "blocked", "review"]),
        )
    ).all()
    campaign_lines = []
    for c in campaigns:
        campaign_lines.append(f"- {c.name} ({c.status}) id={c.id}\n  Goal: {c.goal}")
    task_lines = []
    for t in inbox:
        task_lines.append(f"- [{t.status}] {t.title} id={t.id} campaign={t.campaign_id}")

    return f"""You are on a scheduled heartbeat for {get_settings().app_name}, a marketing control plane.

Brand: {brand.name}
Mission: {brand.mission}
{brand_memory_block(brand)}

Your role: {agent.title} ({agent.role})

Open campaigns:
{chr(10).join(campaign_lines) or '- none — if you are the CMO, create_campaign from the mission NOW'}

Your inbox:
{chr(10).join(task_lines) or '- empty'}

Work only through tools. Check out a task before editing it. Post artifacts for briefs and copy. Request board approval for strategy and publish. Never auto-publish.

If you are the CMO and a draft campaign has no brief, write it this heartbeat with post_artifact(kind=campaign-brief). If you are copywriter or social and a first-post task is open, draft the actual post (kind=social-copy) and queue it with post_social. If you are strategist, post a dated content calendar.

You can run alongside teammates — do not wait for them. Use CRM tools when scoring leads or moving deals.

If your inbox is empty and you are the CMO, inspect draft campaigns and start a brief. If you are CRM/lifecycle, work the pipeline. If you cannot do useful work, say so briefly and stop.
"""


def run_heartbeat(db: Session, agent_id: UUID, trigger: str = "schedule") -> HeartbeatRun:
    agent = db.get(Agent, agent_id)
    if agent is None:
        raise ValueError("Agent not found")
    brand = db.get(Brand, agent.brand_id)
    if brand is None:
        raise ValueError("Brand not found")

    run = HeartbeatRun(
        brand_id=brand.id,
        agent_id=agent.id,
        trigger=trigger,
        adapter=agent.adapter,
        status="running",
    )
    db.add(run)
    db.flush()

    if getattr(brand, "agents_paused", False):
        run.status = "blocked"
        run.result_summary = "Kill switch is on — all agents paused"
        db.commit()
        return run

    if agent.status != "active":
        run.status = "blocked"
        run.result_summary = f"Agent is {agent.status}"
        db.commit()
        return run

    if agent.role == "cmo":
        ensure_launch_campaign(db, brand)

    blocked = budget_block_reason(db, brand, agent)
    if blocked:
        run.status = "blocked"
        run.result_summary = blocked
        agent.last_heartbeat_at = datetime.now(UTC)
        db.commit()
        return run

    skills_text = render_skill_block(agent.role, agent.skill_slugs or [])
    name = get_settings().app_name
    system_prompt = (
        f"{agent.system_prompt}\n\n"
        f"You operate inside {name}. Use tools: search the web, generate images, "
        "create HeyGen videos, call MCP tools, and queue social posts. "
        "Live posts to Reddit/X/LinkedIn/Facebook/Instagram go through board approval. "
        "Check list_connectors before posting. Never invent a successful publish.\n"
        f"{brand_memory_block(brand)}\n\n"
        f"{skills_text}"
    )
    user_prompt = build_user_prompt(db, brand, agent)
    run.prompt_snapshot = user_prompt

    adapter = get_adapter(agent.adapter)
    executor = ToolExecutor(db, brand, agent)
    result = adapter.execute(
        RunContext(
            brand_id=brand.id,
            agent_id=agent.id,
            run_id=run.id,
            model=agent.model,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            tools=TOOL_SPECS,
            execute_tool=executor,
        )
    )

    run.status = strip_nuls(result.status or "ok", 32)
    run.result_summary = strip_nuls(result.summary or "", 4000)
    run.prompt_snapshot = strip_nuls(user_prompt, 20_000)
    run.tokens_in = result.tokens_in
    run.tokens_out = result.tokens_out
    run.cost_usd = Decimal(str(result.cost_usd))
    run.trace = sanitize_json(result.trace)
    agent.last_heartbeat_at = datetime.now(UTC)

    if result.tokens_in or result.tokens_out or result.cost_usd:
        db.add(
            UsageEvent(
                brand_id=brand.id,
                agent_id=agent.id,
                run_id=run.id,
                tokens_in=result.tokens_in,
                tokens_out=result.tokens_out,
                cost_usd=Decimal(str(result.cost_usd)),
            )
        )
    try:
        db.commit()
        db.refresh(run)
        return run
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        failed = HeartbeatRun(
            brand_id=agent.brand_id,
            agent_id=agent.id,
            trigger=trigger,
            adapter=agent.adapter,
            status="error",
            result_summary=strip_nuls(f"Heartbeat persist failed: {exc}", 2000),
        )
        db.add(failed)
        db.commit()
        return failed


def adapter_health() -> list[dict]:
    # Import side-effect adapters
    from app.adapters import openrouter as _or  # noqa: F401
    from app.adapters import stub as _stub  # noqa: F401

    return [h.__dict__ for h in (a.diagnose() for a in all_adapters())]
