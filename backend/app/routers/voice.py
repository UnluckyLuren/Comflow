"""
ClawFlow — Voice Router  (v2)
UC02: Dictar Comando de Automatización
UC03: Procesar Lenguaje y Generar JSON
  + Credential analysis and context injection
"""
from __future__ import annotations
import json

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.models.database import ComandoVoz, get_db, Usuario
from app.services.auth_service import get_current_user
from app.services.credential_service import CredentialService
from app.services.llm_service import LLMService

router      = APIRouter()
llm         = LLMService()
cred_svc    = CredentialService()


# ── Schemas ───────────────────────────────────────────────────────────────────
class AnalyzeRequest(BaseModel):
    text: str


class SelectedCredential(BaseModel):
    node_type:        str
    credential_type:  str
    credential_label: str
    mode:             str        # "use_stored" | "manual_name" | "skip"
    db_credential_id: int | None = None
    manual_name:      str | None = None
    credential_name:  str        # resolved display name to embed in workflow


class GenerateFlowRequest(BaseModel):
    text:                 str
    selected_credentials: list[SelectedCredential] = []
    command_id:           int | None = None


# ── UC02: Transcribe Audio ────────────────────────────────────────────────────
@router.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    content = await audio.read()
    if len(content) > 25 * 1024 * 1024:
        raise HTTPException(413, "El archivo de audio es demasiado grande (máx 25 MB).")
    if not content:
        raise HTTPException(422, "No se recibió audio.")

    cmd = ComandoVoz(id_usuario=current_user.id_usuario, estado="procesando")
    db.add(cmd); db.commit(); db.refresh(cmd)

    try:
        text = llm.transcribe_audio(content, filename=audio.filename or "audio.webm")
    except ValueError as e:
        cmd.estado = "error"; cmd.error_detalle = str(e); db.commit()
        raise HTTPException(422, str(e))
    except Exception:
        cmd.estado = "error"; db.commit()
        raise HTTPException(500, "Error interno en la transcripción.")

    cmd.texto_transcrito = text
    db.commit()
    return {"text": text, "command_id": cmd.id}


# ── NEW: Analyze credentials needed ──────────────────────────────────────────
@router.post("/analyze")
async def analyze_credentials(
    body: AnalyzeRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """
    Step 1.5 between transcription and generation.
    
    - Asks Groq to identify which credential types are needed.
    - Matches them against the user's stored vault.
    - Returns assignment status so the frontend can show the selection modal.
    
    Response:
      nodes_analysis:         raw LLM analysis
      credential_assignments: per-credential-type status + matches
      needs_interaction:      True if user must make choices
      auto_selected:          list of auto-selected credentials (if needs_interaction=False)
      auto_message:           user-friendly summary
    """
    if not body.text.strip():
        raise HTTPException(422, "Texto vacío.")

    # 1. Ask LLM what credentials are needed
    try:
        nodes_analysis = await llm.analyze_for_credentials(body.text)
    except Exception as exc:
        print(f"[voice/analyze] LLM error: {exc}")
        # Non-fatal: if analysis fails we can still proceed without credential injection
        return {
            "nodes_analysis":         [],
            "credential_assignments": [],
            "needs_interaction":      False,
            "auto_selected":          [],
            "auto_message":           "Análisis de credenciales no disponible. Procediendo sin credenciales.",
        }

    # 2. Match against user vault
    assignments, needs_interaction = cred_svc.find_matches_for_analysis(
        db, current_user.id_usuario, nodes_analysis
    )

    # Build auto-selected list (used when needs_interaction=False)
    auto_selected = []
    auto_parts    = []
    for a in assignments:
        if a["status"] == "found":
            auto_selected.append({
                "node_type":        a["node_type"],
                "credential_type":  a["credential_type"],
                "credential_label": a["credential_label"],
                "mode":             "use_stored",
                "db_credential_id": a["auto_selected"],
                "credential_name":  a["auto_name"],
            })
            auto_parts.append(f"✓ {a['credential_label']}: <b>{a['auto_name']}</b>")

    if not assignments:
        auto_message = "Este flujo no requiere credenciales adicionales."
    elif not needs_interaction:
        auto_message = "Credenciales asignadas automáticamente: " + " · ".join(auto_parts)
    else:
        missing = [a["credential_label"] for a in assignments if a["status"] == "not_found"]
        multi   = [a["credential_label"] for a in assignments if a["status"] == "multiple"]
        parts   = []
        if missing: parts.append(f"{len(missing)} credencial(es) faltante(s)")
        if multi:   parts.append(f"{len(multi)} credencial(es) con múltiples opciones")
        auto_message = "Se requiere tu atención: " + " · ".join(parts)

    return {
        "nodes_analysis":         nodes_analysis,
        "credential_assignments": assignments,
        "needs_interaction":      needs_interaction,
        "auto_selected":          auto_selected,
        "auto_message":           auto_message,
    }


# ── UC03: Generate Flow JSON ──────────────────────────────────────────────────
@router.post("/generate-flow")
async def generate_flow(
    body: GenerateFlowRequest,
    db: Session = Depends(get_db),
    current_user: Usuario = Depends(get_current_user),
):
    """
    Generates the n8n workflow JSON.
    If selected_credentials is provided, they are injected into the LLM prompt
    so the JSON already contains proper credential references.
    """
    if not body.text.strip():
        raise HTTPException(422, "El texto del comando no puede estar vacío.")

    # Reuse or create command record
    if body.command_id:
        cmd = db.query(ComandoVoz).filter(
            ComandoVoz.id == body.command_id,
            ComandoVoz.id_usuario == current_user.id_usuario,
        ).first()
    else:
        cmd = None

    if not cmd:
        cmd = ComandoVoz(
            id_usuario=current_user.id_usuario,
            texto_transcrito=body.text,
            estado="procesando",
        )
        db.add(cmd); db.commit(); db.refresh(cmd)

    # Build credential context for the LLM
    cred_list = [c.dict() for c in body.selected_credentials]
    credential_context = cred_svc.build_credential_context(cred_list)

    try:
        workflow_json = await llm.generate_workflow_with_credentials(
            text=body.text,
            credential_context=credential_context,
        )
    except ValueError as e:
        cmd.estado = "error"; cmd.error_detalle = str(e); db.commit()
        raise HTTPException(422, str(e))
    except Exception as e:
        cmd.estado = "error"; cmd.error_detalle = str(e); db.commit()
        raise HTTPException(500, "Error interno al generar el flujo.")

    cmd.json_generado = json.dumps(workflow_json)
    cmd.estado = "exito"
    db.commit()

    nodes = llm.extract_node_names(workflow_json)
    return {
        "workflow_json": workflow_json,
        "nodes":         [{"name": n, "type": n} for n in nodes],
        "command_id":    cmd.id,
        "transcription": body.text,
        # Pass credentials along so the deploy step can sync them
        "selected_credentials": cred_list,
    }
