import { supabaseAdmin } from '../../../utils/supabaseAdmin';
import { getAuthenticatedUser } from '../../../utils/apiAuth';

export default async function handler(req, res) {
  if (req.method !== 'GET') {
    res.setHeader('Allow', 'GET');
    return res.status(405).json({ error: 'Método no permitido' });
  }

  const { user, appUser, error } = await getAuthenticatedUser(req);
  if (error) return res.status(401).json({ error });

  const userId = appUser?.id || user?.id;
  if (!userId) return res.status(400).json({ error: 'Usuario no identificado' });

  const { data, error: fetchError } = await supabaseAdmin
    .from('dj_requests')
    .select('*')
    .eq('user_id', userId)
    .order('created_at', { ascending: false })
    .limit(1)
    .maybeSingle();

  if (fetchError) {
    console.error('[my-request] Error:', fetchError);
    return res.status(500).json({ error: fetchError.message });
  }

  return res.status(200).json({ request: data || null });
}
