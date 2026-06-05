"""
ClawFlow — LLM Service  (v2 — Groq primary, OpenAI/Ollama fallback)
Handles:
  • Speech-to-Text via OpenAI Whisper (local)
  • Credential-need analysis via Groq (fast structured JSON)
  • Workflow JSON generation via Groq with injected credential context
"""
from __future__ import annotations
import json
import os
import re
import tempfile
from typing import Any

import httpx
from groq import Groq


GROQ_API_KEY = os.getenv("LLMAPIKEY", "")
GROQ_MODEL   = os.getenv("LLM_MODEL", "llama-3.3-70b-versatile")

# ── n8n Workflow System Prompt ────────────────────────────────────────────────
_N8N_SYSTEM = """
Eres ClawFlow, un arquitecto experto en flujos de trabajo n8n.
Tu ÚNICA función es generar un objeto JSON de flujo de trabajo n8n válido.
Nunca expliques ni comentes. Solo JSON puro.

REGLAS OBLIGATORIAS:
1. Responde ÚNICAMENTE con un objeto JSON crudo. Sin markdown, sin bloques de código, sin texto extra.
2. El JSON debe tener: "name", "nodes", "connections", "settings".
3. Cada nodo debe tener: "id" (string único), "name", "type" (tipo completo n8n), 
   "typeVersion" (int), "position" ([x, y]), "parameters" (objeto).
4. El primer nodo siempre es un trigger (Webhook, Schedule, Gmail Trigger, etc.).
5. "connections": mapea el "id" del nodo origen a {"main": [[{"node": "id_destino", "type": "main", "index": 0}]]}.
6. "settings": {"executionOrder": "v1"}.
7. Si el contexto de credenciales indica credenciales específicas, DEBES incluirlas en 
   el nodo correspondiente bajo "credentials": {"tipo_cred": {"id": "PLACEHOLDER", "name": "Nombre"}}.

TIPOS DE NODO COMUNES:
n8n-nodes-base.webhook | n8n-nodes-base.gmail | n8n-nodes-base.googleDrive
n8n-nodes-base.googleSheets | n8n-nodes-base.slack | n8n-nodes-base.httpRequest
n8n-nodes-base.set | n8n-nodes-base.if | n8n-nodes-base.scheduleTrigger
n8n-nodes-base.postgres | n8n-nodes-base.mysql | n8n-nodes-base.telegram
n8n-nodes-base.code | n8n-nodes-base.emailSend | n8n-nodes-base.github
n8n-nodes-base.notion | n8n-nodes-base.airtable | n8n-nodes-base.discord
"""

# ── Credential Analysis System Prompt ────────────────────────────────────────
_ANALYSIS_SYSTEM = """
Eres un analizador de flujos n8n. Dado un comando de automatización en español,
identifica qué nodos de n8n requerirán credenciales y de qué tipo.

Responde ÚNICAMENTE con un array JSON. Sin markdown, sin texto adicional.

Tipos de credencial n8n conocidos:
- gmailOAuth2          → nodos Gmail
- googleDriveOAuth2    → nodos Google Drive
- googleSheetsOAuth2   → nodos Google Sheets
- slackApi             → nodos Slack
- githubApi            → nodos GitHub
- notionApi            → nodos Notion
- airtableApi          → nodos Airtable
- telegramApi          → nodos Telegram
- discordWebhookApi    → nodos Discord
- mysqlCredentials     → nodos MySQL
- postgres             → nodos PostgreSQL
- httpBasicAuth        → HTTP Request con autenticación básica

Formato de respuesta:
[
  {
    "node_type": "n8n-nodes-base.gmail",
    "node_name": "Gmail Trigger",
    "credential_type": "gmailOAuth2",
    "credential_label": "Gmail OAuth2",
    "purpose": "Para leer correos entrantes de Gmail"
  }
]

Si ningún nodo requiere credenciales (ej: solo Webhook + HTTP sin auth), devuelve [].
"""


class LLMService:
    """
    Handles STT (Whisper) and LLM operations (Groq → OpenAI → Ollama).
    """

    def __init__(self) -> None:
        self.groq_key    = GROQ_API_KEY
        self.groq_model  = GROQ_MODEL
        self.openai_key  = os.getenv("OPENAI_API_KEY", "")
        self.ollama_url  = os.getenv("OLLAMA_URL", "http://host.docker.internal:11434")
        self.ollama_model= os.getenv("LLM_MODEL", "llama3:8b")
        self._whisper    = None

    # ── Whisper STT ───────────────────────────────────────────────────────────
    def _load_whisper(self):
        if self._whisper is None:
            import whisper as _w
            self._whisper = _w.load_model("base")
        return self._whisper

    def transcribe_audio(self, audio_bytes: bytes, filename: str = "audio.webm") -> str:
        suffix = "." + filename.rsplit(".", 1)[-1] if "." in filename else ".webm"
        with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
            tmp.write(audio_bytes)
            path = tmp.name
        try:
            result = self._load_whisper().transcribe(path, language="es", fp16=False)
            text = result.get("text", "").strip()
        finally:
            os.unlink(path)
        if not text:
            raise ValueError("No se reconoció voz en el audio.")
        return text

    # ── Credential Analysis ───────────────────────────────────────────────────
    async def analyze_for_credentials(self, text: str) -> list[dict]:
        """
        Asks the LLM to identify which n8n credential types are needed for this workflow.
        Returns a list of {node_type, node_name, credential_type, credential_label, purpose}.
        """
        raw = await self._chat(
            system=_ANALYSIS_SYSTEM,
            user=f"Comando de automatización: {text}",
            max_tokens=800,
            temperature=0.05,
        )
        return self._parse_json_array(raw)

    # ── Workflow Generation with Credential Context ────────────────────────────
    async def generate_workflow_with_credentials(
        self,
        text: str,
        credential_context: str = "",
    ) -> dict:
        """
        Generates a full n8n workflow JSON, optionally with credential context
        injected into the system prompt.
        """
        system = _N8N_SYSTEM
        if credential_context:
            system = f"{_N8N_SYSTEM}\n\n{credential_context}"

        raw = await self._chat(
            system=system,
            user=f"Crea un flujo n8n para: {text}",
            max_tokens=3000,
            temperature=0.1,
        )
        return self._parse_and_validate_workflow(raw)

    # ── Internal: unified chat dispatcher ────────────────────────────────────
    async def _chat(
        self,
        system: str,
        user: str,
        max_tokens: int = 2000,
        temperature: float = 0.1,
    ) -> str:
        # 1. Groq (primary)
        if self.groq_key:
            result = await self._groq_chat(system, user, max_tokens, temperature)
            if result:
                return result

        # 2. OpenAI (first fallback)
        if self.openai_key:
            result = await self._openai_chat(system, user, max_tokens, temperature)
            if result:
                return result

        # 3. Ollama (last resort)
        result = await self._ollama_chat(system, user, max_tokens, temperature)
        if result:
            return result

        raise RuntimeError("Ningún proveedor de LLM respondió correctamente.")

    async def _groq_chat(self, system, user, max_tokens, temperature) -> str:
        try:
            # Usamos el cliente síncrono estándar de Groq
            client = Groq(api_key=self.groq_key)
            resp = client.chat.completions.create(
                model=self.groq_model,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user",   "content": user},
                ],
                max_tokens=max_tokens,
                temperature=temperature,
            )
            return resp.choices[0].message.content or ""
        
        except Exception as exc:
            print(f"[LLM] Groq error: {exc}")
            return ""

    async def _openai_chat(self, system, user, max_tokens, temperature) -> str:
        try:
            async with httpx.AsyncClient(timeout=60.0) as c:
                r = await c.post(
                    "https://api.openai.com/v1/chat/completions",
                    headers={"Authorization": f"Bearer {self.openai_key}"},
                    json={
                        "model": "gpt-4o-mini",
                        "messages": [
                            {"role": "system", "content": system},
                            {"role": "user",   "content": user},
                        ],
                        "max_tokens":  max_tokens,
                        "temperature": temperature,
                    },
                )
                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"]
        except Exception as exc:
            print(f"[LLM] OpenAI error: {exc}")
            return ""

    async def _ollama_chat(self, system, user, max_tokens, temperature) -> str:
        try:
            prompt = f"{system}\n\nUSER: {user}"
            async with httpx.AsyncClient(timeout=90.0) as c:
                r = await c.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model":  self.ollama_model,
                        "prompt": prompt,
                        "stream": False,
                        "options": {"temperature": temperature, "num_predict": max_tokens},
                    },
                )
                r.raise_for_status()
                return r.json().get("response", "")
        except Exception as exc:
            print(f"[LLM] Ollama error: {exc}")
            return ""

    # ── JSON parsers ──────────────────────────────────────────────────────────
    @staticmethod
    def _parse_json_array(raw: str) -> list[dict]:
        """Extract a JSON array from potentially messy LLM output."""
        cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
        try:
            result = json.loads(cleaned)
            return result if isinstance(result, list) else []
        except json.JSONDecodeError:
            match = re.search(r"\[.*\]", cleaned, re.DOTALL)
            if match:
                try:
                    return json.loads(match.group())
                except Exception:
                    pass
        return []

    @staticmethod
    def _parse_and_validate_workflow(raw: str) -> dict:
        """Extract and validate the n8n workflow JSON from LLM output."""
        cleaned = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`").strip()
        try:
            wf = json.loads(cleaned)
        except json.JSONDecodeError:
            match = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if not match:
                raise ValueError(
                    "No pude estructurar el flujo correctamente. "
                    "Por favor, sé más específico con los servicios que deseas conectar."
                )
            wf = json.loads(match.group())

        required = {"name", "nodes", "connections", "settings"}
        missing  = required - set(wf.keys())
        if missing:
            raise ValueError(
                f"El JSON generado no tiene los campos requeridos: {missing}. "
                "Intenta ser más específico."
            )
        if not isinstance(wf.get("nodes"), list) or not wf["nodes"]:
            raise ValueError("El flujo generado no contiene nodos. Sé más específico.")
        return wf

    @staticmethod
    def extract_node_names(workflow: dict) -> list[str]:
        return [n.get("name", n.get("type", "Nodo")) for n in workflow.get("nodes", [])]
