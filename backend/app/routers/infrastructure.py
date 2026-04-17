"""
ClawFlow — Infrastructure Router
UC07: Administrar Contenedores y Conexiones
"""
from __future__ import annotations
import os

import httpx
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.database import InstanciaN8N, get_db, Usuario
from app.services.auth_service import get_current_user
from app.services.encryption_service import EncryptionService
from app.services.n8n_service import N8NService

router = APIRouter()
enc    = EncryptionService()


class SaveConfigRequest(BaseModel):
    n8n_url:     str | None = None
    n8n_api_key: str | None = None
    llm_engine:  str | None = None
    ollama_model:str | None = None
    ollama_url:  str | None = None
    openai_key:  str | None = None
    openai_model:str | None = None


# ── UC07: Ping n8n ─────────────────────────────────────────────────────────────
@router.get("/ping-n8n")
async def ping_n8n(current_user: Usuario = Depends(get_current_user)):
    svc    = N8NService()
    online = await svc.ping()
    return {"online": online}


# ── UC07: Full Infrastructure Status ──────────────────────────────────────────
@router.get("/status")
async def infrastructure_status(current_user: Usuario = Depends(get_current_user)):
    services = []

    # n8n
    n8n_online = await N8NService().ping()
    services.append({
        "name":   "n8n",
        "detail": f"{os.getenv('N8N_HOST', 'http://n8n:5678')}",
        "online": n8n_online,
    })

    # FastAPI self (always true if we get here)
    services.append({"name": "FastAPI", "detail": "Backend Python", "online": True})

    # MySQL — try a quick check via SQLAlchemy
    try:
        from app.models.database import engine
        with engine.connect() as conn:
            conn.execute(__import__("sqlalchemy").text("SELECT 1"))
        services.append({"name": "MySQL",   "detail": "clawflow db", "online": True})
    except Exception:
        services.append({"name": "MySQL",   "detail": "clawflow db", "online": False})

    # Nginx — try HTTP HEAD to root
    try:
        async with httpx.AsyncClient(timeout=3.0) as c:
            r = await c.head("http://nginx/")
            services.append({"name": "Nginx", "detail": "Reverse proxy", "online": r.status_code < 500})
    except Exception:
        services.append({"name": "Nginx", "detail": "Reverse proxy", "online": False})

    # Cloudflare — check internet connectivity
    try:
        async with httpx.AsyncClient(timeout=5.0) as c:
            r = await c.get("https://cloudflare.com/cdn-cgi/trace")
            services.append({"name": "Cloudflare", "detail": "Tunnel / CDN", "online": r.status_code == 200})
    except Exception:
        services.append({"name": "Cloudflare", "detail": "Tunnel / CDN", "online": False})

    return {"services": services}


# ── UC07: Save Config ──────────────────────────────────────────────────────────
@router.post("/save-config")
async def save_config(
    body: SaveConfigRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """
    Validates the new n8n API key with a ping test before saving.
    Rejects the save if the ping fails (UC07 Alternative Flow: Clave API Inválida).
    """
    if body.n8n_api_key and body.n8n_url:
        svc = N8NService(host=body.n8n_url, api_key=body.n8n_api_key)
        if not await svc.ping():
            raise HTTPException(
                status_code=400,
                detail="La clave API o URL de n8n no son válidas. Ping de prueba fallido.",
            )

        # Upsert instance
        inst = db.query(InstanciaN8N).filter(
            InstanciaN8N.id_usuario == current_user.id_usuario,
            InstanciaN8N.activa == True,
        ).first()

        if inst:
            inst.host_url        = body.n8n_url
            inst.api_key_cifrada = enc.encrypt(body.n8n_api_key)
        else:
            db.add(InstanciaN8N(
                id_usuario=current_user.id_usuario,
                nombre="Local n8n",
                host_url=body.n8n_url,
                api_key_cifrada=enc.encrypt(body.n8n_api_key),
            ))
        db.commit()

    return {"success": True, "message": "Configuración guardada y verificada correctamente."}
