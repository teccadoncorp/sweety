from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.brand import Brand
from app.models.campaign import Campaign
from app.models.user import User
from app.schemas.common import BrandIn, BrandOut, BrandUpdate, KillSwitchIn
from app.services.access import get_brand_for_user
from app.services.budget import spent_for_brand, spent_map_for_brands
from app.services.loop import queue_launch_heartbeats, spawn_launch_campaign
from app.services.seed import DEMO_BRAND_NAME, seed_default_org

router = APIRouter(prefix="/brands", tags=["brands"])


def _campaign_meta(db: Session, brand_ids: list) -> dict:
    if not brand_ids:
        return {}
    meta: dict = {}
    rows = db.scalars(
        select(Campaign).where(Campaign.brand_id.in_(brand_ids)).order_by(Campaign.created_at.asc())
    ).all()
    for campaign in rows:
        current = meta.get(campaign.brand_id)
        if current is None:
            meta[campaign.brand_id] = [1, campaign.name]
        else:
            current[0] += 1
    return {brand_id: (count, name) for brand_id, (count, name) in meta.items()}


def _out(db: Session, brand: Brand, spent=None, meta=None) -> BrandOut:
    data = BrandOut.model_validate(brand)
    data.spent_usd = spent if spent is not None else spent_for_brand(db, brand.id)
    if meta is None:
        meta = _campaign_meta(db, [brand.id])
    count, name = meta.get(brand.id, (0, ""))
    data.campaigns_count = count
    data.launch_campaign = name
    return data


@router.get("", response_model=list[BrandOut])
def list_brands(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[BrandOut]:
    rows = list(
        db.scalars(
            select(Brand)
            .where(Brand.owner_id == user.id, Brand.name != DEMO_BRAND_NAME)
            .order_by(Brand.created_at.desc())
        ).all()
    )
    spent = spent_map_for_brands(db, [b.id for b in rows])
    meta = _campaign_meta(db, [b.id for b in rows])
    return [_out(db, b, spent.get(b.id), meta) for b in rows]


@router.post("", response_model=BrandOut)
def create_brand(
    payload: BrandIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> BrandOut:
    if not payload.mission.strip():
        raise HTTPException(status_code=400, detail="Mission is required so the CMO can open the first campaign")
    brand = Brand(
        owner_id=user.id,
        name=payload.name,
        mission=payload.mission,
        voice_notes=payload.voice_notes,
        audience=payload.audience,
        guidelines=payload.guidelines,
        logo_url=payload.logo_url,
        website_url=payload.website_url,
        app_url=payload.app_url,
        monthly_budget_usd=payload.monthly_budget_usd,
    )
    db.add(brand)
    db.flush()
    wake_ids: list = []
    if payload.seed_org:
        seed_default_org(db, brand)
    _, wake_ids = spawn_launch_campaign(db, brand)
    db.commit()
    db.refresh(brand)
    if wake_ids and not brand.agents_paused:
        queue_launch_heartbeats(wake_ids, "launch")
    return _out(db, brand)


@router.get("/{brand_id}", response_model=BrandOut)
def get_brand(
    brand_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> BrandOut:
    return _out(db, get_brand_for_user(db, brand_id, user.id))


@router.patch("/{brand_id}", response_model=BrandOut)
def update_brand(
    brand_id: UUID,
    payload: BrandUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BrandOut:
    brand = get_brand_for_user(db, brand_id, user.id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(brand, key, value)
    db.commit()
    db.refresh(brand)
    return _out(db, brand)


@router.post("/{brand_id}/kill-switch", response_model=BrandOut)
def set_kill_switch(
    brand_id: UUID,
    payload: KillSwitchIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> BrandOut:
    brand = get_brand_for_user(db, brand_id, user.id)
    brand.agents_paused = payload.paused
    db.commit()
    db.refresh(brand)
    return _out(db, brand)
