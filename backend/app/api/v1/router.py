from fastapi import APIRouter

from app.api.v1 import (
    agents,
    approvals,
    artifacts,
    auth,
    brands,
    campaigns,
    command,
    connectors,
    content,
    crm,
    godmode,
    meta,
    notifications,
    pm,
    runs,
    tasks,
)

api_router = APIRouter()
api_router.include_router(auth.router)
api_router.include_router(brands.router)
api_router.include_router(agents.router)
api_router.include_router(campaigns.router)
api_router.include_router(tasks.router)
api_router.include_router(artifacts.router)
api_router.include_router(runs.router)
api_router.include_router(approvals.router)
api_router.include_router(connectors.router)
api_router.include_router(godmode.router)
api_router.include_router(crm.router)
api_router.include_router(command.router)
api_router.include_router(meta.router)
api_router.include_router(content.router)
api_router.include_router(notifications.router)
api_router.include_router(pm.router)
