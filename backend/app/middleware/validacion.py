from fastapi import HTTPException, status
import re

def validar_email(email: str) -> bool:
    """Validar formato de email"""
    patron = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(patron, email) is not None

def validar_registro(email: str, password: str, username: str) -> dict:
    """Validar datos de registro"""
    if not validar_email(email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email inválido"
        )
    if len(password) < 6:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña debe tener al menos 6 caracteres"
        )
    if len(username) < 3:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El username debe tener al menos 3 caracteres"
        )
    return {"valid": True}

def validar_login(email: str, password: str) -> dict:
    """Validar datos de login"""
    if not validar_email(email):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email inválido"
        )
    if not password:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La contraseña es requerida"
        )
    return {"valid": True}

def validar_playlist(titulo: str) -> dict:
    """Validar datos de playlist"""
    if not titulo or len(titulo.strip()) < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El título de la playlist es requerido"
        )
    return {"valid": True}

def validar_cancion(titulo: str, artista: str) -> dict:
    """Validar datos de canción"""
    if not titulo or len(titulo.strip()) < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El título de la canción es requerido"
        )
    if not artista or len(artista.strip()) < 1:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="El artista es requerido"
        )
    return {"valid": True}

