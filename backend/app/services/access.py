from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.models.agent import Agent
from app.models.brand import Brand
from app.models.campaign import Campaign
from app.models.task import Task


def get_brand_for_user(db: Session, brand_id: UUID, user_id: UUID) -> Brand:
    brand = db.get(Brand, brand_id)
    if brand is None or brand.owner_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Brand not found")
    return brand


def get_agent_in_brand(db: Session, brand_id: UUID, agent_id: UUID) -> Agent:
    agent = db.get(Agent, agent_id)
    if agent is None or agent.brand_id != brand_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return agent


def get_campaign_in_brand(db: Session, brand_id: UUID, campaign_id: UUID) -> Campaign:
    campaign = db.get(Campaign, campaign_id)
    if campaign is None or campaign.brand_id != brand_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Campaign not found")
    return campaign


def get_task_in_brand(db: Session, brand_id: UUID, task_id: UUID) -> Task:
    task = db.get(Task, task_id)
    if task is None or task.brand_id != brand_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Task not found")
    return task
