from __future__ import annotations

from typing import Any
from uuid import UUID

import httpx
from sqlalchemy.orm import Session

from app.connectors.store import get_connector, secrets_of


class PublishError(RuntimeError):
    pass


def _connected(db: Session, brand_id: UUID, provider: str):
    row = get_connector(db, brand_id, provider)
    if row is None or row.status != "connected":
        raise PublishError(f"{provider} is not connected for this brand")
    return row, secrets_of(row)


def post_reddit(db: Session, brand_id: UUID, title: str, text: str, subreddit: str | None = None) -> dict[str, Any]:
    row, secrets = _connected(db, brand_id, "reddit")
    sr = subreddit or (row.extra or {}).get("subreddit") or secrets.get("subreddit")
    if not sr:
        raise PublishError("Reddit post needs a subreddit")
    response = httpx.post(
        "https://oauth.reddit.com/api/submit",
        data={"sr": sr, "kind": "self", "title": title[:300], "text": text},
        headers={
            "Authorization": f"Bearer {secrets.get('access_token')}",
            "User-Agent": "sweety-control-plane/0.1",
        },
        timeout=30,
    )
    body = response.json() if response.headers.get("content-type", "").startswith("application/json") else {"raw": response.text}
    if response.status_code >= 400:
        raise PublishError(f"Reddit {response.status_code}: {response.text[:400]}")
    return {"ok": True, "provider": "reddit", "result": body}


def post_twitter(db: Session, brand_id: UUID, text: str) -> dict[str, Any]:
    _, secrets = _connected(db, brand_id, "twitter")
    response = httpx.post(
        "https://api.twitter.com/2/tweets",
        json={"text": text[:280]},
        headers={"Authorization": f"Bearer {secrets.get('access_token')}"},
        timeout=30,
    )
    if response.status_code >= 400:
        raise PublishError(f"Twitter {response.status_code}: {response.text[:400]}")
    return {"ok": True, "provider": "twitter", "result": response.json()}


def post_linkedin(db: Session, brand_id: UUID, text: str) -> dict[str, Any]:
    row, secrets = _connected(db, brand_id, "linkedin")
    urn = secrets.get("person_urn") or (row.extra or {}).get("person_urn")
    if not urn:
        raise PublishError("LinkedIn person URN missing — reconnect or paste person_urn")
    payload = {
        "author": urn,
        "lifecycleState": "PUBLISHED",
        "specificContent": {
            "com.linkedin.ugc.ShareContent": {
                "shareCommentary": {"text": text},
                "shareMediaCategory": "NONE",
            }
        },
        "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"},
    }
    response = httpx.post(
        "https://api.linkedin.com/v2/ugcPosts",
        json=payload,
        headers={
            "Authorization": f"Bearer {secrets.get('access_token')}",
            "X-Restli-Protocol-Version": "2.0.0",
        },
        timeout=30,
    )
    if response.status_code >= 400:
        raise PublishError(f"LinkedIn {response.status_code}: {response.text[:400]}")
    return {"ok": True, "provider": "linkedin", "result": response.json() if response.text else {}}


def post_facebook(db: Session, brand_id: UUID, text: str, image_url: str | None = None) -> dict[str, Any]:
    row, secrets = _connected(db, brand_id, "facebook")
    page_id = secrets.get("page_id") or (row.extra or {}).get("page_id")
    token = secrets.get("page_token") or secrets.get("access_token")
    if not page_id:
        raise PublishError("Pick a Facebook Page after connecting")
    data: dict[str, Any] = {"message": text, "access_token": token}
    endpoint = f"https://graph.facebook.com/v21.0/{page_id}/feed"
    if image_url:
        endpoint = f"https://graph.facebook.com/v21.0/{page_id}/photos"
        data["url"] = image_url
        data["caption"] = text
    response = httpx.post(endpoint, data=data, timeout=30)
    if response.status_code >= 400:
        raise PublishError(f"Facebook {response.status_code}: {response.text[:400]}")
    return {"ok": True, "provider": "facebook", "result": response.json()}


def post_instagram(db: Session, brand_id: UUID, image_url: str, caption: str) -> dict[str, Any]:
    row, secrets = _connected(db, brand_id, "instagram")
    ig_id = secrets.get("ig_user_id") or (row.extra or {}).get("ig_user_id")
    token = secrets.get("page_token") or secrets.get("access_token")
    if not ig_id:
        raise PublishError("Pick an Instagram business account after connecting Facebook")
    if not image_url or image_url.startswith("http://localhost"):
        raise PublishError("Instagram needs a publicly reachable image URL (not localhost)")
    create = httpx.post(
        f"https://graph.facebook.com/v21.0/{ig_id}/media",
        data={"image_url": image_url, "caption": caption, "access_token": token},
        timeout=30,
    )
    if create.status_code >= 400:
        raise PublishError(f"Instagram container {create.status_code}: {create.text[:400]}")
    creation_id = create.json().get("id")
    publish = httpx.post(
        f"https://graph.facebook.com/v21.0/{ig_id}/media_publish",
        data={"creation_id": creation_id, "access_token": token},
        timeout=30,
    )
    if publish.status_code >= 400:
        raise PublishError(f"Instagram publish {publish.status_code}: {publish.text[:400]}")
    return {"ok": True, "provider": "instagram", "result": publish.json()}


def publish(db: Session, brand_id: UUID, platform: str, **kwargs: Any) -> dict[str, Any]:
    platform = platform.lower().strip()
    if platform in ("x", "x/twitter"):
        platform = "twitter"
    if platform == "reddit":
        return post_reddit(db, brand_id, kwargs.get("title") or kwargs.get("text", "")[:80], kwargs.get("text", ""), kwargs.get("subreddit"))
    if platform == "twitter":
        return post_twitter(db, brand_id, kwargs.get("text", ""))
    if platform == "linkedin":
        return post_linkedin(db, brand_id, kwargs.get("text", ""))
    if platform == "facebook":
        return post_facebook(db, brand_id, kwargs.get("text", ""), kwargs.get("image_url"))
    if platform == "instagram":
        return post_instagram(db, brand_id, kwargs.get("image_url") or "", kwargs.get("text") or kwargs.get("caption") or "")
    raise PublishError(f"Unsupported platform {platform}")
