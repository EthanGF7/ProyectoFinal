from fastapi import UploadFile
import os

FORMATOS_AUDIO_PERMITIDOS = ["mp3", "wav", "flac", "m4a"]
TAMAÑO_MAXIMO_MB = 50
TAMAÑO_MAXIMO_BYTES = TAMAÑO_MAXIMO_MB * 1024 * 1024

def validar_formato_audio(filename: str) -> bool:
    """Validar que el archivo sea un formato de audio permitido"""
    ext = filename.rsplit(".", 1)[-1].lower()
    return ext in FORMATOS_AUDIO_PERMITIDOS

def validar_tamaño_archivo(tamaño_bytes: int) -> bool:
    """Validar que el archivo no exceda el tamaño máximo"""
    return tamaño_bytes <= TAMAÑO_MAXIMO_BYTES

async def subir_cancion(file: UploadFile) -> dict:
    """Subir canción a Supabase Storage"""
    if not validar_formato_audio(file.filename):
        return {"error": f"Formato no permitido. Use: {', '.join(FORMATOS_AUDIO_PERMITIDOS)}"}

    contenido = await file.read()
    if not validar_tamaño_archivo(len(contenido)):
        return {"error": f"Archivo demasiado grande. Máximo: {TAMAÑO_MAXIMO_MB}MB"}

    return {"message": "Canción subida exitosamente", "filename": file.filename}

async def subir_imagen(file: UploadFile) -> dict:
    """Subir imagen (portadas, avatares) a Supabase Storage"""
    formatos_permitidos = ["jpg", "jpeg", "png", "webp"]
    ext = file.filename.rsplit(".", 1)[-1].lower()

    if ext not in formatos_permitidos:
        return {"error": f"Formato no permitido. Use: {', '.join(formatos_permitidos)}"}

    contenido = await file.read()
    tamaño_maximo_imagen = 10 * 1024 * 1024

    if len(contenido) > tamaño_maximo_imagen:
        return {"error": "Imagen demasiado grande. Máximo: 10MB"}

    return {"message": "Imagen subida exitosamente", "filename": file.filename}

