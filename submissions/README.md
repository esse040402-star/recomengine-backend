# 새 작업물 제출 · 팀원 검토

각자가 **개인 환경에서 오류를 확인한 신규 작업물**을 파트별로 공유하는 공간입니다. 이 안의 파일은 승인 이전에는 기존 실행본에 자동 적용되지 않습니다.

| 폴더 | 대상 |
|---|---|
| [frontend/](frontend/) | React 화면·스타일·인터랙션 |
| [backend/](backend/) | FastAPI 서버·API·추천 로직 |
| [database/](database/) | ERD·SQL·DB 구조 |
| [docs/](docs/) | 기능 명세서·스토리보드 등 |

**폴더 형식:** `submissions/파트/작성자-기능명/`

예: `submissions/frontend/kim-survey-redesign/` 아래에 새 소스 파일과 같은 폴더의 `README.md`를 올려 주세요. 다른 사람의 제출물은 덮어쓰지 마세요.

**검토 절차:** 개인 실행·테스트 → 이 폴더에 제출 → 팀원 리뷰 → 승인된 변경만 `current-project/`에 통합 → 전체 테스트 및 PR 확인.

**README에는** 변경 목적, 기존 실행본 적용 대상 경로, 실행법과 테스트 결과, 추가 의존성, 미해결 오류, 검토 의견을 적어 주세요. [복사용 제출 양식](_template/README.md)

주의: `.env`, 개인 토큰, Supabase 서비스 키, 실제 사용자 데이터를 올리지 마세요. DB SQL은 검토 전 임의 실행하지 마세요.
