
from __future__ import annotations
from datetime import datetime
import os

import httpx
from fastapi import APIRouter, Depends, HTTPException, Path
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.database import CredencialAPI, get_db, Usuario, InstanciaN8N
from app.services.auth_service import get_current_user
from app.services.encryption_service import EncryptionService
from app.services.n8n_service import N8NService

router = APIRouter()
enc    = EncryptionService()

class AddCredentialRequest(BaseModel):
    servicio_base: str
    nombre_app: str
    tipo:       str = "api_key"
    token:      str

# --- NUEVA FUNCIÓN INDEPENDIENTE (Con escudo anti-crash) ---
def _get_n8n_service(db: Session, user: Usuario) -> N8NService:
    inst = db.query(InstanciaN8N).filter(
        InstanciaN8N.id_usuario == user.id_usuario,
        InstanciaN8N.activa == True
    ).first()

    host_url = inst.host_url if inst else os.getenv("N8N_HOST", "https://n8n.curikprojects.me")
    
    # Si la llave en la BD se corrompió, no explota (500), usa la del .env
    try:
        api_key = enc.decrypt(inst.api_key_cifrada) if inst and inst.api_key_cifrada else os.getenv("N8N_API_KEY", "")
    except Exception:
        api_key = os.getenv("N8N_API_KEY", "")

    return N8NService(host=host_url, api_key=api_key)

# ---------------------------------------------------------------------------------

# ── UC08: List Credentials ─────────────────────────────────────────────────────
@router.get("/list")
async def list_credentials(db: Session = Depends(get_db), current_user: Usuario = Depends(get_current_user)):
    # Obtener locales
    creds = db.query(CredencialAPI).filter(
        CredencialAPI.id_usuario == current_user.id_usuario, 
        CredencialAPI.activa == True
    ).all()
    
    # Usar la nueva función local
    svc = _get_n8n_service(db, current_user)
    
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
    except Exception as e:
        print(f"[Credentials] Error listando n8n: {e}")

    return {"credentials": lista_final}

# ── UC08: Add / Validate Credential ───────────────────────────────────────────
@router.post("/add")
async def add_credential(
    body: AddCredentialRequest, 
    db: Session = Depends(get_db), 
    current_user: Usuario = Depends(get_current_user)
):
    svc = _get_n8n_service(db, current_user)
    
    n8n_payloads = {
        "Telegram":      {"type": "telegramApi",       "data": {"accessToken": body.token}},
        "Discord":       {"type": "discordWebhookApi", "data": {"webhookUri": body.token}},
        "GitHub":        {"type": "githubApi",         "data": {"accessToken": body.token}},
        "Slack":         {"type": "slackApi",          "data": {"accessToken": body.token}},
        "Notion":        {"type": "notionApi",         "data": {"apiKey": body.token}},
        "Airtable":      {"type": "airtableApi",       "data": {"apiKey": body.token}},
        "Google_Sheets": {"type": "googleApi",         "data": {"accessToken": body.token}}, 
    }

    # Leemos el servicio base para saber cómo formatear para n8n
    app_key = body.servicio_base
    if app_key in n8n_payloads:
        n8n_type = n8n_payloads[app_key]["type"]
        n8n_data = n8n_payloads[app_key]["data"]
    else:
        n8n_type = "httpHeaderAuth"
        n8n_data = {"name": "Authorization", "value": f"Bearer {body.token}"}

    conexion_n8n_exitosa = False
    try:
        # Enviamos a n8n el ALIAS único (body.nombre_app) para que no haya choques
        await svc.create_credential(body.nombre_app, n8n_type, n8n_data)
        conexion_n8n_exitosa = True
    except Exception as e:
        print(f"[Credentials] Error subiendo a n8n el tipo {n8n_type}: {e}")

    encrypted = enc.encrypt(body.token)
    estado = "valida" if conexion_n8n_exitosa else "invalida"
    
    # Creamos un JSON con el servicio real para esconderlo en la BD
    metadata_dict = {"app_service": body.servicio_base}

    existing = db.query(CredencialAPI).filter(
        CredencialAPI.id_usuario == current_user.id_usuario,
        CredencialAPI.nombre_app == body.nombre_app # Upsert basado en el Alias
    ).first()

    if existing:
        existing.token_cifrado = encrypted
        existing.tipo = body.tipo
        existing.estado_conexion = estado
        existing.metadata_json = metadata_dict
        existing.activa = True
    else:
        db.add(CredencialAPI(
            id_usuario=current_user.id_usuario,
            nombre_app=body.nombre_app,
            tipo=body.tipo,
            token_cifrado=encrypted,
            metadata_json=metadata_dict,
            estado_conexion=estado 
        ))
        
    db.commit()
    
    if not conexion_n8n_exitosa:
        raise HTTPException(status_code=400, detail="n8n rechazó el formato.")

    return {"success": True}

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