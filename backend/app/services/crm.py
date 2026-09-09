from decimal import Decimal
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.crm import CrmAccount, CrmActivity, CrmContact, CrmDeal, DEAL_STAGES


def board_stats(db: Session, brand_id: UUID) -> dict:
    contacts = db.scalar(select(func.count()).select_from(CrmContact).where(CrmContact.brand_id == brand_id)) or 0
    accounts = db.scalar(select(func.count()).select_from(CrmAccount).where(CrmAccount.brand_id == brand_id)) or 0
    deals = db.scalars(select(CrmDeal).where(CrmDeal.brand_id == brand_id)).all()
    open_deals = [d for d in deals if d.stage not in ("won", "lost")]
    pipeline = sum((d.value_usd or Decimal("0")) for d in open_deals)
    won = sum((d.value_usd or Decimal("0")) for d in deals if d.stage == "won")
    hot = db.scalar(
        select(func.count())
        .select_from(CrmContact)
        .where(CrmContact.brand_id == brand_id, CrmContact.temperature.in_(["hot", "star"]))
    ) or 0
    avg = db.scalar(select(func.avg(CrmContact.signal_score)).where(CrmContact.brand_id == brand_id)) or 0
    stages = {stage: 0 for stage in DEAL_STAGES}
    for deal in deals:
        stages[deal.stage] = stages.get(deal.stage, 0) + 1
    return {
        "contacts": int(contacts),
        "accounts": int(accounts),
        "open_deals": len(open_deals),
        "pipeline_usd": pipeline,
        "won_usd": won,
        "hot_leads": int(hot),
        "stages": stages,
        "avg_signal": float(avg or 0),
    }


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
            probability=55,
            close_date="2026-10-15",
            notes="Proposal covers CMO swarm + visual studio.",
        ),
        CrmDeal(
            brand_id=brand_id,
            account_id=accounts[1].id,
            contact_id=contacts[1].id,
            owner_agent_id=crm_agent.id if crm_agent else None,
            name="Harbor lifecycle stack",
            stage="qualify",
            value_usd=Decimal("7200"),
            probability=35,
            close_date="2026-10-30",
            notes="Email + CRM nurture only.",
        ),
        CrmDeal(
            brand_id=brand_id,
            account_id=accounts[2].id,
            contact_id=contacts[2].id,
            name="Northglass paid test",
            stage="signal",
            value_usd=Decimal("4500"),
            probability=20,
            notes="Waiting on creative proof.",
        ),
        CrmDeal(
            brand_id=brand_id,
            contact_id=contacts[3].id,
            name="Atelier Void flagship",
            stage="commit",
            value_usd=Decimal("24000"),
            probability=70,
            close_date="2026-09-28",
            notes="Verbal yes. Need MSA.",
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
