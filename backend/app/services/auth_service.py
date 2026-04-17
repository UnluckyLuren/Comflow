"""
ClawFlow — Auth Service (FastAPI side)
Validates PHP session tokens passed as cookies/headers.
Also provides JWT utilities for API-to-API calls.
"""
from __future__ import annotations
import os
from datetime import datetime, timedelta
from typing import Optional

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from passlib.context import CryptContext
from sqlalchemy.orm import Session

from app.models.database import get_db, Usuario

SECRET_KEY  = os.getenv("SECRET_KEY", "clawflow_super_secret_key_change_in_production")
ALGORITHM   = "HS256"
TOKEN_EXPIRE= 60 * 8  # 8 hours in minutes

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer      = HTTPBearer(auto_error=False)


class AuthService:
    """Handles password hashing and JWT token operations."""

    @staticmethod
    def hash_password(plain: str) -> str:
        return pwd_context.hash(plain)

    @staticmethod
    def verify_password(plain: str, hashed: str) -> bool:
        return pwd_context.verify(plain, hashed)

    @staticmethod
    def create_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
        to_encode = data.copy()
        expire = datetime.utcnow() + (expires_delta or timedelta(minutes=TOKEN_EXPIRE))
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    @staticmethod
    def decode_token(token: str) -> dict:
        try:
            return jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido o expirado",
            )


def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer),
    db: Session = Depends(get_db),
) -> Usuario:
    """
    Extract user from Bearer token or X-User-Id header
    (set by Nginx after PHP session validation).
    """
    token = None

    # 1. Try Bearer
    if credentials:
        token = credentials.credentials

    # 2. Try header set by PHP/Nginx
    user_id_header = request.headers.get("X-User-Id")
    if user_id_header and not token:
        user = db.query(Usuario).filter(
            Usuario.id_usuario == int(user_id_header),
            Usuario.activo == True,
        ).first()
        if user:
            return user

    # 3. Decode JWT
    if token:
        payload = AuthService.decode_token(token)
        uid = payload.get("sub")
        if uid:
            user = db.query(Usuario).filter(
                Usuario.id_usuario == int(uid),
                Usuario.activo == True,
            ).first()
            if user:
                return user

    # 4. Dev fallback: read user_id from cookie (PHP session bridge)
    session_uid = request.cookies.get("cf_uid")
    if session_uid:
        user = db.query(Usuario).filter(
            Usuario.id_usuario == int(session_uid),
            Usuario.activo == True,
        ).first()
        if user:
            return user

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="No autenticado")
