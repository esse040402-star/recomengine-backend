# Supabase 운영 DB 업데이트 기록 (2026-11-17)

## 적용 완료
- survey_questions 74 유지
- taste_traits 6
- survey_options 366
- option_trait_scores 346
- game_trait_tag_rules 118
- diagnosis_sessions 5 유지
- diagnosis_answers 28 유지
- public 테이블 19개 RLS 활성화
- anon/authenticated 직접 접근 테이블 0, 실행 가능 함수 0, 사용 가능 시퀀스 0

## 적용 제한
`postgres` 역할은 `supabase_admin`의 멤버가 아니므로 `ALTER DEFAULT PRIVILEGES FOR ROLE supabase_admin`가 거부됨. `postgres` 소유 객체의 미래 기본 권한은 service_role 전용으로 설정됨. `supabase_admin` 소유 기본 ACL은 여전히 anon/authenticated 권한을 포함하므로, Supabase 프로젝트 소유자/관리자가 해당 역할 권한으로 별도 조정해야 함.

## 미완료
- games 테이블은 현재 0행이므로 game_trait_scores는 0행. 게임 데이터 수집 후 점수 생성/검증 필요.
- Supabase Security Advisor: leaked password protection disabled 경고 1건.
- Render 연결은 워크스페이스 확인 및 서비스 목록 조회가 아직 완료되지 않음.
- Frontend npm ci는 실행환경 Node 22.16.0 (요구 22.18.0 이상) 및 네트워크 시간초과로 완료되지 않아 Vite build 미실행.
