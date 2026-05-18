from fastapi import HTTPException, status
from app.config.supabase import supabase_auth

def verificar_autenticacion(token: str) -> dict:
    """Verificar si el usuario está autenticado con un token válido"""
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token requerido"
        )
    return {"token": token}

def verificar_admin(user_data: dict) -> bool:
    """Verificar si el usuario tiene rol de administrador"""
    return user_data.get("tipo_usuario") == "admin"

def verificar_dj(user_data: dict) -> bool:
    """Verificar si el usuario es DJ o administrador"""
    tipo = user_data.get("tipo_usuario")
    return tipo in ["dj", "admin"]

