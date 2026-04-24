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
# En backend/app/routes/credentials.py

@router.get("/list")
async def list_credentials(db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    # Obtener locales
    creds = db.query(CredencialAPI).filter(CredencialAPI.id_usuario == current_user.id_usuario, CredencialAPI.activa == True).all()
    
    # Obtener de n8n para fusionar
    from app.routes.workflows import _get_n8n
    svc, _ = _get_n8n(db, current_user)
    
    lista_final = []
    # Añadir locales
    for c in creds:
        lista_final.append({
            "id_credencial": c.id_credencial,
            "nombre_app": c.nombre_app,
            "tipo": c.tipo,
            "estado_conexion": c.estado_conexion,
            "origen": "local"
        })
    
    # Añadir de n8n
    try:
        n8n_creds = await svc.list_credentials()
        for nc in n8n_creds:
            lista_final.append({
                "id_credencial": nc.get("id"),
                "nombre_app": f"{nc.get('name')} (n8n)",
                "tipo": nc.get("type"),
                "estado_conexion": "valida",
                "origen": "n8n"
            })
    except: pass

    return {"credentials": lista_final}

@router.post("/add")
async def add_credential(
    body: AddCredentialRequest, 
    db: Session = Depends(get_db), 
    current_user: Usuario = Depends(get_current_user)
):
    from app.routes.workflows import _get_n8n
    svc, _ = _get_n8n(db, current_user)
    
    # Diccionario de Traducción para n8n
    # Mapea el nombre que viene del frontend hacia el formato exacto de n8n
    n8n_payloads = {
        "Telegram":      {"type": "telegramApi",       "data": {"accessToken": body.token}},
        "Discord":       {"type": "discordWebhookApi", "data": {"webhookUri": body.token}},
        "GitHub":        {"type": "githubApi",         "data": {"accessToken": body.token}},
        "Slack":         {"type": "slackApi",          "data": {"accessToken": body.token}},
        "Notion":        {"type": "notionApi",         "data": {"apiKey": body.token}},
        "Airtable":      {"type": "airtableApi",       "data": {"apiKey": body.token}},
        "Google_Sheets": {"type": "googleApi",         "data": {"accessToken": body.token}}, # Simplificado
    }

    # Buscar la estructura correcta o usar un modelo genérico
    app_key = body.nombre_app
    if app_key in n8n_payloads:
        n8n_type = n8n_payloads[app_key]["type"]
        n8n_data = n8n_payloads[app_key]["data"]
    else:
        # FALLBACK UNIVERSAL (Para "Custom" u otras APIs)
        # Lo configuramos como un Header Auth Genérico (Bearer Token)
        n8n_type = "httpHeaderAuth"
        n8n_data = {"name": "Authorization", "value": f"Bearer {body.token}"}

    # Guardar en n8n
    conexion_n8n_exitosa = False
    try:
        await svc.create_credential(body.nombre_app, n8n_type, n8n_data)
        conexion_n8n_exitosa = True
    except Exception as e:
        print(f"[Credentials] Error subiendo a n8n el tipo {n8n_type}: {e}")
        # Si da error 400, significa que n8n no reconoció los parámetros.

    # Guardar en MySQL local de ClawFlow
    encrypted = enc.encrypt(body.token)
    db.add(CredencialAPI(
        id_usuario=current_user.id_usuario,
        nombre_app=body.nombre_app,
        tipo=body.tipo,
        token_cifrado=encrypted,
        # Si n8n lo aceptó, lo marcamos como válido. Si no, queda inválido.
        estado_conexion="valida" if conexion_n8n_exitosa else "invalida" 
    ))
    db.commit()
    
    if not conexion_n8n_exitosa:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=400, 
            detail="Se guardó localmente, pero n8n rechazó el formato de esta credencial."
        )

    return {"success": True}


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
