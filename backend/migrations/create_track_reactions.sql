-- Migration: create_track_reactions
-- Description: Tabla para almacenar likes/dislikes de pistas por usuario y DJ, incluyendo nombre del DJ.
-- Ejecutar en el proyecto de Supabase (SQL Editor o CLI).

create table if not exists public.track_reactions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.app_users(id) on delete cascade,
  dj_id text not null,
  dj_name text,
  track_name text not null,
  reaction smallint not null check (reaction in (-1, 1)),
  created_at timestamptz not null default timezone('utc', now()),
  updated_at timestamptz not null default timezone('utc', now()),
  unique (user_id, dj_id, track_name)
);

create index if not exists track_reactions_user_idx
  on public.track_reactions (user_id);

create index if not exists track_reactions_dj_track_idx
  on public.track_reactions (dj_id, track_name);

comment on table public.track_reactions is 'Preferencias de usuario (likes/dislikes) sobre pistas reproducidas por DJs.';
comment on column public.track_reactions.dj_name is 'Nombre del DJ asociado cuando se registró la reacción.';
comment on column public.track_reactions.reaction is '1 para like, -1 para dislike.';
comment on column public.track_reactions.updated_at is 'Última vez que el usuario modificó la reacción.';
