"""
ClawFlow — FastAPI Backend
Entry point: registers all routers and middleware.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers import voice, workflows, dashboard, infrastructure, credentials, logs
from app.models.database import Base, engine

# Create tables on startup
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="ClawFlow API",
    description="Voice-driven n8n automation backend",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
)

# ── CORS (Nginx handles external, this covers internal dev) ────
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost", "http://frontend", "http://nginx"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Routers ────────────────────────────────────────────────────
app.include_router(voice.router,          prefix="/api/voice",          tags=["Voice"])
app.include_router(workflows.router,      prefix="/api/workflows",      tags=["Workflows"])
app.include_router(dashboard.router,      prefix="/api/dashboard",      tags=["Dashboard"])
app.include_router(infrastructure.router, prefix="/api/infrastructure",  tags=["Infrastructure"])
app.include_router(credentials.router,    prefix="/api/credentials",    tags=["Credentials"])
app.include_router(logs.router,           prefix="/api/logs",           tags=["Logs"])


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "ClawFlow API v1.0"}
