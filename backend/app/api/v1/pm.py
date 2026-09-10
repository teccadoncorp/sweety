import secrets
from datetime import date
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.deps import get_pm_user
from app.core.security import create_access_token, hash_password, verify_password
from app.models.pm import (
    FEATURE_STATUSES,
    ISSUE_KINDS,
    ISSUE_STATUSES,
    MEMBER_ROLES,
    PmComment,
    PmFeature,
    PmIssue,
    PmProject,
    PmUser,
    PmWorkspace,
    PmWorkspaceMember,
)
from app.schemas.common import TokenOut
from app.schemas.pm import (
    PmBoardOut,
    PmChatIn,
    PmCommentIn,
    PmCommentOut,
    PmFeatureIn,
    PmFeatureOut,
    PmFeatureUpdate,
    PmIssueIn,
    PmIssueOut,
    PmIssueUpdate,
    PmCommentUpdate,
    PmLoginIn,
    PmMemberIn,
    PmMemberUpdate,
    PmProjectIn,
    PmProjectOut,
    PmProjectUpdate,
    PmRegisterIn,
    PmReportOut,
    PmUserOut,
    PmWorkspaceIn,
    PmWorkspaceOut,
    PmWorkspaceUpdate,
)
from app.services.pm import (
    add_member,
    create_feature,
    create_issue,
    create_project,
    create_workspace,
    decorate_feature,
    decorate_issue,
    decorate_member,
    decorate_project,
    decorate_workspace,
    display_of,
    get_project_for_user,
    join_default_workspace,
    membership,
    project_report,
    require_god,
    touch_presence,
    user_workspaces,
)
from app.services.pm_godmode import list_messages, reply, serialize_message

router = APIRouter(prefix="/pm", tags=["pm"])


def _apply(row, payload: dict) -> None:
    for key, value in payload.items():
        setattr(row, key, value)


@router.post("/auth/register", response_model=TokenOut)
def register(payload: PmRegisterIn, db: Session = Depends(get_db)) -> TokenOut:
    email = payload.email.lower().strip()
    if db.scalar(select(PmUser).where(PmUser.email == email)):
        raise HTTPException(status_code=409, detail="Email already registered")
    user = PmUser(
        email=email,
        hashed_password=hash_password(payload.password),
        display_name=(payload.display_name or email.split("@")[0]).strip(),
    )
    db.add(user)
    db.flush()
    join_default_workspace(db, user, "member")
    db.commit()
    db.refresh(user)
    return TokenOut(access_token=create_access_token(user.id, audience="pm"))


@router.post("/auth/login", response_model=TokenOut)
def login(payload: PmLoginIn, db: Session = Depends(get_db)) -> TokenOut:
    user = db.scalar(select(PmUser).where(PmUser.email == payload.email.lower().strip()))
    if user is None or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    touch_presence(db, user)
    return TokenOut(access_token=create_access_token(user.id, audience="pm"))


@router.post("/auth/heartbeat")
def heartbeat(user: PmUser = Depends(get_pm_user), db: Session = Depends(get_db)) -> dict:
    touch_presence(db, user)
    return {"ok": True, "last_seen_at": user.last_seen_at}


@router.get("/auth/me", response_model=PmUserOut)
def me(user: PmUser = Depends(get_pm_user), db: Session = Depends(get_db)) -> dict:
    return {
        "id": user.id,
        "email": user.email,
        "display_name": display_of(user),
        "created_at": user.created_at,
        "workspaces": user_workspaces(db, user),
    }


@router.get("/workspaces", response_model=list[PmWorkspaceOut])
def list_workspaces(user: PmUser = Depends(get_pm_user), db: Session = Depends(get_db)) -> list[dict]:
    return [
        decorate_workspace(db, db.get(PmWorkspace, row["id"]), row["role"])
        for row in user_workspaces(db, user)
    ]


@router.post("/workspaces", response_model=PmWorkspaceOut)
def post_workspace(
    payload: PmWorkspaceIn, user: PmUser = Depends(get_pm_user), db: Session = Depends(get_db)
) -> dict:
    workspace = create_workspace(db, user, payload.name, payload.slug)
    db.commit()
    db.refresh(workspace)
    return decorate_workspace(db, workspace, "owner")


@router.get("/workspaces/{workspace_id}", response_model=PmWorkspaceOut)
def get_workspace(
    workspace_id: UUID, user: PmUser = Depends(get_pm_user), db: Session = Depends(get_db)
) -> dict:
    member = membership(db, workspace_id, user.id)
    workspace = db.get(PmWorkspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    return decorate_workspace(db, workspace, member.role)


@router.post("/workspaces/{workspace_id}/members")
def invite_member(
    workspace_id: UUID,
    payload: PmMemberIn,
    user: PmUser = Depends(get_pm_user),
    db: Session = Depends(get_db),
) -> dict:
    member = membership(db, workspace_id, user.id)
    require_god(member)
    if payload.role not in MEMBER_ROLES:
        raise HTTPException(status_code=400, detail="Invalid role")
    email = payload.email.lower().strip()
    invited = db.scalar(select(PmUser).where(PmUser.email == email))
    temporary_password = None
    if invited is None:
        temporary_password = payload.password.strip() or secrets.token_urlsafe(8)
        invited = PmUser(
            email=email,
            hashed_password=hash_password(temporary_password),
            display_name=(payload.display_name or email.split("@")[0]).strip(),
        )
        db.add(invited)
        db.flush()
    workspace = db.get(PmWorkspace, workspace_id)
    added = add_member(db, workspace, invited, payload.role)
    db.commit()
    out = decorate_member(db, added)
    out["temporary_password"] = temporary_password
    return out


@router.patch("/workspaces/{workspace_id}", response_model=PmWorkspaceOut)
def patch_workspace(
    workspace_id: UUID,
    payload: PmWorkspaceUpdate,
    user: PmUser = Depends(get_pm_user),
    db: Session = Depends(get_db),
) -> dict:
    member = membership(db, workspace_id, user.id)
    require_god(member)
    workspace = db.get(PmWorkspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if payload.name:
        workspace.name = payload.name.strip()
    db.commit()
    db.refresh(workspace)
    return decorate_workspace(db, workspace, member.role)


@router.patch("/workspaces/{workspace_id}/members/{member_id}")
def patch_member(
    workspace_id: UUID,
    member_id: UUID,
    payload: PmMemberUpdate,
    user: PmUser = Depends(get_pm_user),
    db: Session = Depends(get_db),
) -> dict:
    actor = membership(db, workspace_id, user.id)
    require_god(actor)
    row = db.get(PmWorkspaceMember, member_id)
    if row is None or row.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Member not found")
    if payload.role:
        if payload.role not in MEMBER_ROLES:
            raise HTTPException(status_code=400, detail="Invalid role")
        row.role = payload.role
    if payload.display_name is not None:
        target = db.get(PmUser, row.user_id)
        if target:
            target.display_name = payload.display_name.strip()
    db.commit()
    db.refresh(row)
    return decorate_member(db, row)


@router.delete("/workspaces/{workspace_id}/members/{member_id}")
def delete_member(
    workspace_id: UUID,
    member_id: UUID,
    user: PmUser = Depends(get_pm_user),
    db: Session = Depends(get_db),
) -> dict:
    actor = membership(db, workspace_id, user.id)
    require_god(actor)
    row = db.get(PmWorkspaceMember, member_id)
    if row is None or row.workspace_id != workspace_id:
        raise HTTPException(status_code=404, detail="Member not found")
    if row.user_id == user.id:
        raise HTTPException(status_code=400, detail="You cannot remove yourself")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.get("/workspaces/{workspace_id}/projects", response_model=list[PmProjectOut])
def list_projects(
    workspace_id: UUID, user: PmUser = Depends(get_pm_user), db: Session = Depends(get_db)
) -> list[dict]:
    membership(db, workspace_id, user.id)
    rows = db.scalars(select(PmProject).where(PmProject.workspace_id == workspace_id)).all()
    return [decorate_project(db, row) for row in rows]


@router.post("/workspaces/{workspace_id}/projects", response_model=PmProjectOut)
def post_project(
    workspace_id: UUID,
    payload: PmProjectIn,
    user: PmUser = Depends(get_pm_user),
    db: Session = Depends(get_db),
) -> dict:
    member = membership(db, workspace_id, user.id)
    require_god(member)
    workspace = db.get(PmWorkspace, workspace_id)
    project = create_project(db, workspace, payload.name, payload.key, payload.description)
    db.commit()
    db.refresh(project)
    return decorate_project(db, project)


@router.get("/projects/{project_id}", response_model=PmProjectOut)
def get_project(
    project_id: UUID, user: PmUser = Depends(get_pm_user), db: Session = Depends(get_db)
) -> dict:
    project, _ = get_project_for_user(db, project_id, user.id)
    return decorate_project(db, project)


@router.patch("/projects/{project_id}", response_model=PmProjectOut)
def patch_project(
    project_id: UUID,
    payload: PmProjectUpdate,
    user: PmUser = Depends(get_pm_user),
    db: Session = Depends(get_db),
) -> dict:
    project, member = get_project_for_user(db, project_id, user.id)
    require_god(member)
    _apply(project, payload.model_dump(exclude_unset=True))
    db.commit()
    db.refresh(project)
    return decorate_project(db, project)


@router.delete("/projects/{project_id}")
def delete_project(
    project_id: UUID, user: PmUser = Depends(get_pm_user), db: Session = Depends(get_db)
) -> dict:
    project, member = get_project_for_user(db, project_id, user.id)
    require_god(member)
    issues = list(db.scalars(select(PmIssue).where(PmIssue.project_id == project.id)))
    for issue in issues:
        for comment in db.scalars(select(PmComment).where(PmComment.issue_id == issue.id)):
            db.delete(comment)
    for issue in issues:
        issue.parent_id = None
    db.flush()
    for issue in issues:
        db.delete(issue)
    for feature in db.scalars(select(PmFeature).where(PmFeature.project_id == project.id)):
        db.delete(feature)
    db.delete(project)
    db.commit()
    return {"ok": True}


@router.get("/projects/{project_id}/report", response_model=PmReportOut)
def get_report(
    project_id: UUID, user: PmUser = Depends(get_pm_user), db: Session = Depends(get_db)
) -> dict:
    project, _ = get_project_for_user(db, project_id, user.id)
    return project_report(db, project)


@router.get("/projects/{project_id}/board", response_model=PmBoardOut)
def get_board(
    project_id: UUID, user: PmUser = Depends(get_pm_user), db: Session = Depends(get_db)
) -> dict:
    project, member = get_project_for_user(db, project_id, user.id)
    workspace = db.get(PmWorkspace, project.workspace_id)
    features = db.scalars(
        select(PmFeature).where(PmFeature.project_id == project.id).order_by(PmFeature.number)
    ).all()
    issues = db.scalars(
        select(PmIssue).where(PmIssue.project_id == project.id).order_by(PmIssue.sort_order, PmIssue.number)
    ).all()
    columns = {status: [] for status in ISSUE_STATUSES}
    for issue in issues:
        columns.setdefault(issue.status, []).append(decorate_issue(db, issue, project))
    return {
        "project": decorate_project(db, project),
        "features": [decorate_feature(db, row, project) for row in features],
        "columns": columns,
        "members": [decorate_member(db, row) for row in workspace.members] if workspace else [],
        "role": member.role,
        "can_create_features": member.role in {"owner", "admin"},
    }


@router.get("/projects/{project_id}/features", response_model=list[PmFeatureOut])
def list_features(
    project_id: UUID, user: PmUser = Depends(get_pm_user), db: Session = Depends(get_db)
) -> list[dict]:
    project, _ = get_project_for_user(db, project_id, user.id)
    rows = db.scalars(
        select(PmFeature).where(PmFeature.project_id == project.id).order_by(PmFeature.number)
    ).all()
    return [decorate_feature(db, row, project) for row in rows]


@router.post("/projects/{project_id}/features", response_model=PmFeatureOut)
def post_feature(
    project_id: UUID,
    payload: PmFeatureIn,
    user: PmUser = Depends(get_pm_user),
    db: Session = Depends(get_db),
) -> dict:
    project, member = get_project_for_user(db, project_id, user.id)
    require_god(member)
    feature = create_feature(
        db,
        project,
        title=payload.title,
        description=payload.description,
        status=payload.status,
        source="human",
        created_by_user_id=user.id,
        stories=payload.stories,
    )
    db.commit()
    db.refresh(feature)
    return decorate_feature(db, feature, project)


@router.patch("/features/{feature_id}", response_model=PmFeatureOut)
def patch_feature(
    feature_id: UUID,
    payload: PmFeatureUpdate,
    user: PmUser = Depends(get_pm_user),
    db: Session = Depends(get_db),
) -> dict:
    feature = db.get(PmFeature, feature_id)
    if feature is None:
        raise HTTPException(status_code=404, detail="Feature not found")
    project, member = get_project_for_user(db, feature.project_id, user.id)
    data = payload.model_dump(exclude_unset=True)
    if "status" in data and data["status"] not in FEATURE_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    _apply(feature, data)
    db.commit()
    db.refresh(feature)
    return decorate_feature(db, feature, project)


@router.delete("/features/{feature_id}")
def delete_feature(
    feature_id: UUID, user: PmUser = Depends(get_pm_user), db: Session = Depends(get_db)
) -> dict:
    feature = db.get(PmFeature, feature_id)
    if feature is None:
        raise HTTPException(status_code=404, detail="Feature not found")
    _, member = get_project_for_user(db, feature.project_id, user.id)
    require_god(member)
    for issue in db.scalars(select(PmIssue).where(PmIssue.feature_id == feature.id)):
        issue.feature_id = None
    db.delete(feature)
    db.commit()
    return {"ok": True}


@router.get("/projects/{project_id}/issues", response_model=list[PmIssueOut])
def list_issues(
    project_id: UUID,
    feature_id: UUID | None = Query(default=None),
    parent_id: UUID | None = Query(default=None),
    q: str = Query(""),
    status: str = Query(""),
    kind: str = Query(""),
    priority: int | None = Query(default=None),
    assignee_id: UUID | None = Query(default=None),
    unassigned: bool = Query(False),
    overdue: bool = Query(False),
    due_before: date | None = Query(default=None),
    due_after: date | None = Query(default=None),
    user: PmUser = Depends(get_pm_user),
    db: Session = Depends(get_db),
) -> list[dict]:
    project, _ = get_project_for_user(db, project_id, user.id)
    stmt = select(PmIssue).where(PmIssue.project_id == project.id)
    if feature_id:
        stmt = stmt.where(PmIssue.feature_id == feature_id)
    if parent_id:
        stmt = stmt.where(PmIssue.parent_id == parent_id)
    if q.strip():
        needle = f"%{q.strip()}%"
        stmt = stmt.where(or_(PmIssue.title.ilike(needle), PmIssue.description.ilike(needle)))
    if status.strip() and status != "all":
        stmt = stmt.where(PmIssue.status == status)
    if kind.strip() and kind != "all":
        stmt = stmt.where(PmIssue.kind == kind)
    if priority is not None:
        stmt = stmt.where(PmIssue.priority == priority)
    if unassigned:
        stmt = stmt.where(PmIssue.assignee_id.is_(None))
    elif assignee_id:
        stmt = stmt.where(PmIssue.assignee_id == assignee_id)
    if due_before:
        stmt = stmt.where(PmIssue.due_date <= due_before)
    if due_after:
        stmt = stmt.where(PmIssue.due_date >= due_after)
    rows = db.scalars(stmt.order_by(PmIssue.sort_order, PmIssue.number)).all()
    out = [decorate_issue(db, row, project) for row in rows]
    if overdue:
        out = [row for row in out if row["overdue"]]
    return out


@router.post("/projects/{project_id}/issues", response_model=PmIssueOut)
def post_issue(
    project_id: UUID,
    payload: PmIssueIn,
    user: PmUser = Depends(get_pm_user),
    db: Session = Depends(get_db),
) -> dict:
    project, _ = get_project_for_user(db, project_id, user.id)
    issue = create_issue(
        db,
        project,
        title=payload.title,
        description=payload.description,
        kind=payload.kind,
        status=payload.status,
        priority=payload.priority,
        feature_id=payload.feature_id,
        parent_id=payload.parent_id,
        assignee_id=payload.assignee_id,
        reporter_id=user.id,
        due_date=payload.due_date,
    )
    db.commit()
    db.refresh(issue)
    return decorate_issue(db, issue, project)


@router.get("/issues/{issue_id}", response_model=PmIssueOut)
def get_issue(
    issue_id: UUID, user: PmUser = Depends(get_pm_user), db: Session = Depends(get_db)
) -> dict:
    issue = db.get(PmIssue, issue_id)
    if issue is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    project, _ = get_project_for_user(db, issue.project_id, user.id)
    return decorate_issue(db, issue, project)


@router.patch("/issues/{issue_id}", response_model=PmIssueOut)
def patch_issue(
    issue_id: UUID,
    payload: PmIssueUpdate,
    user: PmUser = Depends(get_pm_user),
    db: Session = Depends(get_db),
) -> dict:
    issue = db.get(PmIssue, issue_id)
    if issue is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    project, _ = get_project_for_user(db, issue.project_id, user.id)
    data = payload.model_dump(exclude_unset=True)
    if data.get("kind") and data["kind"] not in ISSUE_KINDS:
        raise HTTPException(status_code=400, detail="Invalid kind")
    if data.get("status") and data["status"] not in ISSUE_STATUSES:
        raise HTTPException(status_code=400, detail="Invalid status")
    if "priority" in data and data["priority"] is not None:
        data["priority"] = max(0, min(4, data["priority"]))
    _apply(issue, data)
    db.commit()
    db.refresh(issue)
    return decorate_issue(db, issue, project)


@router.delete("/issues/{issue_id}")
def delete_issue(
    issue_id: UUID, user: PmUser = Depends(get_pm_user), db: Session = Depends(get_db)
) -> dict:
    issue = db.get(PmIssue, issue_id)
    if issue is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    get_project_for_user(db, issue.project_id, user.id)
    for child in db.scalars(select(PmIssue).where(PmIssue.parent_id == issue.id)):
        for comment in db.scalars(select(PmComment).where(PmComment.issue_id == child.id)):
            db.delete(comment)
        db.delete(child)
    for comment in db.scalars(select(PmComment).where(PmComment.issue_id == issue.id)):
        db.delete(comment)
    db.delete(issue)
    db.commit()
    return {"ok": True}


@router.get("/issues/{issue_id}/comments", response_model=list[PmCommentOut])
def list_comments(
    issue_id: UUID, user: PmUser = Depends(get_pm_user), db: Session = Depends(get_db)
) -> list[dict]:
    issue = db.get(PmIssue, issue_id)
    if issue is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    get_project_for_user(db, issue.project_id, user.id)
    rows = db.scalars(
        select(PmComment).where(PmComment.issue_id == issue.id).order_by(PmComment.created_at)
    ).all()
    return [
        {
            "id": row.id,
            "issue_id": row.issue_id,
            "user_id": row.user_id,
            "author_name": display_of(db.get(PmUser, row.user_id)),
            "body": row.body,
            "created_at": row.created_at,
        }
        for row in rows
    ]


@router.post("/issues/{issue_id}/comments", response_model=PmCommentOut)
def post_comment(
    issue_id: UUID,
    payload: PmCommentIn,
    user: PmUser = Depends(get_pm_user),
    db: Session = Depends(get_db),
) -> dict:
    issue = db.get(PmIssue, issue_id)
    if issue is None:
        raise HTTPException(status_code=404, detail="Issue not found")
    get_project_for_user(db, issue.project_id, user.id)
    if not payload.body.strip():
        raise HTTPException(status_code=400, detail="Comment is empty")
    row = PmComment(issue_id=issue.id, user_id=user.id, body=payload.body.strip())
    db.add(row)
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "issue_id": row.issue_id,
        "user_id": row.user_id,
        "author_name": display_of(user),
        "body": row.body,
        "created_at": row.created_at,
    }


@router.patch("/comments/{comment_id}", response_model=PmCommentOut)
def patch_comment(
    comment_id: UUID,
    payload: PmCommentUpdate,
    user: PmUser = Depends(get_pm_user),
    db: Session = Depends(get_db),
) -> dict:
    row = db.get(PmComment, comment_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    issue = db.get(PmIssue, row.issue_id)
    get_project_for_user(db, issue.project_id, user.id)
    if row.user_id != user.id:
        raise HTTPException(status_code=403, detail="You can only edit your comments")
    if not payload.body.strip():
        raise HTTPException(status_code=400, detail="Comment is empty")
    row.body = payload.body.strip()
    db.commit()
    db.refresh(row)
    return {
        "id": row.id,
        "issue_id": row.issue_id,
        "user_id": row.user_id,
        "author_name": display_of(user),
        "body": row.body,
        "created_at": row.created_at,
    }


@router.delete("/comments/{comment_id}")
def delete_comment(
    comment_id: UUID, user: PmUser = Depends(get_pm_user), db: Session = Depends(get_db)
) -> dict:
    row = db.get(PmComment, comment_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Comment not found")
    issue = db.get(PmIssue, row.issue_id)
    _, member = get_project_for_user(db, issue.project_id, user.id)
    if row.user_id != user.id and member.role not in {"owner", "admin"}:
        raise HTTPException(status_code=403, detail="Not allowed")
    db.delete(row)
    db.commit()
    return {"ok": True}


@router.get("/workspaces/{workspace_id}/godmode/messages")
def godmode_messages(
    workspace_id: UUID, user: PmUser = Depends(get_pm_user), db: Session = Depends(get_db)
) -> list[dict]:
    member = membership(db, workspace_id, user.id)
    require_god(member)
    return [serialize_message(row) for row in list_messages(db, workspace_id)]


@router.post("/workspaces/{workspace_id}/godmode/messages")
def godmode_reply(
    workspace_id: UUID,
    payload: PmChatIn,
    user: PmUser = Depends(get_pm_user),
    db: Session = Depends(get_db),
) -> dict:
    member = membership(db, workspace_id, user.id)
    require_god(member)
    workspace = db.get(PmWorkspace, workspace_id)
    if workspace is None:
        raise HTTPException(status_code=404, detail="Workspace not found")
    if not payload.content.strip():
        raise HTTPException(status_code=400, detail="Write a brief first")
    try:
        message = reply(db, workspace, user, payload.content.strip())
    except PermissionError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    return serialize_message(message)
