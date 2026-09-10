from __future__ import annotations

import json
from uuid import UUID

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import get_settings, model_map
from app.models.pm import GOD_ROLES, PmGodModeMessage, PmProject, PmUser, PmWorkspace, PmWorkspaceMember
from app.services import pm as pm_svc
from app.services.sanitize import sanitize_json, strip_nuls, text_from_content

PM_GODMODE_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "list_projects",
            "description": "List projects in this workspace.",
            "parameters": {"type": "object", "properties": {}, "additionalProperties": False},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_features",
            "description": "List features (epics) in a project.",
            "parameters": {
                "type": "object",
                "properties": {"project_key": {"type": "string"}},
                "required": ["project_key"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_project",
            "description": "Create a project in this workspace.",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "key": {"type": "string"},
                    "description": {"type": "string"},
                },
                "required": ["name"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_feature",
            "description": "Create a product feature (epic). Only God Mode and workspace admins can do this. Optionally attach user stories.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_key": {"type": "string"},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "stories": {
                        "type": "string",
                        "description": "Newline-separated user stories to create under the feature",
                    },
                },
                "required": ["project_key", "title"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "create_issue",
            "description": "Create a story, task, or bug. Prefer attaching it to a feature.",
            "parameters": {
                "type": "object",
                "properties": {
                    "project_key": {"type": "string"},
                    "title": {"type": "string"},
                    "description": {"type": "string"},
                    "kind": {"type": "string", "enum": ["story", "task", "bug"]},
                    "feature_key": {"type": "string"},
                },
                "required": ["project_key", "title"],
            },
        },
    },
]


class PmGodModeExecutor:
    def __init__(self, db: Session, workspace: PmWorkspace, user: PmUser):
        self.db = db
        self.workspace = workspace
        self.user = user

    def __call__(self, name: str, args: dict) -> dict:
        handler = getattr(self, name, None)
        if handler is None:
            return {"ok": False, "error": f"Unknown tool {name}"}
        try:
            return handler(**(args or {}))
        except Exception as exc:  # noqa: BLE001
            return {"ok": False, "error": str(exc)}

    def _project(self, project_key: str) -> PmProject:
        project = self.db.scalar(
            select(PmProject).where(
                PmProject.workspace_id == self.workspace.id,
                PmProject.key == project_key.upper(),
            )
        )
        if project is None:
            raise ValueError(f"No project with key {project_key}")
        return project

    def list_projects(self) -> dict:
        rows = self.db.scalars(
            select(PmProject).where(PmProject.workspace_id == self.workspace.id)
        ).all()
        return {"ok": True, "projects": [pm_svc.decorate_project(self.db, row) for row in rows]}

    def list_features(self, project_key: str) -> dict:
        project = self._project(project_key)
        rows = list(project.features)
        return {
            "ok": True,
            "features": [pm_svc.decorate_feature(self.db, row, project) for row in rows],
        }

    def create_project(self, name: str, key: str = "", description: str = "") -> dict:
        project = pm_svc.create_project(self.db, self.workspace, name, key=key, description=description)
        return {"ok": True, "project": pm_svc.decorate_project(self.db, project)}

    def create_feature(
        self,
        project_key: str,
        title: str,
        description: str = "",
        stories: str = "",
    ) -> dict:
        project = self._project(project_key)
        story_list = [line.strip() for line in (stories or "").splitlines() if line.strip()]
        feature = pm_svc.create_feature(
            self.db,
            project,
            title=title,
            description=description,
            source="pm_godmode",
            created_by_user_id=self.user.id,
            stories=story_list,
        )
        return {"ok": True, "feature": pm_svc.decorate_feature(self.db, feature, project)}

    def create_issue(
        self,
        project_key: str,
        title: str,
        description: str = "",
        kind: str = "task",
        feature_key: str = "",
    ) -> dict:
        project = self._project(project_key)
        feature_id = None
        if feature_key:
            for feature in project.features:
                if feature_key.upper() in {self._feature_key(project, feature), f"F{feature.number}"}:
                    feature_id = feature.id
                    break
        issue = pm_svc.create_issue(
            self.db,
            project,
            title=title,
            description=description,
            kind=kind,
            feature_id=feature_id,
            reporter_id=self.user.id,
        )
        return {"ok": True, "issue": pm_svc.decorate_issue(self.db, issue, project)}

    def _feature_key(self, project: PmProject, feature) -> str:
        return pm_svc.feature_key(project, feature)


def list_messages(db: Session, workspace_id: UUID) -> list[PmGodModeMessage]:
    return list(
        db.scalars(
            select(PmGodModeMessage)
            .where(PmGodModeMessage.workspace_id == workspace_id)
            .order_by(PmGodModeMessage.created_at.asc())
        ).all()
    )


def serialize_message(message: PmGodModeMessage) -> dict:
    return {
        "id": str(message.id),
        "role": message.role,
        "content": message.content,
        "trace": message.trace,
        "created_at": message.created_at.isoformat() if message.created_at else None,
    }


def reply(db: Session, workspace: PmWorkspace, user: PmUser, user_text: str) -> PmGodModeMessage:
    member = db.scalar(
        select(PmWorkspaceMember).where(
            PmWorkspaceMember.workspace_id == workspace.id,
            PmWorkspaceMember.user_id == user.id,
        )
    )
    if member is None or member.role not in GOD_ROLES:
        raise PermissionError("Only God Mode can create features")

    user_row = PmGodModeMessage(
        workspace_id=workspace.id, role="user", content=strip_nuls(user_text, 20_000)
    )
    db.add(user_row)
    db.flush()

    history = list_messages(db, workspace.id)
    settings = get_settings()
    projects = db.scalars(select(PmProject).where(PmProject.workspace_id == workspace.id)).all()
    project_lines = [f"- {p.key}: {p.name}" for p in projects] or ["- none yet"]
    system = f"""You are God Mode for the Task console — a Jira-style product board.

Workspace: {workspace.name}
Projects:
{chr(10).join(project_lines)}

You create Features (epics). Members then break work into issues on the board.
When the human describes a product capability, call create_feature. Add stories when they are clear.
Use an existing project key, or create_project first if none fits.
Reply in clean Markdown. Confirm keys (CORE-F1) after you create work.
"""

    messages: list[dict] = [{"role": "system", "content": system}]
    for row in history[-24:]:
        messages.append(
            {"role": row.role if row.role in ("user", "assistant") else "user", "content": row.content}
        )

    if not settings.openrouter_api_key:
        assistant = PmGodModeMessage(
            workspace_id=workspace.id,
            role="assistant",
            content="OpenRouter is not configured, so I cannot create features yet. Add OPENROUTER_API_KEY.",
        )
        db.add(assistant)
        db.commit()
        db.refresh(assistant)
        return assistant

    executor = PmGodModeExecutor(db, workspace, user)
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "HTTP-Referer": settings.sweety_public_url,
        "X-Title": f"{settings.app_name} Task God Mode",
    }
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
                    "tools": PM_GODMODE_TOOLS,
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

    assistant = PmGodModeMessage(
        workspace_id=workspace.id,
        role="assistant",
        content=strip_nuls(final or "Feature logged. Open the board to keep going.", 16_000),
        trace=sanitize_json(trace),
    )
    db.add(assistant)
    db.commit()
    db.refresh(assistant)
    return assistant
