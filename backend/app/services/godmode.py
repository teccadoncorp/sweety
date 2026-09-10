from __future__ import annotations

import json
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings, model_map
from app.models.agent import Agent
from app.models.brand import Brand
from app.models.godmode import GodModeMessage
from app.services.sanitize import sanitize_json, strip_nuls, text_from_content
from app.tools.agent_tools import TOOL_SPECS, ToolExecutor
from app.workers.heartbeat import run_agent_heartbeat

GODMODE_EXTRA_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "update_brand_profile",
            "description": "Save optional brand logo URL, website, or app URL when the user provides them.",
            "parameters": {
                "type": "object",
                "properties": {
                    "logo_url": {"type": "string"},
                    "website_url": {"type": "string"},
                    "app_url": {"type": "string"},
                    "mission": {"type": "string"},
                    "voice_notes": {"type": "string"},
                    "audience": {"type": "string"},
                    "guidelines": {"type": "string"},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "wake_agent",
            "description": "Queue a heartbeat for a role (cmo, strategist, copywriter, seo, social, analyst, media, community, pr, email, crm, designer, video, lifecycle).",
            "parameters": {
                "type": "object",
                "properties": {"role": {"type": "string"}},
                "required": ["role"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "wake_all_agents",
            "description": "Wake every active agent in parallel (swarm).",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_pm_feature",
            "description": "Create a product Feature (epic) in the standalone Task console. Use this for product/engineering work, not marketing campaign tasks. Optionally attach user stories.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "stories": {
                        "type": "string",
                        "description": "Newline-separated user stories to create under the feature",
                    },
                },
                "required": ["title"],
            },
        },
    },
]


class GodModeExecutor(ToolExecutor):
    def update_brand_profile(
        self,
        logo_url: str | None = None,
        website_url: str | None = None,
        app_url: str | None = None,
        mission: str | None = None,
        voice_notes: str | None = None,
        audience: str | None = None,
        guidelines: str | None = None,
    ) -> dict:
        if logo_url is not None:
            self.brand.logo_url = logo_url
        if website_url is not None:
            self.brand.website_url = website_url
        if app_url is not None:
            self.brand.app_url = app_url
        if mission is not None:
            self.brand.mission = mission
        if voice_notes is not None:
            self.brand.voice_notes = voice_notes
        if audience is not None:
            self.brand.audience = audience
        if guidelines is not None:
            self.brand.guidelines = guidelines
        self.db.add(self.brand)
        self.db.flush()
        return {
            "ok": True,
            "logo_url": self.brand.logo_url,
            "website_url": self.brand.website_url,
            "app_url": self.brand.app_url,
        }

    def wake_agent(self, role: str) -> dict:
        if getattr(self.brand, "agents_paused", False):
            return {"ok": False, "error": "Kill switch is on"}
        agent = self._agent_by_role(role)
        if agent is None:
            return {"ok": False, "error": f"No agent with role {role}"}
        run_agent_heartbeat.delay(str(agent.id), "godmode")
        return {"ok": True, "queued": True, "agent_id": str(agent.id), "role": agent.role}

    def wake_all_agents(self) -> dict:
        if getattr(self.brand, "agents_paused", False):
            return {"ok": False, "error": "Kill switch is on", "queued": 0}
        rows = self.db.scalars(select(Agent).where(Agent.brand_id == self.brand.id, Agent.status == "active")).all()
        for agent in rows:
            run_agent_heartbeat.delay(str(agent.id), "godmode-swarm")
        return {"ok": True, "queued": len(rows), "roles": [a.role for a in rows]}

    def create_pm_feature(self, title: str, description: str = "", stories: str = "") -> dict:
        from app.services.pm import create_feature, decorate_feature, ensure_pm_project_for_brand

        project = ensure_pm_project_for_brand(self.db, self.brand)
        story_list = [line.strip() for line in (stories or "").splitlines() if line.strip()]
        feature = create_feature(
            self.db,
            project,
            title=title,
            description=description,
            source="godmode",
            stories=story_list,
        )
        payload = decorate_feature(self.db, feature, project)
        return {
            "ok": True,
            "feature": payload,
            "project_key": project.key,
            "workspace": "Sweety",
            "hint": "Open /pm to work this feature in the Task console.",
        }


def _image_urls_from_trace(trace: list) -> list[str]:
    urls: list[str] = []
    for event in trace:
        result = event.get("result") if isinstance(event, dict) else None
        if not isinstance(result, dict):
            continue
        for url in result.get("urls") or []:
            if isinstance(url, str) and url.startswith("http") and url not in urls:
                urls.append(url)
    return urls


def list_messages(db: Session, brand_id: UUID) -> list[GodModeMessage]:
    return list(
        db.scalars(
            select(GodModeMessage)
            .where(GodModeMessage.brand_id == brand_id)
            .order_by(GodModeMessage.created_at.asc())
        ).all()
    )


def reply(db: Session, brand: Brand, user_text: str) -> GodModeMessage:
    from app.services.loop import brand_memory_block, ensure_launch_campaign

    ensure_launch_campaign(db, brand)
    cmo = db.scalar(select(Agent).where(Agent.brand_id == brand.id, Agent.role == "cmo"))
    actor = cmo or db.scalar(select(Agent).where(Agent.brand_id == brand.id))
    if actor is None:
        raise ValueError("Brand has no agents yet")

    user_row = GodModeMessage(brand_id=brand.id, role="user", content=strip_nuls(user_text, 20_000))
    db.add(user_row)
    db.flush()

    history = list_messages(db, brand.id)
    settings = get_settings()
    system = f"""You are {settings.app_name} God Mode — the CMO sitting with the human board in a ChatGPT-style briefing.

Brand: {brand.name}
Mission: {brand.mission or "(not set)"}
{brand_memory_block(brand)}
Logo: {brand.logo_url or "(optional, not set)"}
Website: {brand.website_url or "(optional, not set)"}
App: {brand.app_url or "(optional, not set)"}
Agents paused: {getattr(brand, "agents_paused", False)}

The human will describe what they want in plain language. You:
1. Ask for logo, website, and app URL if they would help and are still missing — keep it optional, never block.
2. A first campaign is already opened from the mission if one was missing. Checkout or inspect it, write the brief, and make sure the copywriter has a first-post task. Use create_campaign only for additional campaigns.
3. Use tools to create tasks, then wake the right agents — or wake_all_agents to run the swarm in parallel.
4. You can score CRM leads and move deals with CRM tools.
5. When the board wants a product feature, epic, or engineering work item (not a marketing campaign task), call create_pm_feature. That lands in the separate Task console at /pm.
6. Reply in clean Markdown (headings, lists, bold). The UI renders it.
7. Nothing publishes without board approval. After drafts exist, tell the human to open Approvals.

Images:
- If they want a visual, FIRST ask which platform to post on: Instagram feed, Instagram story/reel, X/Twitter, LinkedIn, Facebook, Reddit, Pinterest, or TikTok.
- Do not call generate_image until they pick a platform (or you can infer one clearly).
- Then call generate_image with that `platform` so the aspect ratio is correct.
- After an image is generated, mention the ratio and that it will appear in this chat.

Never invent a live social post. Check connectors before promising publish.
"""

    messages: list[dict] = [{"role": "system", "content": system}]
    for row in history[-24:]:
        messages.append({"role": row.role if row.role in ("user", "assistant") else "user", "content": row.content})

    executor = GodModeExecutor(db, brand, actor)
    tools = [*TOOL_SPECS, *GODMODE_EXTRA_TOOLS]
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "HTTP-Referer": settings.sweety_public_url,
        "X-Title": f"{settings.app_name} God Mode",
    }
    if not settings.openrouter_api_key:
        assistant = GodModeMessage(
            brand_id=brand.id,
            role="assistant",
            content="OpenRouter is not configured, so I cannot plan yet. Add OPENROUTER_API_KEY and recreate the API container.",
        )
        db.add(assistant)
        db.commit()
        db.refresh(assistant)
        return assistant

    trace: list = []
    final = ""
    with httpx.Client(timeout=90.0) as client:
        for _ in range(settings.agent_max_tool_rounds):
            response = client.post(
                f"{settings.openrouter_base_url}/chat/completions",
                headers=headers,
                json={
                    "model": model_map()["chat"],
                    "messages": messages,
                    "tools": tools,
                    "tool_choice": "auto",
                },
            )
            if response.status_code >= 400:
                final = f"God Mode error {response.status_code}: {response.text[:400]}"
                break
            message = ((response.json().get("choices") or [{}])[0].get("message") or {})
            content = text_from_content(message.get("content"), 6000)
            if content:
                final = content
            messages.append(
                {
                    "role": "assistant",
                    "content": content or None,
                    "tool_calls": message.get("tool_calls") or None,
                }
            )
            calls = message.get("tool_calls") or []
            if not calls:
                break
            for call in calls:
                fn = call.get("function") or {}
                name = fn.get("name") or ""
                raw = fn.get("arguments") or "{}"
                try:
                    args = json.loads(raw) if isinstance(raw, str) else raw
                except json.JSONDecodeError:
                    args = {}
                result = executor(name, args or {})
                trace.append({"tool": name, "args": sanitize_json(args), "result": sanitize_json(result)})
                messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": call.get("id"),
                        "content": json.dumps(sanitize_json(result), default=str)[:8000],
                    }
                )

    image_urls = _image_urls_from_trace(trace)
    body = final or "I logged the brief. Ask me to turn it into a campaign when you are ready."
    for url in image_urls:
        if url and url not in body:
            body += f"\n\n![Generated visual]({url})"
    assistant = GodModeMessage(
        brand_id=brand.id,
        role="assistant",
        content=strip_nuls(body, 16_000),
        trace=sanitize_json(trace),
    )
    db.add(assistant)
    db.commit()
    db.refresh(assistant)
    return assistant
