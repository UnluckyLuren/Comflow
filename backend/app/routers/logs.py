"""
ClawFlow — Logs Router
RF-07: Soporte Técnico y Logs del Sistema
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.models.database import LogSistema, get_db, Usuario
from app.services.auth_service import get_current_user

router = APIRouter()


@router.get("")
async def get_logs(
    level:  str | None = Query(None),
    limit:  int        = Query(100, le=500),
    db:     Session    = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    q = db.query(LogSistema)
    if level:
        q = q.filter(LogSistema.nivel == level)
    logs = q.order_by(LogSistema.created_at.desc()).limit(limit).all()

    return {
        "logs": [
            {
                "id":         l.id,
                "nivel":      l.nivel,
                "modulo":     l.modulo,
                "mensaje":    l.mensaje,
                "created_at": l.created_at.isoformat() if l.created_at else None,
            }
            for l in logs
        ]
    }
