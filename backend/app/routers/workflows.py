"""
ClawFlow — Workflows Router
UC04: Desplegar y Activar Flujo en n8n
UC06: Modificar/Eliminar Flujos Existentes
"""
from __future__ import annotations
import json
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.database import ComandoVoz, FlujoTrabajo, InstanciaN8N, get_db, Usuario
from app.services.auth_service import get_current_user
from app.services.n8n_service import N8NService

router = APIRouter()


class DeployRequest(BaseModel):
    workflow_json: dict[str, Any]


class ToggleRequest(BaseModel):
    active: bool


def _get_n8n(db: Session, user: Usuario) -> tuple[N8NService, InstanciaN8N]:
    """Retrieve the user's active n8n instance and build the service."""
    inst = db.query(InstanciaN8N).filter(
        InstanciaN8N.id_usuario == user.id_usuario,
        InstanciaN8N.activa == True,
    ).first()

    if not inst:
        # Create a default instance from env vars
        from app.services.encryption_service import EncryptionService
        import os
        enc = EncryptionService()
        inst = InstanciaN8N(
            id_usuario=user.id_usuario,
            nombre="Local n8n",
            host_url=os.getenv("N8N_HOST", "https://n8n.curikprojects.me"),
            api_key_cifrada=enc.encrypt(os.getenv("N8N_API_KEY", "")),
        )
        db.add(inst)
        db.commit()
        db.refresh(inst)

    from app.services.encryption_service import EncryptionService
    enc = EncryptionService()
    api_key = enc.decrypt(inst.api_key_cifrada) if inst.api_key_cifrada else ""
    svc = N8NService(host=inst.host_url, api_key=api_key)
    return svc, inst


# ── UC04: Deploy Flow ──────────────────────────────────────────────────────────
@router.post("/deploy")
async def deploy_workflow(
    body: DeployRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    svc, inst = _get_n8n(db, current_user)

    try:
        # 1. POST /workflows — Creamos el flujo primero
        created = await svc.create_workflow(body.workflow_json)
        flow_id = str(created.get("id", ""))
        name    = created.get("name", "Flujo sin nombre")

        # 2. POST /workflows/{id}/activate — Lo encendemos usando el ID recién creado
        await svc.activate_workflow(flow_id)

        # 3. Guardamos localmente (aseguramos guardar el estado activo)
        nodes_summary = [
            n.get("name", n.get("type")) for n in body.workflow_json.get("nodes", [])
        ]
        flujo = FlujoTrabajo(
            id_flujo_n8n=flow_id,
            id_instancia=inst.id_instancia,
            id_usuario=current_user.id_usuario,
            nombre=name,
            activo=True, # Lo guardamos como True en nuestra base de datos local
            estructura_json=json.dumps(body.workflow_json),
            nodos_resumen=nodes_summary,
        )
        db.add(flujo)
        db.commit()

    except Exception as exc:
        # Draft fallback: save JSON locally even if n8n is down
        flujo = FlujoTrabajo(
            id_flujo_n8n="draft_" + str(int(__import__("time").time())),
            id_instancia=inst.id_instancia,
            id_usuario=current_user.id_usuario,
            nombre=body.workflow_json.get("name", "Borrador"),
            activo=False,
            estructura_json=json.dumps(body.workflow_json),
        )
        db.add(flujo)
        db.commit()
        raise HTTPException(
            status_code=503,
            detail=f"n8n no disponible. JSON guardado como borrador. Error: {exc}",
        )

    return {"success": True, "flow_id": flow_id, "name": name}


# ── List Workflows ─────────────────────────────────────────────────────────────
@router.get("/list")
async def list_workflows(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    svc, _ = _get_n8n(db, current_user)

    try:
        n8n_flows = await svc.list_workflows()
    except Exception:
        # Fallback to local DB
        local = db.query(FlujoTrabajo).filter(
            FlujoTrabajo.id_usuario == current_user.id_usuario
        ).order_by(FlujoTrabajo.created_at.desc()).all()
        return {"workflows": [
            {
                "id_flujo_n8n": f.id_flujo_n8n,
                "nombre": f.nombre,
                "activo": f.activo,
                "nodos_resumen": f.nodos_resumen or [],
                "created_at": f.created_at.isoformat() if f.created_at else None,
            }
            for f in local
        ], "source": "local"}

    # Sync n8n data to local DB
    for wf in n8n_flows:
        flow_id = str(wf.get("id", ""))
        existing = db.query(FlujoTrabajo).filter(
            FlujoTrabajo.id_flujo_n8n == flow_id,
            FlujoTrabajo.id_usuario == current_user.id_usuario,
        ).first()
        if existing:
            existing.activo = wf.get("active", False)
            existing.nombre = wf.get("name", existing.nombre)
        else:
            nodes = [n.get("name", n.get("type", "Nodo")) for n in wf.get("nodes", [])]
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
                "id_flujo_n8n": str(wf.get("id")),
                "nombre": wf.get("name", ""),
                "activo": wf.get("active", False),
                "nodos_resumen": [n.get("name","") for n in wf.get("nodes",[])],
                "created_at": wf.get("createdAt"),
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
    svc, _ = _get_n8n(db, current_user)
    try:
        wf = await svc.get_workflow(flow_id)
        return {"workflow_json": wf}
    except Exception:
        local = db.query(FlujoTrabajo).filter(
            FlujoTrabajo.id_flujo_n8n == flow_id
        ).first()
        if local and local.estructura_json:
            return {"workflow_json": json.loads(local.estructura_json)}
        raise HTTPException(status_code=404, detail="Flujo no encontrado")


# ── UC06: Toggle Active State ──────────────────────────────────────────────────
@router.put("/{flow_id}/toggle")
async def toggle_workflow(
    flow_id: str,
    body: ToggleRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    svc, _ = _get_n8n(db, current_user)
    try:
        if body.active:
            await svc.activate_workflow(flow_id)
        else:
            await svc.deactivate_workflow(flow_id)
    except Exception as exc:
        raise HTTPException(status_code=503, detail=f"Error comunicando con n8n: {exc}")

    # Sync local
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
    svc, _ = _get_n8n(db, current_user)
    try:
        await svc.delete_workflow(flow_id)
    except Exception as exc:
        # Handle ghost flows (deleted in n8n but still in local DB)
        if "404" in str(exc):
            _cleanup_local(db, flow_id)
            return {"success": True, "note": "Flujo fantasma limpiado de la base de datos local."}
        raise HTTPException(status_code=503, detail=str(exc))

    _cleanup_local(db, flow_id)
    return {"success": True}


def _cleanup_local(db: Session, flow_id: str):
    db.query(FlujoTrabajo).filter(FlujoTrabajo.id_flujo_n8n == flow_id).delete()
    db.commit()
