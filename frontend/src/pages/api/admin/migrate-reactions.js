import { supabaseAdmin } from '../../../utils/supabaseAdmin';

const MIGRATION_TOKEN = process.env.MIGRATION_TOKEN || 'nexus-migrate-2025';

export default async function handler(req, res) {
  if (req.method !== 'POST') {
    return res.status(405).json({ error: 'Método no permitido (usa POST)' });
  }

  const token = req.headers['x-migration-token'] || req.query.token;
  if (token !== MIGRATION_TOKEN) {
    return res.status(401).json({ error: 'Token de migración inválido' });
  }

  try {
    // 1) Comprobar si ya existe
    const { error: probeError } = await supabaseAdmin
      .from('track_reactions')
      .select('id')
      .limit(1);

    if (!probeError) {
      return res.status(200).json({
        ok: true,
        alreadyExists: true,
        message: 'La tabla track_reactions ya existe. Nada que hacer.',
      });
    }

    // 2) Si el error NO es "tabla no existe" (42P01), abortar
    if (probeError.code && probeError.code !== '42P01') {
      console.error('[migrate-reactions] Error al sondear tabla:', probeError);
      return res.status(500).json({
        error: 'No se pudo comprobar el estado de la tabla',
        details: probeError.message,
        code: probeError.code,
      });
    }

    // 3) Crear tabla vía RPC `exec_sql` si está disponible
    const sql = `
      create table if not exists track_reactions (
        id uuid primary key default gen_random_uuid(),
        user_id uuid not null references app_users(id) on delete cascade,
        dj_id text not null,
        track_name text not null,
        reaction smallint not null check (reaction in (-1, 1)),
        created_at timestamptz not null default now(),
        updated_at timestamptz not null default now(),
        unique (user_id, dj_id, track_name)
      );
      create index if not exists track_reactions_user_idx
        on track_reactions(user_id);
      create index if not exists track_reactions_dj_track_idx
        on track_reactions(dj_id, track_name);
    `;

    const { error: rpcError } = await supabaseAdmin.rpc('exec_sql', { sql });

    if (rpcError) {
      // El RPC no existe por defecto. Devolvemos instrucciones claras.
      return res.status(501).json({
        error:
          'No se puede crear la tabla automáticamente porque tu Supabase no expone una función SQL para ejecutar DDL.',
        reason: rpcError.message,
        howToFix:
          'Opción A (recomendada): pega este SQL en Supabase → SQL Editor y dale a Run. Opción B: crea la función exec_sql descrita abajo y vuelve a llamar a este endpoint.',
        sqlToRun: sql.trim(),
        optionalRpcSetup: `
create or replace function exec_sql(sql text)
returns void
language plpgsql
security definer
as $$
begin
  execute sql;
end;
$$;
        `.trim(),
      });
    }

    // 4) Verificar que ahora sí existe
    const { error: verifyError } = await supabaseAdmin
      .from('track_reactions')
      .select('id')
      .limit(1);

    if (verifyError) {
      return res.status(500).json({
        error: 'La migración pareció ejecutarse pero la tabla sigue sin estar accesible.',
        details: verifyError.message,
      });
    }

    return res.status(200).json({
      ok: true,
      created: true,
      message: 'Tabla track_reactions creada correctamente.',
    });
  } catch (err) {
    console.error('[migrate-reactions] Error inesperado:', err);
    return res.status(500).json({
      error: 'Error interno del servidor',
      details: err.message,
    });
  }
}
