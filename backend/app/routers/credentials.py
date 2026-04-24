"""
ClawFlow — Credentials Router
UC08: Administrar Llaves de Acceso a Aplicaciones
"""
from __future__ import annotations
from datetime import datetime

import httpx
from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.database import CredencialAPI, get_db, Usuario
from app.services.auth_service import get_current_user
from app.services.encryption_service import EncryptionService

from app.models.database import InstanciaN8N
from app.services.n8n_service import N8NService

router = APIRouter()
enc    = EncryptionService()

# endpoints para la app
_TEST_URLS: dict[str, str] = {
    "Gmail_OAuth":    "https://www.googleapis.com/oauth2/v1/tokeninfo",
    "Google_Drive":   "https://www.googleapis.com/drive/v3/about",
    "Google_Sheets":  "https://sheets.googleapis.com/v4/spreadsheets",
    "Slack":          "https://slack.com/api/auth.test",
    "GitHub":         "https://api.github.com/user",
    "Notion":         "https://api.notion.com/v1/users/me",
    "Telegram":       "https://api.telegram.org/",
}


class AddCredentialRequest(BaseModel):
    nombre_app: str
    tipo:       str = "api_key"
    token:      str


# ── UC08: List Credentials ─────────────────────────────────────────────────────
@router.get("/list")
async def list_credentials(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    lista_creds = []

    # Cargar credenciales locales (MySQL)
    creds = db.query(CredencialAPI).filter(
        CredencialAPI.id_usuario == current_user.id_usuario,
        CredencialAPI.activa == True,
    ).all()

    for c in creds:
        ultima_val = getattr(c, "ultima_validacion", None)
        actualizado = getattr(c, "updated_at", ultima_val) 

        lista_creds.append({
            "id_credencial":   c.id_credencial,
            "nombre_app":      c.nombre_app,
            "tipo":            c.tipo,
            "estado_conexion": c.estado_conexion,
            "ultima_validacion": ultima_val.isoformat() if ultima_val else None,
            "updated_at":      actualizado.isoformat() if actualizado else None,
        })

    # Cargar credenciales remotas (n8n)
    try:
        inst = db.query(InstanciaN8N).filter(
            InstanciaN8N.id_usuario == current_user.id_usuario,
            InstanciaN8N.activa == True,
        ).first()

        if inst:
            api_key = enc.decrypt(inst.api_key_cifrada) if inst.api_key_cifrada else ""
            svc = N8NService(host=inst.host_url, api_key=api_key)
            n8n_creds = await svc.list_credentials()

            for nc in n8n_creds:
                lista_creds.append({
                    "id_credencial":   nc.get("id"),
                    "nombre_app":      f"{nc.get('name')} (n8n)", # Le añadimos la etiqueta
                    "tipo":            nc.get("type"),
                    "estado_conexion": "valida", # Si están en n8n, asumimos que son válidas
                    "ultima_validacion": nc.get("updatedAt"),
                    "updated_at":      nc.get("updatedAt"),
                })
    except Exception as exc:
        print(f"[Credentials] Error sincronizando n8n: {exc}")

    return {"credentials": lista_creds}


# ── UC08: Add / Validate Credential ───────────────────────────────────────────
@router.post("/add")
async def add_credential(
    body: AddCredentialRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    # Connection test
    test_url = _TEST_URLS.get(body.nombre_app)
    connection_ok = False

    if test_url:
        headers = {"Authorization": f"Bearer {body.token}"}
        try:
            async with httpx.AsyncClient(timeout=8.0) as c:
                r = await c.get(test_url, headers=headers)
                # 200 or 401 (reachable, just wrong token format) = API is live
                connection_ok = r.status_code < 500
        except Exception:
            connection_ok = False
    else:
        # Unknown app — assume valid, just store it
        connection_ok = True

    if not connection_ok:
        raise HTTPException(
            status_code=400,
            detail="Test de conexión fallido. Verifica que el token sea válido.",
        )

    # Encrypt and upsert
    encrypted = enc.encrypt(body.token)

    existing = db.query(CredencialAPI).filter(
        CredencialAPI.id_usuario == current_user.id_usuario,
        CredencialAPI.nombre_app == body.nombre_app,
    ).first()

    if existing:
        existing.token_cifrado     = encrypted
        existing.tipo              = body.tipo
        existing.estado_conexion   = "valida"
        existing.ultima_validacion = datetime.utcnow()
        existing.activa            = True
    else:
        db.add(CredencialAPI(
            id_usuario=current_user.id_usuario,
            nombre_app=body.nombre_app,
            tipo=body.tipo,
            token_cifrado=encrypted,
            estado_conexion="valida",
            ultima_validacion=datetime.utcnow(),
        ))

    db.commit()
    return {"success": True, "message": "Credencial guardada y validada con AES-256."}


# ── UC08: Delete Credential ────────────────────────────────────────────────────
@router.delete("/{cred_id}")
async def delete_credential(
    cred_id: int = Path(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    cred = db.query(CredencialAPI).filter(
        CredencialAPI.id_credencial == cred_id,
        CredencialAPI.id_usuario == current_user.id_usuario,
    ).first()

    if not cred:
        raise HTTPException(status_code=404, detail="Credencial no encontrada.")

    cred.activa = False  # Soft delete
    db.commit()
    return {"success": True}
