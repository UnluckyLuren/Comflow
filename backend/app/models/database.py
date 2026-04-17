"""
ClawFlow — SQLAlchemy ORM Models
All domain entities as Python classes.
"""
from __future__ import annotations
import os
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, Column, DateTime, Enum, ForeignKey,
    Integer, JSON, String, Text, create_engine,
)
from sqlalchemy.orm import DeclarativeBase, relationship, sessionmaker

DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "mysql+pymysql://clawflow:clawflow_pass@mysql:3306/clawflow"
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True, pool_recycle=3600)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    pass


# ── Dependency ────────────────────────────────────────────────
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ── ORM Models ────────────────────────────────────────────────
class Usuario(Base):
    __tablename__ = "usuarios"

    id_usuario        = Column(Integer, primary_key=True, index=True)
    correo            = Column(String(255), unique=True, nullable=False, index=True)
    nombre            = Column(String(100), nullable=False)
    hash_contrasena   = Column(String(255), nullable=False)
    acceso_admin      = Column(Boolean, default=False)
    activo            = Column(Boolean, default=True)
    intentos_fallidos = Column(Integer, default=0)
    bloqueado_hasta   = Column(DateTime, nullable=True)
    ultimo_acceso     = Column(DateTime, nullable=True)
    created_at        = Column(DateTime, default=datetime.utcnow)
    updated_at        = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    instancias  = relationship("InstanciaN8N",   back_populates="usuario", cascade="all, delete")
    comandos    = relationship("ComandoVoz",      back_populates="usuario", cascade="all, delete")
    credenciales= relationship("CredencialAPI",  back_populates="usuario", cascade="all, delete")
    flujos      = relationship("FlujoTrabajo",   back_populates="usuario")


class InstanciaN8N(Base):
    __tablename__ = "instancias_n8n"

    id_instancia    = Column(Integer, primary_key=True, index=True)
    id_usuario      = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    nombre          = Column(String(100), default="Local n8n")
    host_url        = Column(String(500), nullable=False)
    api_key_cifrada = Column(Text, nullable=False)
    activa          = Column(Boolean, default=True)
    ultima_sync     = Column(DateTime, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)

    usuario = relationship("Usuario", back_populates="instancias")
    flujos  = relationship("FlujoTrabajo", back_populates="instancia")


class FlujoTrabajo(Base):
    __tablename__ = "flujos_trabajo"

    id              = Column(Integer, primary_key=True, index=True)
    id_flujo_n8n    = Column(String(100), nullable=False, index=True)
    id_instancia    = Column(Integer, ForeignKey("instancias_n8n.id_instancia"), nullable=False)
    id_usuario      = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    nombre          = Column(String(255), nullable=False)
    activo          = Column(Boolean, default=False)
    estructura_json = Column(Text, nullable=True)
    nodos_resumen   = Column(JSON, nullable=True)
    origen_comando  = Column(Text, nullable=True)
    created_at      = Column(DateTime, default=datetime.utcnow)
    updated_at      = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    usuario  = relationship("Usuario",     back_populates="flujos")
    instancia= relationship("InstanciaN8N",back_populates="flujos")


class ComandoVoz(Base):
    __tablename__ = "comandos_voz"

    id                  = Column(Integer, primary_key=True, index=True)
    id_usuario          = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    url_audio           = Column(String(500), nullable=True)
    texto_transcrito    = Column(Text, nullable=True)
    json_generado       = Column(Text, nullable=True)
    id_flujo_desplegado = Column(Integer, ForeignKey("flujos_trabajo.id"), nullable=True)
    estado              = Column(Enum("procesando","exito","error","cancelado"), default="procesando")
    error_detalle       = Column(Text, nullable=True)
    created_at          = Column(DateTime, default=datetime.utcnow)

    usuario = relationship("Usuario", back_populates="comandos")


class CredencialAPI(Base):
    __tablename__ = "credenciales_api"

    id_credencial     = Column(Integer, primary_key=True, index=True)
    id_usuario        = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=False)
    nombre_app        = Column(String(100), nullable=False)
    tipo              = Column(Enum("oauth2","api_key","basic","token"), default="api_key")
    token_cifrado     = Column(Text, nullable=False)
    metadata_json     = Column(JSON, nullable=True)
    activa            = Column(Boolean, default=True)
    ultima_validacion = Column(DateTime, nullable=True)
    estado_conexion   = Column(Enum("valida","invalida","sin_probar"), default="sin_probar")
    created_at        = Column(DateTime, default=datetime.utcnow)
    updated_at        = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    usuario = relationship("Usuario", back_populates="credenciales")


class LogSistema(Base):
    __tablename__ = "logs_sistema"

    id         = Column(Integer, primary_key=True, index=True)
    id_usuario = Column(Integer, ForeignKey("usuarios.id_usuario"), nullable=True)
    nivel      = Column(Enum("info","warning","error","critical"), default="info")
    modulo     = Column(String(100), nullable=True)
    mensaje    = Column(Text, nullable=False)
    detalle    = Column(JSON, nullable=True)
    ip_origen  = Column(String(45), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
