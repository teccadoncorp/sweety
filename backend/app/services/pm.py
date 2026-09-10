from __future__ import annotations

import re
from uuid import UUID

from datetime import UTC, datetime, timedelta

from fastapi import HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.exc import ProgrammingError
from sqlalchemy.orm import Session

from app.core.security import hash_password
from app.models.brand import Brand
from app.models.pm import (
    FEATURE_STATUSES,
    GOD_ROLES,
    ISSUE_KINDS,
    ISSUE_STATUSES,
    MEMBER_ROLES,
    PmFeature,
    PmIssue,
    PmProject,
    PmUser,
    PmWorkspace,
    PmWorkspaceMember,
)

DEFAULT_WORKSPACE_SLUG = "sweety"
DEFAULT_WORKSPACE_NAME = "Sweety"
PM_ADMIN_EMAIL = "contact@cpdash.ai"
PM_ADMIN_PASSWORD = "supersecret123"
PM_ADMIN_NAME = "CPDash Admin"


def slugify(value: str) -> str:
    text = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return text[:80] or "workspace"


def project_key_from_name(name: str) -> str:
    letters = "".join(ch for ch in name.upper() if ch.isalnum())[:6]
    return letters or "PROJ"


def feature_key(project: PmProject, feature: PmFeature) -> str:
    return f"{project.key}-F{feature.number}"


def issue_key(project: PmProject, issue: PmIssue) -> str:
    return f"{project.key}-{issue.number}"


def next_feature_number(db: Session, project_id: UUID) -> int:
    last = db.scalar(select(func.max(PmFeature.number)).where(PmFeature.project_id == project_id))
    return (last or 0) + 1


def next_issue_number(db: Session, project_id: UUID) -> int:
    last = db.scalar(select(func.max(PmIssue.number)).where(PmIssue.project_id == project_id))
    return (last or 0) + 1


def display_of(user: PmUser | None) -> str:
    if user is None:
        return ""
    return user.display_name or user.email.split("@")[0]


def ensure_unique_slug(db: Session, desired: str) -> str:
    base = slugify(desired)
    slug = base
    n = 2
    while db.scalar(select(PmWorkspace.id).where(PmWorkspace.slug == slug)):
        slug = f"{base}-{n}"[:80]
        n += 1
    return slug


def ensure_unique_key(db: Session, workspace_id: UUID, desired: str) -> str:
    base = project_key_from_name(desired)
    key = base
    n = 2
    while db.scalar(
        select(PmProject.id).where(PmProject.workspace_id == workspace_id, PmProject.key == key)
    ):
        suffix = str(n)
        key = f"{base[: 12 - len(suffix)]}{suffix}"
        n += 1
    return key


def default_workspace(db: Session) -> PmWorkspace:
    workspace = db.scalar(select(PmWorkspace).where(PmWorkspace.slug == DEFAULT_WORKSPACE_SLUG))
    if workspace:
        return workspace
    workspace = PmWorkspace(name=DEFAULT_WORKSPACE_NAME, slug=DEFAULT_WORKSPACE_SLUG)
    db.add(workspace)
    db.flush()
    return workspace


def add_member(db: Session, workspace: PmWorkspace, user: PmUser, role: str) -> PmWorkspaceMember:
    existing = db.scalar(
        select(PmWorkspaceMember).where(
            PmWorkspaceMember.workspace_id == workspace.id,
            PmWorkspaceMember.user_id == user.id,
        )
    )
    if existing:
        if role in GOD_ROLES and existing.role not in GOD_ROLES:
            existing.role = role
        return existing
    member = PmWorkspaceMember(workspace_id=workspace.id, user_id=user.id, role=role)
    db.add(member)
    db.flush()
    return member


def membership(db: Session, workspace_id: UUID, user_id: UUID) -> PmWorkspaceMember:
    row = db.scalar(
        select(PmWorkspaceMember).where(
            PmWorkspaceMember.workspace_id == workspace_id,
            PmWorkspaceMember.user_id == user_id,
        )
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Workspace not found")
    return row


def require_god(member: PmWorkspaceMember) -> None:
    if member.role not in GOD_ROLES:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only God Mode or workspace admins can create features",
        )


def get_project_for_user(db: Session, project_id: UUID, user_id: UUID) -> tuple[PmProject, PmWorkspaceMember]:
    project = db.get(PmProject, project_id)
    if project is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Project not found")
    member = membership(db, project.workspace_id, user_id)
    return project, member


def user_workspaces(db: Session, user: PmUser) -> list[dict]:
    rows = db.scalars(select(PmWorkspaceMember).where(PmWorkspaceMember.user_id == user.id)).all()
    out = []
    for row in rows:
        workspace = db.get(PmWorkspace, row.workspace_id)
        if workspace is None:
            continue
        out.append(
            {
                "id": workspace.id,
                "name": workspace.name,
                "slug": workspace.slug,
                "role": row.role,
                "can_create_features": row.role in GOD_ROLES,
            }
        )
    return out


def is_online(user: PmUser | None) -> bool:
    if user is None or user.last_seen_at is None:
        return False
    seen = user.last_seen_at
    if seen.tzinfo is None:
        seen = seen.replace(tzinfo=UTC)
    return datetime.now(UTC) - seen <= timedelta(minutes=3)


def touch_presence(db: Session, user: PmUser) -> None:
    user.last_seen_at = datetime.now(UTC)
    db.add(user)
    db.commit()


def decorate_member(db: Session, row: PmWorkspaceMember) -> dict:
    user = db.get(PmUser, row.user_id)
    return {
        "id": row.id,
        "user_id": row.user_id,
        "email": user.email if user else "",
        "display_name": display_of(user),
        "role": row.role,
        "online": is_online(user),
        "last_seen_at": user.last_seen_at if user else None,
        "created_at": row.created_at,
    }


def decorate_workspace(db: Session, workspace: PmWorkspace, role: str) -> dict:
    members = db.scalars(
        select(PmWorkspaceMember).where(PmWorkspaceMember.workspace_id == workspace.id)
    ).all()
    return {
        "id": workspace.id,
        "name": workspace.name,
        "slug": workspace.slug,
        "role": role,
        "can_create_features": role in GOD_ROLES,
        "created_at": workspace.created_at,
        "members": [decorate_member(db, row) for row in members],
    }


def decorate_project(db: Session, project: PmProject) -> dict:
    return {
        "id": project.id,
        "workspace_id": project.workspace_id,
        "name": project.name,
        "key": project.key,
        "description": project.description,
        "sweety_brand_id": project.sweety_brand_id,
        "created_at": project.created_at,
        "feature_count": db.scalar(
            select(func.count()).select_from(PmFeature).where(PmFeature.project_id == project.id)
        )
        or 0,
        "issue_count": db.scalar(
            select(func.count()).select_from(PmIssue).where(PmIssue.project_id == project.id)
        )
        or 0,
    }


def decorate_feature(db: Session, feature: PmFeature, project: PmProject | None = None) -> dict:
    project = project or db.get(PmProject, feature.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return {
        "id": feature.id,
        "project_id": feature.project_id,
        "key": feature_key(project, feature),
        "number": feature.number,
        "title": feature.title,
        "description": feature.description,
        "status": feature.status,
        "source": feature.source,
        "created_by_user_id": feature.created_by_user_id,
        "issue_count": db.scalar(
            select(func.count()).select_from(PmIssue).where(PmIssue.feature_id == feature.id)
        )
        or 0,
        "created_at": feature.created_at,
        "updated_at": feature.updated_at,
    }


def decorate_issue(db: Session, issue: PmIssue, project: PmProject | None = None) -> dict:
    project = project or db.get(PmProject, issue.project_id)
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    feature = db.get(PmFeature, issue.feature_id) if issue.feature_id else None
    assignee = db.get(PmUser, issue.assignee_id) if issue.assignee_id else None
    reporter = db.get(PmUser, issue.reporter_id) if issue.reporter_id else None
    parent = db.get(PmIssue, issue.parent_id) if getattr(issue, "parent_id", None) else None
    subs = db.scalar(select(func.count()).select_from(PmIssue).where(PmIssue.parent_id == issue.id)) or 0
    overdue = bool(issue.due_date and issue.status != "done" and issue.due_date < datetime.now(UTC).date())
    return {
        "id": issue.id,
        "project_id": issue.project_id,
        "feature_id": issue.feature_id,
        "parent_id": getattr(issue, "parent_id", None),
        "parent_key": issue_key(project, parent) if parent else "",
        "subticket_count": subs,
        "key": issue_key(project, issue),
        "number": issue.number,
        "title": issue.title,
        "description": issue.description,
        "kind": issue.kind,
        "status": issue.status,
        "priority": issue.priority,
        "assignee_id": issue.assignee_id,
        "reporter_id": issue.reporter_id,
        "assignee_name": display_of(assignee),
        "reporter_name": display_of(reporter),
        "feature_title": feature.title if feature else "",
        "feature_key": feature_key(project, feature) if feature else "",
        "due_date": issue.due_date,
        "overdue": overdue,
        "sort_order": issue.sort_order,
        "created_at": issue.created_at,
        "updated_at": issue.updated_at,
    }


def create_workspace(db: Session, user: PmUser, name: str, slug: str = "") -> PmWorkspace:
    workspace = PmWorkspace(name=name.strip() or "Workspace", slug=ensure_unique_slug(db, slug or name))
    db.add(workspace)
    db.flush()
    add_member(db, workspace, user, "owner")
    return workspace


def create_project(
    db: Session,
    workspace: PmWorkspace,
    name: str,
    key: str = "",
    description: str = "",
    sweety_brand_id: UUID | None = None,
) -> PmProject:
    project = PmProject(
        workspace_id=workspace.id,
        name=name.strip() or "Project",
        key=ensure_unique_key(db, workspace.id, key or name),
        description=description or "",
        sweety_brand_id=sweety_brand_id,
    )
    db.add(project)
    db.flush()
    return project


def create_feature(
    db: Session,
    project: PmProject,
    title: str,
    description: str = "",
    status: str = "backlog",
    source: str = "human",
    created_by_user_id: UUID | None = None,
    stories: list[str] | None = None,
) -> PmFeature:
    if status not in FEATURE_STATUSES:
        status = "backlog"
    feature = PmFeature(
        project_id=project.id,
        number=next_feature_number(db, project.id),
        title=title.strip() or "Untitled feature",
        description=description or "",
        status=status,
        source=source,
        created_by_user_id=created_by_user_id,
    )
    db.add(feature)
    db.flush()
    for story in stories or []:
        line = story.strip()
        if line:
            create_issue(db, project, title=line, feature_id=feature.id, kind="story", source_reporter=None)
    return feature


def create_issue(
    db: Session,
    project: PmProject,
    title: str,
    description: str = "",
    kind: str = "task",
    status: str = "backlog",
    priority: int = 2,
    feature_id: UUID | None = None,
    assignee_id: UUID | None = None,
    reporter_id: UUID | None = None,
    due_date=None,
    parent_id: UUID | None = None,
    source_reporter: UUID | None = None,
) -> PmIssue:
    if kind not in ISSUE_KINDS:
        kind = "task"
    if status not in ISSUE_STATUSES:
        status = "backlog"
    if feature_id:
        feature = db.get(PmFeature, feature_id)
        if feature is None or feature.project_id != project.id:
            raise HTTPException(status_code=400, detail="Feature not in this project")
    if parent_id:
        parent = db.get(PmIssue, parent_id)
        if parent is None or parent.project_id != project.id:
            raise HTTPException(status_code=400, detail="Parent ticket not in this project")
        if kind != "subticket":
            kind = "subticket"
    issue = PmIssue(
        project_id=project.id,
        feature_id=feature_id,
        parent_id=parent_id,
        number=next_issue_number(db, project.id),
        title=title.strip() or "Untitled",
        description=description or "",
        kind=kind,
        status=status,
        priority=max(0, min(4, priority)),
        assignee_id=assignee_id,
        reporter_id=reporter_id or source_reporter,
        due_date=due_date,
    )
    db.add(issue)
    db.flush()
    return issue


def ensure_pm_project_for_brand(db: Session, brand: Brand) -> PmProject:
    existing = db.scalar(select(PmProject).where(PmProject.sweety_brand_id == brand.id))
    if existing:
        return existing
    workspace = default_workspace(db)
    return create_project(
        db,
        workspace,
        name=brand.name,
        key=project_key_from_name(brand.name),
        description=brand.mission or "",
        sweety_brand_id=brand.id,
    )


def join_default_workspace(db: Session, user: PmUser, role: str = "member") -> PmWorkspace:
    workspace = default_workspace(db)
    add_member(db, workspace, user, role)
    return workspace


def ensure_pm_admin(db: Session) -> PmUser | None:
    try:
        user = db.scalar(select(PmUser).where(PmUser.email == PM_ADMIN_EMAIL))
    except ProgrammingError:
        db.rollback()
        return None
    if user is None:
        user = PmUser(
            email=PM_ADMIN_EMAIL,
            hashed_password=hash_password(PM_ADMIN_PASSWORD),
            display_name=PM_ADMIN_NAME,
        )
        db.add(user)
        db.flush()
    else:
        user.hashed_password = hash_password(PM_ADMIN_PASSWORD)
        if not user.display_name:
            user.display_name = PM_ADMIN_NAME
    workspace = default_workspace(db)
    add_member(db, workspace, user, "owner")
    return user


def seed_pm_if_empty(db: Session) -> None:
    user = ensure_pm_admin(db)
    if user is None:
        return
    workspace = default_workspace(db)
    has_project = db.scalar(select(PmProject.id).where(PmProject.workspace_id == workspace.id).limit(1))
    if has_project is not None:
        db.commit()
        return
    project = create_project(
        db,
        workspace,
        name="Core product",
        key="CORE",
        description="Default board for product work created from God Mode.",
    )
    feature = create_feature(
        db,
        project,
        title="Task console",
        description="Standalone Jira-style workspace with its own login.",
        status="in_progress",
        source="godmode",
        stories=[
            "Separate login for the task console",
            "Kanban board with features and issues",
            "God Mode can create features",
        ],
    )
    first = db.scalar(select(PmIssue).where(PmIssue.feature_id == feature.id).order_by(PmIssue.number))
    if first:
        first.status = "in_progress"
        first.assignee_id = user.id
    db.commit()


def project_report(db: Session, project: PmProject) -> dict:
    issues = list(db.scalars(select(PmIssue).where(PmIssue.project_id == project.id)).all())
    features = list(db.scalars(select(PmFeature).where(PmFeature.project_id == project.id)).all())
    by_status = {status: 0 for status in ISSUE_STATUSES}
    by_kind = {kind: 0 for kind in ISSUE_KINDS}
    assignee_map: dict[str, dict] = {}
    overdue_rows = []
    for issue in issues:
        by_status[issue.status] = by_status.get(issue.status, 0) + 1
        by_kind[issue.kind] = by_kind.get(issue.kind, 0) + 1
        key = str(issue.assignee_id or "unassigned")
        bucket = assignee_map.setdefault(
            key, {"assignee_id": issue.assignee_id, "name": "Unassigned", "open": 0, "done": 0}
        )
        if issue.assignee_id:
            bucket["name"] = display_of(db.get(PmUser, issue.assignee_id))
        if issue.status == "done":
            bucket["done"] += 1
        else:
            bucket["open"] += 1
        decorated = decorate_issue(db, issue, project)
        if decorated["overdue"]:
            overdue_rows.append(decorated)
    by_epic = []
    for feature in features:
        kids = [i for i in issues if i.feature_id == feature.id]
        done = sum(1 for i in kids if i.status == "done")
        by_epic.append(
            {
                "id": str(feature.id),
                "key": feature_key(project, feature),
                "title": feature.title,
                "status": feature.status,
                "open": len(kids) - done,
                "done": done,
                "pct": round(100 * done / len(kids)) if kids else 0,
            }
        )
    return {
        "totals": {
            "issues": len(issues),
            "epics": len(features),
            "stories": by_kind.get("story", 0),
            "tickets": by_kind.get("ticket", 0) + by_kind.get("task", 0),
            "bugs": by_kind.get("bug", 0),
            "subtickets": by_kind.get("subticket", 0),
            "done": by_status.get("done", 0),
            "overdue": len(overdue_rows),
        },
        "by_status": by_status,
        "by_kind": by_kind,
        "by_assignee": list(assignee_map.values()),
        "by_epic": by_epic,
        "overdue": overdue_rows,
    }
