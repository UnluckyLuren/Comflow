"""
ClawFlow — Credential Service
Central service for:
  1. Mapping n8n credential types ↔ stored credentials
  2. Matching user's vault to workflow needs
  3. Syncing credentials to n8n (auto-create API-key types)
  4. Generating step-by-step guidance for OAuth / complex credentials
"""
from __future__ import annotations
import json
from typing import Any

from sqlalchemy.orm import Session

# ── Credential Catalog ────────────────────────────────────────────────────────
# Each entry: our stored app name → n8n metadata
CREDENTIAL_CATALOG: dict[str, dict] = {
    "Gmail_OAuth": {
        "n8n_type":        "gmailOAuth2",
        "node_types":      ["n8n-nodes-base.gmail"],
        "label":           "Gmail OAuth2",
        "is_auto_creatable": False,   # Requires OAuth2 flow in n8n UI
        "data_format":     {"accessToken": "{token}"},
        "guidance": [
            "1. Ve a <b>console.cloud.google.com</b> → APIs y Servicios → Credenciales",
            "2. Crea un <b>ID de cliente OAuth 2.0</b> (tipo: Aplicación web)",
            "3. URI de redirección autorizada: <code>[URL de n8n]/rest/oauth2-credential/callback</code>",
            "4. Descarga el JSON con <b>Client ID</b> y <b>Client Secret</b>",
            "5. En n8n UI: <b>Configuración → Credenciales → Nueva → Gmail OAuth2 API</b>",
            "6. Pega Client ID y Client Secret → haz clic en <b>Conectar con Google</b>",
            "7. Completa la autorización en el navegador",
            "8. Anota el nombre de la credencial creada y escríbelo abajo",
        ],
    },
    "Google_Drive": {
        "n8n_type":        "googleDriveOAuth2",
        "node_types":      ["n8n-nodes-base.googleDrive"],
        "label":           "Google Drive OAuth2",
        "is_auto_creatable": False,
        "data_format":     {"accessToken": "{token}"},
        "guidance": [
            "1. En <b>console.cloud.google.com</b> activa la <b>API de Google Drive</b>",
            "2. Crea credenciales OAuth 2.0 (igual que Gmail)",
            "3. URI de redirección: <code>[URL de n8n]/rest/oauth2-credential/callback</code>",
            "4. En n8n UI: <b>Credenciales → Nueva → Google Drive OAuth2 API</b>",
            "5. Pega Client ID y Client Secret → conecta con Google",
            "6. Anota el nombre de la credencial creada",
        ],
    },
    "Google_Sheets": {
        "n8n_type":        "googleSheetsOAuth2",
        "node_types":      ["n8n-nodes-base.googleSheets"],
        "label":           "Google Sheets OAuth2",
        "is_auto_creatable": False,
        "guidance": [
            "1. Activa la <b>API de Google Sheets</b> en Cloud Console",
            "2. Crea credenciales OAuth 2.0",
            "3. En n8n UI: <b>Credenciales → Nueva → Google Sheets OAuth2 API</b>",
            "4. Conecta con Google y anota el nombre",
        ],
    },
    "Slack": {
        "n8n_type":        "slackApi",
        "node_types":      ["n8n-nodes-base.slack"],
        "label":           "Slack Bot Token",
        "is_auto_creatable": True,
        "data_format":     {"accessToken": "{token}"},
        "guidance": [
            "1. Ve a <b>api.slack.com/apps</b> → Crear nueva app",
            "2. En <b>OAuth & Permissions</b> agrega los scopes necesarios (chat:write, etc.)",
            "3. Instala la app en tu workspace",
            "4. Copia el <b>Bot User OAuth Token</b> (empieza con <code>xoxb-</code>)",
            "5. Pégalo en la <b>Bóveda de Credenciales</b> de ClawFlow como 'Slack'",
        ],
    },
    "GitHub": {
        "n8n_type":        "githubApi",
        "node_types":      ["n8n-nodes-base.github"],
        "label":           "GitHub Personal Access Token",
        "is_auto_creatable": True,
        "data_format":     {"accessToken": "{token}"},
        "guidance": [
            "1. Ve a <b>github.com → Settings → Developer settings → Personal access tokens</b>",
            "2. <b>Generate new token (classic)</b>",
            "3. Selecciona scopes: <code>repo</code>, <code>read:user</code>",
            "4. Genera y copia el token (<code>ghp_...</code>)",
            "5. Pégalo en la Bóveda de ClawFlow como 'GitHub'",
        ],
    },
    "Notion": {
        "n8n_type":        "notionApi",
        "node_types":      ["n8n-nodes-base.notion"],
        "label":           "Notion Integration Token",
        "is_auto_creatable": True,
        "data_format":     {"apiKey": "{token}"},
        "guidance": [
            "1. Ve a <b>notion.so/my-integrations</b> → Nueva integración",
            "2. Dale un nombre y elige el workspace",
            "3. Copia el <b>Internal Integration Secret</b> (<code>secret_...</code>)",
            "4. <b>Comparte las páginas</b> de Notion con la integración",
            "5. Pégalo en la Bóveda de ClawFlow como 'Notion'",
        ],
    },
    "Airtable": {
        "n8n_type":        "airtableApi",
        "node_types":      ["n8n-nodes-base.airtable"],
        "label":           "Airtable Personal Access Token",
        "is_auto_creatable": True,
        "data_format":     {"apiKey": "{token}"},
        "guidance": [
            "1. Ve a <b>airtable.com/create/tokens</b>",
            "2. Crea un <b>Personal Access Token</b>",
            "3. Scopes mínimos: <code>data.records:read</code>, <code>data.records:write</code>",
            "4. Copia el token (<code>pat...</code>)",
            "5. Pégalo en la Bóveda de ClawFlow como 'Airtable'",
        ],
    },
    "Telegram": {
        "n8n_type":        "telegramApi",
        "node_types":      ["n8n-nodes-base.telegram"],
        "label":           "Telegram Bot Token",
        "is_auto_creatable": True,
        "data_format":     {"accessToken": "{token}"},
        "guidance": [
            "1. Abre Telegram y busca <b>@BotFather</b>",
            "2. Envía <code>/newbot</code> y sigue las instrucciones",
            "3. Copia el token que te da BotFather",
            "4. Pégalo en la Bóveda de ClawFlow como 'Telegram'",
        ],
    },
    "Discord": {
        "n8n_type":        "discordWebhookApi",
        "node_types":      ["n8n-nodes-base.discord"],
        "label":           "Discord Webhook URL",
        "is_auto_creatable": True,
        "data_format":     {"webhookUri": "{token}"},
        "guidance": [
            "1. En Discord: <b>Configuración del servidor → Integraciones → Webhooks</b>",
            "2. Crea un nuevo webhook para el canal deseado",
            "3. Copia la <b>URL del webhook</b>",
            "4. Pégala en la Bóveda de ClawFlow como 'Discord'",
        ],
    },
    "Custom": {
        "n8n_type":        "httpHeaderAuth",
        "node_types":      ["n8n-nodes-base.httpRequest"],
        "label":           "HTTP Header Auth (API Key genérica)",
        "is_auto_creatable": True,
        "data_format":     {"name": "Authorization", "value": "Bearer {token}"},
        "guidance": [
            "1. Obtén el API Key o token de tu servicio",
            "2. Pégalo en la Bóveda de ClawFlow como 'Custom'",
        ],
    },
}

# Reverse: n8n_type → catalog entry name
N8N_TYPE_TO_APP: dict[str, str] = {
    info["n8n_type"]: name for name, info in CREDENTIAL_CATALOG.items()
}

# node_type → required n8n credential type
NODE_TO_CRED_TYPE: dict[str, str] = {}
for _app, _info in CREDENTIAL_CATALOG.items():
    for _nt in _info.get("node_types", []):
        NODE_TO_CRED_TYPE[_nt] = _info["n8n_type"]


# ── Service Class ─────────────────────────────────────────────────────────────
class CredentialService:
    """
    Encapsulates all logic for matching, guiding, and syncing credentials
    between ClawFlow's vault and n8n.
    """

    # ── 1. Match stored creds to workflow needs ────────────────────────────
    def find_matches_for_analysis(
        self,
        db: Session,
        user_id: int,
        nodes_analysis: list[dict],
    ) -> tuple[list[dict], bool]:
        """
        Given the LLM's nodes analysis, find which stored credentials match.

        Returns:
            credential_assignments: list of assignment dicts (one per needed credential type)
            needs_interaction: True if the user must make choices
        """
        from app.models.database import CredencialAPI

        # Load user's active credentials
        stored = db.query(CredencialAPI).filter(
            CredencialAPI.id_usuario == user_id,
            CredencialAPI.activa == True,
        ).all()

       # Build index: n8n_type → list of stored creds
        cred_index: dict[str, list] = {}
        for cred in stored:
            # 1. Búsqueda estricta por metadatos (el método ideal)
            base_service = cred.metadata_json.get("app_service") if cred.metadata_json else cred.nombre_app
            info = CREDENTIAL_CATALOG.get(base_service)
            
            # 2. Búsqueda flexible (Fuzzy) si falla la estricta
            if not info:
                # Intentar adivinar basándose en el nombre de la app (útil para credenciales antiguas o importadas)
                name_lower = cred.nombre_app.lower()
                if "telegram" in name_lower: info = CREDENTIAL_CATALOG.get("Telegram")
                elif "github" in name_lower: info = CREDENTIAL_CATALOG.get("GitHub")
                elif "slack" in name_lower: info = CREDENTIAL_CATALOG.get("Slack")
                elif "discord" in name_lower: info = CREDENTIAL_CATALOG.get("Discord")
                elif "notion" in name_lower: info = CREDENTIAL_CATALOG.get("Notion")
                elif "airtable" in name_lower: info = CREDENTIAL_CATALOG.get("Airtable")
                elif "gmail" in name_lower: info = CREDENTIAL_CATALOG.get("Gmail_OAuth")
                elif "sheets" in name_lower: info = CREDENTIAL_CATALOG.get("Google_Sheets")
                elif "drive" in name_lower: info = CREDENTIAL_CATALOG.get("Google_Drive")

            if info:
                n8n_type = info["n8n_type"]
                cred_index.setdefault(n8n_type, []).append(cred)
            else:
                # Si de verdad no se pudo identificar, asignarlo a Custom (Header genérico)
                cred_index.setdefault("httpHeaderAuth", []).append(cred)
                
        assignments: list[dict] = []
        needs_interaction = False
        seen_cred_types: set[str] = set()

        for node in nodes_analysis:
            cred_type = node.get("credential_type")
            node_type  = node.get("node_type", "")
            if not cred_type or cred_type in seen_cred_types:
                continue
            seen_cred_types.add(cred_type)

            matches = cred_index.get(cred_type, [])
            catalog = CREDENTIAL_CATALOG.get(N8N_TYPE_TO_APP.get(cred_type, ""), {})

            if len(matches) == 1:
                status = "found"
                # Single match: auto-select, no interaction needed
            elif len(matches) > 1:
                status = "multiple"
                needs_interaction = True
            else:
                status = "not_found"
                needs_interaction = True

            assignments.append({
                "node_type":       node_type,
                "credential_type": cred_type,
                "credential_label": catalog.get("label", cred_type),
                "node_name":       node.get("node_name", node_type),
                "purpose":         node.get("purpose", ""),
                "status":          status,
                "matches": [
                    {
                        "id":         m.id_credencial,
                        "nombre_app": m.nombre_app,
                        "name":       m.nombre_app.replace("_", " "),
                        "tipo":       m.tipo,
                        "estado":     m.estado_conexion,
                    }
                    for m in matches
                ],
                "auto_selected": matches[0].id_credencial if len(matches) == 1 else None,
                "auto_name": matches[0].nombre_app.replace("_", " ") if len(matches) == 1 else None,
                "guidance":  catalog.get("guidance", []) if not matches else [],
                "is_auto_creatable": catalog.get("is_auto_creatable", False),
            })

        return assignments, needs_interaction

    # ── 2. Build credential context string for LLM prompt ─────────────────
    def build_credential_context(self, selected_credentials: list[dict]) -> str:
        """
        Builds the CREDENTIAL CONTEXT section injected into the LLM system prompt
        so it generates proper credential references in the workflow JSON.
        """
        if not selected_credentials:
            return ""

        lines = [
            "CREDENCIALES DISPONIBLES (obligatorio incluirlas en los nodos correspondientes):",
            "",
        ]
        for sel in selected_credentials:
            mode  = sel.get("mode", "skip")
            if mode == "skip":
                continue

            cred_type = sel.get("credential_type", "")
            cred_name = sel.get("credential_name", "")
            node_type = sel.get("node_type", "")
            placeholder_id = f"CF_SYNC_{sel.get('db_credential_id', 'NEW')}"

            lines.append(
                f"- Nodo tipo '{node_type}' → credencial '{cred_type}':"
                f" nombre=\"{cred_name}\", id_placeholder=\"{placeholder_id}\""
            )
            lines.append(
                f"  Incluir en el nodo: \"credentials\": {{\"{cred_type}\": "
                f"{{\"id\": \"{placeholder_id}\", \"name\": \"{cred_name}\"}}}}"
            )
            lines.append("")

        return "\n".join(lines)

    # ── 3. Sync credentials to n8n and resolve placeholder IDs ────────────
    async def sync_and_resolve(
        self,
        n8n_svc,
        db: Session,
        user_id: int,
        workflow_json: dict,
        selected_credentials: list[dict],
    ) -> dict:
        """
        Before deploying:
          1. For each selected credential with mode='use_stored': create/find in n8n
          2. Replace CF_SYNC_* placeholders with real n8n credential IDs
          3. Return the patched workflow_json
        """
        from app.services.encryption_service import EncryptionService
        from app.models.database import CredencialAPI

        enc        = EncryptionService()
        id_map: dict[str, str] = {}   # placeholder → real n8n ID

        # Build existing n8n credentials index
        try:
            # CORRECCIÓN 1: El método correcto es list_credentials
            n8n_creds = await n8n_svc.list_credentials()
            n8n_by_name = {c.get("name", ""): c for c in n8n_creds}
        except Exception:
            n8n_by_name = {}

        for sel in selected_credentials:
            mode         = sel.get("mode", "skip")
            if mode == "skip":
                continue

            db_cred_id   = sel.get("db_credential_id")
            cred_name    = sel.get("credential_name", "")
            cred_type    = sel.get("credential_type", "")
            placeholder  = f"CF_SYNC_{db_cred_id or 'NEW'}"
            manual_name  = sel.get("manual_name")

            if mode == "manual_name" and manual_name:
                existing = n8n_by_name.get(manual_name)
                if existing:
                    id_map[placeholder] = str(existing.get("id", manual_name))
                else:
                    id_map[placeholder] = manual_name  
                continue

            if mode == "use_stored" and db_cred_id:
                stored = db.query(CredencialAPI).filter(
                    CredencialAPI.id_credencial == db_cred_id
                ).first()
                if not stored:
                    continue

                existing = n8n_by_name.get(cred_name)
                if existing:
                    id_map[placeholder] = str(existing.get("id", cred_name))
                    continue

                # CORRECCIÓN 2: Leer el servicio base desde metadata (Soporte de Alias)
                base_app = stored.metadata_json.get("app_service") if stored.metadata_json else stored.nombre_app
                catalog = CREDENTIAL_CATALOG.get(base_app, {})
                
                if catalog.get("is_auto_creatable"):
                    try:
                        token = enc.decrypt(stored.token_cifrado)
                        data_fmt = catalog.get("data_format", {})
                        cred_data = {
                            k: v.replace("{token}", token) for k, v in data_fmt.items()
                        }
                        # CORRECCIÓN 3: Método create_credential y el parámetro type_name
                        created = await n8n_svc.create_credential(
                            name=cred_name, type_name=cred_type, data=cred_data
                        )
                        id_map[placeholder] = str(created.get("id", cred_name))
                    except Exception as exc:
                        print(f"[CredService] Error subiendo a n8n: {exc}")
                        id_map[placeholder] = cred_name  

        # Patch workflow JSON: replace all placeholders
        wf_str = json.dumps(workflow_json)
        for placeholder, real_id in id_map.items():
            wf_str = wf_str.replace(placeholder, real_id)
        return json.loads(wf_str)
    
    # ── 4. Get guidance for a specific credential type ─────────────────────
    @staticmethod
    def get_guidance(n8n_type: str) -> dict:
        app_name = N8N_TYPE_TO_APP.get(n8n_type, "Custom")
        catalog  = CREDENTIAL_CATALOG.get(app_name, CREDENTIAL_CATALOG["Custom"])
        return {
            "label":             catalog.get("label", n8n_type),
            "steps":             catalog.get("guidance", []),
            "is_auto_creatable": catalog.get("is_auto_creatable", False),
        }
