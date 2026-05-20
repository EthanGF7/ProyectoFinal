from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from datetime import datetime

router = APIRouter(prefix="/eventos", tags=["Eventos"])

class EventoRequest(BaseModel):
    titulo: str
    descripcion: str
    fecha: str
    ubicacion: str
    estado: str = "activo"

@router.get("/")
async def obtener_eventos(skip: int = 0, limit: int = 10):
    """Obtener lista de eventos"""
    return {"eventos": [], "total": 0}

@router.get("/activo")
async def obtener_evento_activo():
    """Obtener evento actualmente activo"""
    return {"evento": None, "mensaje": "No hay evento activo"}

@router.get("/{evento_id}")
async def obtener_evento(evento_id: str):
    """Obtener evento específico"""
    return {"evento": None, "error": "Evento no encontrado"}

@router.post("/")
async def crear_evento(data: EventoRequest):
    """Crear nuevo evento"""
    return {"message": "Evento creado exitosamente", "evento": data}

@router.put("/{evento_id}/estado")
async def cambiar_estado_evento(evento_id: str, estado: str):
    """Cambiar estado del evento"""
    return {"message": f"Evento actualizado a {estado}"}

@router.delete("/{evento_id}")
async def eliminar_evento(evento_id: str):
    """Eliminar evento"""
    return {"message": "Evento eliminado exitosamente"}

