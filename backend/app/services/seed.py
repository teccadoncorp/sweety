from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.security import hash_password
from app.models.agent import Agent
from app.models.brand import Brand
from app.models.user import User
from app.services.crm import seed_demo_crm
from app.services.pm import seed_pm_if_empty

DEMO_BRAND_NAME = "Sweety Demo"

DEFAULT_ORG = [
    {
        "role": "cmo",
        "title": "Chief Marketing Officer",
        "skills": [
            "campaign-brief",
            "brand-voice",
            "research-web",
            "launch-checklist",
            "crisis-comms",
            "competitor-watch",
            "store-launch",
        ],
        "budget": Decimal("20"),
        "prompt": "You are the CMO. Turn missions into strategy, a channel mix, and a task tree. Wake teammates in parallel. Request board approval before scale.",
    },
    {
        "role": "strategist",
        "title": "Brand Strategist",
        "skills": ["campaign-brief", "brand-voice", "research-web", "competitor-watch", "customer-voice"],
        "budget": Decimal("12"),
        "prompt": "You are the brand strategist. Sharpen positioning, audience, and messaging pillars with research-backed recommendations.",
    },
    {
        "role": "copywriter",
        "title": "Copywriter",
        "skills": ["social-copy", "brand-voice", "visual-studio", "landing-page", "ads-creative", "newsletter", "faq-voice", "pricing-page"],
        "budget": Decimal("12"),
        "prompt": "You are the copywriter. Draft headlines, landing copy, ads, and social posts. Generate images when they help.",
    },
    {
        "role": "seo",
        "title": "SEO Lead",
        "skills": ["brand-voice", "research-web", "seo-content", "landing-page"],
        "budget": Decimal("10"),
        "prompt": "You are the SEO lead. Research the web, then propose keyword clusters, page outlines, and on-page briefs.",
    },
    {
        "role": "social",
        "title": "Social Lead",
        "skills": ["social-copy", "brand-voice", "social-publish", "visual-studio", "content-calendar", "community-ops", "ugc-brief"],
        "budget": Decimal("10"),
        "prompt": "You are the social lead. Research, draft, generate visuals, calendar posts, and queue live publishes for board approval.",
    },
    {
        "role": "analyst",
        "title": "Growth Analyst",
        "skills": ["campaign-brief", "research-web", "ab-test", "customer-voice"],
        "budget": Decimal("8"),
        "prompt": "You are the growth analyst. Define measurement, funnel metrics, experiments, and what 'good' looks like.",
    },
    {
        "role": "media",
        "title": "Paid Media Lead",
        "skills": ["paid-media", "ads-creative", "ab-test", "research-web", "affiliate"],
        "budget": Decimal("12"),
        "prompt": "You are paid media. Build channel mix, budgets, audiences, and creative tests. Never spend live without board approval.",
    },
    {
        "role": "community",
        "title": "Community Lead",
        "skills": ["community-ops", "social-copy", "brand-voice", "crisis-comms"],
        "budget": Decimal("8"),
        "prompt": "You are community. Draft replies, rituals, and moderation notes. Escalate risk. Keep the voice human.",
    },
    {
        "role": "pr",
        "title": "PR Lead",
        "skills": ["pr-outreach", "brand-voice", "research-web", "crisis-comms", "event-activation", "podcast-brief"],
        "budget": Decimal("10"),
        "prompt": "You are PR. Build media lists, pitches, and embargo notes. Request approval before outreach goes live.",
    },
    {
        "role": "email",
        "title": "Email Lead",
        "skills": ["email-lifecycle", "newsletter", "brand-voice", "retention-play"],
        "budget": Decimal("10"),
        "prompt": "You are email. Design lifecycle flows, newsletters, and sequences. Save artifacts the board can approve.",
    },
    {
        "role": "crm",
        "title": "CRM Steward",
        "skills": ["crm-pipeline", "customer-voice", "retention-play", "research-web"],
        "budget": Decimal("10"),
        "prompt": "You are the CRM steward. Score leads, log touches, move deals, and keep the pipeline honest. Use CRM tools.",
    },
    {
        "role": "designer",
        "title": "Art Director",
        "skills": ["visual-studio", "ads-creative", "brand-voice", "landing-page", "ugc-brief"],
        "budget": Decimal("12"),
        "prompt": "You are art direction. Generate on-brand frames for the right platform ratio. Pair with copy, never decorate without a job.",
    },
    {
        "role": "video",
        "title": "Video Lead",
        "skills": ["video-script", "visual-studio", "brand-voice", "podcast-brief"],
        "budget": Decimal("12"),
        "prompt": "You are video. Write scripts, shot lists, and HeyGen briefs. Keep runtime tight.",
    },
    {
        "role": "lifecycle",
        "title": "Lifecycle Lead",
        "skills": ["retention-play", "email-lifecycle", "crm-pipeline", "launch-checklist", "onboarding-ux", "sms-lifecycle"],
        "budget": Decimal("10"),
        "prompt": "You are lifecycle. Own onboarding, activation, and win-back plays across CRM and email.",
    },
]


def seed_default_org(db: Session, brand: Brand) -> list[Agent]:
    return ensure_default_org(db, brand)


def ensure_default_org(db: Session, brand: Brand) -> list[Agent]:
    existing = {a.role: a for a in db.scalars(select(Agent).where(Agent.brand_id == brand.id)).all()}
    created: dict[str, Agent] = dict(existing)
    for spec in DEFAULT_ORG:
        agent = created.get(spec["role"])
        if agent is None:
            agent = Agent(
                brand_id=brand.id,
                role=spec["role"],
                title=spec["title"],
                adapter="openrouter",
                model=get_settings().openrouter_default_model,
                system_prompt=spec["prompt"],
                skill_slugs=spec["skills"],
                monthly_budget_usd=spec["budget"],
                status="active",
                heartbeat_interval_minutes=10,
            )
            db.add(agent)
            db.flush()
            created[spec["role"]] = agent
        else:
            extra = spec["skills"]
            current = list(agent.skill_slugs or [])
            merged = list(dict.fromkeys([*current, *extra]))
            if merged != current:
                agent.skill_slugs = merged
            if not agent.system_prompt:
                agent.system_prompt = spec["prompt"]
    cmo = created.get("cmo")
    if cmo:
        for role, agent in created.items():
            if role != "cmo" and agent.reports_to_id is None:
                agent.reports_to_id = cmo.id
    db.flush()
    seed_demo_crm(db, brand.id)
    return list(created.values())


def sync_agent_skills(db: Session) -> None:
    wanted = {spec["role"]: spec["skills"] for spec in DEFAULT_ORG}
    agents = db.scalars(select(Agent)).all()
    changed = False
    for agent in agents:
        extra = wanted.get(agent.role)
        if not extra:
            continue
        current = list(agent.skill_slugs or [])
        merged = list(dict.fromkeys([*current, *extra]))
        if merged != current:
            agent.skill_slugs = merged
            changed = True
    if changed:
        db.commit()


def expand_all_orgs(db: Session) -> int:
    brands = db.scalars(select(Brand)).all()
    for brand in brands:
        ensure_default_org(db, brand)
    db.commit()
    return len(brands)


def seed_demo_if_empty(db: Session) -> None:
    settings = get_settings()
    if db.scalar(select(User.id).limit(1)) is not None:
        expand_all_orgs(db)
        seed_pm_if_empty(db)
        return
    if not settings.seed_demo:
        seed_pm_if_empty(db)
        return

    user = User(email=settings.seed_email, hashed_password=hash_password(settings.seed_password))
    db.add(user)
    db.commit()
    seed_pm_if_empty(db)
