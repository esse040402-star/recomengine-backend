-- Supabase 대시보드 > SQL Editor 에서 한 번 실행하세요.

-- 1) 프로토타입의 질문 ID(q1, d01, p1 ...)는 survey_questions 의 ID(G_ONB_01 ...)와 달라서
--    diagnosis_answers.question_id 의 외래키를 제거합니다.
alter table public.diagnosis_answers
  drop constraint if exists diagnosis_answers_question_id_fkey;

-- 2) 같은 세션에서 같은 질문의 답변은 하나만 (답변 upsert에 필요)
create unique index if not exists diagnosis_answers_session_question_uidx
  on public.diagnosis_answers (session_id, question_id);

-- 3) 같은 세션에 같은 게임이 중복 추천되지 않도록
create unique index if not exists recommendations_session_game_uidx
  on public.recommendations (session_id, game_id);

-- 4) RLS 활성화: 정책이 없으므로 anon 키로는 접근 불가, 백엔드(service role)만 접근 가능
alter table public.diagnosis_sessions enable row level security;
alter table public.survey_questions   enable row level security;
alter table public.diagnosis_answers  enable row level security;
alter table public.analysis_reports   enable row level security;
alter table public.analysis_scores    enable row level security;
alter table public.games              enable row level security;
alter table public.recommendations    enable row level security;
