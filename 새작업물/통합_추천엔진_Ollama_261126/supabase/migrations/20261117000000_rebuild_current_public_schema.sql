-- Reproducible snapshot of the current RecomEngine public schema (Postgres 17).
-- This is deliberately additive/idempotent: it preserves existing rows and never drops tables.

create table if not exists public.taste_traits (
  trait_id uuid primary key default gen_random_uuid(),
  trait_name text not null unique,
  description text
);

create table if not exists public.diagnosis_sessions (
  id uuid primary key default gen_random_uuid(),
  track text not null check (track in ('gamer','nongamer')),
  status text not null default 'in_progress' check (status in ('in_progress','completed','abandoned')),
  user_id uuid references auth.users(id) on delete set null,
  started_at timestamptz not null default now(),
  completed_at timestamptz,
  created_at timestamptz not null default now()
);

create table if not exists public.survey_questions (
  id text primary key,
  track text not null check (track in ('gamer','nongamer')),
  stage text not null check (stage in ('onboarding','profile','deep')),
  question_no integer not null,
  category text,
  select_type text not null check (select_type in ('SINGLE','MULTI_MAX_2','MULTI_MAX_4','MULTI_MAX_5','MULTI_UNLIMITED')),
  question_text text not null,
  options jsonb not null,
  created_at timestamptz not null default now(),
  unique (track,stage,question_no)
);

create table if not exists public.users (
  id uuid primary key references auth.users(id) on delete cascade,
  email text unique,
  nickname text
);

create table if not exists public.games (
  id uuid primary key default gen_random_uuid(),
  rawg_id bigint unique,
  igdb_id bigint unique,
  steam_app_id bigint unique,
  title text not null,
  description text,
  release_date date,
  genres text[] not null default array[]::text[],
  tags text[] not null default array[]::text[],
  platforms text[] not null default array[]::text[],
  cover_url text,
  playtime_hours numeric,
  price_info jsonb not null default '{}'::jsonb,
  source_data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.analysis_reports (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null unique references public.diagnosis_sessions(id) on delete cascade,
  profile_name text,
  keywords text[] not null default array[]::text[],
  summary jsonb not null default '{}'::jsonb,
  detail jsonb not null default '{}'::jsonb,
  anti_match jsonb not null default '{}'::jsonb,
  play_tip jsonb not null default '{}'::jsonb,
  generated_by text not null default 'ollama',
  model_name text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  is_representative boolean not null default false
);

create table if not exists public.analysis_scores (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null unique references public.diagnosis_sessions(id) on delete cascade,
  physical numeric not null default 0,
  strategy numeric not null default 0,
  exploration numeric not null default 0,
  emotion numeric not null default 0,
  comfort numeric not null default 0,
  competition numeric not null default 0,
  platform_fit jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table if not exists public.diagnosis_answers (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.diagnosis_sessions(id) on delete cascade,
  question_id text not null,
  answer jsonb not null,
  answered_at timestamptz not null default now(),
  unique (session_id,question_id)
);

create table if not exists public.survey_options (
  option_id uuid primary key default gen_random_uuid(),
  question_id text not null references public.survey_questions(id) on delete cascade,
  option_text text not null,
  option_order integer not null,
  unique (question_id,option_order)
);

create table if not exists public.option_trait_scores (
  option_id uuid not null references public.survey_options(option_id) on delete cascade,
  trait_id uuid not null references public.taste_traits(trait_id) on delete cascade,
  base_weight numeric not null default 0,
  primary key (option_id,trait_id)
);

create table if not exists public.game_trait_tag_rules (
  id uuid primary key default gen_random_uuid(),
  tag_name text not null,
  trait_id uuid not null references public.taste_traits(trait_id) on delete cascade,
  weight numeric not null check (weight > 0),
  created_at timestamptz not null default now(),
  normalized_tag_name text generated always as (lower(regexp_replace(btrim(tag_name), '[[:space:]]+'::text, ' '::text, 'g'::text))) stored,
  unique (tag_name,trait_id),
  unique (normalized_tag_name,trait_id)
);

create table if not exists public.game_trait_scores (
  game_id uuid not null references public.games(id) on delete cascade,
  trait_id uuid not null references public.taste_traits(trait_id) on delete cascade,
  trait_score numeric not null default 0 check (trait_score >= 0 and trait_score <= 100),
  updated_at timestamptz not null default now(),
  score_evidence jsonb not null default '{}'::jsonb,
  primary key (game_id,trait_id)
);

create table if not exists public.survey_trait_scores (
  session_id uuid not null references public.diagnosis_sessions(id) on delete cascade,
  trait_id uuid not null references public.taste_traits(trait_id) on delete cascade,
  trait_score numeric not null default 0,
  primary key (session_id,trait_id)
);

create table if not exists public.recommendation_records (
  id uuid primary key default gen_random_uuid(),
  session_id uuid references public.diagnosis_sessions(id) on delete set null,
  profile_id uuid references public.analysis_reports(id) on delete set null,
  recommendation_basis text not null,
  created_at timestamptz not null default now(),
  constraint recommendation_records_source_required check (session_id is not null or profile_id is not null)
);

create table if not exists public.recommendations (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references public.diagnosis_sessions(id) on delete cascade,
  game_id uuid not null references public.games(id) on delete restrict,
  rank integer not null check (rank > 0),
  match_score numeric not null check (match_score >= 0 and match_score <= 100),
  reason text,
  matched_tags text[] not null default array[]::text[],
  algorithm_version text,
  created_at timestamptz not null default now(),
  recommendation_record_id uuid references public.recommendation_records(id),
  unique (session_id,game_id),
  unique (session_id,rank),
  unique (recommendation_record_id,game_id),
  unique (recommendation_record_id,rank)
);

create table if not exists public.profile_evidence_games (
  profile_id uuid not null references public.analysis_reports(id) on delete cascade,
  game_id uuid not null references public.games(id) on delete cascade,
  similarity_score numeric,
  primary key (profile_id,game_id)
);

create table if not exists public.game_metadata_aliases (
  id uuid primary key default gen_random_uuid(),
  alias_name text not null check (btrim(alias_name) <> ''),
  canonical_name text not null check (btrim(canonical_name) <> ''),
  created_at timestamptz not null default now(),
  normalized_alias_name text,
  constraint game_metadata_aliases_alias_unique unique (alias_name),
  constraint game_metadata_aliases_normalized_alias_unique unique (normalized_alias_name)
);

create table if not exists public.game_metadata_sources (
  id uuid primary key default gen_random_uuid(),
  game_id uuid not null references public.games(id) on delete cascade,
  source_name text not null check (btrim(source_name) <> ''),
  metadata_type text not null check (metadata_type in ('genre','tag')),
  original_value text not null check (btrim(original_value) <> ''),
  created_at timestamptz not null default now(),
  normalized_original_value text,
  normalized_source_name text,
  constraint game_metadata_sources_unique unique (game_id,source_name,metadata_type,original_value),
  constraint game_metadata_sources_normalized_unique unique (game_id,source_name,metadata_type,normalized_original_value),
  constraint game_metadata_sources_normalized_source_value_unique unique (game_id,normalized_source_name,metadata_type,normalized_original_value)
);

create table if not exists public.user_states (
  user_id uuid primary key references auth.users(id) on delete cascade,
  state jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

-- Supporting indexes (safe to run repeatedly).
create index if not exists idx_answers_session on public.diagnosis_answers(session_id);
create index if not exists idx_diagnosis_sessions_user_id on public.diagnosis_sessions(user_id);
create index if not exists idx_game_trait_scores_trait_id on public.game_trait_scores(trait_id);
create index if not exists idx_game_trait_tag_rules_trait_id on public.game_trait_tag_rules(trait_id);
create index if not exists idx_option_trait_scores_trait_id on public.option_trait_scores(trait_id);
create index if not exists idx_profile_evidence_games_game_id on public.profile_evidence_games(game_id);
create index if not exists idx_recommendation_records_profile_id on public.recommendation_records(profile_id);
create index if not exists idx_recommendation_records_session_id on public.recommendation_records(session_id);
create index if not exists idx_recommendations_game_id on public.recommendations(game_id);
create index if not exists idx_recommendations_session on public.recommendations(session_id,rank);
create index if not exists idx_questions_track_stage on public.survey_questions(track,stage,question_no);
create index if not exists idx_survey_trait_scores_trait_id on public.survey_trait_scores(trait_id);

-- RLS is enabled on every public table. Client roles are explicitly denied;
-- the Python API uses the service-role key server-side.
do $$
declare t text;
begin
  foreach t in array array[
    'analysis_reports','analysis_scores','diagnosis_answers','diagnosis_sessions',
    'game_metadata_aliases','game_metadata_sources','game_trait_scores','game_trait_tag_rules',
    'games','option_trait_scores','profile_evidence_games','recommendation_records',
    'recommendations','survey_options','survey_questions','survey_trait_scores',
    'taste_traits','user_states','users'
  ] loop
    execute format('alter table public.%I enable row level security', t);
    execute format('drop policy if exists deny_direct_client_access on public.%I', t);
    execute format('create policy deny_direct_client_access on public.%I for all to anon, authenticated using (false) with check (false)', t);
  end loop;
end $$;

create or replace function public.set_games_updated_at()
returns trigger language plpgsql set search_path to '' as $$
begin
  new.updated_at = pg_catalog.now();
  return new;
end;
$$;

create or replace function public.validate_recommendation_record_source()
returns trigger language plpgsql set search_path to '' as $$
declare profile_session_id uuid;
begin
  if new.session_id is not null and new.profile_id is not null then
    select ar.session_id into profile_session_id
    from public.analysis_reports as ar where ar.id = new.profile_id;
    if profile_session_id is not null and new.session_id <> profile_session_id then
      raise exception 'Recommendation session_id does not match profile session_id';
    end if;
  end if;
  return new;
end;
$$;

create or replace function public.claim_guest_diagnosis_sessions(p_session_ids uuid[], p_user_id uuid)
returns integer language plpgsql security definer set search_path to '' as $$
declare requested_count integer; eligible_count integer; claimed_count integer;
begin
  select count(distinct sid) into requested_count
  from unnest(coalesce(p_session_ids, array[]::uuid[])) as sid;
  if requested_count = 0 then return 0; end if;
  if requested_count > 20 or p_user_id is null then
    raise exception 'invalid guest session claim request';
  end if;
  select count(*) into eligible_count from public.diagnosis_sessions
  where id = any(p_session_ids) and status = 'completed'
    and (user_id is null or user_id = p_user_id);
  if eligible_count <> requested_count then
    raise exception 'one or more guest sessions are unavailable';
  end if;
  update public.diagnosis_sessions set user_id = p_user_id
  where id = any(p_session_ids) and user_id is null and status = 'completed';
  get diagnostics claimed_count = row_count;
  return requested_count;
end;
$$;

create or replace function public.handle_new_user()
returns trigger language plpgsql security definer set search_path to '' as $$
begin
  insert into public.users(id,email,nickname)
  values(new.id,new.email,null)
  on conflict (id) do nothing;
  return new;
end;
$$;

revoke all on function public.claim_guest_diagnosis_sessions(uuid[],uuid) from public, anon, authenticated;
grant execute on function public.claim_guest_diagnosis_sessions(uuid[],uuid) to service_role;
revoke all on function public.handle_new_user() from public, anon, authenticated;
revoke all on function public.set_games_updated_at() from public, anon, authenticated;
revoke all on function public.validate_recommendation_record_source() from public, anon, authenticated;

-- Trigger definitions are replaced in-place to keep the snapshot repeatable.
drop trigger if exists trg_game_trait_scores_updated_at on public.game_trait_scores;
create trigger trg_game_trait_scores_updated_at before update on public.game_trait_scores
for each row execute function public.set_games_updated_at();
drop trigger if exists trg_games_updated_at on public.games;
create trigger trg_games_updated_at before update on public.games
for each row execute function public.set_games_updated_at();
drop trigger if exists check_recommendation_record_source on public.recommendation_records;
create trigger check_recommendation_record_source before insert or update on public.recommendation_records
for each row execute function public.validate_recommendation_record_source();

do $$
begin
  if not exists (
    select 1 from pg_trigger
    where tgname = 'on_auth_user_created'
      and tgrelid = 'auth.users'::regclass
      and not tgisinternal
  ) then
    create trigger on_auth_user_created after insert on auth.users
    for each row execute function public.handle_new_user();
  end if;
end $$;

-- Match the existing project's deny-by-default posture for current and future objects.
revoke all on all tables in schema public from anon, authenticated;
revoke all on all sequences in schema public from anon, authenticated;
alter default privileges in schema public revoke all on tables from anon, authenticated;
alter default privileges in schema public revoke all on sequences from anon, authenticated;
