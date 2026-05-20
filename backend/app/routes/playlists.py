from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

router = APIRouter(prefix="/playlists", tags=["Playlists"])

class PlaylistRequest(BaseModel):
    titulo: str
    descripcion: str = None
    publico: bool = True

class PlaylistUpdateRequest(BaseModel):
    titulo: str = None
    descripcion: str = None
    publico: bool = None

@router.get("/")
async def obtener_playlists(skip: int = 0, limit: int = 10):
    """Obtener lista de playlists"""
    return {"playlists": [], "total": 0}

@router.get("/{playlist_id}")
async def obtener_playlist_por_id(playlist_id: str):
    """Obtener playlist específica"""
    return {"playlist": None, "error": "Playlist no encontrada"}

@router.post("/")
async def crear_playlist(data: PlaylistRequest):
    """Crear nueva playlist"""
    return {"message": "Playlist creada exitosamente", "playlist": data}

@router.put("/{playlist_id}")
async def actualizar_playlist(playlist_id: str, data: PlaylistUpdateRequest):
    """Actualizar playlist"""
    return {"message": "Playlist actualizada", "playlist": data}

@router.delete("/{playlist_id}")
async def eliminar_playlist(playlist_id: str):
    """Eliminar playlist"""
    return {"message": "Playlist eliminada exitosamente"}

@router.post("/{playlist_id}/canciones/{cancion_id}")
async def agregar_cancion_playlist(playlist_id: str, cancion_id: str):
    """Agregar canción a playlist"""
    return {"message": "Canción agregada a playlist"}

@router.delete("/{playlist_id}/canciones/{cancion_id}")
async def eliminar_cancion_playlist(playlist_id: str, cancion_id: str):
    """Eliminar canción de playlist"""
    return {"message": "Canción eliminada de playlist"}

