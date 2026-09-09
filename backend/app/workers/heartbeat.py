from app.core.celery_app import celery_app
from app.core.db import SessionLocal
from app.services.heartbeat import due_agents, run_heartbeat


@celery_app.task(name="app.workers.heartbeat.run_agent_heartbeat")
def run_agent_heartbeat(agent_id: str, trigger: str = "schedule") -> str:
    db = SessionLocal()
    try:
        run = run_heartbeat(db, agent_id, trigger=trigger)
        return str(run.id)
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@celery_app.task(name="app.workers.heartbeat.scan_due_heartbeats")
def scan_due_heartbeats() -> int:
    db = SessionLocal()
    try:
        agents = due_agents(db)
        for agent in agents:
            run_agent_heartbeat.delay(str(agent.id), "schedule")
        return len(agents)
    finally:
        db.close()
