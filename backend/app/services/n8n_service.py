"""
ClawFlow — N8N API Service
All communication with the n8n REST API is encapsulated here (OOP).
"""
from __future__ import annotations
import os
from typing import Any

import httpx

N8N_HOST    = os.getenv("N8N_HOST", "http://n8n:5678")
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
        self.headers = {
            "X-N8N-API-KEY": api_key,
            "Content-Type": "application/json",
        }

    def _client(self) -> httpx.AsyncClient:
        return httpx.AsyncClient(headers=self.headers, timeout=30.0)

    # ── Workflows ─────────────────────────────────────────────────────────────
    async def list_workflows(self) -> list[dict]:
        async with self._client() as c:
            r = await c.get(f"{self.base}/workflows")
            r.raise_for_status()
            return r.json().get("data", [])

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

    # ── Executions ────────────────────────────────────────────────────────────
    async def list_executions(self, limit: int = 20) -> list[dict]:
        async with self._client() as c:
            r = await c.get(f"{self.base}/executions", params={"limit": limit})
            r.raise_for_status()
            return r.json().get("data", [])

    # ── Health ────────────────────────────────────────────────────────────────
    async def ping(self) -> bool:
        try:
            async with self._client() as c:
                r = await c.get(f"{self.base}/workflows", timeout=5.0)
                return r.status_code < 500
        except Exception:
            return False
