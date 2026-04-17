"""
ClawFlow — Voice Router
UC02: Dictar Comando de Automatización
UC03: Procesar Lenguaje y Generar JSON
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.database import ComandoVoz, get_db
from app.services.llm_service import LLMService
from app.services.auth_service import get_current_user
from app.models.database import Usuario

router     = APIRouter()
llm_service = LLMService()


class GenerateFlowRequest(BaseModel):
    text: str


# ── UC02: Transcribe Audio ─────────────────────────────────────────────────────
@router.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """
    Receives audio blob from frontend (MediaRecorder / WebSpeech API),
    runs Whisper STT, and returns the transcribed text.
    """
    # Validate file size (max 25 MB)
    content = await audio.read()
    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="El archivo de audio es demasiado grande (máx 25 MB).")

    if not content:
        raise HTTPException(status_code=422, detail="No se recibió audio.")

    # Log the attempt
    cmd = ComandoVoz(id_usuario=current_user.id_usuario, estado="procesando")
    db.add(cmd)
    db.commit()
    db.refresh(cmd)

    try:
        text = llm_service.transcribe_audio(content, filename=audio.filename or "audio.webm")
    except ValueError as e:
        cmd.estado = "error"
        cmd.error_detalle = str(e)
        db.commit()
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        cmd.estado = "error"
        cmd.error_detalle = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail="Error interno en la transcripción.")

    cmd.texto_transcrito = text
    db.commit()

    return {"text": text, "command_id": cmd.id}


# ── UC03: Generate n8n JSON ────────────────────────────────────────────────────
@router.post("/generate-flow")
async def generate_flow(
    body: GenerateFlowRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """
    Sends transcribed (or manually typed) text to the LLM,
    which returns a valid n8n workflow JSON structure.
    """
    if not body.text.strip():
        raise HTTPException(status_code=422, detail="El texto del comando no puede estar vacío.")

    # Save command record
    cmd = ComandoVoz(
        id_usuario=current_user.id_usuario,
        texto_transcrito=body.text,
        estado="procesando",
    )
    db.add(cmd)
    db.commit()
    db.refresh(cmd)

    try:
        workflow_json = await llm_service.generate_workflow_json(body.text)
    except ValueError as e:
        cmd.estado = "error"
        cmd.error_detalle = str(e)
        db.commit()
        raise HTTPException(status_code=422, detail=str(e))
    except Exception as e:
        cmd.estado = "error"
        cmd.error_detalle = str(e)
        db.commit()
        raise HTTPException(status_code=500, detail="Error interno al generar el flujo.")

    import json
    cmd.json_generado = json.dumps(workflow_json)
    cmd.estado = "exito"
    db.commit()

    nodes = llm_service.extract_node_names(workflow_json)

    return {
        "workflow_json": workflow_json,
        "nodes": [{"name": n, "type": n} for n in nodes],
        "command_id": cmd.id,
        "transcription": body.text,
    }
