from uuid import UUID

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.brand import Brand
from app.models.user import User
from app.schemas.common import BrandIn, BrandOut, BrandUpdate
from app.services.access import get_brand_for_user
from app.services.budget import spent_for_brand
from app.services.seed import seed_default_org

router = APIRouter(prefix="/brands", tags=["brands"])


def _out(db: Session, brand: Brand) -> BrandOut:
    data = BrandOut.model_validate(brand)
    data.spent_usd = spent_for_brand(db, brand.id)
    return data


@router.get("", response_model=list[BrandOut])
def list_brands(db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> list[BrandOut]:
    rows = db.scalars(select(Brand).where(Brand.owner_id == user.id).order_by(Brand.created_at.desc())).all()
    return [_out(db, b) for b in rows]


@router.post("", response_model=BrandOut)
def create_brand(
    payload: BrandIn, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> BrandOut:
    brand = Brand(
        owner_id=user.id,
        name=payload.name,
        mission=payload.mission,
        voice_notes=payload.voice_notes,
        logo_url=payload.logo_url,
        website_url=payload.website_url,
        app_url=payload.app_url,
        monthly_budget_usd=payload.monthly_budget_usd,
    )
    db.add(brand)
    db.flush()
    if payload.seed_org:
        seed_default_org(db, brand)
    db.commit()
    db.refresh(brand)
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
