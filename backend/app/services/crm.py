from datetime import UTC, datetime, timedelta
from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.crm import (
    CONTACT_TEMPS,
    DEAL_STAGES,
    STAGE_PROBABILITY,
    CrmAccount,
    CrmActivity,
    CrmContact,
    CrmDeal,
)


def apply_stage(deal: CrmDeal, stage: str, lost_reason: str = "") -> None:
    if stage not in DEAL_STAGES:
        raise ValueError("Invalid stage")
    deal.stage = stage
    deal.probability = STAGE_PROBABILITY.get(stage, deal.probability)
    if stage == "lost":
        deal.lost_reason = lost_reason or deal.lost_reason
    elif stage == "won":
        deal.lost_reason = ""


def log_activity(
    db: Session,
    brand_id: UUID,
    *,
    kind: str,
    title: str,
    body: str,
    contact_id: UUID | None = None,
    account_id: UUID | None = None,
    deal_id: UUID | None = None,
    agent_id: UUID | None = None,
    due_at: datetime | None = None,
) -> CrmActivity:
    row = CrmActivity(
        brand_id=brand_id,
        kind=kind,
        title=title[:240],
        body=body,
        contact_id=contact_id,
        account_id=account_id,
        deal_id=deal_id,
        agent_id=agent_id,
        due_at=due_at,
    )
    db.add(row)
    if contact_id:
        contact = db.get(CrmContact, contact_id)
        if contact and contact.brand_id == brand_id:
            contact.last_touch_at = datetime.now(UTC)
    return row


def decorate_deal(db: Session, deal: CrmDeal) -> dict:
    contact = db.get(CrmContact, deal.contact_id) if deal.contact_id else None
    account = db.get(CrmAccount, deal.account_id) if deal.account_id else None
    return {
        "id": deal.id,
        "brand_id": deal.brand_id,
        "account_id": deal.account_id,
        "contact_id": deal.contact_id,
        "campaign_id": deal.campaign_id,
        "owner_agent_id": deal.owner_agent_id,
        "name": deal.name,
        "stage": deal.stage,
        "value_usd": deal.value_usd,
        "probability": deal.probability,
        "close_date": deal.close_date,
        "notes": deal.notes,
        "lost_reason": deal.lost_reason,
        "sort_order": deal.sort_order,
        "contact_name": contact.name if contact else "",
        "account_name": account.name if account else "",
        "created_at": deal.created_at,
        "updated_at": deal.updated_at,
    }


def decorate_contact(db: Session, contact: CrmContact) -> dict:
    account = db.get(CrmAccount, contact.account_id) if contact.account_id else None
    data = {
        "id": contact.id,
        "brand_id": contact.brand_id,
        "account_id": contact.account_id,
        "name": contact.name,
        "email": contact.email,
        "phone": contact.phone,
        "title": contact.title,
        "company": contact.company,
        "channel": contact.channel,
        "status": contact.status,
        "temperature": contact.temperature,
        "signal_score": contact.signal_score,
        "tags": contact.tags or [],
        "source": contact.source,
        "next_action": contact.next_action,
        "notes": contact.notes,
        "last_touch_at": contact.last_touch_at,
        "created_at": contact.created_at,
        "account_name": account.name if account else "",
    }
    return data


def board_stats(db: Session, brand_id: UUID) -> dict:
    contacts = db.scalar(select(func.count()).select_from(CrmContact).where(CrmContact.brand_id == brand_id)) or 0
    accounts = db.scalar(select(func.count()).select_from(CrmAccount).where(CrmAccount.brand_id == brand_id)) or 0
    deals = db.scalars(select(CrmDeal).where(CrmDeal.brand_id == brand_id)).all()
    open_deals = [d for d in deals if d.stage not in ("won", "lost")]
    pipeline = sum((d.value_usd or Decimal("0")) for d in open_deals)
    weighted = sum(((d.value_usd or Decimal("0")) * Decimal(d.probability or 0) / Decimal(100)) for d in open_deals)
    won = sum((d.value_usd or Decimal("0")) for d in deals if d.stage == "won")
    avg_deal = (pipeline / len(open_deals)) if open_deals else Decimal("0")
    hot = db.scalar(
        select(func.count())
        .select_from(CrmContact)
        .where(CrmContact.brand_id == brand_id, CrmContact.temperature.in_(["hot", "star"]))
    ) or 0
    avg = db.scalar(select(func.avg(CrmContact.signal_score)).where(CrmContact.brand_id == brand_id)) or 0
    cutoff = datetime.now(UTC) - timedelta(days=7)
    stale = db.scalar(
        select(func.count())
        .select_from(CrmContact)
        .where(
            CrmContact.brand_id == brand_id,
            CrmContact.next_action != "",
            or_(CrmContact.last_touch_at.is_(None), CrmContact.last_touch_at < cutoff),
        )
    ) or 0
    stages = {stage: 0 for stage in DEAL_STAGES}
    for deal in deals:
        stages[deal.stage] = stages.get(deal.stage, 0) + 1
    return {
        "contacts": int(contacts),
        "accounts": int(accounts),
        "open_deals": len(open_deals),
        "pipeline_usd": pipeline,
        "weighted_pipeline_usd": weighted,
        "won_usd": won,
        "avg_deal_usd": avg_deal,
        "hot_leads": int(hot),
        "overdue": int(stale),
        "stages": stages,
        "avg_signal": float(avg or 0),
    }


def overdue_contacts(db: Session, brand_id: UUID) -> list[CrmContact]:
    cutoff = datetime.now(UTC) - timedelta(days=7)
    return list(
        db.scalars(
            select(CrmContact)
            .where(
                CrmContact.brand_id == brand_id,
                CrmContact.next_action != "",
                or_(CrmContact.last_touch_at.is_(None), CrmContact.last_touch_at < cutoff),
            )
            .order_by(CrmContact.signal_score.desc())
            .limit(40)
        ).all()
    )


def heuristic_score(contact: CrmContact) -> tuple[int, str, str]:
    score = 30
    reasons: list[str] = []
    title = (contact.title or "").lower()
    if contact.email:
        score += 8
        reasons.append("has email")
    if contact.phone:
        score += 6
        reasons.append("has phone")
    if any(token in title for token in ("vp", "chief", "founder", "director", "head", "owner", "cmo", "ceo")):
        score += 18
        reasons.append("senior title")
    if contact.company or contact.account_id:
        score += 8
        reasons.append("company attached")
    if contact.next_action:
        score += 10
        reasons.append("next action set")
    if contact.last_touch_at and datetime.now(UTC) - contact.last_touch_at < timedelta(days=3):
        score += 12
        reasons.append("recent touch")
    elif not contact.last_touch_at:
        score -= 6
        reasons.append("never touched")
    score = max(0, min(100, score))
    if score >= 85:
        temp = "star"
    elif score >= 70:
        temp = "hot"
    elif score >= 50:
        temp = "warm"
    elif score >= 30:
        temp = "cool"
    else:
        temp = "ice"
    if temp not in CONTACT_TEMPS:
        temp = "cool"
    return score, temp, "; ".join(reasons) or "baseline"


def search_records(db: Session, brand_id: UUID, q: str, limit: int = 20) -> dict:
    needle = f"%{q.strip()}%"
    contacts = db.scalars(
        select(CrmContact)
        .where(
            CrmContact.brand_id == brand_id,
            or_(
                CrmContact.name.ilike(needle),
                CrmContact.email.ilike(needle),
                CrmContact.company.ilike(needle),
                CrmContact.notes.ilike(needle),
            ),
        )
        .limit(limit)
    ).all()
    accounts = db.scalars(
        select(CrmAccount)
        .where(
            CrmAccount.brand_id == brand_id,
            or_(CrmAccount.name.ilike(needle), CrmAccount.domain.ilike(needle), CrmAccount.industry.ilike(needle)),
        )
        .limit(limit)
    ).all()
    deals = db.scalars(
        select(CrmDeal)
        .where(CrmDeal.brand_id == brand_id, CrmDeal.name.ilike(needle))
        .limit(limit)
    ).all()
    return {"contacts": contacts, "accounts": accounts, "deals": deals}


def seed_demo_crm(db: Session, brand_id: UUID) -> None:
    if db.scalar(select(CrmContact.id).where(CrmContact.brand_id == brand_id).limit(1)):
        return
    crm_agent = db.scalar(select(Agent).where(Agent.brand_id == brand_id, Agent.role == "crm"))
    accounts = [
        CrmAccount(
            brand_id=brand_id,
            name="Lumen Labs",
            domain="lumenlabs.io",
            industry="Beauty tech",
            size="51-200",
            website="https://lumenlabs.io",
            signal_score=78,
            tags=["enterprise", "retail"],
            notes="Evaluating a seasonal launch suite.",
        ),
        CrmAccount(
            brand_id=brand_id,
            name="Harbor Botanics",
            domain="harborbotanics.com",
            industry="Wellness",
            size="11-50",
            website="https://harborbotanics.com",
            signal_score=64,
            tags=["dtc", "warm"],
            notes="Wants lifecycle email + CRM nurture.",
        ),
        CrmAccount(
            brand_id=brand_id,
            name="Northglass",
            domain="northglass.co",
            industry="CPG",
            size="201-500",
            signal_score=51,
            tags=["inbound"],
            notes="Came from LinkedIn thought-leadership.",
        ),
    ]
    db.add_all(accounts)
    db.flush()

    contacts = [
        CrmContact(
            brand_id=brand_id,
            account_id=accounts[0].id,
            name="Ava Chen",
            email="ava.chen@lumenlabs.io",
            phone="+1-415-555-0142",
            title="VP Brand",
            company="Lumen Labs",
            channel="linkedin",
            status="active",
            temperature="hot",
            signal_score=88,
            tags=["decision-maker", "launch"],
            source="outbound",
            next_action="Send Spring Edit lookbook",
            notes="Asked for a two-week campaign sprint.",
            last_touch_at=datetime.now(UTC) - timedelta(days=2),
        ),
        CrmContact(
            brand_id=brand_id,
            account_id=accounts[1].id,
            name="Jonah Reed",
            email="jonah@harborbotanics.com",
            title="Founder",
            company="Harbor Botanics",
            channel="web",
            status="lead",
            temperature="warm",
            signal_score=71,
            tags=["founder", "email"],
            source="site",
            next_action="Book strategy huddle",
            notes="Loves warm voice, hates hype adjectives.",
            last_touch_at=datetime.now(UTC) - timedelta(days=9),
        ),
        CrmContact(
            brand_id=brand_id,
            account_id=accounts[2].id,
            name="Priya Shah",
            email="priya.shah@northglass.co",
            title="Growth Lead",
            company="Northglass",
            channel="twitter",
            status="lead",
            temperature="cool",
            signal_score=46,
            tags=["growth"],
            source="social",
            next_action="Nurture with case study",
            notes="Wants proof before a paid test.",
        ),
        CrmContact(
            brand_id=brand_id,
            name="Sam Okonkwo",
            email="sam@ateliervoid.studio",
            title="Creative Director",
            company="Atelier Void",
            channel="referral",
            status="lead",
            temperature="star",
            signal_score=92,
            tags=["creative", "referral"],
            source="partner",
            next_action="Intro to designer + video agents",
            notes="Could become a flagship case.",
            last_touch_at=datetime.now(UTC) - timedelta(days=1),
        ),
    ]
    db.add_all(contacts)
    db.flush()

    deals = [
        CrmDeal(
            brand_id=brand_id,
            account_id=accounts[0].id,
            contact_id=contacts[0].id,
            owner_agent_id=crm_agent.id if crm_agent else None,
            name="Lumen — Spring Edit retain",
            stage="propose",
            value_usd=Decimal("18000"),
            probability=50,
            close_date="2026-10-15",
            notes="Proposal covers CMO swarm + visual studio.",
            sort_order=0,
        ),
        CrmDeal(
            brand_id=brand_id,
            account_id=accounts[1].id,
            contact_id=contacts[1].id,
            owner_agent_id=crm_agent.id if crm_agent else None,
            name="Harbor lifecycle stack",
            stage="qualify",
            value_usd=Decimal("7200"),
            probability=25,
            close_date="2026-10-30",
            notes="Email + CRM nurture only.",
            sort_order=0,
        ),
        CrmDeal(
            brand_id=brand_id,
            account_id=accounts[2].id,
            contact_id=contacts[2].id,
            name="Northglass paid test",
            stage="signal",
            value_usd=Decimal("4500"),
            probability=10,
            notes="Waiting on creative proof.",
            sort_order=0,
        ),
        CrmDeal(
            brand_id=brand_id,
            contact_id=contacts[3].id,
            name="Atelier Void flagship",
            stage="commit",
            value_usd=Decimal("24000"),
            probability=75,
            close_date="2026-09-28",
            notes="Verbal yes. Need MSA.",
            sort_order=0,
        ),
    ]
    db.add_all(deals)
    db.flush()
    db.add(
        CrmActivity(
            brand_id=brand_id,
            contact_id=contacts[0].id,
            deal_id=deals[0].id,
            agent_id=crm_agent.id if crm_agent else None,
            kind="ai",
            title="Signal spike",
            body="VP Brand opened the lookbook twice and asked about Instagram 4:5 frames.",
        )
    )
    db.add(
        CrmActivity(
            brand_id=brand_id,
            contact_id=contacts[3].id,
            deal_id=deals[3].id,
            kind="note",
            title="Referral intro",
            body="Partner said they want a control plane, not an agency.",
        )
    )
    db.flush()
