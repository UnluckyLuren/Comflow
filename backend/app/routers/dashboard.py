"""
ClawFlow — Dashboard Router
UC05: Consultar Dashboard de Flujos Activos
"""
from datetime import datetime, date

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.models.database import ComandoVoz, FlujoTrabajo, LogSistema, get_db, Usuario
from app.services.auth_service import get_current_user
from app.services.n8n_service import N8NService

router = APIRouter()


@router.get("/status")
async def dashboard_status(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """
    Aggregates data from n8n and MySQL for the main dashboard:
    - Flow counts (active / inactive)
    - Command stats today
    - Recent executions from n8n
    - Recent voice commands from local DB
    """
    # ── Local stats ────────────────────────────────────────────────────────
    today = datetime.combine(date.today(), datetime.min.time())

    total_count    = db.query(func.count(FlujoTrabajo.id)).filter(
        FlujoTrabajo.id_usuario == current_user.id_usuario
    ).scalar() or 0

    active_count   = db.query(func.count(FlujoTrabajo.id)).filter(
        FlujoTrabajo.id_usuario == current_user.id_usuario,
        FlujoTrabajo.activo == True,
    ).scalar() or 0

    inactive_count = total_count - active_count

    commands_today = db.query(func.count(ComandoVoz.id)).filter(
        ComandoVoz.id_usuario == current_user.id_usuario,
        ComandoVoz.created_at >= today,
    ).scalar() or 0

    errors_today = db.query(func.count(ComandoVoz.id)).filter(
        ComandoVoz.id_usuario == current_user.id_usuario,
        ComandoVoz.estado == "error",
        ComandoVoz.created_at >= today,
    ).scalar() or 0

    # ── Recent commands ────────────────────────────────────────────────────
    recent_cmds = db.query(ComandoVoz).filter(
        ComandoVoz.id_usuario == current_user.id_usuario,
    ).order_by(ComandoVoz.created_at.desc()).limit(6).all()

    # ── Recent n8n executions ──────────────────────────────────────────────
    recent_execs = []
    try:
        n8n = N8NService()
        raw_execs = await n8n.list_executions(limit=10)
        for ex in raw_execs:
            recent_execs.append({
                "flow_id":    str(ex.get("workflowId", "")),
                "name":       ex.get("workflowData", {}).get("name", "—"),
                "started_at": ex.get("startedAt"),
                "status":     "success" if ex.get("finished") and not ex.get("stoppedAt") else "error",
                "duration_ms": None,
            })
    except Exception:
        pass  # Offline — skip executions

    return {
        "total_count":      total_count,
        "active_count":     active_count,
        "inactive_count":   inactive_count,
        "commands_today":   commands_today,
        "errors_today":     errors_today,
        "recent_executions": recent_execs,
        "recent_commands": [
            {
                "id":               c.id,
                "texto_transcrito": c.texto_transcrito,
                "estado":           c.estado,
                "created_at":       c.created_at.isoformat() if c.created_at else None,
            }
            for c in recent_cmds
        ],
    }
