from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/generos", tags=["Géneros"])

class GeneroRequest(BaseModel):
    nombre: str
    descripcion: str = None
    icono: str = None

@router.get("/")
async def obtener_generos():
    """Obtener lista de géneros musicales"""
    return {
        "generos": [
            {"id": 1, "nombre": "House", "icono": "🎵"},
            {"id": 2, "nombre": "Techno", "icono": "🔊"},
            {"id": 3, "nombre": "Drum & Bass", "icono": "🥁"},
        ],
        "total": 3
    }

@router.get("/{genero_id}")
async def obtener_genero_por_id(genero_id: str):
    """Obtener género específico"""
    return {"genero": None, "error": "Género no encontrado"}

@router.post("/")
async def crear_genero(data: GeneroRequest):
    """Crear nuevo género"""
    return {"message": "Género creado exitosamente", "genero": data}

@router.put("/{genero_id}")
async def actualizar_genero(genero_id: str, data: GeneroRequest):
    """Actualizar género"""
    return {"message": "Género actualizado", "genero": data}

@router.delete("/{genero_id}")
async def eliminar_genero(genero_id: str):
    """Eliminar género"""
    return {"message": "Género eliminado exitosamente"}

