from __future__ import annotations

from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.approval import Approval
from app.models.brand import Brand
from app.models.campaign import Campaign
from app.models.content import ContentItem
from app.models.notification import Notification
from app.models.task import Task
from app.services.sanitize import strip_nuls

CONTENT_KINDS = {
    "social-copy",
    "blog",
    "email",
    "ad-copy",
    "newsletter",
    "post",
}
BRIEF_KINDS = {"brief", "campaign-brief"}
SOCIAL_CHANNELS = {"linkedin", "instagram", "facebook", "twitter", "x", "reddit"}
KIND_CHANNEL = {
    "social-copy": "linkedin",
    "social-post": "linkedin",
    "post": "linkedin",
    "blog": "blog",
    "email": "email",
    "ad-copy": "ads",
    "newsletter": "email",
}


def brand_memory_block(brand: Brand) -> str:
    return (
        f"Brand memory (follow on every draft):\n"
        f"- Voice / tone: {brand.voice_notes or 'not set'}\n"
        f"- Audience: {brand.audience or 'not set'}\n"
        f"- Do's / don'ts: {brand.guidelines or 'not set'}"
    )


def notify(
    db: Session,
    brand_id: UUID,
    *,
    kind: str,
    title: str,
    body: str = "",
    href: str = "",
    subject_type: str = "",
    subject_id: UUID | None = None,
) -> Notification:
    row = Notification(
        brand_id=brand_id,
        kind=kind,
        title=strip_nuls(title, 300),
        body=strip_nuls(body, 4000),
        href=href,
        subject_type=subject_type,
        subject_id=subject_id,
    )
    db.add(row)
    db.flush()
    return row


def _agent(db: Session, brand_id: UUID, role: str) -> Agent | None:
    return db.scalar(select(Agent).where(Agent.brand_id == brand_id, Agent.role == role))


def _first_agent(db: Session, brand_id: UUID, roles: list[str]) -> Agent | None:
    for role in roles:
        agent = _agent(db, brand_id, role)
        if agent:
            return agent
    return None


def campaign_name_from_mission(brand: Brand) -> str:
    mission = (brand.mission or "").strip()
    if not mission:
        return f"{brand.name} — first campaign"
    first = mission.split(".")[0].strip()
    return (first[:80] or f"{brand.name} — first campaign").rstrip(" ,;:-")


def spawn_launch_campaign(
    db: Session,
    brand: Brand,
    *,
    name: str | None = None,
    goal: str | None = None,
    budget_cap_usd=None,
) -> tuple[Campaign, list[UUID]]:
    campaign = Campaign(
        brand_id=brand.id,
        name=strip_nuls(name or campaign_name_from_mission(brand), 200),
        goal=strip_nuls(goal or brand.mission or f"Launch {brand.name} from the stated mission.", 8000),
        brief="",
        status="draft",
    )
    if budget_cap_usd is not None:
        campaign.budget_cap_usd = budget_cap_usd
    db.add(campaign)
    db.flush()
    wake_ids = attach_launch_tasks(db, brand, campaign)
    return campaign, wake_ids


def attach_launch_tasks(db: Session, brand: Brand, campaign: Campaign) -> list[UUID]:
    cmo = _agent(db, brand.id, "cmo")
    copywriter = _first_agent(db, brand.id, ["copywriter", "social"])
    strategist = _first_agent(db, brand.id, ["strategist", "cmo"])
    wake: list[UUID] = []

    if cmo and not _open_task(db, campaign.id, cmo.id, "campaign brief"):
        db.add(
            Task(
                brand_id=brand.id,
                campaign_id=campaign.id,
                assignee_agent_id=cmo.id,
                title="Write campaign brief and task tree",
                description=(
                    f"This campaign was opened automatically from the brand mission.\n\n"
                    f"Mission: {brand.mission or '(not set)'}\n\n"
                    "Checkout this task. Write a real campaign brief (positioning, audience, channel mix, first 2 weeks). "
                    "Save it with post_artifact(kind=campaign-brief). Request board approval. "
                    "Delegate a first-post task to the copywriter if one is not already open."
                ),
                status="ready",
                priority=1,
            )
        )
        wake.append(cmo.id)

    ensure_content_followup(db, brand, campaign)
    if copywriter:
        wake.append(copywriter.id)

    if strategist and not _open_task(db, campaign.id, strategist.id, "content plan"):
        db.add(
            Task(
                brand_id=brand.id,
                campaign_id=campaign.id,
                assignee_agent_id=strategist.id,
                title="Turn the mission into a 2-week content plan",
                description=(
                    "Produce a dated content calendar for the next 14 days. "
                    "Save it with post_artifact(kind=content-calendar). "
                    "Each item should name the channel, the hook, and the CTA."
                ),
                status="ready",
                priority=2,
            )
        )
        if strategist.id not in wake:
            wake.append(strategist.id)

    db.flush()
    return list(dict.fromkeys(wake))


def _open_task(db: Session, campaign_id: UUID, agent_id: UUID, needle: str) -> Task | None:
    rows = db.scalars(
        select(Task).where(Task.campaign_id == campaign_id, Task.assignee_agent_id == agent_id)
    ).all()
    needle = needle.lower()
    for task in rows:
        hay = f"{task.title} {task.description}".lower()
        if needle in hay:
            return task
    return None


def ensure_content_followup(db: Session, brand: Brand, campaign: Campaign) -> Task | None:
    copywriter = _first_agent(db, brand.id, ["copywriter", "social"])
    if copywriter is None:
        return None
    existing = _open_task(db, campaign.id, copywriter.id, "first")
    if existing is None:
        existing = _open_task(db, campaign.id, copywriter.id, "linkedin")
    if existing is not None:
        if existing.status in ("done", "cancelled"):
            return existing
        return existing
    any_open = db.scalar(
        select(Task).where(
            Task.campaign_id == campaign.id,
            Task.assignee_agent_id == copywriter.id,
            Task.status.in_(["ready", "checked_out", "blocked", "review", "backlog"]),
        )
    )
    if any_open:
        return any_open
    task = Task(
        brand_id=brand.id,
        campaign_id=campaign.id,
        assignee_agent_id=copywriter.id,
        title="Draft the first LinkedIn post",
        description=(
            "Checkout this task. Write an actual LinkedIn post for this campaign — a real post a human could publish, "
            "not a plan. Follow brand memory. Then: "
            "1) post_artifact(kind=social-copy, title, content=the post). "
            "2) post_social(platform=linkedin, text=the same copy). "
            "Stop once the board has a pending approval. Never claim it went live."
        ),
        status="ready",
        priority=1,
    )
    db.add(task)
    db.flush()
    return task


def ensure_launch_campaign(db: Session, brand: Brand) -> Campaign | None:
    campaign = db.scalar(
        select(Campaign).where(Campaign.brand_id == brand.id).order_by(Campaign.created_at.asc())
    )
    if campaign is None:
        campaign, _ = spawn_launch_campaign(db, brand)
        return campaign
    if campaign.status in ("draft", "awaiting_approval", "active"):
        attach_launch_tasks(db, brand, campaign)
    return campaign


def queue_launch_heartbeats(agent_ids: list[UUID], trigger: str = "launch") -> None:
    from app.workers.heartbeat import run_agent_heartbeat

    for agent_id in agent_ids:
        run_agent_heartbeat.delay(str(agent_id), trigger)


def queue_draft_for_approval(
    db: Session,
    brand: Brand,
    agent: Agent,
    *,
    title: str,
    text: str,
    kind: str,
    channel: str,
    task_id: UUID | None = None,
    campaign_id: UUID | None = None,
    artifact_id: UUID | None = None,
    extra: dict[str, Any] | None = None,
) -> tuple[ContentItem, Approval]:
    channel = (channel or KIND_CHANNEL.get(kind, "linkedin")).lower().strip()
    if channel == "x":
        channel = "twitter"
    payload = {
        "summary": f"{kind} for {channel}: {title}"[:180],
        "text": text,
        "title": title,
        "platform": channel,
        "channel": channel,
        "kind": kind,
        **(extra or {}),
    }
    approval = None
    item = None
    if task_id:
        approval = db.scalar(
            select(Approval).where(
                Approval.brand_id == brand.id,
                Approval.status == "pending",
                Approval.subject_id == task_id,
                Approval.kind.in_(["content", "publish"]),
            )
        )
        item = db.scalar(
            select(ContentItem).where(
                ContentItem.brand_id == brand.id,
                ContentItem.task_id == task_id,
                ContentItem.status.in_(["draft", "awaiting_approval"]),
            )
        )
    if item is None:
        item = ContentItem(
            brand_id=brand.id,
            campaign_id=campaign_id,
            task_id=task_id,
            artifact_id=artifact_id,
            created_by_agent_id=agent.id,
            kind=kind,
            channel=channel,
            title=strip_nuls(title, 300),
            body=strip_nuls(text, 100_000),
            status="awaiting_approval",
            extra=extra or {},
        )
        db.add(item)
        db.flush()
    else:
        item.kind = kind
        item.channel = channel
        item.title = strip_nuls(title, 300)
        item.body = strip_nuls(text, 100_000)
        item.status = "awaiting_approval"
        if artifact_id:
            item.artifact_id = artifact_id
        if extra:
            item.extra = {**(item.extra or {}), **extra}
        db.add(item)

    payload["content_item_id"] = str(item.id)
    approval_kind = "publish" if channel in SOCIAL_CHANNELS else "content"
    if approval is None:
        approval = Approval(
            brand_id=brand.id,
            kind=approval_kind,
            status="pending",
            subject_type="task" if task_id else "content",
            subject_id=task_id or item.id,
            requested_by_agent_id=agent.id,
            payload=payload,
        )
        db.add(approval)
        db.flush()
        notify(
            db,
            brand.id,
            kind="approval",
            title=f"Needs approval: {title or kind}",
            body=(text or "")[:400],
            href=f"/brands/{brand.id}/approvals",
            subject_type="approval",
            subject_id=approval.id,
        )
    else:
        merged = dict(approval.payload or {})
        merged.update(payload)
        approval.kind = approval_kind
        approval.payload = merged
        db.add(approval)

    item.approval_id = approval.id
    db.add(item)
    db.flush()
    return item, approval


def apply_content_decision(
    db: Session,
    approval: Approval,
    *,
    status: str,
    text: str | None = None,
    title: str | None = None,
    scheduled_for: datetime | None = None,
) -> dict[str, Any] | None:
    payload = dict(approval.payload or {})
    if text is not None:
        payload["text"] = text
    if title is not None:
        payload["title"] = title
    item = _content_for_approval(db, approval, payload)
    if item is None and (payload.get("text") or payload.get("platform")):
        item = ContentItem(
            brand_id=approval.brand_id,
            campaign_id=None,
            task_id=approval.subject_id if approval.subject_type == "task" else None,
            approval_id=approval.id,
            created_by_agent_id=approval.requested_by_agent_id,
            kind=payload.get("kind") or "social-copy",
            channel=(payload.get("platform") or payload.get("channel") or "linkedin"),
            title=strip_nuls(payload.get("title") or payload.get("summary") or "Draft", 300),
            body=strip_nuls(payload.get("text") or "", 100_000),
            status="awaiting_approval",
            extra={},
        )
        db.add(item)
        db.flush()
        payload["content_item_id"] = str(item.id)

    if item is not None:
        if text is not None:
            item.body = strip_nuls(text, 100_000)
        if title is not None:
            item.title = strip_nuls(title, 300)
        if scheduled_for is not None:
            item.scheduled_for = scheduled_for
            payload["scheduled_for"] = scheduled_for.isoformat()
        item.approval_id = approval.id
        if status == "rejected":
            item.status = "rejected"
        elif scheduled_for and scheduled_for > datetime.now(UTC):
            item.status = "scheduled"
        else:
            item.status = "approved"
        db.add(item)

    approval.payload = payload
    db.add(approval)
    _mark_related_notifications_read(db, approval)

    if status != "approved":
        return None
    if item is not None and item.status == "scheduled":
        return {"ok": True, "scheduled": True, "content_item_id": str(item.id)}
    return publish_content_item(db, item, payload) if item is not None else None


def publish_content_item(
    db: Session, item: ContentItem | None, payload: dict[str, Any] | None = None
) -> dict[str, Any] | None:
    if item is None:
        return None
    payload = payload or dict(item.extra or {})
    platform = (payload.get("platform") or item.channel or "").lower()
    text = payload.get("text") or item.body
    if platform in SOCIAL_CHANNELS and text:
        from app.services.publish import execute_social_payload

        result = execute_social_payload(
            db,
            item.brand_id,
            {
                "platform": platform,
                "text": text,
                "title": payload.get("title") or item.title,
                "image_url": payload.get("image_url"),
                "subreddit": payload.get("subreddit"),
                "caption": payload.get("caption"),
            },
        )
        extra = dict(item.extra or {})
        extra["publish_result"] = result
        item.extra = extra
        if result.get("ok"):
            item.status = "published"
            item.published_at = datetime.now(UTC)
        else:
            item.status = "awaiting_approval"
        db.add(item)
        if item.approval_id:
            approval = db.get(Approval, item.approval_id)
            if approval:
                merged = dict(approval.payload or {})
                merged["publish_result"] = result
                approval.payload = merged
                db.add(approval)
        return result
    item.status = "published"
    item.published_at = datetime.now(UTC)
    db.add(item)
    return {"ok": True, "published": True, "channel": item.channel}


def _content_for_approval(db: Session, approval: Approval, payload: dict[str, Any]) -> ContentItem | None:
    raw = payload.get("content_item_id")
    if raw:
        try:
            item = db.get(ContentItem, UUID(str(raw)))
            if item and item.brand_id == approval.brand_id:
                return item
        except ValueError:
            pass
    if approval.id:
        item = db.scalar(select(ContentItem).where(ContentItem.approval_id == approval.id))
        if item:
            return item
    if approval.subject_type == "task" and approval.subject_id:
        return db.scalar(
            select(ContentItem)
            .where(ContentItem.task_id == approval.subject_id)
            .order_by(ContentItem.created_at.desc())
        )
    return None


def _mark_related_notifications_read(db: Session, approval: Approval) -> None:
    rows = db.scalars(
        select(Notification).where(
            Notification.brand_id == approval.brand_id,
            Notification.read_at.is_(None),
            Notification.subject_id == approval.id,
        )
    ).all()
    now = datetime.now(UTC)
    for row in rows:
        row.read_at = now
        db.add(row)


def publish_due_content(db: Session) -> int:
    now = datetime.now(UTC)
    rows = db.scalars(
        select(ContentItem).where(
            ContentItem.status == "scheduled",
            ContentItem.scheduled_for.is_not(None),
            ContentItem.scheduled_for <= now,
        )
    ).all()
    count = 0
    for item in rows:
        payload = dict(item.extra or {})
        payload.setdefault("platform", item.channel)
        payload.setdefault("text", item.body)
        payload.setdefault("title", item.title)
        publish_content_item(db, item, payload)
        count += 1
    if count:
        db.commit()
    return count


def reporting_counts(db: Session, brand_id: UUID) -> dict[str, int]:
    rows = db.execute(
        select(ContentItem.status, func.count())
        .where(ContentItem.brand_id == brand_id)
        .group_by(ContentItem.status)
    ).all()
    counts = {status: int(n) for status, n in rows}
    pending = db.scalar(
        select(func.count())
        .select_from(Approval)
        .where(Approval.brand_id == brand_id, Approval.status == "pending")
    ) or 0
    rejected = db.scalar(
        select(func.count())
        .select_from(Approval)
        .where(Approval.brand_id == brand_id, Approval.status == "rejected")
    ) or 0
    return {
        "draft": counts.get("draft", 0),
        "awaiting_approval": counts.get("awaiting_approval", 0) + int(pending),
        "scheduled": counts.get("scheduled", 0),
        "published": counts.get("published", 0),
        "rejected": counts.get("rejected", 0) + int(rejected),
        "created": sum(counts.values()),
    }
