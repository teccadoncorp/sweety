from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.brand import Brand
from app.models.crm import CrmAccount, CrmActivity, CrmContact, CrmDeal, CrmLineItem, DEAL_STAGES, STAGE_PROBABILITY
from app.models.user import User
from app.schemas.crm import (
    AccountIn,
    AccountOut,
    AccountUpdate,
    ActivityIn,
    ActivityOut,
    ActivityUpdate,
    LineItemIn,
    LineItemOut,
    LineItemUpdate,
    ContactIn,
    ContactOut,
    ContactUpdate,
    CrmBoardOut,
    DealIn,
    DealOut,
    DealUpdate,
)
from app.services.access import get_brand_for_user
from app.services.crm import (
    apply_stage,
    board_stats,
    decorate_contact,
    decorate_deal,
    log_activity,
    overdue_contacts,
    seed_demo_crm,
)
from app.services import crm_ai

router = APIRouter(prefix="/brands/{brand_id}/crm", tags=["crm"])


def _apply(row, payload: dict) -> None:
    for key, value in payload.items():
        setattr(row, key, value)


def _brand(db: Session, brand_id: UUID, user: User) -> Brand:
    return get_brand_for_user(db, brand_id, user.id)


@router.get("/board", response_model=CrmBoardOut)
def crm_board(
    brand_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> CrmBoardOut:
    _brand(db, brand_id, user)
    return CrmBoardOut(**board_stats(db, brand_id))


@router.get("/overdue", response_model=list[ContactOut])
def list_overdue(
    brand_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[dict]:
    _brand(db, brand_id, user)
    return [decorate_contact(db, row) for row in overdue_contacts(db, brand_id)]


@router.post("/seed")
def seed_crm(brand_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)) -> dict:
    _brand(db, brand_id, user)
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
    _brand(db, brand_id, user)
    return list(
        db.scalars(select(CrmAccount).where(CrmAccount.brand_id == brand_id).order_by(CrmAccount.signal_score.desc())).all()
    )


@router.post("/accounts", response_model=AccountOut)
def create_account(
    brand_id: UUID,
    payload: AccountIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CrmAccount:
    _brand(db, brand_id, user)
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
    _brand(db, brand_id, user)
    row = db.get(CrmAccount, account_id)
    if row is None or row.brand_id != brand_id:
        raise HTTPException(status_code=404, detail="Account not found")
    _apply(row, payload.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(row)
    return row


@router.delete("/accounts/{account_id}")
def delete_account(
    brand_id: UUID,
    account_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    _brand(db, brand_id, user)
    row = db.get(CrmAccount, account_id)
    if row is None or row.brand_id != brand_id:
        raise HTTPException(status_code=404, detail="Account not found")
    for contact in db.scalars(select(CrmContact).where(CrmContact.account_id == account_id)):
        contact.account_id = None
    for deal in db.scalars(select(CrmDeal).where(CrmDeal.account_id == account_id)):
        deal.account_id = None
    for act in db.scalars(select(CrmActivity).where(CrmActivity.account_id == account_id)):
        act.account_id = None
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.get("/contacts", response_model=list[ContactOut])
def list_contacts(
    brand_id: UUID,
    q: str = Query(""),
    temperature: str = Query(""),
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict]:
    _brand(db, brand_id, user)
    stmt = select(CrmContact).where(CrmContact.brand_id == brand_id)
    if q.strip():
        needle = f"%{q.strip()}%"
        stmt = stmt.where(
            or_(
                CrmContact.name.ilike(needle),
                CrmContact.email.ilike(needle),
                CrmContact.company.ilike(needle),
                CrmContact.phone.ilike(needle),
            )
        )
    if temperature.strip() and temperature != "all":
        stmt = stmt.where(CrmContact.temperature == temperature)
    rows = db.scalars(stmt.order_by(CrmContact.signal_score.desc())).all()
    return [decorate_contact(db, row) for row in rows]


@router.post("/contacts", response_model=ContactOut)
def create_contact(
    brand_id: UUID,
    payload: ContactIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    _brand(db, brand_id, user)
    data = payload.model_dump()
    data["email"] = (data.get("email") or "").strip().lower()
    row = CrmContact(brand_id=brand_id, **data)
    db.add(row)
    db.flush()
    log_activity(db, brand_id, kind="note", title="Contact created", body=f"{row.name} added to CRM.", contact_id=row.id)
    db.commit()
    db.refresh(row)
    return decorate_contact(db, row)


@router.patch("/contacts/{contact_id}", response_model=ContactOut)
def update_contact(
    brand_id: UUID,
    contact_id: UUID,
    payload: ContactUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    _brand(db, brand_id, user)
    row = db.get(CrmContact, contact_id)
    if row is None or row.brand_id != brand_id:
        raise HTTPException(status_code=404, detail="Contact not found")
    data = payload.model_dump(exclude_unset=True)
    if "email" in data and data["email"] is not None:
        data["email"] = data["email"].strip().lower()
    _apply(row, data)
    db.commit()
    db.refresh(row)
    return decorate_contact(db, row)


@router.delete("/contacts/{contact_id}")
def delete_contact(
    brand_id: UUID,
    contact_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    _brand(db, brand_id, user)
    row = db.get(CrmContact, contact_id)
    if row is None or row.brand_id != brand_id:
        raise HTTPException(status_code=404, detail="Contact not found")
    for deal in db.scalars(select(CrmDeal).where(CrmDeal.contact_id == contact_id)):
        deal.contact_id = None
    for act in db.scalars(select(CrmActivity).where(CrmActivity.contact_id == contact_id)):
        act.contact_id = None
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.post("/contacts/{contact_id}/score")
def score_contact(
    brand_id: UUID,
    contact_id: UUID,
    apply: bool = True,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    _brand(db, brand_id, user)
    row = db.get(CrmContact, contact_id)
    if row is None or row.brand_id != brand_id:
        raise HTTPException(status_code=404, detail="Contact not found")
    result = crm_ai.score_contact(row)
    if apply:
        row.signal_score = result["signal_score"]
        row.temperature = result["temperature"]
        if result.get("next_action"):
            row.next_action = result["next_action"]
        log_activity(
            db,
            brand_id,
            kind="ai",
            title="Lead scored",
            body=f"Score {result['signal_score']} ({result['temperature']}): {result['reasons']}",
            contact_id=row.id,
        )
        db.commit()
        db.refresh(row)
    return {**result, "contact": decorate_contact(db, row)}


@router.get("/deals", response_model=list[DealOut])
def list_deals(
    brand_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[dict]:
    _brand(db, brand_id, user)
    rows = db.scalars(
        select(CrmDeal).where(CrmDeal.brand_id == brand_id).order_by(CrmDeal.sort_order, CrmDeal.created_at.desc())
    ).all()
    return [decorate_deal(db, row) for row in rows]


@router.post("/deals", response_model=DealOut)
def create_deal(
    brand_id: UUID,
    payload: DealIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    _brand(db, brand_id, user)
    data = payload.model_dump()
    if data.get("stage") and data["stage"] not in DEAL_STAGES:
        raise HTTPException(status_code=400, detail="Invalid stage")
    data["probability"] = STAGE_PROBABILITY.get(data.get("stage") or "signal", 10)
    row = CrmDeal(brand_id=brand_id, **data)
    db.add(row)
    db.flush()
    log_activity(
        db,
        brand_id,
        kind="note",
        title="Deal created",
        body=f"{row.name} opened in {row.stage} at ${row.value_usd}.",
        deal_id=row.id,
        contact_id=row.contact_id,
        account_id=row.account_id,
    )
    db.commit()
    db.refresh(row)
    return decorate_deal(db, row)


@router.patch("/deals/{deal_id}", response_model=DealOut)
def update_deal(
    brand_id: UUID,
    deal_id: UUID,
    payload: DealUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    _brand(db, brand_id, user)
    row = db.get(CrmDeal, deal_id)
    if row is None or row.brand_id != brand_id:
        raise HTTPException(status_code=404, detail="Deal not found")
    data = payload.model_dump(exclude_unset=True)
    previous = row.stage
    if data.get("stage"):
        try:
            apply_stage(row, data.pop("stage"), data.get("lost_reason") or "")
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        if "probability" in data and previous != row.stage:
            data.pop("probability", None)
    _apply(row, data)
    if previous != row.stage:
        log_activity(
            db,
            brand_id,
            kind="stage",
            title=f"Moved to {row.stage}",
            body=f"{row.name} moved from {previous} to {row.stage} ({row.probability}% probability).",
            deal_id=row.id,
            contact_id=row.contact_id,
            account_id=row.account_id,
        )
    db.commit()
    db.refresh(row)
    return decorate_deal(db, row)


@router.delete("/deals/{deal_id}")
def delete_deal(
    brand_id: UUID,
    deal_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    _brand(db, brand_id, user)
    row = db.get(CrmDeal, deal_id)
    if row is None or row.brand_id != brand_id:
        raise HTTPException(status_code=404, detail="Deal not found")
    for act in db.scalars(select(CrmActivity).where(CrmActivity.deal_id == deal_id)):
        act.deal_id = None
    for item in db.scalars(select(CrmLineItem).where(CrmLineItem.deal_id == deal_id)):
        db.delete(item)
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.post("/deals/{deal_id}/coach")
def coach_deal(
    brand_id: UUID,
    deal_id: UUID,
    apply_action: bool = True,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    _brand(db, brand_id, user)
    row = db.get(CrmDeal, deal_id)
    if row is None or row.brand_id != brand_id:
        raise HTTPException(status_code=404, detail="Deal not found")
    contact = db.get(CrmContact, row.contact_id) if row.contact_id else None
    result = crm_ai.coach_deal(row, contact)
    if apply_action and contact and result.get("next_action"):
        contact.next_action = result["next_action"]
        log_activity(
            db,
            brand_id,
            kind="ai",
            title="AI coach",
            body=f"{result['next_action']}\nRisk: {result['risk']}",
            deal_id=row.id,
            contact_id=contact.id,
        )
        db.commit()
    return {**result, "deal": decorate_deal(db, row)}


@router.get("/activities", response_model=list[ActivityOut])
def list_activities(
    brand_id: UUID,
    contact_id: UUID | None = None,
    deal_id: UUID | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[CrmActivity]:
    _brand(db, brand_id, user)
    stmt = select(CrmActivity).where(CrmActivity.brand_id == brand_id)
    if contact_id:
        stmt = stmt.where(CrmActivity.contact_id == contact_id)
    if deal_id:
        stmt = stmt.where(CrmActivity.deal_id == deal_id)
    return list(db.scalars(stmt.order_by(CrmActivity.created_at.desc()).limit(120)).all())


@router.post("/activities", response_model=ActivityOut)
def create_activity(
    brand_id: UUID,
    payload: ActivityIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CrmActivity:
    _brand(db, brand_id, user)
    row = log_activity(
        db,
        brand_id,
        kind=payload.kind or "note",
        title=payload.title or "Note",
        body=payload.body,
        contact_id=payload.contact_id,
        account_id=payload.account_id,
        deal_id=payload.deal_id,
        agent_id=payload.agent_id,
        due_at=payload.due_at,
    )
    db.commit()
    db.refresh(row)
    return row


@router.patch("/activities/{activity_id}", response_model=ActivityOut)
def update_activity(
    brand_id: UUID,
    activity_id: UUID,
    payload: ActivityUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> CrmActivity:
    _brand(db, brand_id, user)
    row = db.get(CrmActivity, activity_id)
    if row is None or row.brand_id != brand_id:
        raise HTTPException(status_code=404, detail="Activity not found")
    _apply(row, payload.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(row)
    return row


@router.delete("/activities/{activity_id}")
def delete_activity(
    brand_id: UUID,
    activity_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    _brand(db, brand_id, user)
    row = db.get(CrmActivity, activity_id)
    if row is None or row.brand_id != brand_id:
        raise HTTPException(status_code=404, detail="Activity not found")
    db.delete(row)
    db.commit()
    return {"ok": True}


def _decorate_line(db: Session, row: CrmLineItem) -> dict:
    deal = db.get(CrmDeal, row.deal_id)
    return {
        "id": row.id,
        "brand_id": row.brand_id,
        "deal_id": row.deal_id,
        "name": row.name,
        "sku": row.sku,
        "qty": row.qty,
        "unit_price_usd": row.unit_price_usd,
        "notes": row.notes,
        "deal_name": deal.name if deal else "",
        "created_at": row.created_at,
        "updated_at": row.updated_at,
    }


@router.get("/cart", response_model=list[LineItemOut])
def list_cart(
    brand_id: UUID,
    deal_id: UUID | None = None,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> list[dict]:
    _brand(db, brand_id, user)
    stmt = select(CrmLineItem).where(CrmLineItem.brand_id == brand_id)
    if deal_id:
        stmt = stmt.where(CrmLineItem.deal_id == deal_id)
    rows = db.scalars(stmt.order_by(CrmLineItem.created_at.desc())).all()
    return [_decorate_line(db, row) for row in rows]


@router.post("/cart", response_model=LineItemOut)
def create_cart_item(
    brand_id: UUID,
    payload: LineItemIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    _brand(db, brand_id, user)
    deal = db.get(CrmDeal, payload.deal_id)
    if deal is None or deal.brand_id != brand_id:
        raise HTTPException(status_code=404, detail="Deal not found")
    row = CrmLineItem(brand_id=brand_id, **payload.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return _decorate_line(db, row)


@router.patch("/cart/{item_id}", response_model=LineItemOut)
def update_cart_item(
    brand_id: UUID,
    item_id: UUID,
    payload: LineItemUpdate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    _brand(db, brand_id, user)
    row = db.get(CrmLineItem, item_id)
    if row is None or row.brand_id != brand_id:
        raise HTTPException(status_code=404, detail="Cart item not found")
    data = payload.model_dump(exclude_unset=True)
    if data.get("deal_id"):
        deal = db.get(CrmDeal, data["deal_id"])
        if deal is None or deal.brand_id != brand_id:
            raise HTTPException(status_code=404, detail="Deal not found")
    _apply(row, data)
    db.commit()
    db.refresh(row)
    return _decorate_line(db, row)


@router.delete("/cart/{item_id}")
def delete_cart_item(
    brand_id: UUID,
    item_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    _brand(db, brand_id, user)
    row = db.get(CrmLineItem, item_id)
    if row is None or row.brand_id != brand_id:
        raise HTTPException(status_code=404, detail="Cart item not found")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.post("/ai/brief")
def ai_brief(
    brand_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> dict:
    brand = _brand(db, brand_id, user)
    return crm_ai.pipeline_brief(db, brand_id, brand.name)
