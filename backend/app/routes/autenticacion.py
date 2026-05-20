from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, EmailStr

router = APIRouter(prefix="/auth", tags=["Autenticación"])

class RegistroRequest(BaseModel):
    email: EmailStr
    password: str
    username: str

class LoginRequest(BaseModel):
    email: EmailStr
    password: str

@router.post("/registro")
async def registrar_usuario(data: RegistroRequest):
    """Registrar un nuevo usuario"""
    return {"message": "Registro procesado", "email": data.email, "username": data.username}

@router.post("/login")
async def iniciar_sesion(data: LoginRequest):
    """Iniciar sesión de usuario"""
    return {"message": "Inicio de sesión procesado", "email": data.email}

@router.post("/logout")
async def cerrar_sesion():
    """Cerrar sesión de usuario"""
    return {"message": "Sesión cerrada exitosamente"}

@router.get("/me")
async def obtener_usuario_actual():
    """Obtener información del usuario actual"""
    return {"message": "Información del usuario actual"}

