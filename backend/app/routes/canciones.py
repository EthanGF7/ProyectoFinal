from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/canciones", tags=["Canciones"])

class CancionRequest(BaseModel):
    titulo: str
    artista: str
    album: str = None
    genero: str = None
    duracion: int = None

@router.get("/")
async def obtener_canciones(skip: int = 0, limit: int = 10):
    """Obtener lista de canciones"""
    return {"canciones": [], "total": 0}

@router.get("/{cancion_id}")
async def obtener_cancion_por_id(cancion_id: str):
    """Obtener canción específica"""
    return {"cancion": None, "error": "Canción no encontrada"}

@router.post("/")
async def subir_cancion(data: CancionRequest):
    """Subir una nueva canción"""
    return {"message": "Canción subida exitosamente", "cancion": data}

@router.put("/{cancion_id}")
async def actualizar_cancion(cancion_id: str, data: CancionRequest):
    """Actualizar información de canción"""
    return {"message": "Canción actualizada", "cancion": data}

@router.delete("/{cancion_id}")
async def eliminar_cancion(cancion_id: str):
    """Eliminar una canción"""
    return {"message": "Canción eliminada exitosamente"}

