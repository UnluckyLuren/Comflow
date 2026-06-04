"""
ClawFlow — Infrastructure Router  (v2)
UC07: Administrar Contenedores y Conexiones

KEY FIX: save-config now:
  1. Tests the ping with the NEW credentials BEFORE saving
  2. Upserts InstanciaN8N for the current user
  3. All subsequent calls use get_n8n_for_user() which reads from DB
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
from app.services.n8n_service import N8NService, get_n8n_for_user

router = APIRouter()
enc    = EncryptionService()


class SaveConfigRequest(BaseModel):
    n8n_url:      str | None = None
    n8n_api_key:  str | None = None
    # LLM config (stored for future use, not validated here)
    llm_engine:   str | None = None
    ollama_model: str | None = None
    ollama_url:   str | None = None
    openai_key:   str | None = None
    openai_model: str | None = None


# ── Ping n8n ──────────────────────────────────────────────────────────────────
@router.get("/ping-n8n")
async def ping_n8n(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """Uses the user's stored n8n instance credentials (not env vars)."""
    svc    = await get_n8n_for_user(db, current_user.id_usuario)
    online = await svc.ping()
    return {"online": online}


# ── Full Status ───────────────────────────────────────────────────────────────
@router.get("/status")
async def infrastructure_status(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    services = []

    # n8n — use user's stored instance
    svc        = await get_n8n_for_user(db, current_user.id_usuario)
    n8n_online = await svc.ping()

    # Retrieve host URL for display
    inst = db.query(InstanciaN8N).filter(
        InstanciaN8N.id_usuario == current_user.id_usuario,
        InstanciaN8N.activa     == True,
    ).first()
    n8n_url_display = inst.host_url if inst else os.getenv("N8N_HOST", "http://n8n:5678")

    services.append({
        "name":   "n8n",
        "detail": n8n_url_display,
        "online": n8n_online,
    })

    # FastAPI
    services.append({"name": "FastAPI", "detail": "Backend Python 3.11", "online": True})

    # MySQL
    try:
        from app.models.database import engine
        import sqlalchemy
        with engine.connect() as conn:
            conn.execute(sqlalchemy.text("SELECT 1"))
        services.append({"name": "MySQL", "detail": "clawflow db", "online": True})
    except Exception:
        services.append({"name": "MySQL", "detail": "clawflow db", "online": False})

    # Nginx
    try:
        async with httpx.AsyncClient(timeout=3.0) as c:
            r = await c.head("http://nginx/")
            services.append({"name": "Nginx", "detail": "Reverse proxy", "online": r.status_code < 500})
    except Exception:
        services.append({"name": "Nginx", "detail": "Reverse proxy", "online": False})

    # Cloudflare
    try:
        async with httpx.AsyncClient(timeout=5.0) as c:
            r = await c.get("https://cloudflare.com/cdn-cgi/trace")
            services.append({"name": "Cloudflare", "detail": "Tunnel / CDN", "online": r.status_code == 200})
    except Exception:
        services.append({"name": "Cloudflare", "detail": "Tunnel / CDN", "online": False})

    return {"services": services}


# ── UC07: Save Config (FIXED) ────────────────────────────────────────────────
@router.post("/save-config")
async def save_config(
    body: SaveConfigRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """
    Save n8n connection settings.

    Flow:
      1. If n8n_url or n8n_api_key provided:
         a. Ping n8n with the NEW credentials
         b. If ping fails → return 400 (UC07 Alternative: Clave API Inválida)
         c. If ping succeeds → encrypt key and upsert InstanciaN8N in DB
      2. Return success

    This ensures get_n8n_for_user() will pick up the new config immediately.
    """
    if body.n8n_url or body.n8n_api_key:
        # Resolve final values (keep existing if not provided)
        inst_existing = db.query(InstanciaN8N).filter(
            InstanciaN8N.id_usuario == current_user.id_usuario,
            InstanciaN8N.activa     == True,
        ).first()

        # Determine effective URL and key
        if body.n8n_url:
            new_url = body.n8n_url.rstrip("/")
        elif inst_existing:
            new_url = inst_existing.host_url
        else:
            new_url = os.getenv("N8N_HOST", "http://n8n:5678")

        if body.n8n_api_key:
            new_key = body.n8n_api_key.strip()
        elif inst_existing:
            try:
                new_key = enc.decrypt(inst_existing.api_key_cifrada)
            except Exception:
                new_key = os.getenv("N8N_API_KEY", "")
        else:
            new_key = os.getenv("N8N_API_KEY", "")

        # ── Ping test with NEW credentials ──────────────────────────────────
        test_svc = N8NService(host=new_url, api_key=new_key)
        if not await test_svc.ping():
            raise HTTPException(
                status_code=400,
                detail=(
                    "Ping de prueba fallido. "
                    "Verifica que la URL de n8n sea accesible y que la API Key sea válida. "
                    "Recuerda activar la API en n8n: Configuración → API → Habilitar API."
                ),
            )

        # ── Persist to DB ────────────────────────────────────────────────────
        encrypted_key = enc.encrypt(new_key)

        if inst_existing:
            inst_existing.host_url        = new_url
            inst_existing.api_key_cifrada = encrypted_key
        else:
            db.add(InstanciaN8N(
                id_usuario=current_user.id_usuario,
                nombre="Local n8n",
                host_url=new_url,
                api_key_cifrada=encrypted_key,
                activa=True,
            ))
        db.commit()

    return {
        "success": True,
        "message": "Configuración de n8n guardada y verificada correctamente.",
    }


# ── Get current n8n config (for form pre-population) ─────────────────────────
@router.get("/n8n-config")
async def get_n8n_config(
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    inst = db.query(InstanciaN8N).filter(
        InstanciaN8N.id_usuario == current_user.id_usuario,
        InstanciaN8N.activa     == True,
    ).first()

    if not inst:
        return {
            "host_url":     os.getenv("N8N_HOST", "http://n8n:5678"),
            "has_api_key":  bool(os.getenv("N8N_API_KEY", "")),
            "source":       "env",
        }

    return {
        "host_url":    inst.host_url,
        "has_api_key": bool(inst.api_key_cifrada),
        "source":      "database",
    }
