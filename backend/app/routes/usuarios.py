from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/usuarios", tags=["Usuarios"])

class PerfilRequest(BaseModel):
    username: str = None
    bio: str = None

@router.get("/perfil/{user_id}")
async def obtener_perfil(user_id: str):
    """Obtener perfil de usuario"""
    return {"perfil": None, "error": "Usuario no encontrado"}

@router.put("/perfil/{user_id}")
async def actualizar_perfil(user_id: str, data: PerfilRequest):
    """Actualizar perfil de usuario"""
    return {"message": "Perfil actualizado", "perfil": data}

@router.get("/djs")
async def obtener_djs(skip: int = 0, limit: int = 10):
    """Obtener lista de DJs"""
    return {"djs": [], "total": 0}

@router.get("/djs/{dj_id}")
async def obtener_dj_perfil(dj_id: str):
    """Obtener perfil de DJ específico"""
    return {"dj": None, "error": "DJ no encontrado"}

