// Cliente de Supabase con la clave de servicio (solo uso en el servidor)
import { createClient } from '@supabase/supabase-js';

const supabaseUrl = process.env.NEXT_PUBLIC_SUPABASE_URL;
const serviceRoleKey = process.env.SUPABASE_SERVICE_ROLE_KEY;

if (!supabaseUrl) {
  console.warn('[supabaseAdmin] Falta NEXT_PUBLIC_SUPABASE_URL.');
}

if (!serviceRoleKey) {
  console.warn('[supabaseAdmin] Falta SUPABASE_SERVICE_ROLE_KEY. Asegúrate de definirla en el entorno del servidor.');
}

export const supabaseAdmin = createClient(supabaseUrl, serviceRoleKey, {
  auth: {
    autoRefreshToken: false,
    persistSession: false,
  },
});
