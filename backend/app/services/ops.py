from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.approval import Approval
from app.models.crm import CrmContact
from app.models.heartbeat_run import HeartbeatRun
from app.models.task import Task
from app.services.budget import spent_for_agent


def command_snapshot(db: Session, brand_id: UUID) -> dict:
    agents = list(db.scalars(select(Agent).where(Agent.brand_id == brand_id)).all())
    live_ids = {
        str(r.agent_id)
        for r in db.scalars(
            select(HeartbeatRun).where(HeartbeatRun.brand_id == brand_id, HeartbeatRun.status == "running")
        ).all()
    }
    ready_tasks = db.scalar(
        select(func.count())
        .select_from(Task)
        .where(Task.brand_id == brand_id, Task.status.in_(["ready", "checked_out", "blocked"]))
    ) or 0
    pending = db.scalar(
        select(func.count())
        .select_from(Approval)
        .where(Approval.brand_id == brand_id, Approval.status == "pending")
    ) or 0
    hot = db.scalar(
        select(func.count())
        .select_from(CrmContact)
        .where(CrmContact.brand_id == brand_id, CrmContact.temperature.in_(["hot", "star"]))
    ) or 0

    rows = []
    for agent in agents:
        inbox = db.scalar(
            select(func.count())
            .select_from(Task)
            .where(
                Task.assignee_agent_id == agent.id,
                Task.status.in_(["ready", "checked_out", "blocked", "review"]),
            )
        ) or 0
        last = db.scalar(
            select(HeartbeatRun)
            .where(HeartbeatRun.agent_id == agent.id)
            .order_by(HeartbeatRun.created_at.desc())
            .limit(1)
        )
        rows.append(
            {
                "id": agent.id,
                "role": agent.role,
                "title": agent.title,
                "status": agent.status,
                "model": agent.model,
                "last_heartbeat_at": agent.last_heartbeat_at,
                "inbox": int(inbox),
                "live": str(agent.id) in live_ids,
                "last_run_status": last.status if last else "",
                "last_summary": (last.result_summary or "")[:280] if last else "",
                "skill_count": len(agent.skill_slugs or []),
                "spent_usd": str(spent_for_agent(db, agent.id)),
            }
        )
    rows.sort(key=lambda r: (0 if r["role"] == "cmo" else 1, r["title"]))
    return {
        "live_runs": len(live_ids),
        "ready_tasks": int(ready_tasks),
        "pending_approvals": int(pending),
        "crm_hot": int(hot),
        "agents": rows,
    }
