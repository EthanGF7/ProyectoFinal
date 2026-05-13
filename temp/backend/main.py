# Archivo principal del servidor Python FastAPI
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
import os
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Crear aplicación FastAPI
app = FastAPI(
    title="Discoteca Online API",
    description="API para la aplicación de música Discoteca Online",
    version="1.0.0"
)

# Configurar CORS para permitir conexiones desde el frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],  # Frontend Next.js
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ruta de prueba
@app.get("/")
async def root():
    return {"message": "¡Bienvenido a Discoteca Online API!", "status": "funcionando"}

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "Discoteca Online Backend"}

def main():
    # Obtener puerto desde variables de entorno o usar 5000 por defecto
    port = int(os.getenv("PORT", 5000))
    
    print(f"🎵 Iniciando Discoteca Online API en puerto {port}")
    print(f"📡 Frontend conectado desde: http://localhost:3000")
    print(f"🔗 API disponible en: http://localhost:{port}")
    
    # Iniciar servidor
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=port,
        reload=True,  # Recarga automática en desarrollo
        log_level="info"
    )

if __name__ == "__main__":
    main()
