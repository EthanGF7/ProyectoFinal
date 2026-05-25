-- Migration: create_user_listen_history
-- Description: Tabla para almacenar el historial de escuchas de DJs por usuario.
-- Ejecutar en el proyecto de Supabase (SQL Editor o CLI).

create table if not exists public.user_listen_history (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid not null references public.app_users(id) on delete cascade,
  dj_id text,
  dj_name text,
  playlist_id text,
  playlist_name text,
  track_name text,
  listened_at timestamptz not null default timezone('utc', now())
);

create index if not exists user_listen_history_user_id_idx
  on public.user_listen_history (user_id, listened_at desc);

create index if not exists user_listen_history_user_dj_idx
  on public.user_listen_history (user_id, dj_id, listened_at desc);

comment on table public.user_listen_history is 'Registro de las últimas reproducciones de DJs por usuario.';
comment on column public.user_listen_history.user_id is 'Usuario autenticado que escuchó la pista.';
comment on column public.user_listen_history.dj_id is 'Identificador del DJ que originó la reproducción.';
comment on column public.user_listen_history.dj_name is 'Nombre del DJ si estaba disponible en el momento de la reproducción.';
comment on column public.user_listen_history.playlist_id is 'Playlist desde la que se reprodujo la pista (si aplica).';
comment on column public.user_listen_history.playlist_name is 'Nombre descriptivo de la playlist reproducida.';
comment on column public.user_listen_history.track_name is 'Nombre o título de la pista reproducida.';
comment on column public.user_listen_history.listened_at is 'Marca temporal de la reproducción en UTC.';
