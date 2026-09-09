from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.crm import CrmAccount, CrmActivity, CrmContact, CrmDeal, DEAL_STAGES
from app.models.user import User
from app.schemas.crm import (
    AccountIn,
    AccountOut,
    AccountUpdate,
    ActivityIn,
    ActivityOut,
    ContactIn,
    ContactOut,
    ContactUpdate,
    CrmBoardOut,
    DealIn,
    DealOut,
    DealUpdate,
)
from app.services.access import get_brand_for_user
from app.services.crm import board_stats, seed_demo_crm

router = APIRouter(prefix="/brands/{brand_id}/crm", tags=["crm"])


def _apply(row, payload: dict) -> None:
    for key, value in payload.items():
        setattr(row, key, value)


@router.get("/board", response_model=CrmBoardOut)
def crm_board(
    brand_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> CrmBoardOut:
    get_brand_for_user(db, brand_id, user.id)
    return CrmBoardOut(**board_stats(db, brand_id))


@router.post("/seed")
def seed_crm(brand_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    get_brand_for_user(db, brand_id, user.id)
    seed_demo_crm(db, brand_id)
    db.commit()
    stats = board_stats(db, brand_id)
    return {
        "ok": True,
        "contacts": stats["contacts"],
        "accounts": stats["accounts"],
        "open_deals": stats["open_deals"],
        "pipeline_usd": str(stats["pipeline_usd"]),
        "won_usd": str(stats["won_usd"]),
        "hot_leads": stats["hot_leads"],
    }


@router.get("/accounts", response_model=list[AccountOut])
def list_accounts(
    brand_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[CrmAccount]:
    get_brand_for_user(db, brand_id, user.id)
    return list(db.scalars(select(CrmAccount).where(CrmAccount.brand_id == brand_id).order_by(CrmAccount.signal_score.desc())).all())


@router.post("/accounts", response_model=AccountOut)
def create_account(
    brand_id: UUID,
    payload: AccountIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CrmAccount:
    get_brand_for_user(db, brand_id, user.id)
    row = CrmAccount(brand_id=brand_id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/accounts/{account_id}", response_model=AccountOut)
def update_account(
    brand_id: UUID,
    account_id: UUID,
    payload: AccountUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CrmAccount:
    get_brand_for_user(db, brand_id, user.id)
    row = db.get(CrmAccount, account_id)
    if row is None or row.brand_id != brand_id:
        raise HTTPException(status_code=404, detail="Account not found")
    _apply(row, payload.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(row)
    return row


@router.get("/contacts", response_model=list[ContactOut])
def list_contacts(
    brand_id: UUID,
    q: str = Query(""),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[CrmContact]:
    get_brand_for_user(db, brand_id, user.id)
    stmt = select(CrmContact).where(CrmContact.brand_id == brand_id)
    if q.strip():
        needle = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                CrmContact.name.ilike(needle),
                CrmContact.email.ilike(needle),
                CrmContact.company.ilike(needle),
            )
        )
    return list(db.scalars(stmt.order_by(CrmContact.signal_score.desc())).all())


@router.post("/contacts", response_model=ContactOut)
def create_contact(
    brand_id: UUID,
    payload: ContactIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CrmContact:
    get_brand_for_user(db, brand_id, user.id)
    data = payload.model_dump()
    data["email"] = (data.get("email") or "").strip().lower()
    row = CrmContact(brand_id=brand_id, **data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/contacts/{contact_id}", response_model=ContactOut)
def update_contact(
    brand_id: UUID,
    contact_id: UUID,
    payload: ContactUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CrmContact:
    get_brand_for_user(db, brand_id, user.id)
    row = db.get(CrmContact, contact_id)
    if row is None or row.brand_id != brand_id:
        raise HTTPException(status_code=404, detail="Contact not found")
    data = payload.model_dump(exclude_unset=True)
    if "email" in data and data["email"] is not None:
        data["email"] = data["email"].strip().lower()
    _apply(row, data)
    db.commit()
    db.refresh(row)
    return row


@router.get("/deals", response_model=list[DealOut])
def list_deals(
    brand_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[CrmDeal]:
    get_brand_for_user(db, brand_id, user.id)
    return list(db.scalars(select(CrmDeal).where(CrmDeal.brand_id == brand_id).order_by(CrmDeal.created_at.desc())).all())


@router.post("/deals", response_model=DealOut)
def create_deal(
    brand_id: UUID,
    payload: DealIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CrmDeal:
    get_brand_for_user(db, brand_id, user.id)
    data = payload.model_dump()
    if data.get("stage") and data["stage"] not in DEAL_STAGES:
        raise HTTPException(status_code=400, detail="Invalid stage")
    row = CrmDeal(brand_id=brand_id, **data)
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/deals/{deal_id}", response_model=DealOut)
def update_deal(
    brand_id: UUID,
    deal_id: UUID,
    payload: DealUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CrmDeal:
    get_brand_for_user(db, brand_id, user.id)
    row = db.get(CrmDeal, deal_id)
    if row is None or row.brand_id != brand_id:
        raise HTTPException(status_code=404, detail="Deal not found")
    data = payload.model_dump(exclude_unset=True)
    if data.get("stage") and data["stage"] not in DEAL_STAGES:
        raise HTTPException(status_code=400, detail="Invalid stage")
    _apply(row, data)
    db.commit()
    db.refresh(row)
    return row


@router.get("/activities", response_model=list[ActivityOut])
def list_activities(
    brand_id: UUID,
    contact_id: UUID | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[CrmActivity]:
    get_brand_for_user(db, brand_id, user.id)
    stmt = select(CrmActivity).where(CrmActivity.brand_id == brand_id)
    if contact_id:
        stmt = stmt.where(CrmActivity.contact_id == contact_id)
    return list(db.scalars(stmt.order_by(CrmActivity.created_at.desc()).limit(80)).all())


@router.post("/activities", response_model=ActivityOut)
def create_activity(
    brand_id: UUID,
    payload: ActivityIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CrmActivity:
    get_brand_for_user(db, brand_id, user.id)
    row = CrmActivity(brand_id=brand_id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row
