# 🦀 ClawFlow — Voice-Driven Automation OS
**Sistema de Automatización por Voz · v1.0**

> Dicta un comando. ClawFlow lo transcribe, lo convierte en un flujo n8n, y lo despliega — sin tocar el teclado.

---

## 🏗️ Arquitectura

```
Browser ──HTTPS──► Cloudflare Tunnel ──► Nginx (80/443)
                                              │
                          ┌───────────────────┼─────────────────┐
                          ▼                   ▼                  ▼
                    PHP Frontend         FastAPI           MySQL :3306
                    (HTML/CSS/JS)        (Python)          (clawflow db)
                          │                   │
                          └───────────────────┼──► n8n :5678
                                              │
                                    Whisper STT + Llama3 LLM
```

**Stack completo:**
| Capa | Tecnología |
|------|-----------|
| Frontend | HTML5 · CSS3 · JavaScript (Vanilla OOP) · PHP 8.2 |
| Backend  | Python 3.11 · FastAPI · SQLAlchemy 2 |
| Base de datos | MySQL 8.0 |
| Orquestación | Docker Compose · Nginx |
| IA/LLM | OpenAI Whisper (STT) · Llama3:8b via Ollama (o OpenAI) |
| Automatización | n8n (API REST) |
| Seguridad | bcrypt · AES-256 (Fernet) · JWT · Cloudflare Tunnel |

---

## 🚀 Inicio Rápido

### 1. Requisitos previos
```bash
# Docker + Docker Compose
docker --version          # >= 24.0
docker compose version    # >= 2.20

# Ollama (opcional, para LLM local)
curl -fsSL https://ollama.ai/install.sh | sh
ollama pull llama3:8b
```

### 2. Variables de entorno
```bash
cp .env.example .env
# Edita .env con tus valores
```

**.env.example:**
```env
N8N_API_KEY=your_n8n_api_key_here
OPENAI_API_KEY=               # Opcional, si no usas Ollama
LLM_MODEL=llama3:8b           # o gpt-4o-mini
OLLAMA_URL=http://host.docker.internal:11434
```

### 3. Levantar los servicios
```bash
docker compose up -d --build
```

### 4. Acceder al sistema
- **ClawFlow UI:** http://localhost
- **FastAPI Docs:** http://localhost/api/docs
- **n8n UI:** http://localhost/n8n/

### 5. Login inicial
```
Email:    admin@clawflow.local
Password: Admin@ClawFlow2026
```

---

## 📁 Estructura del Proyecto

```
clawflow/
├── docker-compose.yml
├── .env
├── nginx/
│   ├── Dockerfile
│   └── nginx.conf
├── frontend/                   # PHP + HTML/CSS/JS
│   ├── Dockerfile
│   ├── index.php               # Login / Register
│   ├── dashboard.php           # UC05: Dashboard
│   ├── workflows.php           # UC03/04/06: Flujos
│   ├── infrastructure.php      # UC07: Infraestructura
│   ├── credentials.php         # UC08: Bóveda
│   ├── logs.php                # RF-07: Logs
│   ├── includes/
│   │   ├── Database.php        # Singleton PDO
│   │   ├── AuthService.php     # UC01: Autenticación
│   │   ├── header.php          # Layout: sidebar + topbar
│   │   └── footer.php          # Layout: modales + scripts
│   ├── assets/
│   │   ├── css/style.css       # Design system completo
│   │   └── js/
│   │       ├── utils.js        # Toast, apiFetch, helpers
│   │       ├── voice.js        # VoiceController (OOP)
│   │       ├── dashboard.js    # DashboardController (OOP)
│   │       └── main.js         # App init + todos los controllers
│   └── api/auth/logout.php
├── backend/                    # FastAPI (Python)
│   ├── Dockerfile
│   ├── requirements.txt
│   └── app/
│       ├── main.py             # FastAPI app + routers
│       ├── models/
│       │   └── database.py     # SQLAlchemy ORM models
│       ├── services/
│       │   ├── auth_service.py      # JWT + bcrypt
│       │   ├── llm_service.py       # Whisper STT + LLM
│       │   ├── n8n_service.py       # n8n REST API client
│       │   └── encryption_service.py# AES-256 Fernet
│       └── routers/
│           ├── voice.py         # UC02, UC03
│           ├── workflows.py     # UC04, UC06
│           ├── dashboard.py     # UC05
│           ├── infrastructure.py# UC07
│           ├── credentials.py   # UC08
│           └── logs.py          # RF-07
└── mysql/
    └── init.sql                # Schema + seed data
```

---

## 🎤 Flujo de Uso

```
1. Login → Dashboard
2. Clic en botón 🎤 (flotante) o FAB
3. Dicta: "Crea un flujo que lea correos de Gmail con adjuntos y los guarde en Drive"
4. Whisper transcribe el audio en < 2s
5. Llama3 genera el JSON n8n en < 3s  [total < 5s — RNF-R1]
6. Vista previa muestra los nodos que se crearán
7. Click "Confirmar Despliegue"
8. FastAPI hace POST /workflows + PUT /activate a n8n
9. El flujo aparece activo en el Dashboard
```

---

## 🔒 Seguridad

| Aspecto | Implementación |
|---------|---------------|
| Contraseñas | bcrypt cost=12 |
| API Keys | AES-256 (Fernet) |
| Sesiones | PHP session + JWT |
| Brute force | Bloqueo 3 min tras 3 intentos |
| HTTPS | Cloudflare Tunnel |
| Backend | No expuesto a internet (solo Nginx) |
| Auditoría | Logs en MySQL para cada evento |

---

## 🐳 Comandos Docker

```bash
# Ver logs en tiempo real
docker compose logs -f backend

# Reiniciar solo el backend
docker compose restart backend

# Acceder a MySQL
docker compose exec mysql mysql -u clawflow -pclawflow_pass clawflow

# Rebuild completo
docker compose down && docker compose up -d --build
```

---

## 🧠 Configuración del LLM

### Opción A: Ollama (local, privado)
```bash
ollama pull llama3:8b   # ~4.7 GB
# El backend lo detecta automáticamente vía OLLAMA_URL
```

### Opción B: OpenAI (nube)
```env
OPENAI_API_KEY=sk-...
LLM_MODEL=gpt-4o-mini
```
Configurable también desde la UI en `Infraestructura → Configuración LLM`.

---

*Autor: Luis V. — ClawFlow v1.0 — 14/04/2026*
