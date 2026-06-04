"""
ClawFlow — Workflows Router  (v2)
UC04: Desplegar y Activar Flujo en n8n
UC06: Modificar/Eliminar Flujos Existentes
Deploy now syncs/creates credentials in n8n before posting the workflow.
"""
from __future__ import annotations
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.database import FlujoTrabajo, InstanciaN8N, get_db, Usuario
from app.services.auth_service import get_current_user
from app.services.credential_service import CredentialService
from app.services.n8n_service import N8NService, get_n8n_for_user

router   = APIRouter()
cred_svc = CredentialService()


# ── Schemas ───────────────────────────────────────────────────────────────────
class DeployRequest(BaseModel):
    workflow_json:        dict[str, Any]
    selected_credentials: list[dict] = []   # forwarded from generate-flow response


class ToggleRequest(BaseModel):
    active: bool


# ── UC04: Deploy Workflow ─────────────────────────────────────────────────────
@router.post("/deploy")
async def deploy_workflow(
    body: DeployRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    svc  = await get_n8n_for_user(db, current_user.id_usuario)
    inst = _get_instance(db, current_user.id_usuario)

    # 1. Sync / create credentials in n8n, replace CF_SYNC_* placeholders
    workflow_to_deploy = body.workflow_json
    if body.selected_credentials:
        try:
            workflow_to_deploy = await cred_svc.sync_and_resolve(
                n8n_svc=svc,
                db=db,
                user_id=current_user.id_usuario,
                workflow_json=body.workflow_json,
                selected_credentials=body.selected_credentials,
            )
        except Exception as exc:
            print(f"[deploy] Credential sync warning: {exc}")
            # Non-fatal: deploy with placeholders, n8n will flag missing creds

    # 2. POST /workflows → create
    try:
        created = await svc.create_workflow(workflow_to_deploy)
        flow_id = str(created.get("id", ""))
        name    = created.get("name", "Flujo sin nombre")

        # 3. PUT activate
        await svc.activate_workflow(flow_id)

        # 4. Persist locally
        nodes_summary = [
            n.get("name", n.get("type")) for n in workflow_to_deploy.get("nodes", [])
        ]
        db.add(FlujoTrabajo(
            id_flujo_n8n=flow_id,
            id_instancia=inst.id_instancia if inst else 1,
            id_usuario=current_user.id_usuario,
            nombre=name,
            activo=True,
            estructura_json=json.dumps(workflow_to_deploy),
            nodos_resumen=nodes_summary,
        ))
        db.commit()

    except Exception as exc:
        # Draft fallback: save locally even when n8n is unreachable
        import time
        db.add(FlujoTrabajo(
            id_flujo_n8n=f"draft_{int(time.time())}",
            id_instancia=inst.id_instancia if inst else 1,
            id_usuario=current_user.id_usuario,
            nombre=body.workflow_json.get("name", "Borrador"),
            activo=False,
            estructura_json=json.dumps(body.workflow_json),
        ))
        db.commit()
        raise HTTPException(
            503,
            f"n8n no disponible. JSON guardado como borrador local. Error: {exc}",
        )

    return {"success": True, "flow_id": flow_id, "name": name}


# ── List Workflows ─────────────────────────────────────────────────────────────
@router.get("/list")
async def list_workflows(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    svc = await get_n8n_for_user(db, current_user.id_usuario)

    try:
        n8n_flows = await svc.list_workflows()
    except Exception:
        # Fallback to local DB cache
        local = db.query(FlujoTrabajo).filter(
            FlujoTrabajo.id_usuario == current_user.id_usuario
        ).order_by(FlujoTrabajo.created_at.desc()).all()
        return {"workflows": [_flujo_to_dict(f) for f in local], "source": "local"}

    # Sync n8n data to local DB
    for wf in n8n_flows:
        flow_id  = str(wf.get("id", ""))
        existing = db.query(FlujoTrabajo).filter(
            FlujoTrabajo.id_flujo_n8n == flow_id,
            FlujoTrabajo.id_usuario   == current_user.id_usuario,
        ).first()
        if existing:
            existing.activo = wf.get("active", False)
            existing.nombre = wf.get("name", existing.nombre)
        else:
            nodes = [n.get("name", n.get("type", "")) for n in wf.get("nodes", [])]
            db.add(FlujoTrabajo(
                id_flujo_n8n=flow_id,
                id_instancia=1,
                id_usuario=current_user.id_usuario,
                nombre=wf.get("name", "Sin nombre"),
                activo=wf.get("active", False),
                nodos_resumen=nodes,
            ))
    db.commit()

    return {
        "workflows": [
            {
                "id_flujo_n8n":  str(wf.get("id")),
                "nombre":        wf.get("name", ""),
                "activo":        wf.get("active", False),
                "nodos_resumen": [n.get("name", "") for n in wf.get("nodes", [])],
                "created_at":    wf.get("createdAt"),
            }
            for wf in n8n_flows
        ],
        "source": "n8n",
    }


# ── Get Workflow JSON ──────────────────────────────────────────────────────────
@router.get("/{flow_id}/json")
async def get_workflow_json(
    flow_id: str = Path(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    svc = await get_n8n_for_user(db, current_user.id_usuario)
    try:
        wf = await svc.get_workflow(flow_id)
        return {"workflow_json": wf}
    except Exception:
        local = db.query(FlujoTrabajo).filter(
            FlujoTrabajo.id_flujo_n8n == flow_id
        ).first()
        if local and local.estructura_json:
            return {"workflow_json": json.loads(local.estructura_json)}
        raise HTTPException(404, "Flujo no encontrado")


# ── UC06: Toggle Active ────────────────────────────────────────────────────────
@router.put("/{flow_id}/toggle")
async def toggle_workflow(
    flow_id: str,
    body: ToggleRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    svc = await get_n8n_for_user(db, current_user.id_usuario)
    try:
        if body.active:
            await svc.activate_workflow(flow_id)
        else:
            await svc.deactivate_workflow(flow_id)
    except Exception as exc:
        raise HTTPException(503, f"Error comunicando con n8n: {exc}")

    local = db.query(FlujoTrabajo).filter(FlujoTrabajo.id_flujo_n8n == flow_id).first()
    if local:
        local.activo = body.active
        db.commit()
    return {"success": True, "active": body.active}


# ── UC06: Delete Workflow ──────────────────────────────────────────────────────
@router.delete("/{flow_id}")
async def delete_workflow(
    flow_id: str,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    svc = await get_n8n_for_user(db, current_user.id_usuario)
    try:
        await svc.delete_workflow(flow_id)
    except Exception as exc:
        if "404" in str(exc):
            _cleanup_local(db, flow_id)
            return {"success": True, "note": "Flujo fantasma eliminado de la base de datos local."}
        raise HTTPException(503, str(exc))
    _cleanup_local(db, flow_id)
    return {"success": True}


# ── Helpers ────────────────────────────────────────────────────────────────────
def _get_instance(db: Session, user_id: int):
    return db.query(InstanciaN8N).filter(
        InstanciaN8N.id_usuario == user_id,
        InstanciaN8N.activa     == True,
    ).first()


def _flujo_to_dict(f: FlujoTrabajo) -> dict:
    return {
        "id_flujo_n8n":  f.id_flujo_n8n,
        "nombre":        f.nombre,
        "activo":        f.activo,
        "nodos_resumen": f.nodos_resumen or [],
        "created_at":    f.created_at.isoformat() if f.created_at else None,
    }


def _cleanup_local(db: Session, flow_id: str):
    db.query(FlujoTrabajo).filter(FlujoTrabajo.id_flujo_n8n == flow_id).delete()
    db.commit()
