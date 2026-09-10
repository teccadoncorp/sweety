from __future__ import annotations

from typing import Any

import httpx

from app.connectors.store import get_connector, secrets_of
from app.core.config import get_settings, model_map


def search_web(query: str, brand_id=None, db=None) -> dict[str, Any]:
    settings = get_settings()
    tavily_key = settings.tavily_api_key
    if db is not None and brand_id is not None:
        row = get_connector(db, brand_id, "tavily")
        if row and row.status == "connected":
            tavily_key = secrets_of(row).get("api_key") or tavily_key

    if tavily_key:
        response = httpx.post(
            "https://api.tavily.com/search",
            json={"query": query, "max_results": 6, "search_depth": "basic"},
            headers={"Authorization": f"Bearer {tavily_key}"},
            timeout=40,
        )
        if response.status_code < 400:
            data = response.json()
            hits = [
                {"title": r.get("title"), "url": r.get("url"), "snippet": r.get("content")}
                for r in data.get("results") or []
            ]
            return {"ok": True, "provider": "tavily", "results": hits}

    if settings.brave_api_key:
        response = httpx.get(
            "https://api.search.brave.com/res/v1/web/search",
            params={"q": query, "count": 6},
            headers={"X-Subscription-Token": settings.brave_api_key, "Accept": "application/json"},
            timeout=30,
        )
        if response.status_code < 400:
            web = (response.json().get("web") or {}).get("results") or []
            hits = [{"title": r.get("title"), "url": r.get("url"), "snippet": r.get("description")} for r in web]
            return {"ok": True, "provider": "brave", "results": hits}

    if not settings.openrouter_api_key:
        return {"ok": False, "error": "No search provider. Set OPENROUTER_API_KEY or TAVILY_API_KEY."}

    response = httpx.post(
        f"{settings.openrouter_base_url}/chat/completions",
        headers={
            "Authorization": f"Bearer {settings.openrouter_api_key}",
            "HTTP-Referer": settings.sweety_public_url,
            "X-Title": settings.app_name,
        },
        json={
            "model": model_map()["search"],
            "messages": [
                {
                    "role": "system",
                    "content": "Search the public web. Return a compact JSON array of {title,url,snippet} only.",
                },
                {"role": "user", "content": query},
            ],
            "plugins": [{"id": "web", "max_results": 6}],
        },
        timeout=60,
    )
    if response.status_code >= 400:
        return {"ok": False, "error": f"OpenRouter search {response.status_code}: {response.text[:400]}"}
    from app.services.sanitize import text_from_content

    message = ((response.json().get("choices") or [{}])[0].get("message") or {})
    return {"ok": True, "provider": "openrouter_web", "summary": text_from_content(message.get("content"), 8000)}
