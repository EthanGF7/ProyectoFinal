import { supabaseAdmin } from '../../../utils/supabaseAdmin';
import { getAuthenticatedUser, ensureDj } from '../../../utils/apiAuth';

const DJ_SELECT = 'id, nombre_artistico, bio, estilo_visual, estilo_musical';

export default async function handler(req, res) {
  const { user, appUser, error } = await getAuthenticatedUser(req);

  if (error) {
    return res.status(401).json({ error });
  }

  if (!ensureDj(appUser)) {
    return res.status(403).json({ error: 'Solo los DJs pueden acceder a este recurso' });
  }

  if (req.method === 'GET') {
    try {
      const { data, error: fetchError } = await supabaseAdmin
        .from('djs')
        .select(DJ_SELECT)
        .eq('id', user.id)
        .maybeSingle();

      if (fetchError) {
        if (fetchError.code === '42P01') {
          console.warn('[dj/profile] Tabla djs no existe todavía.');
          return res.status(200).json({ profile: null });
        }
        console.error('[dj/profile] Error obteniendo perfil DJ:', fetchError);
        return res.status(500).json({ error: 'No se pudo cargar el perfil de DJ' });
      }

      return res.status(200).json({ profile: data || null });
    } catch (err) {
      console.error('[dj/profile] Error inesperado:', err);
      return res.status(500).json({ error: 'Error interno del servidor' });
    }
  }

  if (req.method === 'PATCH') {
    const body = typeof req.body === 'object' ? req.body : {};
    const { nombre_artistico, bio, estilo_visual, estilo_musical } = body;

    if (!nombre_artistico) {
      return res.status(400).json({ error: 'El nombre artístico es obligatorio' });
    }

    try {
      const payload = {
        id: user.id,
        nombre_artistico,
        bio: bio ?? null,
        estilo_visual: estilo_visual ?? null,
        estilo_musical: estilo_musical ?? null,
      };

      const { error: upsertError } = await supabaseAdmin
        .from('djs')
        .upsert(payload, { onConflict: 'id' });

      if (upsertError) {
        if (upsertError.code === '42P01') {
          return res.status(400).json({
            error: 'La tabla djs no existe. Crea la tabla en Supabase antes de guardar el perfil.',
          });
        }
        if (upsertError.code === '42703') {
          console.warn('[dj/profile] Columnas opcionales ausentes, guardando perfil parcial.');
        } else {
          console.error('[dj/profile] Error actualizando perfil DJ:', upsertError);
          return res.status(500).json({ error: 'No se pudo actualizar el perfil' });
        }
      }

      let profileData = null;

      const { data, error: selectError } = await supabaseAdmin
        .from('djs')
        .select(DJ_SELECT)
        .eq('id', user.id)
        .maybeSingle();

      if (selectError) {
        if (selectError.code === '42703') {
          const { data: fallbackData, error: fallbackError } = await supabaseAdmin
            .from('djs')
            .select('id, nombre_artistico, bio')
            .eq('id', user.id)
            .maybeSingle();

          if (!fallbackError) {
            profileData = fallbackData;
          } else {
            console.error('[dj/profile] Perfil guardado pero no recuperado:', fallbackError);
            return res.status(500).json({ error: 'El perfil se guardó pero no se pudo recuperar.' });
          }
        } else {
          console.error('[dj/profile] Perfil guardado pero no recuperado:', selectError);
          return res.status(500).json({ error: 'El perfil se guardó pero no se pudo recuperar.' });
        }
      } else {
        profileData = data;
      }

      return res.status(200).json({ profile: profileData });
    } catch (err) {
      console.error('[dj/profile] Error inesperado PATCH:', err);
      return res.status(500).json({ error: 'Error interno del servidor' });
    }
  }

  return res.status(405).json({ error: 'Método no permitido' });
}
