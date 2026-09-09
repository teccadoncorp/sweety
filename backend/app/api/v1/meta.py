from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings, model_map
from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.agent import Agent
from app.models.user import User
from app.schemas.common import AdapterHealthOut, SkillOut, UsageOut
from app.services.access import get_brand_for_user
from app.services.budget import spent_for_agent, spent_for_brand
from app.services.heartbeat import adapter_health
from app.services.skills import load_all_skills

router = APIRouter(tags=["meta"])


@router.get("/adapters", response_model=list[AdapterHealthOut])
def list_adapters(user: User = Depends(get_current_user)) -> list[dict]:
    return adapter_health()


@router.get("/skills", response_model=list[SkillOut])
def list_skills(user: User = Depends(get_current_user)) -> list[SkillOut]:
    return [
        SkillOut(
            slug=p.slug,
            name=p.name,
            version=p.version,
            allowed_roles=p.allowed_roles,
            description=p.description,
        )
        for p in load_all_skills().values()
    ]


@router.get("/brands/{brand_id}/usage", response_model=UsageOut)
def brand_usage(
    brand_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> UsageOut:
    brand = get_brand_for_user(db, brand_id, user.id)
    agents = db.scalars(select(Agent).where(Agent.brand_id == brand_id)).all()
    return UsageOut(
        brand_spent_usd=spent_for_brand(db, brand.id),
        brand_budget_usd=brand.monthly_budget_usd,
        by_agent=[
            {
                "agent_id": str(a.id),
                "title": a.title,
                "role": a.role,
                "spent_usd": str(spent_for_agent(db, a.id)),
                "budget_usd": str(a.monthly_budget_usd),
            }
            for a in agents
        ],
    )


@router.get("/settings/status")
def settings_status(user: User = Depends(get_current_user)) -> dict:
    settings = get_settings()
    key = settings.openrouter_api_key
    masked = ""
    if key:
        masked = f"{key[:6]}…{key[-4:]}" if len(key) > 12 else "set"
    return {
        "openrouter_configured": bool(key),
        "openrouter_key_preview": masked,
        "default_model": settings.openrouter_default_model,
        "public_url": settings.sweety_public_url,
        "api_public_url": settings.sweety_api_public_url,
        "models": model_map(),
        "heygen_configured": bool(settings.heygen_api_key),
        "tavily_configured": bool(settings.tavily_api_key),
        "require_publish_approval": settings.require_publish_approval,
        "oauth_apps": {
            "reddit": bool(settings.reddit_client_id and settings.reddit_client_secret),
            "twitter": bool(settings.twitter_client_id and settings.twitter_client_secret),
            "linkedin": bool(settings.linkedin_client_id and settings.linkedin_client_secret),
            "facebook": bool(settings.facebook_client_id and settings.facebook_client_secret),
        },
    }
