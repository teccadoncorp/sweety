from __future__ import annotations

from datetime import UTC, datetime, timedelta
from decimal import Decimal
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.connectors.heygen import generate_video, video_status
from app.connectors.images import generate_image
from app.connectors.mcp import call_tool as mcp_call_tool
from app.connectors.mcp import list_tools as mcp_list_tools
from app.connectors.search import search_web
from app.connectors.store import public_connector
from app.core.config import get_settings
from app.models.agent import Agent
from app.models.approval import Approval
from app.models.artifact import Artifact
from app.models.brand import Brand
from app.models.campaign import Campaign
from app.models.connector import Connector
from app.models.crm import CrmAccount, CrmActivity, CrmContact, CrmDeal, DEAL_STAGES
from app.models.media_asset import MediaAsset
from app.models.task import Task
from app.services.publish import execute_social_payload
from app.services.sanitize import sanitize_json, strip_nuls

TOOL_SPECS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_brand_context",
            "description": "Read the brand mission, voice, budget, and org.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_campaign",
            "description": "Read a campaign by id.",
            "parameters": {
                "type": "object",
                "properties": {"campaign_id": {"type": "string"}},
                "required": ["campaign_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_inbox",
            "description": "List tasks assigned to you that are ready, blocked, or already checked out by you.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "checkout_task",
            "description": "Atomically check out a ready task so only you work on it.",
            "parameters": {
                "type": "object",
                "properties": {"task_id": {"type": "string"}},
                "required": ["task_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "update_task",
            "description": "Update a task you own. Status: backlog, ready, checked_out, review, done, blocked.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                    "status": {"type": "string"},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                },
                "required": ["task_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_task",
            "description": "Create a child or sibling task, optionally assigned to a teammate by role.",
            "parameters": {
                "type": "object",
                "properties": {
                    "campaign_id": {"type": "string"},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "assignee_role": {"type": "string"},
                    "parent_id": {"type": "string"},
                    "priority": {"type": "integer"},
                    "status": {"type": "string"},
                },
                "required": ["campaign_id", "title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "delegate_task",
            "description": "Reassign a task to a teammate by role.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                    "assignee_role": {"type": "string"},
                },
                "required": ["task_id", "assignee_role"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "post_artifact",
            "description": "Save a brief, copy draft, or calendar as an artifact on a task.",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string"},
                    "title": {"type": "string"},
                    "content": {"type": "string"},
                    "kind": {"type": "string"},
                },
                "required": ["task_id", "title", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "request_approval",
            "description": "Ask the human board to approve strategy, hire, or publish.",
            "parameters": {
                "type": "object",
                "properties": {
                    "kind": {"type": "string"},
                    "subject_type": {"type": "string"},
                    "subject_id": {"type": "string"},
                    "summary": {"type": "string"},
                },
                "required": ["kind", "summary"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_connectors",
            "description": "See which social, search, video, and MCP connectors are connected.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_web",
            "description": "Search the public internet for research, trends, or fact-checking.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_image",
            "description": "Generate a marketing image. Ask which social platform first, then pass platform so aspect ratio is set (instagram 4:5, instagram_story 9:16, twitter 16:9, linkedin 1.91:1, facebook 1.91:1, reddit 16:9, pinterest 2:3, tiktok 9:16).",
            "parameters": {
                "type": "object",
                "properties": {
                    "prompt": {"type": "string"},
                    "platform": {
                        "type": "string",
                        "description": "instagram, instagram_story, twitter, linkedin, facebook, reddit, pinterest, tiktok, youtube",
                    },
                    "aspect_ratio": {"type": "string"},
                    "task_id": {"type": "string"},
                    "model": {"type": "string"},
                },
                "required": ["prompt"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "generate_heygen_video",
            "description": "Generate a HeyGen avatar video from a script. Check status with video_id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "script": {"type": "string"},
                    "avatar_id": {"type": "string"},
                    "voice_id": {"type": "string"},
                    "task_id": {"type": "string"},
                },
                "required": ["script"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "check_heygen_video",
            "description": "Poll a HeyGen video job.",
            "parameters": {
                "type": "object",
                "properties": {"video_id": {"type": "string"}},
                "required": ["video_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "post_social",
            "description": "Queue or publish to reddit, twitter, linkedin, facebook, or instagram. Live posts need board approval unless already approved.",
            "parameters": {
                "type": "object",
                "properties": {
                    "platform": {"type": "string"},
                    "text": {"type": "string"},
                    "title": {"type": "string"},
                    "image_url": {"type": "string"},
                    "subreddit": {"type": "string"},
                    "task_id": {"type": "string"},
                    "approval_id": {"type": "string"},
                },
                "required": ["platform", "text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_mcp_tools",
            "description": "List tools from connected MCP servers for this brand.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "call_mcp_tool",
            "description": "Call a tool on a connected MCP server.",
            "parameters": {
                "type": "object",
                "properties": {
                    "server_id": {"type": "string"},
                    "tool": {"type": "string"},
                    "arguments": {"type": "object"},
                },
                "required": ["server_id", "tool"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "crm_board",
            "description": "Read CRM HUD: pipeline value, stages, hot leads, contact counts.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "crm_search",
            "description": "Search CRM contacts, accounts, and deals by name, email, or company.",
            "parameters": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "crm_upsert_contact",
            "description": "Create or update a CRM contact. Match by email when provided.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "email": {"type": "string"},
                    "title": {"type": "string"},
                    "company": {"type": "string"},
                    "channel": {"type": "string"},
                    "status": {"type": "string"},
                    "temperature": {"type": "string"},
                    "signal_score": {"type": "integer"},
                    "next_action": {"type": "string"},
                    "notes": {"type": "string"},
                    "tags": {"type": "array", "items": {"type": "string"}},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "crm_upsert_account",
            "description": "Create or update a CRM account/company.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "domain": {"type": "string"},
                    "industry": {"type": "string"},
                    "signal_score": {"type": "integer"},
                    "notes": {"type": "string"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "crm_upsert_deal",
            "description": "Create or update a pipeline deal. Stages: signal, qualify, propose, commit, won, lost.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "deal_id": {"type": "string"},
                    "contact_email": {"type": "string"},
                    "stage": {"type": "string"},
                    "value_usd": {"type": "number"},
                    "probability": {"type": "integer"},
                    "notes": {"type": "string"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "crm_log_activity",
            "description": "Log a CRM touch: note, call, email, meeting, ai, touch.",
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "body": {"type": "string"},
                    "kind": {"type": "string"},
                    "contact_email": {"type": "string"},
                    "deal_id": {"type": "string"},
                },
                "required": ["title", "body"],
            },
        },
    },
]


class ToolExecutor:
    def __init__(self, db: Session, brand: Brand, agent: Agent):
        self.db = db
        self.brand = brand
        self.agent = agent

    def __call__(self, name: str, args: dict[str, Any]) -> dict[str, Any]:
        handler = getattr(self, name, None)
        if handler is None:
            return {"ok": False, "error": f"Unknown tool {name}"}
        try:
            with self.db.begin_nested():
                return handler(**(args or {}))
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def _agent_by_role(self, role: str) -> Agent | None:
        return self.db.scalar(
            select(Agent).where(Agent.brand_id == self.brand.id, Agent.role == role.lower())
        )

    def _task(self, task_id: str) -> Task:
        task = self.db.get(Task, UUID(task_id))
        if task is None or task.brand_id != self.brand.id:
            raise ValueError("Task not found")
        return task

    def get_brand_context(self) -> dict[str, Any]:
        org = self.db.scalars(select(Agent).where(Agent.brand_id == self.brand.id)).all()
        return {
            "ok": True,
            "brand": {
                "id": str(self.brand.id),
                "name": self.brand.name,
                "mission": self.brand.mission,
                "voice_notes": self.brand.voice_notes,
                "logo_url": self.brand.logo_url,
                "website_url": self.brand.website_url,
                "app_url": self.brand.app_url,
                "monthly_budget_usd": str(self.brand.monthly_budget_usd),
            },
            "you": {"id": str(self.agent.id), "role": self.agent.role, "title": self.agent.title},
            "org": [{"id": str(a.id), "role": a.role, "title": a.title, "status": a.status} for a in org],
        }

    def get_campaign(self, campaign_id: str) -> dict[str, Any]:
        campaign = self.db.get(Campaign, UUID(campaign_id))
        if campaign is None or campaign.brand_id != self.brand.id:
            return {"ok": False, "error": "Campaign not found"}
        return {
            "ok": True,
            "campaign": {
                "id": str(campaign.id),
                "name": campaign.name,
                "goal": campaign.goal,
                "brief": campaign.brief,
                "status": campaign.status,
            },
        }

    def list_inbox(self) -> dict[str, Any]:
        rows = self.db.scalars(
            select(Task).where(
                Task.brand_id == self.brand.id,
                Task.assignee_agent_id == self.agent.id,
                Task.status.in_(["ready", "checked_out", "blocked", "review"]),
            )
        ).all()
        return {
            "ok": True,
            "tasks": [
                {
                    "id": str(t.id),
                    "campaign_id": str(t.campaign_id),
                    "title": t.title,
                    "description": t.description,
                    "status": t.status,
                    "priority": t.priority,
                }
                for t in rows
            ],
        }

    def checkout_task(self, task_id: str) -> dict[str, Any]:
        task = self._task(task_id)
        now = datetime.now(UTC)
        lease_ok = task.lease_expires_at is None or task.lease_expires_at < now
        owned = task.checked_out_by == self.agent.id
        if task.status not in ("ready", "checked_out", "blocked") and not owned:
            return {"ok": False, "error": f"Task is {task.status} and cannot be checked out"}
        if task.checked_out_by and not owned and not lease_ok:
            return {"ok": False, "error": "Task is checked out by another agent"}
        if task.assignee_agent_id and task.assignee_agent_id != self.agent.id:
            return {"ok": False, "error": "Task is assigned to someone else"}
        task.assignee_agent_id = self.agent.id
        task.checked_out_by = self.agent.id
        task.status = "checked_out"
        task.lease_expires_at = now + timedelta(minutes=get_settings().checkout_lease_minutes)
        self.db.add(task)
        self.db.flush()
        return {"ok": True, "task_id": str(task.id), "status": task.status}

    def update_task(
        self,
        task_id: str,
        status: str | None = None,
        title: str | None = None,
        description: str | None = None,
    ) -> dict[str, Any]:
        task = self._task(task_id)
        if task.checked_out_by not in (None, self.agent.id) and task.assignee_agent_id != self.agent.id:
            return {"ok": False, "error": "You do not own this task"}
        if title:
            task.title = title
        if description is not None:
            task.description = description
        if status:
            task.status = status
            if status in ("done", "review", "ready", "backlog"):
                task.checked_out_by = None
                task.lease_expires_at = None
        self.db.add(task)
        self.db.flush()
        return {"ok": True, "task_id": str(task.id), "status": task.status}

    def create_task(
        self,
        campaign_id: str,
        title: str,
        description: str = "",
        assignee_role: str | None = None,
        parent_id: str | None = None,
        priority: int = 2,
        status: str = "ready",
    ) -> dict[str, Any]:
        campaign = self.db.get(Campaign, UUID(campaign_id))
        if campaign is None or campaign.brand_id != self.brand.id:
            return {"ok": False, "error": "Campaign not found"}
        assignee_id = self.agent.id
        if assignee_role:
            other = self._agent_by_role(assignee_role)
            if other:
                assignee_id = other.id
        task = Task(
            brand_id=self.brand.id,
            campaign_id=campaign.id,
            parent_id=UUID(parent_id) if parent_id else None,
            assignee_agent_id=assignee_id,
            title=title,
            description=description or "",
            priority=priority,
            status=status,
        )
        self.db.add(task)
        self.db.flush()
        return {"ok": True, "task_id": str(task.id), "assignee_agent_id": str(assignee_id)}

    def delegate_task(self, task_id: str, assignee_role: str) -> dict[str, Any]:
        task = self._task(task_id)
        other = self._agent_by_role(assignee_role)
        if other is None:
            return {"ok": False, "error": f"No agent with role {assignee_role}"}
        task.assignee_agent_id = other.id
        task.status = "ready"
        task.checked_out_by = None
        task.lease_expires_at = None
        self.db.add(task)
        self.db.flush()
        return {"ok": True, "task_id": str(task.id), "assignee_agent_id": str(other.id)}

    def post_artifact(
        self, task_id: str, title: str, content: str, kind: str = "markdown"
    ) -> dict[str, Any]:
        task = self._task(task_id)
        artifact = Artifact(
            brand_id=self.brand.id,
            campaign_id=task.campaign_id,
            task_id=task.id,
            created_by_agent_id=self.agent.id,
            kind=kind,
            title=strip_nuls(title, 300),
            content=strip_nuls(content, 100_000),
        )
        self.db.add(artifact)
        if kind in ("brief", "campaign-brief") and content:
            campaign = self.db.get(Campaign, task.campaign_id)
            if campaign and not campaign.brief:
                campaign.brief = content
                if campaign.status == "draft":
                    campaign.status = "awaiting_approval"
                self.db.add(campaign)
        self.db.flush()
        return {"ok": True, "artifact_id": str(artifact.id)}

    def request_approval(
        self,
        kind: str,
        summary: str,
        subject_type: str = "campaign",
        subject_id: str | None = None,
    ) -> dict[str, Any]:
        approval = Approval(
            brand_id=self.brand.id,
            kind=kind,
            status="pending",
            subject_type=subject_type,
            subject_id=UUID(subject_id) if subject_id else None,
            requested_by_agent_id=self.agent.id,
            payload={"summary": summary},
        )
        self.db.add(approval)
        if subject_id and subject_type == "campaign":
            campaign = self.db.get(Campaign, UUID(subject_id))
            if campaign and campaign.brand_id == self.brand.id:
                campaign.status = "awaiting_approval"
                self.db.add(campaign)
        self.db.flush()
        return {"ok": True, "approval_id": str(approval.id)}

    def list_connectors(self) -> dict[str, Any]:
        rows = self.db.scalars(select(Connector).where(Connector.brand_id == self.brand.id)).all()
        return {"ok": True, "connectors": [public_connector(r) for r in rows]}

    def search_web(self, query: str) -> dict[str, Any]:
        return search_web(query, brand_id=self.brand.id, db=self.db)

    def generate_image(
        self,
        prompt: str,
        task_id: str | None = None,
        model: str | None = None,
        platform: str | None = None,
        aspect_ratio: str | None = None,
    ) -> dict[str, Any]:
        result = generate_image(prompt, model=model, platform=platform, aspect_ratio=aspect_ratio)
        if not result.get("ok"):
            return result
        url = (result.get("urls") or [""])[0]
        asset = MediaAsset(
            brand_id=self.brand.id,
            task_id=UUID(task_id) if task_id else None,
            created_by_agent_id=self.agent.id,
            kind="image",
            provider="openrouter",
            prompt=prompt,
            url=url,
            extra=sanitize_json(
                {
                    "model": result.get("model"),
                    "urls": result.get("urls"),
                    "platform": result.get("platform"),
                    "aspect_ratio": result.get("aspect_ratio"),
                }
            ),
        )
        if task_id:
            task = self._task(task_id)
            asset.campaign_id = task.campaign_id
        self.db.add(asset)
        self.db.flush()
        result["asset_id"] = str(asset.id)
        return result

    def generate_heygen_video(
        self,
        script: str,
        avatar_id: str | None = None,
        voice_id: str | None = None,
        task_id: str | None = None,
    ) -> dict[str, Any]:
        result = generate_video(script, db=self.db, brand_id=self.brand.id, avatar_id=avatar_id, voice_id=voice_id)
        if not result.get("ok"):
            return result
        asset = MediaAsset(
            brand_id=self.brand.id,
            task_id=UUID(task_id) if task_id else None,
            created_by_agent_id=self.agent.id,
            kind="video",
            provider="heygen",
            prompt=script,
            external_id=result.get("video_id") or "",
            extra=sanitize_json(result),
        )
        if task_id:
            asset.campaign_id = self._task(task_id).campaign_id
        self.db.add(asset)
        self.db.flush()
        result["asset_id"] = str(asset.id)
        return result

    def check_heygen_video(self, video_id: str) -> dict[str, Any]:
        return video_status(video_id, db=self.db, brand_id=self.brand.id)

    def post_social(
        self,
        platform: str,
        text: str,
        title: str | None = None,
        image_url: str | None = None,
        subreddit: str | None = None,
        task_id: str | None = None,
        approval_id: str | None = None,
    ) -> dict[str, Any]:
        payload = {
            "platform": platform,
            "text": text,
            "title": title,
            "image_url": image_url,
            "subreddit": subreddit,
            "summary": f"Publish to {platform}: {(title or text)[:180]}",
        }
        if get_settings().require_publish_approval:
            approved = None
            if approval_id:
                approved = self.db.get(Approval, UUID(approval_id))
            if approved is None or approved.brand_id != self.brand.id or approved.status != "approved":
                approval = Approval(
                    brand_id=self.brand.id,
                    kind="publish",
                    status="pending",
                    subject_type="task" if task_id else "brand",
                    subject_id=UUID(task_id) if task_id else None,
                    requested_by_agent_id=self.agent.id,
                    payload=payload,
                )
                self.db.add(approval)
                self.db.flush()
                return {
                    "ok": True,
                    "queued": True,
                    "needs_approval": True,
                    "approval_id": str(approval.id),
                    "detail": "Board must approve before this goes live.",
                }
        result = execute_social_payload(self.db, self.brand.id, payload)
        if result.get("ok") and task_id:
            self.post_artifact(task_id, f"Posted to {platform}", text, kind="social-post")
        return result

    def list_mcp_tools(self) -> dict[str, Any]:
        return mcp_list_tools(self.db, self.brand.id)

    def call_mcp_tool(self, server_id: str, tool: str, arguments: dict | None = None) -> dict[str, Any]:
        return mcp_call_tool(self.db, self.brand.id, server_id, tool, arguments)

    def crm_board(self) -> dict[str, Any]:
        from app.services.crm import board_stats

        stats = board_stats(self.db, self.brand.id)
        stats["ok"] = True
        stats["pipeline_usd"] = str(stats["pipeline_usd"])
        stats["won_usd"] = str(stats["won_usd"])
        return stats

    def crm_search(self, query: str) -> dict[str, Any]:
        from app.services.crm import search_records

        found = search_records(self.db, self.brand.id, query)
        return {
            "ok": True,
            "contacts": [
                {
                    "id": str(c.id),
                    "name": c.name,
                    "email": c.email,
                    "company": c.company,
                    "temperature": c.temperature,
                    "signal_score": c.signal_score,
                    "next_action": c.next_action,
                }
                for c in found["contacts"]
            ],
            "accounts": [{"id": str(a.id), "name": a.name, "domain": a.domain, "signal_score": a.signal_score} for a in found["accounts"]],
            "deals": [
                {
                    "id": str(d.id),
                    "name": d.name,
                    "stage": d.stage,
                    "value_usd": str(d.value_usd),
                }
                for d in found["deals"]
            ],
        }

    def _contact_by_email(self, email: str) -> CrmContact | None:
        email = (email or "").strip().lower()
        if not email:
            return None
        return self.db.scalar(
            select(CrmContact).where(CrmContact.brand_id == self.brand.id, CrmContact.email == email)
        )

    def crm_upsert_contact(
        self,
        name: str,
        email: str = "",
        title: str = "",
        company: str = "",
        channel: str = "web",
        status: str = "lead",
        temperature: str = "cool",
        signal_score: int = 35,
        next_action: str = "",
        notes: str = "",
        tags: list[str] | None = None,
    ) -> dict[str, Any]:
        email = (email or "").strip().lower()
        row = self._contact_by_email(email) if email else None
        if row is None:
            row = CrmContact(brand_id=self.brand.id, name=name)
            self.db.add(row)
        row.name = name
        if email:
            row.email = email
        if title:
            row.title = title
        if company:
            row.company = company
        if channel:
            row.channel = channel
        if status:
            row.status = status
        if temperature:
            row.temperature = temperature
        row.signal_score = max(0, min(100, int(signal_score)))
        if next_action:
            row.next_action = next_action
        if notes:
            row.notes = notes
        if tags is not None:
            row.tags = tags
        row.last_touch_at = datetime.now(UTC)
        self.db.flush()
        return {"ok": True, "contact_id": str(row.id), "email": row.email, "signal_score": row.signal_score}

    def crm_upsert_account(
        self,
        name: str,
        domain: str = "",
        industry: str = "",
        signal_score: int = 40,
        notes: str = "",
    ) -> dict[str, Any]:
        row = self.db.scalar(
            select(CrmAccount).where(CrmAccount.brand_id == self.brand.id, CrmAccount.name.ilike(name))
        )
        if row is None and domain:
            row = self.db.scalar(
                select(CrmAccount).where(CrmAccount.brand_id == self.brand.id, CrmAccount.domain == domain.lower())
            )
        if row is None:
            row = CrmAccount(brand_id=self.brand.id, name=name)
            self.db.add(row)
        row.name = name
        if domain:
            row.domain = domain.lower()
        if industry:
            row.industry = industry
        row.signal_score = max(0, min(100, int(signal_score)))
        if notes:
            row.notes = notes
        self.db.flush()
        return {"ok": True, "account_id": str(row.id)}

    def crm_upsert_deal(
        self,
        name: str,
        deal_id: str | None = None,
        contact_email: str | None = None,
        stage: str = "signal",
        value_usd: float = 0,
        probability: int = 20,
        notes: str = "",
    ) -> dict[str, Any]:
        row = None
        if deal_id:
            row = self.db.get(CrmDeal, UUID(deal_id))
            if row and row.brand_id != self.brand.id:
                row = None
        if row is None:
            row = CrmDeal(brand_id=self.brand.id, name=name)
            self.db.add(row)
        row.name = name
        if stage in DEAL_STAGES:
            row.stage = stage
        row.value_usd = Decimal(str(value_usd))
        row.probability = max(0, min(100, int(probability)))
        if notes:
            row.notes = notes
        if contact_email:
            contact = self._contact_by_email(contact_email)
            if contact:
                row.contact_id = contact.id
                row.account_id = contact.account_id
        self.db.flush()
        return {"ok": True, "deal_id": str(row.id), "stage": row.stage, "value_usd": str(row.value_usd)}

    def crm_log_activity(
        self,
        title: str,
        body: str,
        kind: str = "note",
        contact_email: str | None = None,
        deal_id: str | None = None,
    ) -> dict[str, Any]:
        contact = self._contact_by_email(contact_email or "")
        activity = CrmActivity(
            brand_id=self.brand.id,
            contact_id=contact.id if contact else None,
            account_id=contact.account_id if contact else None,
            deal_id=UUID(deal_id) if deal_id else None,
            agent_id=self.agent.id,
            kind=kind or "note",
            title=strip_nuls(title, 240),
            body=strip_nuls(body, 8000),
        )
        self.db.add(activity)
        if contact:
            contact.last_touch_at = datetime.now(UTC)
        self.db.flush()
        return {"ok": True, "activity_id": str(activity.id)}
