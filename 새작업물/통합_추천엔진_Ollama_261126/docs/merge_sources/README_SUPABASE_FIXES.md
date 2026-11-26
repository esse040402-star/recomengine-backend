# RecomEngine Supabase 보안 및 비회원 진단 연결 수정

## 실제 Supabase 프로젝트에 적용한 변경
- `public` 19개 테이블의 RLS를 유지하고, `anon`/`authenticated`에 직접 허용되는 테이블 권한을 회수했습니다.
- 19개 테이블에 `deny_direct_client_access` restrictive 정책을 적용했습니다. FastAPI가 `service_role`로 접근하는 백엔드 전용 구조입니다.
- `public` 함수의 RPC 실행 권한을 `service_role`로 제한했습니다. `anon`/`authenticated` 실행 권한은 0건입니다.
- 기존/미래 public sequence 접근 권한도 `service_role` 중심으로 제한했습니다.
- `claim_guest_diagnosis_sessions`를 같은 계정에 반복 연결해도 성공하는 멱등 함수로 보완했습니다. 완료된 세션만 연결되고, 타 계정 소유/진행 중 세션은 거부됩니다.

## 코드 수정 파일
- `app/routers/account.py`: 가입/로그인 요청에서 비회원 세션 ID를 받아 계정 연결 RPC 실행
- `app/services/accounts.py`: 회원가입 요청이 기존 계정에 자동 로그인하지 않고 중복 가입을 거부하도록 수정
- `app/mock_db.py`: 회원가입/RPC mock 지원
- `app/routers/survey.py`, `app/docs.py`: 설문 문항 조회 API 설명 추가 및 회원가입/로그인 문서 갱신
- `frontend/src/services/guestSessionStore.js`: 완료된 비회원 진단 ID를 브라우저에 임시 보관
- `frontend/src/services/recommendationService.js`: 진단 완료 후 비회원 세션 ID 저장
- `frontend/src/services/accountService.js`, `frontend/src/state/AppContext.jsx`: 가입/로그인 때 ID 전달 및 연결 완료 시 정리
- `frontend/src/hooks/profileActions.js`: 세션 연결 실패를 사용자에게 알림
- `tests/`, `frontend/tests/`: 세션 연결 및 문서/API 테스트 보강
- `sql/003`~`sql/006`: 실제 적용된 SQL 변경사항을 프로젝트 내 SQL 파일로 보관

## 검증 결과
- 백엔드: `pytest -q` → **98 passed**
- 프론트엔드: `npm test` → **9 passed**
- 변경한 프론트엔드 JS/JSX 파일 Babel 파싱: 모두 성공
- 실제 Supabase에서 `service_role`로 게스트 세션 연결 RPC 실행: 테스트 세션을 트랜잭션 롤백 방식으로 검증 성공
- Supabase 보안 진단: RLS 정책 누락 경고 해소. 현재 남은 보안 경고는 Leaked Password Protection 비활성화 1건
- Supabase 성능 진단: 미사용으로 표시된 인덱스 정보 10건. 테이블 데이터가 적어 아직 사용되지 않은 것으로 보이며, 외래키/향후 조회에 필요할 수 있어 무작정 삭제하지 않았습니다.
- 프론트엔드 빌드: 이 실행 환경에 포함된 `node_modules`가 Windows용이며 Linux용 Rolldown 네이티브 바인딩이 없어 여기서는 빌드 검증 불가. 사용자 PC에서 `npm ci` 후 `npm run build`로 최종 확인해야 합니다.

## 남은 대시보드 작업
Supabase Auth의 **Leaked Password Protection**은 SQL로 켤 수 있는 설정이 아닙니다. Supabase Dashboard → Authentication → Providers → Email의 Password Security 설정에서 활성화해야 합니다. Supabase 공식 문서에 따르면 이 기능은 Pro 이상 요금제에서 제공됩니다: https://supabase.com/docs/guides/auth/password-security

## 주의
이 패치 아카이브는 저장소 파일에 반영할 변경분입니다. 실제 Supabase DB 마이그레이션은 이미 프로젝트에 적용했습니다. GitHub main 반영 및 Render 재배포는 이 작업에서 수행하지 않았습니다.
