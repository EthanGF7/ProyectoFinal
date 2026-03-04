// Configuración de Supabase para el frontend
import { createClient } from '@supabase/supabase-js';

// Variables de entorno de Supabase
const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const supabaseAnonKey = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY;

// Verificar que las variables de entorno estén configuradas
if (!supabaseUrl || !supabaseAnonKey) {
  console.error('Faltan las variables de entorno de Supabase');
  console.error('Asegúrate de tener NEXT_PUBLIC_SUPABASE_URL y NEXT_PUBLIC_SUPABASE_ANON_KEY en tu .env.local');
}

// Cliente de Supabase para el frontend
export const supabase = createClient(supabaseUrl, supabaseAnonKey);

// Función para verificar la conexión
export const verificarConexion = async () => {
  try {
    const { data, error } = await supabase
      .from('genres')
      .select('*')
      .limit(1);
    
    if (error) throw error;
    
    return { success: true, message: 'Conexión exitosa con Supabase' };
  } catch (error) {
    return { success: false, message: `Error de conexión: ${error.message}` };
  }
};

// Funciones de autenticación
export const auth = {
  // Registrar usuario
  signUp: async (email, password, userData = {}) => {
    const { data, error } = await supabase.auth.signUp({
      email,
      password,
      options: {
        data: userData
      }
    });
    return { data, error };
  },

  // Iniciar sesión
  signIn: async (email, password) => {
    const { data, error } = await supabase.auth.signInWithPassword({
      email,
      password
    });
    return { data, error };
  },

  // Cerrar sesión
  signOut: async () => {
    const { error } = await supabase.auth.signOut();
    return { error };
  },

  // Obtener usuario actual
  getUser: async () => {
    const { data: { user } } = await supabase.auth.getUser();
    return user;
  }
};
