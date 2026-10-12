from fastapi import APIRouter, Depends
from sqlmodel import Session, select, func
from typing import List
from database import get_session
from models import ExecutionHistory, Prompt, AuditLog, AuditLogRead

router = APIRouter(
    prefix="/analytics",
    tags=["analytics"],
)


@router.get("/usage")
def get_usage_stats(session: Session = Depends(get_session)):
    # Count executions per prompt
    statement = select(
        ExecutionHistory.prompt_id, func.count(ExecutionHistory.id)
    ).group_by(ExecutionHistory.prompt_id)
    results = session.exec(statement).all()

    # Map to prompt names
    stats = []
    for prompt_id, count in results:
        prompt = session.get(Prompt, prompt_id)
        if prompt:
            stats.append({"name": prompt.name, "executions": count})

    return sorted(stats, key=lambda x: x["executions"], reverse=True)


@router.get("/history", response_model=List[AuditLogRead])
def get_audit_history(limit: int = 20, session: Session = Depends(get_session)):
    statement = select(AuditLog).order_by(AuditLog.created_at.desc()).limit(limit)
    logs = session.exec(statement).all()
    return logs
