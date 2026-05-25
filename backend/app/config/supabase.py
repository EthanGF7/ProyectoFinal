# Configuración del cliente de Supabase para Python
import os
from supabase import create_client, Client
from dotenv import load_dotenv

# Cargar variables de entorno
load_dotenv()

# Variables de entorno de Supabase
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_ANON_KEY = os.getenv("SUPABASE_ANON_KEY")
SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")

# Cliente de Supabase para el backend (con permisos completos)
def crear_cliente_supabase():
    """
    Crear cliente de Supabase con service role key para operaciones del backend
    """
    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise ValueError("Faltan las variables de entorno de Supabase")
    
    return create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)

# Cliente de Supabase para autenticación (con clave pública)
def crear_cliente_auth():
    """
    Crear cliente de Supabase con anon key para autenticación
    """
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        raise ValueError("Faltan las variables de entorno de Supabase")
    
    return create_client(SUPABASE_URL, SUPABASE_ANON_KEY)

def verificar_conexion():
    """
    Verificar que la conexión con Supabase funciona correctamente
    """
    try:
        supabase = crear_cliente_supabase()
        # Crear cliente y realizar una operación mínima para verificar conexión
        supabase.storage.list_buckets()
        return True, "Conexión exitosa con Supabase"
    except Exception as e:
        return False, f"Error de conexión: {str(e)}"

# Instancias globales
supabase = crear_cliente_supabase()
supabase_auth = crear_cliente_auth()
