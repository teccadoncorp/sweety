from __future__ import annotations

import base64
import hashlib
import secrets
from typing import Any
from urllib.parse import urlencode
from uuid import UUID

import httpx
from jose import JWTError, jwt

from app.connectors.catalog import spec_map
from app.core.config import get_settings


def _api_base() -> str:
    return get_settings().sweety_api_public_url.rstrip("/")


def callback_url(provider: str) -> str:
    return f"{_api_base()}/api/v1/connectors/callback/{provider}"


def sign_state(brand_id: UUID, user_id: UUID, provider: str, extra: dict | None = None) -> str:
    settings = get_settings()
    payload = {"brand_id": str(brand_id), "user_id": str(user_id), "provider": provider, **(extra or {})}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)


def read_state(token: str) -> dict[str, Any]:
    settings = get_settings()
    try:
        return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
    except JWTError as exc:
        raise ValueError("Invalid OAuth state") from exc


def _basic(client_id: str, client_secret: str) -> str:
    raw = f"{client_id}:{client_secret}".encode()
    return base64.b64encode(raw).decode()


def pkce_pair() -> tuple[str, str]:
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).decode().rstrip("=")
    return verifier, challenge


def authorize_url(provider: str, brand_id: UUID, user_id: UUID) -> dict[str, str]:
    settings = get_settings()
    spec = spec_map().get(provider)
    if spec is None or spec.auth != "oauth":
        raise ValueError("Provider does not support OAuth login")
    if not spec.oauth_ready:
        raise ValueError(f"{spec.label} app credentials are missing in .env")

    extra: dict[str, str] = {}
    if provider == "twitter":
        verifier, challenge = pkce_pair()
        extra["pkce_verifier"] = verifier
        state = sign_state(brand_id, user_id, provider, extra)
        params = {
            "response_type": "code",
            "client_id": settings.twitter_client_id,
            "redirect_uri": callback_url(provider),
            "scope": " ".join(spec.scopes),
            "state": state,
            "code_challenge": challenge,
            "code_challenge_method": "S256",
        }
        return {
            "url": f"https://twitter.com/i/oauth2/authorize?{urlencode(params)}",
            "state": state,
            "pkce_verifier": verifier,
        }

    state = sign_state(brand_id, user_id, provider)
    if provider == "reddit":
        params = {
            "client_id": settings.reddit_client_id,
            "response_type": "code",
            "state": state,
            "redirect_uri": callback_url(provider),
            "duration": "permanent",
            "scope": " ".join(spec.scopes),
        }
        return {"url": f"https://www.reddit.com/api/v1/authorize?{urlencode(params)}", "state": state}

    if provider == "linkedin":
        params = {
            "response_type": "code",
            "client_id": settings.linkedin_client_id,
            "redirect_uri": callback_url(provider),
            "state": state,
            "scope": " ".join(spec.scopes),
        }
        return {"url": f"https://www.linkedin.com/oauth/v2/authorization?{urlencode(params)}", "state": state}

    if provider in ("facebook", "instagram"):
        params = {
            "client_id": settings.facebook_client_id,
            "redirect_uri": callback_url(provider),
            "state": state,
            "scope": ",".join(spec.scopes),
            "response_type": "code",
        }
        return {"url": f"https://www.facebook.com/v21.0/dialog/oauth?{urlencode(params)}", "state": state}

    raise ValueError(f"No OAuth URL for {provider}")


def exchange_code(provider: str, code: str, pkce_verifier: str | None = None) -> dict[str, Any]:
    settings = get_settings()
    redirect = callback_url(provider)

    if provider == "reddit":
        response = httpx.post(
            "https://www.reddit.com/api/v1/access_token",
            data={"grant_type": "authorization_code", "code": code, "redirect_uri": redirect},
            headers={
                "Authorization": f"Basic {_basic(settings.reddit_client_id, settings.reddit_client_secret)}",
                "User-Agent": "sweety-control-plane/0.1",
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        me = httpx.get(
            "https://oauth.reddit.com/api/v1/me",
            headers={
                "Authorization": f"Bearer {data.get('access_token')}",
                "User-Agent": "sweety-control-plane/0.1",
            },
            timeout=30,
        )
        name = me.json().get("name") if me.status_code < 400 else ""
        return {**data, "display_name": name}

    if provider == "twitter":
        response = httpx.post(
            "https://api.twitter.com/2/oauth2/token",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect,
                "code_verifier": pkce_verifier or "",
                "client_id": settings.twitter_client_id,
            },
            headers={"Authorization": f"Basic {_basic(settings.twitter_client_id, settings.twitter_client_secret)}"},
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        me = httpx.get(
            "https://api.twitter.com/2/users/me",
            headers={"Authorization": f"Bearer {data.get('access_token')}"},
            timeout=30,
        )
        username = ""
        if me.status_code < 400:
            username = ((me.json().get("data") or {}).get("username")) or ""
        return {**data, "display_name": username}

    if provider == "linkedin":
        response = httpx.post(
            "https://www.linkedin.com/oauth/v2/accessToken",
            data={
                "grant_type": "authorization_code",
                "code": code,
                "redirect_uri": redirect,
                "client_id": settings.linkedin_client_id,
                "client_secret": settings.linkedin_client_secret,
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        me = httpx.get(
            "https://api.linkedin.com/v2/userinfo",
            headers={"Authorization": f"Bearer {data.get('access_token')}"},
            timeout=30,
        )
        info = me.json() if me.status_code < 400 else {}
        sub = info.get("sub", "")
        return {**data, "display_name": info.get("name", ""), "person_urn": f"urn:li:person:{sub}" if sub else ""}

    if provider in ("facebook", "instagram"):
        response = httpx.get(
            "https://graph.facebook.com/v21.0/oauth/access_token",
            params={
                "client_id": settings.facebook_client_id,
                "client_secret": settings.facebook_client_secret,
                "redirect_uri": redirect,
                "code": code,
            },
            timeout=30,
        )
        response.raise_for_status()
        data = response.json()
        pages = httpx.get(
            "https://graph.facebook.com/v21.0/me/accounts",
            params={"access_token": data.get("access_token"), "fields": "id,name,access_token,instagram_business_account"},
            timeout=30,
        )
        page_list = pages.json().get("data", []) if pages.status_code < 400 else []
        return {**data, "pages": page_list, "display_name": "Facebook"}

    raise ValueError(f"No token exchange for {provider}")
