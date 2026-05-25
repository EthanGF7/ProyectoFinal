import { supabaseAdmin } from '../../../../utils/supabaseAdmin';
import { getAuthenticatedUser } from '../../../../utils/apiAuth';

const TABLE_NAME = 'rhythm_game_scores';
const SCORE_SELECT = 'id, user_id, username, score, max_combo, song_title, difficulty, created_at';

async function fetchTopScores(res) {
  const { data, error } = await supabaseAdmin
    .from(TABLE_NAME)
    .select(SCORE_SELECT)
    .order('score', { ascending: false })
    .order('max_combo', { ascending: false })
    .limit(3);

  if (error) {
    if (error.code === '42P01') {
      return res.status(200).json({
        ranking: [],
        setupRequired: true,
        setupSql:
          'create table rhythm_game_scores (id uuid primary key default gen_random_uuid(), user_id uuid references app_users(id), username text not null, score integer not null, max_combo integer not null default 0, song_title text, difficulty text, created_at timestamptz not null default now());',
      });
    }
    console.error('[eventos/ritmo/ranking] Error obteniendo ranking:', error);
    return res.status(500).json({ error: 'No se pudo cargar el ranking' });
  }

  return res.status(200).json({ ranking: data || [] });
}

export default async function handler(req, res) {
  if (req.method === 'GET') {
    return fetchTopScores(res);
  }

  if (req.method === 'POST') {
    const { user, appUser, error: authError } = await getAuthenticatedUser(req);
    if (authError) {
      return res.status(401).json({ error: 'Inicia sesión para guardar tu puntuación' });
    }

    const body = typeof req.body === 'object' ? req.body : {};
    const score = Number(body.score || 0);
    const maxCombo = Number(body.maxCombo || 0);
    const songTitle = body.songTitle || null;
    const difficulty = body.difficulty || null;

    if (!Number.isFinite(score) || score <= 0) {
      return res.status(400).json({ error: 'Puntuación no válida' });
    }

    const username = appUser?.username || user.email || 'Jugador';

    const { error: insertError } = await supabaseAdmin.from(TABLE_NAME).insert({
      user_id: user.id,
      username,
      score: Math.round(score),
      max_combo: Math.round(maxCombo),
      song_title: songTitle,
      difficulty,
    });

    if (insertError) {
      if (insertError.code === '42P01') {
        return res.status(400).json({ error: 'Falta crear la tabla rhythm_game_scores en Supabase' });
      }
      console.error('[eventos/ritmo/ranking] Error guardando score:', insertError);
      return res.status(500).json({ error: 'No se pudo guardar la puntuación' });
    }

    return fetchTopScores(res);
  }

  return res.status(405).json({ error: 'Método no permitido' });
}
