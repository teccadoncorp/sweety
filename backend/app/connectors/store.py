from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.connector import Connector
from app.services.crypto import decrypt_json, encrypt_json


def get_connector(db: Session, brand_id: UUID, provider: str) -> Connector | None:
    return db.scalar(
        select(Connector).where(Connector.brand_id == brand_id, Connector.provider == provider)
    )


def upsert_connector(
    db: Session,
    brand_id: UUID,
    provider: str,
    *,
    status: str,
    auth_type: str,
    secrets: dict[str, Any] | None = None,
    extra: dict[str, Any] | None = None,
    display_name: str = "",
    expires_in: int | None = None,
    error: str = "",
) -> Connector:
    row = get_connector(db, brand_id, provider)
    if row is None:
        row = Connector(brand_id=brand_id, provider=provider)
        db.add(row)
    row.status = status
    row.auth_type = auth_type
    row.display_name = display_name or row.display_name
    row.error = error
    if secrets is not None:
        existing = decrypt_json(row.secrets_enc)
        existing.update({k: v for k, v in secrets.items() if v})
        row.secrets_enc = encrypt_json(existing)
    if extra is not None:
        merged = dict(row.extra or {})
        merged.update(extra)
        row.extra = merged
    if expires_in:
        row.expires_at = datetime.now(UTC) + timedelta(seconds=int(expires_in))
    db.flush()
    return row


def secrets_of(row: Connector) -> dict[str, Any]:
    return decrypt_json(row.secrets_enc)


def public_connector(row: Connector) -> dict[str, Any]:
    return {
        "id": str(row.id),
        "provider": row.provider,
        "status": row.status,
        "auth_type": row.auth_type,
        "display_name": row.display_name,
        "extra": {k: v for k, v in (row.extra or {}).items() if k != "pkce_verifier"},
        "error": row.error,
        "expires_at": row.expires_at.isoformat() if row.expires_at else None,
        "connected": row.status == "connected",
    }
