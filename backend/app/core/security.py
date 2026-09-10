from datetime import UTC, datetime, timedelta
from uuid import UUID

from jose import JWTError, jwt
from passlib.context import CryptContext

from app.core.config import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(password: str, hashed: str) -> bool:
    return pwd_context.verify(password, hashed)


def create_access_token(user_id: UUID, audience: str = "sweety") -> str:
    settings = get_settings()
    expire = datetime.now(UTC) + timedelta(minutes=settings.jwt_expire_minutes)
    return jwt.encode(
        {"sub": str(user_id), "exp": expire, "aud": audience},
        settings.jwt_secret,
        algorithm=settings.jwt_algorithm,
    )


def decode_token(token: str, audience: str | None = None) -> UUID | None:
    settings = get_settings()
    try:
        options = {"verify_aud": False} if audience is None else {}
        kwargs = {"audience": audience} if audience else {}
        payload = jwt.decode(
            token,
            settings.jwt_secret,
            algorithms=[settings.jwt_algorithm],
            options=options,
            **kwargs,
        )
        if audience is None and payload.get("aud") == "pm":
            return None
        sub = payload.get("sub")
        if not sub:
            return None
        return UUID(sub)
    except (JWTError, ValueError):
        return None
