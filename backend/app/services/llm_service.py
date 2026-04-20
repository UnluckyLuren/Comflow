"""
ClawFlow — LLM Service
Handles Speech-to-Text (Whisper) and n8n JSON generation (LLM).
"""
from __future__ import annotations
import json
import os
import re
import tempfile
from typing import Any

import httpx
import whisper

# ── N8n System Prompt ─────────────────────────────────────────────────────────
# ── N8n System Prompt ─────────────────────────────────────────────────────────
N8N_SYSTEM_PROMPT = """
You are ComFlow, an expert n8n workflow architect. Your ONLY job is to output
a valid n8n workflow JSON object. Never explain, never apologize. Just JSON.

RULES:
1. Output ONLY a raw JSON object. No markdown, no code fences, no extra text.
2. The JSON must have these top-level keys: "name", "nodes", "connections", "settings".
3. Every node must have: "id" (unique string), "name", "type" (full n8n node type like
   "n8n-nodes-base.gmail"), "typeVersion" (integer), "position" ([x, y] array),
   "parameters" (object).
4. The first node must always be a trigger (Webhook, Schedule, Gmail Trigger, etc.).
5. "settings" must include: {"executionOrder": "v1"}.
6. CRITICAL - CONNECTIONS: "connections" maps source node "id" to {"main": [[{"node": "target_id", "type": "main", "index": 0}]]}. Pay attention to the double brackets [ [ { ... } ] ]. EVERY NODE EXCEPT THE LAST MUST BE CONNECTED. DO NOT LEAVE ANY NODE ISOLATED ON THE CANVAS.
7. CRITICAL - SPATIAL SPACING ("position"): Nodes MUST NOT overlap. The first node starts at [200, 300]. Increase the X coordinate by 200 for every subsequent connected node in the chain (e.g., [400, 300], [600, 300], [800, 300]).
8. CRITICAL - FUNCTIONAL PARAMETERS: Always infer and include necessary parameters so the workflow works out-of-the-box. For example: Telegram needs {"chatId": "...", "text": "..."}, HTTP Request needs {"url": "...", "method": "GET"}, Webhook needs {"httpMethod": "POST", "path": "webhook-path"}. Use logical placeholder data if the user doesn't provide specifics.

COMMON NODE TYPES:
- n8n-nodes-base.webhook (Webhook Trigger)
- n8n-nodes-base.gmail (Gmail)
- n8n-nodes-base.googleDrive (Google Drive)
- n8n-nodes-base.googleSheets (Google Sheets)
- n8n-nodes-base.slack (Slack)
- n8n-nodes-base.httpRequest (HTTP Request)
- n8n-nodes-base.set (Set Variables)
- n8n-nodes-base.if (Conditional)
- n8n-nodes-base.scheduleTrigger (Schedule Trigger)
- n8n-nodes-base.postgres (PostgreSQL)
- n8n-nodes-base.mysql (MySQL)
- n8n-nodes-base.telegram (Telegram)
- n8n-nodes-base.code (Code/JavaScript)
- n8n-nodes-base.emailSend (Send Email SMTP)
- n8n-nodes-base.github (GitHub)
- n8n-nodes-base.notion (Notion)
- n8n-nodes-base.airtable (Airtable)

EXAMPLE OUTPUT:
{
  "name": "Gmail to Drive Backup",
  "nodes": [
    {
      "id": "node_1",
      "name": "Gmail Trigger",
      "type": "n8n-nodes-base.gmail",
      "typeVersion": 2,
      "position": [100, 300],
      "parameters": {"operation": "getAll", "filters": {}}
    },
    {
      "id": "node_2",
      "name": "Save to Drive",
      "type": "n8n-nodes-base.googleDrive",
      "typeVersion": 3,
      "position": [300, 300],
      "parameters": {"operation": "upload", "folderId": "root"}
    }
  ],
  "connections": {
    "node_1": {"main": [[{"node": "node_2", "type": "main", "index": 0}]]}
  },
  "settings": {"executionOrder": "v1"}
}
"""


class LLMService:
    """
    Handles:
      - STT transcription via OpenAI Whisper (local model)
      - Workflow JSON generation via Ollama (Llama3) or OpenAI
    """

    def __init__(self) -> None:
        self.llm_model   = os.getenv("LLM_MODEL", "openai/gpt-oss-120b")
        self.ollama_url  = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
        self.openai_key  = os.getenv("OPENAI_API_KEY", "")
        self.groq_key    = os.getenv("LLM_API_KEY", "")
        self._whisper_model: Any = None

    # ── Whisper STT ───────────────────────────────────────────────────────────
    def _load_whisper(self):
        if self._whisper_model is None:
            self._whisper_model = whisper.load_model("base")
        return self._whisper_model

    def transcribe_audio(self, audio_bytes: bytes, filename: str = "audio.webm") -> str:
        """Write audio to a temp file and run Whisper STT."""
        suffix = "." + filename.rsplit(".", 1)[-1] if "." in filename else ".webm"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name

        try:
            model = self._load_whisper()
            result = model.transcribe(tmp_path, language="es", fp16=False)
            text = result.get("text", "").strip()
        finally:
            os.unlink(tmp_path)

        if not text:
            raise ValueError("No se reconoció voz en el audio.")
        return text

    # ── LLM JSON Generation ────────────────────────────────────────────────────
    async def generate_workflow_json(self, text: str) -> dict:
        """
        Send transcribed text to LLM and get back a valid n8n workflow JSON.
        Tries Groq first, then Ollama, falls back to OpenAI.
        """
        raw = ""
        
        # 1. Prioridad principal: Groq
        if self.groq_key:
            raw = await self._call_groq(text)
            
        # 2. Fallback local: Ollama
        if not raw and self.ollama_url:
            raw = await self._call_ollama(text)
            
        # 3. Fallback nube: OpenAI
        if not raw and self.openai_key:
            raw = await self._call_openai(text)

        if not raw:
            raise ValueError("El LLM no devolvió una respuesta válida. Revisa tus API Keys o conexión.")

        workflow = self._parse_and_validate_json(raw)
        return workflow

    async def _call_ollama(self, text: str) -> str:
        """POST to local Ollama API."""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.llm_model,
                        "prompt": f"{N8N_SYSTEM_PROMPT}\n\nUSER REQUEST:\n{text}",
                        "stream": False,
                        "options": {"temperature": 0.1, "num_predict": 2048},
                    },
                )
                resp.raise_for_status()
                data = resp.json()
                return data.get("response", "")
        except Exception as exc:
            print(f"[LLMService] Ollama error: {exc}")
            return ""

    async def _call_openai(self, text: str) -> str:
        """Call OpenAI Chat Completions."""
        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                resp = await client.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.openai_key}"},
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [
                            {"role": "system", "content": N8N_SYSTEM_PROMPT},
                            {"role": "user",   "content": text},
                        ],
                        "temperature": 0.1,
                    },
                )
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]
        except Exception as exc:
            print(f"[LLMService] OpenAI error: {exc}")
            return ""

    async def _call_groq(self, text: str) -> str:
        """Call Groq API (OpenAI compatible endpoint) in Strict JSON Mode."""
        try:
            async with httpx.AsyncClient(timeout=15.0) as client:
                resp = await client.post(
                    "https://api.groq.com/openai/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.groq_key}"},
                    json={
                        "model": self.llm_model,
                        "messages": [
                            {"role": "system", "content": N8N_SYSTEM_PROMPT},
                            {"role": "user",   "content": f"Crea un flujo para: {text}. Devuelve el código en formato JSON."},
                        ],
                        "temperature": 0.0, # Temperatura 0 para lógica estricta y predecible
                        "response_format": { "type": "json_object" } # <--- LA MAGIA DE GROQ AQUÍ
                    },
                )
                resp.raise_for_status()
                return resp.json()["choices"][0]["message"]["content"]
        except Exception as exc:
            print(f"[LLMService] Groq error: {exc}")
            return ""
        
    def _parse_and_validate_json(self, raw: str) -> dict:
        """Extract and validate JSON from LLM response."""
        # Strip markdown code fences if present
        cleaned = re.sub(r"```(?:json)?", "", raw).strip()
        cleaned = cleaned.rstrip("`").strip()

        # Try direct parse
        try:
            workflow = json.loads(cleaned)
        except json.JSONDecodeError:
            # Find first { ... } block
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if not match:
                raise ValueError(
                    "No pude estructurar el flujo correctamente. "
                    "Por favor, sé más específico con los servicios que deseas conectar."
                )
            workflow = json.loads(match.group())

        # Validate required keys
        required = {"name", "nodes", "connections", "settings"}
        missing  = required - set(workflow.keys())
        if missing:
            raise ValueError(
                f"El JSON generado no tiene los campos requeridos: {missing}. "
                "Intenta ser más específico."
            )

        if not isinstance(workflow.get("nodes"), list) or not workflow["nodes"]:
            raise ValueError("El flujo generado no contiene nodos. Sé más específico.")

        return workflow

    @staticmethod
    def extract_node_names(workflow: dict) -> list[str]:
        """Return a list of node names for the preview UI."""
        return [n.get("name", n.get("type", "Nodo")) for n in workflow.get("nodes", [])]
