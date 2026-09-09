from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import RedirectResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.connectors.catalog import provider_specs
from app.connectors.heygen import list_avatars
from app.connectors.mcp import list_tools as mcp_list_tools
from app.connectors.oauth import authorize_url, callback_url, exchange_code, read_state
from app.connectors.store import get_connector, public_connector, upsert_connector
from app.core.config import get_settings, model_map
from app.core.db import get_db
from app.core.deps import get_current_user
from app.models.connector import Connector
from app.models.mcp_server import McpServer
from app.models.media_asset import MediaAsset
from app.models.user import User
from app.services.access import get_brand_for_user
from app.services.crypto import encrypt_json

router = APIRouter(tags=["connectors"])


class ManualConnectIn(BaseModel):
    access_token: str | None = None
    refresh_token: str | None = None
    api_key: str | None = None
    page_id: str | None = None
    page_token: str | None = None
    ig_user_id: str | None = None
    person_urn: str | None = None
    subreddit: str | None = None
    avatar_id: str | None = None
    voice_id: str | None = None
    display_name: str = ""


class SelectPageIn(BaseModel):
    page_id: str
    page_token: str | None = None
    ig_user_id: str | None = None
    page_name: str = ""


class McpIn(BaseModel):
    name: str
    transport: str = "http"
    url: str = ""
    command: str = ""
    args: list[str] = Field(default_factory=list)
    headers: dict[str, str] = Field(default_factory=dict)
    enabled: bool = True


@router.get("/connector-catalog")
def catalog(user: User = Depends(get_current_user)) -> dict:
    settings = get_settings()
    api = settings.sweety_api_public_url.rstrip("/")
    specs = []
    for spec in provider_specs():
        specs.append(
            {
                "id": spec.id,
                "label": spec.label,
                "auth": spec.auth,
                "description": spec.description,
                "connect_hint": spec.connect_hint.format(api=api),
                "scopes": spec.scopes,
                "manual_fields": spec.manual_fields,
                "oauth_ready": spec.oauth_ready,
                "env_ready": spec.env_ready,
                "callback_url": callback_url(spec.id) if spec.auth == "oauth" else None,
            }
        )
    return {"providers": specs, "models": model_map(), "openrouter_configured": bool(settings.openrouter_api_key)}


@router.get("/brands/{brand_id}/connectors")
def list_connectors(
    brand_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> dict:
    get_brand_for_user(db, brand_id, user.id)
    rows = db.scalars(select(Connector).where(Connector.brand_id == brand_id)).all()
    by_provider = {r.provider: public_connector(r) for r in rows}
    return {"connectors": by_provider}


@router.get("/brands/{brand_id}/connectors/{provider}/authorize")
def start_oauth(
    brand_id: UUID,
    provider: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    get_brand_for_user(db, brand_id, user.id)
    try:
        data = authorize_url(provider, brand_id, user.id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    if data.get("pkce_verifier"):
        upsert_connector(
            db,
            brand_id,
            provider,
            status="pending",
            auth_type="oauth",
            extra={"pkce_verifier": data["pkce_verifier"]},
        )
        db.commit()
    return {"authorize_url": data["url"], "callback_url": callback_url(provider)}


@router.get("/connectors/callback/{provider}")
def oauth_callback(
    provider: str,
    code: str | None = None,
    state: str | None = None,
    error: str | None = None,
    db: Session = Depends(get_db),
):
    settings = get_settings()
    frontend = settings.sweety_public_url.rstrip("/")
    if error or not code or not state:
        return RedirectResponse(f"{frontend}/settings?connector_error={error or 'missing_code'}")
    try:
        claims = read_state(state)
        brand_id = UUID(claims["brand_id"])
        if claims.get("provider") != provider:
            raise ValueError("Provider mismatch")
        pkce = None
        if provider == "twitter":
            row = get_connector(db, brand_id, provider)
            pkce = ((row.extra or {}).get("pkce_verifier") if row else None) or claims.get("pkce_verifier")
        tokens = exchange_code(provider, code, pkce)
    except Exception as exc:  # noqa: BLE001
        return RedirectResponse(f"{frontend}/settings?connector_error={str(exc)[:120]}")

    extra: dict[str, Any] = {}
    secrets = {
        "access_token": tokens.get("access_token"),
        "refresh_token": tokens.get("refresh_token"),
        "person_urn": tokens.get("person_urn"),
    }
    if provider in ("facebook", "instagram"):
        extra["pages"] = tokens.get("pages") or []
        pages = extra["pages"]
        if pages:
            first = pages[0]
            secrets["page_id"] = first.get("id")
            secrets["page_token"] = first.get("access_token")
            extra["page_id"] = first.get("id")
            extra["page_name"] = first.get("name")
            ig = first.get("instagram_business_account") or {}
            if ig.get("id"):
                secrets["ig_user_id"] = ig["id"]
                extra["ig_user_id"] = ig["id"]
        status = "connected" if secrets.get("page_id") or secrets.get("access_token") else "pending"
    else:
        status = "connected"

    upsert_connector(
        db,
        brand_id,
        provider,
        status=status,
        auth_type="oauth",
        secrets=secrets,
        extra=extra,
        display_name=tokens.get("display_name") or provider,
        expires_in=tokens.get("expires_in"),
        error="",
    )
    db.commit()
    return RedirectResponse(f"{frontend}/settings?connected={provider}&brand={brand_id}")


@router.post("/brands/{brand_id}/connectors/{provider}/manual")
def manual_connect(
    brand_id: UUID,
    provider: str,
    payload: ManualConnectIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    get_brand_for_user(db, brand_id, user.id)
    secrets = payload.model_dump(exclude_none=True)
    extra = {k: secrets.pop(k) for k in ("subreddit", "page_id", "ig_user_id", "person_urn", "avatar_id", "voice_id") if k in secrets}
    row = upsert_connector(
        db,
        brand_id,
        provider,
        status="connected",
        auth_type="manual",
        secrets=secrets,
        extra=extra,
        display_name=payload.display_name or provider,
        error="",
    )
    db.commit()
    return public_connector(row)


@router.post("/brands/{brand_id}/connectors/{provider}/select-page")
def select_page(
    brand_id: UUID,
    provider: str,
    payload: SelectPageIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    get_brand_for_user(db, brand_id, user.id)
    row = get_connector(db, brand_id, provider)
    if row is None:
        raise HTTPException(status_code=404, detail="Connect the account first")
    row = upsert_connector(
        db,
        brand_id,
        provider,
        status="connected",
        auth_type=row.auth_type,
        secrets={"page_id": payload.page_id, "page_token": payload.page_token, "ig_user_id": payload.ig_user_id},
        extra={"page_id": payload.page_id, "page_name": payload.page_name, "ig_user_id": payload.ig_user_id},
    )
    db.commit()
    return public_connector(row)


@router.delete("/brands/{brand_id}/connectors/{provider}")
def disconnect(
    brand_id: UUID,
    provider: str,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    get_brand_for_user(db, brand_id, user.id)
    row = get_connector(db, brand_id, provider)
    if row:
        db.delete(row)
        db.commit()
    return {"ok": True}


@router.get("/brands/{brand_id}/heygen/avatars")
def heygen_avatars(
    brand_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> dict:
    get_brand_for_user(db, brand_id, user.id)
    return list_avatars(db, brand_id)


@router.get("/brands/{brand_id}/media")
def list_media(
    brand_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[dict]:
    get_brand_for_user(db, brand_id, user.id)
    rows = db.scalars(
        select(MediaAsset).where(MediaAsset.brand_id == brand_id).order_by(MediaAsset.created_at.desc())
    ).all()
    return [
        {
            "id": str(r.id),
            "kind": r.kind,
            "provider": r.provider,
            "prompt": r.prompt,
            "url": r.url,
            "external_id": r.external_id,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }
        for r in rows
    ]


@router.get("/brands/{brand_id}/mcp")
def list_mcp(
    brand_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> list[dict]:
    get_brand_for_user(db, brand_id, user.id)
    rows = db.scalars(select(McpServer).where(McpServer.brand_id == brand_id)).all()
    return [
        {
            "id": str(r.id),
            "name": r.name,
            "transport": r.transport,
            "url": r.url,
            "command": r.command,
            "args": r.args,
            "enabled": r.enabled,
        }
        for r in rows
    ]


@router.post("/brands/{brand_id}/mcp")
def create_mcp(
    brand_id: UUID,
    payload: McpIn,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    get_brand_for_user(db, brand_id, user.id)
    server = McpServer(
        brand_id=brand_id,
        name=payload.name,
        transport=payload.transport,
        url=payload.url,
        command=payload.command,
        args=payload.args,
        headers_enc=encrypt_json(payload.headers) if payload.headers else "",
        enabled=payload.enabled,
    )
    db.add(server)
    db.commit()
    db.refresh(server)
    return {"id": str(server.id), "name": server.name, "transport": server.transport}


@router.delete("/brands/{brand_id}/mcp/{server_id}")
def delete_mcp(
    brand_id: UUID,
    server_id: UUID,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
) -> dict:
    get_brand_for_user(db, brand_id, user.id)
    server = db.get(McpServer, server_id)
    if server and server.brand_id == brand_id:
        db.delete(server)
        db.commit()
    return {"ok": True}


@router.get("/brands/{brand_id}/mcp/tools")
def mcp_tools(
    brand_id: UUID, db: Session = Depends(get_db), user: User = Depends(get_current_user)
) -> dict:
    get_brand_for_user(db, brand_id, user.id)
    return mcp_list_tools(db, brand_id)
