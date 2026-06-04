"""
ClawFlow — N8N API Service  (v2)
All n8n REST API communication + user-aware factory function.
"""
from __future__ import annotations
import os
from typing import Any

import httpx

N8N_HOST    = os.getenv("N8N_HOST",    "http://n8n:5678")
N8N_API_KEY = os.getenv("N8N_API_KEY", "")


class N8NService:
    """
    Wraps the n8n REST API.
    All methods are async and raise httpx.HTTPError on failure.
    """

    def __init__(
        self,
        host: str = N8N_HOST,
        api_key: str = N8N_API_KEY,
    ) -> None:
        self.base = host.rstrip("/") + "/api/v1"
        # Agregamos el User-Agent para evitar bloqueos de Cloudflare
        self.headers = {
            "X-N8N-API-KEY": api_key,
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ClawFlow/1.0",
        }

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(headers=self.headers, timeout=30.0)

    # ── Workflows ─────────────────────────────────────────────────────────────
    async def list_workflows(self) -> list[dict]:
        async with self._client() as c:
            r = await c.get(f"{self.base}/workflows")
            r.raise_for_status()
            return r.json().get("data", r.json() if isinstance(r.json(), list) else [])

    async def get_workflow(self, flow_id: str) -> dict:
        async with self._client() as c:
            r = await c.get(f"{self.base}/workflows/{flow_id}")
            r.raise_for_status()
            return r.json()

    async def create_workflow(self, payload: dict) -> dict:
        async with self._client() as c:
            r = await c.post(f"{self.base}/workflows", json=payload)
            r.raise_for_status()
            return r.json()

    async def activate_workflow(self, flow_id: str) -> dict:
        async with self._client() as c:
            r = await c.put(f"{self.base}/workflows/{flow_id}/activate")
            r.raise_for_status()
            return r.json()

    async def deactivate_workflow(self, flow_id: str) -> dict:
        async with self._client() as c:
            r = await c.put(f"{self.base}/workflows/{flow_id}/deactivate")
            r.raise_for_status()
            return r.json()

    async def delete_workflow(self, flow_id: str) -> bool:
        async with self._client() as c:
            r = await c.delete(f"{self.base}/workflows/{flow_id}")
            return r.status_code in (200, 204)

    async def list_executions(self, limit: int = 20) -> list[dict]:
        async with self._client() as c:
            r = await c.get(f"{self.base}/executions", params={"limit": limit})
            r.raise_for_status()
            return r.json().get("data", [])

    # ── Credentials (NEW) ─────────────────────────────────────────────────────
    async def list_n8n_credentials(self) -> list[dict]:
        """List all credentials stored in this n8n instance."""
        async with self._client() as c:
            r = await c.get(f"{self.base}/credentials")

            if r.status_code >= 400:
                print(f"❌ ERROR N8N: {r.text}") 
            r.raise_for_status()
            data = r.json()
            # n8n returns {"data": [...]} or directly a list
            return data.get("data", data) if isinstance(data, dict) else data
            

    async def create_n8n_credential(
        self, name: str, n8n_type: str, data: dict[str, Any]
    ) -> dict:
        """
        Create a new credential in n8n.
        Works reliably for API-key / token-based credential types.
        OAuth2 credentials cannot be fully created this way (require browser flow).
        """
        payload = {"name": name, "type": n8n_type, "data": data}
        async with self._client() as c:
            r = await c.post(f"{self.base}/credentials", json=payload)
            r.raise_for_status()
            return r.json()

    async def get_n8n_credential_by_name(self, name: str) -> dict | None:
        """Find an n8n credential by name (case-sensitive)."""
        creds = await self.list_n8n_credentials()
        for cred in creds:
            if cred.get("name") == name:
                return cred
        return None

    # ── Health ────────────────────────────────────────────────────────────────
    async def ping(self) -> bool:
        """Returns True if n8n responds (regardless of credential validity)."""
        try:
            async with self._client(timeout=6.0) as c:
                r = await c.get(f"{self.base}/workflows", params={"limit": 1})
                return r.status_code < 500
        except Exception:
            return False


# ── Factory: user-aware N8NService ────────────────────────────────────────────
async def get_n8n_for_user(db, user_id: int) -> N8NService:
    """
    Returns an N8NService configured with the user's active n8n instance
    (host_url + api_key from DB). Falls back to env vars if no record found.

    This is the ONLY correct way to instantiate N8NService across all routers.
    """
    from app.models.database import InstanciaN8N
    from app.services.encryption_service import EncryptionService

    inst = db.query(InstanciaN8N).filter(
        InstanciaN8N.id_usuario == user_id,
        InstanciaN8N.activa == True,
    ).first()

    if not inst:
        return N8NService()   # env-var defaults

    enc = EncryptionService()
    try:
        api_key = enc.decrypt(inst.api_key_cifrada) if inst.api_key_cifrada else N8N_API_KEY
    except Exception:
        api_key = N8N_API_KEY

    return N8NService(host=inst.host_url, api_key=api_key)
