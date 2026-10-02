-- 새 프로토타입의 계정 기능용: 로그인한 사용자의 화면 상태(설문 답변, 찜한 게임 등)를 통째로 저장합니다.
-- DB 담당자와 합의한 뒤 Supabase SQL Editor 에서 실행하세요. (기존 테이블은 바꾸지 않고 새 테이블만 추가합니다)
create table if not exists public.user_states (
  user_id    uuid primary key references auth.users(id) on delete cascade,
  state      jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

-- 정책이 없으므로 anon/authenticated 키로는 접근할 수 없고, 백엔드(service role)만 접근합니다.
alter table public.user_states enable row level security;
